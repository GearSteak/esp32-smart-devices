idf_component_register(
    SRCS "csv_editor.c"
    INCLUDE_DIRS "include"
    REQUIRES
        doc_manager
        esp_timer
        esp_event
)
