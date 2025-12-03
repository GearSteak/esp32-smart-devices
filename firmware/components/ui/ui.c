/**
 * @file ui.c
 * @brief UI Framework - Core implementation
 */

#include "ui.h"
#include "display.h"
#include "esp_log.h"
#include "esp_timer.h"
#include <string.h>

static const char *TAG = "ui";

/* ============================================================================
 * Internal State
 * ============================================================================ */

/* Registered apps */
static const ui_app_t *s_apps[UI_MAX_APPS];
static size_t s_app_count = 0;

/* Scene stack */
static ui_scene_t s_scene_stack[UI_MAX_SCENE_STACK];
static int s_scene_top = -1;

/* System status */
static ui_status_t s_status = {0};

/* Notification state */
typedef struct {
    bool active;
    ui_notification_t notif;
    uint32_t show_time;
    int16_t y_offset;           /* For slide animation */
} notify_state_t;
static notify_state_t s_notify = {0};

/* Dialog state */
typedef struct {
    bool active;
    ui_dialog_t dialog;
    int selected;
} dialog_state_t;
static dialog_state_t s_dialog = {0};

/* OSK state */
typedef struct {
    bool active;
    ui_osk_config_t config;
    char buffer[128];
    size_t cursor;
    int8_t key_row;
    int8_t key_col;
} osk_state_t;
static osk_state_t s_osk = {0};

/* Main menu state */
typedef struct {
    int selected;
    int scroll_offset;
} menu_state_t;
static menu_state_t s_menu = {0};

/* Input debouncing */
static uint32_t s_last_input_time = 0;
static uint8_t s_last_buttons = 0;

/* ============================================================================
 * Forward Declarations
 * ============================================================================ */

static void render_status_bar(void);
static void render_notification(void);
static void render_main_menu(void);
static void render_dialog(void);
static void render_osk(void);
static void handle_menu_input(int8_t x, int8_t y, uint8_t buttons);
static void handle_dialog_input(int8_t x, int8_t y, uint8_t buttons);
static void handle_osk_input(int8_t x, int8_t y, uint8_t buttons);

/* ============================================================================
 * Core API Implementation
 * ============================================================================ */

esp_err_t ui_init(void)
{
    ESP_LOGI(TAG, "Initializing UI framework");
    
    s_app_count = 0;
    s_scene_top = -1;
    memset(&s_status, 0, sizeof(s_status));
    memset(&s_notify, 0, sizeof(s_notify));
    memset(&s_dialog, 0, sizeof(s_dialog));
    memset(&s_osk, 0, sizeof(s_osk));
    memset(&s_menu, 0, sizeof(s_menu));
    
    /* Start at main menu */
    s_scene_stack[0].type = UI_SCENE_MENU;
    s_scene_stack[0].app = NULL;
    s_scene_stack[0].context = NULL;
    s_scene_top = 0;
    
    ESP_LOGI(TAG, "UI framework initialized");
    return ESP_OK;
}

esp_err_t ui_register_app(const ui_app_t *app)
{
    if (!app || !app->id || !app->name) {
        return ESP_ERR_INVALID_ARG;
    }
    
    if (s_app_count >= UI_MAX_APPS) {
        ESP_LOGE(TAG, "Too many apps registered");
        return ESP_ERR_NO_MEM;
    }
    
    s_apps[s_app_count++] = app;
    ESP_LOGI(TAG, "Registered app: %s", app->name);
    
    return ESP_OK;
}

size_t ui_get_apps(const ui_app_t **apps, size_t max_apps)
{
    size_t count = (s_app_count < max_apps) ? s_app_count : max_apps;
    for (size_t i = 0; i < count; i++) {
        apps[i] = s_apps[i];
    }
    return count;
}

esp_err_t ui_launch_app(const char *app_id)
{
    const ui_app_t *app = NULL;
    
    for (size_t i = 0; i < s_app_count; i++) {
        if (strcmp(s_apps[i]->id, app_id) == 0) {
            app = s_apps[i];
            break;
        }
    }
    
    if (!app) {
        ESP_LOGE(TAG, "App not found: %s", app_id);
        return ESP_ERR_NOT_FOUND;
    }
    
    /* Push app scene */
    if (s_scene_top >= UI_MAX_SCENE_STACK - 1) {
        ESP_LOGE(TAG, "Scene stack full");
        return ESP_ERR_NO_MEM;
    }
    
    s_scene_top++;
    s_scene_stack[s_scene_top].type = UI_SCENE_APP;
    s_scene_stack[s_scene_top].app = app;
    s_scene_stack[s_scene_top].context = NULL;
    
    if (app->on_enter) {
        app->on_enter();
    }
    
    ESP_LOGI(TAG, "Launched app: %s", app->name);
    return ESP_OK;
}

void ui_go_back(void)
{
    if (s_scene_top <= 0) {
        /* Already at menu */
        return;
    }
    
    ui_scene_t *current = &s_scene_stack[s_scene_top];
    
    if (current->type == UI_SCENE_APP && current->app && current->app->on_exit) {
        current->app->on_exit();
    }
    
    s_scene_top--;
    ESP_LOGD(TAG, "Popped scene, now at level %d", s_scene_top);
}

void ui_go_home(void)
{
    while (s_scene_top > 0) {
        ui_go_back();
    }
}

void ui_input(int8_t x, int8_t y, uint8_t buttons)
{
    uint32_t now = esp_timer_get_time() / 1000;
    
    /* Detect button edges */
    uint8_t pressed = buttons & ~s_last_buttons;
    s_last_buttons = buttons;
    s_last_input_time = now;
    
    /* Home button always goes home */
    if (pressed & UI_BTN_HOME) {
        if (s_osk.active) {
            /* Cancel OSK */
            s_osk.active = false;
            if (s_osk.config.callback) {
                s_osk.config.callback(NULL, false);
            }
        } else if (s_dialog.active) {
            ui_close_dialog();
        } else {
            ui_go_home();
        }
        return;
    }
    
    /* Back button */
    if (pressed & UI_BTN_BACK) {
        if (s_osk.active) {
            s_osk.active = false;
            if (s_osk.config.callback) {
                s_osk.config.callback(NULL, false);
            }
        } else if (s_dialog.active) {
            ui_close_dialog();
        } else {
            ui_go_back();
        }
        return;
    }
    
    /* Dismiss notification on any press */
    if (s_notify.active && (pressed & UI_BTN_PRESS)) {
        if (s_notify.notif.on_tap) {
            s_notify.notif.on_tap();
        }
        ui_notify_dismiss();
        return;
    }
    
    /* Route input to current layer */
    if (s_osk.active) {
        handle_osk_input(x, y, buttons);
    } else if (s_dialog.active) {
        handle_dialog_input(x, y, buttons);
    } else if (s_scene_top >= 0) {
        ui_scene_t *current = &s_scene_stack[s_scene_top];
        
        if (current->type == UI_SCENE_MENU) {
            handle_menu_input(x, y, buttons);
        } else if (current->type == UI_SCENE_APP && current->app && current->app->on_input) {
            current->app->on_input(x, y, buttons);
        }
    }
}

void ui_render(void)
{
    display_clear();
    
    /* Render current scene */
    if (s_scene_top >= 0) {
        ui_scene_t *current = &s_scene_stack[s_scene_top];
        
        /* Status bar (always visible, reserve top 10px) */
        render_status_bar();
        
        if (current->type == UI_SCENE_MENU) {
            render_main_menu();
        } else if (current->type == UI_SCENE_APP && current->app && current->app->on_render) {
            current->app->on_render();
        }
    }
    
    /* Overlay layers */
    if (s_dialog.active) {
        render_dialog();
    }
    
    if (s_osk.active) {
        render_osk();
    }
    
    if (s_notify.active) {
        render_notification();
    }
    
    display_refresh();
}

void ui_tick(uint32_t dt_ms)
{
    /* Update notification animation */
    if (s_notify.active) {
        uint32_t now = esp_timer_get_time() / 1000;
        uint32_t elapsed = now - s_notify.show_time;
        
        /* Slide in animation (first 200ms) */
        if (elapsed < 200) {
            s_notify.y_offset = -UI_NOTIFY_HEIGHT + (UI_NOTIFY_HEIGHT * elapsed / 200);
        } else {
            s_notify.y_offset = 0;
        }
        
        /* Auto-dismiss */
        uint32_t duration = s_notify.notif.duration_ms ? s_notify.notif.duration_ms : 3000;
        if (elapsed > duration) {
            ui_notify_dismiss();
        }
    }
    
    /* Tick all apps (for background tasks) */
    for (size_t i = 0; i < s_app_count; i++) {
        if (s_apps[i]->on_tick) {
            s_apps[i]->on_tick(dt_ms);
        }
    }
}

void ui_update_status(const ui_status_t *status)
{
    if (status) {
        memcpy(&s_status, status, sizeof(s_status));
    }
}

const ui_status_t *ui_get_status(void)
{
    return &s_status;
}

/* ============================================================================
 * Notification Implementation
 * ============================================================================ */

esp_err_t ui_notify(const ui_notification_t *notif)
{
    if (!notif || !notif->title) {
        return ESP_ERR_INVALID_ARG;
    }
    
    memcpy(&s_notify.notif, notif, sizeof(ui_notification_t));
    s_notify.active = true;
    s_notify.show_time = esp_timer_get_time() / 1000;
    s_notify.y_offset = -UI_NOTIFY_HEIGHT;
    
    if (s_status.unread_notifications < 255) {
        s_status.unread_notifications++;
    }
    
    ESP_LOGI(TAG, "Notification: %s", notif->title);
    return ESP_OK;
}

void ui_notify_simple(const char *text)
{
    ui_notification_t notif = {
        .title = text,
        .body = NULL,
        .priority = UI_NOTIFY_NORMAL,
        .duration_ms = 0,
        .on_tap = NULL,
    };
    ui_notify(&notif);
}

void ui_notify_dismiss(void)
{
    s_notify.active = false;
}

/* ============================================================================
 * Dialog Implementation
 * ============================================================================ */

esp_err_t ui_show_dialog(const ui_dialog_t *dialog)
{
    if (!dialog || dialog->button_count == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    
    memcpy(&s_dialog.dialog, dialog, sizeof(ui_dialog_t));
    s_dialog.active = true;
    s_dialog.selected = dialog->default_button;
    
    return ESP_OK;
}

void ui_close_dialog(void)
{
    s_dialog.active = false;
}

/* ============================================================================
 * OSK Implementation
 * ============================================================================ */

esp_err_t ui_show_osk(const ui_osk_config_t *config)
{
    if (!config || !config->callback) {
        return ESP_ERR_INVALID_ARG;
    }
    
    memcpy(&s_osk.config, config, sizeof(ui_osk_config_t));
    s_osk.active = true;
    s_osk.cursor = 0;
    s_osk.key_row = 1;
    s_osk.key_col = 4;
    
    if (config->initial_text) {
        strncpy(s_osk.buffer, config->initial_text, sizeof(s_osk.buffer) - 1);
        s_osk.cursor = strlen(s_osk.buffer);
    } else {
        s_osk.buffer[0] = '\0';
    }
    
    return ESP_OK;
}

bool ui_osk_active(void)
{
    return s_osk.active;
}

/* ============================================================================
 * Rendering Functions
 * ============================================================================ */

static void render_status_bar(void)
{
    /* Background */
    display_fill_rect(0, 0, DISPLAY_WIDTH, UI_STATUS_BAR_HEIGHT, COLOR_BLACK);
    
    /* Clock (right side) */
    display_printf(DISPLAY_WIDTH - 30, 1, COLOR_WHITE, 1, "%02d:%02d", 
                   s_status.hour, s_status.minute);
    
    /* BLE indicator (left) */
    int x = 2;
    if (s_status.ble_connected) {
        display_draw_string(x, 1, "B", COLOR_WHITE, 1);
    } else {
        display_draw_string(x, 1, ".", COLOR_WHITE, 1);
    }
    x += 8;
    
    /* WiFi indicator */
    if (s_status.wifi_connected) {
        display_draw_string(x, 1, "W", COLOR_WHITE, 1);
    }
    x += 8;
    
    /* Music indicator */
    if (s_status.music_playing) {
        display_draw_string(x, 1, ">", COLOR_WHITE, 1);
    }
    x += 8;
    
    /* Notification count */
    if (s_status.unread_notifications > 0) {
        display_printf(x, 1, COLOR_WHITE, 1, "[%d]", s_status.unread_notifications);
    }
    
    /* Separator line */
    display_draw_hline(0, UI_STATUS_BAR_HEIGHT - 1, DISPLAY_WIDTH, COLOR_WHITE);
}

static void render_notification(void)
{
    if (!s_notify.active) return;
    
    int y = s_notify.y_offset;
    
    /* Background bar */
    display_fill_rect(0, y, DISPLAY_WIDTH, UI_NOTIFY_HEIGHT, COLOR_WHITE);
    
    /* Title text (inverted) */
    if (s_notify.notif.title) {
        display_draw_string(2, y + 2, s_notify.notif.title, COLOR_BLACK, 1);
    }
}

static void render_main_menu(void)
{
    int start_y = UI_STATUS_BAR_HEIGHT + 2;
    
    if (s_app_count == 0) {
        display_draw_string(10, 30, "No apps", COLOR_WHITE, 1);
        return;
    }
    
    /* Grid layout: 4 columns, 2 rows */
    int cols = 4;
    int cell_w = DISPLAY_WIDTH / cols;
    int cell_h = (DISPLAY_HEIGHT - start_y) / 2;
    
    for (size_t i = 0; i < s_app_count && i < 8; i++) {
        int col = i % cols;
        int row = i / cols;
        int x = col * cell_w;
        int y = start_y + row * cell_h;
        
        /* Selection highlight */
        if ((int)i == s_menu.selected) {
            display_draw_rect(x, y, cell_w, cell_h, COLOR_WHITE);
        }
        
        /* Icon placeholder (centered in cell) */
        int icon_x = x + (cell_w - 16) / 2;
        int icon_y = y + 2;
        
        if (s_apps[i]->icon) {
            display_draw_bitmap(icon_x, icon_y, s_apps[i]->icon, 16, 16, COLOR_WHITE);
        } else {
            /* Default icon (simple box) */
            display_draw_rect(icon_x, icon_y, 16, 16, COLOR_WHITE);
        }
        
        /* App name (centered below icon, truncated) */
        const char *name = s_apps[i]->name;
        int name_len = strlen(name);
        if (name_len > 5) name_len = 5;
        int name_x = x + (cell_w - name_len * 6) / 2;
        
        char short_name[6];
        strncpy(short_name, name, 5);
        short_name[5] = '\0';
        display_draw_string(name_x, icon_y + 18, short_name, COLOR_WHITE, 1);
    }
}

static void render_dialog(void)
{
    if (!s_dialog.active) return;
    
    /* Dialog box dimensions */
    int w = 100;
    int h = 40;
    int x = (DISPLAY_WIDTH - w) / 2;
    int y = (DISPLAY_HEIGHT - h) / 2;
    
    /* Background with border */
    display_fill_rect(x, y, w, h, COLOR_BLACK);
    display_draw_rect(x, y, w, h, COLOR_WHITE);
    
    /* Title */
    if (s_dialog.dialog.title) {
        display_draw_string(x + 4, y + 2, s_dialog.dialog.title, COLOR_WHITE, 1);
    }
    
    /* Buttons */
    int btn_y = y + h - 12;
    int btn_w = w / s_dialog.dialog.button_count;
    
    for (int i = 0; i < s_dialog.dialog.button_count; i++) {
        int btn_x = x + i * btn_w;
        
        if (i == s_dialog.selected) {
            display_fill_rect(btn_x + 2, btn_y, btn_w - 4, 10, COLOR_WHITE);
            display_draw_string(btn_x + 4, btn_y + 1, s_dialog.dialog.buttons[i].label, COLOR_BLACK, 1);
        } else {
            display_draw_string(btn_x + 4, btn_y + 1, s_dialog.dialog.buttons[i].label, COLOR_WHITE, 1);
        }
    }
}

static void render_osk(void)
{
    if (!s_osk.active) return;
    
    /* OSK takes bottom half of screen */
    int osk_y = DISPLAY_HEIGHT / 2;
    int osk_h = DISPLAY_HEIGHT - osk_y;
    
    /* Background */
    display_fill_rect(0, osk_y, DISPLAY_WIDTH, osk_h, COLOR_BLACK);
    display_draw_hline(0, osk_y, DISPLAY_WIDTH, COLOR_WHITE);
    
    /* Text input field at top of OSK area */
    display_draw_rect(2, osk_y + 2, DISPLAY_WIDTH - 4, 10, COLOR_WHITE);
    
    /* Show buffer content */
    char display_buf[20];
    if (s_osk.config.password_mode) {
        memset(display_buf, '*', sizeof(display_buf) - 1);
        display_buf[s_osk.cursor < 18 ? s_osk.cursor : 18] = '\0';
    } else {
        size_t start = 0;
        if (s_osk.cursor > 17) {
            start = s_osk.cursor - 17;
        }
        strncpy(display_buf, s_osk.buffer + start, 18);
        display_buf[18] = '\0';
    }
    display_draw_string(4, osk_y + 4, display_buf, COLOR_WHITE, 1);
    
    /* Keyboard layout (4 rows) */
    static const char *keys[] = {
        "1234567890",
        "QWERTYUIOP",
        "ASDFGHJKL",
        "ZXCVBNM <>"   /* < = backspace, > = enter */
    };
    
    int key_y = osk_y + 14;
    int key_h = (osk_h - 14) / 4;
    
    for (int row = 0; row < 4; row++) {
        int row_len = strlen(keys[row]);
        int key_w = DISPLAY_WIDTH / row_len;
        
        for (int col = 0; col < row_len; col++) {
            int kx = col * key_w;
            int ky = key_y + row * key_h;
            
            /* Highlight selected key */
            if (row == s_osk.key_row && col == s_osk.key_col) {
                display_fill_rect(kx, ky, key_w, key_h, COLOR_WHITE);
                char c[2] = {keys[row][col], '\0'};
                display_draw_string(kx + 2, ky + 1, c, COLOR_BLACK, 1);
            } else {
                char c[2] = {keys[row][col], '\0'};
                display_draw_string(kx + 2, ky + 1, c, COLOR_WHITE, 1);
            }
        }
    }
}

/* ============================================================================
 * Input Handlers
 * ============================================================================ */

static void handle_menu_input(int8_t x, int8_t y, uint8_t buttons)
{
    if (s_app_count == 0) return;
    
    int cols = 4;
    int max_items = s_app_count < 8 ? s_app_count : 8;
    
    /* Navigation */
    static uint32_t last_nav = 0;
    uint32_t now = esp_timer_get_time() / 1000;
    
    if (now - last_nav > 150) {  /* Debounce */
        if (x > 30) {
            s_menu.selected = (s_menu.selected + 1) % max_items;
            last_nav = now;
        } else if (x < -30) {
            s_menu.selected = (s_menu.selected - 1 + max_items) % max_items;
            last_nav = now;
        } else if (y > 30) {
            s_menu.selected = (s_menu.selected - cols + max_items) % max_items;
            last_nav = now;
        } else if (y < -30) {
            s_menu.selected = (s_menu.selected + cols) % max_items;
            last_nav = now;
        }
    }
    
    /* Select */
    if (buttons & UI_BTN_PRESS) {
        static uint32_t last_press = 0;
        if (now - last_press > 300) {
            if (s_menu.selected >= 0 && s_menu.selected < (int)s_app_count) {
                ui_launch_app(s_apps[s_menu.selected]->id);
            }
            last_press = now;
        }
    }
}

static void handle_dialog_input(int8_t x, int8_t y, uint8_t buttons)
{
    static uint32_t last_nav = 0;
    uint32_t now = esp_timer_get_time() / 1000;
    
    if (now - last_nav > 150) {
        if (x > 30) {
            s_dialog.selected = (s_dialog.selected + 1) % s_dialog.dialog.button_count;
            last_nav = now;
        } else if (x < -30) {
            s_dialog.selected = (s_dialog.selected - 1 + s_dialog.dialog.button_count) % s_dialog.dialog.button_count;
            last_nav = now;
        }
    }
    
    if (buttons & UI_BTN_PRESS) {
        static uint32_t last_press = 0;
        if (now - last_press > 300) {
            if (s_dialog.dialog.buttons[s_dialog.selected].on_click) {
                s_dialog.dialog.buttons[s_dialog.selected].on_click();
            }
            ui_close_dialog();
            last_press = now;
        }
    }
}

static void handle_osk_input(int8_t x, int8_t y, uint8_t buttons)
{
    static const char *keys[] = {
        "1234567890",
        "QWERTYUIOP",
        "ASDFGHJKL",
        "ZXCVBNM <>"
    };
    
    static uint32_t last_nav = 0;
    uint32_t now = esp_timer_get_time() / 1000;
    
    if (now - last_nav > 120) {
        int row_len = strlen(keys[s_osk.key_row]);
        
        if (x > 30) {
            s_osk.key_col = (s_osk.key_col + 1) % row_len;
            last_nav = now;
        } else if (x < -30) {
            s_osk.key_col = (s_osk.key_col - 1 + row_len) % row_len;
            last_nav = now;
        } else if (y > 30) {
            s_osk.key_row = (s_osk.key_row - 1 + 4) % 4;
            int new_row_len = strlen(keys[s_osk.key_row]);
            if (s_osk.key_col >= new_row_len) {
                s_osk.key_col = new_row_len - 1;
            }
            last_nav = now;
        } else if (y < -30) {
            s_osk.key_row = (s_osk.key_row + 1) % 4;
            int new_row_len = strlen(keys[s_osk.key_row]);
            if (s_osk.key_col >= new_row_len) {
                s_osk.key_col = new_row_len - 1;
            }
            last_nav = now;
        }
    }
    
    if (buttons & UI_BTN_PRESS) {
        static uint32_t last_press = 0;
        if (now - last_press > 200) {
            char key = keys[s_osk.key_row][s_osk.key_col];
            
            if (key == '<') {
                /* Backspace */
                if (s_osk.cursor > 0) {
                    s_osk.cursor--;
                    s_osk.buffer[s_osk.cursor] = '\0';
                }
            } else if (key == '>') {
                /* Enter - confirm */
                s_osk.active = false;
                if (s_osk.config.callback) {
                    s_osk.config.callback(s_osk.buffer, true);
                }
            } else {
                /* Add character */
                size_t max_len = s_osk.config.max_length ? s_osk.config.max_length : sizeof(s_osk.buffer) - 1;
                if (s_osk.cursor < max_len) {
                    s_osk.buffer[s_osk.cursor++] = key;
                    s_osk.buffer[s_osk.cursor] = '\0';
                }
            }
            last_press = now;
        }
    }
}

/* ============================================================================
 * Menu Widget Implementation
 * ============================================================================ */

void ui_draw_menu_list(int x, int y, int w, int h,
                       const ui_menu_item_t *items, size_t count,
                       int selected, int scroll_offset)
{
    int item_h = 10;
    int visible = h / item_h;
    
    for (int i = 0; i < visible && (scroll_offset + i) < (int)count; i++) {
        int idx = scroll_offset + i;
        int item_y = y + i * item_h;
        
        if (idx == selected) {
            display_fill_rect(x, item_y, w, item_h, COLOR_WHITE);
            display_draw_string(x + 2, item_y + 1, items[idx].label, COLOR_BLACK, 1);
        } else {
            display_draw_string(x + 2, item_y + 1, items[idx].label, COLOR_WHITE, 1);
        }
    }
    
    /* Scroll indicator */
    if (count > (size_t)visible) {
        int bar_h = h * visible / count;
        int bar_y = y + (h - bar_h) * scroll_offset / (count - visible);
        display_fill_rect(x + w - 2, bar_y, 2, bar_h, COLOR_WHITE);
    }
}

bool ui_handle_menu_input(int8_t y, uint8_t buttons,
                          const ui_menu_item_t *items, size_t count,
                          int *selected, int *scroll_offset)
{
    static uint32_t last_nav = 0;
    uint32_t now = esp_timer_get_time() / 1000;
    
    if (now - last_nav > 150) {
        if (y < -30 && *selected < (int)count - 1) {
            (*selected)++;
            last_nav = now;
        } else if (y > 30 && *selected > 0) {
            (*selected)--;
            last_nav = now;
        }
        
        /* Update scroll */
        int visible = 5;  /* Assume 5 visible items */
        if (*selected < *scroll_offset) {
            *scroll_offset = *selected;
        } else if (*selected >= *scroll_offset + visible) {
            *scroll_offset = *selected - visible + 1;
        }
    }
    
    if (buttons & UI_BTN_PRESS) {
        static uint32_t last_press = 0;
        if (now - last_press > 300) {
            if (items[*selected].on_select) {
                items[*selected].on_select();
            }
            last_press = now;
            return true;
        }
    }
    
    return false;
}

