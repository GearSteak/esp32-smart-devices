## Joystick Control Strategy

The joystick-equipped partner ESP32 is the **primary** input device: it must drive every interaction path (scrolling, menus, dialogs, and the on-screen keyboard whenever no BLE keyboard is paired). Bluetooth keyboards are optional enhancements, not requirements.

### Hardware (Partner ESP32)
- 2-axis analog joystick (X/Y) connected to ADC inputs, plus integrated push button for select/confirm.
- Optional secondary buttons (Home, Back) for quick scene switching.
- Sampling rate: 100 Hz, oversampled/filtered to reduce jitter.
- Dead zone: ±8% around center to avoid drift; values normalized to -100…100.

### Interaction Model
- **Navigation**: joystick deflection emulates directional input for both editors and UI scenes.
  - Up/Down: scroll lines (text) or move rows (CSV).
  - Left/Right: move cursor columns; long-hold triggers word/column jumps.
- **Context Layers**:
  - Global layer (0): default when no editor has focus; controls scene switching and system menus.
  - Text editor layer (1): engaged when text editor active; deflection mapped to cursor movement and selection.
  - CSV editor layer (2): engaged when CSV editor active; column/row navigation.
  - Modifier layer (3): pressing joystick button + deflecting triggers gestures (e.g., button+up = page up).
  - Mesh compose layer (4): compose and send Meshtastic mesh messages.
  - Mesh inbox layer (5): browse and reply to received mesh messages.
- **Selection/Actions**:
  - Short press: confirm / enter edit mode.
  - Long press (700 ms): open command palette.
  - Double press: toggle between text and CSV editors.
  - Press + hold left/right: cycle through saved documents/sheets.
- **On-screen keyboard**:
  - Activated automatically when BLE keyboard is absent or user requests OSK.
  - Radial keyboard layout navigated purely by joystick (deflect to select cluster, press to confirm character).
  - Long-press + Up switches keyboard layers (latin, kana, symbols); long-press + Down toggles predictive suggestions.

### BLE Payloads
- Joystick state published via `Remote Input` service `JoystickEvent` characteristic (notify, 8 B payload):
  ```
  struct {
      int8_t x;   // -100..100
      int8_t y;   // -100..100
      uint8_t buttons; // bit0=press, bit1=double, bit2=long
      uint8_t layer;   // 0=global, 1=text, 2=csv, 3=modifier, 4=mesh_compose, 5=mesh_inbox
      uint32_t seq;
  }
  ```
- Events sent only on state change >2 units or button transitions to save bandwidth.
- Partner keeps recent `seq`; main device ACKs via Command service `Ack`.

### Mapping to Editors
- Text editor converts joystick deltas into cursor/scroll using acceleration curves (faster movement when deflection sustained >400 ms).
- CSV editor treats joystick x/y as column/row navigation with wrap-around off by default.
- Command palette uses radial menu UI; joystick deflection selects wedge, button confirms.

### Mesh Messaging Controls
The partner device includes LoRa mesh networking via Meshtastic. Mesh layers enable composing and reading messages.

#### Mesh Compose Mode (Layer 4)
- **Activation**: Long-press Home button from any screen, or select "New Message" from menu.
- **Navigation**: Joystick controls the on-screen keyboard (radial layout).
- **Character entry**: Short press confirms selected character.
- **Backspace**: Double press deletes last character.
- **Send message**: Long press sends the composed message.
- **Cancel**: Back button exits compose mode without sending.
- **Recipient selection**: Press Home in compose mode to switch between broadcast (^all) and direct message (select from node list).

#### Mesh Inbox Mode (Layer 5)
- **Activation**: New message notification tap, or select "Mesh Inbox" from menu.
- **Navigation**: Up/down scrolls through message list.
- **View message**: Short press opens full message view.
- **Reply**: Long press on a message opens compose mode with recipient pre-filled.
- **Exit**: Back button returns to previous screen.

#### Mesh Status Indicators
- Partner device LED blinks when transmitting/receiving LoRa packets.
- Main device status bar shows: mesh connection status, unread message count, signal strength of last received message.

### Error Handling
- If joystick disconnects, main device falls back to BLE keyboard/gesture input and displays warning banner.
- Partner sends heartbeat containing last joystick status every 2 s; missing 3 heartbeats triggers reconnect.

### Future Enhancements
- Add haptic feedback motor on partner device for confirmation pulses.
- Support macros (e.g., press+hold while drawing circle) that map to editor shortcuts.
- GPS module on partner device for location sharing via Meshtastic.
- Canned responses for quick mesh replies.
- Message encryption key management via main device UI.
