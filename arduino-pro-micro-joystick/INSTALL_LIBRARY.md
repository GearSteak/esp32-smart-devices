# Installing the Correct Joystick Library

Giuseppe Martini's library is for **reading** joysticks, not **emulating** them as USB devices.

You need the **Arduino Joystick Library by MHeironimus** for USB HID joystick emulation.

## Manual Installation

1. **Download the library:**
   - Go to: https://github.com/MHeironimus/ArduinoJoystickLibrary
   - Click "Code" → "Download ZIP"
   - Save the ZIP file

2. **Install in Arduino IDE:**
   - Open Arduino IDE
   - Go to: Sketch → Include Library → Add .ZIP Library
   - Select the downloaded ZIP file
   - Restart Arduino IDE

3. **Verify installation:**
   - Go to: Sketch → Include Library
   - You should see "Joystick" in the list (by MHeironimus)

4. **Compile the code** - it should work now!

## Alternative: Use Keyboard/Mouse Instead

If you can't install the library, we can use the built-in Keyboard/Mouse libraries instead. The code is already created - just use the version that uses Keyboard.h and Mouse.h instead of Joystick.h.

