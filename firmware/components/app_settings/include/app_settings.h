/**
 * @file app_settings.h
 * @brief Settings App
 */

#pragma once

#include "ui.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Settings app definition
 */
extern const ui_app_t app_settings;

/**
 * @brief Get current display brightness (0-100)
 */
uint8_t settings_get_brightness(void);

/**
 * @brief Set display brightness (0-100)
 */
void settings_set_brightness(uint8_t brightness);

/**
 * @brief Get volume (0-100)
 */
uint8_t settings_get_volume(void);

/**
 * @brief Set volume (0-100)
 */
void settings_set_volume(uint8_t volume);

/**
 * @brief Check if notification sounds are enabled
 */
bool settings_get_notification_sounds(void);

/**
 * @brief Save all settings to NVS
 */
void settings_save(void);

/**
 * @brief Load settings from NVS
 */
void settings_load(void);

#ifdef __cplusplus
}
#endif

