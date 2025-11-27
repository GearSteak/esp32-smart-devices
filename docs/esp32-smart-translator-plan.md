## ESP32 Transparent Translator & Smart Display

### 1. Product Intent
- Wearable or desk companion that translates Japanese ↔ English speech/text, mirrors high-signal phone notifications, and edits lightweight TXT/CSV documents.
- Uses an ESP32 WROVER-CAM (8 MB PSRAM) with transparent 128×64 OLED so text floats within the user’s field of view.
- Operates standalone on Wi‑Fi, while leveraging a phone companion app for notifications, credentials, and heavy ML workloads.
- Connects to BLE keyboards for input and a partner ESP32 device (BLE link) that can act as remote controller, sensor pod, or always-on microphone.

### 2. Hardware Platform
| Subsystem | Components | Notes |
| --- | --- | --- |
| Core MCU | ESP32 WROVER-CAM module | Dual-core, Wi‑Fi + BLE, 8 MB PSRAM for frame buffers/OCR, onboard camera for Kanji capture. |
| Display | 128×64 transparent OLED (SPI) | Choose panel with >60% transparency. Need level shifting + dimming FET for readability vs. see-through. |
| Audio I/O | I²S MEMS mic (top-port) + I²S class‑D amp + bone-conduction transducer or micro speaker | Enables speech capture and spoken prompts. Add analog mic bias disable to save power. |
| Storage | microSD slot (wired to ESP32 SDMMC) + 4 MB flash partitions + SPIFFS/LittleFS | SD stores offline dictionaries, cached translations, documents. Flash partitioned for dual OTA slots. |
| Inputs | Capacitive swipe strip, 3 tact buttons, BLE HID keyboards, partner ESP32 controller over BLE | Joystick-equipped partner ESP32 is the primary input (scrolling, menus, OSK); keyboards are optional add-ons. |
| Sensors | Onboard camera, ambient light sensor (ALS), IMU optional | ALS auto-adjusts OLED brightness; IMU for gesture-based UI (optional). |
| Power | 3.7 V LiPo, USB‑C charging (5 V), fuel gauge (MAX17048) | Budget ~350 mA peak with Wi‑Fi + audio + display. Support sleep states <10 mA. |

### 3. Connectivity & Partner Device Strategy
- **Wi‑Fi Station**: default internet link for translation APIs and OTA updates. AP fallback for provisioning.
- **BLE**
  - **Phone Companion**: GATT service for notification push, file transfer, credential sync. Phone app also proxies REST translation/OCR when Wi‑Fi unavailable.
  - **BLE Keyboards**: ESP32 central role using NimBLE stack for reduced RAM.
  - **Partner ESP32**: Dedicated BLE connection with custom GATT profile (CBOR payloads). Roles: remote keypad, sensor streamer, wake-word audio front-end. Use encrypted pairing and persistent bonding.
- **Cloud endpoints**: REST/gRPC translation (DeepL/Google), optional MQTT for push configuration.

### 4. Software Architecture (ESP32, ESP-IDF)
| Layer | Responsibilities |
| --- | --- |
| Board Support | SPI display driver w/ double buffer, SDMMC driver, I²S audio pipeline, GPIO abstraction for buttons/ALS/IMU. |
| Services (FreeRTOS tasks) | Display/UI task, Connectivity task (Wi‑Fi/BLE state machine), Translation task (queue-based), Notification router, Storage manager, Power supervisor. |
| Data Pipes | Message queues + event groups. Use central event dispatcher to synchronize UI state, translation results, and notifications. |
| OTA & Security | `esp_https_ota` with pinned certs, SPIFFS config encrypted via NVS key, BLE numeric-comparison pairing, hashed SD document index. |

#### Translation Pipeline
1. Inputs: microphone audio chunks, BLE text, camera frames.
2. Local processing: VAD/noise suppression, quick kanji lookup (tiny on-device OCR for single characters), transliteration.
3. Cloud/Phone offload: speech-to-text + translation APIs via Wi‑Fi or phone relay.
4. Output: bilingual text lines rendered on OLED + optional spoken audio.
5. Cache: frequently used phrases stored on SD for offline fallback.

#### Notification & Document UX
- **Notification scenes**: prioritize critical apps, offer quick-reply templates via joystick or BLE keyboard.
- **Document editor**: minimalist text mode with command palette, autosave snapshots to SD, version tags in metadata JSON. CSV mode offers row/column navigation and quick chart preview (phone renders chart, device displays summary). On-screen keyboard is fully joystick-controlled when no BLE keyboard is paired.

### 5. Companion Phone App
- Cross-platform (Flutter/React Native) to minimize duplication.
- Features: credential provisioning, notification relay (ANCS on iOS, Notification Listener on Android), translation/OCR proxy, SD file browser/sync to cloud drives, partner-device management.
- Provides hotspot credentials and user account tokens securely over BLE.

### 6. Development Workflow
1. **BSP Bring-up**: validate power tree, display SPI timings, SD throughput, audio paths.
2. **Connectivity Stack**: implement Wi‑Fi provisioning + BLE roles; build mock partner device firmware.
3. **Core Services**: UI task framework, translation pipeline scaffolding, storage manager.
4. **Companion App MVP**: notifications + credential provisioning.
5. **Feature Iteration**: document editor, CSV tooling, camera-based translation, partner-device special modes.
6. **Optimization**: power profiling, memory tuning, usability polish.

Tooling: ESP-IDF 5.x, `idf.py flash monitor`, Unity/CMock for unit tests, hardware-in-loop rigs for BLE/regression tests, automated OTA pipeline for nightly builds.

### 7. Testing Plan
- **Unit**: driver mocks, translation pipeline interfaces, storage indexer.
- **Integration**: Wi‑Fi/BLE coexistence stress, SD endurance (fsck + CRC), UI latency under translation load (<150 ms frame updates).
- **System**: multilingual scenarios (speech vs. text), notification storms, partner-device loss/reconnect, OTA recovery.
- **Field**: readability in varied lighting, battery endurance for translator vs. passive notification mode.

### 8. Risks & Mitigations
- **Cloud dependency** → Cache top phrases + allow phone-offload fallback.
- **Transparent OLED visibility outdoors** → ALS-driven brightness + optional contrast film accessory.
- **BLE congestion (phone, keyboard, partner)** → Use connection parameter scheduling, prioritize notification channel, implement reconnect backoff.
- **Memory pressure (camera + UI)** → Reuse PSRAM pools, disable camera task outside capture mode, compress SD caches.
- **Security of documents/notifications** → Enforce BLE bonding, encrypt SD metadata, support PIN unlock for editor mode.

### 9. Next Steps
1. Finalize pin map + schematic (focus on BLE antenna isolation and display flex routing).
2. Build ESP-IDF BSP repo structure (drivers/, components/, main/).
3. Prototype BLE control protocol shared between main + partner ESP32.
4. Draft companion app UX flows for notifications and translation relay.
5. Define MVP success metrics (translation latency, notification delivery rate, editor usability).
