/**
 * @file app_music.c
 * @brief MP3 Music Player App Implementation
 * 
 * Uses I2S output to MAX98357A or similar amplifier
 * Supports MP3 files from SD card
 */

#include "app_music.h"
#include "ui.h"
#include "display.h"
#include "sprites.h"
#include "esp_log.h"
#include "esp_timer.h"
#include <string.h>
#include <stdio.h>
#include <dirent.h>

static const char *TAG = "music";

/* ============================================================================
 * Configuration
 * ============================================================================ */

#define MUSIC_DIR "/sdcard/music"
#define MAX_TRACKS 64

/* ============================================================================
 * Types
 * ============================================================================ */

typedef struct {
    char filename[48];
    char title[32];
    char artist[24];
    uint32_t duration_sec;
} track_t;

typedef enum {
    VIEW_BROWSER,
    VIEW_PLAYING,
} view_mode_t;

/* ============================================================================
 * State
 * ============================================================================ */

static view_mode_t s_mode = VIEW_BROWSER;
static track_t s_tracks[MAX_TRACKS];
static int s_track_count = 0;
static int s_selected = 0;
static int s_scroll = 0;

/* Playback state */
static bool s_playing = false;
static int s_current_track = -1;
static uint32_t s_position_sec = 0;
static uint8_t s_volume = 80;

/* ============================================================================
 * File Operations
 * ============================================================================ */

static void scan_music(void)
{
    s_track_count = 0;
    
    DIR *dir = opendir(MUSIC_DIR);
    if (!dir) {
        ESP_LOGW(TAG, "Music directory not found");
        return;
    }
    
    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL && s_track_count < MAX_TRACKS) {
        if (entry->d_name[0] == '.') continue;
        
        size_t len = strlen(entry->d_name);
        if (len > 4 && strcasecmp(entry->d_name + len - 4, ".mp3") == 0) {
            track_t *t = &s_tracks[s_track_count];
            strncpy(t->filename, entry->d_name, sizeof(t->filename) - 1);
            
            /* Default title from filename (strip .mp3) */
            strncpy(t->title, entry->d_name, sizeof(t->title) - 1);
            size_t title_len = strlen(t->title);
            if (title_len > 4) t->title[title_len - 4] = '\0';
            
            strcpy(t->artist, "Unknown");
            t->duration_sec = 0;
            
            /* TODO: Parse ID3 tags for title/artist/duration */
            
            s_track_count++;
        }
    }
    
    closedir(dir);
    ESP_LOGI(TAG, "Found %d tracks", s_track_count);
}

/* ============================================================================
 * Playback Control
 * ============================================================================ */

static void start_playback(int track_idx)
{
    if (track_idx < 0 || track_idx >= s_track_count) return;
    
    s_current_track = track_idx;
    s_position_sec = 0;
    s_playing = true;
    
    /* TODO: Initialize I2S and start MP3 decoder task */
    ESP_LOGI(TAG, "Playing: %s", s_tracks[track_idx].title);
    
    /* Update status bar */
    ui_status_t status = *ui_get_status();
    status.music_playing = true;
    ui_update_status(&status);
}

static void stop_playback(void)
{
    s_playing = false;
    s_position_sec = 0;
    
    /* TODO: Stop I2S and decoder task */
    
    ui_status_t status = *ui_get_status();
    status.music_playing = false;
    ui_update_status(&status);
}

static void pause_playback(void)
{
    s_playing = false;
    /* TODO: Pause I2S output */
}

static void resume_playback(void)
{
    if (s_current_track >= 0) {
        s_playing = true;
        /* TODO: Resume I2S output */
    }
}

static void next_track(void)
{
    if (s_track_count == 0) return;
    
    int next = (s_current_track + 1) % s_track_count;
    start_playback(next);
}

static void prev_track(void)
{
    if (s_track_count == 0) return;
    
    /* If more than 3 seconds in, restart current track */
    if (s_position_sec > 3) {
        s_position_sec = 0;
        return;
    }
    
    int prev = (s_current_track - 1 + s_track_count) % s_track_count;
    start_playback(prev);
}

/* ============================================================================
 * Public API
 * ============================================================================ */

bool music_is_playing(void)
{
    return s_playing;
}

void music_toggle(void)
{
    if (s_playing) {
        pause_playback();
    } else {
        resume_playback();
    }
}

void music_stop(void)
{
    stop_playback();
}

/* ============================================================================
 * App Callbacks
 * ============================================================================ */

static void on_enter(void)
{
    ESP_LOGI(TAG, "Music app entered");
    scan_music();
    
    if (s_current_track >= 0 && s_playing) {
        s_mode = VIEW_PLAYING;
    } else {
        s_mode = VIEW_BROWSER;
        s_selected = 0;
        s_scroll = 0;
    }
}

static void on_exit(void)
{
    ESP_LOGI(TAG, "Music app exited");
    /* Keep playing in background */
}

static void on_input(int8_t x, int8_t y, uint8_t buttons)
{
    static uint32_t last_nav = 0;
    uint32_t now = esp_timer_get_time() / 1000;
    
    if (buttons & UI_BTN_BACK) {
        if (s_mode == VIEW_PLAYING) {
            s_mode = VIEW_BROWSER;
        } else {
            ui_go_back();
        }
        return;
    }
    
    if (s_mode == VIEW_BROWSER) {
        if (now - last_nav > 150) {
            if (y < -30 && s_selected < s_track_count - 1) {
                s_selected++;
                if (s_selected >= s_scroll + 4) s_scroll++;
                last_nav = now;
            } else if (y > 30 && s_selected > 0) {
                s_selected--;
                if (s_selected < s_scroll) s_scroll--;
                last_nav = now;
            }
        }
        
        if (buttons & UI_BTN_PRESS) {
            if (s_track_count > 0) {
                start_playback(s_selected);
                s_mode = VIEW_PLAYING;
            }
        }
        
    } else if (s_mode == VIEW_PLAYING) {
        if (now - last_nav > 150) {
            /* Volume control */
            if (y > 30 && s_volume < 100) {
                s_volume += 5;
                last_nav = now;
            } else if (y < -30 && s_volume > 0) {
                s_volume -= 5;
                last_nav = now;
            }
            
            /* Track skip */
            if (x > 30) {
                next_track();
                last_nav = now;
            } else if (x < -30) {
                prev_track();
                last_nav = now;
            }
        }
        
        if (buttons & UI_BTN_PRESS) {
            music_toggle();
        }
        
        if (buttons & UI_BTN_LONG) {
            stop_playback();
            s_mode = VIEW_BROWSER;
        }
    }
}

static void on_render(void)
{
    int y = UI_STATUS_BAR_HEIGHT + 2;
    
    if (s_mode == VIEW_BROWSER) {
        display_draw_string(2, y, "Music", COLOR_WHITE, 1);
        display_printf(50, y, COLOR_WHITE, 1, "(%d)", s_track_count);
        display_draw_hline(0, y + 9, DISPLAY_WIDTH, COLOR_WHITE);
        y += 12;
        
        if (s_track_count == 0) {
            display_draw_string(2, y, "No music found", COLOR_WHITE, 1);
            display_draw_string(2, y + 12, "Add to /music/", COLOR_WHITE, 1);
        } else {
            int visible = (DISPLAY_HEIGHT - y) / 12;
            
            for (int i = 0; i < visible && (s_scroll + i) < s_track_count; i++) {
                int idx = s_scroll + i;
                int item_y = y + i * 12;
                
                /* Now playing indicator */
                const char *prefix = (idx == s_current_track && s_playing) ? ">" : " ";
                
                if (idx == s_selected) {
                    display_fill_rect(0, item_y, DISPLAY_WIDTH, 11, COLOR_WHITE);
                    display_printf(2, item_y + 1, COLOR_BLACK, 1, "%s%.16s", 
                                  prefix, s_tracks[idx].title);
                } else {
                    display_printf(2, item_y + 1, COLOR_WHITE, 1, "%s%.16s", 
                                  prefix, s_tracks[idx].title);
                }
            }
        }
        
    } else if (s_mode == VIEW_PLAYING) {
        /* Now Playing screen */
        if (s_current_track >= 0 && s_current_track < s_track_count) {
            track_t *t = &s_tracks[s_current_track];
            
            /* Title (centered, larger) */
            int title_len = strlen(t->title);
            if (title_len > 16) title_len = 16;
            int title_x = (DISPLAY_WIDTH - title_len * 6) / 2;
            display_draw_string(title_x, y, t->title, COLOR_WHITE, 1);
            y += 12;
            
            /* Artist */
            int artist_len = strlen(t->artist);
            if (artist_len > 20) artist_len = 20;
            int artist_x = (DISPLAY_WIDTH - artist_len * 6) / 2;
            display_draw_string(artist_x, y, t->artist, COLOR_WHITE, 1);
            y += 14;
            
            /* Progress bar */
            display_draw_progress(10, y, DISPLAY_WIDTH - 20, 6, 
                                 t->duration_sec > 0 ? (s_position_sec * 100 / t->duration_sec) : 0);
            y += 10;
            
            /* Time display */
            uint32_t pos_min = s_position_sec / 60;
            uint32_t pos_sec = s_position_sec % 60;
            uint32_t dur_min = t->duration_sec / 60;
            uint32_t dur_sec = t->duration_sec % 60;
            display_printf(10, y, COLOR_WHITE, 1, "%d:%02d", pos_min, pos_sec);
            display_printf(90, y, COLOR_WHITE, 1, "%d:%02d", dur_min, dur_sec);
            y += 12;
            
            /* Play/Pause indicator */
            const char *state = s_playing ? "||" : ">";
            int state_x = (DISPLAY_WIDTH - 12) / 2;
            display_draw_string(state_x, y, state, COLOR_WHITE, 1);
            
            /* Volume bar at bottom */
            display_printf(2, DISPLAY_HEIGHT - 10, COLOR_WHITE, 1, "Vol:%d%%", s_volume);
            display_draw_progress(50, DISPLAY_HEIGHT - 10, 60, 6, s_volume);
        }
    }
}

static void on_tick(uint32_t dt_ms)
{
    static uint32_t accum = 0;
    
    if (s_playing) {
        accum += dt_ms;
        if (accum >= 1000) {
            s_position_sec++;
            accum -= 1000;
            
            /* Check for end of track */
            if (s_current_track >= 0 && s_current_track < s_track_count) {
                track_t *t = &s_tracks[s_current_track];
                if (t->duration_sec > 0 && s_position_sec >= t->duration_sec) {
                    next_track();
                }
            }
        }
    }
}

/* ============================================================================
 * App Definition
 * ============================================================================ */

const ui_app_t app_music = {
    .id = "music",
    .name = "Music",
    .icon = ICON_MUSIC,
    .on_enter = on_enter,
    .on_exit = on_exit,
    .on_input = on_input,
    .on_render = on_render,
    .on_tick = on_tick,
};

