"""
Battery Service

Reads battery status from UPS-Lite via I2C.
"""

import smbus2
import threading
import time
from dataclasses import dataclass
from typing import Callable


@dataclass
class BatteryData:
    """Battery status data."""
    voltage: float = 0.0  # Volts
    percent: int = 100
    charging: bool = False
    timestamp: float = 0.0


class BatteryService:
    """UPS-Lite battery monitoring via I2C."""
    
    # UPS-Lite I2C address
    I2C_ADDRESS = 0x36
    
    def __init__(self, config: dict = None):
        """
        Initialize battery service.
        
        Args:
            config: Optional configuration
        """
        self.enabled = True
        self.i2c_bus = 1
        
        self._data = BatteryData()
        self._running = False
        self._thread = None
        self._callbacks = []
        self._bus = None
    
    def start(self):
        """Start battery monitoring."""
        try:
            self._bus = smbus2.SMBus(self.i2c_bus)
            
            self._running = True
            self._thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._thread.start()
        except Exception as e:
            print(f"Battery: Failed to init I2C: {e}")
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
        """Read battery data from UPS-Lite."""
        try:
            # Read voltage (register 0x02, 0x03)
            # UPS-Lite uses MAX17040 fuel gauge
            read = self._bus.read_word_data(self.I2C_ADDRESS, 0x02)
            voltage = ((read >> 8) + ((read & 0xFF) << 8)) * 78.125 / 1000000
            self._data.voltage = round(voltage, 2)
            
            # Read capacity (register 0x04, 0x05)
            read = self._bus.read_word_data(self.I2C_ADDRESS, 0x04)
            capacity = ((read >> 8) + ((read & 0xFF) << 8)) / 256
            self._data.percent = min(100, max(0, int(capacity)))
            
            self._data.timestamp = time.time()
            
            # Estimate charging based on voltage increase
            # (UPS-Lite doesn't have a charging indicator)
            
        except Exception as e:
            # I2C read error - keep last values
            pass
    
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

