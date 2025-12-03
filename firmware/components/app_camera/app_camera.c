/**
 * @file app_camera.c
 * @brief Camera App Implementation
 */

#include "app_camera.h"
#include "ui.h"
#include "display.h"
#include "sprites.h"
#include "esp_log.h"
#include "esp_timer.h"
#include <string.h>
#include <stdio.h>
#include <dirent.h>

static const char *TAG = "camera";

/* ============================================================================
 * Configuration
 * ============================================================================ */

#define PHOTOS_DIR "/sdcard/photos"
#define MAX_PHOTOS 100
#define THUMB_W 32
#define THUMB_H 24

/* ============================================================================
 * Types
 * ============================================================================ */

typedef struct {
    char filename[32];
} photo_t;

typedef enum {
    VIEW_CAMERA,
    VIEW_GALLERY,
    VIEW_PHOTO,
} view_mode_t;

/* ============================================================================
 * State
 * ============================================================================ */

static view_mode_t s_mode = VIEW_CAMERA;
static photo_t s_photos[MAX_PHOTOS];
static int s_photo_count = 0;
static int s_selected = 0;
static int s_scroll = 0;
static int s_next_photo_num = 1;

/* Camera state */
static bool s_camera_ready = false;
static bool s_preview_active = false;

/* ============================================================================
 * File Operations
 * ============================================================================ */

static void ensure_photos_dir(void)
{
    /* TODO: Create directory if not exists */
}

static void scan_photos(void)
{
    s_photo_count = 0;
    ensure_photos_dir();
    
    DIR *dir = opendir(PHOTOS_DIR);
    if (!dir) {
        ESP_LOGW(TAG, "Photos directory not found");
        return;
    }
    
    struct dirent *entry;
    int max_num = 0;
    
    while ((entry = readdir(dir)) != NULL && s_photo_count < MAX_PHOTOS) {
        if (entry->d_name[0] == '.') continue;
        
        size_t len = strlen(entry->d_name);
        if (len > 4 && strcasecmp(entry->d_name + len - 4, ".jpg") == 0) {
            strncpy(s_photos[s_photo_count].filename, entry->d_name, sizeof(s_photos[0].filename) - 1);
            
            /* Track highest photo number */
            int num = 0;
            if (sscanf(entry->d_name, "IMG_%d", &num) == 1 && num > max_num) {
                max_num = num;
            }
            
            s_photo_count++;
        }
    }
    
    closedir(dir);
    s_next_photo_num = max_num + 1;
    ESP_LOGI(TAG, "Found %d photos", s_photo_count);
}

/* ============================================================================
 * Camera Operations
 * ============================================================================ */

static void init_camera(void)
{
    /* TODO: Initialize ESP32-CAM module */
    s_camera_ready = false;
    ESP_LOGI(TAG, "Camera init (stub)");
}

static void start_preview(void)
{
    if (!s_camera_ready) return;
    s_preview_active = true;
    /* TODO: Start camera preview stream */
}

static void stop_preview(void)
{
    s_preview_active = false;
    /* TODO: Stop camera preview */
}

static void capture_photo(void)
{
    if (!s_camera_ready) {
        ui_notify_simple("Camera not ready");
        return;
    }
    
    char filename[48];
    snprintf(filename, sizeof(filename), "%s/IMG_%04d.jpg", PHOTOS_DIR, s_next_photo_num);
    
    /* TODO: Capture frame and save to SD */
    /* esp_camera_fb_get() -> write to file -> esp_camera_fb_return() */
    
    ESP_LOGI(TAG, "Captured: %s", filename);
    s_next_photo_num++;
    
    ui_notify_simple("Photo saved!");
    scan_photos();
}

static void delete_photo(int idx)
{
    if (idx < 0 || idx >= s_photo_count) return;
    
    char path[64];
    snprintf(path, sizeof(path), "%s/%s", PHOTOS_DIR, s_photos[idx].filename);
    
    if (remove(path) == 0) {
        ESP_LOGI(TAG, "Deleted: %s", s_photos[idx].filename);
        scan_photos();
        if (s_selected >= s_photo_count) {
            s_selected = s_photo_count > 0 ? s_photo_count - 1 : 0;
        }
    }
}

/* ============================================================================
 * App Callbacks
 * ============================================================================ */

static void on_enter(void)
{
    ESP_LOGI(TAG, "Camera app entered");
    init_camera();
    scan_photos();
    s_mode = VIEW_CAMERA;
}

static void on_exit(void)
{
    ESP_LOGI(TAG, "Camera app exited");
    stop_preview();
}

static void on_input(int8_t x, int8_t y, uint8_t buttons)
{
    static uint32_t last_nav = 0;
    uint32_t now = esp_timer_get_time() / 1000;
    
    if (buttons & UI_BTN_BACK) {
        if (s_mode == VIEW_PHOTO) {
            s_mode = VIEW_GALLERY;
        } else if (s_mode == VIEW_GALLERY) {
            s_mode = VIEW_CAMERA;
            start_preview();
        } else {
            ui_go_back();
        }
        return;
    }
    
    switch (s_mode) {
    case VIEW_CAMERA:
        if (buttons & UI_BTN_PRESS) {
            capture_photo();
        }
        
        if (buttons & UI_BTN_LONG) {
            stop_preview();
            s_mode = VIEW_GALLERY;
            s_selected = 0;
            s_scroll = 0;
        }
        break;
        
    case VIEW_GALLERY:
        if (now - last_nav > 150) {
            int cols = 3;
            if (x > 30) {
                s_selected = (s_selected + 1) % (s_photo_count > 0 ? s_photo_count : 1);
                last_nav = now;
            } else if (x < -30) {
                s_selected = (s_selected - 1 + s_photo_count) % (s_photo_count > 0 ? s_photo_count : 1);
                last_nav = now;
            } else if (y < -30 && s_selected + cols < s_photo_count) {
                s_selected += cols;
                last_nav = now;
            } else if (y > 30 && s_selected >= cols) {
                s_selected -= cols;
                last_nav = now;
            }
        }
        
        if (buttons & UI_BTN_PRESS) {
            if (s_photo_count > 0) {
                s_mode = VIEW_PHOTO;
            }
        }
        
        if (buttons & UI_BTN_DOUBLE) {
            delete_photo(s_selected);
        }
        break;
        
    case VIEW_PHOTO:
        /* Pan around large image */
        if (buttons & UI_BTN_DOUBLE) {
            delete_photo(s_selected);
            if (s_photo_count > 0) {
                s_mode = VIEW_GALLERY;
            } else {
                s_mode = VIEW_CAMERA;
            }
        }
        break;
    }
}

static void on_render(void)
{
    int y = UI_STATUS_BAR_HEIGHT + 2;
    
    switch (s_mode) {
    case VIEW_CAMERA:
        if (s_camera_ready) {
            /* TODO: Draw preview frame */
            display_draw_rect(10, 15, 108, 45, COLOR_WHITE);
            display_draw_string(35, 35, "Preview", COLOR_WHITE, 1);
        } else {
            display_draw_string(20, 25, "Camera", COLOR_WHITE, 1);
            display_draw_string(20, 35, "not ready", COLOR_WHITE, 1);
        }
        
        display_draw_string(2, DISPLAY_HEIGHT - 10, "Press: Photo", COLOR_WHITE, 1);
        display_draw_string(70, DISPLAY_HEIGHT - 10, "Hold: Gallery", COLOR_WHITE, 1);
        break;
        
    case VIEW_GALLERY:
        display_draw_string(2, y, "Gallery", COLOR_WHITE, 1);
        display_printf(60, y, COLOR_WHITE, 1, "(%d)", s_photo_count);
        display_draw_hline(0, y + 9, DISPLAY_WIDTH, COLOR_WHITE);
        y += 12;
        
        if (s_photo_count == 0) {
            display_draw_string(20, 30, "No photos", COLOR_WHITE, 1);
        } else {
            /* Thumbnail grid (3 columns) */
            int cols = 3;
            int tw = 40;
            int th = 24;
            int gap = 2;
            
            for (int i = 0; i < 6 && (s_scroll + i) < s_photo_count; i++) {
                int idx = s_scroll + i;
                int col = i % cols;
                int row = i / cols;
                int tx = col * (tw + gap) + 2;
                int ty = y + row * (th + gap);
                
                /* Thumbnail placeholder */
                display_draw_rect(tx, ty, tw, th, COLOR_WHITE);
                
                /* Photo number */
                int num = 0;
                sscanf(s_photos[idx].filename, "IMG_%d", &num);
                display_printf(tx + 2, ty + 8, COLOR_WHITE, 1, "%d", num);
                
                /* Selection highlight */
                if (idx == s_selected) {
                    display_draw_rect(tx - 1, ty - 1, tw + 2, th + 2, COLOR_WHITE);
                    display_draw_rect(tx - 2, ty - 2, tw + 4, th + 4, COLOR_WHITE);
                }
            }
        }
        break;
        
    case VIEW_PHOTO:
        if (s_selected >= 0 && s_selected < s_photo_count) {
            /* TODO: Load and display JPEG (downscaled) */
            display_draw_rect(0, 12, DISPLAY_WIDTH, 50, COLOR_WHITE);
            
            /* Show filename */
            display_draw_string(2, DISPLAY_HEIGHT - 10, s_photos[s_selected].filename, COLOR_WHITE, 1);
        }
        break;
    }
}

static void on_tick(uint32_t dt_ms)
{
    (void)dt_ms;
    
    /* TODO: Update preview frame periodically */
}

/* ============================================================================
 * App Definition
 * ============================================================================ */

const ui_app_t app_camera = {
    .id = "camera",
    .name = "Camera",
    .icon = ICON_CAMERA,
    .on_enter = on_enter,
    .on_exit = on_exit,
    .on_input = on_input,
    .on_render = on_render,
    .on_tick = on_tick,
};

