/**
 * @file MainDeviceBridgeModule.h
 * @brief BLE bridge to main translator device
 * 
 * Creates custom BLE GATT services for bidirectional communication
 * with the main translator device:
 * - Joystick events (partner -> main)
 * - Mesh messages (both directions)
 * - Status updates (partner -> main)
 */

#pragma once

#include "SinglePortModule.h"
#include "configuration.h"
#include "JoystickInputModule.h"
#include "mesh/generated/meshtastic/mesh.pb.h"

#include <NimBLEDevice.h>
#include <NimBLEServer.h>
#include <NimBLECharacteristic.h>

#ifdef HAS_MAIN_DEVICE_BRIDGE

/**
 * @brief Mesh message for BLE transmission
 */
struct MeshBridgeMessage {
    uint32_t id;                    ///< Meshtastic packet ID
    uint32_t from;                  ///< Sender node number
    uint32_t to;                    ///< Destination node number
    char fromName[32];              ///< Sender display name
    char message[238];              ///< Message text
    uint8_t channel;                ///< Channel index
    int8_t rssi;                    ///< Signal strength
    float snr;                      ///< Signal-to-noise ratio
    uint32_t timestamp;             ///< Unix timestamp
};

/**
 * @brief Mesh network status
 */
struct MeshBridgeStatus {
    bool radioOn;                   ///< Radio is active
    bool hasNodes;                  ///< Has heard from other nodes
    uint32_t myNodeNum;             ///< This node's number
    char myName[32];                ///< This node's name
    uint8_t nodesHeard;             ///< Count of recently heard nodes
    uint8_t txQueue;                ///< Pending transmissions
    char channelName[16];           ///< Current channel name
    uint32_t lastRxTime;            ///< Last message timestamp
};

/**
 * @brief Outgoing message request from main device
 */
struct MeshSendRequest {
    uint32_t seq;                   ///< Sequence for ACK
    uint32_t to;                    ///< Destination (0 = broadcast)
    char message[238];              ///< Message text
    uint8_t channel;                ///< Channel to send on
    bool wantAck;                   ///< Request delivery ACK
};

/**
 * @brief BLE callback handler for MeshSend writes
 */
class MeshSendCallback : public NimBLECharacteristicCallbacks {
public:
    MeshSendCallback(class MainDeviceBridgeModule *bridge) : bridge(bridge) {}
    void onWrite(NimBLECharacteristic *pCharacteristic) override;
    
private:
    class MainDeviceBridgeModule *bridge;
};

/**
 * @brief BLE server callbacks for connection management
 */
class BridgeServerCallbacks : public NimBLEServerCallbacks {
public:
    BridgeServerCallbacks(class MainDeviceBridgeModule *bridge) : bridge(bridge) {}
    void onConnect(NimBLEServer *pServer) override;
    void onDisconnect(NimBLEServer *pServer) override;
    
private:
    class MainDeviceBridgeModule *bridge;
};

/**
 * @brief Main device bridge module
 * 
 * Integrates with Meshtastic to relay mesh messages via BLE and
 * publishes joystick/button events to the main device.
 */
class MainDeviceBridgeModule : public SinglePortModule {
public:
    /**
     * @brief Construct the bridge module
     */
    MainDeviceBridgeModule();
    
    /**
     * @brief Get singleton instance
     */
    static MainDeviceBridgeModule *getInstance();
    
    /**
     * @brief Initialize BLE services
     * @param server NimBLE server instance
     */
    void setupBLEServices(NimBLEServer *server);
    
    /**
     * @brief Handle incoming Meshtastic packet
     * @param mp Mesh packet
     * @return Processing result
     */
    virtual ProcessMessage handleReceived(const meshtastic_MeshPacket &mp) override;
    
    /**
     * @brief Send joystick event to main device
     * @param evt Joystick event struct
     */
    void sendJoystickEvent(const JoystickEvent &evt);
    
    /**
     * @brief Send keypad event to main device
     * @param buttons Button bitmask
     * @param seq Sequence number
     */
    void sendKeypadEvent(uint8_t buttons, uint32_t seq);
    
    /**
     * @brief Queue outgoing mesh message
     * @param to Destination node (0 = broadcast)
     * @param message Message text
     * @param channel Channel index
     * @param wantAck Request ACK
     * @param seq Sequence number for tracking
     */
    void queueOutgoingMessage(uint32_t to, const char *message, uint8_t channel, bool wantAck, uint32_t seq);
    
    /**
     * @brief Check if main device is connected
     */
    bool isConnected() const { return mainDeviceConnected; }
    
    /**
     * @brief Handle connection event
     */
    void onMainDeviceConnect();
    
    /**
     * @brief Handle disconnection event
     */
    void onMainDeviceDisconnect();

protected:
    /**
     * @brief Module tick function
     * @return Milliseconds until next call
     */
    virtual int32_t runOnce() override;

private:
    /**
     * @brief Send mesh inbox notification
     * @param mp Received mesh packet
     */
    void notifyMeshInbox(const meshtastic_MeshPacket &mp);
    
    /**
     * @brief Update and send mesh status
     */
    void updateMeshStatus();
    
    /**
     * @brief Encode message to CBOR
     */
    size_t encodeMeshInbox(const MeshBridgeMessage &msg, uint8_t *buf, size_t bufLen);
    
    /**
     * @brief Encode status to CBOR
     */
    size_t encodeMeshStatus(const MeshBridgeStatus &status, uint8_t *buf, size_t bufLen);
    
    /**
     * @brief Decode incoming send request from CBOR
     */
    bool decodeMeshSend(const uint8_t *buf, size_t len, MeshSendRequest &req);
    
    /**
     * @brief Build node list response
     */
    size_t buildNodeList(uint8_t *buf, size_t bufLen);

    // BLE characteristics
    NimBLECharacteristic *meshInboxChar;
    NimBLECharacteristic *meshSendChar;
    NimBLECharacteristic *meshStatusChar;
    NimBLECharacteristic *nodeListChar;
    NimBLECharacteristic *joystickEventChar;
    NimBLECharacteristic *keypadEventChar;
    NimBLECharacteristic *ackChar;
    NimBLECharacteristic *heartbeatChar;
    
    // Connection state
    bool mainDeviceConnected;
    uint32_t lastHeartbeat;
    uint32_t lastStatusUpdate;
    
    // Callbacks (prevent dangling pointers)
    MeshSendCallback *meshSendCallback;
    BridgeServerCallbacks *serverCallbacks;
    
    // Singleton
    static MainDeviceBridgeModule *instance;
    
    friend class MeshSendCallback;
    friend class BridgeServerCallbacks;
};

// Global pointer
extern MainDeviceBridgeModule *mainDeviceBridgeModule;

#endif // HAS_MAIN_DEVICE_BRIDGE

