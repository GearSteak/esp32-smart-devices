# ESP32 Smart Translator & Display

Artifacts in this repo track the concept, firmware scaffold, and collaboration docs for the transparent OLED Japanese↔English translator with smart notification and document features.

## Repo Layout
- `docs/esp32-smart-translator-plan.md` – end-to-end product concept, hardware, software, and testing strategy.
- `docs/ble-partner-protocol.md` – BLE GATT schema and lifecycle for the partner ESP32 controller.
- `docs/development-roadmap.md` – phased schedule and priorities.
- `docs/editors-spec.md` – functional spec for the text processor and CSV editor modules.
- `docs/joystick-control.md` – joystick hardware + UX map for the external controller ESP32.
- `firmware/` – ESP-IDF project scaffold for the main device firmware (`idf.py build` ready once ESP-IDF is installed).

## Getting Started
1. Install ESP-IDF 5.x and export the environment (`. $IDF_PATH/export.sh`).
2. `cd firmware && idf.py set-target esp32 && idf.py build`.
3. Iterate on components under `components/` (editors, document manager, control link) and tasks in `main/app_main.c`.