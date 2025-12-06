/**
 * @file main.cpp
 * @brief Standalone Joystick Partner Device Firmware
 * 
 * ESP32 controller device with:
 * - Joystick input (KY-023)
 * - Tilt sensor (SW-520D on GPIO16)
 * - Buttons (Home, Back)
 * - USB Serial communication with pi wrist computer
 * 
 * Sends joystick events as 8-byte packets via USB Serial at 115200 baud.
 */

#include <Arduino.h>
#include <driver/adc.h>
#include <driver/gpio.h>
#include <esp_adc_cal.h>
#include "modules/JoystickEvent.h"

// Include pin definitions from variant.h
#include "variants/translator_partner/variant.h"

// BLE support
#ifdef USE_BLE_JOYSTICK
#include <NimBLEDevice.h>
#include <NimBLEServer.h>
#include <NimBLECharacteristic.h>

// BLE Service UUIDs (must match Pi side)
#define REMOTE_INPUT_SERVICE_UUID "4f9a0001-8c3f-4a0e-89a7-6d277cf9a000"
#define JOYSTICK_EVENT_CHAR_UUID  "4f9a0002-8c3f-4a0e-89a7-6d277cf9a000"

static NimBLEServer* pServer = nullptr;
static NimBLECharacteristic* pJoystickChar = nullptr;
static bool deviceConnected = false;

class ServerCallbacks: public NimBLEServerCallbacks {
    void onConnect(NimBLEServer* pServer) {
        deviceConnected = true;
    }
    void onDisconnect(NimBLEServer* pServer) {
        deviceConnected = false;
        NimBLEDevice::startAdvertising();
    }
};
#endif

// ADC calibration
static esp_adc_cal_characteristics_t adc_chars;
static bool adc_cal_done = false;

void setup() {
    // Initialize USB Serial
    Serial.begin(115200);
    Serial.setTimeout(10);
    delay(1000);  // Wait for serial port to be ready
    
    // Send startup message
#ifdef DEBUG_JOYSTICK
    Serial.println("\n\n=== Joystick Partner Device (DEBUG MODE) ===");
    Serial.println("ESP32 Controller with Joystick + Tilt Sensor");
    Serial.printf("USB Serial: %d baud\n", 115200);
    Serial.println("DEBUG MODE: Sending readable text output");
    Serial.println("Use production build (without DEBUG_JOYSTICK) for binary packets\n");
#else
    // In production mode, DO NOT send text messages - only binary packets!
    // Text messages will corrupt the Pi's binary packet reading.
    // The Pi expects pure binary data starting immediately.
    // (No Serial.println calls here - they would break packet alignment)
#endif
    
    // Initialize ADC for joystick
#ifdef HAS_JOYSTICK
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(ADC1_CHANNEL_6, ADC_ATTEN_DB_11);  // GPIO34 -> Y axis
    adc1_config_channel_atten(ADC1_CHANNEL_7, ADC_ATTEN_DB_11);  // GPIO35 -> X axis
    
    esp_adc_cal_characterize(
        ADC_UNIT_1,
        ADC_ATTEN_DB_11,
        ADC_WIDTH_BIT_12,
        1100,
        &adc_chars
    );
    
    adc_cal_done = true;
#ifdef DEBUG_JOYSTICK
    Serial.println("ADC initialized");
    Serial.println("\n=== ADC Channel Test ===");
    Serial.println("Testing ADC1 channels for joystick:");
    // Note: GPIO32 and GPIO33 are digital pins (buttons), not ADC
    Serial.println("Channel 6 (GPIO34) - Y axis: " + String(adc1_get_raw(ADC1_CHANNEL_6)));
    Serial.println("Channel 7 (GPIO35) - X axis: " + String(adc1_get_raw(ADC1_CHANNEL_7)));
    Serial.println("Expected: Should read ~1500-2500 when centered");
    Serial.println("If reading 0, very low, or 4095 (max), check wiring!");
    Serial.println("Reading 4095 means pin is floating (not connected)");
    Serial.println("\nNOTE: GPIO35 reading 4095 = X axis not connected!");
#endif
    
    // Initialize GPIO pins BEFORE reading them
    // GPIO32 and GPIO33 may not have reliable internal pull-ups on ESP32
    // Using ESP-IDF specific pull-up configuration for these pins
    pinMode(JOYSTICK_BTN_PIN, INPUT);  // GPIO32: Confirm/Select button
    pinMode(BUTTON_HOME_PIN, INPUT);  // GPIO33: Back/Cancel button
    
    // Configure pull-up resistors (LOW = pressed, HIGH = not pressed)
    gpio_set_pull_mode((gpio_num_t)JOYSTICK_BTN_PIN, GPIO_PULLUP_ONLY);
    gpio_set_pull_mode((gpio_num_t)BUTTON_HOME_PIN, GPIO_PULLUP_ONLY);
    
    delay(50);  // Allow pull-up to stabilize
    
#ifdef DEBUG_JOYSTICK
    Serial.println("\nButton states (should be HIGH when not pressed):");
    Serial.println("GPIO32 (Joystick button): " + String(digitalRead(JOYSTICK_BTN_PIN)));
    Serial.println("GPIO33 (Back button): " + String(digitalRead(BUTTON_HOME_PIN)));
    Serial.println("(LOW = pressed, HIGH = not pressed)");
    Serial.println("\n*** IMPORTANT: DEBUG MODE sends TEXT, not binary packets! ***");
    Serial.println("*** The Pi needs BINARY packets to work! ***");
    Serial.println("*** Build with: pio run -e translator-partner -t upload ***");
    Serial.println("*** (without -debug) for actual use with the Pi ***\n");
#endif
    // GPIO25 button not used
#endif
    
#ifdef HAS_TILT_SENSOR
    pinMode(TILT_SENSOR_PIN, INPUT_PULLUP);
#ifdef DEBUG_JOYSTICK
    Serial.printf("Tilt sensor (SW-520D) on GPIO%d\n", TILT_SENSOR_PIN);
#endif
#endif
    
#ifdef DEBUG_JOYSTICK
    Serial.println("GPIO pins initialized");
    Serial.println("Ready! Sending joystick events via USB Serial...\n");
#endif
    
    // Flush serial buffer before starting binary data stream
    Serial.flush();
    delay(100);  // Give time for messages to be sent
    
#ifdef USE_BLE_JOYSTICK
    // Initialize BLE
    NimBLEDevice::init(BLE_NAME);
    NimBLEDevice::setPower(ESP_PWR_LVL_P9);  // Max power for better range
    
    pServer = NimBLEDevice::createServer();
    pServer->setCallbacks(new ServerCallbacks());
    
    // Create Remote Input Service
    NimBLEService* pService = pServer->createService(REMOTE_INPUT_SERVICE_UUID);
    
    // Create Joystick Event Characteristic
    pJoystickChar = pService->createCharacteristic(
        JOYSTICK_EVENT_CHAR_UUID,
        NIMBLE_PROPERTY::NOTIFY
    );
    
    pService->start();
    
    // Start advertising
    NimBLEAdvertising* pAdvertising = NimBLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(REMOTE_INPUT_SERVICE_UUID);
    pAdvertising->setScanResponse(true);
    pAdvertising->setMinPreferred(0x06);  // helps with iPhone connections issue
    pAdvertising->setMinPreferred(0x12);
    NimBLEDevice::startAdvertising();
    
#ifdef DEBUG_JOYSTICK
    Serial.println("BLE initialized and advertising as 'TransPartner'");
    Serial.println("Connect from Pi using BLE joystick handler");
#endif
#endif
}

void loop() {
#ifdef HAS_JOYSTICK
    static uint32_t lastSend = 0;
    static JoystickEvent lastState = {};
    uint32_t now = millis();
    
    // Read at 100 Hz (every 10ms)
    if (now - lastSend < 10) {
        delay(1);
        return;
    }
    lastSend = now;
    
    JoystickEvent evt = {};
    evt.seq = now / 10;  // Simple sequence number
    
    // Auto-calibration: find actual center values on first run
    // Declare these static variables at the start so they're accessible throughout
    static bool calibrated = false;
    static int center_x = JOYSTICK_CENTER;
    static int center_y = JOYSTICK_CENTER;
    static uint32_t calibration_start = 0;
    
    // Read joystick axes
    int raw_x = adc1_get_raw(ADC1_CHANNEL_7);  // GPIO35 -> X axis (VRX)
    int raw_y = adc1_get_raw(ADC1_CHANNEL_6);  // GPIO34 -> Y axis (VRY)
    
    // Check if X axis is floating (reading max value = not connected)
    static bool x_floating_warned = false;
    if (raw_x >= 4090 && !x_floating_warned) {
#ifdef DEBUG_JOYSTICK
        Serial.println("\n*** WARNING: X axis (GPIO35) is floating (reading 4095)! ***");
        Serial.println("Possible causes:");
        Serial.println("  1. VRX wire not connected to GPIO35");
        Serial.println("  2. Loose/broken connection");
        Serial.println("  3. Joystick module VRX pin not working");
        Serial.println("  4. VRX and VRY might be swapped on joystick module");
        Serial.println("  5. Joystick module not powered (check VCC to 3.3V)");
        Serial.println("Trying workaround: using Y axis center for X...\n");
#endif
        x_floating_warned = true;
    }
    
    // If X is floating, use Y's center as fallback (better than 4095)
    if (raw_x >= 4090) {
        raw_x = center_y;  // Use Y center as reasonable fallback
    }
    
    // Handle Y axis hitting max (4095) - might be extreme position or floating
    // Clamp to reasonable range to avoid calculation issues
    if (raw_y >= 4090) {
        raw_y = 4090;  // Clamp instead of using center, to preserve extreme position detection
    }
    
    if (!calibrated) {
        if (calibration_start == 0) {
            calibration_start = now;
        }
        // Calibrate for 2 seconds (assume joystick is centered)
        if (now - calibration_start < 2000) {
            // Accumulate samples to find average center
            static int32_t sum_x = 0, sum_y = 0;
            static int samples = 0;
            sum_x += raw_x;
            sum_y += raw_y;
            samples++;
            center_x = sum_x / samples;
            center_y = sum_y / samples;
            return;  // Don't send data during calibration
        } else {
            calibrated = true;
#ifdef DEBUG_JOYSTICK
            Serial.printf("Calibration complete: center_x=%d center_y=%d\n", center_x, center_y);
            Serial.printf("Expected center: %d (if very different, check wiring)\n", JOYSTICK_CENTER);
            
            // Warn if calibration center is suspiciously high (floating pins)
            if (center_x > 3500 || center_y > 3500) {
                Serial.println("\n*** WARNING: Calibration center is very high (>3500)! ***");
                Serial.println("This usually means the joystick pins are FLOATING (not connected)!");
                Serial.println("Check wiring:");
                Serial.println("  - GPIO34 (Y axis/VRY) should connect to joystick module");
                Serial.println("  - GPIO35 (X axis/VRX) should connect to joystick module");
                Serial.println("  - Joystick module needs VCC (3.3V) and GND connected");
                Serial.println("  - If pins are floating, they read 4095 (max value)");
                Serial.println("  - Joystick will not work correctly with floating pins!\n");
            } else if (abs(center_x - JOYSTICK_CENTER) > 1000 || abs(center_y - JOYSTICK_CENTER) > 1000) {
                Serial.println("\n*** WARNING: Calibration center is far from expected value! ***");
                Serial.println("Expected ~2048, but got very different values.");
                Serial.println("This might indicate wiring issues or wrong joystick module.\n");
            }
#endif
        }
    }
    
    // Center and normalize using calibrated center values
    int centered_x = raw_x - center_x;
    int centered_y = raw_y - center_y;
    
    // Apply deadzone
    if (abs(centered_x) < JOYSTICK_DEADZONE) centered_x = 0;
    else if (centered_x > 0) centered_x -= JOYSTICK_DEADZONE;
    else centered_x += JOYSTICK_DEADZONE;
    
    if (abs(centered_y) < JOYSTICK_DEADZONE) centered_y = 0;
    else if (centered_y > 0) centered_y -= JOYSTICK_DEADZONE;
    else centered_y += JOYSTICK_DEADZONE;
    
    // Normalize to -100..+100 using calibrated center
    // Use a reasonable range based on typical joystick movement
    int range = (JOYSTICK_CENTER - JOYSTICK_DEADZONE);
    if (range < 100) range = 100;  // Safety check
    
    evt.x = (centered_x * 100) / range;
    evt.y = (centered_y * 100) / range;
    if (JOYSTICK_INVERT_Y) evt.y = -evt.y;
    
    // Clamp
    if (evt.x > 100) evt.x = 100;
    if (evt.x < -100) evt.x = -100;
    if (evt.y > 100) evt.y = 100;
    if (evt.y < -100) evt.y = -100;
    
    // Process tilt sensor (overrides joystick if tilted)
#ifdef HAS_TILT_SENSOR
    bool tilted = (digitalRead(TILT_SENSOR_PIN) == LOW);
    if (tilted) {
        if (TILT_DIRECTION_X != 0) {
            evt.x = TILT_DIRECTION_X * TILT_MOVEMENT_SPEED;
        }
        if (TILT_DIRECTION_Y != 0) {
            evt.y = TILT_DIRECTION_Y * TILT_MOVEMENT_SPEED;
        }
    }
#endif
    
    // Read buttons
    // Joystick button (GPIO32) = Confirm/Select (left click)
    // Button on GPIO33 = Back/Cancel (right click/ESC)
    evt.buttons = 0;
    
    // Read raw button states
    int gpio32_raw = digitalRead(JOYSTICK_BTN_PIN);
    int gpio33_raw = digitalRead(BUTTON_HOME_PIN);
    
    // Button reading: active LOW (button connects to GND when pressed)
    // LOW (0) = pressed, HIGH (1) = not pressed (with pull-up)
    bool joystick_btn = (gpio32_raw == LOW);
    bool back_btn = (gpio33_raw == LOW);
    
    if (joystick_btn) {
        evt.buttons |= 0x01;  // Bit0: Confirm/Select (left click)
    }
    if (back_btn) {
        evt.buttons |= 0x10;  // Bit4: Back/Cancel (right click/ESC)
    }
    
#ifdef DEBUG_JOYSTICK
    // Track button state changes for debugging
    static int last_gpio32 = -1;
    static int last_gpio33 = -1;
    static uint32_t lastButtonPrint = 0;
    
    // Print button state changes immediately, or every 500ms to show current state
    bool buttonStateChanged = (gpio32_raw != last_gpio32 || gpio33_raw != last_gpio33);
    bool periodicButtonPrint = (now - lastButtonPrint >= 500);
    
    if (buttonStateChanged || periodicButtonPrint) {
        if (buttonStateChanged) {
            Serial.printf("*** BUTTON CHANGE: GPIO32=%d->%d GPIO33=%d->%d (LOW=pressed) btn=0x%02x ***\n",
                         last_gpio32, gpio32_raw, last_gpio33, gpio33_raw, evt.buttons);
        } else {
            Serial.printf("Button state: GPIO32=%d GPIO33=%d (LOW=pressed, HIGH=not pressed) btn=0x%02x\n",
                         gpio32_raw, gpio33_raw, evt.buttons);
        }
        last_gpio32 = gpio32_raw;
        last_gpio33 = gpio33_raw;
        lastButtonPrint = now;
    }
#endif
    
    evt.layer = 0;  // Global layer
    
    // Send periodic updates (every 100ms) or on change (whichever comes first)
    // This ensures the receiver knows the device is alive and responsive
    static uint32_t lastPeriodicSend = 0;
    bool stateChanged = (evt.x != lastState.x || evt.y != lastState.y || evt.buttons != lastState.buttons);
    bool periodicUpdate = (now - lastPeriodicSend >= 100);  // Send at least every 100ms
    
    // Always send at least every 100ms, even if nothing changed (keep-alive)
    if (stateChanged || periodicUpdate) {
#ifdef DEBUG_JOYSTICK
        // In debug mode, print all state changes and periodic updates
        // Print more frequently so you can see what's happening
        static uint32_t lastDebugPrint = 0;
        bool shouldPrint = stateChanged || (now - lastDebugPrint >= 200);  // Print on change or every 200ms
        
        if (shouldPrint) {
            bool buttonChanged = (evt.buttons != lastState.buttons);
            
            // Always print button state changes immediately
            if (buttonChanged) {
                Serial.printf("*** BUTTON CHANGE: btn=0x%02x (GPIO32=%d GPIO33=%d) ***\n",
                             evt.buttons, digitalRead(JOYSTICK_BTN_PIN), digitalRead(BUTTON_HOME_PIN));
            }
            
            // Print joystick values
            Serial.printf("Joy: x=%4d y=%4d btn=0x%02x | raw: x=%4d y=%4d | center: x=%4d y=%4d | GPIO32=%d GPIO33=%d\n", 
                         evt.x, evt.y, evt.buttons, raw_x, raw_y, center_x, center_y,
                         digitalRead(JOYSTICK_BTN_PIN), digitalRead(BUTTON_HOME_PIN));
            
            lastDebugPrint = now;
        }
#else
        // Production mode: send via USB Serial
        // Always send via USB Serial (BLE disabled)
        size_t written = Serial.write((uint8_t *)&evt, sizeof(JoystickEvent));
        if (written != sizeof(JoystickEvent)) {
            // Packet write failed - this shouldn't happen but log it
            static uint32_t lastError = 0;
            if (now - lastError > 1000) {  // Only log once per second
                // Can't use Serial.println in production, but this helps debug
                lastError = now;
            }
        }
        Serial.flush();  // Ensure data is sent immediately
#endif
        
        // Update tracking variables
        if (stateChanged) {
            lastState = evt;
        }
        // Always update periodic send time when we send a packet
        lastPeriodicSend = now;
    }
#else
    delay(100);
#endif
}

