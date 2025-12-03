/**
 * @file app_translate.c
 * @brief Translation App Implementation
 * 
 * Uses WiFi to connect to translation APIs (LibreTranslate, DeepL, or Google)
 */

#include "app_translate.h"
#include "ui.h"
#include "display.h"
#include "sprites.h"
#include "esp_log.h"
#include "esp_timer.h"
#include <string.h>

static const char *TAG = "translate";

/* ============================================================================
 * Configuration
 * ============================================================================ */

#define MAX_INPUT_LEN 128
#define MAX_OUTPUT_LEN 256
#define MAX_HISTORY 10

/* ============================================================================
 * Languages
 * ============================================================================ */

typedef struct {
    const char *code;
    const char *name;
} language_t;

static const language_t languages[] = {
    {"en", "English"},
    {"es", "Spanish"},
    {"fr", "French"},
    {"de", "German"},
    {"it", "Italian"},
    {"pt", "Portuguese"},
    {"ja", "Japanese"},
    {"ko", "Korean"},
    {"zh", "Chinese"},
    {"ru", "Russian"},
    {"ar", "Arabic"},
};
#define NUM_LANGUAGES (sizeof(languages) / sizeof(languages[0]))

/* ============================================================================
 * State
 * ============================================================================ */

typedef enum {
    VIEW_MAIN,
    VIEW_SELECT_SRC,
    VIEW_SELECT_DST,
    VIEW_TRANSLATING,
    VIEW_RESULT,
    VIEW_HISTORY,
} view_mode_t;

typedef struct {
    char input[MAX_INPUT_LEN];
    char output[MAX_OUTPUT_LEN];
    int src_lang;
    int dst_lang;
} history_entry_t;

static view_mode_t s_mode = VIEW_MAIN;
static int s_src_lang = 0;  /* English */
static int s_dst_lang = 1;  /* Spanish */
static char s_input[MAX_INPUT_LEN] = "";
static char s_output[MAX_OUTPUT_LEN] = "";
static bool s_translating = false;
static int s_selected = 0;

static history_entry_t s_history[MAX_HISTORY];
static int s_history_count = 0;

/* ============================================================================
 * Translation
 * ============================================================================ */

static void on_input_done(const char *text, bool confirmed)
{
    if (confirmed && text && text[0] != '\0') {
        strncpy(s_input, text, MAX_INPUT_LEN - 1);
        s_mode = VIEW_TRANSLATING;
        s_translating = true;
        
        /* TODO: Make HTTP request to translation API */
        /* For now, simulate with placeholder */
    }
}

static void do_translation(void)
{
    /* TODO: Implement actual HTTP request to translation API
     * 
     * Example with LibreTranslate:
     * POST https://libretranslate.com/translate
     * {
     *   "q": s_input,
     *   "source": languages[s_src_lang].code,
     *   "target": languages[s_dst_lang].code
     * }
     */
    
    /* Simulate translation for now */
    snprintf(s_output, MAX_OUTPUT_LEN, "[%s->%s] %s", 
             languages[s_src_lang].code,
             languages[s_dst_lang].code,
             s_input);
    
    s_translating = false;
    s_mode = VIEW_RESULT;
    
    /* Add to history */
    if (s_history_count < MAX_HISTORY) {
        history_entry_t *h = &s_history[s_history_count++];
        strncpy(h->input, s_input, MAX_INPUT_LEN - 1);
        strncpy(h->output, s_output, MAX_OUTPUT_LEN - 1);
        h->src_lang = s_src_lang;
        h->dst_lang = s_dst_lang;
    }
}

static void swap_languages(void)
{
    int tmp = s_src_lang;
    s_src_lang = s_dst_lang;
    s_dst_lang = tmp;
}

/* ============================================================================
 * App Callbacks
 * ============================================================================ */

static void on_enter(void)
{
    ESP_LOGI(TAG, "Translate app entered");
    s_mode = VIEW_MAIN;
    s_input[0] = '\0';
    s_output[0] = '\0';
}

static void on_exit(void)
{
    ESP_LOGI(TAG, "Translate app exited");
}

static void on_input(int8_t x, int8_t y, uint8_t buttons)
{
    static uint32_t last_nav = 0;
    uint32_t now = esp_timer_get_time() / 1000;
    
    if (buttons & UI_BTN_BACK) {
        if (s_mode != VIEW_MAIN) {
            s_mode = VIEW_MAIN;
        } else {
            ui_go_back();
        }
        return;
    }
    
    switch (s_mode) {
    case VIEW_MAIN:
        if (now - last_nav > 150) {
            if (y < -30 && s_selected < 3) {
                s_selected++;
                last_nav = now;
            } else if (y > 30 && s_selected > 0) {
                s_selected--;
                last_nav = now;
            }
        }
        
        if (buttons & UI_BTN_PRESS) {
            switch (s_selected) {
            case 0:  /* Source language */
                s_mode = VIEW_SELECT_SRC;
                s_selected = s_src_lang;
                break;
            case 1:  /* Target language */
                s_mode = VIEW_SELECT_DST;
                s_selected = s_dst_lang;
                break;
            case 2:  /* Input text */
                {
                    ui_osk_config_t osk = {
                        .title = "Enter text:",
                        .initial_text = s_input,
                        .max_length = MAX_INPUT_LEN - 1,
                        .password_mode = false,
                        .callback = on_input_done,
                    };
                    ui_show_osk(&osk);
                }
                break;
            case 3:  /* History */
                s_mode = VIEW_HISTORY;
                s_selected = 0;
                break;
            }
        }
        
        if (buttons & UI_BTN_LONG) {
            swap_languages();
        }
        break;
        
    case VIEW_SELECT_SRC:
    case VIEW_SELECT_DST:
        if (now - last_nav > 150) {
            if (y < -30 && s_selected < (int)NUM_LANGUAGES - 1) {
                s_selected++;
                last_nav = now;
            } else if (y > 30 && s_selected > 0) {
                s_selected--;
                last_nav = now;
            }
        }
        
        if (buttons & UI_BTN_PRESS) {
            if (s_mode == VIEW_SELECT_SRC) {
                s_src_lang = s_selected;
            } else {
                s_dst_lang = s_selected;
            }
            s_mode = VIEW_MAIN;
            s_selected = 0;
        }
        break;
        
    case VIEW_TRANSLATING:
        /* Cannot interrupt */
        break;
        
    case VIEW_RESULT:
        if (buttons & UI_BTN_PRESS) {
            s_mode = VIEW_MAIN;
            s_selected = 2;  /* Back to input */
        }
        break;
        
    case VIEW_HISTORY:
        if (now - last_nav > 150) {
            if (y < -30 && s_selected < s_history_count - 1) {
                s_selected++;
                last_nav = now;
            } else if (y > 30 && s_selected > 0) {
                s_selected--;
                last_nav = now;
            }
        }
        
        if (buttons & UI_BTN_PRESS) {
            if (s_history_count > 0) {
                history_entry_t *h = &s_history[s_selected];
                strncpy(s_input, h->input, MAX_INPUT_LEN);
                strncpy(s_output, h->output, MAX_OUTPUT_LEN);
                s_src_lang = h->src_lang;
                s_dst_lang = h->dst_lang;
                s_mode = VIEW_RESULT;
            }
        }
        break;
    }
}

static void on_render(void)
{
    int y = UI_STATUS_BAR_HEIGHT + 2;
    
    switch (s_mode) {
    case VIEW_MAIN:
        display_draw_string(2, y, "Translate", COLOR_WHITE, 1);
        display_draw_hline(0, y + 9, DISPLAY_WIDTH, COLOR_WHITE);
        y += 12;
        
        /* Source language */
        if (s_selected == 0) {
            display_fill_rect(0, y, DISPLAY_WIDTH, 10, COLOR_WHITE);
            display_printf(2, y + 1, COLOR_BLACK, 1, "From: %s", languages[s_src_lang].name);
        } else {
            display_printf(2, y + 1, COLOR_WHITE, 1, "From: %s", languages[s_src_lang].name);
        }
        y += 11;
        
        /* Target language */
        if (s_selected == 1) {
            display_fill_rect(0, y, DISPLAY_WIDTH, 10, COLOR_WHITE);
            display_printf(2, y + 1, COLOR_BLACK, 1, "To: %s", languages[s_dst_lang].name);
        } else {
            display_printf(2, y + 1, COLOR_WHITE, 1, "To: %s", languages[s_dst_lang].name);
        }
        y += 11;
        
        /* Input text */
        if (s_selected == 2) {
            display_fill_rect(0, y, DISPLAY_WIDTH, 10, COLOR_WHITE);
            if (s_input[0]) {
                display_printf(2, y + 1, COLOR_BLACK, 1, "\"%.16s\"", s_input);
            } else {
                display_draw_string(2, y + 1, "[Enter text]", COLOR_BLACK, 1);
            }
        } else {
            if (s_input[0]) {
                display_printf(2, y + 1, COLOR_WHITE, 1, "\"%.16s\"", s_input);
            } else {
                display_draw_string(2, y + 1, "[Enter text]", COLOR_WHITE, 1);
            }
        }
        y += 11;
        
        /* History */
        if (s_selected == 3) {
            display_fill_rect(0, y, DISPLAY_WIDTH, 10, COLOR_WHITE);
            display_printf(2, y + 1, COLOR_BLACK, 1, "History (%d)", s_history_count);
        } else {
            display_printf(2, y + 1, COLOR_WHITE, 1, "History (%d)", s_history_count);
        }
        
        display_draw_string(2, DISPLAY_HEIGHT - 10, "Hold: Swap langs", COLOR_WHITE, 1);
        break;
        
    case VIEW_SELECT_SRC:
    case VIEW_SELECT_DST:
        display_printf(2, y, COLOR_WHITE, 1, "Select %s", s_mode == VIEW_SELECT_SRC ? "source" : "target");
        display_draw_hline(0, y + 9, DISPLAY_WIDTH, COLOR_WHITE);
        y += 12;
        
        for (int i = 0; i < 5 && i < (int)NUM_LANGUAGES; i++) {
            int idx = i;  /* TODO: scroll offset */
            int item_y = y + i * 10;
            
            if (idx == s_selected) {
                display_fill_rect(0, item_y, DISPLAY_WIDTH, 10, COLOR_WHITE);
                display_draw_string(2, item_y + 1, languages[idx].name, COLOR_BLACK, 1);
            } else {
                display_draw_string(2, item_y + 1, languages[idx].name, COLOR_WHITE, 1);
            }
        }
        break;
        
    case VIEW_TRANSLATING:
        display_draw_string(30, 25, "Translating", COLOR_WHITE, 1);
        display_draw_string(45, 40, "...", COLOR_WHITE, 1);
        break;
        
    case VIEW_RESULT:
        display_draw_string(2, y, "Result", COLOR_WHITE, 1);
        display_draw_hline(0, y + 9, DISPLAY_WIDTH, COLOR_WHITE);
        y += 12;
        
        /* Input */
        display_printf(2, y, COLOR_WHITE, 1, "%s:", languages[s_src_lang].code);
        y += 10;
        display_printf(2, y, COLOR_WHITE, 1, "%.20s", s_input);
        y += 12;
        
        /* Output */
        display_printf(2, y, COLOR_WHITE, 1, "%s:", languages[s_dst_lang].code);
        y += 10;
        
        /* Word wrap output */
        int chars_per_line = 20;
        for (int i = 0; i < 3 && s_output[i * chars_per_line]; i++) {
            char line[21];
            strncpy(line, &s_output[i * chars_per_line], 20);
            line[20] = '\0';
            display_draw_string(2, y + i * 9, line, COLOR_WHITE, 1);
        }
        break;
        
    case VIEW_HISTORY:
        display_draw_string(2, y, "History", COLOR_WHITE, 1);
        display_draw_hline(0, y + 9, DISPLAY_WIDTH, COLOR_WHITE);
        y += 12;
        
        if (s_history_count == 0) {
            display_draw_string(2, y, "No history", COLOR_WHITE, 1);
        } else {
            for (int i = 0; i < 4 && i < s_history_count; i++) {
                int item_y = y + i * 12;
                history_entry_t *h = &s_history[i];
                
                if (i == s_selected) {
                    display_fill_rect(0, item_y, DISPLAY_WIDTH, 11, COLOR_WHITE);
                    display_printf(2, item_y + 1, COLOR_BLACK, 1, "%.18s", h->input);
                } else {
                    display_printf(2, item_y + 1, COLOR_WHITE, 1, "%.18s", h->input);
                }
            }
        }
        break;
    }
}

static void on_tick(uint32_t dt_ms)
{
    if (s_translating) {
        static uint32_t accum = 0;
        accum += dt_ms;
        
        /* Simulate translation delay */
        if (accum >= 1000) {
            accum = 0;
            do_translation();
        }
    }
}

/* ============================================================================
 * App Definition
 * ============================================================================ */

const ui_app_t app_translate = {
    .id = "translate",
    .name = "Translate",
    .icon = ICON_TRANSLATE,
    .on_enter = on_enter,
    .on_exit = on_exit,
    .on_input = on_input,
    .on_render = on_render,
    .on_tick = on_tick,
};

