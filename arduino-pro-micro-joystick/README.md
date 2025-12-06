# Arduino Pro Micro Joystick Controller

USB HID joystick controller using Arduino Pro Micro. Works on Raspberry Pi without any drivers!

## Wiring

```
Joystick (KY-023):
  VCC → 5V (or 3.3V)
  GND → GND
  VRX → A0 (X axis)
  VRY → A1 (Y axis)
  SW  → Pin 2 (with internal pull-up)

Buttons:
  Button 1 (Home/Back) → Pin 3 (with internal pull-up)
  (One side to pin, other side to GND)
```

## Installation

1. Install Arduino IDE
2. Install "Joystick" library by Matthew Heironimus
   - Tools → Manage Libraries → Search "Joystick"
3. Select board: Tools → Board → Arduino Leonardo (Pro Micro uses same core)
4. Upload the sketch

## Usage

The Arduino will show up as `/dev/input/js0` on the Pi automatically. No drivers needed!

The Pi code will auto-detect it and use it for joystick input.

## Pin Configuration

- **A0**: Joystick X axis
- **A1**: Joystick Y axis  
- **Pin 2**: Joystick button (Select/Confirm)
- **Pin 3**: Home button (Back/ESC)

## Calibration

The joystick auto-calibrates on startup. Make sure the joystick is centered when you power on the Arduino.

