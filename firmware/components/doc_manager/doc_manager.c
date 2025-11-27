#include "doc_manager.h"

#include "esp_log.h"

static const char *TAG = "doc_manager";

esp_err_t doc_manager_init(void)
{
    ESP_LOGI(TAG, "Mounting SD card and preparing metadata index");
    // TODO: mount FatFS / cache index file
    return ESP_OK;
}

esp_err_t doc_manager_load(const char *path, void *ctx)
{
    if (!path) {
        return ESP_ERR_INVALID_ARG;
    }

    ESP_LOGI(TAG, "Loading document %s", path);
    // TODO: stream file into provided context (rope buffer, CSV grid, etc.)
    return ESP_OK;
}

esp_err_t doc_manager_save(const char *path, const void *data, size_t len)
{
    if (!path || (!data && len)) {
        return ESP_ERR_INVALID_ARG;
    }

    ESP_LOGI(TAG, "Saving document %s (%d bytes)", path, (int)len);
    // TODO: write file to SD card and update metadata index
    return ESP_OK;
}

esp_err_t doc_manager_get_metadata(const char *path, doc_metadata_t *out)
{
    if (!path || !out) {
        return ESP_ERR_INVALID_ARG;
    }

    // TODO: look up metadata entry from index
    snprintf(out->path, sizeof(out->path), "%s", path);
    snprintf(out->title, sizeof(out->title), "%s", "untitled");
    snprintf(out->lang, sizeof(out->lang), "%s", "ja");
    out->updated_ts = 0;
    return ESP_OK;
}
