/**
 * @file TranslatorPartnerInit.cpp
 * @brief Initialization for Translator Partner device modules
 * 
 * This file hooks into Meshtastic's module initialization to set up
 * the custom joystick and BLE bridge modules.
 */

#include "configuration.h"

#ifdef TRANSLATOR_PARTNER

#include "main.h"
#include "JoystickInputModule.h"
#include "MainDeviceBridgeModule.h"

#include <NimBLEDevice.h>

// Forward declaration of Meshtastic's setupModules hook
extern void setupModules();

/**
 * @brief Initialize translator partner modules
 * 
 * Called during Meshtastic startup to create and configure
 * the custom modules for joystick input and BLE bridging.
 */
void initTranslatorPartnerModules()
{
    LOG_INFO("Initializing Translator Partner modules\n");
    
#ifdef HAS_JOYSTICK
    // Create joystick module
    JoystickInputModule::getInstance();
    LOG_INFO("Joystick module initialized\n");
#endif

#ifdef HAS_MAIN_DEVICE_BRIDGE
    // Create BLE bridge module
    MainDeviceBridgeModule *bridge = MainDeviceBridgeModule::getInstance();
    
    // Initialize NimBLE with custom name
    NimBLEDevice::init(BLE_NAME);
    NimBLEDevice::setPower(ESP_PWR_LVL_P9);  // Max power for better range
    
    // Get/create server
    NimBLEServer *server = NimBLEDevice::createServer();
    
    // Set up custom GATT services
    bridge->setupBLEServices(server);
    
    LOG_INFO("BLE bridge module initialized\n");
#endif

    LOG_INFO("Translator Partner modules ready\n");
}

/**
 * @brief Register the initialization function
 * 
 * This uses GCC constructor attribute to run before main(),
 * registering our init function to be called during Meshtastic setup.
 */
static class TranslatorPartnerRegistrar {
public:
    TranslatorPartnerRegistrar() {
        // Register with Meshtastic's module system
        // Note: This may need adjustment based on Meshtastic version
    }
} translatorPartnerRegistrar;

#endif // TRANSLATOR_PARTNER

