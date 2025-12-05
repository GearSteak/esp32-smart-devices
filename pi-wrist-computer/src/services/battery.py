"""
Battery Service

Reads battery status from UPS-Lite via I2C.
Can also run in 'none' mode for batteries without monitoring.
"""

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

# Try to import smbus2 (might not be available on all systems)
try:
    import smbus2
    SMBUS_AVAILABLE = True
except ImportError:
    SMBUS_AVAILABLE = False


@dataclass
class BatteryData:
    """Battery status data."""
    voltage: float = 0.0  # Volts
    percent: int = 100
    charging: bool = False
    timestamp: float = 0.0


class BatteryService:
    """
    Battery monitoring service.
    
    Modes:
    - 'ups_lite': UPS-Lite with MAX17040 fuel gauge (I2C 0x36)
    - 'pisugar': PiSugar battery (I2C 0x57)
    - 'none': No battery monitoring (shows static 100% or hidden)
    """
    
    # I2C addresses for different modules
    ADDRESSES = {
        'ups_lite': 0x36,
        'pisugar': 0x57,
    }
    
    def __init__(self, config: dict = None):
        """
        Initialize battery service.
        
        Args:
            config: Configuration with:
                - mode: 'ups_lite', 'pisugar', 'none', or 'auto'
                - show_indicator: Whether to show battery in status bar
        """
        config = config or {}
        self.mode = config.get('mode', 'none')  # Default to none
        self.show_indicator = config.get('show_indicator', True)
        self.i2c_bus = config.get('i2c_bus', 1)
        
        self._data = BatteryData(percent=100)  # Default to 100%
        self._running = False
        self._thread = None
        self._callbacks = []
        self._bus = None
        self.enabled = False  # Will be set True if battery detected
    
    def start(self):
        """Start battery monitoring."""
        if self.mode == 'none':
            # No battery monitoring - just use static 100%
            self._data.percent = 100
            self._data.voltage = 5.0
            self.enabled = False
            print("Battery: No monitoring (mode=none)")
            return
        
        if not SMBUS_AVAILABLE:
            print("Battery: smbus2 not available, disabling")
            self.enabled = False
            return
        
        # Try to detect and connect to battery module
        if self.mode == 'auto':
            self._auto_detect()
        else:
            self._connect_module(self.mode)
        
        if self.enabled:
            self._running = True
            self._thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._thread.start()
    
    def _auto_detect(self):
        """Auto-detect battery module."""
        try:
            self._bus = smbus2.SMBus(self.i2c_bus)
            
            # Try UPS-Lite first
            try:
                self._bus.read_word_data(self.ADDRESSES['ups_lite'], 0x02)
                self.mode = 'ups_lite'
                self.enabled = True
                print("Battery: UPS-Lite detected")
                return
            except:
                pass
            
            # Try PiSugar
            try:
                self._bus.read_byte_data(self.ADDRESSES['pisugar'], 0x2a)
                self.mode = 'pisugar'
                self.enabled = True
                print("Battery: PiSugar detected")
                return
            except:
                pass
            
            # No battery module found
            print("Battery: No module detected, disabling")
            self._bus.close()
            self._bus = None
            self.enabled = False
            
        except Exception as e:
            print(f"Battery: I2C init failed: {e}")
            self.enabled = False
    
    def _connect_module(self, mode: str):
        """Connect to specific battery module."""
        if mode not in self.ADDRESSES:
            print(f"Battery: Unknown mode '{mode}'")
            self.enabled = False
            return
        
        try:
            self._bus = smbus2.SMBus(self.i2c_bus)
            # Test read
            addr = self.ADDRESSES[mode]
            if mode == 'ups_lite':
                self._bus.read_word_data(addr, 0x02)
            elif mode == 'pisugar':
                self._bus.read_byte_data(addr, 0x2a)
            
            self.enabled = True
            print(f"Battery: {mode} connected")
        except Exception as e:
            print(f"Battery: Failed to connect to {mode}: {e}")
            if self._bus:
                self._bus.close()
                self._bus = None
            self.enabled = False
    
    def stop(self):
        """Stop battery monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._bus:
            self._bus.close()
    
    def _poll_loop(self):
        """Background polling loop."""
        while self._running:
            try:
                self._read_battery()
                
                # Notify callbacks
                for cb in self._callbacks:
                    try:
                        cb(self._data)
                    except Exception as e:
                        print(f"Battery callback error: {e}")
            
            except Exception as e:
                pass
            
            time.sleep(30)  # Poll every 30 seconds
    
    def _read_battery(self):
        """Read battery data based on mode."""
        if not self._bus or not self.enabled:
            return
        
        try:
            if self.mode == 'ups_lite':
                self._read_ups_lite()
            elif self.mode == 'pisugar':
                self._read_pisugar()
            
            self._data.timestamp = time.time()
            
        except Exception as e:
            # I2C read error - keep last values
            pass
    
    def _read_ups_lite(self):
        """Read from UPS-Lite (MAX17040 fuel gauge)."""
        addr = self.ADDRESSES['ups_lite']
        
        # Read voltage (register 0x02, 0x03)
        read = self._bus.read_word_data(addr, 0x02)
        voltage = ((read >> 8) + ((read & 0xFF) << 8)) * 78.125 / 1000000
        self._data.voltage = round(voltage, 2)
        
        # Read capacity (register 0x04, 0x05)
        read = self._bus.read_word_data(addr, 0x04)
        capacity = ((read >> 8) + ((read & 0xFF) << 8)) / 256
        self._data.percent = min(100, max(0, int(capacity)))
    
    def _read_pisugar(self):
        """Read from PiSugar battery."""
        addr = self.ADDRESSES['pisugar']
        
        # Read battery level (register 0x2a)
        level = self._bus.read_byte_data(addr, 0x2a)
        self._data.percent = min(100, max(0, level))
        
        # Read voltage (registers 0x22, 0x23)
        try:
            high = self._bus.read_byte_data(addr, 0x22)
            low = self._bus.read_byte_data(addr, 0x23)
            voltage = ((high << 8) | low) / 1000.0
            self._data.voltage = round(voltage, 2)
        except:
            self._data.voltage = 3.7  # Default LiPo voltage
    
    def on_update(self, callback: Callable[[BatteryData], None]):
        """Register callback for battery updates."""
        self._callbacks.append(callback)
    
    def get_data(self) -> BatteryData:
        """Get current battery data."""
        return self._data
    
    @property
    def percent(self) -> int:
        """Get battery percentage."""
        return self._data.percent
    
    @property
    def voltage(self) -> float:
        """Get battery voltage."""
        return self._data.voltage
    
    @property
    def is_low(self) -> bool:
        """Check if battery is low (<20%)."""
        return self._data.percent < 20

