/**
 * @file JoystickInputModule.h
 * @brief Joystick input handling for partner device
 * 
 * Reads analog joystick position and button states, then publishes
 * JoystickEvent packets via BLE to the main translator device.
 */

#pragma once

#include "SinglePortModule.h"
#include "configuration.h"
#include <Arduino.h>

#ifdef HAS_JOYSTICK

/**
 * @brief Joystick event structure (matches main device protocol)
 * 
 * This 8-byte structure is sent via BLE notification to the main device.
 * It must be packed to ensure correct byte alignment across devices.
 */
struct __attribute__((packed)) JoystickEvent {
    int8_t x;           ///< X-axis: -100 (left) to +100 (right)
    int8_t y;           ///< Y-axis: -100 (down) to +100 (up)
    uint8_t buttons;    ///< Button bitmask: bit0=press, bit1=double, bit2=long
    uint8_t layer;      ///< Context layer: 0=global, 1=text, 2=csv, 3=mod, 4=mesh_compose, 5=mesh_inbox
    uint32_t seq;       ///< Sequence number for ACK correlation
};

/**
 * @brief Button state bits
 */
enum ButtonBits {
    BTN_PRESS       = 0x01,     ///< Single press detected
    BTN_DOUBLE      = 0x02,     ///< Double press detected
    BTN_LONG        = 0x04,     ///< Long press detected (700ms+)
    BTN_HOME        = 0x08,     ///< Home button pressed
    BTN_BACK        = 0x10      ///< Back button pressed
};

/**
 * @brief Context layer codes
 */
enum JoystickLayer {
    LAYER_GLOBAL        = 0,
    LAYER_TEXT_EDITOR   = 1,
    LAYER_CSV_EDITOR    = 2,
    LAYER_MODIFIER      = 3,
    LAYER_MESH_COMPOSE  = 4,
    LAYER_MESH_INBOX    = 5
};

/**
 * @brief Joystick input module for Meshtastic
 * 
 * This module integrates with Meshtastic's module system to provide
 * periodic joystick polling and BLE event publishing.
 */
class JoystickInputModule : public SinglePortModule {
public:
    /**
     * @brief Construct the joystick module
     */
    JoystickInputModule();

    /**
     * @brief Get the singleton instance
     */
    static JoystickInputModule *getInstance();

    /**
     * @brief Get current joystick state
     * @return Current JoystickEvent with x, y, buttons
     */
    JoystickEvent getCurrentState() const;

    /**
     * @brief Check if joystick has moved significantly since last read
     * @param threshold Movement threshold (0-100)
     * @return true if position changed more than threshold
     */
    bool hasMovement(int threshold = 5) const;

    /**
     * @brief Set the current context layer
     * @param layer Layer code (0-5)
     */
    void setLayer(uint8_t layer);

    /**
     * @brief Get the current context layer
     */
    uint8_t getLayer() const { return currentLayer; }

protected:
    /**
     * @brief Module tick function called by Meshtastic scheduler
     * @return Milliseconds until next call (10ms for 100Hz)
     */
    virtual int32_t runOnce() override;

private:
    /**
     * @brief Initialize ADC for joystick axes
     */
    void initADC();

    /**
     * @brief Read and normalize a joystick axis
     * @param pin GPIO pin number
     * @param invert Whether to invert the axis
     * @return Normalized value -100 to +100
     */
    int16_t readAxis(uint8_t pin, bool invert);

    /**
     * @brief Process button state changes and detect gestures
     */
    void processButtons();

    /**
     * @brief Check if state has changed enough to send an update
     * @return true if should send BLE notification
     */
    bool shouldSendUpdate();

    /**
     * @brief Send joystick event to main device via BLE
     */
    void sendJoystickEvent();

    // State tracking
    JoystickEvent currentState;
    JoystickEvent lastSentState;
    uint32_t seqCounter;
    uint8_t currentLayer;

    // Button gesture detection
    uint32_t lastButtonPressTime;
    uint32_t buttonDownTime;
    uint8_t pressCount;
    bool buttonWasPressed;
    bool longPressTriggered;

    // ADC state
    bool adcInitialized;

    // Singleton instance
    static JoystickInputModule *instance;
};

// Global pointer for other modules to access
extern JoystickInputModule *joystickInputModule;

/**
 * @brief Global function to send joystick event (called by bridge module)
 * @param evt Event to send
 */
void sendJoystickToMainDevice(const JoystickEvent &evt);

#endif // HAS_JOYSTICK

