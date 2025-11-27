#pragma once

#include "esp_err.h"
#include "esp_event.h"
#include <stdint.h>

ESP_EVENT_DECLARE_BASE(TEXT_EDITOR_EVENT);

typedef enum {
    TEXT_EDITOR_EVENT_RENDER,
    TEXT_EDITOR_EVENT_STATUS,
} text_editor_event_id_t;

typedef enum {
    TEXT_EDITOR_VIEW_DRAFT,
    TEXT_EDITOR_VIEW_FOCUS,
    TEXT_EDITOR_VIEW_TRANSLATION,
} text_editor_view_t;

typedef struct {
    const char *path;
    text_editor_view_t view;
} text_editor_open_cfg_t;

esp_err_t text_editor_init(void);
esp_err_t text_editor_open(const text_editor_open_cfg_t *cfg);
esp_err_t text_editor_handle_input(const uint8_t *keycode_stream, size_t len);
esp_err_t text_editor_tick(void);
esp_err_t text_editor_handle_joystick(int8_t x, int8_t y, uint8_t buttons, uint8_t layer);
