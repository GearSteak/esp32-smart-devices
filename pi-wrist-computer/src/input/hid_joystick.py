"""
USB HID Input Handler

Reads mouse/keyboard events from USB HID device (Arduino Pro Micro as mouse/keyboard)
using evdev. Compatible with Trackball interface.
"""

import time
import threading
from typing import Callable, Optional

try:
    import evdev
    from evdev import InputDevice, categorize, ecodes
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False
    evdev = None
    InputDevice = None


class HIDJoystick:
    """
    USB HID joystick input handler.
    
    Reads from /dev/input/js0 or similar using evdev.
    Compatible with Trackball interface.
    """
    
    def __init__(self, config: dict):
        """
        Initialize USB HID joystick.
        
        Args:
            config: Configuration dict with:
                - enabled: Enable HID joystick (default: True)
                - device_path: Path to joystick device (default: auto-detect)
                - sensitivity: Movement multiplier (default: 2.0)
                - auto_reconnect: Auto-reconnect on disconnect (default: True)
        """
        print(f"HID Joystick: __init__ called with config: {config}")
        print(f"HID Joystick: EVDEV_AVAILABLE = {EVDEV_AVAILABLE}")
        
        # Allow force-enabling even if evdev isn't available (will fail gracefully later)
        force_enable = config.get('force_enable', False)
        if force_enable:
            print("HID Joystick: FORCE ENABLE - ignoring evdev availability check")
            self.enabled = config.get('enabled', True)
        else:
            self.enabled = config.get('enabled', True) and EVDEV_AVAILABLE
        
        print(f"HID Joystick: enabled = {self.enabled}")
        self.device_path = config.get('device_path', None)  # None = auto-detect
        self.sensitivity = config.get('sensitivity', 2.0)
        self.auto_reconnect = config.get('auto_reconnect', True)
        
        # State
        self._x = 0
        self._y = 0
        self._clicked = False
        self._click_count = 0
        self._home_pressed = False
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Callbacks
        self._move_callbacks = []
        self._click_callbacks = []
        self._key_callbacks = []  # For home/back button
        
        # Device state
        self._connected = False
        self._connecting = False
        self._device = None
        self._read_thread = None
        self._stop_event = threading.Event()
        
        if self.enabled:
            print(f"HID Joystick: Initializing (enabled={self.enabled}, EVDEV_AVAILABLE={EVDEV_AVAILABLE})")
            self._start_read_thread()
        else:
            print("HID Joystick: Disabled")
    
    def _find_joystick_device(self) -> Optional[str]:
        """Auto-detect mouse/keyboard device (Arduino Pro Micro or USB keyboard/trackpad)."""
        if not EVDEV_AVAILABLE:
            return None
        
        # Try to find device with both mouse and keyboard capabilities
        try:
            import glob
            # Look for all input devices
            all_devices = glob.glob('/dev/input/event*')
            print(f"HID Joystick: Scanning {len(all_devices)} input devices...")
            
            for path in sorted(all_devices):
                try:
                    device = InputDevice(path)
                    caps = device.capabilities()
                    
                    # Check if it has both mouse (REL) and keyboard (KEY) capabilities
                    has_mouse = ecodes.EV_REL in caps
                    has_keyboard = ecodes.EV_KEY in caps
                    
                    # Also accept devices with just mouse (for Arduino) or just keyboard+mouse (for USB keyboard/trackpad)
                    # Accept devices with mouse OR keyboard (or both)
                    # This will catch USB keyboard/trackpad (has both) or Arduino (has mouse)
                    if has_mouse or has_keyboard:
                        key_caps = caps.get(ecodes.EV_KEY, [])
                        has_mouse_btn = ecodes.BTN_LEFT in key_caps or ecodes.BTN_MOUSE in key_caps
                        has_keys = ecodes.KEY_A in key_caps or ecodes.KEY_ESC in key_caps or ecodes.KEY_ENTER in key_caps
                        
                        # Prefer devices with both mouse and keyboard (USB keyboard/trackpad)
                        if (has_mouse and has_keyboard) or has_mouse_btn or has_keys:
                            print(f"HID Joystick: Found device: {device.name} at {path}")
                            print(f"  - Has mouse: {has_mouse}, Has keyboard: {has_keyboard}")
                            return path
                except Exception as e:
                    if "Permission denied" not in str(e):
                        pass  # Skip devices we can't read
        
        except Exception as e:
            print(f"HID Joystick: Error scanning devices: {e}")
        
        print("HID Joystick: No keyboard+mouse device found")
        return None
    
    def _start_read_thread(self):
        """Start joystick reading thread."""
        if self._read_thread and self._read_thread.is_alive():
            return
        
        print("HID Joystick: Starting read thread...")
        self._stop_event.clear()
        self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._read_thread.start()
        print("HID Joystick: Read thread started")
    
    def _read_loop(self):
        """Main joystick reading loop."""
        print("HID Joystick: Read loop started")
        while not self._stop_event.is_set():
            try:
                if not self._connected and not self._connecting:
                    print("HID Joystick: Not connected, attempting to connect...")
                    self._connect()
                
                if self._connected and self._device:
                    try:
                        # Read events (blocking, but that's okay in a thread)
                        # Use read_loop() which handles blocking reads
                        for event in self._device.read_loop():
                            if self._stop_event.is_set():
                                break
                            self._handle_event(event)
                    except PermissionError:
                        print("HID Joystick: Permission denied - need root or input group")
                        self._connected = False
                        break
                    except OSError:
                        print("HID Joystick: Device disconnected")
                        self._connected = False
                        if self.auto_reconnect:
                            time.sleep(1)
                else:
                    time.sleep(1)  # Wait before retry
                    
            except Exception as e:
                print(f"HID Joystick error: {e}")
                self._connected = False
                if self.auto_reconnect:
                    time.sleep(2)
    
    def _connect(self):
        """Connect to joystick device."""
        print("HID Joystick: _connect() called")
        if not EVDEV_AVAILABLE:
            print("HID Joystick: ERROR - evdev not available!")
            print("HID Joystick: Install with: pip3 install evdev")
            print("HID Joystick: Or system package: sudo apt-get install python3-evdev")
            print("HID Joystick: Connection will fail without evdev")
            return
        
        self._connecting = True
        try:
            # Find device
            path = self.device_path
            print(f"HID Joystick: device_path from config: {path}")
            if not path:
                print("HID Joystick: No path specified, auto-detecting...")
                path = self._find_joystick_device()
            
            if not path:
                print("HID Joystick: No device found, cannot connect")
                self._connecting = False
                return
            
            # Open device
            self._device = InputDevice(path)
            print(f"HID Joystick: Opened device: {self._device.name} at {path}")
            
            # Try to grab it exclusively (so terminal doesn't consume events)
            try:
                self._device.grab()
                print(f"HID Joystick: Device grabbed exclusively - terminal won't receive events")
            except PermissionError:
                print(f"HID Joystick: WARNING: Could not grab device - need root or input group")
                print(f"HID Joystick: Run: sudo usermod -a -G input $USER (then log out/in)")
                print(f"HID Joystick: Or run program with: sudo python3 main.py")
            except Exception as e:
                print(f"HID Joystick: WARNING: Could not grab device: {e}")
                print(f"HID Joystick: Events may still go to terminal")
            
            print(f"HID Joystick: Device capabilities: {list(self._device.capabilities().keys())}")
            self._connected = True
            self._connecting = False
            print("HID Joystick: Successfully connected!")
            
        except Exception as e:
            print(f"HID Joystick: Connection failed: {e}")
            import traceback
            traceback.print_exc()
            self._connected = False
            self._connecting = False
    
    def _handle_event(self, event):
        """Handle input event from mouse/keyboard."""
        # Debug: print first few events to verify reception
        if not hasattr(self, '_debug_event_count'):
            self._debug_event_count = 0
        self._debug_event_count += 1
        if self._debug_event_count <= 20:
            print(f"HID Joystick: Event #{self._debug_event_count} - type={event.type} (EV_REL={ecodes.EV_REL}, EV_KEY={ecodes.EV_KEY}) code={event.code} value={event.value}")
        
        if event.type == ecodes.EV_REL:
            # Mouse relative movement
            if event.code == ecodes.REL_X:
                # X movement - use value directly (it's already a delta)
                dx = int(event.value * self.sensitivity)
                if dx == 0 and event.value != 0:
                    dx = 1 if event.value > 0 else -1
                with self._lock:
                    self._x += dx
                    if self._debug_event_count <= 20:
                        print(f"HID Joystick: REL_X event: raw_value={event.value}, dx={dx}, total_x={self._x}")
                    if dx != 0:
                        self._notify_move()
            elif event.code == ecodes.REL_Y:
                # Y movement - use value directly (it's already a delta)
                dy = int(event.value * self.sensitivity)
                if dy == 0 and event.value != 0:
                    dy = 1 if event.value > 0 else -1
                with self._lock:
                    self._y += dy
                    if self._debug_event_count <= 20:
                        print(f"HID Joystick: REL_Y event: raw_value={event.value}, dy={dy}, total_y={self._y}")
                    if dy != 0:
                        self._notify_move()
        
        elif event.type == ecodes.EV_KEY:
            # Button/key press/release
            pressed = event.value == 1
            
            if event.code == ecodes.BTN_LEFT or event.code == ecodes.BTN_MOUSE:
                # Left mouse button (Joystick button = Select/Confirm)
                with self._lock:
                    if pressed and not self._clicked:
                        self._clicked = True
                        self._click_count += 1
                        self._notify_click(True)
                    elif not pressed and self._clicked:
                        self._clicked = False
                        self._notify_click(False)
            
            elif event.code == ecodes.KEY_ESC:
                # ESC key (Home button = Back/ESC)
                with self._lock:
                    # Only send on press, not release
                    if pressed and not self._home_pressed:
                        self._home_pressed = True
                        self._notify_key_esc()
                    elif not pressed:
                        self._home_pressed = False
            else:
                # Handle other keyboard keys (from USB keyboard)
                # Convert evdev key codes to our KeyEvent format
                if pressed:
                    self._notify_keyboard_key(event.code)
    
    def _notify_move(self):
        """Notify move callbacks with current delta movement."""
        # Get current accumulated values and reset them
        with self._lock:
            dx = self._x
            dy = self._y
            self._x = 0
            self._y = 0
        
        # Call callbacks with the delta values (not accumulated)
        if dx != 0 or dy != 0:
            for cb in self._move_callbacks:
                try:
                    cb(dx, dy)
                except Exception as e:
                    print(f"HID joystick move callback error: {e}")
    
    def _notify_click(self, pressed: bool):
        """Notify click callbacks."""
        for cb in self._click_callbacks:
            try:
                cb(pressed)
            except Exception as e:
                print(f"HID joystick click callback error: {e}")
    
    def _notify_key_esc(self):
        """Notify key callbacks with ESC key event."""
        from ..input.cardkb import KeyEvent, KeyCode
        import time
        event = KeyEvent(
            code=KeyCode.ESC, 
            char=None,
            is_special=True,
            timestamp=time.time()
        )
        for cb in self._key_callbacks:
            try:
                cb(event)
            except Exception as e:
                print(f"HID joystick key callback error: {e}")
    
    def _notify_keyboard_key(self, key_code):
        """Notify key callbacks with keyboard key event."""
        from ..input.cardkb import KeyEvent, KeyCode
        import time
        
        # Map evdev key codes to our KeyCode enum
        key_map = {
            ecodes.KEY_ESC: KeyCode.ESC,
            ecodes.KEY_ENTER: KeyCode.ENTER,
            ecodes.KEY_BACKSPACE: KeyCode.BACKSPACE,
            ecodes.KEY_TAB: KeyCode.TAB,
            ecodes.KEY_SPACE: KeyCode.SPACE,
            ecodes.KEY_DELETE: KeyCode.DEL,
            ecodes.KEY_UP: KeyCode.UP,
            ecodes.KEY_DOWN: KeyCode.DOWN,
            ecodes.KEY_LEFT: KeyCode.LEFT,
            ecodes.KEY_RIGHT: KeyCode.RIGHT,
        }
        
        # Get mapped code or use raw code
        mapped_code = key_map.get(key_code, key_code)
        
        # Determine if special key
        is_special = mapped_code < 0x20 or mapped_code >= 0x80
        char = '' if is_special else (chr(mapped_code) if 0x20 <= mapped_code < 0x7F else '')
        
        event = KeyEvent(
            code=mapped_code,
            char=char,
            is_special=is_special,
            timestamp=time.time()
        )
        
        for cb in self._key_callbacks:
            try:
                cb(event)
            except Exception as e:
                print(f"HID joystick key callback error: {e}")
    
    # Trackball-compatible interface
    def on_move(self, callback: Callable[[int, int], None]):
        """Register move callback. Called with (x, y) deltas."""
        self._move_callbacks.append(callback)
    
    def on_click(self, callback: Callable[[bool], None]):
        """Register click callback. Called with pressed state."""
        self._click_callbacks.append(callback)
    
    def on_key(self, callback: Callable):
        """Register key callback. Called with KeyEvent for home/back button."""
        self._key_callbacks.append(callback)
    
    def get_delta(self) -> tuple[int, int]:
        """Get and reset accumulated movement."""
        with self._lock:
            dx, dy = self._x, self._y
            self._x = 0
            self._y = 0
            return dx, dy
    
    def is_clicked(self) -> bool:
        """Check if currently clicked."""
        return self._clicked
    
    def reset(self):
        """Reset accumulated movement."""
        with self._lock:
            self._x = 0
            self._y = 0
    
    def shutdown(self):
        """Clean up."""
        self._stop_event.set()
        if self._device:
            try:
                self._device.ungrab()  # Release device
                self._device.close()
            except:
                pass
        if self._read_thread:
            self._read_thread.join(timeout=2)
        self._connected = False

