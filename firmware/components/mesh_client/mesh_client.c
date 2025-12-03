/**
 * @file mesh_client.c
 * @brief Meshtastic mesh network client implementation
 */

#include "mesh_client.h"
#include "esp_log.h"
#include "esp_event.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "freertos/queue.h"
#include <string.h>

static const char *TAG = "mesh_client";

/* Mesh Relay Service UUIDs */
#define MESH_RELAY_SERVICE_UUID         "4f9a0030-8c3f-4a0e-89a7-6d277cf9a000"
#define MESH_INBOX_CHAR_UUID            "4f9a0031-8c3f-4a0e-89a7-6d277cf9a000"
#define MESH_SEND_CHAR_UUID             "4f9a0032-8c3f-4a0e-89a7-6d277cf9a000"
#define MESH_STATUS_CHAR_UUID           "4f9a0033-8c3f-4a0e-89a7-6d277cf9a000"
#define MESH_NODE_LIST_CHAR_UUID        "4f9a0034-8c3f-4a0e-89a7-6d277cf9a000"

/* Message inbox buffer size */
#define MESH_INBOX_SIZE                 20

/* Internal state */
typedef struct {
    bool initialized;
    bool connected;
    
    /* Callbacks */
    mesh_inbox_cb_t inbox_cb;
    mesh_status_cb_t status_cb;
    mesh_send_complete_cb_t send_complete_cb;
    
    /* Cached status */
    mesh_status_t status;
    
    /* Node list cache */
    mesh_node_t nodes[MESH_MAX_NODES];
    size_t node_count;
    
    /* Message inbox (circular buffer) */
    mesh_message_t inbox[MESH_INBOX_SIZE];
    size_t inbox_head;
    size_t inbox_count;
    size_t unread_count;
    
    /* Sequence number for outgoing messages */
    uint32_t seq_counter;
    
    /* Synchronization */
    SemaphoreHandle_t mutex;
    
    /* BLE handles (populated when connected) */
    uint16_t conn_handle;
    uint16_t inbox_char_handle;
    uint16_t send_char_handle;
    uint16_t status_char_handle;
    uint16_t node_list_char_handle;
} mesh_client_state_t;

static mesh_client_state_t s_state = {0};

/* Forward declarations for CBOR parsing (simplified) */
static esp_err_t parse_mesh_message(const uint8_t *data, size_t len, mesh_message_t *msg);
static esp_err_t parse_mesh_status(const uint8_t *data, size_t len, mesh_status_t *status);
static esp_err_t parse_node_list(const uint8_t *data, size_t len, mesh_node_t *nodes, size_t max_nodes, size_t *count);
static esp_err_t encode_mesh_send(const char *to, const char *message, uint8_t channel, bool want_ack, uint32_t seq, uint8_t *out_buf, size_t *out_len);

/**
 * @brief Handle incoming MeshInbox notification
 */
static void handle_inbox_notification(const uint8_t *data, size_t len)
{
    mesh_message_t msg = {0};
    
    if (parse_mesh_message(data, len, &msg) != ESP_OK) {
        ESP_LOGW(TAG, "Failed to parse inbox message");
        return;
    }
    
    xSemaphoreTake(s_state.mutex, portMAX_DELAY);
    
    /* Store in circular buffer */
    size_t idx = (s_state.inbox_head + s_state.inbox_count) % MESH_INBOX_SIZE;
    if (s_state.inbox_count >= MESH_INBOX_SIZE) {
        /* Buffer full, overwrite oldest */
        s_state.inbox_head = (s_state.inbox_head + 1) % MESH_INBOX_SIZE;
    } else {
        s_state.inbox_count++;
    }
    memcpy(&s_state.inbox[idx], &msg, sizeof(mesh_message_t));
    s_state.unread_count++;
    
    xSemaphoreGive(s_state.mutex);
    
    ESP_LOGI(TAG, "Mesh message from %s: %.32s...", msg.from_name, msg.message);
    
    /* Notify callback */
    if (s_state.inbox_cb) {
        s_state.inbox_cb(&msg);
    }
}

/**
 * @brief Handle incoming MeshStatus notification
 */
static void handle_status_notification(const uint8_t *data, size_t len)
{
    mesh_status_t status = {0};
    
    if (parse_mesh_status(data, len, &status) != ESP_OK) {
        ESP_LOGW(TAG, "Failed to parse status update");
        return;
    }
    
    xSemaphoreTake(s_state.mutex, portMAX_DELAY);
    memcpy(&s_state.status, &status, sizeof(mesh_status_t));
    s_state.connected = status.radio_on;
    xSemaphoreGive(s_state.mutex);
    
    ESP_LOGD(TAG, "Mesh status: radio=%d nodes=%d", status.radio_on, status.nodes_heard);
    
    /* Notify callback */
    if (s_state.status_cb) {
        s_state.status_cb(&status);
    }
}

/**
 * @brief BLE GATT notification callback (to be connected to BLE stack)
 * 
 * This is a stub that should be connected to your BLE GATT client
 * notification handler in control_link or a dedicated BLE module.
 */
void mesh_client_on_notification(uint16_t char_handle, const uint8_t *data, size_t len)
{
    if (!s_state.initialized) {
        return;
    }
    
    if (char_handle == s_state.inbox_char_handle) {
        handle_inbox_notification(data, len);
    } else if (char_handle == s_state.status_char_handle) {
        handle_status_notification(data, len);
    }
}

/**
 * @brief BLE write response callback
 */
void mesh_client_on_write_response(uint16_t char_handle, esp_err_t status, uint32_t seq)
{
    if (!s_state.initialized) {
        return;
    }
    
    if (char_handle == s_state.send_char_handle && s_state.send_complete_cb) {
        s_state.send_complete_cb(seq, status == ESP_OK);
    }
}

/* ============================================================================
 * Public API Implementation
 * ============================================================================ */

esp_err_t mesh_client_init(void)
{
    if (s_state.initialized) {
        ESP_LOGW(TAG, "Already initialized");
        return ESP_ERR_INVALID_STATE;
    }
    
    memset(&s_state, 0, sizeof(s_state));
    
    s_state.mutex = xSemaphoreCreateMutex();
    if (!s_state.mutex) {
        ESP_LOGE(TAG, "Failed to create mutex");
        return ESP_ERR_NO_MEM;
    }
    
    s_state.initialized = true;
    s_state.seq_counter = 1;
    
    ESP_LOGI(TAG, "Mesh client initialized");
    
    /* TODO: Register with BLE GATT client to discover Mesh Relay service
     * and subscribe to MeshInbox and MeshStatus notifications.
     * This depends on how control_link manages BLE connections.
     */
    
    return ESP_OK;
}

esp_err_t mesh_client_deinit(void)
{
    if (!s_state.initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    
    if (s_state.mutex) {
        vSemaphoreDelete(s_state.mutex);
    }
    
    memset(&s_state, 0, sizeof(s_state));
    
    ESP_LOGI(TAG, "Mesh client deinitialized");
    return ESP_OK;
}

bool mesh_client_is_connected(void)
{
    return s_state.initialized && s_state.connected;
}

esp_err_t mesh_client_subscribe_inbox(mesh_inbox_cb_t callback)
{
    if (!s_state.initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    s_state.inbox_cb = callback;
    return ESP_OK;
}

esp_err_t mesh_client_subscribe_status(mesh_status_cb_t callback)
{
    if (!s_state.initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    s_state.status_cb = callback;
    return ESP_OK;
}

esp_err_t mesh_client_subscribe_send_complete(mesh_send_complete_cb_t callback)
{
    if (!s_state.initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    s_state.send_complete_cb = callback;
    return ESP_OK;
}

esp_err_t mesh_client_send(const char *to, const char *message, uint8_t channel, bool want_ack)
{
    if (!s_state.initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    
    if (!to || !message) {
        return ESP_ERR_INVALID_ARG;
    }
    
    size_t msg_len = strlen(message);
    if (msg_len > MESH_MSG_MAX_LEN) {
        ESP_LOGW(TAG, "Message too long (%d > %d)", (int)msg_len, MESH_MSG_MAX_LEN);
        return ESP_ERR_INVALID_SIZE;
    }
    
    /* Encode CBOR payload */
    uint8_t buf[300];
    size_t buf_len = sizeof(buf);
    uint32_t seq = s_state.seq_counter++;
    
    esp_err_t ret = encode_mesh_send(to, message, channel, want_ack, seq, buf, &buf_len);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to encode message");
        return ret;
    }
    
    /* TODO: Write to MeshSend characteristic via BLE GATT client
     * ret = ble_gatt_write(s_state.conn_handle, s_state.send_char_handle, buf, buf_len);
     */
    
    ESP_LOGI(TAG, "Queued mesh message to %s (seq=%lu, len=%d)", to, (unsigned long)seq, (int)msg_len);
    
    return ESP_OK;
}

esp_err_t mesh_client_broadcast(const char *message, uint8_t channel)
{
    return mesh_client_send("^all", message, channel, false);
}

esp_err_t mesh_client_send_direct(const char *node_id, const char *message, uint8_t channel)
{
    return mesh_client_send(node_id, message, channel, true);
}

esp_err_t mesh_client_get_status(mesh_status_t *status)
{
    if (!s_state.initialized || !status) {
        return ESP_ERR_INVALID_ARG;
    }
    
    if (!s_state.connected) {
        return ESP_ERR_NOT_FOUND;
    }
    
    xSemaphoreTake(s_state.mutex, portMAX_DELAY);
    memcpy(status, &s_state.status, sizeof(mesh_status_t));
    xSemaphoreGive(s_state.mutex);
    
    return ESP_OK;
}

esp_err_t mesh_client_get_nodes(mesh_node_t *nodes, size_t max_nodes, size_t *out_count)
{
    if (!s_state.initialized || !nodes || !out_count) {
        return ESP_ERR_INVALID_ARG;
    }
    
    xSemaphoreTake(s_state.mutex, portMAX_DELAY);
    size_t count = (s_state.node_count < max_nodes) ? s_state.node_count : max_nodes;
    memcpy(nodes, s_state.nodes, count * sizeof(mesh_node_t));
    *out_count = count;
    xSemaphoreGive(s_state.mutex);
    
    return ESP_OK;
}

esp_err_t mesh_client_refresh_nodes(void)
{
    if (!s_state.initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    
    /* TODO: Read NodeList characteristic via BLE GATT client
     * uint8_t buf[512];
     * size_t len;
     * ret = ble_gatt_read(s_state.conn_handle, s_state.node_list_char_handle, buf, &len);
     * parse_node_list(buf, len, s_state.nodes, MESH_MAX_NODES, &s_state.node_count);
     */
    
    return ESP_OK;
}

size_t mesh_client_get_unread_count(void)
{
    return s_state.unread_count;
}

void mesh_client_mark_all_read(void)
{
    xSemaphoreTake(s_state.mutex, portMAX_DELAY);
    s_state.unread_count = 0;
    xSemaphoreGive(s_state.mutex);
}

/* ============================================================================
 * CBOR Parsing Helpers (Simplified Implementation)
 * 
 * For production, use a proper CBOR library like tinycbor.
 * These are simplified placeholders that demonstrate the structure.
 * ============================================================================ */

/**
 * @brief Parse incoming mesh message from CBOR
 * 
 * Expected format:
 * {
 *   "id": uint,
 *   "from": string,
 *   "from_name": string,
 *   "to": string,
 *   "msg": string,
 *   "channel": uint,
 *   "rssi": int,
 *   "snr": float,
 *   "ts": uint
 * }
 */
static esp_err_t parse_mesh_message(const uint8_t *data, size_t len, mesh_message_t *msg)
{
    if (!data || !msg || len < 10) {
        return ESP_ERR_INVALID_ARG;
    }
    
    /* TODO: Implement proper CBOR parsing using tinycbor
     * 
     * For now, we'll use a simple placeholder that demonstrates
     * what the parsing would extract:
     */
    
    /* Placeholder - in production, parse the actual CBOR */
    msg->id = 0;
    strncpy(msg->from_id, "!00000000", MESH_NODE_ID_LEN);
    strncpy(msg->from_name, "Unknown", MESH_NODE_NAME_LEN);
    strncpy(msg->to_id, "^all", MESH_NODE_ID_LEN);
    strncpy(msg->message, "(parse not implemented)", MESH_MSG_MAX_LEN);
    msg->channel = 0;
    msg->rssi = -100;
    msg->snr = 0.0f;
    msg->timestamp = 0;
    
    ESP_LOGW(TAG, "CBOR parsing not fully implemented - using placeholder");
    
    return ESP_OK;
}

/**
 * @brief Parse mesh status from CBOR
 */
static esp_err_t parse_mesh_status(const uint8_t *data, size_t len, mesh_status_t *status)
{
    if (!data || !status || len < 5) {
        return ESP_ERR_INVALID_ARG;
    }
    
    /* TODO: Implement proper CBOR parsing */
    
    /* Placeholder */
    status->radio_on = true;
    status->connected = true;
    strncpy(status->my_id, "!00000000", MESH_NODE_ID_LEN);
    strncpy(status->my_name, "Translator", MESH_NODE_NAME_LEN);
    status->nodes_heard = 0;
    status->tx_queue = 0;
    strncpy(status->channel_name, "LongFast", sizeof(status->channel_name));
    status->last_rx_ts = 0;
    
    return ESP_OK;
}

/**
 * @brief Parse node list from CBOR array
 */
static esp_err_t parse_node_list(const uint8_t *data, size_t len, mesh_node_t *nodes, size_t max_nodes, size_t *count)
{
    if (!data || !nodes || !count) {
        return ESP_ERR_INVALID_ARG;
    }
    
    /* TODO: Implement proper CBOR array parsing */
    
    *count = 0;
    return ESP_OK;
}

/**
 * @brief Encode outgoing message to CBOR
 * 
 * Output format:
 * {
 *   "seq": uint,
 *   "to": string,
 *   "msg": string,
 *   "channel": uint,
 *   "want_ack": bool
 * }
 */
static esp_err_t encode_mesh_send(const char *to, const char *message, uint8_t channel, bool want_ack, uint32_t seq, uint8_t *out_buf, size_t *out_len)
{
    if (!to || !message || !out_buf || !out_len) {
        return ESP_ERR_INVALID_ARG;
    }
    
    /* TODO: Implement proper CBOR encoding using tinycbor
     * 
     * For now, create a simple JSON-like structure as placeholder.
     * In production, this MUST be proper CBOR.
     */
    
    int written = snprintf((char *)out_buf, *out_len,
        "{\"seq\":%lu,\"to\":\"%s\",\"msg\":\"%s\",\"channel\":%d,\"want_ack\":%s}",
        (unsigned long)seq, to, message, channel, want_ack ? "true" : "false");
    
    if (written < 0 || (size_t)written >= *out_len) {
        return ESP_ERR_NO_MEM;
    }
    
    *out_len = (size_t)written;
    
    ESP_LOGW(TAG, "CBOR encoding not fully implemented - using JSON placeholder");
    
    return ESP_OK;
}

