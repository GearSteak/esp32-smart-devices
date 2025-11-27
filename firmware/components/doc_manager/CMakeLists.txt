idf_component_register(
    SRCS "doc_manager.c"
    INCLUDE_DIRS "include"
    REQUIRES
        esp_event
        fatfs
)
