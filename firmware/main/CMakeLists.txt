set(SRCS
    "app_main.c"
)

idf_component_register(
    SRCS ${SRCS}
    INCLUDE_DIRS "."
    REQUIRES
        esp_event
        nvs_flash
)
