/**
 * @file ui.h
 * @brief UI Framework - Scene manager, app system, and common types
 */

#pragma once

#include "esp_err.h"
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * Constants
 * ============================================================================ */

#define UI_MAX_APPS             16
#define UI_MAX_SCENE_STACK      8
#define UI_ICON_WIDTH           16
#define UI_ICON_HEIGHT          16
#define UI_STATUS_BAR_HEIGHT    10
#define UI_NOTIFY_HEIGHT        12

/* Button bit masks (from joystick) */
#define UI_BTN_PRESS            0x01
#define UI_BTN_DOUBLE           0x02
#define UI_BTN_LONG             0x04
#define UI_BTN_HOME             0x08
#define UI_BTN_BACK             0x10

/* ============================================================================
 * Types
 * ============================================================================ */

/**
 * @brief App definition structure
 */
typedef struct {
    const char *id;                 /**< Unique app identifier */
    const char *name;               /**< Display name */
    const uint8_t *icon;            /**< 16x16 bitmap icon (NULL for default) */
    void (*on_enter)(void);         /**< Called when app becomes active */
    void (*on_exit)(void);          /**< Called when app is deactivated */
    void (*on_input)(int8_t x, int8_t y, uint8_t buttons);  /**< Input handler */
    void (*on_render)(void);        /**< Render handler (called each frame) */
    void (*on_tick)(uint32_t dt_ms); /**< Background tick (even when not focused) */
} ui_app_t;

/**
 * @brief Scene types
 */
typedef enum {
    UI_SCENE_MENU,          /**< Main menu */
    UI_SCENE_APP,           /**< App running */
    UI_SCENE_DIALOG,        /**< Modal dialog overlay */
    UI_SCENE_OSK,           /**< On-screen keyboard overlay */
} ui_scene_type_t;

/**
 * @brief Scene definition
 */
typedef struct {
    ui_scene_type_t type;
    const ui_app_t *app;            /**< App for APP scene, NULL otherwise */
    void *context;                  /**< Scene-specific context */
} ui_scene_t;

/**
 * @brief Notification priority
 */
typedef enum {
    UI_NOTIFY_LOW,
    UI_NOTIFY_NORMAL,
    UI_NOTIFY_HIGH,
} ui_notify_priority_t;

/**
 * @brief Notification structure
 */
typedef struct {
    const char *title;              /**< Short title (max 16 chars) */
    const char *body;               /**< Body text (max 32 chars) */
    ui_notify_priority_t priority;
    uint32_t duration_ms;           /**< 0 = default (3000ms) */
    void (*on_tap)(void);           /**< Optional tap callback */
} ui_notification_t;

/**
 * @brief Dialog button
 */
typedef struct {
    const char *label;
    void (*on_click)(void);
} ui_dialog_btn_t;

/**
 * @brief Dialog configuration
 */
typedef struct {
    const char *title;
    const char *message;
    ui_dialog_btn_t buttons[3];     /**< Up to 3 buttons */
    uint8_t button_count;
    uint8_t default_button;         /**< 0-based index */
} ui_dialog_t;

/**
 * @brief On-screen keyboard callback
 */
typedef void (*ui_osk_callback_t)(const char *text, bool confirmed);

/**
 * @brief On-screen keyboard configuration
 */
typedef struct {
    const char *title;              /**< Prompt text */
    const char *initial_text;       /**< Initial value */
    size_t max_length;              /**< Maximum input length */
    bool password_mode;             /**< Hide characters */
    ui_osk_callback_t callback;     /**< Completion callback */
} ui_osk_config_t;

/**
 * @brief System status for status bar
 */
typedef struct {
    bool ble_connected;
    bool wifi_connected;
    int8_t wifi_rssi;               /**< Signal strength in dBm */
    int8_t battery_percent;         /**< -1 if not available */
    bool music_playing;
    uint8_t unread_notifications;
    uint8_t hour;
    uint8_t minute;
} ui_status_t;

/* ============================================================================
 * Core API
 * ============================================================================ */

/**
 * @brief Initialize the UI framework
 * @return ESP_OK on success
 */
esp_err_t ui_init(void);

/**
 * @brief Register an app with the UI system
 * @param app App definition (must remain valid)
 * @return ESP_OK on success
 */
esp_err_t ui_register_app(const ui_app_t *app);

/**
 * @brief Get registered apps
 * @param apps Output array
 * @param max_apps Array size
 * @return Number of apps returned
 */
size_t ui_get_apps(const ui_app_t **apps, size_t max_apps);

/**
 * @brief Launch an app by ID
 * @param app_id App identifier
 * @return ESP_OK on success
 */
esp_err_t ui_launch_app(const char *app_id);

/**
 * @brief Go back to previous scene (or menu if at root)
 */
void ui_go_back(void);

/**
 * @brief Go directly to main menu
 */
void ui_go_home(void);

/**
 * @brief Process joystick input
 * @param x X-axis (-100 to 100)
 * @param y Y-axis (-100 to 100)
 * @param buttons Button bitmask
 */
void ui_input(int8_t x, int8_t y, uint8_t buttons);

/**
 * @brief Render current frame
 * Call this from your display task at desired FPS
 */
void ui_render(void);

/**
 * @brief Background tick for all apps
 * @param dt_ms Milliseconds since last tick
 */
void ui_tick(uint32_t dt_ms);

/**
 * @brief Update system status
 * @param status New status values
 */
void ui_update_status(const ui_status_t *status);

/**
 * @brief Get current system status
 */
const ui_status_t *ui_get_status(void);

/* ============================================================================
 * Notification API
 * ============================================================================ */

/**
 * @brief Show a notification
 * @param notif Notification to display
 * @return ESP_OK on success
 */
esp_err_t ui_notify(const ui_notification_t *notif);

/**
 * @brief Show a simple text notification
 * @param text Notification text
 */
void ui_notify_simple(const char *text);

/**
 * @brief Dismiss current notification
 */
void ui_notify_dismiss(void);

/* ============================================================================
 * Dialog API
 * ============================================================================ */

/**
 * @brief Show a modal dialog
 * @param dialog Dialog configuration
 * @return ESP_OK on success
 */
esp_err_t ui_show_dialog(const ui_dialog_t *dialog);

/**
 * @brief Close current dialog
 */
void ui_close_dialog(void);

/* ============================================================================
 * On-Screen Keyboard API
 * ============================================================================ */

/**
 * @brief Show on-screen keyboard
 * @param config Keyboard configuration
 * @return ESP_OK on success
 */
esp_err_t ui_show_osk(const ui_osk_config_t *config);

/**
 * @brief Check if OSK is active
 */
bool ui_osk_active(void);

/* ============================================================================
 * Menu Widget API (for use in apps)
 * ============================================================================ */

/**
 * @brief Menu item
 */
typedef struct {
    const char *label;
    const uint8_t *icon;            /**< Optional 8x8 icon */
    void (*on_select)(void);
    void *user_data;
} ui_menu_item_t;

/**
 * @brief Draw a scrollable menu list
 * @param x X position
 * @param y Y position
 * @param w Width
 * @param h Height
 * @param items Menu items array
 * @param count Number of items
 * @param selected Currently selected index
 * @param scroll_offset Scroll position
 */
void ui_draw_menu_list(int x, int y, int w, int h,
                       const ui_menu_item_t *items, size_t count,
                       int selected, int scroll_offset);

/**
 * @brief Handle menu list input
 * @param y Joystick Y axis
 * @param buttons Button state
 * @param items Menu items array
 * @param count Number of items
 * @param selected Pointer to selected index
 * @param scroll_offset Pointer to scroll offset
 * @return true if selection was activated
 */
bool ui_handle_menu_input(int8_t y, uint8_t buttons,
                          const ui_menu_item_t *items, size_t count,
                          int *selected, int *scroll_offset);

#ifdef __cplusplus
}
#endif

