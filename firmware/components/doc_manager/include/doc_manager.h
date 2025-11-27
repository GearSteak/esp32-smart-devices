#pragma once

#include "esp_err.h"

typedef struct {
    char path[128];
    char title[64];
    char lang[8];
    uint32_t updated_ts;
} doc_metadata_t;

esp_err_t doc_manager_init(void);
esp_err_t doc_manager_load(const char *path, void *ctx);
esp_err_t doc_manager_save(const char *path, const void *data, size_t len);
esp_err_t doc_manager_get_metadata(const char *path, doc_metadata_t *out);
