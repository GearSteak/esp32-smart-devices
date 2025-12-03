/**
 * @file app_notes.c
 * @brief Notes App Implementation
 */

#include "app_notes.h"
#include "ui.h"
#include "display.h"
#include "esp_log.h"
#include <string.h>
#include <stdio.h>
#include <dirent.h>
#include <sys/stat.h>

static const char *TAG = "notes";

/* ============================================================================
 * Configuration
 * ============================================================================ */

#define NOTES_DIR "/sdcard/notes"
#define MAX_NOTES 32
#define MAX_NOTE_SIZE 2048
#define MAX_LINES 256
#define LINE_HEIGHT 10

/* ============================================================================
 * State
 * ============================================================================ */

typedef enum {
    VIEW_LIST,
    VIEW_EDIT,
} view_mode_t;

typedef struct {
    char filename[32];
} note_entry_t;

static view_mode_t s_mode = VIEW_LIST;
static note_entry_t s_notes[MAX_NOTES];
static int s_note_count = 0;
static int s_selected = 0;
static int s_scroll = 0;

/* Editor state */
static char s_buffer[MAX_NOTE_SIZE];
static size_t s_buffer_len = 0;
static int s_cursor = 0;
static int s_cursor_line = 0;
static int s_cursor_col = 0;
static int s_view_scroll = 0;
static char s_current_file[64] = "";

/* ============================================================================
 * File Operations
 * ============================================================================ */

static void ensure_notes_dir(void)
{
    struct stat st;
    if (stat(NOTES_DIR, &st) != 0) {
        mkdir(NOTES_DIR, 0755);
        ESP_LOGI(TAG, "Created notes directory");
    }
}

static void scan_notes(void)
{
    s_note_count = 0;
    ensure_notes_dir();
    
    DIR *dir = opendir(NOTES_DIR);
    if (!dir) {
        ESP_LOGW(TAG, "Cannot open notes directory");
        return;
    }
    
    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL && s_note_count < MAX_NOTES) {
        if (entry->d_name[0] == '.') continue;
        
        size_t len = strlen(entry->d_name);
        if (len > 4 && strcmp(entry->d_name + len - 4, ".txt") == 0) {
            strncpy(s_notes[s_note_count].filename, entry->d_name, 31);
            s_notes[s_note_count].filename[31] = '\0';
            s_note_count++;
        }
    }
    
    closedir(dir);
    ESP_LOGI(TAG, "Found %d notes", s_note_count);
}

static bool load_note(const char *filename)
{
    char path[96];
    snprintf(path, sizeof(path), "%s/%s", NOTES_DIR, filename);
    
    FILE *f = fopen(path, "r");
    if (!f) {
        ESP_LOGW(TAG, "Cannot open: %s", path);
        return false;
    }
    
    s_buffer_len = fread(s_buffer, 1, MAX_NOTE_SIZE - 1, f);
    s_buffer[s_buffer_len] = '\0';
    fclose(f);
    
    strncpy(s_current_file, filename, sizeof(s_current_file) - 1);
    s_cursor = 0;
    s_cursor_line = 0;
    s_cursor_col = 0;
    s_view_scroll = 0;
    
    ESP_LOGI(TAG, "Loaded: %s (%d bytes)", filename, (int)s_buffer_len);
    return true;
}

static bool save_note(void)
{
    if (s_current_file[0] == '\0') return false;
    
    char path[96];
    snprintf(path, sizeof(path), "%s/%s", NOTES_DIR, s_current_file);
    
    FILE *f = fopen(path, "w");
    if (!f) {
        ESP_LOGW(TAG, "Cannot save: %s", path);
        return false;
    }
    
    fwrite(s_buffer, 1, s_buffer_len, f);
    fclose(f);
    
    ESP_LOGI(TAG, "Saved: %s", s_current_file);
    return true;
}

static void create_new_note(const char *name)
{
    if (!name || name[0] == '\0') return;
    
    snprintf(s_current_file, sizeof(s_current_file), "%s.txt", name);
    s_buffer[0] = '\0';
    s_buffer_len = 0;
    s_cursor = 0;
    s_cursor_line = 0;
    s_cursor_col = 0;
    s_view_scroll = 0;
    s_mode = VIEW_EDIT;
    
    save_note();  /* Create empty file */
    scan_notes();
}

static void delete_note(const char *filename)
{
    char path[96];
    snprintf(path, sizeof(path), "%s/%s", NOTES_DIR, filename);
    
    if (remove(path) == 0) {
        ESP_LOGI(TAG, "Deleted: %s", filename);
        scan_notes();
        if (s_selected >= s_note_count) {
            s_selected = s_note_count > 0 ? s_note_count - 1 : 0;
        }
    }
}

/* ============================================================================
 * Cursor Management
 * ============================================================================ */

static void update_cursor_position(void)
{
    /* Calculate line and column from buffer position */
    s_cursor_line = 0;
    s_cursor_col = 0;
    
    for (int i = 0; i < s_cursor && i < (int)s_buffer_len; i++) {
        if (s_buffer[i] == '\n') {
            s_cursor_line++;
            s_cursor_col = 0;
        } else {
            s_cursor_col++;
        }
    }
}

static int get_line_start(int line)
{
    int pos = 0;
    int current_line = 0;
    
    while (pos < (int)s_buffer_len && current_line < line) {
        if (s_buffer[pos] == '\n') current_line++;
        pos++;
    }
    
    return pos;
}

static int get_line_length(int line)
{
    int start = get_line_start(line);
    int len = 0;
    
    while (start + len < (int)s_buffer_len && s_buffer[start + len] != '\n') {
        len++;
    }
    
    return len;
}

static void cursor_up(void)
{
    if (s_cursor_line > 0) {
        int target_line = s_cursor_line - 1;
        int line_len = get_line_length(target_line);
        int new_col = s_cursor_col < line_len ? s_cursor_col : line_len;
        s_cursor = get_line_start(target_line) + new_col;
        update_cursor_position();
    }
}

static void cursor_down(void)
{
    int target_line = s_cursor_line + 1;
    int line_start = get_line_start(target_line);
    
    if (line_start <= (int)s_buffer_len) {
        int line_len = get_line_length(target_line);
        int new_col = s_cursor_col < line_len ? s_cursor_col : line_len;
        s_cursor = line_start + new_col;
        if (s_cursor > (int)s_buffer_len) s_cursor = s_buffer_len;
        update_cursor_position();
    }
}

static void cursor_left(void)
{
    if (s_cursor > 0) {
        s_cursor--;
        update_cursor_position();
    }
}

static void cursor_right(void)
{
    if (s_cursor < (int)s_buffer_len) {
        s_cursor++;
        update_cursor_position();
    }
}

/* ============================================================================
 * Text Editing
 * ============================================================================ */

static void insert_char(char c)
{
    if (s_buffer_len >= MAX_NOTE_SIZE - 1) return;
    
    /* Shift text right */
    memmove(&s_buffer[s_cursor + 1], &s_buffer[s_cursor], s_buffer_len - s_cursor);
    s_buffer[s_cursor] = c;
    s_buffer_len++;
    s_buffer[s_buffer_len] = '\0';
    s_cursor++;
    update_cursor_position();
}

static void delete_char(void)
{
    if (s_cursor > 0 && s_buffer_len > 0) {
        s_cursor--;
        memmove(&s_buffer[s_cursor], &s_buffer[s_cursor + 1], s_buffer_len - s_cursor);
        s_buffer_len--;
        s_buffer[s_buffer_len] = '\0';
        update_cursor_position();
    }
}

/* ============================================================================
 * OSK Callback
 * ============================================================================ */

static void on_new_note_name(const char *text, bool confirmed)
{
    if (confirmed && text && text[0] != '\0') {
        create_new_note(text);
    }
}

/* ============================================================================
 * App Callbacks
 * ============================================================================ */

static void on_enter(void)
{
    ESP_LOGI(TAG, "Notes app entered");
    s_mode = VIEW_LIST;
    s_selected = 0;
    s_scroll = 0;
    scan_notes();
}

static void on_exit(void)
{
    ESP_LOGI(TAG, "Notes app exited");
    if (s_mode == VIEW_EDIT && s_current_file[0] != '\0') {
        save_note();
    }
}

static void on_input(int8_t x, int8_t y, uint8_t buttons)
{
    static uint32_t last_nav = 0;
    uint32_t now = esp_timer_get_time() / 1000;
    
    if (buttons & UI_BTN_BACK) {
        if (s_mode == VIEW_EDIT) {
            save_note();
            s_mode = VIEW_LIST;
            scan_notes();
        } else {
            ui_go_back();
        }
        return;
    }
    
    if (s_mode == VIEW_LIST) {
        /* List navigation */
        if (now - last_nav > 150) {
            if (y < -30 && s_selected < s_note_count - 1) {
                s_selected++;
                last_nav = now;
            } else if (y > 30 && s_selected > 0) {
                s_selected--;
                last_nav = now;
            }
        }
        
        if (buttons & UI_BTN_PRESS) {
            if (s_note_count > 0) {
                if (load_note(s_notes[s_selected].filename)) {
                    s_mode = VIEW_EDIT;
                }
            }
        }
        
        if (buttons & UI_BTN_LONG) {
            /* Create new note */
            ui_osk_config_t osk = {
                .title = "Note name:",
                .initial_text = "",
                .max_length = 20,
                .password_mode = false,
                .callback = on_new_note_name,
            };
            ui_show_osk(&osk);
        }
        
        if (buttons & UI_BTN_DOUBLE) {
            /* Delete selected */
            if (s_note_count > 0) {
                delete_note(s_notes[s_selected].filename);
            }
        }
        
    } else {
        /* Editor navigation/input */
        if (now - last_nav > 80) {
            if (y < -30) { cursor_down(); last_nav = now; }
            else if (y > 30) { cursor_up(); last_nav = now; }
            else if (x < -30) { cursor_left(); last_nav = now; }
            else if (x > 30) { cursor_right(); last_nav = now; }
        }
        
        if (buttons & UI_BTN_PRESS) {
            /* Open OSK for character input */
            ui_osk_config_t osk = {
                .title = "Type:",
                .initial_text = "",
                .max_length = 1,
                .password_mode = false,
                .callback = NULL,  /* TODO: single-char OSK mode */
            };
            /* For now, insert space on press */
            insert_char(' ');
        }
        
        if (buttons & UI_BTN_DOUBLE) {
            delete_char();
        }
        
        if (buttons & UI_BTN_LONG) {
            insert_char('\n');
        }
        
        /* Update scroll to keep cursor visible */
        int visible_lines = (DISPLAY_HEIGHT - UI_STATUS_BAR_HEIGHT - 14) / LINE_HEIGHT;
        if (s_cursor_line < s_view_scroll) {
            s_view_scroll = s_cursor_line;
        } else if (s_cursor_line >= s_view_scroll + visible_lines) {
            s_view_scroll = s_cursor_line - visible_lines + 1;
        }
    }
}

static void on_render(void)
{
    int y = UI_STATUS_BAR_HEIGHT + 2;
    
    if (s_mode == VIEW_LIST) {
        /* Title */
        display_draw_string(2, y, "Notes", COLOR_WHITE, 1);
        display_printf(80, y, COLOR_WHITE, 1, "(%d)", s_note_count);
        display_draw_hline(0, y + 9, DISPLAY_WIDTH, COLOR_WHITE);
        y += 12;
        
        if (s_note_count == 0) {
            display_draw_string(2, y, "No notes", COLOR_WHITE, 1);
            display_draw_string(2, y + 12, "Long press: New", COLOR_WHITE, 1);
        } else {
            int visible = (DISPLAY_HEIGHT - y) / LINE_HEIGHT;
            
            for (int i = 0; i < visible && (s_scroll + i) < s_note_count; i++) {
                int idx = s_scroll + i;
                int item_y = y + i * LINE_HEIGHT;
                
                /* Truncate filename (remove .txt) */
                char name[20];
                strncpy(name, s_notes[idx].filename, 16);
                name[16] = '\0';
                size_t len = strlen(name);
                if (len > 4) name[len - 4] = '\0';  /* Remove .txt */
                
                if (idx == s_selected) {
                    display_fill_rect(0, item_y, DISPLAY_WIDTH, LINE_HEIGHT, COLOR_WHITE);
                    display_draw_string(2, item_y + 1, name, COLOR_BLACK, 1);
                } else {
                    display_draw_string(2, item_y + 1, name, COLOR_WHITE, 1);
                }
            }
        }
        
    } else {
        /* Editor view */
        /* Title bar */
        char title[24];
        strncpy(title, s_current_file, 16);
        title[16] = '\0';
        size_t len = strlen(title);
        if (len > 4) title[len - 4] = '\0';
        display_draw_string(2, y, title, COLOR_WHITE, 1);
        display_printf(80, y, COLOR_WHITE, 1, "L%d", s_cursor_line + 1);
        display_draw_hline(0, y + 9, DISPLAY_WIDTH, COLOR_WHITE);
        y += 12;
        
        /* Text content */
        int visible_lines = (DISPLAY_HEIGHT - y) / LINE_HEIGHT;
        int line = 0;
        int pos = 0;
        int line_start = 0;
        
        /* Skip to scroll position */
        while (line < s_view_scroll && pos < (int)s_buffer_len) {
            if (s_buffer[pos] == '\n') {
                line++;
            }
            pos++;
        }
        line_start = pos;
        
        /* Render visible lines */
        for (int v = 0; v < visible_lines && pos <= (int)s_buffer_len; v++) {
            int line_y = y + v * LINE_HEIGHT;
            int col = 0;
            line_start = pos;
            
            while (pos < (int)s_buffer_len && s_buffer[pos] != '\n') {
                if (col < 21) {  /* Max chars per line */
                    char c = s_buffer[pos];
                    display_draw_char(2 + col * 6, line_y, c, COLOR_WHITE, 1);
                    
                    /* Draw cursor */
                    if (pos == s_cursor) {
                        display_draw_vline(2 + col * 6, line_y, 8, COLOR_INVERSE);
                    }
                }
                col++;
                pos++;
            }
            
            /* Cursor at end of line */
            if (pos == s_cursor && col < 21) {
                display_draw_vline(2 + col * 6, line_y, 8, COLOR_WHITE);
            }
            
            if (pos < (int)s_buffer_len) pos++;  /* Skip newline */
            line++;
        }
    }
}

static void on_tick(uint32_t dt_ms)
{
    (void)dt_ms;
}

/* ============================================================================
 * App Definition
 * ============================================================================ */

#include "sprites.h"

const ui_app_t app_notes = {
    .id = "notes",
    .name = "Notes",
    .icon = ICON_NOTES,
    .on_enter = on_enter,
    .on_exit = on_exit,
    .on_input = on_input,
    .on_render = on_render,
    .on_tick = on_tick,
};

