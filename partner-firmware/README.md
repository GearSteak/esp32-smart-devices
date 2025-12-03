# Partner Device Firmware

Meshtastic-based firmware for the ESP32 partner device with joystick control and LoRa mesh networking.

## Features

- **Joystick Input**: 2-axis analog joystick with button for navigation
- **Home/Back Buttons**: Quick access buttons for UI control
- **LoRa Mesh Networking**: Meshtastic-compatible mesh messaging
- **BLE Bridge**: Custom GATT services for main device communication
- **Battery Monitoring**: Optional voltage sensing

## Hardware Requirements

| Component | Specification |
|-----------|---------------|
| MCU | ESP32 WROOM-32 DevKit (Type-C) |
| LoRa | SX1262 / LLCC68 module (868/915 MHz) |
| Joystick | KY-023 dual-axis analog module |
| Buttons | 2× tactile switches (6mm) |
| Antenna | u.FL or SMA, tuned for frequency |
| Power | USB or 3.7V LiPo with TP4056 |

## Pin Configuration

```
LoRa SPI:
  GPIO18 → SCK
  GPIO19 → MISO
  GPIO23 → MOSI
  GPIO5  → CS
  GPIO26 → DIO1
  GPIO27 → BUSY
  GPIO14 → RESET

Joystick:
  GPIO34 → X-axis (ADC)
  GPIO35 → Y-axis (ADC)
  GPIO32 → Button

Buttons:
  GPIO33 → Home
  GPIO25 → Back

Battery (optional):
  GPIO36 → Voltage divider
```

## Setup Instructions

### Option A: Standalone Build (Simplified)

This option builds just the custom modules without full Meshtastic:

```bash
cd partner-firmware
pio run -e translator-partner
pio run -e translator-partner -t upload
```

### Option B: Full Meshtastic Fork (Recommended)

For full mesh networking functionality:

1. **Clone Meshtastic firmware**:
   ```bash
   git clone https://github.com/meshtastic/firmware.git meshtastic-fork
   cd meshtastic-fork
   ```

2. **Copy custom modules**:
   ```bash
   cp -r ../partner-firmware/src/modules/* src/modules/
   cp -r ../partner-firmware/variants/translator_partner variants/
   ```

3. **Build the firmware**:
   ```bash
   pio run -e translator-partner
   ```

4. **Flash to device**:
   ```bash
   pio run -e translator-partner -t upload
   ```

### Option C: Using the Setup Script

```bash
./setup-meshtastic-fork.sh
```

## BLE Services

The partner device exposes these custom GATT services:

### Mesh Relay Service (`4f9a0030-...`)
- `MeshInbox` (notify) - Incoming mesh messages
- `MeshSend` (write) - Outgoing mesh messages
- `MeshStatus` (notify/read) - Network status
- `NodeList` (read) - Known mesh nodes

### Remote Input Service (`4f9a0001-...`)
- `JoystickEvent` (notify) - Joystick position and buttons
- `KeypadEvent` (notify) - Home/Back button events

### Command & Sync Service (`4f9a0020-...`)
- `Ack` (indicate) - Acknowledgments
- `Heartbeat` (notify) - Connection keepalive

## Message Format

### JoystickEvent (8 bytes)
```c
struct {
    int8_t x;        // -100 to +100
    int8_t y;        // -100 to +100
    uint8_t buttons; // Bitmask
    uint8_t layer;   // Context layer
    uint32_t seq;    // Sequence number
}
```

### MeshInbox (CBOR/JSON)
```json
{
  "id": 12345,
  "from": "!abcd1234",
  "from_name": "Bob",
  "msg": "Hello!",
  "rssi": -92,
  "snr": 6.25
}
```

## Debugging

Monitor serial output:
```bash
pio device monitor
```

Enable debug logging:
```bash
pio run -e translator-partner-debug -t upload
```

## Configuration

Edit `variants/translator_partner/variant.h` to customize:
- Pin assignments
- Joystick calibration
- BLE device name
- Radio settings

## Troubleshooting

### No LoRa connectivity
- Verify antenna is connected
- Check SPI wiring (especially CS, DIO1, BUSY)
- Confirm correct frequency for your region

### Joystick not responding
- Check ADC pins (must be ADC1: GPIO32-39)
- Verify 3.3V power to joystick module
- Adjust `JOYSTICK_DEADZONE` if drift occurs

### BLE connection issues
- Ensure main device is scanning for `TransPartner`
- Check BLE advertising is started (LED should blink)
- Try power cycling both devices

## License

This firmware is based on Meshtastic which is licensed under GPL-3.0.
Custom modules are provided under the same license.

## Related Documentation

- [Partner Device Meshtastic Integration](../docs/partner-device-meshtastic.md)
- [BLE Partner Protocol](../docs/ble-partner-protocol.md)
- [Joystick Control Strategy](../docs/joystick-control.md)

