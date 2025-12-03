#!/bin/bash
#
# Setup script for Translator Partner Device Firmware
# 
# This script clones the Meshtastic firmware and integrates
# the custom joystick and BLE bridge modules.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MESHTASTIC_DIR="${SCRIPT_DIR}/meshtastic-fork"
MESHTASTIC_REPO="https://github.com/meshtastic/firmware.git"

echo "========================================"
echo "Translator Partner Device Setup"
echo "========================================"
echo ""

# Check for PlatformIO
if ! command -v pio &> /dev/null; then
    echo "ERROR: PlatformIO CLI not found."
    echo "Install it with: pip install platformio"
    echo "Or install the VS Code extension."
    exit 1
fi

# Clone Meshtastic if not already present
if [ -d "$MESHTASTIC_DIR" ]; then
    echo "Meshtastic directory exists, updating..."
    cd "$MESHTASTIC_DIR"
    git pull
else
    echo "Cloning Meshtastic firmware..."
    git clone --depth 1 "$MESHTASTIC_REPO" "$MESHTASTIC_DIR"
fi

cd "$MESHTASTIC_DIR"

# Copy custom variant
echo ""
echo "Installing translator-partner variant..."
mkdir -p variants/translator_partner
cp -v "${SCRIPT_DIR}/variants/translator_partner/variant.h" variants/translator_partner/
cp -v "${SCRIPT_DIR}/variants/translator_partner/platformio.ini" variants/translator_partner/

# Copy custom modules
echo ""
echo "Installing custom modules..."
cp -v "${SCRIPT_DIR}/src/modules/JoystickInputModule.h" src/modules/
cp -v "${SCRIPT_DIR}/src/modules/JoystickInputModule.cpp" src/modules/
cp -v "${SCRIPT_DIR}/src/modules/MainDeviceBridgeModule.h" src/modules/
cp -v "${SCRIPT_DIR}/src/modules/MainDeviceBridgeModule.cpp" src/modules/
cp -v "${SCRIPT_DIR}/src/modules/TranslatorPartnerInit.cpp" src/modules/

# Add translator-partner to platformio.ini if not present
if ! grep -q "translator-partner" platformio.ini; then
    echo ""
    echo "Adding translator-partner environment to platformio.ini..."
    cat >> platformio.ini << 'EOF'

; ============================================================================
; Translator Partner Device
; ============================================================================

[env:translator-partner]
extends = env:esp32-s3
board = esp32dev
board_build.mcu = esp32

build_flags = 
    ${env:esp32-s3.build_flags}
    -D TRANSLATOR_PARTNER=1
    -D HAS_JOYSTICK=1
    -D HAS_MAIN_DEVICE_BRIDGE=1
    -D MESHTASTIC_EXCLUDE_SCREEN=1
    -D MESHTASTIC_EXCLUDE_GPS=1
    -I variants/translator_partner

lib_deps = 
    ${env:esp32-s3.lib_deps}

monitor_speed = 115200
monitor_filters = esp32_exception_decoder

upload_speed = 921600
EOF
fi

echo ""
echo "========================================"
echo "Setup complete!"
echo "========================================"
echo ""
echo "To build the firmware:"
echo "  cd ${MESHTASTIC_DIR}"
echo "  pio run -e translator-partner"
echo ""
echo "To flash:"
echo "  pio run -e translator-partner -t upload"
echo ""
echo "To monitor serial:"
echo "  pio device monitor"
echo ""

