#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"

#include "control_link.h"
#include "csv_editor.h"
#include "doc_manager.h"
#include "text_editor.h"

static const char *TAG = "main";

typedef enum {
    PIPE_EVENT_TRANSLATION,
    PIPE_EVENT_NOTIFICATION,
    PIPE_EVENT_PARTNER_CTRL,
} pipe_event_t;

static void handle_macro_packet(const control_link_packet_t *packet)
{
    if (!packet) {
        return;
    }

    ESP_LOGI(TAG, "Macro packet len=%d", (int)packet->payload_len);
    // TODO: parse CBOR and route to text/csv editors
    control_link_send_ack(packet->seq);
}

static void display_task(void *arg)
{
    ESP_LOGI(TAG, "Display task bootstrap");
    while (true) {
        // TODO: pull from UI queue and push frames to transparent OLED
        vTaskDelay(pdMS_TO_TICKS(250));
    }
}

static void connectivity_task(void *arg)
{
    ESP_LOGI(TAG, "Connectivity task bootstrap");
    ESP_ERROR_CHECK(control_link_start_advertising());

    while (true) {
        // TODO: manage Wi-Fi STA + BLE (phone, keyboard, partner)
        vTaskDelay(pdMS_TO_TICKS(250));
    }
}

static void translation_task(void *arg)
{
    ESP_LOGI(TAG, "Translation task bootstrap");
    while (true) {
        // TODO: route audio/text to translation providers and cache results
        vTaskDelay(pdMS_TO_TICKS(250));
    }
}

static void editor_task(void *arg)
{
    ESP_LOGI(TAG, "Editor task bootstrap");
    while (true) {
        text_editor_tick();
        csv_editor_tick();
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

static void init_services(void)
{
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    ESP_LOGI(TAG, "Event loop ready");

    ESP_ERROR_CHECK(doc_manager_init());
    ESP_ERROR_CHECK(text_editor_init());
    ESP_ERROR_CHECK(csv_editor_init());
    ESP_ERROR_CHECK(control_link_init());
    ESP_ERROR_CHECK(control_link_subscribe_macros(handle_macro_packet));

    // TODO: initialize display, audio, SD card, and BLE subsystems.
}

void app_main(void)
{
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ESP_ERROR_CHECK(nvs_flash_init());
    }

    init_services();

    xTaskCreate(display_task, "display_task", 4096, NULL, 5, NULL);
    xTaskCreate(connectivity_task, "connectivity_task", 4096, NULL, 6, NULL);
    xTaskCreate(translation_task, "translation_task", 4096, NULL, 5, NULL);
    xTaskCreate(editor_task, "editor_task", 4096, NULL, 5, NULL);

    ESP_LOGI(TAG, "System init complete");
}
