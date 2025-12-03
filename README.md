# ESP32 Smart Translator & Display

Artifacts in this repo track the concept, firmware scaffold, and collaboration docs for the transparent OLED Japanese↔English translator with smart notification and document features.

## Repo Layout
- `docs/esp32-smart-translator-plan.md` – end-to-end product concept, hardware, software, and testing strategy.
- `docs/ble-partner-protocol.md` – BLE GATT schema and lifecycle for the partner ESP32 controller.
- `docs/partner-device-meshtastic.md` – partner device hardware and Meshtastic LoRa mesh integration.
- `docs/development-roadmap.md` – phased schedule and priorities.
- `docs/editors-spec.md` – functional spec for the text processor and CSV editor modules.
- `docs/joystick-control.md` – joystick hardware + UX map for the external controller ESP32 (primary input across the whole UI + on-screen keyboard fallback).
- `firmware/` – ESP-IDF project scaffold for the main device firmware (`idf.py build` ready once ESP-IDF is installed).
- `partner-firmware/` – Meshtastic-based firmware for the partner ESP32 with joystick and LoRa mesh.

## Getting Started

### Main Device Firmware
1. Install ESP-IDF 5.x and export the environment (`. $IDF_PATH/export.sh`).
2. `cd firmware && idf.py set-target esp32 && idf.py build`.
3. Iterate on components under `components/` (editors, document manager, control link, mesh client) and tasks in `main/app_main.c`.

### Partner Device Firmware
1. Install PlatformIO CLI (`pip install platformio`).
2. Run the setup script: `cd partner-firmware && ./setup-meshtastic-fork.sh`.
3. Build and flash: `cd meshtastic-fork && pio run -e translator-partner -t upload`.

See `partner-firmware/README.md` for detailed instructions.