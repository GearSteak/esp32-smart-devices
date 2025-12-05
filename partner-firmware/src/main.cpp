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
#include <esp_adc_cal.h>
#include "modules/JoystickEvent.h"

// Include pin definitions from variant.h
#include "variants/translator_partner/variant.h"

// ADC calibration
static esp_adc_cal_characteristics_t adc_chars;
static bool adc_cal_done = false;

void setup() {
    // Initialize USB Serial
    Serial.begin(115200);
    Serial.setTimeout(10);
    delay(1000);  // Wait for serial port to be ready
    
    Serial.println("\n\n=== Joystick Partner Device ===");
    Serial.println("ESP32 Controller with Joystick + Tilt Sensor");
    Serial.printf("USB Serial: %d baud\n", 115200);
    
    // Initialize ADC for joystick
#ifdef HAS_JOYSTICK
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(ADC1_CHANNEL_6, ADC_ATTEN_DB_11);  // GPIO34
    adc1_config_channel_atten(ADC1_CHANNEL_7, ADC_ATTEN_DB_11);  // GPIO35
    
    esp_adc_cal_value_t cal_type = esp_adc_cal_characterize(
        ADC_UNIT_1,
        ADC_ATTEN_DB_11,
        ADC_WIDTH_BIT_12,
        1100,
        &adc_chars
    );
    
    adc_cal_done = true;
    Serial.println("ADC initialized");
    
    // Initialize GPIO pins
    pinMode(JOYSTICK_BTN_PIN, INPUT_PULLUP);
    pinMode(BUTTON_HOME_PIN, INPUT_PULLUP);
    pinMode(BUTTON_BACK_PIN, INPUT_PULLUP);
    
#ifdef HAS_TILT_SENSOR
    pinMode(TILT_SENSOR_PIN, INPUT_PULLUP);
    Serial.printf("Tilt sensor (SW-520D) on GPIO%d\n", TILT_SENSOR_PIN);
#endif
    
    Serial.println("GPIO pins initialized");
    Serial.println("Ready! Sending joystick events via USB Serial...\n");
#endif
}

void loop() {
#ifdef HAS_JOYSTICK
    static uint32_t lastSend = 0;
    static JoystickEvent lastState = {0};
    uint32_t now = millis();
    
    // Read at 100 Hz (every 10ms)
    if (now - lastSend < 10) {
        delay(1);
        return;
    }
    lastSend = now;
    
    JoystickEvent evt = {0};
    evt.seq = now / 10;  // Simple sequence number
    
    // Read joystick axes
    int raw_x = adc1_get_raw(ADC1_CHANNEL_6);
    int raw_y = adc1_get_raw(ADC1_CHANNEL_7);
    
    // Center and normalize
    int centered_x = raw_x - JOYSTICK_CENTER;
    int centered_y = raw_y - JOYSTICK_CENTER;
    
    // Apply deadzone
    if (abs(centered_x) < JOYSTICK_DEADZONE) centered_x = 0;
    else if (centered_x > 0) centered_x -= JOYSTICK_DEADZONE;
    else centered_x += JOYSTICK_DEADZONE;
    
    if (abs(centered_y) < JOYSTICK_DEADZONE) centered_y = 0;
    else if (centered_y > 0) centered_y -= JOYSTICK_DEADZONE;
    else centered_y += JOYSTICK_DEADZONE;
    
    // Normalize to -100..+100
    evt.x = (centered_x * 100) / (JOYSTICK_CENTER - JOYSTICK_DEADZONE);
    evt.y = (centered_y * 100) / (JOYSTICK_CENTER - JOYSTICK_DEADZONE);
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
    evt.buttons = 0;
    if (digitalRead(JOYSTICK_BTN_PIN) == LOW) {
        evt.buttons |= 0x01;  // Press
    }
    if (digitalRead(BUTTON_HOME_PIN) == LOW) {
        evt.buttons |= 0x08;  // Home
    }
    if (digitalRead(BUTTON_BACK_PIN) == LOW) {
        evt.buttons |= 0x10;  // Back
    }
    
    evt.layer = 0;  // Global layer
    
    // Send if changed
    if (evt.x != lastState.x || evt.y != lastState.y || evt.buttons != lastState.buttons) {
        Serial.write((uint8_t *)&evt, sizeof(JoystickEvent));
        lastState = evt;
    }
#else
    delay(100);
#endif
}

