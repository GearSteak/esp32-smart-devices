/**
 * @file app_settings.c
 * @brief Settings App Implementation
 */

#include "app_settings.h"
#include "ui.h"
#include "display.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "nvs_flash.h"
#include "nvs.h"
#include <string.h>

static const char *TAG = "settings";

/* ============================================================================
 * Settings State
 * ============================================================================ */

typedef struct {
    uint8_t brightness;
    uint8_t volume;
    bool notification_sounds;
    bool display_flip;
    uint8_t screen_timeout;  /* minutes, 0 = never */
} settings_data_t;

static settings_data_t s_settings = {
    .brightness = 80,
    .volume = 50,
    .notification_sounds = true,
    .display_flip = false,
    .screen_timeout = 5,
};

/* Menu navigation state */
typedef enum {
    MENU_MAIN,
    MENU_WIFI,
    MENU_BLUETOOTH,
    MENU_DISPLAY,
    MENU_AUDIO,
    MENU_STORAGE,
    MENU_DATETIME,
    MENU_ABOUT,
} menu_level_t;

static menu_level_t s_menu_level = MENU_MAIN;
static int s_selected = 0;
static int s_scroll = 0;

/* WiFi scan state */
static bool s_wifi_scanning = false;

/* ============================================================================
 * Menu Definitions
 * ============================================================================ */

static void go_to_wifi(void);
static void go_to_bluetooth(void);
static void go_to_display(void);
static void go_to_audio(void);
static void go_to_storage(void);
static void go_to_datetime(void);
static void go_to_about(void);
static void go_back(void);

/* Main menu items */
static const ui_menu_item_t main_menu[] = {
    { .label = "WiFi",      .on_select = go_to_wifi },
    { .label = "Bluetooth", .on_select = go_to_bluetooth },
    { .label = "Display",   .on_select = go_to_display },
    { .label = "Audio",     .on_select = go_to_audio },
    { .label = "Storage",   .on_select = go_to_storage },
    { .label = "Date/Time", .on_select = go_to_datetime },
    { .label = "About",     .on_select = go_to_about },
};
#define MAIN_MENU_COUNT (sizeof(main_menu) / sizeof(main_menu[0]))

/* Submenu navigation */
static void go_to_wifi(void) { s_menu_level = MENU_WIFI; s_selected = 0; s_scroll = 0; }
static void go_to_bluetooth(void) { s_menu_level = MENU_BLUETOOTH; s_selected = 0; s_scroll = 0; }
static void go_to_display(void) { s_menu_level = MENU_DISPLAY; s_selected = 0; s_scroll = 0; }
static void go_to_audio(void) { s_menu_level = MENU_AUDIO; s_selected = 0; s_scroll = 0; }
static void go_to_storage(void) { s_menu_level = MENU_STORAGE; s_selected = 0; s_scroll = 0; }
static void go_to_datetime(void) { s_menu_level = MENU_DATETIME; s_selected = 0; s_scroll = 0; }
static void go_to_about(void) { s_menu_level = MENU_ABOUT; s_selected = 0; s_scroll = 0; }
static void go_back(void) { s_menu_level = MENU_MAIN; s_selected = 0; s_scroll = 0; }

/* ============================================================================
 * Settings Persistence
 * ============================================================================ */

void settings_save(void)
{
    nvs_handle_t nvs;
    if (nvs_open("settings", NVS_READWRITE, &nvs) == ESP_OK) {
        nvs_set_u8(nvs, "brightness", s_settings.brightness);
        nvs_set_u8(nvs, "volume", s_settings.volume);
        nvs_set_u8(nvs, "notif_snd", s_settings.notification_sounds ? 1 : 0);
        nvs_set_u8(nvs, "flip", s_settings.display_flip ? 1 : 0);
        nvs_set_u8(nvs, "timeout", s_settings.screen_timeout);
        nvs_commit(nvs);
        nvs_close(nvs);
        ESP_LOGI(TAG, "Settings saved");
    }
}

void settings_load(void)
{
    nvs_handle_t nvs;
    if (nvs_open("settings", NVS_READONLY, &nvs) == ESP_OK) {
        nvs_get_u8(nvs, "brightness", &s_settings.brightness);
        nvs_get_u8(nvs, "volume", &s_settings.volume);
        uint8_t tmp;
        if (nvs_get_u8(nvs, "notif_snd", &tmp) == ESP_OK) s_settings.notification_sounds = tmp;
        if (nvs_get_u8(nvs, "flip", &tmp) == ESP_OK) s_settings.display_flip = tmp;
        nvs_get_u8(nvs, "timeout", &s_settings.screen_timeout);
        nvs_close(nvs);
        ESP_LOGI(TAG, "Settings loaded");
    }
}

uint8_t settings_get_brightness(void) { return s_settings.brightness; }
void settings_set_brightness(uint8_t b) { s_settings.brightness = b; display_set_brightness(b * 255 / 100); }
uint8_t settings_get_volume(void) { return s_settings.volume; }
void settings_set_volume(uint8_t v) { s_settings.volume = v; }
bool settings_get_notification_sounds(void) { return s_settings.notification_sounds; }

/* ============================================================================
 * App Callbacks
 * ============================================================================ */

static void on_enter(void)
{
    ESP_LOGI(TAG, "Settings app entered");
    s_menu_level = MENU_MAIN;
    s_selected = 0;
    s_scroll = 0;
    settings_load();
}

static void on_exit(void)
{
    ESP_LOGI(TAG, "Settings app exited");
    settings_save();
}

static void on_input(int8_t x, int8_t y, uint8_t buttons)
{
    /* Back button */
    if (buttons & UI_BTN_BACK) {
        if (s_menu_level == MENU_MAIN) {
            ui_go_back();
        } else {
            go_back();
        }
        return;
    }
    
    /* Handle based on current menu */
    switch (s_menu_level) {
    case MENU_MAIN:
        ui_handle_menu_input(y, buttons, main_menu, MAIN_MENU_COUNT, &s_selected, &s_scroll);
        break;
        
    case MENU_DISPLAY:
        /* Simple brightness adjustment */
        if (x > 30 && s_settings.brightness < 100) {
            s_settings.brightness += 5;
            display_set_brightness(s_settings.brightness * 255 / 100);
        } else if (x < -30 && s_settings.brightness > 0) {
            s_settings.brightness -= 5;
            display_set_brightness(s_settings.brightness * 255 / 100);
        }
        break;
        
    case MENU_AUDIO:
        /* Volume adjustment */
        if (x > 30 && s_settings.volume < 100) {
            s_settings.volume += 5;
        } else if (x < -30 && s_settings.volume > 0) {
            s_settings.volume -= 5;
        }
        if (buttons & UI_BTN_PRESS) {
            s_settings.notification_sounds = !s_settings.notification_sounds;
        }
        break;
        
    default:
        /* Other menus - just navigate */
        break;
    }
}

static void on_render(void)
{
    int y = UI_STATUS_BAR_HEIGHT + 2;
    
    /* Title */
    const char *title = "Settings";
    switch (s_menu_level) {
        case MENU_WIFI: title = "WiFi"; break;
        case MENU_BLUETOOTH: title = "Bluetooth"; break;
        case MENU_DISPLAY: title = "Display"; break;
        case MENU_AUDIO: title = "Audio"; break;
        case MENU_STORAGE: title = "Storage"; break;
        case MENU_DATETIME: title = "Date/Time"; break;
        case MENU_ABOUT: title = "About"; break;
        default: break;
    }
    display_draw_string(2, y, title, COLOR_WHITE, 1);
    display_draw_hline(0, y + 9, DISPLAY_WIDTH, COLOR_WHITE);
    y += 12;
    
    switch (s_menu_level) {
    case MENU_MAIN:
        ui_draw_menu_list(0, y, DISPLAY_WIDTH, DISPLAY_HEIGHT - y,
                          main_menu, MAIN_MENU_COUNT, s_selected, s_scroll);
        break;
        
    case MENU_WIFI:
        if (s_wifi_scanning) {
            display_draw_string(2, y, "Scanning...", COLOR_WHITE, 1);
        } else {
            display_draw_string(2, y, "Not connected", COLOR_WHITE, 1);
            display_draw_string(2, y + 12, "Press to scan", COLOR_WHITE, 1);
        }
        break;
        
    case MENU_BLUETOOTH:
        display_draw_string(2, y, "Partner: ", COLOR_WHITE, 1);
        display_draw_string(60, y, control_link_is_connected() ? "OK" : "--", COLOR_WHITE, 1);
        break;
        
    case MENU_DISPLAY:
        display_printf(2, y, COLOR_WHITE, 1, "Brightness: %d%%", s_settings.brightness);
        display_draw_progress(2, y + 12, 100, 8, s_settings.brightness);
        display_draw_string(2, y + 24, "<-/-> to adjust", COLOR_WHITE, 1);
        break;
        
    case MENU_AUDIO:
        display_printf(2, y, COLOR_WHITE, 1, "Volume: %d%%", s_settings.volume);
        display_draw_progress(2, y + 12, 100, 8, s_settings.volume);
        display_printf(2, y + 24, COLOR_WHITE, 1, "Sounds: %s", 
                      s_settings.notification_sounds ? "ON" : "OFF");
        break;
        
    case MENU_STORAGE:
        display_draw_string(2, y, "SD Card: ", COLOR_WHITE, 1);
        display_draw_string(60, y, "Not mounted", COLOR_WHITE, 1);
        break;
        
    case MENU_DATETIME:
        {
            const ui_status_t *st = ui_get_status();
            display_printf(2, y, COLOR_WHITE, 1, "Time: %02d:%02d", st->hour, st->minute);
            display_draw_string(2, y + 12, "Set via NTP", COLOR_WHITE, 1);
        }
        break;
        
    case MENU_ABOUT:
        display_draw_string(2, y, "Smart Device", COLOR_WHITE, 1);
        display_draw_string(2, y + 10, "Version: 0.1.0", COLOR_WHITE, 1);
        display_draw_string(2, y + 20, "ESP32-WROVER", COLOR_WHITE, 1);
        break;
    }
}

static void on_tick(uint32_t dt_ms)
{
    (void)dt_ms;
    /* No background tasks for settings */
}

/* ============================================================================
 * App Definition
 * ============================================================================ */

#include "sprites.h"

const ui_app_t app_settings = {
    .id = "settings",
    .name = "Settings",
    .icon = ICON_SETTINGS,
    .on_enter = on_enter,
    .on_exit = on_exit,
    .on_input = on_input,
    .on_render = on_render,
    .on_tick = on_tick,
};

