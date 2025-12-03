set(SRCS
    "app_main.c"
)

idf_component_register(
    SRCS ${SRCS}
    INCLUDE_DIRS "."
    REQUIRES
        esp_event
        esp_timer
        nvs_flash
        control_link
        mesh_client
        display
        ui
        app_settings
        app_notes
        app_calendar
        app_mesh
        app_music
        app_camera
        app_solitaire
        app_translate
        app_email
        app_browser
)
