#include "text_editor.h"

#include "doc_manager.h"
#include "esp_event.h"
#include "esp_log.h"

ESP_EVENT_DEFINE_BASE(TEXT_EDITOR_EVENT);

static const char *TAG = "text_editor";

static text_editor_open_cfg_t current_doc = {
    .path = NULL,
    .view = TEXT_EDITOR_VIEW_DRAFT,
};

esp_err_t text_editor_init(void)
{
    ESP_LOGI(TAG, "Initializing text editor subsystem");
    return ESP_OK;
}

esp_err_t text_editor_open(const text_editor_open_cfg_t *cfg)
{
    if (!cfg || !cfg->path) {
        return ESP_ERR_INVALID_ARG;
    }

    current_doc = *cfg;
    ESP_LOGI(TAG, "Opening document %s (view %d)", cfg->path, cfg->view);

    // TODO: request document stream from doc_manager and populate rope buffer
    return ESP_OK;
}

esp_err_t text_editor_handle_input(const uint8_t *keycode_stream, size_t len)
{
    if (!keycode_stream || !len) {
        return ESP_ERR_INVALID_ARG;
    }

    // TODO: translate keycodes into editor actions and update buffer
    esp_event_post(TEXT_EDITOR_EVENT, TEXT_EDITOR_EVENT_STATUS, NULL, 0, portMAX_DELAY);
    return ESP_OK;
}

esp_err_t text_editor_tick(void)
{
    // TODO: flush pending renders to UI subsystem
    esp_event_post(TEXT_EDITOR_EVENT, TEXT_EDITOR_EVENT_RENDER, NULL, 0, 0);
    return ESP_OK;
}
