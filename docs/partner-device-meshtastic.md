## Partner Device: Meshtastic LoRa Integration

This document specifies the hardware and firmware for the partner ESP32 device that combines joystick input control with Meshtastic mesh networking capabilities.

### 1. Overview

The partner device serves dual purposes:
1. **Primary input controller** for the main translator device (joystick navigation, buttons, tilt sensor)
2. **Meshtastic mesh gateway** enabling off-grid text messaging via LoRa

The device communicates with the main device (pi wrist computer) via **USB Serial** at 115200 baud. Joystick and button events are sent as 8-byte packets over USB. Messages typed on the main device are transmitted over the LoRa mesh network, and incoming mesh messages are displayed on the main device's transparent OLED.

### 2. Hardware Platform

#### 2.1 Core Components

| Component | Specification | Notes |
| --- | --- | --- |
| MCU | ESP32 WROOM-32 DevKit (Type-C) | Dual-core Xtensa @ 240 MHz, 4MB Flash, Wi-Fi + BT 4.2 |
| LoRa Radio | SX1262 / LLCC68 / SX1268 module | 868/915 MHz depending on region, +22 dBm TX |
| Joystick | KY-023 dual-axis analog + button | Connected to ADC1 channels |
| Buttons | 2× tactile switches (Home, Back) | Active LOW with internal pullup |
| Tilt Sensor | SW-520D ball tilt switch | GPIO16, generates joystick movement when tilted |
| Power | 3.7V LiPo + TP4056 charge controller | Or USB power via DevKit |
| Antenna | u.FL or SMA, tuned for LoRa frequency | **Required** for any transmission |

#### 2.2 Pin Assignments

```
ESP32 WROOM-32 Pin Map
──────────────────────

LoRa Radio (SPI - VSPI):
  GPIO18  →  SCK
  GPIO19  →  MISO
  GPIO23  →  MOSI
  GPIO5   →  NSS (CS)
  GPIO26  →  DIO1 (interrupt)
  GPIO27  →  BUSY
  GPIO14  →  RESET
  3.3V    →  VCC
  GND     →  GND

Joystick (ADC1 - works with WiFi/BLE):
  GPIO34  →  VRx (X-axis)  [ADC1_CH6, input only]
  GPIO35  →  VRy (Y-axis)  [ADC1_CH7, input only]
  GPIO32  →  SW (button)   [internal pullup]
  3.3V    →  +V
  GND     →  GND

Buttons:
  GPIO33  →  Home button   [internal pullup, to GND]
  GPIO25  →  Back button   [internal pullup, to GND]

Tilt Sensor (SW-520D):
  GPIO16  →  Tilt sensor   [internal pullup, active LOW when tilted]
  GND     →  GND
  3.3V    →  VCC (optional, if sensor needs power)

Battery Monitoring (optional):
  GPIO36  →  Voltage divider midpoint (100kΩ + 100kΩ)

Status LED:
  GPIO2   →  Onboard LED (active HIGH on most devkits)
```

#### 2.3 Wiring Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                     Partner Device Assembly                         │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   ESP32 WROOM-32 DevKit                      │   │
│  │                                                              │   │
│  │   3V3 ●────┬──────────────────────────────────┬──● VIN (5V)  │   │
│  │   GND ●────┼───────────┬───────────┬──────────┼──● GND       │   │
│  │            │           │           │          │              │   │
│  │  IO18 ●────┼───● SCK   │           │          │              │   │
│  │  IO19 ●────┼───● MISO  │  SX1262   │          │              │   │
│  │  IO23 ●────┼───● MOSI  │  LoRa     │          │              │   │
│  │   IO5 ●────┼───● NSS   │  Module   │          │              │   │
│  │  IO26 ●────┼───● DIO1  │           │          │              │   │
│  │  IO27 ●────┼───● BUSY  │    🔌ANT  │          │              │   │
│  │  IO14 ●────┼───● RST   └───────────┘          │              │   │
│  │            │                                   │              │   │
│  │  IO34 ●────┼───● VRx ┐                        │              │   │
│  │  IO35 ●────┼───● VRy ├─ KY-023 Joystick       │              │   │
│  │  IO32 ●────┼───● SW  ┘      🕹️                │              │   │
│  │            │                                   │              │   │
│  │  IO33 ●────┼───● Home Button ─┐               │              │   │
│  │  IO25 ●────┼───● Back Button ─┴─● GND         │              │   │
│  │            │                                   │              │   │
│  │  IO16 ●────┼───● SW-520D Tilt Sensor          │              │   │
│  │            │         (active LOW)              │              │   │
│  │  IO36 ●────┼───● Battery voltage divider      │              │   │
│  │            │         (optional)               │              │   │
│  │   IO2 ●────┼───● Status LED (onboard)         │              │   │
│  │            │                                   │              │   │
│  └────────────┴───────────────────────────────────┴──────────────┘   │
│                           │                                         │
│                      USB-C (power/programming)                      │
│                                                                     │
│  ┌─────────────────┐                                                │
│  │  3.7V LiPo      │  (Optional battery for portable use)           │
│  │  + TP4056 BMS   │                                                │
│  └─────────────────┘                                                │
└─────────────────────────────────────────────────────────────────────┘
```

#### 2.4 LoRa Frequency Selection

| Region | Frequency | ISM Band |
| --- | --- | --- |
| Americas (US, CA, SA) | 915 MHz | FCC Part 15 |
| Europe, Africa, Middle East | 868 MHz | ETSI |
| Asia (varies by country) | 433 MHz or 868 MHz | Check local regulations |

**Important:** Use an antenna tuned for your frequency band. Operating without an antenna can damage the LoRa module.

### 3. Firmware Architecture

The partner device runs a **modified Meshtastic firmware** with custom modules for joystick input and main device BLE bridging.

#### 3.1 Firmware Structure

```
meshtastic-firmware/  (fork of github.com/meshtastic/firmware)
├── platformio.ini
├── variants/
│   └── translator_partner/
│       ├── variant.h          # Pin definitions
│       └── platformio.ini     # Build configuration
└── src/
    └── modules/
        ├── JoystickInputModule.cpp   # Joystick ADC + button handling
        ├── JoystickInputModule.h
        ├── MainDeviceBridgeModule.cpp # Custom BLE GATT for main device
        └── MainDeviceBridgeModule.h
```

#### 3.2 Custom Modules

**JoystickInputModule**
- Reads joystick X/Y axes from ADC1 at 100 Hz
- Applies deadzone filtering (±8%)
- Normalizes values to -100..+100 range
- Detects button press, double-press, and long-press events
- Publishes `JoystickEvent` via BLE to main device

**MainDeviceBridgeModule**
- Creates custom BLE GATT services for main device communication
- Bridges incoming Meshtastic text messages to BLE notifications
- Receives outgoing messages from main device via BLE writes
- Maintains connection state and heartbeat

### 4. Communication Protocol

The partner device communicates with the main device (pi wrist computer) via **USB Serial** at 115200 baud. Joystick events are sent as 8-byte binary packets.

#### 4.1 USB Serial Protocol

**JoystickEvent Packet (8 bytes):**
```
Offset  Size    Type      Description
0       1       int8_t    X-axis: -100 (left) to +100 (right)
1       1       int8_t    Y-axis: -100 (down) to +100 (up)
2       1       uint8_t   Button bitmask (bit0=press, bit1=double, bit2=long, bit3=home, bit4=back)
3       1       uint8_t   Context layer (0=global, 1=text, 2=csv, 3=modifier, 4=mesh_compose, 5=mesh_inbox)
4-7     4       uint32_t  Sequence number (little-endian)
```

The device sends joystick events at 100 Hz (every 10ms) when movement or button state changes.

**Note:** BLE communication is optional and can be disabled by setting `HAS_MAIN_DEVICE_BRIDGE` to 0 in `variant.h`.

### 5. BLE Protocol Extension (Optional)

If BLE is enabled, the partner device extends the existing BLE partner protocol with a new **Mesh Relay Service**.

#### 4.1 Service UUID

| Service | UUID |
| --- | --- |
| Mesh Relay | `4f9a0030-8c3f-4a0e-89a7-6d277cf9a000` |

#### 4.2 Characteristics

| Characteristic | UUID Suffix | Properties | Max Size | Description |
| --- | --- | --- | --- | --- |
| MeshInbox | `...0031...` | Notify | 256 B | Incoming mesh messages |
| MeshSend | `...0032...` | Write | 256 B | Outgoing mesh messages |
| MeshStatus | `...0033...` | Notify, Read | 64 B | Radio/mesh status |
| NodeList | `...0034...` | Read | 512 B | Known mesh nodes |

#### 4.3 Payload Schemas (CBOR)

**MeshInbox** (Partner → Main):
```json
{
  "id": 2847561234,
  "from": "!abcd1234",
  "from_name": "Bob",
  "to": "^all",
  "msg": "Hello from the mesh!",
  "channel": 0,
  "rssi": -92,
  "snr": 6.25,
  "ts": 1732691234
}
```

**MeshSend** (Main → Partner):
```json
{
  "seq": 101,
  "to": "^all",
  "msg": "Reply from translator",
  "channel": 0,
  "want_ack": true
}
```

**MeshStatus**:
```json
{
  "radio_on": true,
  "connected": true,
  "my_id": "!1234abcd",
  "my_name": "Translator",
  "nodes_heard": 5,
  "channel_name": "LongFast"
}
```

### 6. Message Flow

#### 5.1 Receiving Mesh Messages

```
LoRa antenna
    │
    ▼
┌───────────────────────────────────┐
│  Meshtastic Radio Layer           │
│  - Decrypt packet                 │
│  - Validate routing               │
└───────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────┐
│  MainDeviceBridgeModule           │
│  - Format CBOR payload            │
│  - Send BLE notification          │
└───────────────────────────────────┘
    │
    ▼ BLE (MeshInbox notify)
    │
┌───────────────────────────────────┐
│  Main Device - mesh_client        │
│  - Parse CBOR                     │
│  - Queue for display              │
│  - Play notification sound        │
└───────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────┐
│  Transparent OLED Display         │
│  "Bob: Hello from the mesh!"      │
└───────────────────────────────────┘
```

#### 5.2 Sending Mesh Messages

```
┌───────────────────────────────────┐
│  Main Device - Text Editor        │
│  User types message via:          │
│  - BLE keyboard, or               │
│  - On-screen keyboard (joystick)  │
└───────────────────────────────────┘
    │
    ▼ User confirms send
    │
┌───────────────────────────────────┐
│  Main Device - mesh_client        │
│  - Build CBOR payload             │
│  - Write to MeshSend char         │
└───────────────────────────────────┘
    │
    ▼ BLE (MeshSend write)
    │
┌───────────────────────────────────┐
│  MainDeviceBridgeModule           │
│  - Parse CBOR                     │
│  - Create Meshtastic packet       │
│  - Queue for transmission         │
└───────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────┐
│  Meshtastic Radio Layer           │
│  - Encrypt packet                 │
│  - Transmit via LoRa              │
└───────────────────────────────────┘
    │
    ▼
LoRa antenna → Mesh network
```

### 7. UI Integration on Main Device

#### 6.1 Layer System

The main device uses joystick "layers" to switch input contexts:

| Layer | Value | Purpose |
| --- | --- | --- |
| Global | 0 | System menus, scene switching |
| Text Editor | 1 | Document editing |
| CSV Editor | 2 | Spreadsheet navigation |
| Modifier | 3 | Gesture combinations |
| **Mesh Compose** | **4** | Compose/send mesh messages |
| **Mesh Inbox** | **5** | Browse received messages |

#### 6.2 Mesh Compose Mode

- Activated via: Long-press Home button, or menu selection
- Joystick controls on-screen keyboard
- Short press: select character
- Long press: send message
- Back button: cancel/return

#### 6.3 Mesh Inbox Mode

- Activated via: Menu selection, or notification tap
- Joystick up/down: scroll through messages
- Short press: view full message / reply
- Back button: return to previous screen

### 8. Building the Partner Device Firmware

#### 7.1 Prerequisites

1. Install PlatformIO CLI or VS Code extension
2. Clone Meshtastic firmware:
   ```bash
   git clone https://github.com/meshtastic/firmware.git meshtastic-partner
   cd meshtastic-partner
   ```

#### 7.2 Add Custom Variant

Create `variants/translator_partner/variant.h`:
```cpp
#pragma once

#define MESHTASTIC_NAME "translator-partner"

// LoRa Radio (VSPI)
#define USE_SX1262
#define LORA_SCK   18
#define LORA_MISO  19
#define LORA_MOSI  23
#define LORA_CS    5
#define SX126X_CS     LORA_CS
#define SX126X_DIO1   26
#define SX126X_BUSY   27
#define SX126X_RESET  14

// Joystick
#define HAS_JOYSTICK           1
#define JOYSTICK_X_PIN         34
#define JOYSTICK_Y_PIN         35
#define JOYSTICK_BTN_PIN       32
#define JOYSTICK_CENTER        2048
#define JOYSTICK_DEADZONE      164

// Buttons
#define BUTTON_HOME_PIN        33
#define BUTTON_BACK_PIN        25

// Battery
#define BATTERY_PIN            36
#define ADC_MULTIPLIER         2.0

// No screen
#define HAS_SCREEN             0
#define HAS_GPS                0

// LED
#define LED_PIN                2

// BLE
#define HAS_MAIN_DEVICE_BRIDGE 1
#define BLE_NAME               "TransPartner"
```

Create `variants/translator_partner/platformio.ini`:
```ini
[env:translator-partner]
extends = esp32_base
board = esp32dev

build_flags = 
    ${esp32_base.build_flags}
    -D TRANSLATOR_PARTNER
    -D HAS_JOYSTICK=1
    -D HAS_MAIN_DEVICE_BRIDGE=1
    -I variants/translator_partner
```

#### 7.3 Build and Flash

```bash
pio run -e translator-partner
pio run -e translator-partner -t upload
```

### 9. Bill of Materials

| Part | Quantity | Est. Price | Source |
| --- | --- | --- | --- |
| ESP32 WROOM-32 DevKit (Type-C) | 1 | $5-8 | AliExpress |
| SX1262/LLCC68 LoRa module (915/868 MHz) | 1 | $4-8 | AliExpress |
| KY-023 Joystick module | 1 | $2 | AliExpress |
| Tactile buttons 6mm | 2 | $0.50 | AliExpress |
| 3.7V LiPo battery (500-1000mAh) | 1 | $5-10 | AliExpress |
| TP4056 USB charge module | 1 | $0.50 | AliExpress |
| u.FL or SMA antenna (tuned) | 1 | $2-3 | AliExpress |
| Perfboard + wires | 1 | $2 | Local/AliExpress |
| **Total** | | **~$20-35** | |

### 10. Safety and Regulatory Notes

1. **Antenna required**: Never power the LoRa module without an antenna connected.
2. **Frequency compliance**: Use the correct frequency for your region.
3. **Transmission power**: Default Meshtastic settings comply with ISM band limits.
4. **Battery safety**: Use batteries with built-in protection circuits; do not overcharge or puncture.

### 11. Future Enhancements

- [ ] Haptic feedback motor for message notifications
- [ ] GPS module for location sharing
- [ ] E-ink display for message preview on partner device
- [ ] Solar charging for extended off-grid use
- [ ] Encryption key management via main device UI

