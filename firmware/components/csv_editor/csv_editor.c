#include "csv_editor.h"

#include "doc_manager.h"
#include "esp_event.h"
#include "esp_log.h"

ESP_EVENT_DEFINE_BASE(CSV_EDITOR_EVENT);

static const char *TAG = "csv_editor";

typedef struct {
    int row;
    int col;
} cursor_pos_t;

static csv_editor_open_cfg_t current_sheet = {
    .path = NULL,
    .viewport_rows = 4,
    .viewport_cols = 8,
};

static cursor_pos_t cursor;

esp_err_t csv_editor_init(void)
{
    ESP_LOGI(TAG, "Initializing CSV editor");
    cursor.row = 0;
    cursor.col = 0;
    return ESP_OK;
}

esp_err_t csv_editor_open(const csv_editor_open_cfg_t *cfg)
{
    if (!cfg || !cfg->path) {
        return ESP_ERR_INVALID_ARG;
    }

    current_sheet = *cfg;
    cursor.row = 0;
    cursor.col = 0;

    ESP_LOGI(TAG, "Opening CSV sheet %s (%ux%u viewport)", cfg->path, cfg->viewport_rows, cfg->viewport_cols);
    // TODO: stream CSV header via doc_manager and cache visible window
    return ESP_OK;
}

esp_err_t csv_editor_move_cursor(int delta_row, int delta_col)
{
    cursor.row += delta_row;
    cursor.col += delta_col;

    if (cursor.row < 0) {
        cursor.row = 0;
    }
    if (cursor.col < 0) {
        cursor.col = 0;
    }

    // TODO: trigger window scroll if cursor exits viewport
    esp_event_post(CSV_EDITOR_EVENT, CSV_EDITOR_EVENT_RENDER, NULL, 0, 0);
    return ESP_OK;
}

esp_err_t csv_editor_edit_cell(const char *value)
{
    if (!value) {
        return ESP_ERR_INVALID_ARG;
    }

    ESP_LOGI(TAG, "Editing cell (%d,%d) -> %s", cursor.row, cursor.col, value);
    // TODO: stage edit in buffer and schedule persistence via doc_manager
    esp_event_post(CSV_EDITOR_EVENT, CSV_EDITOR_EVENT_STATUS, NULL, 0, portMAX_DELAY);
    return ESP_OK;
}

esp_err_t csv_editor_tick(void)
{
    // TODO: flush pending operations / autosave
    return ESP_OK;
}
