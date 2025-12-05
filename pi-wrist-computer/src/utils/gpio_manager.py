"""
GPIO Manager - Centralized GPIO handling.

Prevents conflicts from multiple modules calling GPIO.setmode().
"""

import threading

# Try to import GPIO, but allow running without it (for testing)
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    GPIO = None


class GPIOManager:
    """Singleton GPIO manager for safe multi-module access."""
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    _allocated_pins = set()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        pass
    
    def initialize(self):
        """Initialize GPIO once."""
        if not GPIO_AVAILABLE:
            print("GPIO not available (not running on Pi?)")
            return False
        
        with self._lock:
            if not self._initialized:
                try:
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setwarnings(False)
                    self._initialized = True
                    return True
                except RuntimeError as e:
                    # If mode is already set, that's okay
                    if "mode" in str(e).lower() and "already" in str(e).lower():
                        self._initialized = True
                        return True
                    print(f"GPIO init failed: {e}")
                    return False
                except Exception as e:
                    print(f"GPIO init failed: {e}")
                    return False
            return True
    
    def setup_output(self, pin: int) -> bool:
        """Setup a pin as output."""
        if not self.initialize():
            return False
        
        with self._lock:
            # If pin is already allocated, assume it's already set up
            if pin in self._allocated_pins:
                return True
            
            try:
                GPIO.setup(pin, GPIO.OUT)
                self._allocated_pins.add(pin)
                return True
            except RuntimeError as e:
                error_str = str(e).lower()
                # Handle "GPIO not allocated" or "not set for this channel" errors
                if "not allocated" in error_str or "not set" in error_str:
                    # Re-initialize and try again
                    try:
                        GPIO.setmode(GPIO.BCM)
                        GPIO.setup(pin, GPIO.OUT)
                        self._allocated_pins.add(pin)
                        return True
                    except Exception as e2:
                        print(f"GPIO setup output pin {pin} failed after re-init: {e2}")
                        return False
                # If pin is already set up, just add it to allocated list
                elif "already" in error_str or "in use" in error_str:
                    self._allocated_pins.add(pin)
                    return True
                print(f"GPIO setup output pin {pin} failed: {e}")
                return False
            except Exception as e:
                error_str = str(e).lower()
                # If pin is already set up, just add it to allocated list
                if "already" in error_str or "in use" in error_str:
                    self._allocated_pins.add(pin)
                    return True
                print(f"GPIO setup output pin {pin} failed: {e}")
                return False
    
    def setup_input(self, pin: int, pull_up: bool = True) -> bool:
        """Setup a pin as input with optional pull-up."""
        if not self.initialize():
            return False
        
        with self._lock:
            # If pin is already allocated, assume it's already set up
            if pin in self._allocated_pins:
                return True
            
            try:
                pud = GPIO.PUD_UP if pull_up else GPIO.PUD_DOWN
                GPIO.setup(pin, GPIO.IN, pull_up_down=pud)
                self._allocated_pins.add(pin)
                return True
            except Exception as e:
                # If pin is already set up, just add it to allocated list
                if "already" in str(e).lower() or "in use" in str(e).lower() or "not allocated" in str(e).lower():
                    self._allocated_pins.add(pin)
                    return True
                print(f"GPIO setup input pin {pin} failed: {e}")
                return False
    
    def output(self, pin: int, value: bool):
        """Set output pin value."""
        if GPIO_AVAILABLE and pin in self._allocated_pins:
            try:
                GPIO.output(pin, GPIO.HIGH if value else GPIO.LOW)
            except Exception as e:
                print(f"GPIO output pin {pin} failed: {e}")
    
    def input(self, pin: int) -> bool:
        """Read input pin value."""
        if GPIO_AVAILABLE and pin in self._allocated_pins:
            try:
                return GPIO.input(pin) == GPIO.HIGH
            except Exception:
                return False
        return False
    
    def add_event_detect(self, pin: int, edge: str, callback, bouncetime: int = 50) -> bool:
        """Add edge detection to a pin."""
        if not GPIO_AVAILABLE:
            return False
        
        edge_map = {
            'rising': GPIO.RISING,
            'falling': GPIO.FALLING,
            'both': GPIO.BOTH
        }
        
        try:
            GPIO.add_event_detect(pin, edge_map.get(edge, GPIO.BOTH),
                                  callback=callback, bouncetime=bouncetime)
            return True
        except Exception as e:
            print(f"GPIO add_event_detect pin {pin} failed: {e}")
            return False
    
    def remove_event_detect(self, pin: int):
        """Remove edge detection from a pin."""
        if GPIO_AVAILABLE:
            try:
                GPIO.remove_event_detect(pin)
            except Exception:
                pass
    
    def setup_pwm(self, pin: int, frequency: int = 1000):
        """Setup PWM on a pin."""
        if not GPIO_AVAILABLE:
            return None
        
        try:
            self.setup_output(pin)
            return GPIO.PWM(pin, frequency)
        except Exception as e:
            print(f"GPIO PWM setup pin {pin} failed: {e}")
            return None
    
    def cleanup(self, pins: list = None):
        """Clean up GPIO pins."""
        if not GPIO_AVAILABLE:
            return
        
        with self._lock:
            try:
                if pins:
                    GPIO.cleanup(pins)
                    for pin in pins:
                        self._allocated_pins.discard(pin)
                else:
                    GPIO.cleanup()
                    self._allocated_pins.clear()
                    self._initialized = False
            except Exception:
                pass
    
    @property
    def available(self) -> bool:
        """Check if GPIO is available."""
        return GPIO_AVAILABLE
    
    @property 
    def HIGH(self):
        return GPIO.HIGH if GPIO_AVAILABLE else True
    
    @property
    def LOW(self):
        return GPIO.LOW if GPIO_AVAILABLE else False


# Global instance
gpio = GPIOManager()

