#pragma once

#include "esp_err.h"
#include "esp_event.h"
#include <stdint.h>

ESP_EVENT_DECLARE_BASE(CONTROL_LINK_EVENT);

typedef enum {
    CONTROL_LINK_EVENT_CONNECTED,
    CONTROL_LINK_EVENT_DISCONNECTED,
    CONTROL_LINK_EVENT_MACRO,
    CONTROL_LINK_EVENT_SENSOR,
    CONTROL_LINK_EVENT_JOYSTICK,
} control_link_event_id_t;

typedef struct {
    uint32_t seq;
    const uint8_t *payload;
    size_t payload_len;
} control_link_packet_t;

typedef struct {
    int8_t x;
    int8_t y;
    uint8_t buttons;
    uint8_t layer;
    uint32_t seq;
} control_link_joystick_t;

esp_err_t control_link_init(void);
esp_err_t control_link_start_advertising(void);
esp_err_t control_link_send_ack(uint32_t seq);
esp_err_t control_link_subscribe_macros(void (*handler)(const control_link_packet_t *packet));
esp_err_t control_link_subscribe_joystick(void (*handler)(const control_link_joystick_t *state));
bool control_link_is_connected(void);
