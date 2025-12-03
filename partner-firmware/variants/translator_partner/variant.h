/**
 * @file variant.h
 * @brief Hardware variant configuration for Translator Partner Device
 * 
 * ESP32 WROOM-32 DevKit + SX1262 LoRa + Joystick
 * 
 * This variant extends Meshtastic with custom joystick input and
 * BLE bridge functionality for the main translator device.
 */

#pragma once

// ============================================================================
// Device Identity
// ============================================================================

#define MESHTASTIC_NAME         "translator-partner"
#define HW_VENDOR               meshtastic_HardwareModel_PRIVATE_HW

// ============================================================================
// LoRa Radio Configuration (SX1262 via VSPI)
// ============================================================================

#define USE_SX1262

// SPI pins (VSPI)
#define LORA_SCK                18
#define LORA_MISO               19
#define LORA_MOSI               23
#define LORA_CS                 5

// SX1262 control pins
#define SX126X_CS               LORA_CS
#define SX126X_DIO1             26      // Interrupt
#define SX126X_BUSY             27
#define SX126X_RESET            14

// Radio power settings
#define SX126X_MAX_POWER        22      // dBm

// Uncomment if your module has TCXO
// #define SX126X_DIO3_TCXO_VOLTAGE 1.8

// DIO2 controls RF switch on some modules
// #define SX126X_DIO2_AS_RF_SWITCH

// ============================================================================
// Joystick Configuration (ADC1 - works with WiFi/BLE)
// ============================================================================

#define HAS_JOYSTICK            1

// Analog inputs (ADC1 channels - safe to use with WiFi active)
#define JOYSTICK_X_PIN          34      // ADC1_CH6, input only
#define JOYSTICK_Y_PIN          35      // ADC1_CH7, input only

// Digital inputs
#define JOYSTICK_BTN_PIN        32      // Joystick push button

// Calibration values (12-bit ADC, 0-4095)
#define JOYSTICK_CENTER         2048
#define JOYSTICK_DEADZONE       164     // ~8% of center value
#define JOYSTICK_SAMPLE_RATE_HZ 100

// Axis inversion (adjust based on physical orientation)
#define JOYSTICK_INVERT_X       false
#define JOYSTICK_INVERT_Y       true

// ============================================================================
// Button Configuration
// ============================================================================

#define BUTTON_HOME_PIN         33      // Home/Menu button
#define BUTTON_BACK_PIN         25      // Back/Cancel button

// Button timing (ms)
#define BUTTON_DEBOUNCE_MS      50
#define BUTTON_LONG_PRESS_MS    700
#define BUTTON_DOUBLE_PRESS_MS  300

// ============================================================================
// Battery Monitoring (Optional)
// ============================================================================

// Voltage divider: Battery+ -> 100kΩ -> GPIO36 -> 100kΩ -> GND
#define BATTERY_PIN             36      // VP, ADC1_CH0
#define ADC_MULTIPLIER          2.0     // For 1:1 voltage divider
#define BATTERY_SENSE_SAMPLES   10      // Oversample for accuracy

// ============================================================================
// Status LED
// ============================================================================

#define LED_PIN                 2       // Onboard LED (most ESP32 devkits)
#define LED_INVERTED            false   // true if LED is active LOW

// ============================================================================
// Display Configuration
// ============================================================================

// Partner device has no display - all UI is on main device
#define HAS_SCREEN              0

// ============================================================================
// GPS Configuration
// ============================================================================

// No GPS on base partner device (can be added later)
#define HAS_GPS                 0

// ============================================================================
// BLE Configuration
// ============================================================================

#define HAS_MAIN_DEVICE_BRIDGE  1
#define BLE_NAME                "TransPartner"

// Custom GATT service UUIDs (must match main device)
#define MESH_RELAY_SERVICE_UUID         "4f9a0030-8c3f-4a0e-89a7-6d277cf9a000"
#define MESH_INBOX_CHAR_UUID            "4f9a0031-8c3f-4a0e-89a7-6d277cf9a000"
#define MESH_SEND_CHAR_UUID             "4f9a0032-8c3f-4a0e-89a7-6d277cf9a000"
#define MESH_STATUS_CHAR_UUID           "4f9a0033-8c3f-4a0e-89a7-6d277cf9a000"
#define MESH_NODE_LIST_CHAR_UUID        "4f9a0034-8c3f-4a0e-89a7-6d277cf9a000"

#define REMOTE_INPUT_SERVICE_UUID       "4f9a0001-8c3f-4a0e-89a7-6d277cf9a000"
#define JOYSTICK_EVENT_CHAR_UUID        "4f9a0002-8c3f-4a0e-89a7-6d277cf9a000"
#define KEYPAD_EVENT_CHAR_UUID          "4f9a0003-8c3f-4a0e-89a7-6d277cf9a000"

#define COMMAND_SYNC_SERVICE_UUID       "4f9a0020-8c3f-4a0e-89a7-6d277cf9a000"
#define COMMAND_CHAR_UUID               "4f9a0021-8c3f-4a0e-89a7-6d277cf9a000"
#define ACK_CHAR_UUID                   "4f9a0022-8c3f-4a0e-89a7-6d277cf9a000"
#define HEARTBEAT_CHAR_UUID             "4f9a0023-8c3f-4a0e-89a7-6d277cf9a000"

// ============================================================================
// Power Management
// ============================================================================

// Deep sleep not recommended for partner device (needs to be responsive)
#define SLEEP_TIME_MS           0       // 0 = no automatic sleep

// Light sleep between polling cycles
#define USE_LIGHT_SLEEP         false

