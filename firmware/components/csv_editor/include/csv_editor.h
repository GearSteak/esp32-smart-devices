#pragma once

#include "esp_err.h"
#include "esp_event.h"
#include <stddef.h>

ESP_EVENT_DECLARE_BASE(CSV_EDITOR_EVENT);

typedef enum {
    CSV_EDITOR_EVENT_RENDER,
    CSV_EDITOR_EVENT_STATUS,
} csv_editor_event_id_t;

typedef struct {
    const char *path;
    uint16_t viewport_rows;
    uint16_t viewport_cols;
} csv_editor_open_cfg_t;

esp_err_t csv_editor_init(void);
esp_err_t csv_editor_open(const csv_editor_open_cfg_t *cfg);
esp_err_t csv_editor_move_cursor(int delta_row, int delta_col);
esp_err_t csv_editor_edit_cell(const char *value);
esp_err_t csv_editor_tick(void);
