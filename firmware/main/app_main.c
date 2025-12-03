/**
 * @file app_main.c
 * @brief ESP32 Smart Device - Main Application
 */

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "nvs_flash.h"
#include <stdbool.h>
#include <string.h>

#include "control_link.h"
#include "display.h"
#include "ui.h"
#include "mesh_client.h"

/* App headers */
#include "app_settings.h"
#include "app_notes.h"
#include "app_calendar.h"
#include "app_mesh.h"
#include "app_music.h"
#include "app_camera.h"
#include "app_solitaire.h"
#include "app_translate.h"
#include "app_email.h"
#include "app_browser.h"

static const char *TAG = "main";

/* ============================================================================
 * Configuration
 * ============================================================================ */

#define TEST_OLED_SDA_PIN   21
#define TEST_OLED_SCL_PIN   22
#define TEST_OLED_I2C_ADDR  0x3C

/* ============================================================================
 * Input Handling
 * ============================================================================ */

static void handle_joystick_state(const control_link_joystick_t *state)
{
    if (!state) {
        return;
    }
    
    /* Route all input through UI framework */
    ui_input(state->x, state->y, state->buttons);
    
    control_link_send_ack(state->seq);
}

static void handle_macro_packet(const control_link_packet_t *packet)
{
    if (!packet) {
        return;
    }
    ESP_LOGI(TAG, "Macro packet len=%d", (int)packet->payload_len);
    control_link_send_ack(packet->seq);
}

/* ============================================================================
 * Mesh Message Handlers
 * ============================================================================ */

static void handle_mesh_message(const mesh_message_t *msg)
{
    if (!msg) return;
    
    ESP_LOGI(TAG, "Mesh from %s: %s", msg->from_name, msg->message);
    
    /* Show notification */
    ui_notification_t notif = {
        .title = msg->from_name,
        .body = msg->message,
        .priority = UI_NOTIFY_NORMAL,
        .duration_ms = 5000,
    };
    ui_notify(&notif);
}

static void handle_mesh_status(const mesh_status_t *status)
{
    if (!status) return;
    
    /* Update UI status */
    ui_status_t ui_status = *ui_get_status();
    ui_status.ble_connected = status->connected;
    ui_update_status(&ui_status);
}

static void handle_mesh_send_complete(uint32_t seq, bool success)
{
    if (success) {
        ui_notify_simple("Message sent");
    } else {
        ui_notify_simple("Send failed");
    }
}

/* ============================================================================
 * Tasks
 * ============================================================================ */

static void ui_task(void *arg)
{
    ESP_LOGI(TAG, "UI task starting");
    
    /* Initialize display */
    display_config_t disp_cfg = {
        .type = DISPLAY_TYPE_SSD1306_I2C,
        .i2c = {
            .i2c_addr = TEST_OLED_I2C_ADDR,
            .sda_pin = TEST_OLED_SDA_PIN,
            .scl_pin = TEST_OLED_SCL_PIN,
        },
        .flip_horizontal = false,
        .flip_vertical = false,
    };
    
    if (display_init(&disp_cfg) != ESP_OK) {
        ESP_LOGE(TAG, "Display init failed");
        vTaskDelete(NULL);
        return;
    }
    
    /* Initialize UI framework */
    if (ui_init() != ESP_OK) {
        ESP_LOGE(TAG, "UI init failed");
        vTaskDelete(NULL);
        return;
    }
    
    /* Register all apps */
    ui_register_app(&app_settings);
    ui_register_app(&app_notes);
    ui_register_app(&app_calendar);
    ui_register_app(&app_mesh);
    ui_register_app(&app_music);
    ui_register_app(&app_solitaire);
    ui_register_app(&app_camera);
    ui_register_app(&app_translate);
    /* Uncomment when WiFi is configured:
    ui_register_app(&app_email);
    ui_register_app(&app_browser);
    */
    
    ESP_LOGI(TAG, "UI ready, entering render loop");
    
    uint32_t last_tick = esp_timer_get_time() / 1000;
    
    while (true) {
        uint32_t now = esp_timer_get_time() / 1000;
        uint32_t dt = now - last_tick;
        last_tick = now;
        
        /* Update status bar info */
        ui_status_t status = *ui_get_status();
        status.ble_connected = control_link_is_connected();
        
        /* Update time (TODO: get from RTC/NTP) */
        uint32_t secs = now / 1000;
        status.hour = (secs / 3600) % 24;
        status.minute = (secs / 60) % 60;
        
        ui_update_status(&status);
        
        /* Tick and render */
        ui_tick(dt);
        ui_render();
        
        vTaskDelay(pdMS_TO_TICKS(50));  /* 20 FPS */
    }
}

static void connectivity_task(void *arg)
{
    ESP_LOGI(TAG, "Connectivity task starting");
    ESP_ERROR_CHECK(control_link_start_advertising());
    
    while (true) {
        /* TODO: WiFi management, connection monitoring */
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

/* ============================================================================
 * Initialization
 * ============================================================================ */

static void init_services(void)
{
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    ESP_LOGI(TAG, "Event loop ready");
    
    /* Initialize control link (BLE to partner device) */
    ESP_ERROR_CHECK(control_link_init());
    ESP_ERROR_CHECK(control_link_subscribe_macros(handle_macro_packet));
    ESP_ERROR_CHECK(control_link_subscribe_joystick(handle_joystick_state));
    
    /* Initialize mesh client */
    ESP_ERROR_CHECK(mesh_client_init());
    ESP_ERROR_CHECK(mesh_client_subscribe_inbox(handle_mesh_message));
    ESP_ERROR_CHECK(mesh_client_subscribe_status(handle_mesh_status));
    ESP_ERROR_CHECK(mesh_client_subscribe_send_complete(handle_mesh_send_complete));
    
    ESP_LOGI(TAG, "Services initialized");
}

void app_main(void)
{
    ESP_LOGI(TAG, "ESP32 Smart Device starting...");
    
    /* Initialize NVS */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ESP_ERROR_CHECK(nvs_flash_init());
    }
    
    init_services();
    
    /* Create tasks */
    xTaskCreate(ui_task, "ui_task", 8192, NULL, 5, NULL);
    xTaskCreate(connectivity_task, "conn_task", 4096, NULL, 6, NULL);
    
    ESP_LOGI(TAG, "System init complete");
}
