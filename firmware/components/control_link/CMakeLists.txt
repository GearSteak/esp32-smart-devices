idf_component_register(
    SRCS "control_link.c"
    INCLUDE_DIRS "include"
    REQUIRES
        esp_event
        nvs_flash
        bt
)
