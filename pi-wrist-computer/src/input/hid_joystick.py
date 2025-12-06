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
        self.enabled = config.get('enabled', True) and EVDEV_AVAILABLE
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
        self._device = None
        self._read_thread = None
        self._stop_event = threading.Event()
        
        if self.enabled:
            self._start_read_thread()
    
    def _find_joystick_device(self) -> Optional[str]:
        """Auto-detect mouse/keyboard device (Arduino Pro Micro)."""
        if not EVDEV_AVAILABLE:
            return None
        
        # Try to find mouse device (Arduino Pro Micro will show up as mouse)
        try:
            import glob
            # Look for mouse devices
            mouse_devices = glob.glob('/dev/input/event*')
            for path in mouse_devices:
                try:
                    device = InputDevice(path)
                    # Check if it has mouse capabilities
                    if ecodes.EV_REL in device.capabilities() and ecodes.EV_KEY in device.capabilities():
                        # Check if it's likely our Arduino (has mouse buttons and relative movement)
                        caps = device.capabilities()
                        if ecodes.BTN_LEFT in caps.get(ecodes.EV_KEY, []):
                            print(f"HID Joystick: Found mouse device at {path}")
                            return path
                except:
                    pass
        except:
            pass
        
        # Fallback: try common mouse paths
        common_paths = ['/dev/input/mouse0', '/dev/input/mice']
        for path in common_paths:
            try:
                device = InputDevice(path)
                print(f"HID Joystick: Found mouse at {path}")
                return path
            except:
                pass
        
        print("HID Joystick: No mouse device found")
        return None
    
    def _start_read_thread(self):
        """Start joystick reading thread."""
        if self._read_thread and self._read_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._read_thread.start()
    
    def _read_loop(self):
        """Main joystick reading loop."""
        while not self._stop_event.is_set():
            try:
                if not self._connected:
                    self._connect()
                
                if self._connected and self._device:
                    try:
                        # Read events (non-blocking)
                        for event in self._device.read_loop():
                            if self._stop_event.is_set():
                                break
                            self._handle_event(event)
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
        if not EVDEV_AVAILABLE:
            print("HID Joystick: evdev not available - install: pip3 install evdev")
            return
        
        try:
            # Find device
            path = self.device_path
            if not path:
                path = self._find_joystick_device()
            
            if not path:
                return
            
            # Open device
            self._device = InputDevice(path)
            print(f"HID Joystick: Connected to {path}")
            print(f"HID Joystick: Device name: {self._device.name}")
            print(f"HID Joystick: Device capabilities: {list(self._device.capabilities().keys())}")
            self._connected = True
            
        except Exception as e:
            print(f"HID Joystick: Connection failed: {e}")
            self._connected = False
    
    def _handle_event(self, event):
        """Handle input event from mouse/keyboard."""
        # Debug: print first few events to verify reception
        if not hasattr(self, '_debug_event_count'):
            self._debug_event_count = 0
        self._debug_event_count += 1
        if self._debug_event_count <= 10:
            print(f"HID Joystick: Event #{self._debug_event_count} - type={event.type} code={event.code} value={event.value}")
        
        if event.type == ecodes.EV_REL:
            # Mouse relative movement
            if event.code == ecodes.REL_X:
                # X movement
                dx = int(event.value * self.sensitivity)
                with self._lock:
                    self._x += dx
                    if dx != 0:
                        if self._debug_event_count <= 10:
                            print(f"HID Joystick: X movement: {dx}")
                        self._notify_move()
            elif event.code == ecodes.REL_Y:
                # Y movement
                dy = int(event.value * self.sensitivity)
                with self._lock:
                    self._y += dy
                    if dy != 0:
                        if self._debug_event_count <= 10:
                            print(f"HID Joystick: Y movement: {dy}")
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
    
    def _notify_move(self):
        """Notify move callbacks."""
        for cb in self._move_callbacks:
            try:
                cb(self._x, self._y)
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
                self._device.close()
            except:
                pass
        if self._read_thread:
            self._read_thread.join(timeout=2)
        self._connected = False

