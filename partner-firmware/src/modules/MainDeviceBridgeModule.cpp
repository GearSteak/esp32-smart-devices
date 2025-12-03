/**
 * @file MainDeviceBridgeModule.cpp
 * @brief BLE bridge to main translator device implementation
 */

#include "MainDeviceBridgeModule.h"

#ifdef HAS_MAIN_DEVICE_BRIDGE

#include "configuration.h"
#include "main.h"
#include "MeshService.h"
#include "NodeDB.h"
#include "Router.h"
#include "mesh/generated/meshtastic/mesh.pb.h"

#include <cstring>

// Singleton instances
MainDeviceBridgeModule *MainDeviceBridgeModule::instance = nullptr;
MainDeviceBridgeModule *mainDeviceBridgeModule = nullptr;

// ============================================================================
// BLE Callbacks
// ============================================================================

void MeshSendCallback::onWrite(NimBLECharacteristic *pCharacteristic)
{
    std::string value = pCharacteristic->getValue();
    if (value.empty() || !bridge) {
        return;
    }
    
    MeshSendRequest req;
    if (bridge->decodeMeshSend((const uint8_t *)value.data(), value.length(), req)) {
        bridge->queueOutgoingMessage(req.to, req.message, req.channel, req.wantAck, req.seq);
    } else {
        LOG_WARN("Failed to decode MeshSend request\n");
    }
}

void BridgeServerCallbacks::onConnect(NimBLEServer *pServer)
{
    if (bridge) {
        bridge->onMainDeviceConnect();
    }
}

void BridgeServerCallbacks::onDisconnect(NimBLEServer *pServer)
{
    if (bridge) {
        bridge->onMainDeviceDisconnect();
    }
    
    // Resume advertising
    NimBLEDevice::startAdvertising();
}

// ============================================================================
// MainDeviceBridgeModule Implementation
// ============================================================================

MainDeviceBridgeModule::MainDeviceBridgeModule()
    : SinglePortModule("mainbridge", meshtastic_PortNum_TEXT_MESSAGE_APP),
      meshInboxChar(nullptr),
      meshSendChar(nullptr),
      meshStatusChar(nullptr),
      nodeListChar(nullptr),
      joystickEventChar(nullptr),
      keypadEventChar(nullptr),
      ackChar(nullptr),
      heartbeatChar(nullptr),
      mainDeviceConnected(false),
      lastHeartbeat(0),
      lastStatusUpdate(0),
      meshSendCallback(nullptr),
      serverCallbacks(nullptr)
{
    instance = this;
    mainDeviceBridgeModule = this;
    
    LOG_INFO("MainDeviceBridgeModule constructed\n");
}

MainDeviceBridgeModule *MainDeviceBridgeModule::getInstance()
{
    if (!instance) {
        instance = new MainDeviceBridgeModule();
    }
    return instance;
}

void MainDeviceBridgeModule::setupBLEServices(NimBLEServer *server)
{
    if (!server) {
        LOG_ERROR("BLE server is null\n");
        return;
    }
    
    // Set server callbacks
    serverCallbacks = new BridgeServerCallbacks(this);
    server->setCallbacks(serverCallbacks);
    
    // ========================================================================
    // Mesh Relay Service
    // ========================================================================
    NimBLEService *meshService = server->createService(MESH_RELAY_SERVICE_UUID);
    
    // MeshInbox - incoming messages (notify)
    meshInboxChar = meshService->createCharacteristic(
        MESH_INBOX_CHAR_UUID,
        NIMBLE_PROPERTY::NOTIFY
    );
    meshInboxChar->setValue("");
    
    // MeshSend - outgoing messages (write)
    meshSendChar = meshService->createCharacteristic(
        MESH_SEND_CHAR_UUID,
        NIMBLE_PROPERTY::WRITE
    );
    meshSendCallback = new MeshSendCallback(this);
    meshSendChar->setCallbacks(meshSendCallback);
    
    // MeshStatus - network status (notify + read)
    meshStatusChar = meshService->createCharacteristic(
        MESH_STATUS_CHAR_UUID,
        NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
    );
    meshStatusChar->setValue("");
    
    // NodeList - known nodes (read)
    nodeListChar = meshService->createCharacteristic(
        MESH_NODE_LIST_CHAR_UUID,
        NIMBLE_PROPERTY::READ
    );
    nodeListChar->setValue("");
    
    meshService->start();
    LOG_INFO("Mesh Relay service started\n");
    
    // ========================================================================
    // Remote Input Service
    // ========================================================================
    NimBLEService *inputService = server->createService(REMOTE_INPUT_SERVICE_UUID);
    
    // JoystickEvent (notify)
    joystickEventChar = inputService->createCharacteristic(
        JOYSTICK_EVENT_CHAR_UUID,
        NIMBLE_PROPERTY::NOTIFY
    );
    joystickEventChar->setValue("");
    
    // KeypadEvent (notify)
    keypadEventChar = inputService->createCharacteristic(
        KEYPAD_EVENT_CHAR_UUID,
        NIMBLE_PROPERTY::NOTIFY
    );
    keypadEventChar->setValue("");
    
    inputService->start();
    LOG_INFO("Remote Input service started\n");
    
    // ========================================================================
    // Command & Sync Service
    // ========================================================================
    NimBLEService *cmdService = server->createService(COMMAND_SYNC_SERVICE_UUID);
    
    // Ack (indicate)
    ackChar = cmdService->createCharacteristic(
        ACK_CHAR_UUID,
        NIMBLE_PROPERTY::INDICATE
    );
    ackChar->setValue("");
    
    // Heartbeat (notify)
    heartbeatChar = cmdService->createCharacteristic(
        HEARTBEAT_CHAR_UUID,
        NIMBLE_PROPERTY::NOTIFY
    );
    heartbeatChar->setValue("");
    
    cmdService->start();
    LOG_INFO("Command & Sync service started\n");
    
    // Start advertising
    NimBLEAdvertising *advertising = NimBLEDevice::getAdvertising();
    advertising->addServiceUUID(MESH_RELAY_SERVICE_UUID);
    advertising->addServiceUUID(REMOTE_INPUT_SERVICE_UUID);
    advertising->setScanResponse(true);
    advertising->start();
    
    LOG_INFO("BLE advertising started as '%s'\n", BLE_NAME);
}

void MainDeviceBridgeModule::onMainDeviceConnect()
{
    mainDeviceConnected = true;
    lastHeartbeat = millis();
    LOG_INFO("Main device connected\n");
    
    // Send initial status
    updateMeshStatus();
}

void MainDeviceBridgeModule::onMainDeviceDisconnect()
{
    mainDeviceConnected = false;
    LOG_INFO("Main device disconnected\n");
}

ProcessMessage MainDeviceBridgeModule::handleReceived(const meshtastic_MeshPacket &mp)
{
    // Only handle text messages
    if (mp.decoded.portnum != meshtastic_PortNum_TEXT_MESSAGE_APP) {
        return ProcessMessage::CONTINUE;
    }
    
    // Forward to main device if connected
    if (mainDeviceConnected && meshInboxChar) {
        notifyMeshInbox(mp);
    }
    
    return ProcessMessage::CONTINUE;
}

void MainDeviceBridgeModule::notifyMeshInbox(const meshtastic_MeshPacket &mp)
{
    MeshBridgeMessage msg;
    memset(&msg, 0, sizeof(msg));
    
    msg.id = mp.id;
    msg.from = mp.from;
    msg.to = mp.to;
    msg.channel = cycleChannelIndex;  // Use current channel
    msg.rssi = mp.rx_rssi;
    msg.snr = mp.rx_snr;
    msg.timestamp = mp.rx_time;
    
    // Get sender name from NodeDB
    meshtastic_NodeInfoLite *node = nodeDB->getMeshNode(mp.from);
    if (node && node->has_user && node->user.long_name[0] != '\0') {
        strncpy(msg.fromName, node->user.long_name, sizeof(msg.fromName) - 1);
    } else {
        snprintf(msg.fromName, sizeof(msg.fromName), "!%08x", mp.from);
    }
    
    // Copy message text
    if (mp.decoded.payload.size > 0 && mp.decoded.payload.size < sizeof(msg.message)) {
        memcpy(msg.message, mp.decoded.payload.bytes, mp.decoded.payload.size);
        msg.message[mp.decoded.payload.size] = '\0';
    }
    
    // Encode to CBOR and send
    uint8_t buf[300];
    size_t len = encodeMeshInbox(msg, buf, sizeof(buf));
    
    if (len > 0) {
        meshInboxChar->setValue(buf, len);
        meshInboxChar->notify();
        LOG_INFO("Forwarded mesh message from %s: %.32s\n", msg.fromName, msg.message);
    }
}

void MainDeviceBridgeModule::updateMeshStatus()
{
    if (!meshStatusChar) {
        return;
    }
    
    MeshBridgeStatus status;
    memset(&status, 0, sizeof(status));
    
    status.radioOn = true;  // We're running, radio should be on
    status.myNodeNum = nodeDB->getNodeNum();
    
    // Get our name
    const meshtastic_User &user = owner;
    if (user.long_name[0] != '\0') {
        strncpy(status.myName, user.long_name, sizeof(status.myName) - 1);
    } else {
        snprintf(status.myName, sizeof(status.myName), "!%08x", status.myNodeNum);
    }
    
    // Count nodes heard recently (within 15 minutes)
    uint32_t now = getTime();
    status.nodesHeard = 0;
    for (int i = 0; i < nodeDB->getNumMeshNodes(); i++) {
        meshtastic_NodeInfoLite *node = nodeDB->getMeshNodeByIndex(i);
        if (node && node->num != status.myNodeNum) {
            if (now - node->last_heard < 900) {  // 15 minutes
                status.nodesHeard++;
                status.hasNodes = true;
            }
        }
    }
    
    // Get channel name
    const meshtastic_Channel &ch = channels.getByIndex(cycleChannelIndex);
    if (ch.settings.name[0] != '\0') {
        strncpy(status.channelName, ch.settings.name, sizeof(status.channelName) - 1);
    } else {
        strncpy(status.channelName, "Default", sizeof(status.channelName) - 1);
    }
    
    // TODO: Get actual tx queue length
    status.txQueue = 0;
    status.lastRxTime = 0;  // TODO: Track this
    
    // Encode and send
    uint8_t buf[100];
    size_t len = encodeMeshStatus(status, buf, sizeof(buf));
    
    if (len > 0) {
        meshStatusChar->setValue(buf, len);
        meshStatusChar->notify();
    }
}

void MainDeviceBridgeModule::queueOutgoingMessage(uint32_t to, const char *message, 
                                                   uint8_t channel, bool wantAck, uint32_t seq)
{
    if (!message || message[0] == '\0') {
        LOG_WARN("Empty message, not sending\n");
        return;
    }
    
    // Allocate a new packet
    meshtastic_MeshPacket *p = router->allocForSending();
    if (!p) {
        LOG_ERROR("Failed to allocate packet\n");
        return;
    }
    
    // Set destination
    p->to = (to == 0) ? NODENUM_BROADCAST : to;
    p->channel = channel;
    p->want_ack = wantAck;
    p->decoded.portnum = meshtastic_PortNum_TEXT_MESSAGE_APP;
    
    // Copy message payload
    size_t msgLen = strlen(message);
    if (msgLen > sizeof(p->decoded.payload.bytes) - 1) {
        msgLen = sizeof(p->decoded.payload.bytes) - 1;
    }
    memcpy(p->decoded.payload.bytes, message, msgLen);
    p->decoded.payload.size = msgLen;
    
    // Send the packet
    service->sendToMesh(p, RX_SRC_LOCAL, true);
    
    LOG_INFO("Queued mesh message to %08x: %.32s (seq=%u)\n", to, message, seq);
    
    // Send ACK to main device
    if (ackChar && mainDeviceConnected) {
        uint8_t ackBuf[8];
        // Simple ACK: just the sequence number
        memcpy(ackBuf, &seq, sizeof(seq));
        ackChar->setValue(ackBuf, sizeof(seq));
        ackChar->indicate();
    }
}

void MainDeviceBridgeModule::sendJoystickEvent(const JoystickEvent &evt)
{
    if (!joystickEventChar || !mainDeviceConnected) {
        return;
    }
    
    // Send raw struct (8 bytes, packed)
    joystickEventChar->setValue((uint8_t *)&evt, sizeof(JoystickEvent));
    joystickEventChar->notify();
}

void MainDeviceBridgeModule::sendKeypadEvent(uint8_t buttons, uint32_t seq)
{
    if (!keypadEventChar || !mainDeviceConnected) {
        return;
    }
    
    uint8_t buf[5];
    buf[0] = buttons;
    memcpy(&buf[1], &seq, sizeof(seq));
    
    keypadEventChar->setValue(buf, sizeof(buf));
    keypadEventChar->notify();
}

int32_t MainDeviceBridgeModule::runOnce()
{
    uint32_t now = millis();
    
    // Send heartbeat every 2 seconds
    if (mainDeviceConnected && heartbeatChar && (now - lastHeartbeat > 2000)) {
        lastHeartbeat = now;
        
        // Heartbeat contains connection time and status byte
        uint8_t hb[5];
        uint32_t uptime = now / 1000;
        memcpy(hb, &uptime, sizeof(uptime));
        hb[4] = mainDeviceConnected ? 0x01 : 0x00;
        
        heartbeatChar->setValue(hb, sizeof(hb));
        heartbeatChar->notify();
    }
    
    // Update status every 30 seconds
    if (mainDeviceConnected && (now - lastStatusUpdate > 30000)) {
        lastStatusUpdate = now;
        updateMeshStatus();
    }
    
    // Update node list periodically
    if (mainDeviceConnected && nodeListChar && (now - lastStatusUpdate > 60000)) {
        uint8_t buf[512];
        size_t len = buildNodeList(buf, sizeof(buf));
        if (len > 0) {
            nodeListChar->setValue(buf, len);
        }
    }
    
    return 500;  // Run every 500ms
}

// ============================================================================
// CBOR Encoding/Decoding
// 
// NOTE: These are simplified implementations using JSON-like format.
// For production, use tinycbor library for proper CBOR encoding.
// ============================================================================

size_t MainDeviceBridgeModule::encodeMeshInbox(const MeshBridgeMessage &msg, uint8_t *buf, size_t bufLen)
{
    // Simplified: Use JSON-like format for now
    // In production, replace with proper CBOR using tinycbor
    
    int written = snprintf((char *)buf, bufLen,
        "{\"id\":%u,\"from\":\"!%08x\",\"from_name\":\"%s\",\"to\":\"!%08x\","
        "\"msg\":\"%s\",\"channel\":%d,\"rssi\":%d,\"snr\":%.2f,\"ts\":%u}",
        msg.id, msg.from, msg.fromName, msg.to,
        msg.message, msg.channel, msg.rssi, msg.snr, msg.timestamp);
    
    if (written < 0 || (size_t)written >= bufLen) {
        return 0;
    }
    
    return (size_t)written;
}

size_t MainDeviceBridgeModule::encodeMeshStatus(const MeshBridgeStatus &status, uint8_t *buf, size_t bufLen)
{
    int written = snprintf((char *)buf, bufLen,
        "{\"radio_on\":%s,\"connected\":%s,\"my_id\":\"!%08x\",\"my_name\":\"%s\","
        "\"nodes_heard\":%d,\"tx_queue\":%d,\"channel_name\":\"%s\",\"last_rx_ts\":%u}",
        status.radioOn ? "true" : "false",
        status.hasNodes ? "true" : "false",
        status.myNodeNum, status.myName,
        status.nodesHeard, status.txQueue,
        status.channelName, status.lastRxTime);
    
    if (written < 0 || (size_t)written >= bufLen) {
        return 0;
    }
    
    return (size_t)written;
}

bool MainDeviceBridgeModule::decodeMeshSend(const uint8_t *buf, size_t len, MeshSendRequest &req)
{
    // Simplified JSON parsing - in production use a proper parser
    // Expected format: {"seq":123,"to":"^all","msg":"hello","channel":0,"want_ack":true}
    
    memset(&req, 0, sizeof(req));
    
    const char *json = (const char *)buf;
    
    // Parse "seq"
    const char *seqPtr = strstr(json, "\"seq\":");
    if (seqPtr) {
        req.seq = atoi(seqPtr + 6);
    }
    
    // Parse "to" - check for broadcast or node ID
    const char *toPtr = strstr(json, "\"to\":\"");
    if (toPtr) {
        toPtr += 6;
        if (toPtr[0] == '^') {
            // Broadcast
            req.to = 0;
        } else if (toPtr[0] == '!') {
            // Node ID in hex
            req.to = strtoul(toPtr + 1, nullptr, 16);
        }
    }
    
    // Parse "msg"
    const char *msgPtr = strstr(json, "\"msg\":\"");
    if (msgPtr) {
        msgPtr += 7;
        const char *msgEnd = strchr(msgPtr, '"');
        if (msgEnd) {
            size_t msgLen = msgEnd - msgPtr;
            if (msgLen >= sizeof(req.message)) {
                msgLen = sizeof(req.message) - 1;
            }
            memcpy(req.message, msgPtr, msgLen);
            req.message[msgLen] = '\0';
        }
    }
    
    // Parse "channel"
    const char *chPtr = strstr(json, "\"channel\":");
    if (chPtr) {
        req.channel = atoi(chPtr + 10);
    }
    
    // Parse "want_ack"
    req.wantAck = (strstr(json, "\"want_ack\":true") != nullptr);
    
    // Validate we got at least a message
    return (req.message[0] != '\0');
}

size_t MainDeviceBridgeModule::buildNodeList(uint8_t *buf, size_t bufLen)
{
    // Build JSON array of nodes
    int written = 0;
    int total = 0;
    
    written = snprintf((char *)buf, bufLen, "[");
    total += written;
    
    uint32_t now = getTime();
    int count = 0;
    const int maxNodes = 10;
    
    for (int i = 0; i < nodeDB->getNumMeshNodes() && count < maxNodes; i++) {
        meshtastic_NodeInfoLite *node = nodeDB->getMeshNodeByIndex(i);
        if (!node || node->num == nodeDB->getNodeNum()) {
            continue;
        }
        
        // Skip nodes not heard recently
        if (now - node->last_heard > 3600) {  // 1 hour
            continue;
        }
        
        const char *name = "Unknown";
        if (node->has_user && node->user.long_name[0] != '\0') {
            name = node->user.long_name;
        }
        
        if (count > 0) {
            written = snprintf((char *)buf + total, bufLen - total, ",");
            total += written;
        }
        
        written = snprintf((char *)buf + total, bufLen - total,
            "{\"id\":\"!%08x\",\"name\":\"%s\",\"last_heard\":%u,\"rssi\":%d,\"hops\":%d}",
            node->num, name, node->last_heard, node->snr, node->hops_away);
        
        if (written < 0 || total + written >= (int)bufLen) {
            break;
        }
        total += written;
        count++;
    }
    
    written = snprintf((char *)buf + total, bufLen - total, "]");
    total += written;
    
    return (size_t)total;
}

// ============================================================================
// Global Function Implementation
// ============================================================================

#ifdef HAS_JOYSTICK
/**
 * @brief Send joystick event to main device via BLE
 * 
 * This overrides the weak symbol in JoystickInputModule.
 */
void sendJoystickToMainDevice(const JoystickEvent &evt)
{
    if (mainDeviceBridgeModule) {
        mainDeviceBridgeModule->sendJoystickEvent(evt);
    }
}
#endif

#endif // HAS_MAIN_DEVICE_BRIDGE

