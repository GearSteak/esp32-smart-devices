idf_component_register(
    SRCS "mesh_client.c"
    INCLUDE_DIRS "include"
    REQUIRES esp_event nvs_flash bt
    PRIV_REQUIRES esp_timer
)

