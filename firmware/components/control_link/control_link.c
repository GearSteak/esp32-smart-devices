#include "control_link.h"

#include "esp_event.h"
#include "esp_log.h"

ESP_EVENT_DEFINE_BASE(CONTROL_LINK_EVENT);

static const char *TAG = "control_link";

static void (*macro_handler)(const control_link_packet_t *packet) = NULL;
static void (*joystick_handler)(const control_link_joystick_t *state) = NULL;

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
    if (!handler) {
        return ESP_ERR_INVALID_ARG;
    }
    macro_handler = handler;
    return ESP_OK;
}

esp_err_t control_link_subscribe_joystick(void (*handler)(const control_link_joystick_t *state))
{
    if (!handler) {
        return ESP_ERR_INVALID_ARG;
    }
    joystick_handler = handler;
    return ESP_OK;
}

static void __attribute__((unused)) on_macro_received(const uint8_t *data, size_t len)
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

static void __attribute__((unused)) on_joystick_frame(const uint8_t *data, size_t len)
{
    if (!joystick_handler || len < 8) {
        return;
    }

    control_link_joystick_t state = {
        .x = (int8_t)data[0],
        .y = (int8_t)data[1],
        .buttons = data[2],
        .layer = data[3],
        .seq = (uint32_t)data[4] | ((uint32_t)data[5] << 8) | ((uint32_t)data[6] << 16) | ((uint32_t)data[7] << 24),
    };

    joystick_handler(&state);
    esp_event_post(CONTROL_LINK_EVENT, CONTROL_LINK_EVENT_JOYSTICK, &state, sizeof(state), portMAX_DELAY);
}
