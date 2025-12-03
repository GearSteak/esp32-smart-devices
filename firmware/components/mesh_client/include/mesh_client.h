/**
 * @file mesh_client.h
 * @brief Meshtastic mesh network client for main device
 *
 * This component handles BLE communication with the partner device's
 * Mesh Relay service, enabling bidirectional LoRa mesh messaging.
 */

#pragma once

#include "esp_err.h"
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Maximum length of a mesh message
 */
#define MESH_MSG_MAX_LEN        237

/**
 * @brief Maximum length of node ID string (e.g., "!abcd1234")
 */
#define MESH_NODE_ID_LEN        12

/**
 * @brief Maximum length of node name
 */
#define MESH_NODE_NAME_LEN      32

/**
 * @brief Maximum number of nodes in node list
 */
#define MESH_MAX_NODES          10

/**
 * @brief Joystick input layer for mesh compose mode
 */
#define LAYER_MESH_COMPOSE      4

/**
 * @brief Joystick input layer for mesh inbox mode
 */
#define LAYER_MESH_INBOX        5

/**
 * @brief Incoming mesh message structure
 */
typedef struct {
    uint32_t id;                            /**< Meshtastic packet ID */
    char from_id[MESH_NODE_ID_LEN];         /**< Sender node ID (e.g., "!abcd1234") */
    char from_name[MESH_NODE_NAME_LEN];     /**< Sender's display name */
    char to_id[MESH_NODE_ID_LEN];           /**< Destination ("^all" for broadcast) */
    char message[MESH_MSG_MAX_LEN + 1];     /**< Message text */
    uint8_t channel;                        /**< Channel index */
    int8_t rssi;                            /**< Receive signal strength (dBm) */
    float snr;                              /**< Signal-to-noise ratio (dB) */
    uint32_t timestamp;                     /**< Unix timestamp of receipt */
    bool wants_ack;                         /**< Whether sender requested ACK */
} mesh_message_t;

/**
 * @brief Mesh network status
 */
typedef struct {
    bool radio_on;                          /**< LoRa radio is active */
    bool connected;                         /**< Has heard from nodes recently */
    char my_id[MESH_NODE_ID_LEN];           /**< This device's mesh node ID */
    char my_name[MESH_NODE_NAME_LEN];       /**< This device's display name */
    uint8_t nodes_heard;                    /**< Number of nodes seen recently */
    uint8_t tx_queue;                       /**< Messages pending transmission */
    char channel_name[32];                  /**< Current channel name */
    uint32_t last_rx_ts;                    /**< Timestamp of last received packet */
} mesh_status_t;

/**
 * @brief Known mesh node information
 */
typedef struct {
    char id[MESH_NODE_ID_LEN];              /**< Node ID */
    char name[MESH_NODE_NAME_LEN];          /**< Node display name */
    uint32_t last_heard;                    /**< Unix timestamp of last contact */
    int8_t rssi;                            /**< Last RSSI value */
    uint8_t hops;                           /**< Hop count to this node */
} mesh_node_t;

/**
 * @brief Callback for incoming mesh messages
 *
 * @param msg Pointer to the received message
 */
typedef void (*mesh_inbox_cb_t)(const mesh_message_t *msg);

/**
 * @brief Callback for mesh status updates
 *
 * @param status Pointer to the status structure
 */
typedef void (*mesh_status_cb_t)(const mesh_status_t *status);

/**
 * @brief Callback for send completion
 *
 * @param seq Sequence number of the sent message
 * @param success True if message was transmitted successfully
 */
typedef void (*mesh_send_complete_cb_t)(uint32_t seq, bool success);

/**
 * @brief Initialize the mesh client
 *
 * Sets up BLE GATT client for the Mesh Relay service.
 * Must be called after BLE stack initialization.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t mesh_client_init(void);

/**
 * @brief Deinitialize the mesh client
 *
 * @return ESP_OK on success
 */
esp_err_t mesh_client_deinit(void);

/**
 * @brief Check if mesh client is connected to partner device
 *
 * @return true if connected and ready
 */
bool mesh_client_is_connected(void);

/**
 * @brief Subscribe to incoming mesh messages
 *
 * @param callback Function to call when a message is received
 * @return ESP_OK on success
 */
esp_err_t mesh_client_subscribe_inbox(mesh_inbox_cb_t callback);

/**
 * @brief Subscribe to mesh status updates
 *
 * @param callback Function to call when status changes
 * @return ESP_OK on success
 */
esp_err_t mesh_client_subscribe_status(mesh_status_cb_t callback);

/**
 * @brief Subscribe to send completion notifications
 *
 * @param callback Function to call when a send completes
 * @return ESP_OK on success
 */
esp_err_t mesh_client_subscribe_send_complete(mesh_send_complete_cb_t callback);

/**
 * @brief Send a message via the mesh network
 *
 * @param to Destination node ID ("^all" for broadcast, "!nodeId" for direct)
 * @param message Message text (max MESH_MSG_MAX_LEN characters)
 * @param channel Channel index to send on (usually 0)
 * @param want_ack Request delivery acknowledgment
 * @return ESP_OK if queued successfully, error code otherwise
 */
esp_err_t mesh_client_send(const char *to, const char *message, uint8_t channel, bool want_ack);

/**
 * @brief Broadcast a message to all nodes
 *
 * Convenience wrapper for mesh_client_send with "^all" destination.
 *
 * @param message Message text
 * @param channel Channel index
 * @return ESP_OK if queued successfully
 */
esp_err_t mesh_client_broadcast(const char *message, uint8_t channel);

/**
 * @brief Send a direct message to a specific node
 *
 * @param node_id Target node ID (e.g., "!abcd1234")
 * @param message Message text
 * @param channel Channel index
 * @return ESP_OK if queued successfully
 */
esp_err_t mesh_client_send_direct(const char *node_id, const char *message, uint8_t channel);

/**
 * @brief Get current mesh network status
 *
 * @param status Pointer to status structure to fill
 * @return ESP_OK on success, ESP_ERR_NOT_FOUND if not connected
 */
esp_err_t mesh_client_get_status(mesh_status_t *status);

/**
 * @brief Get list of known mesh nodes
 *
 * @param nodes Array to fill with node information
 * @param max_nodes Maximum number of nodes to return
 * @param out_count Actual number of nodes returned
 * @return ESP_OK on success
 */
esp_err_t mesh_client_get_nodes(mesh_node_t *nodes, size_t max_nodes, size_t *out_count);

/**
 * @brief Request updated node list from partner device
 *
 * Triggers a read of the NodeList characteristic.
 *
 * @return ESP_OK if request sent
 */
esp_err_t mesh_client_refresh_nodes(void);

/**
 * @brief Get count of unread messages
 *
 * @return Number of unread messages in inbox
 */
size_t mesh_client_get_unread_count(void);

/**
 * @brief Mark all messages as read
 */
void mesh_client_mark_all_read(void);

#ifdef __cplusplus
}
#endif

