/**
 * @file app_email.c
 * @brief Text-Only Email Client Implementation
 * 
 * Basic IMAP/SMTP client for text-only email
 * - Plain text only (no HTML)
 * - Fetches one message at a time (memory limited)
 * - Simple compose with on-screen keyboard
 */

#include "app_email.h"
#include "ui.h"
#include "display.h"
#include "sprites.h"
#include "esp_log.h"
#include "esp_timer.h"
#include <string.h>

static const char *TAG = "email";

/* ============================================================================
 * Configuration
 * ============================================================================ */

#define MAX_EMAILS 20
#define MAX_SUBJECT_LEN 64
#define MAX_BODY_LEN 512
#define MAX_ADDR_LEN 64

/* ============================================================================
 * Types
 * ============================================================================ */

typedef struct {
    char from[MAX_ADDR_LEN];
    char subject[MAX_SUBJECT_LEN];
    char date[20];
    bool read;
} email_header_t;

typedef struct {
    email_header_t header;
    char body[MAX_BODY_LEN];
} email_t;

typedef enum {
    VIEW_SETUP,
    VIEW_INBOX,
    VIEW_READ,
    VIEW_COMPOSE,
} view_mode_t;

/* ============================================================================
 * State
 * ============================================================================ */

static view_mode_t s_mode = VIEW_SETUP;
static email_header_t s_inbox[MAX_EMAILS];
static int s_inbox_count = 0;
static int s_selected = 0;
static int s_scroll = 0;
static email_t s_current = {0};

/* Account config */
static bool s_configured = false;
static char s_email_addr[MAX_ADDR_LEN] = "";
static char s_imap_server[64] = "";
static char s_smtp_server[64] = "";

/* Compose state */
static char s_compose_to[MAX_ADDR_LEN] = "";
static char s_compose_subject[MAX_SUBJECT_LEN] = "";
static char s_compose_body[MAX_BODY_LEN] = "";
static int s_compose_field = 0;

/* Loading state */
static bool s_loading = false;

/* ============================================================================
 * Email Operations (Stubs)
 * ============================================================================ */

static void load_config(void)
{
    /* TODO: Load from NVS */
    s_configured = false;
}

static void fetch_inbox(void)
{
    if (!s_configured) return;
    
    s_loading = true;
    /* TODO: Connect to IMAP server and fetch headers
     * 
     * Basic IMAP sequence:
     * 1. Connect to IMAP server (SSL port 993)
     * 2. LOGIN user password
     * 3. SELECT INBOX
     * 4. FETCH 1:20 (FLAGS BODY[HEADER.FIELDS (FROM SUBJECT DATE)])
     * 5. Parse responses
     */
    
    /* Stub: Add demo emails */
    s_inbox_count = 2;
    strcpy(s_inbox[0].from, "test@example.com");
    strcpy(s_inbox[0].subject, "Welcome!");
    strcpy(s_inbox[0].date, "Nov 30");
    s_inbox[0].read = false;
    
    strcpy(s_inbox[1].from, "news@update.com");
    strcpy(s_inbox[1].subject, "Daily Update");
    strcpy(s_inbox[1].date, "Nov 29");
    s_inbox[1].read = true;
    
    s_loading = false;
}

static void fetch_email(int idx)
{
    if (idx < 0 || idx >= s_inbox_count) return;
    
    s_loading = true;
    
    /* TODO: FETCH idx+1 BODY[TEXT] */
    
    /* Stub */
    memcpy(&s_current.header, &s_inbox[idx], sizeof(email_header_t));
    strcpy(s_current.body, "This is a sample email body.\n\nHello from the ESP32!");
    
    s_inbox[idx].read = true;
    s_loading = false;
}

static void send_email(void)
{
    if (!s_configured) {
        ui_notify_simple("Not configured");
        return;
    }
    
    /* TODO: Connect to SMTP server and send
     * 
     * Basic SMTP sequence:
     * 1. Connect to SMTP server (SSL port 465 or STARTTLS 587)
     * 2. EHLO
     * 3. AUTH LOGIN
     * 4. MAIL FROM:<addr>
     * 5. RCPT TO:<addr>
     * 6. DATA
     * 7. Send headers and body
     * 8. .
     * 9. QUIT
     */
    
    ESP_LOGI(TAG, "Sending to: %s", s_compose_to);
    ui_notify_simple("Email sent!");
    
    /* Clear compose */
    s_compose_to[0] = '\0';
    s_compose_subject[0] = '\0';
    s_compose_body[0] = '\0';
}

/* ============================================================================
 * OSK Callbacks
 * ============================================================================ */

static void on_to_done(const char *text, bool confirmed)
{
    if (confirmed && text) {
        strncpy(s_compose_to, text, MAX_ADDR_LEN - 1);
    }
}

static void on_subject_done(const char *text, bool confirmed)
{
    if (confirmed && text) {
        strncpy(s_compose_subject, text, MAX_SUBJECT_LEN - 1);
    }
}

static void on_body_done(const char *text, bool confirmed)
{
    if (confirmed && text) {
        strncpy(s_compose_body, text, MAX_BODY_LEN - 1);
    }
}

static void on_email_done(const char *text, bool confirmed)
{
    if (confirmed && text) {
        strncpy(s_email_addr, text, MAX_ADDR_LEN - 1);
    }
}

/* ============================================================================
 * App Callbacks
 * ============================================================================ */

static void on_enter(void)
{
    ESP_LOGI(TAG, "Email app entered");
    load_config();
    
    if (s_configured) {
        s_mode = VIEW_INBOX;
        fetch_inbox();
    } else {
        s_mode = VIEW_SETUP;
    }
}

static void on_exit(void)
{
    ESP_LOGI(TAG, "Email app exited");
}

static void on_input(int8_t x, int8_t y, uint8_t buttons)
{
    static uint32_t last_nav = 0;
    uint32_t now = esp_timer_get_time() / 1000;
    
    if (s_loading) return;
    
    if (buttons & UI_BTN_BACK) {
        switch (s_mode) {
        case VIEW_READ:
            s_mode = VIEW_INBOX;
            break;
        case VIEW_COMPOSE:
            s_mode = VIEW_INBOX;
            break;
        case VIEW_INBOX:
        case VIEW_SETUP:
            ui_go_back();
            break;
        }
        return;
    }
    
    switch (s_mode) {
    case VIEW_SETUP:
        if (buttons & UI_BTN_PRESS) {
            ui_osk_config_t osk = {
                .title = "Email address:",
                .initial_text = s_email_addr,
                .max_length = MAX_ADDR_LEN - 1,
                .password_mode = false,
                .callback = on_email_done,
            };
            ui_show_osk(&osk);
        }
        
        if (buttons & UI_BTN_LONG) {
            /* Demo mode - skip config */
            s_configured = true;
            s_mode = VIEW_INBOX;
            fetch_inbox();
        }
        break;
        
    case VIEW_INBOX:
        if (now - last_nav > 150) {
            if (y < -30 && s_selected < s_inbox_count - 1) {
                s_selected++;
                last_nav = now;
            } else if (y > 30 && s_selected > 0) {
                s_selected--;
                last_nav = now;
            }
        }
        
        if (buttons & UI_BTN_PRESS) {
            if (s_inbox_count > 0) {
                fetch_email(s_selected);
                s_mode = VIEW_READ;
            }
        }
        
        if (buttons & UI_BTN_LONG) {
            s_mode = VIEW_COMPOSE;
            s_compose_field = 0;
        }
        
        if (buttons & UI_BTN_DOUBLE) {
            fetch_inbox();
        }
        break;
        
    case VIEW_READ:
        /* Scroll body */
        if (now - last_nav > 150) {
            if (y < -30) {
                s_scroll++;
                last_nav = now;
            } else if (y > 30 && s_scroll > 0) {
                s_scroll--;
                last_nav = now;
            }
        }
        
        if (buttons & UI_BTN_LONG) {
            /* Reply */
            snprintf(s_compose_to, MAX_ADDR_LEN, "%s", s_current.header.from);
            snprintf(s_compose_subject, MAX_SUBJECT_LEN, "Re: %s", s_current.header.subject);
            s_compose_body[0] = '\0';
            s_mode = VIEW_COMPOSE;
            s_compose_field = 2;  /* Jump to body */
        }
        break;
        
    case VIEW_COMPOSE:
        if (now - last_nav > 150) {
            if (y < -30 && s_compose_field < 3) {
                s_compose_field++;
                last_nav = now;
            } else if (y > 30 && s_compose_field > 0) {
                s_compose_field--;
                last_nav = now;
            }
        }
        
        if (buttons & UI_BTN_PRESS) {
            ui_osk_config_t osk = {0};
            
            switch (s_compose_field) {
            case 0:
                osk.title = "To:";
                osk.initial_text = s_compose_to;
                osk.max_length = MAX_ADDR_LEN - 1;
                osk.callback = on_to_done;
                break;
            case 1:
                osk.title = "Subject:";
                osk.initial_text = s_compose_subject;
                osk.max_length = MAX_SUBJECT_LEN - 1;
                osk.callback = on_subject_done;
                break;
            case 2:
                osk.title = "Body:";
                osk.initial_text = s_compose_body;
                osk.max_length = MAX_BODY_LEN - 1;
                osk.callback = on_body_done;
                break;
            case 3:
                send_email();
                s_mode = VIEW_INBOX;
                return;
            }
            
            ui_show_osk(&osk);
        }
        break;
    }
}

static void on_render(void)
{
    int y = UI_STATUS_BAR_HEIGHT + 2;
    
    if (s_loading) {
        display_draw_string(40, 30, "Loading...", COLOR_WHITE, 1);
        return;
    }
    
    switch (s_mode) {
    case VIEW_SETUP:
        display_draw_string(2, y, "Email Setup", COLOR_WHITE, 1);
        display_draw_hline(0, y + 9, DISPLAY_WIDTH, COLOR_WHITE);
        y += 14;
        
        display_draw_string(2, y, "Not configured", COLOR_WHITE, 1);
        y += 12;
        display_draw_string(2, y, "Press: Setup", COLOR_WHITE, 1);
        y += 12;
        display_draw_string(2, y, "Hold: Demo mode", COLOR_WHITE, 1);
        break;
        
    case VIEW_INBOX:
        display_draw_string(2, y, "Inbox", COLOR_WHITE, 1);
        display_printf(50, y, COLOR_WHITE, 1, "(%d)", s_inbox_count);
        display_draw_hline(0, y + 9, DISPLAY_WIDTH, COLOR_WHITE);
        y += 12;
        
        if (s_inbox_count == 0) {
            display_draw_string(2, y, "No emails", COLOR_WHITE, 1);
            display_draw_string(2, y + 12, "Double: Refresh", COLOR_WHITE, 1);
        } else {
            int visible = (DISPLAY_HEIGHT - y) / 12;
            
            for (int i = 0; i < visible && i < s_inbox_count; i++) {
                int item_y = y + i * 12;
                email_header_t *h = &s_inbox[i];
                
                /* Unread indicator */
                const char *indicator = h->read ? " " : "*";
                
                if (i == s_selected) {
                    display_fill_rect(0, item_y, DISPLAY_WIDTH, 11, COLOR_WHITE);
                    display_printf(2, item_y + 1, COLOR_BLACK, 1, "%s%.16s", indicator, h->subject);
                } else {
                    display_printf(2, item_y + 1, COLOR_WHITE, 1, "%s%.16s", indicator, h->subject);
                }
            }
        }
        break;
        
    case VIEW_READ:
        /* Header */
        display_printf(2, y, COLOR_WHITE, 1, "From: %.14s", s_current.header.from);
        y += 10;
        display_printf(2, y, COLOR_WHITE, 1, "Subj: %.14s", s_current.header.subject);
        y += 10;
        display_draw_hline(0, y, DISPLAY_WIDTH, COLOR_WHITE);
        y += 2;
        
        /* Body (scrollable) */
        int chars_per_line = 20;
        int lines_visible = (DISPLAY_HEIGHT - y) / 9;
        
        for (int i = 0; i < lines_visible; i++) {
            int line_idx = s_scroll + i;
            int offset = line_idx * chars_per_line;
            
            if (offset >= (int)strlen(s_current.body)) break;
            
            char line[21];
            strncpy(line, &s_current.body[offset], 20);
            line[20] = '\0';
            display_draw_string(2, y + i * 9, line, COLOR_WHITE, 1);
        }
        break;
        
    case VIEW_COMPOSE:
        display_draw_string(2, y, "Compose", COLOR_WHITE, 1);
        display_draw_hline(0, y + 9, DISPLAY_WIDTH, COLOR_WHITE);
        y += 12;
        
        /* To field */
        if (s_compose_field == 0) {
            display_fill_rect(0, y, DISPLAY_WIDTH, 10, COLOR_WHITE);
            display_printf(2, y + 1, COLOR_BLACK, 1, "To: %.16s", s_compose_to[0] ? s_compose_to : "...");
        } else {
            display_printf(2, y + 1, COLOR_WHITE, 1, "To: %.16s", s_compose_to[0] ? s_compose_to : "...");
        }
        y += 11;
        
        /* Subject */
        if (s_compose_field == 1) {
            display_fill_rect(0, y, DISPLAY_WIDTH, 10, COLOR_WHITE);
            display_printf(2, y + 1, COLOR_BLACK, 1, "Subj: %.14s", s_compose_subject[0] ? s_compose_subject : "...");
        } else {
            display_printf(2, y + 1, COLOR_WHITE, 1, "Subj: %.14s", s_compose_subject[0] ? s_compose_subject : "...");
        }
        y += 11;
        
        /* Body preview */
        if (s_compose_field == 2) {
            display_fill_rect(0, y, DISPLAY_WIDTH, 10, COLOR_WHITE);
            display_printf(2, y + 1, COLOR_BLACK, 1, "Body: %.14s", s_compose_body[0] ? s_compose_body : "...");
        } else {
            display_printf(2, y + 1, COLOR_WHITE, 1, "Body: %.14s", s_compose_body[0] ? s_compose_body : "...");
        }
        y += 11;
        
        /* Send button */
        if (s_compose_field == 3) {
            display_fill_rect(40, y, 48, 12, COLOR_WHITE);
            display_draw_string(50, y + 2, "SEND", COLOR_BLACK, 1);
        } else {
            display_draw_rect(40, y, 48, 12, COLOR_WHITE);
            display_draw_string(50, y + 2, "SEND", COLOR_WHITE, 1);
        }
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

const ui_app_t app_email = {
    .id = "email",
    .name = "Email",
    .icon = ICON_EMAIL,
    .on_enter = on_enter,
    .on_exit = on_exit,
    .on_input = on_input,
    .on_render = on_render,
    .on_tick = on_tick,
};

