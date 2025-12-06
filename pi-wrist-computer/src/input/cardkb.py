"""
CardKB I2C Keyboard Driver

M5Stack CardKB mini keyboard connected via I2C.
Address: 0x5F
"""

import smbus2
import time
from typing import Optional, Callable
from dataclasses import dataclass
from enum import IntEnum


class KeyCode(IntEnum):
    """Special key codes from CardKB."""
    NONE = 0x00
    BACKSPACE = 0x08
    TAB = 0x09
    ENTER = 0x0D
    ESC = 0x1B
    SPACE = 0x20
    DEL = 0x7F
    
    # Function keys (Fn + number)
    F1 = 0x80
    F2 = 0x81
    F3 = 0x82
    F4 = 0x83
    F5 = 0x84
    F6 = 0x85
    F7 = 0x86
    F8 = 0x87
    F9 = 0x88
    F10 = 0x89
    
    # Arrow keys (Fn + direction)
    UP = 0xB5
    DOWN = 0xB6
    LEFT = 0xB4
    RIGHT = 0xB7
    
    # Special combinations
    HOME = 0x90
    END = 0x91
    PAGEUP = 0x92
    PAGEDOWN = 0x93


@dataclass
class KeyEvent:
    """Key event data."""
    code: int
    char: str
    is_special: bool
    timestamp: float


class CardKB:
    """CardKB I2C keyboard driver."""
    
    I2C_ADDRESS = 0x5F
    
    def __init__(self, config: dict):
        """
        Initialize CardKB.
        
        Args:
            config: Configuration with:
                - i2c_bus: I2C bus number (default 1)
                - address: I2C address (default 0x5F)
        """
        self.bus_num = config.get('i2c_bus', 1)
        self.address = config.get('address', self.I2C_ADDRESS)
        self.enabled = config.get('enabled', True)
        
        self._bus = None
        self._callbacks = []
        self._last_key = 0
        self._last_time = 0
        self._repeat_delay = 0.05  # Initial delay before repeat (very fast)
        self._repeat_rate = 0.01  # Time between repeats (extremely fast - 100Hz)
        
        if self.enabled:
            self._init_bus()
    
    def _init_bus(self):
        """Initialize I2C bus."""
        try:
            self._bus = smbus2.SMBus(self.bus_num)
        except Exception as e:
            print(f"CardKB: Failed to init I2C bus {self.bus_num}: {e}")
            self.enabled = False
    
    def on_key(self, callback: Callable[[KeyEvent], None]):
        """Register key event callback."""
        self._callbacks.append(callback)
    
    def read(self) -> Optional[KeyEvent]:
        """
        Read a key from the keyboard.
        
        Returns:
            KeyEvent if key pressed, None otherwise.
        """
        if not self.enabled:
            return None
        
        if not self._bus:
            if not hasattr(self, '_bus_error_printed'):
                print("CardKB: I2C bus not initialized")
                self._bus_error_printed = True
            return None
        
        try:
            key = self._bus.read_byte(self.address)
        except Exception:
            return None
        
        if key == 0:
            self._last_key = 0
            self._last_time = 0  # Reset timer when key released
            return None
        
        now = time.time()
        
        # Determine if special key
        is_special = key < 0x20 or key >= 0x80
        char = '' if is_special else chr(key)
        
        # Handle key repeat - allow first press immediately, throttle repeats
        if key == self._last_key:
            # Same key - check if enough time has passed for repeat
            elapsed = now - self._last_time
            if elapsed < self._repeat_rate:
                return None  # Too soon, skip this repeat
            # Update time for next repeat
            self._last_time = now
        else:
            # New key pressed - allow immediately, no delay
            self._last_key = key
            self._last_time = now
        
        # Create and send event
        event = KeyEvent(
            code=key,
            char=char,
            is_special=is_special,
            timestamp=now
        )
        
        # Notify callbacks
        for cb in self._callbacks:
            try:
                cb(event)
            except Exception as e:
                print(f"CardKB callback error: {e}")
        
        return event
    
    def poll(self) -> Optional[KeyEvent]:
        """Alias for read()."""
        return self.read()
    
    @staticmethod
    def key_name(code: int) -> str:
        """Get human-readable name for key code."""
        try:
            return KeyCode(code).name
        except ValueError:
            if 0x20 <= code < 0x7F:
                return chr(code)
            return f"0x{code:02X}"
    
    def shutdown(self):
        """Clean up resources."""
        if self._bus:
            self._bus.close()
            self._bus = None


# Key mapping helpers
def is_printable(code: int) -> bool:
    """Check if key code is a printable character."""
    return 0x20 <= code < 0x7F


def is_arrow(code: int) -> bool:
    """Check if key code is an arrow key."""
    return code in (KeyCode.UP, KeyCode.DOWN, KeyCode.LEFT, KeyCode.RIGHT)


def is_modifier(code: int) -> bool:
    """Check if key code is a modifier."""
    return code in (KeyCode.ESC, KeyCode.TAB, KeyCode.BACKSPACE, KeyCode.DEL)

