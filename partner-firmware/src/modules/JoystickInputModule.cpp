/**
 * @file JoystickInputModule.cpp
 * @brief Joystick input handling implementation
 */

#include "JoystickInputModule.h"

#ifdef HAS_JOYSTICK

#include "configuration.h"
#include "main.h"
#include "MeshService.h"
#include <esp_adc_cal.h>
#include <driver/adc.h>

// Singleton instance
JoystickInputModule *JoystickInputModule::instance = nullptr;
JoystickInputModule *joystickInputModule = nullptr;

// ADC calibration characteristics
static esp_adc_cal_characteristics_t adc_chars;
static bool adc_cal_done = false;

JoystickInputModule::JoystickInputModule()
    : SinglePortModule("joystick", meshtastic_PortNum_PRIVATE_APP),
      seqCounter(0),
      currentLayer(LAYER_GLOBAL),
      lastButtonPressTime(0),
      buttonDownTime(0),
      pressCount(0),
      buttonWasPressed(false),
      longPressTriggered(false),
      adcInitialized(false)
{
    instance = this;
    joystickInputModule = this;
    
    memset(&currentState, 0, sizeof(currentState));
    memset(&lastSentState, 0, sizeof(lastSentState));
    
    initADC();
    
    // Configure button pins with internal pullup
    pinMode(JOYSTICK_BTN_PIN, INPUT_PULLUP);
    
#ifdef BUTTON_HOME_PIN
    pinMode(BUTTON_HOME_PIN, INPUT_PULLUP);
#endif

#ifdef BUTTON_BACK_PIN
    pinMode(BUTTON_BACK_PIN, INPUT_PULLUP);
#endif

    LOG_INFO("JoystickInputModule initialized\n");
}

JoystickInputModule *JoystickInputModule::getInstance()
{
    if (!instance) {
        instance = new JoystickInputModule();
    }
    return instance;
}

void JoystickInputModule::initADC()
{
    // Configure ADC1 (works alongside WiFi/BLE)
    adc1_config_width(ADC_WIDTH_BIT_12);
    
    // Configure X-axis channel
    // GPIO34 = ADC1_CH6
    adc1_config_channel_atten(ADC1_CHANNEL_6, ADC_ATTEN_DB_11);
    
    // GPIO35 = ADC1_CH7
    adc1_config_channel_atten(ADC1_CHANNEL_7, ADC_ATTEN_DB_11);
    
    // Calibrate ADC
    esp_adc_cal_value_t cal_type = esp_adc_cal_characterize(
        ADC_UNIT_1,
        ADC_ATTEN_DB_11,
        ADC_WIDTH_BIT_12,
        1100,  // Default Vref
        &adc_chars
    );
    
    if (cal_type == ESP_ADC_CAL_VAL_EFUSE_VREF) {
        LOG_DEBUG("ADC calibration: eFuse Vref\n");
    } else if (cal_type == ESP_ADC_CAL_VAL_EFUSE_TP) {
        LOG_DEBUG("ADC calibration: eFuse Two Point\n");
    } else {
        LOG_DEBUG("ADC calibration: Default\n");
    }
    
    adc_cal_done = true;
    adcInitialized = true;
}

int16_t JoystickInputModule::readAxis(uint8_t pin, bool invert)
{
    if (!adcInitialized) {
        return 0;
    }
    
    // Determine ADC channel from pin
    adc1_channel_t channel;
    if (pin == JOYSTICK_X_PIN) {
        channel = ADC1_CHANNEL_6;  // GPIO34
    } else if (pin == JOYSTICK_Y_PIN) {
        channel = ADC1_CHANNEL_7;  // GPIO35
    } else {
        return 0;
    }
    
    // Read with oversampling for noise reduction
    int32_t sum = 0;
    const int samples = 4;
    for (int i = 0; i < samples; i++) {
        sum += adc1_get_raw(channel);
    }
    int raw = sum / samples;
    
    // Center around midpoint
    int centered = raw - JOYSTICK_CENTER;
    
    // Apply deadzone
    if (abs(centered) < JOYSTICK_DEADZONE) {
        return 0;
    }
    
    // Remove deadzone from calculation range
    if (centered > 0) {
        centered -= JOYSTICK_DEADZONE;
    } else {
        centered += JOYSTICK_DEADZONE;
    }
    
    // Normalize to -100..+100
    int16_t normalized = (centered * 100) / (JOYSTICK_CENTER - JOYSTICK_DEADZONE);
    
    // Clamp to valid range
    if (normalized > 100) normalized = 100;
    if (normalized < -100) normalized = -100;
    
    // Apply inversion if needed
    if (invert) {
        normalized = -normalized;
    }
    
    return normalized;
}

void JoystickInputModule::processButtons()
{
    uint32_t now = millis();
    
    // Read joystick button (active LOW)
    bool btnPressed = (digitalRead(JOYSTICK_BTN_PIN) == LOW);
    
    currentState.buttons = 0;
    
    // Detect button press edge
    if (btnPressed && !buttonWasPressed) {
        // Button just pressed
        buttonDownTime = now;
        longPressTriggered = false;
        
        // Check for double press
        if (now - lastButtonPressTime < BUTTON_DOUBLE_PRESS_MS) {
            pressCount++;
        } else {
            pressCount = 1;
        }
        lastButtonPressTime = now;
    }
    
    // Current button state
    if (btnPressed) {
        currentState.buttons |= BTN_PRESS;
        
        // Check for long press
        if (!longPressTriggered && (now - buttonDownTime > BUTTON_LONG_PRESS_MS)) {
            currentState.buttons |= BTN_LONG;
            longPressTriggered = true;
        }
    }
    
    // Double press detection (on release)
    if (!btnPressed && buttonWasPressed && pressCount >= 2) {
        currentState.buttons |= BTN_DOUBLE;
    }
    
    buttonWasPressed = btnPressed;
    
    // Read Home button
#ifdef BUTTON_HOME_PIN
    if (digitalRead(BUTTON_HOME_PIN) == LOW) {
        currentState.buttons |= BTN_HOME;
    }
#endif

    // Read Back button
#ifdef BUTTON_BACK_PIN
    if (digitalRead(BUTTON_BACK_PIN) == LOW) {
        currentState.buttons |= BTN_BACK;
    }
#endif
}

bool JoystickInputModule::shouldSendUpdate()
{
    // Always send on button change
    if (currentState.buttons != lastSentState.buttons) {
        return true;
    }
    
    // Send on significant axis movement
    if (abs(currentState.x - lastSentState.x) > 2) {
        return true;
    }
    if (abs(currentState.y - lastSentState.y) > 2) {
        return true;
    }
    
    // Send on layer change
    if (currentState.layer != lastSentState.layer) {
        return true;
    }
    
    return false;
}

void JoystickInputModule::sendJoystickEvent()
{
    currentState.seq = ++seqCounter;
    currentState.layer = currentLayer;
    
    // Send via BLE to main device
    sendJoystickToMainDevice(currentState);
    
    // Update last sent state
    memcpy(&lastSentState, &currentState, sizeof(JoystickEvent));
    
    LOG_DEBUG("Joystick event: x=%d y=%d btn=0x%02x layer=%d seq=%u\n",
              currentState.x, currentState.y, currentState.buttons,
              currentState.layer, currentState.seq);
}

int32_t JoystickInputModule::runOnce()
{
    // Read joystick axes
    currentState.x = readAxis(JOYSTICK_X_PIN, JOYSTICK_INVERT_X);
    currentState.y = readAxis(JOYSTICK_Y_PIN, JOYSTICK_INVERT_Y);
    
    // Process button states
    processButtons();
    
    // Send update if needed
    if (shouldSendUpdate()) {
        sendJoystickEvent();
    }
    
    // Return ms until next run (100 Hz = 10ms)
    return 1000 / JOYSTICK_SAMPLE_RATE_HZ;
}

JoystickEvent JoystickInputModule::getCurrentState() const
{
    return currentState;
}

bool JoystickInputModule::hasMovement(int threshold) const
{
    return (abs(currentState.x) > threshold || abs(currentState.y) > threshold);
}

void JoystickInputModule::setLayer(uint8_t layer)
{
    if (layer <= LAYER_MESH_INBOX) {
        currentLayer = layer;
    }
}

// The actual BLE send is implemented in MainDeviceBridgeModule
// This is a forward declaration / weak symbol that gets overridden
__attribute__((weak)) void sendJoystickToMainDevice(const JoystickEvent &evt)
{
    LOG_WARN("sendJoystickToMainDevice not implemented - MainDeviceBridgeModule not linked?\n");
}

#endif // HAS_JOYSTICK

