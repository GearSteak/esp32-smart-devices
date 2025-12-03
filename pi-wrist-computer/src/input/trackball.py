"""
303trackba1 Trackball Driver

Digital direction trackball with GPIO inputs.
Outputs pulses on direction pins when rolled.
"""

import RPi.GPIO as GPIO
import time
import threading
from typing import Callable, Tuple
from dataclasses import dataclass


@dataclass
class TrackballState:
    """Current trackball state."""
    x: int  # Accumulated X movement
    y: int  # Accumulated Y movement
    clicked: bool
    click_count: int


class Trackball:
    """Digital trackball driver using GPIO interrupts."""
    
    def __init__(self, config: dict):
        """
        Initialize trackball.
        
        Args:
            config: Configuration with GPIO pins:
                - gpio_up, gpio_down, gpio_left, gpio_right: Direction pins
                - gpio_click: Button pin
                - sensitivity: Pixels per pulse
                - acceleration: Enable acceleration
        """
        self.gpio_up = config.get('gpio_up', 5)
        self.gpio_down = config.get('gpio_down', 6)
        self.gpio_left = config.get('gpio_left', 13)
        self.gpio_right = config.get('gpio_right', 19)
        self.gpio_click = config.get('gpio_click', 26)
        self.sensitivity = config.get('sensitivity', 3)
        self.acceleration = config.get('acceleration', True)
        self.enabled = config.get('enabled', True)
        
        # State
        self._x = 0
        self._y = 0
        self._clicked = False
        self._click_count = 0
        self._last_pulse_time = 0
        self._pulse_rate = 0
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Callbacks
        self._move_callbacks = []
        self._click_callbacks = []
        
        if self.enabled:
            self._setup_gpio()
    
    def _setup_gpio(self):
        """Setup GPIO pins with interrupts."""
        GPIO.setmode(GPIO.BCM)
        
        # Direction pins - input with pull-up
        for pin in [self.gpio_up, self.gpio_down, self.gpio_left, self.gpio_right]:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Click pin
        GPIO.setup(self.gpio_click, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Add edge detection
        GPIO.add_event_detect(self.gpio_up, GPIO.FALLING, 
                              callback=self._on_up, bouncetime=5)
        GPIO.add_event_detect(self.gpio_down, GPIO.FALLING, 
                              callback=self._on_down, bouncetime=5)
        GPIO.add_event_detect(self.gpio_left, GPIO.FALLING, 
                              callback=self._on_left, bouncetime=5)
        GPIO.add_event_detect(self.gpio_right, GPIO.FALLING, 
                              callback=self._on_right, bouncetime=5)
        GPIO.add_event_detect(self.gpio_click, GPIO.BOTH, 
                              callback=self._on_click, bouncetime=50)
    
    def _calculate_movement(self) -> int:
        """Calculate movement amount with optional acceleration."""
        now = time.time()
        
        if self.acceleration and self._last_pulse_time > 0:
            # Calculate pulse rate
            delta = now - self._last_pulse_time
            if delta > 0:
                self._pulse_rate = 1.0 / delta
            
            # Accelerate based on rate
            if self._pulse_rate > 50:
                multiplier = 4
            elif self._pulse_rate > 30:
                multiplier = 3
            elif self._pulse_rate > 15:
                multiplier = 2
            else:
                multiplier = 1
        else:
            multiplier = 1
        
        self._last_pulse_time = now
        return self.sensitivity * multiplier
    
    def _on_up(self, channel):
        """Handle up pulse."""
        with self._lock:
            movement = self._calculate_movement()
            self._y -= movement
            self._notify_move()
    
    def _on_down(self, channel):
        """Handle down pulse."""
        with self._lock:
            movement = self._calculate_movement()
            self._y += movement
            self._notify_move()
    
    def _on_left(self, channel):
        """Handle left pulse."""
        with self._lock:
            movement = self._calculate_movement()
            self._x -= movement
            self._notify_move()
    
    def _on_right(self, channel):
        """Handle right pulse."""
        with self._lock:
            movement = self._calculate_movement()
            self._x += movement
            self._notify_move()
    
    def _on_click(self, channel):
        """Handle click event."""
        with self._lock:
            # Read actual state (FALLING = pressed, RISING = released)
            pressed = GPIO.input(self.gpio_click) == GPIO.LOW
            
            if pressed and not self._clicked:
                self._clicked = True
                self._click_count += 1
                self._notify_click(True)
            elif not pressed and self._clicked:
                self._clicked = False
                self._notify_click(False)
    
    def _notify_move(self):
        """Notify move callbacks."""
        for cb in self._move_callbacks:
            try:
                cb(self._x, self._y)
            except Exception as e:
                print(f"Trackball move callback error: {e}")
    
    def _notify_click(self, pressed: bool):
        """Notify click callbacks."""
        for cb in self._click_callbacks:
            try:
                cb(pressed)
            except Exception as e:
                print(f"Trackball click callback error: {e}")
    
    def on_move(self, callback: Callable[[int, int], None]):
        """Register move callback. Called with (x, y) deltas."""
        self._move_callbacks.append(callback)
    
    def on_click(self, callback: Callable[[bool], None]):
        """Register click callback. Called with pressed state."""
        self._click_callbacks.append(callback)
    
    def get_state(self) -> TrackballState:
        """Get current trackball state."""
        with self._lock:
            return TrackballState(
                x=self._x,
                y=self._y,
                clicked=self._clicked,
                click_count=self._click_count
            )
    
    def get_delta(self) -> Tuple[int, int]:
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
        """Clean up GPIO."""
        if self.enabled:
            for pin in [self.gpio_up, self.gpio_down, self.gpio_left, 
                        self.gpio_right, self.gpio_click]:
                try:
                    GPIO.remove_event_detect(pin)
                except Exception:
                    pass
            GPIO.cleanup([self.gpio_up, self.gpio_down, self.gpio_left,
                         self.gpio_right, self.gpio_click])

