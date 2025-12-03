idf_component_register(
    SRCS "app_settings.c"
    INCLUDE_DIRS "include"
    REQUIRES ui display nvs_flash control_link
)

