## BLE Partner ESP32 Protocol

### Roles
- **Main device**: GATT server hosting Translation, Notification, and Control services; also GATT client subscribing to partner telemetry.
- **Partner ESP32**: GATT server exposing Remote Input + Sensor streams; optional client for haptic notifications.

### Connection Lifecycle
1. BLE advertising from main device with custom service UUID; partner initiates pairing on first boot.
2. Numeric-comparison pairing with bonding (IO capability: DisplayYesNo). Store keys in NVS.
3. On reconnect, both sides negotiate connection parameters prioritizing low latency (interval 24–30 ms, latency 0–2, timeout 4000 ms).
4. If link drops >5 s, partner enters slow-advertise; main device issues reconnect attempts with exponential backoff.

### GATT Services
| Service | UUID (128-bit) | Characteristics | Purpose |
| --- | --- | --- | --- |
| Remote Input | `4f9a0001-8c3f-4a0e-89a7-6d277cf9a000` | `JoystickEvent` (notify, 6 B), `KeypadEvent` (notify, 20 B), `GestureEvent` (notify), `HIDReport` (write w/ resp) | Joystick-driven navigation plus button/gesture events or mini-HID packets. |
| Sensor Hub | `4f9a0010-8c3f-4a0e-89a7-6d277cf9a000` | `EnvSample` (notify), `IMUSample` (notify) | Stream environmental or IMU data for context-aware UI. |
| Command & Sync | `4f9a0020-8c3f-4a0e-89a7-6d277cf9a000` | `Command` (write), `Ack` (indicate), `Heartbeat` (notify) | Reliable control messages using CBOR payloads with sequence numbers. |

### Payload Schema (CBOR) & Joystick Frame
```json
{
  "seq": 42,
  "type": "keypad|gesture|cmd|telemetry",
  "ts": 1732691123,
  "body": {
    "...": "Event-specific content"
  }
}
```
- `JoystickEvent` payload (binary) is structured as: `int8 x`, `int8 y`, `uint8 buttons`, `uint8 layer`, `uint16 seq`. Axes normalized to -100…100 with ±8% dead zone, buttons bitmask (bit0=press, bit1=double, bit2=long). Layer codes: 0 global, 1 text editor, 2 CSV editor, 3 modifier.
- Sequence number increments per message; receiver returns ACK containing last seq (Command service `Ack` char).
- Timestamps use UNIX seconds; optional ms extension.
- Commands examples: `{"type":"cmd","body":{"action":"wake_main"}}`, `{"action":"start_stream","sensor":"imu","rate_hz":50}`.

### Reliability & QoS
- For control messages, enable indications to guarantee delivery; partner waits for confirmation or retries after 200 ms.
- For streaming telemetry, notifications suffice; batch small samples (<100 B) to fit within 20 B payload or enable MTU 185.
- Heartbeat interval 2 s; missing 3 beats triggers reconnect procedure.

### Security
- BLE bonding + LTK stored securely; require re-pair after 5 failed auth attempts.
- Command characteristic writes require application-level HMAC (pre-shared key stored in secure NVS) appended to payload.
- On SD-card PIN lock, disable remote commands except `wake_main` until user unlocks locally.

### Firmware Hooks
- Partner device exposes modular callbacks:
  - `on_remote_command(cmd)` to trigger UI changes or macros.
  - `on_sensor_request(sensor_id)` to adjust sampling.
- Main firmware registers service handlers in Connectivity task; events forwarded to translation/UI queues.
