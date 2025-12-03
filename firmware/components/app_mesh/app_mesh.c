/**
 * @file app_mesh.c
 * @brief Mesh Messaging App Implementation
 */

#include "app_mesh.h"
#include "ui.h"
#include "display.h"
#include "mesh_client.h"
#include "sprites.h"
#include "esp_log.h"
#include "esp_timer.h"
#include <string.h>

static const char *TAG = "mesh_app";

/* ============================================================================
 * Configuration
 * ============================================================================ */

#define MAX_CONVERSATIONS 16
#define MAX_MESSAGES 32
#define MSG_DISPLAY_LEN 18

/* ============================================================================
 * Types
 * ============================================================================ */

typedef struct {
    char node_id[MESH_NODE_ID_LEN];
    char name[32];
    int unread;
    uint32_t last_time;
} conversation_t;

typedef struct {
    char from_id[MESH_NODE_ID_LEN];
    char from_name[32];
    char text[MESH_MSG_MAX_LEN];
    uint32_t timestamp;
    bool is_outgoing;
} message_t;

typedef enum {
    VIEW_CONVERSATIONS,
    VIEW_THREAD,
    VIEW_COMPOSE,
    VIEW_NODES,
} view_mode_t;

/* ============================================================================
 * State
 * ============================================================================ */

static view_mode_t s_mode = VIEW_CONVERSATIONS;
static conversation_t s_convos[MAX_CONVERSATIONS];
static int s_convo_count = 0;
static int s_selected = 0;
static int s_scroll = 0;

static message_t s_messages[MAX_MESSAGES];
static int s_msg_count = 0;
static int s_msg_scroll = 0;

static char s_compose_buffer[MESH_MSG_MAX_LEN];
static size_t s_compose_len = 0;
static char s_compose_to[MESH_NODE_ID_LEN] = "^all";

/* ============================================================================
 * Helpers
 * ============================================================================ */

static conversation_t *find_conversation(const char *node_id)
{
    for (int i = 0; i < s_convo_count; i++) {
        if (strcmp(s_convos[i].node_id, node_id) == 0) {
            return &s_convos[i];
        }
    }
    return NULL;
}

static conversation_t *add_conversation(const char *node_id, const char *name)
{
    if (s_convo_count >= MAX_CONVERSATIONS) return NULL;
    
    conversation_t *c = &s_convos[s_convo_count++];
    strncpy(c->node_id, node_id, MESH_NODE_ID_LEN - 1);
    strncpy(c->name, name, sizeof(c->name) - 1);
    c->unread = 0;
    c->last_time = esp_timer_get_time() / 1000;
    
    return c;
}

static void add_message(const char *from_id, const char *from_name, 
                        const char *text, bool is_outgoing)
{
    if (s_msg_count >= MAX_MESSAGES) {
        /* Shift messages to make room */
        memmove(&s_messages[0], &s_messages[1], sizeof(message_t) * (MAX_MESSAGES - 1));
        s_msg_count = MAX_MESSAGES - 1;
    }
    
    message_t *m = &s_messages[s_msg_count++];
    strncpy(m->from_id, from_id, MESH_NODE_ID_LEN - 1);
    strncpy(m->from_name, from_name, sizeof(m->from_name) - 1);
    strncpy(m->text, text, MESH_MSG_MAX_LEN - 1);
    m->timestamp = esp_timer_get_time() / 1000;
    m->is_outgoing = is_outgoing;
}

static void load_thread(const char *node_id)
{
    /* TODO: Load from SD storage */
    s_msg_count = 0;
    s_msg_scroll = 0;
    
    /* Load all messages with this contact */
    /* For now, filter from memory */
}

static void on_compose_done(const char *text, bool confirmed)
{
    if (confirmed && text && text[0] != '\0') {
        strncpy(s_compose_buffer, text, MESH_MSG_MAX_LEN - 1);
        s_compose_len = strlen(s_compose_buffer);
        
        /* Send the message */
        bool is_broadcast = (strcmp(s_compose_to, "^all") == 0);
        esp_err_t err;
        
        if (is_broadcast) {
            err = mesh_client_broadcast(s_compose_buffer, 0);
        } else {
            err = mesh_client_send(s_compose_to, s_compose_buffer, 0, true);
        }
        
        if (err == ESP_OK) {
            add_message("me", "Me", s_compose_buffer, true);
            ui_notify_simple("Message sent");
        } else {
            ui_notify_simple("Send failed");
        }
        
        s_compose_buffer[0] = '\0';
        s_compose_len = 0;
    }
    
    s_mode = VIEW_THREAD;
}

/* ============================================================================
 * App Callbacks
 * ============================================================================ */

static void on_enter(void)
{
    ESP_LOGI(TAG, "Mesh app entered");
    s_mode = VIEW_CONVERSATIONS;
    s_selected = 0;
    s_scroll = 0;
    
    /* Add broadcast as first "conversation" */
    if (s_convo_count == 0) {
        conversation_t *c = add_conversation("^all", "Broadcast");
        if (c) c->unread = 0;
    }
}

static void on_exit(void)
{
    ESP_LOGI(TAG, "Mesh app exited");
}

static void on_input(int8_t x, int8_t y, uint8_t buttons)
{
    static uint32_t last_nav = 0;
    uint32_t now = esp_timer_get_time() / 1000;
    
    if (buttons & UI_BTN_BACK) {
        if (s_mode == VIEW_COMPOSE) {
            s_mode = VIEW_THREAD;
        } else if (s_mode == VIEW_THREAD || s_mode == VIEW_NODES) {
            s_mode = VIEW_CONVERSATIONS;
        } else {
            ui_go_back();
        }
        return;
    }
    
    switch (s_mode) {
    case VIEW_CONVERSATIONS:
        if (now - last_nav > 150) {
            if (y < -30 && s_selected < s_convo_count - 1) {
                s_selected++;
                last_nav = now;
            } else if (y > 30 && s_selected > 0) {
                s_selected--;
                last_nav = now;
            }
        }
        
        if (buttons & UI_BTN_PRESS) {
            if (s_convo_count > 0) {
                strncpy(s_compose_to, s_convos[s_selected].node_id, MESH_NODE_ID_LEN);
                s_convos[s_selected].unread = 0;
                load_thread(s_compose_to);
                s_mode = VIEW_THREAD;
            }
        }
        
        if (buttons & UI_BTN_LONG) {
            s_mode = VIEW_NODES;
            s_selected = 0;
        }
        break;
        
    case VIEW_THREAD:
        if (now - last_nav > 150) {
            if (y < -30 && s_msg_scroll < s_msg_count - 4) {
                s_msg_scroll++;
                last_nav = now;
            } else if (y > 30 && s_msg_scroll > 0) {
                s_msg_scroll--;
                last_nav = now;
            }
        }
        
        if (buttons & UI_BTN_PRESS) {
            /* Open compose */
            ui_osk_config_t osk = {
                .title = "Message:",
                .initial_text = "",
                .max_length = MESH_MSG_MAX_LEN - 1,
                .password_mode = false,
                .callback = on_compose_done,
            };
            ui_show_osk(&osk);
        }
        break;
        
    case VIEW_NODES:
        /* TODO: Show discovered nodes */
        if (buttons & UI_BTN_PRESS) {
            s_mode = VIEW_CONVERSATIONS;
        }
        break;
        
    default:
        break;
    }
}

static void on_render(void)
{
    int y = UI_STATUS_BAR_HEIGHT + 2;
    
    switch (s_mode) {
    case VIEW_CONVERSATIONS:
        display_draw_string(2, y, "Messages", COLOR_WHITE, 1);
        display_printf(70, y, COLOR_WHITE, 1, "(%d)", s_convo_count);
        display_draw_hline(0, y + 9, DISPLAY_WIDTH, COLOR_WHITE);
        y += 12;
        
        if (s_convo_count == 0) {
            display_draw_string(2, y, "No messages", COLOR_WHITE, 1);
            display_draw_string(2, y + 12, "Long: Nodes", COLOR_WHITE, 1);
        } else {
            int visible = (DISPLAY_HEIGHT - y) / 12;
            
            for (int i = 0; i < visible && (s_scroll + i) < s_convo_count; i++) {
                int idx = s_scroll + i;
                int item_y = y + i * 12;
                
                if (idx == s_selected) {
                    display_fill_rect(0, item_y, DISPLAY_WIDTH, 11, COLOR_WHITE);
                    display_draw_string(2, item_y + 1, s_convos[idx].name, COLOR_BLACK, 1);
                    if (s_convos[idx].unread > 0) {
                        display_printf(100, item_y + 1, COLOR_BLACK, 1, "[%d]", s_convos[idx].unread);
                    }
                } else {
                    display_draw_string(2, item_y + 1, s_convos[idx].name, COLOR_WHITE, 1);
                    if (s_convos[idx].unread > 0) {
                        display_printf(100, item_y + 1, COLOR_WHITE, 1, "[%d]", s_convos[idx].unread);
                    }
                }
            }
        }
        break;
        
    case VIEW_THREAD:
        {
            /* Header with recipient name */
            const char *name = "Broadcast";
            for (int i = 0; i < s_convo_count; i++) {
                if (strcmp(s_convos[i].node_id, s_compose_to) == 0) {
                    name = s_convos[i].name;
                    break;
                }
            }
            display_draw_string(2, y, name, COLOR_WHITE, 1);
            display_draw_hline(0, y + 9, DISPLAY_WIDTH, COLOR_WHITE);
            y += 12;
            
            if (s_msg_count == 0) {
                display_draw_string(2, y, "No messages", COLOR_WHITE, 1);
                display_draw_string(2, y + 12, "Press: Compose", COLOR_WHITE, 1);
            } else {
                int visible = (DISPLAY_HEIGHT - y) / 12;
                
                for (int i = 0; i < visible && (s_msg_scroll + i) < s_msg_count; i++) {
                    int idx = s_msg_scroll + i;
                    int item_y = y + i * 12;
                    
                    /* Direction indicator */
                    const char *prefix = s_messages[idx].is_outgoing ? ">" : "<";
                    display_draw_string(2, item_y, prefix, COLOR_WHITE, 1);
                    
                    /* Message text (truncated) */
                    char buf[MSG_DISPLAY_LEN + 1];
                    strncpy(buf, s_messages[idx].text, MSG_DISPLAY_LEN);
                    buf[MSG_DISPLAY_LEN] = '\0';
                    display_draw_string(10, item_y, buf, COLOR_WHITE, 1);
                }
            }
        }
        break;
        
    case VIEW_NODES:
        display_draw_string(2, y, "Nodes", COLOR_WHITE, 1);
        display_draw_hline(0, y + 9, DISPLAY_WIDTH, COLOR_WHITE);
        y += 12;
        
        display_draw_string(2, y, "Scanning...", COLOR_WHITE, 1);
        display_draw_string(2, y + 12, "Press: Back", COLOR_WHITE, 1);
        break;
        
    default:
        break;
    }
}

static void on_tick(uint32_t dt_ms)
{
    (void)dt_ms;
    /* Handled by mesh_client callbacks in main */
}

/* ============================================================================
 * Message Callback (called from main)
 * ============================================================================ */

void app_mesh_on_message(const mesh_message_t *msg)
{
    if (!msg) return;
    
    /* Find or create conversation */
    conversation_t *c = find_conversation(msg->from_id);
    if (!c) {
        c = add_conversation(msg->from_id, msg->from_name);
    }
    
    if (c) {
        c->unread++;
        c->last_time = esp_timer_get_time() / 1000;
        strncpy(c->name, msg->from_name, sizeof(c->name) - 1);
    }
    
    /* Add to messages if viewing this thread */
    if (strcmp(s_compose_to, msg->from_id) == 0) {
        add_message(msg->from_id, msg->from_name, msg->message, false);
    }
}

/* ============================================================================
 * App Definition
 * ============================================================================ */

const ui_app_t app_mesh = {
    .id = "mesh",
    .name = "Messages",
    .icon = ICON_MESH,
    .on_enter = on_enter,
    .on_exit = on_exit,
    .on_input = on_input,
    .on_render = on_render,
    .on_tick = on_tick,
};

