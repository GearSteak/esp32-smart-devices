/**
 * @file app_calendar.c
 * @brief Calendar App Implementation
 */

#include "app_calendar.h"
#include "ui.h"
#include "display.h"
#include "esp_log.h"
#include "esp_timer.h"
#include <string.h>
#include <stdio.h>
#include <time.h>

static const char *TAG = "calendar";

/* ============================================================================
 * Configuration
 * ============================================================================ */

#define MAX_EVENTS 20
#define EVENT_DIR "/sdcard/calendar"

/* ============================================================================
 * Types
 * ============================================================================ */

typedef struct {
    uint16_t year;
    uint8_t month;
    uint8_t day;
    uint8_t hour;
    uint8_t minute;
    char title[32];
    uint8_t reminder;  /* Minutes before (0, 5, 15, 60) */
} calendar_event_t;

typedef enum {
    VIEW_MONTH,
    VIEW_DAY,
    VIEW_EVENT,
} view_mode_t;

/* ============================================================================
 * State
 * ============================================================================ */

static view_mode_t s_mode = VIEW_MONTH;
static int s_year = 2025;
static int s_month = 1;
static int s_day = 1;
static int s_selected_day = 1;
static int s_cursor_x = 0;
static int s_cursor_y = 0;

static calendar_event_t s_events[MAX_EVENTS];
static int s_event_count = 0;
static int s_selected_event = 0;

/* ============================================================================
 * Date Utilities
 * ============================================================================ */

static int days_in_month(int year, int month)
{
    static const int days[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    int d = days[month - 1];
    
    if (month == 2 && (year % 4 == 0 && (year % 100 != 0 || year % 400 == 0))) {
        d = 29;  /* Leap year */
    }
    
    return d;
}

static int day_of_week(int year, int month, int day)
{
    /* Zeller's congruence */
    if (month < 3) {
        month += 12;
        year--;
    }
    
    int k = year % 100;
    int j = year / 100;
    int h = (day + (13 * (month + 1)) / 5 + k + k / 4 + j / 4 - 2 * j) % 7;
    
    return (h + 6) % 7;  /* 0 = Sunday */
}

static void get_current_date(void)
{
    /* Get time from system (TODO: sync with RTC/NTP) */
    const ui_status_t *status = ui_get_status();
    
    /* Default to system timer approximation */
    uint64_t now = esp_timer_get_time() / 1000000;  /* seconds */
    
    /* Basic epoch calculation (2025-01-01 base) */
    time_t t = now;
    struct tm *tm = localtime(&t);
    if (tm) {
        s_year = tm->tm_year + 1900;
        s_month = tm->tm_mon + 1;
        s_day = tm->tm_mday;
    }
}

/* ============================================================================
 * Event Management
 * ============================================================================ */

static int count_events_on_day(int year, int month, int day)
{
    int count = 0;
    for (int i = 0; i < s_event_count; i++) {
        if (s_events[i].year == year &&
            s_events[i].month == month &&
            s_events[i].day == day) {
            count++;
        }
    }
    return count;
}

static void load_events(void)
{
    /* TODO: Load from SD card JSON files */
    s_event_count = 0;
    
    /* Demo event */
    s_events[0] = (calendar_event_t){
        .year = 2025,
        .month = 1,
        .day = 15,
        .hour = 14,
        .minute = 0,
        .title = "Meeting",
        .reminder = 15,
    };
    s_event_count = 1;
}

static void create_event(void)
{
    if (s_event_count >= MAX_EVENTS) return;
    
    calendar_event_t *e = &s_events[s_event_count];
    e->year = s_year;
    e->month = s_month;
    e->day = s_selected_day;
    e->hour = 12;
    e->minute = 0;
    strcpy(e->title, "New Event");
    e->reminder = 15;
    
    s_event_count++;
    ESP_LOGI(TAG, "Created event on %d-%02d-%02d", e->year, e->month, e->day);
}

/* ============================================================================
 * App Callbacks
 * ============================================================================ */

static void on_enter(void)
{
    ESP_LOGI(TAG, "Calendar entered");
    get_current_date();
    s_selected_day = s_day;
    s_mode = VIEW_MONTH;
    load_events();
}

static void on_exit(void)
{
    ESP_LOGI(TAG, "Calendar exited");
}

static void on_input(int8_t x, int8_t y, uint8_t buttons)
{
    static uint32_t last_nav = 0;
    uint32_t now = esp_timer_get_time() / 1000;
    
    if (buttons & UI_BTN_BACK) {
        if (s_mode == VIEW_DAY) {
            s_mode = VIEW_MONTH;
        } else if (s_mode == VIEW_EVENT) {
            s_mode = VIEW_DAY;
        } else {
            ui_go_back();
        }
        return;
    }
    
    if (s_mode == VIEW_MONTH) {
        int dim = days_in_month(s_year, s_month);
        int first_dow = day_of_week(s_year, s_month, 1);
        
        if (now - last_nav > 150) {
            if (x > 30) {
                s_selected_day++;
                if (s_selected_day > dim) {
                    s_selected_day = 1;
                    s_month++;
                    if (s_month > 12) { s_month = 1; s_year++; }
                }
                last_nav = now;
            } else if (x < -30) {
                s_selected_day--;
                if (s_selected_day < 1) {
                    s_month--;
                    if (s_month < 1) { s_month = 12; s_year--; }
                    s_selected_day = days_in_month(s_year, s_month);
                }
                last_nav = now;
            } else if (y < -30) {
                s_selected_day += 7;
                if (s_selected_day > dim) s_selected_day = dim;
                last_nav = now;
            } else if (y > 30) {
                s_selected_day -= 7;
                if (s_selected_day < 1) s_selected_day = 1;
                last_nav = now;
            }
        }
        
        if (buttons & UI_BTN_PRESS) {
            s_mode = VIEW_DAY;
            s_selected_event = 0;
        }
        
        if (buttons & UI_BTN_LONG) {
            create_event();
        }
        
    } else if (s_mode == VIEW_DAY) {
        int day_events = count_events_on_day(s_year, s_month, s_selected_day);
        
        if (now - last_nav > 150) {
            if (y < -30 && s_selected_event < day_events - 1) {
                s_selected_event++;
                last_nav = now;
            } else if (y > 30 && s_selected_event > 0) {
                s_selected_event--;
                last_nav = now;
            }
        }
        
        if (buttons & UI_BTN_PRESS && day_events > 0) {
            s_mode = VIEW_EVENT;
        }
        
        if (buttons & UI_BTN_LONG) {
            create_event();
        }
    }
}

static void on_render(void)
{
    int y = UI_STATUS_BAR_HEIGHT + 2;
    static const char *months[] = {
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    };
    
    if (s_mode == VIEW_MONTH) {
        /* Month/Year header */
        display_printf(2, y, COLOR_WHITE, 1, "%s %d", months[s_month - 1], s_year);
        display_draw_hline(0, y + 9, DISPLAY_WIDTH, COLOR_WHITE);
        y += 12;
        
        /* Day of week headers */
        static const char *dow[] = {"S", "M", "T", "W", "T", "F", "S"};
        for (int i = 0; i < 7; i++) {
            display_draw_string(2 + i * 18, y, dow[i], COLOR_WHITE, 1);
        }
        y += 10;
        
        /* Calendar grid */
        int dim = days_in_month(s_year, s_month);
        int first_dow = day_of_week(s_year, s_month, 1);
        int cell_w = 18;
        int cell_h = 8;
        
        int row = 0;
        int col = first_dow;
        
        for (int d = 1; d <= dim; d++) {
            int cx = 2 + col * cell_w;
            int cy = y + row * cell_h;
            
            if (d == s_selected_day) {
                display_fill_rect(cx - 1, cy, cell_w - 2, cell_h, COLOR_WHITE);
                display_printf(cx, cy, COLOR_BLACK, 1, "%d", d);
            } else {
                display_printf(cx, cy, COLOR_WHITE, 1, "%d", d);
            }
            
            /* Event indicator */
            if (count_events_on_day(s_year, s_month, d) > 0) {
                display_draw_pixel(cx + 8, cy + 6, d == s_selected_day ? COLOR_BLACK : COLOR_WHITE);
            }
            
            col++;
            if (col > 6) {
                col = 0;
                row++;
            }
        }
        
    } else if (s_mode == VIEW_DAY) {
        /* Day header */
        display_printf(2, y, COLOR_WHITE, 1, "%s %d, %d", 
                      months[s_month - 1], s_selected_day, s_year);
        display_draw_hline(0, y + 9, DISPLAY_WIDTH, COLOR_WHITE);
        y += 12;
        
        /* Events list */
        int event_idx = 0;
        for (int i = 0; i < s_event_count; i++) {
            if (s_events[i].year == s_year &&
                s_events[i].month == s_month &&
                s_events[i].day == s_selected_day) {
                
                int ey = y + event_idx * 12;
                
                if (event_idx == s_selected_event) {
                    display_fill_rect(0, ey, DISPLAY_WIDTH, 11, COLOR_WHITE);
                    display_printf(2, ey + 1, COLOR_BLACK, 1, "%02d:%02d %s",
                                  s_events[i].hour, s_events[i].minute, s_events[i].title);
                } else {
                    display_printf(2, ey + 1, COLOR_WHITE, 1, "%02d:%02d %s",
                                  s_events[i].hour, s_events[i].minute, s_events[i].title);
                }
                
                event_idx++;
            }
        }
        
        if (event_idx == 0) {
            display_draw_string(2, y, "No events", COLOR_WHITE, 1);
            display_draw_string(2, y + 12, "Long press: New", COLOR_WHITE, 1);
        }
        
    } else if (s_mode == VIEW_EVENT) {
        /* Find selected event */
        int event_idx = 0;
        calendar_event_t *event = NULL;
        for (int i = 0; i < s_event_count; i++) {
            if (s_events[i].year == s_year &&
                s_events[i].month == s_month &&
                s_events[i].day == s_selected_day) {
                if (event_idx == s_selected_event) {
                    event = &s_events[i];
                    break;
                }
                event_idx++;
            }
        }
        
        if (event) {
            display_draw_string(2, y, event->title, COLOR_WHITE, 1);
            display_draw_hline(0, y + 9, DISPLAY_WIDTH, COLOR_WHITE);
            y += 12;
            
            display_printf(2, y, COLOR_WHITE, 1, "Date: %s %d, %d",
                          months[event->month - 1], event->day, event->year);
            y += 10;
            display_printf(2, y, COLOR_WHITE, 1, "Time: %02d:%02d",
                          event->hour, event->minute);
            y += 10;
            
            if (event->reminder > 0) {
                display_printf(2, y, COLOR_WHITE, 1, "Remind: %d min", event->reminder);
            }
        }
    }
}

static void on_tick(uint32_t dt_ms)
{
    /* Check for reminders */
    static uint32_t check_interval = 0;
    check_interval += dt_ms;
    
    if (check_interval >= 60000) {  /* Check every minute */
        check_interval = 0;
        
        const ui_status_t *status = ui_get_status();
        int now_hour = status->hour;
        int now_min = status->minute;
        
        for (int i = 0; i < s_event_count; i++) {
            if (s_events[i].reminder > 0) {
                int event_min = s_events[i].hour * 60 + s_events[i].minute;
                int now_total = now_hour * 60 + now_min;
                int reminder_at = event_min - s_events[i].reminder;
                
                if (now_total == reminder_at) {
                    ui_notification_t notif = {
                        .title = s_events[i].title,
                        .body = "Reminder",
                        .priority = UI_NOTIFY_HIGH,
                        .duration_ms = 10000,
                    };
                    ui_notify(&notif);
                }
            }
        }
    }
}

/* ============================================================================
 * App Definition
 * ============================================================================ */

#include "sprites.h"

const ui_app_t app_calendar = {
    .id = "calendar",
    .name = "Calendar",
    .icon = ICON_CALENDAR,
    .on_enter = on_enter,
    .on_exit = on_exit,
    .on_input = on_input,
    .on_render = on_render,
    .on_tick = on_tick,
};

