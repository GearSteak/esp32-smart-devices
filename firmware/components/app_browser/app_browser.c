/**
 * @file app_browser.c
 * @brief Text-Only Web Browser Implementation
 * 
 * Minimal text-mode web browser:
 * - HTTP GET requests (HTTPS if memory allows)
 * - HTML stripped to plain text
 * - Basic link detection
 * - Bookmarks stored on SD
 */

#include "app_browser.h"
#include "ui.h"
#include "display.h"
#include "sprites.h"
#include "esp_log.h"
#include "esp_timer.h"
#include <string.h>
#include <stdio.h>

static const char *TAG = "browser";

/* ============================================================================
 * Configuration
 * ============================================================================ */

#define MAX_URL_LEN 128
#define MAX_PAGE_LEN 4096
#define MAX_LINKS 20
#define MAX_BOOKMARKS 10

/* ============================================================================
 * Types
 * ============================================================================ */

typedef struct {
    char text[32];
    char url[MAX_URL_LEN];
} link_t;

typedef struct {
    char title[32];
    char url[MAX_URL_LEN];
} bookmark_t;

typedef enum {
    VIEW_HOME,
    VIEW_LOADING,
    VIEW_PAGE,
    VIEW_BOOKMARKS,
} view_mode_t;

/* ============================================================================
 * State
 * ============================================================================ */

static view_mode_t s_mode = VIEW_HOME;
static char s_url[MAX_URL_LEN] = "";
static char s_page_title[64] = "";
static char s_page_text[MAX_PAGE_LEN] = "";
static int s_page_len = 0;

static link_t s_links[MAX_LINKS];
static int s_link_count = 0;
static int s_selected_link = 0;

static bookmark_t s_bookmarks[MAX_BOOKMARKS];
static int s_bookmark_count = 0;

static int s_scroll = 0;
static bool s_loading = false;

/* History for back button */
static char s_history[10][MAX_URL_LEN];
static int s_history_count = 0;

/* ============================================================================
 * HTML Parser (Very Basic)
 * ============================================================================ */

static void strip_html_to_text(const char *html, size_t html_len)
{
    /* Very basic HTML to text conversion:
     * - Remove all tags
     * - Decode basic entities (&amp; &lt; &gt; &nbsp;)
     * - Extract link hrefs
     */
    
    s_page_len = 0;
    s_link_count = 0;
    s_page_title[0] = '\0';
    
    bool in_tag = false;
    bool in_script = false;
    bool in_style = false;
    int text_pos = 0;
    
    for (size_t i = 0; i < html_len && text_pos < MAX_PAGE_LEN - 1; i++) {
        char c = html[i];
        
        if (c == '<') {
            in_tag = true;
            
            /* Check for script/style tags */
            if (i + 7 < html_len) {
                if (strncasecmp(&html[i], "<script", 7) == 0) in_script = true;
                if (strncasecmp(&html[i], "<style", 6) == 0) in_style = true;
            }
            if (i + 8 < html_len) {
                if (strncasecmp(&html[i], "</script", 8) == 0) in_script = false;
                if (strncasecmp(&html[i], "</style", 7) == 0) in_style = false;
            }
            
            /* Check for <a href="..."> */
            if (i + 9 < html_len && strncasecmp(&html[i], "<a href=\"", 9) == 0 && s_link_count < MAX_LINKS) {
                size_t href_start = i + 9;
                size_t href_end = href_start;
                while (href_end < html_len && html[href_end] != '"') href_end++;
                
                if (href_end - href_start < MAX_URL_LEN) {
                    strncpy(s_links[s_link_count].url, &html[href_start], href_end - href_start);
                    s_links[s_link_count].url[href_end - href_start] = '\0';
                    s_links[s_link_count].text[0] = '\0';
                    s_link_count++;
                }
            }
            
            continue;
        }
        
        if (c == '>') {
            in_tag = false;
            continue;
        }
        
        if (in_tag || in_script || in_style) continue;
        
        /* Handle entities */
        if (c == '&') {
            if (strncmp(&html[i], "&amp;", 5) == 0) { c = '&'; i += 4; }
            else if (strncmp(&html[i], "&lt;", 4) == 0) { c = '<'; i += 3; }
            else if (strncmp(&html[i], "&gt;", 4) == 0) { c = '>'; i += 3; }
            else if (strncmp(&html[i], "&nbsp;", 6) == 0) { c = ' '; i += 5; }
            else if (strncmp(&html[i], "&quot;", 6) == 0) { c = '"'; i += 5; }
        }
        
        /* Normalize whitespace */
        if (c == '\r' || c == '\n' || c == '\t') c = ' ';
        
        /* Skip multiple spaces */
        if (c == ' ' && text_pos > 0 && s_page_text[text_pos - 1] == ' ') continue;
        
        s_page_text[text_pos++] = c;
    }
    
    s_page_text[text_pos] = '\0';
    s_page_len = text_pos;
    
    /* Extract title if present in first 200 chars */
    const char *title_start = strstr(s_page_text, "<title>");
    if (!title_start) {
        /* Use URL as title */
        strncpy(s_page_title, s_url, 63);
    }
}

/* ============================================================================
 * Network Operations (Stubs)
 * ============================================================================ */

static void fetch_url(const char *url)
{
    ESP_LOGI(TAG, "Fetching: %s", url);
    
    /* Add to history */
    if (s_url[0] != '\0' && s_history_count < 10) {
        strcpy(s_history[s_history_count++], s_url);
    }
    
    strncpy(s_url, url, MAX_URL_LEN - 1);
    s_loading = true;
    s_scroll = 0;
    s_selected_link = 0;
    
    /* TODO: Implement actual HTTP GET request
     * 
     * esp_http_client_config_t config = {
     *     .url = url,
     *     .method = HTTP_METHOD_GET,
     * };
     * esp_http_client_handle_t client = esp_http_client_init(&config);
     * esp_http_client_perform(client);
     * // Read response...
     * esp_http_client_cleanup(client);
     */
    
    /* Stub response */
    const char *demo_html = 
        "<html><head><title>Demo Page</title></head>"
        "<body>"
        "<h1>Welcome to ESP32 Browser!</h1>"
        "<p>This is a demonstration page. The browser strips HTML to text.</p>"
        "<p>Links: <a href=\"http://example.com\">Example</a> "
        "<a href=\"http://esp32.com\">ESP32</a></p>"
        "<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>"
        "</body></html>";
    
    strip_html_to_text(demo_html, strlen(demo_html));
    strcpy(s_page_title, "Demo Page");
    
    s_loading = false;
    s_mode = VIEW_PAGE;
}

static void go_back(void)
{
    if (s_history_count > 0) {
        s_history_count--;
        fetch_url(s_history[s_history_count]);
        s_history_count--;  /* Don't add to history again */
    }
}

static void add_bookmark(void)
{
    if (s_bookmark_count >= MAX_BOOKMARKS) return;
    if (s_url[0] == '\0') return;
    
    bookmark_t *b = &s_bookmarks[s_bookmark_count++];
    strncpy(b->url, s_url, MAX_URL_LEN - 1);
    strncpy(b->title, s_page_title, 31);
    
    ui_notify_simple("Bookmarked!");
}

/* ============================================================================
 * OSK Callback
 * ============================================================================ */

static void on_url_entered(const char *text, bool confirmed)
{
    if (confirmed && text && text[0] != '\0') {
        /* Add http:// if missing */
        char full_url[MAX_URL_LEN];
        if (strncmp(text, "http://", 7) != 0 && strncmp(text, "https://", 8) != 0) {
            snprintf(full_url, MAX_URL_LEN, "http://%s", text);
        } else {
            strncpy(full_url, text, MAX_URL_LEN - 1);
        }
        fetch_url(full_url);
    }
}

/* ============================================================================
 * App Callbacks
 * ============================================================================ */

static void on_enter(void)
{
    ESP_LOGI(TAG, "Browser app entered");
    
    if (s_url[0] != '\0') {
        s_mode = VIEW_PAGE;
    } else {
        s_mode = VIEW_HOME;
    }
    
    /* Load bookmarks from SD */
    /* TODO: Load from /sdcard/bookmarks.txt */
    if (s_bookmark_count == 0) {
        strcpy(s_bookmarks[0].title, "Example");
        strcpy(s_bookmarks[0].url, "http://example.com");
        s_bookmark_count = 1;
    }
}

static void on_exit(void)
{
    ESP_LOGI(TAG, "Browser app exited");
}

static void on_input(int8_t x, int8_t y, uint8_t buttons)
{
    static uint32_t last_nav = 0;
    uint32_t now = esp_timer_get_time() / 1000;
    
    if (s_loading) return;
    
    if (buttons & UI_BTN_BACK) {
        if (s_mode == VIEW_PAGE && s_history_count > 0) {
            go_back();
        } else if (s_mode == VIEW_BOOKMARKS) {
            s_mode = VIEW_HOME;
        } else {
            ui_go_back();
        }
        return;
    }
    
    switch (s_mode) {
    case VIEW_HOME:
        if (buttons & UI_BTN_PRESS) {
            ui_osk_config_t osk = {
                .title = "Enter URL:",
                .initial_text = "",
                .max_length = MAX_URL_LEN - 8,
                .password_mode = false,
                .callback = on_url_entered,
            };
            ui_show_osk(&osk);
        }
        
        if (buttons & UI_BTN_LONG) {
            s_mode = VIEW_BOOKMARKS;
            s_scroll = 0;
        }
        break;
        
    case VIEW_PAGE:
        if (now - last_nav > 100) {
            /* Scroll page */
            if (y < -30) {
                s_scroll++;
                last_nav = now;
            } else if (y > 30 && s_scroll > 0) {
                s_scroll--;
                last_nav = now;
            }
            
            /* Navigate links */
            if (x > 30 && s_selected_link < s_link_count - 1) {
                s_selected_link++;
                last_nav = now;
            } else if (x < -30 && s_selected_link > 0) {
                s_selected_link--;
                last_nav = now;
            }
        }
        
        if (buttons & UI_BTN_PRESS) {
            /* Follow selected link */
            if (s_link_count > 0) {
                fetch_url(s_links[s_selected_link].url);
            }
        }
        
        if (buttons & UI_BTN_LONG) {
            add_bookmark();
        }
        
        if (buttons & UI_BTN_DOUBLE) {
            /* New URL */
            ui_osk_config_t osk = {
                .title = "Enter URL:",
                .initial_text = s_url,
                .max_length = MAX_URL_LEN - 1,
                .password_mode = false,
                .callback = on_url_entered,
            };
            ui_show_osk(&osk);
        }
        break;
        
    case VIEW_BOOKMARKS:
        if (now - last_nav > 150) {
            if (y < -30 && s_scroll < s_bookmark_count - 1) {
                s_scroll++;
                last_nav = now;
            } else if (y > 30 && s_scroll > 0) {
                s_scroll--;
                last_nav = now;
            }
        }
        
        if (buttons & UI_BTN_PRESS) {
            if (s_bookmark_count > 0) {
                fetch_url(s_bookmarks[s_scroll].url);
            }
        }
        break;
        
    default:
        break;
    }
}

static void on_render(void)
{
    int y = UI_STATUS_BAR_HEIGHT + 2;
    
    if (s_loading) {
        display_draw_string(35, 30, "Loading...", COLOR_WHITE, 1);
        return;
    }
    
    switch (s_mode) {
    case VIEW_HOME:
        display_draw_string(2, y, "Browser", COLOR_WHITE, 1);
        display_draw_hline(0, y + 9, DISPLAY_WIDTH, COLOR_WHITE);
        y += 14;
        
        display_draw_string(2, y, "Press: Enter URL", COLOR_WHITE, 1);
        y += 12;
        display_draw_string(2, y, "Hold: Bookmarks", COLOR_WHITE, 1);
        y += 16;
        
        display_draw_string(2, y, "Text-only mode", COLOR_WHITE, 1);
        y += 10;
        display_draw_string(2, y, "No images/JS", COLOR_WHITE, 1);
        break;
        
    case VIEW_PAGE:
        /* URL bar */
        display_printf(2, y, COLOR_WHITE, 1, "%.20s", s_url);
        display_draw_hline(0, y + 9, DISPLAY_WIDTH, COLOR_WHITE);
        y += 11;
        
        /* Page content */
        int chars_per_line = 20;
        int lines_visible = (DISPLAY_HEIGHT - y) / 9;
        
        for (int i = 0; i < lines_visible; i++) {
            int line_idx = s_scroll + i;
            int offset = line_idx * chars_per_line;
            
            if (offset >= s_page_len) break;
            
            char line[21];
            strncpy(line, &s_page_text[offset], 20);
            line[20] = '\0';
            display_draw_string(2, y + i * 9, line, COLOR_WHITE, 1);
        }
        
        /* Link indicator at bottom */
        if (s_link_count > 0) {
            display_printf(2, DISPLAY_HEIGHT - 9, COLOR_WHITE, 1, 
                          "Link %d/%d: %.12s", 
                          s_selected_link + 1, s_link_count,
                          s_links[s_selected_link].url);
        }
        break;
        
    case VIEW_BOOKMARKS:
        display_draw_string(2, y, "Bookmarks", COLOR_WHITE, 1);
        display_draw_hline(0, y + 9, DISPLAY_WIDTH, COLOR_WHITE);
        y += 12;
        
        if (s_bookmark_count == 0) {
            display_draw_string(2, y, "No bookmarks", COLOR_WHITE, 1);
        } else {
            int visible = (DISPLAY_HEIGHT - y) / 12;
            
            for (int i = 0; i < visible && i < s_bookmark_count; i++) {
                int item_y = y + i * 12;
                
                if (i == s_scroll) {
                    display_fill_rect(0, item_y, DISPLAY_WIDTH, 11, COLOR_WHITE);
                    display_draw_string(2, item_y + 1, s_bookmarks[i].title, COLOR_BLACK, 1);
                } else {
                    display_draw_string(2, item_y + 1, s_bookmarks[i].title, COLOR_WHITE, 1);
                }
            }
        }
        break;
        
    default:
        break;
    }
}

static void on_tick(uint32_t dt_ms)
{
    (void)dt_ms;
}

/* ============================================================================
 * App Definition
 * ============================================================================ */

const ui_app_t app_browser = {
    .id = "browser",
    .name = "Web",
    .icon = ICON_BROWSER,
    .on_enter = on_enter,
    .on_exit = on_exit,
    .on_input = on_input,
    .on_render = on_render,
    .on_tick = on_tick,
};

