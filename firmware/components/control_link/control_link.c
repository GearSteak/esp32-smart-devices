#include "control_link.h"

#include "esp_event.h"
#include "esp_log.h"

ESP_EVENT_DEFINE_BASE(CONTROL_LINK_EVENT);

static const char *TAG = "control_link";

static void (*macro_handler)(const control_link_packet_t *packet) = NULL;

esp_err_t control_link_init(void)
{
    ESP_LOGI(TAG, "Initializing BLE control link");
    // TODO: configure NimBLE stack, register GATT services from docs/ble-partner-protocol
    return ESP_OK;
}

esp_err_t control_link_start_advertising(void)
{
    ESP_LOGI(TAG, "Starting advertising for partner ESP32");
    // TODO: start BLE advertising with custom UUIDs
    return ESP_OK;
}

esp_err_t control_link_send_ack(uint32_t seq)
{
    ESP_LOGD(TAG, "ACK seq %u", seq);
    // TODO: send indication back to partner
    return ESP_OK;
}

esp_err_t control_link_subscribe_macros(void (*handler)(const control_link_packet_t *packet))
{
    macro_handler = handler;
    return ESP_OK;
}

static void on_macro_received(const uint8_t *data, size_t len)
{
    if (!macro_handler) {
        return;
    }

    control_link_packet_t pkt = {
        .seq = 0, // TODO: parse incoming CBOR sequence
        .payload = data,
        .payload_len = len,
    };
    macro_handler(&pkt);
    esp_event_post(CONTROL_LINK_EVENT, CONTROL_LINK_EVENT_MACRO, NULL, 0, 0);
}
