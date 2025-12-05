"""
BLE Joystick Input Handler

Receives joystick events from ESP32 controller device via BLE
and converts them to trackball-like movement for compatibility
with all existing apps.
"""

import time
import threading
from typing import Callable, Optional
from dataclasses import dataclass

try:
    import bluetooth
    BLE_AVAILABLE = True
except ImportError:
    BLE_AVAILABLE = False
    bluetooth = None


@dataclass
class JoystickState:
    """Current joystick state from ESP32 controller."""
    x: int  # -100 to +100
    y: int  # -100 to +100
    buttons: int  # Bitmask
    layer: int
    seq: int


class BLEJoystick:
    """
    BLE joystick input handler for ESP32 controller.
    
    Connects to ESP32 partner device and receives joystick events,
    converting them to trackball movement deltas.
    """
    
    # ESP32 controller BLE service UUIDs
    REMOTE_INPUT_SERVICE_UUID = "4f9a0001-8c3f-4a0e-89a7-6d277cf9a000"
    JOYSTICK_EVENT_CHAR_UUID = "4f9a0002-8c3f-4a0e-89a7-6d277cf9a000"
    
    # Device name to scan for
    DEVICE_NAME = "TransPartner"
    
    def __init__(self, config: dict):
        """
        Initialize BLE joystick.
        
        Args:
            config: Configuration dict with:
                - enabled: Enable BLE joystick (default: True)
                - device_name: BLE device name to connect to (default: "TransPartner")
                - sensitivity: Movement multiplier (default: 2.0)
                - auto_reconnect: Auto-reconnect on disconnect (default: True)
        """
        self.enabled = config.get('enabled', True) and BLE_AVAILABLE
        self.device_name = config.get('device_name', self.DEVICE_NAME)
        self.sensitivity = config.get('sensitivity', 2.0)
        self.auto_reconnect = config.get('auto_reconnect', True)
        
        # State
        self._x = 0
        self._y = 0
        self._clicked = False
        self._click_count = 0
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Callbacks (compatible with Trackball interface)
        self._move_callbacks = []
        self._click_callbacks = []
        
        # BLE state
        self._connected = False
        self._connecting = False
        self._ble_thread = None
        self._stop_event = threading.Event()
        
        if self.enabled:
            self._start_ble_thread()
    
    def _start_ble_thread(self):
        """Start BLE connection thread."""
        if self._ble_thread and self._ble_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._ble_thread = threading.Thread(target=self._ble_loop, daemon=True)
        self._ble_thread.start()
    
    def _ble_loop(self):
        """Main BLE connection and event loop."""
        while not self._stop_event.is_set():
            try:
                if not self._connected and not self._connecting:
                    self._connect()
                
                if self._connected:
                    # Process BLE events (would need actual BLE implementation)
                    # For now, simulate connection
                    time.sleep(0.1)
                else:
                    time.sleep(1)  # Wait before retry
                    
            except Exception as e:
                print(f"BLE joystick error: {e}")
                self._connected = False
                self._connecting = False
                if self.auto_reconnect:
                    time.sleep(2)  # Wait before reconnect attempt
    
    def _connect(self):
        """Connect to ESP32 controller via BLE."""
        if not BLE_AVAILABLE:
            print("BLE not available - install bluez or pybluez")
            return
        
        self._connecting = True
        try:
            # TODO: Implement actual BLE connection
            # This would use bluez/pybluez to:
            # 1. Scan for device with name "TransPartner"
            # 2. Connect to it
            # 3. Discover services and characteristics
            # 4. Subscribe to JoystickEvent notifications
            # 5. Parse incoming 8-byte joystick events
            
            print(f"BLE joystick: Looking for {self.device_name}...")
            # Placeholder - actual implementation would go here
            # self._connected = True
            
        except Exception as e:
            print(f"BLE joystick connection failed: {e}")
            self._connected = False
        finally:
            self._connecting = False
    
    def _on_joystick_event(self, data: bytes):
        """
        Handle incoming joystick event from ESP32.
        
        Args:
            data: 8-byte joystick event packet:
                [0]: int8_t x (-100 to +100)
                [1]: int8_t y (-100 to +100)
                [2]: uint8_t buttons (bitmask)
                [3]: uint8_t layer
                [4-7]: uint32_t seq (little-endian)
        """
        if len(data) < 8:
            return
        
        # Parse packet
        x = int.from_bytes([data[0]], byteorder='little', signed=True)
        y = int.from_bytes([data[1]], byteorder='little', signed=True)
        buttons = data[2]
        layer = data[3]
        seq = int.from_bytes(data[4:8], byteorder='little')
        
        with self._lock:
            # Convert joystick values to movement deltas
            # Joystick: -100 to +100, Trackball: pixels
            dx = int(x * self.sensitivity / 10)  # Scale to reasonable pixel movement
            dy = int(y * self.sensitivity / 10)
            
            if dx != 0 or dy != 0:
                self._x += dx
                self._y += dy
                self._notify_move()
            
            # Handle button presses (bit0 = press, bit1 = double, bit2 = long)
            if buttons & 0x01:  # Press
                if not self._clicked:
                    self._clicked = True
                    self._click_count += 1
                    self._notify_click(True)
            else:
                if self._clicked:
                    self._clicked = False
                    self._notify_click(False)
    
    def _notify_move(self):
        """Notify move callbacks."""
        for cb in self._move_callbacks:
            try:
                cb(self._x, self._y)
            except Exception as e:
                print(f"BLE joystick move callback error: {e}")
    
    def _notify_click(self, pressed: bool):
        """Notify click callbacks."""
        for cb in self._click_callbacks:
            try:
                cb(pressed)
            except Exception as e:
                print(f"BLE joystick click callback error: {e}")
    
    # Trackball-compatible interface
    def on_move(self, callback: Callable[[int, int], None]):
        """Register move callback. Called with (x, y) deltas."""
        self._move_callbacks.append(callback)
    
    def on_click(self, callback: Callable[[bool], None]):
        """Register click callback. Called with pressed state."""
        self._click_callbacks.append(callback)
    
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
        """Clean up BLE connection."""
        self._stop_event.set()
        if self._ble_thread:
            self._ble_thread.join(timeout=2)
        self._connected = False

