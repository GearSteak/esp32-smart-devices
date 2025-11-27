## Development Roadmap

### Phase 0 – Infrastructure (Week 0-1)
- ✅ Repository + documentation scaffold.
- Set up ESP-IDF toolchain, CI (lint + `idf.py build`), clang-format, pre-commit hooks.
- Hardware bring-up checklist (power, display SPI loopback, SD card detection).

### Phase 1 – Core Platform (Week 2-4)
- Implement BSP drivers (display, SDMMC, audio, ALS, buttons).
- Build FreeRTOS service framework (UI, connectivity, translation, storage, power).
- Integrate Wi‑Fi provisioning (softAP + BLE), basic BLE pairing with phone + keyboard.
- Mock partner ESP32 firmware with protocol defined in `docs/ble-partner-protocol.md`.

### Phase 2 – Translation & Notifications (Week 4-7)
- Audio capture pipeline (VAD, buffering) + REST client scaffolding.
- Hook into phone companion relay + direct Wi‑Fi translation APIs.
- Notification ingestion from phone app, prioritization rules, UI ticker.
- Implement transparent OLED UI scenes + navigation gestures.

### Phase 3 – Document/CSV Tools (Week 7-9)
- Text editor core (line buffer, command palette, autosave).
- CSV grid view with navigation + quick summary generation (offloaded to phone when needed).
- SD metadata indexer w/ version tags, sync hooks for companion app/cloud drive.

### Phase 4 – Partner Device & UX Polish (Week 9-11)
- Finalize BLE partner firmware (remote keypad, sensor hub, wake-word link).
- Power optimization, sleep/wake flows, ALS-based brightness control.
- Field tests for translation latency, notification reliability, and daylight readability.

### Phase 5 – Release Prep (Week 11-12)
- OTA pipeline hardening, failsafe testing.
- Security review (BLE bonding, encrypted configs, SD PIN lock).
- Manufacturing test plan + documentation (bed-of-nails scripts, calibration steps).
