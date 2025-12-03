/**
 * @file app_music.h
 * @brief MP3 Music Player App
 */

#pragma once

#include "ui.h"

#ifdef __cplusplus
extern "C" {
#endif

extern const ui_app_t app_music;

/**
 * @brief Check if music is currently playing
 */
bool music_is_playing(void);

/**
 * @brief Play/pause toggle
 */
void music_toggle(void);

/**
 * @brief Stop playback
 */
void music_stop(void);

#ifdef __cplusplus
}
#endif

