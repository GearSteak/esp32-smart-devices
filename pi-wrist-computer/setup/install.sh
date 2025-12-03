#!/bin/bash
# Pi Wrist Computer - Installation Script

set -e

echo "==================================="
echo "Pi Wrist Computer - Installer"
echo "==================================="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Please run without sudo (it will be requested when needed)"
    exit 1
fi

# Update system
echo ""
echo "Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install dependencies
echo ""
echo "Installing system dependencies..."
sudo apt install -y \
    python3-pip \
    python3-dev \
    python3-pil \
    gpsd \
    gpsd-clients \
    libatlas-base-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    fonts-dejavu

# Install Python packages
echo ""
echo "Installing Python packages..."
pip3 install --user -r requirements.txt

# Enable interfaces
echo ""
echo "Enabling required interfaces..."
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_serial 2  # Enable UART, disable console

# Configure GPSD
echo ""
echo "Configuring GPSD..."
sudo tee /etc/default/gpsd > /dev/null << 'EOF'
# Default settings for the gpsd init script and the hotplug wrapper.
START_DAEMON="true"
GPSD_OPTIONS="-n"
DEVICES="/dev/ttyAMA0"
USBAUTO="true"
GPSD_SOCKET="/var/run/gpsd.sock"
EOF

sudo systemctl enable gpsd
sudo systemctl restart gpsd

# Create data directories
echo ""
echo "Creating data directories..."
mkdir -p data/notes data/calendar

# Create systemd service (optional)
echo ""
echo "Creating systemd service..."
sudo tee /etc/systemd/system/pi-wrist.service > /dev/null << EOF
[Unit]
Description=Pi Wrist Computer
After=network.target gpsd.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/python3 main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo "==================================="
echo "Installation Complete!"
echo "==================================="
echo ""
echo "To run manually:"
echo "  python3 main.py"
echo ""
echo "To enable auto-start on boot:"
echo "  sudo systemctl enable pi-wrist"
echo "  sudo systemctl start pi-wrist"
echo ""
echo "IMPORTANT: Reboot required for interface changes!"
echo "  sudo reboot"

