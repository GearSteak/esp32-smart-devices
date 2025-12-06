"""
USB Serial Joystick Input Handler

Receives joystick events from ESP32 controller device via USB Serial
and converts them to trackball-like movement for compatibility
with all existing apps.
"""

import time
import threading
import serial
import serial.tools.list_ports
from typing import Callable, Optional


class USBJoystick:
    """
    USB Serial joystick input handler for ESP32 controller.
    
    Connects to ESP32 partner device via USB Serial and receives joystick events,
    converting them to trackball movement deltas.
    """
    
    def __init__(self, config: dict):
        """
        Initialize USB Serial joystick.
        
        Args:
            config: Configuration dict with:
                - enabled: Enable USB joystick (default: True)
                - port: Serial port path (default: auto-detect)
                - baudrate: Serial baud rate (default: 115200)
                - sensitivity: Movement multiplier (default: 2.0)
                - auto_reconnect: Auto-reconnect on disconnect (default: True)
        """
        self.enabled = config.get('enabled', True)
        self.port = config.get('port', None)  # None = auto-detect
        self.baudrate = config.get('baudrate', 115200)
        self.sensitivity = config.get('sensitivity', 2.0)
        self.auto_reconnect = config.get('auto_reconnect', True)
        
        # State
        self._x = 0
        self._y = 0
        self._clicked = False
        self._click_count = 0
        self._back_pressed = False
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Callbacks (compatible with Trackball interface)
        self._move_callbacks = []
        self._click_callbacks = []
        self._key_callbacks = []  # For ESC/back button
        
        # Serial state
        self._connected = False
        self._connecting = False
        self._serial = None
        self._serial_thread = None
        self._stop_event = threading.Event()
        
        if self.enabled:
            self._start_serial_thread()
    
    def _find_esp32_port(self) -> Optional[str]:
        """Auto-detect ESP32 USB serial port."""
        # Common ESP32 USB serial identifiers
        esp32_identifiers = [
            'CP210',  # CP210x USB to UART
            'CH340',  # CH340 USB to UART
            'CH341',  # CH341 USB to UART
            'FT232',  # FTDI FT232
            'Silicon Labs',  # CP210x
            'USB Serial',  # Generic
        ]
        
        ports = serial.tools.list_ports.comports()
        for port in ports:
            description = port.description.upper()
            for identifier in esp32_identifiers:
                if identifier.upper() in description:
                    print(f"USB Joystick: Found ESP32 on {port.device}")
                    return port.device
        
        # Fallback: try common port names
        common_ports = ['/dev/ttyUSB0', '/dev/ttyACM0', '/dev/ttyUSB1', '/dev/ttyACM1']
        for port_name in common_ports:
            try:
                test_serial = serial.Serial(port_name, self.baudrate, timeout=0.1)
                test_serial.close()
                print(f"USB Joystick: Using port {port_name}")
                return port_name
            except:
                pass
        
        return None
    
    def _start_serial_thread(self):
        """Start USB Serial connection thread."""
        if self._serial_thread and self._serial_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._serial_thread = threading.Thread(target=self._serial_loop, daemon=True)
        self._serial_thread.start()
    
    def _serial_loop(self):
        """Main USB Serial connection and event loop."""
        while not self._stop_event.is_set():
            try:
                if not self._connected and not self._connecting:
                    self._connect()
                
                if self._connected and self._serial:
                    # Read joystick events (8-byte packets)
                    if self._serial.in_waiting >= 8:
                        data = self._serial.read(8)
                        if len(data) == 8:
                            self._on_joystick_event(data)
                    else:
                        time.sleep(0.01)  # Small delay to avoid busy-waiting
                else:
                    time.sleep(1)  # Wait before retry
                    
            except serial.SerialException as e:
                print(f"USB joystick serial error: {e}")
                self._disconnect()
                if self.auto_reconnect:
                    time.sleep(2)  # Wait before reconnect attempt
            except Exception as e:
                print(f"USB joystick error: {e}")
                self._disconnect()
                if self.auto_reconnect:
                    time.sleep(2)
    
    def _connect(self):
        """Connect to ESP32 controller via USB Serial."""
        self._connecting = True
        try:
            # Find port if not specified
            port = self.port
            if not port:
                port = self._find_esp32_port()
            
            if not port:
                print("USB Joystick: No ESP32 device found")
                self._connecting = False
                return
            
            # Open serial connection
            self._serial = serial.Serial(
                port=port,
                baudrate=self.baudrate,
                timeout=0.1,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            
            # Flush any stale data
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
            
            self._connected = True
            print(f"USB Joystick: Connected to {port} at {self.baudrate} baud")
            
        except serial.SerialException as e:
            print(f"USB Joystick: Connection failed: {e}")
            self._connected = False
        except Exception as e:
            print(f"USB Joystick: Unexpected error: {e}")
            self._connected = False
        finally:
            self._connecting = False
    
    def _disconnect(self):
        """Disconnect from ESP32 controller."""
        if self._serial:
            try:
                self._serial.close()
            except:
                pass
            self._serial = None
        self._connected = False
    
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
        
        # Validate packet - skip if values are out of expected range
        # This helps recover from misaligned reads (e.g., if text messages were in buffer)
        if abs(x) > 100 or abs(y) > 100:
            # Invalid packet - likely misaligned, skip it
            print(f"USB Joystick: Invalid packet (x={x}, y={y}), skipping")
            return
        
        # Debug: Print first few packets to verify reception
        if not hasattr(self, '_debug_packet_count'):
            self._debug_packet_count = 0
        self._debug_packet_count += 1
        if self._debug_packet_count <= 5:
            print(f"USB Joystick: Received packet #{self._debug_packet_count}: x={x} y={y} btn=0x{buttons:02x}")
        
        with self._lock:
            # Convert joystick values to movement deltas
            # Joystick: -100 to +100, Trackball: pixels
            dx = int(x * self.sensitivity / 10)  # Scale to reasonable pixel movement
            dy = int(y * self.sensitivity / 10)
            
            if dx != 0 or dy != 0:
                self._x += dx
                self._y += dy
                self._notify_move()
            
            # Handle button presses
            # Bit0 = Confirm/Select (left click)
            # Bit4 = Back/Cancel (ESC key)
            if buttons & 0x01:  # Confirm/Select button
                if not self._clicked:
                    self._clicked = True
                    self._click_count += 1
                    self._notify_click(True)
            else:
                if self._clicked:
                    self._clicked = False
                    self._notify_click(False)
            
            # Handle back button (bit4) - send ESC key event
            if buttons & 0x10:  # Back/Cancel button
                if not hasattr(self, '_back_pressed') or not self._back_pressed:
                    self._back_pressed = True
                    self._notify_key_esc()
            else:
                self._back_pressed = False
    
    def _notify_move(self):
        """Notify move callbacks."""
        for cb in self._move_callbacks:
            try:
                cb(self._x, self._y)
            except Exception as e:
                print(f"USB joystick move callback error: {e}")
    
    def _notify_click(self, pressed: bool):
        """Notify click callbacks."""
        for cb in self._click_callbacks:
            try:
                cb(pressed)
            except Exception as e:
                print(f"USB joystick click callback error: {e}")
    
    def _notify_key_esc(self):
        """Notify key callbacks with ESC key event."""
        from ..input.cardkb import KeyEvent, KeyCode
        event = KeyEvent(code=KeyCode.ESC, char=None)
        for cb in self._key_callbacks:
            try:
                cb(event)
            except Exception as e:
                print(f"USB joystick key callback error: {e}")
    
    # Trackball-compatible interface
    def on_move(self, callback: Callable[[int, int], None]):
        """Register move callback. Called with (x, y) deltas."""
        self._move_callbacks.append(callback)
    
    def on_click(self, callback: Callable[[bool], None]):
        """Register click callback. Called with pressed state."""
        self._click_callbacks.append(callback)
    
    def on_key(self, callback: Callable):
        """Register key callback. Called with KeyEvent for ESC/back button."""
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
        """Clean up USB Serial connection."""
        self._stop_event.set()
        self._disconnect()
        if self._serial_thread:
            self._serial_thread.join(timeout=2)

