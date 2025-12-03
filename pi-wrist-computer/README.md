# Pi Wrist Computer

A standalone wearable wrist computer built on Raspberry Pi Zero 2W.

## Features

### Hardware
- **Display**: Waveshare ST7789V 240x320 LCD
- **Input**: CardKB I2C keyboard + 303trackba1 digital trackball
- **GPS**: NEO-6M UART GPS module
- **Power**: UPS-Lite with battery monitoring

### Applications
- **Settings** - System configuration
- **Notes** - Text note-taking
- **Calendar** - Events and reminders
- **Calculator** - Scientific calculator
- **Weather** - Weather forecasts (requires API key)
- **Tetris** - Classic block game
- **Snake** - Classic snake game
- **2048** - Number puzzle game
- **Solitaire** - Klondike solitaire

### Coming Soon
- Email client
- Text-mode web browser
- Spotify control
- Home Assistant integration
- iOS notifications (ANCS)
- Password vault
- GPS navigation

## Hardware Setup

### GPIO Pinout

| GPIO | Function | Device |
|------|----------|--------|
| 2, 3 | I2C | CardKB (0x5F), UPS (0x36) |
| 8, 10, 11 | SPI | ST7789V (MOSI, SCLK, CE0) |
| 24, 25, 27 | GPIO | ST7789V (BL, DC, RST) |
| 5, 6, 13, 19, 26 | GPIO | Trackball (U, D, L, R, Click) |
| 14, 15 | UART | GPS |

### Wiring

**ST7789V Display (240x320):**
```
VCC → 3.3V
GND → GND
DIN → GPIO 10 (SPI MOSI)
CLK → GPIO 11 (SPI SCLK)
CS  → GPIO 8 (SPI CE0)
DC  → GPIO 25
RST → GPIO 27
BL  → GPIO 24
```

**CardKB:**
```
VCC → 3.3V
GND → GND
SDA → GPIO 2
SCL → GPIO 3
```

**Trackball (303trackba1):**
```
VCC → 3.3V
GND → GND
U   → GPIO 5
D   → GPIO 6
L   → GPIO 13
R   → GPIO 19
SW  → GPIO 26
(LED pins not connected)
```

**GPS (NEO-6M):**
```
VCC → 3.3V
GND → GND
TX  → GPIO 15 (RX)
RX  → GPIO 14 (TX)
```

## Installation

### 1. Enable Interfaces

```bash
sudo raspi-config
# Enable: SPI, I2C, Serial Port (disable serial console)
```

### 2. Install Dependencies

```bash
sudo apt update
sudo apt install python3-pip gpsd gpsd-clients libatlas-base-dev

pip3 install -r requirements.txt
```

### 3. Configure GPSD

```bash
sudo nano /etc/default/gpsd
# Set: DEVICES="/dev/ttyAMA0"
# Set: GPSD_OPTIONS="-n"

sudo systemctl enable gpsd
sudo systemctl start gpsd
```

### 4. Run

```bash
python3 main.py
```

## Configuration

Edit `config.yaml` to customize:

```yaml
display:
  brightness: 100
  rotation: 0

input:
  trackball:
    sensitivity: 3
    acceleration: true

apps:
  weather:
    api_key: "YOUR_OPENWEATHERMAP_API_KEY"
    location: "London,UK"
```

## Controls

### Navigation
- **Trackball**: Move cursor / navigate menus
- **Trackball Click**: Select / confirm
- **CardKB arrows**: Navigate
- **Enter**: Confirm
- **ESC**: Back / Home

### In Games
- **Arrows**: Move/direction
- **Space/Click**: Action
- **P**: Pause
- **R**: Restart

## Project Structure

```
pi-wrist-computer/
├── main.py              # Entry point
├── config.yaml          # Configuration
├── requirements.txt     # Python dependencies
├── src/
│   ├── ui/
│   │   ├── display.py   # ST7789V driver
│   │   └── framework.py # UI system
│   ├── input/
│   │   ├── cardkb.py    # Keyboard driver
│   │   └── trackball.py # Trackball driver
│   ├── apps/
│   │   ├── home.py      # Home screen
│   │   ├── settings.py  # Settings app
│   │   ├── notes.py     # Notes app
│   │   └── games/       # Game apps
│   └── services/
│       ├── gps.py       # GPS service
│       └── battery.py   # Battery monitor
└── data/
    ├── notes/           # Saved notes
    └── calendar/        # Calendar events
```

## License

MIT License

