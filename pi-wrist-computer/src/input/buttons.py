"""
Button Navigation Driver

D-pad style navigation using GPIO buttons.
Can replace trackball for cursor/menu control.
"""

import RPi.GPIO as GPIO
import time
import threading
from typing import Callable, Tuple
from dataclasses import dataclass


@dataclass
class ButtonState:
    """Current button state."""
    up: bool = False
    down: bool = False
    left: bool = False
    right: bool = False
    select: bool = False


class ButtonNav:
    """Button-based navigation using GPIO."""
    
    def __init__(self, config: dict):
        """
        Initialize button navigation.
        
        Args:
            config: Configuration with GPIO pins:
                - gpio_up, gpio_down, gpio_left, gpio_right: Direction buttons
                - gpio_select: Select/click button
                - cursor_speed: Pixels per step (for cursor mode)
                - repeat_delay: Initial delay before key repeat (ms)
                - repeat_rate: Rate of key repeat (ms)
        """
        self.gpio_up = config.get('gpio_up', 5)
        self.gpio_down = config.get('gpio_down', 6)
        self.gpio_left = config.get('gpio_left', 13)
        self.gpio_right = config.get('gpio_right', 19)
        self.gpio_select = config.get('gpio_select', 26)
        self.cursor_speed = config.get('cursor_speed', 5)
        self.repeat_delay = config.get('repeat_delay', 400) / 1000  # Convert to seconds
        self.repeat_rate = config.get('repeat_rate', 50) / 1000
        self.enabled = config.get('enabled', True)
        
        # State tracking
        self._state = ButtonState()
        self._press_times = {
            'up': 0, 'down': 0, 'left': 0, 'right': 0, 'select': 0
        }
        self._last_repeat = {
            'up': 0, 'down': 0, 'left': 0, 'right': 0
        }
        
        # Accumulated cursor movement
        self._cursor_x = 0
        self._cursor_y = 0
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Callbacks
        self._move_callbacks = []
        self._click_callbacks = []
        self._direction_callbacks = []  # For menu navigation
        
        # Repeat thread
        self._running = False
        self._repeat_thread = None
        
        if self.enabled:
            self._setup_gpio()
            self._start_repeat_thread()
    
    def _setup_gpio(self):
        """Setup GPIO pins."""
        GPIO.setmode(GPIO.BCM)
        
        pins = [self.gpio_up, self.gpio_down, self.gpio_left, 
                self.gpio_right, self.gpio_select]
        
        for pin in pins:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Edge detection for button presses
        GPIO.add_event_detect(self.gpio_up, GPIO.BOTH,
                              callback=lambda c: self._on_button('up', c),
                              bouncetime=20)
        GPIO.add_event_detect(self.gpio_down, GPIO.BOTH,
                              callback=lambda c: self._on_button('down', c),
                              bouncetime=20)
        GPIO.add_event_detect(self.gpio_left, GPIO.BOTH,
                              callback=lambda c: self._on_button('left', c),
                              bouncetime=20)
        GPIO.add_event_detect(self.gpio_right, GPIO.BOTH,
                              callback=lambda c: self._on_button('right', c),
                              bouncetime=20)
        GPIO.add_event_detect(self.gpio_select, GPIO.BOTH,
                              callback=lambda c: self._on_button('select', c),
                              bouncetime=50)
    
    def _start_repeat_thread(self):
        """Start key repeat handling thread."""
        self._running = True
        self._repeat_thread = threading.Thread(target=self._repeat_loop, daemon=True)
        self._repeat_thread.start()
    
    def _on_button(self, button: str, channel):
        """Handle button press/release."""
        # Read actual state (LOW = pressed due to pull-up)
        pin = getattr(self, f'gpio_{button}')
        pressed = GPIO.input(pin) == GPIO.LOW
        
        with self._lock:
            # Update state
            setattr(self._state, button, pressed)
            
            now = time.time()
            
            if pressed:
                self._press_times[button] = now
                
                if button == 'select':
                    self._notify_click(True)
                else:
                    # Immediate first movement
                    self._handle_direction(button)
            else:
                self._press_times[button] = 0
                
                if button == 'select':
                    self._notify_click(False)
    
    def _repeat_loop(self):
        """Handle key repeat for held buttons."""
        while self._running:
            now = time.time()
            
            with self._lock:
                for direction in ['up', 'down', 'left', 'right']:
                    press_time = self._press_times[direction]
                    
                    if press_time > 0:  # Button is held
                        held_duration = now - press_time
                        
                        if held_duration >= self.repeat_delay:
                            last_repeat = self._last_repeat[direction]
                            
                            if now - last_repeat >= self.repeat_rate:
                                self._handle_direction(direction)
                                self._last_repeat[direction] = now
            
            time.sleep(0.01)  # 10ms polling
    
    def _handle_direction(self, direction: str):
        """Handle a direction input."""
        # Update cursor position
        if direction == 'up':
            self._cursor_y -= self.cursor_speed
        elif direction == 'down':
            self._cursor_y += self.cursor_speed
        elif direction == 'left':
            self._cursor_x -= self.cursor_speed
        elif direction == 'right':
            self._cursor_x += self.cursor_speed
        
        # Notify move callbacks
        self._notify_move()
        
        # Notify direction callbacks (for menu navigation)
        self._notify_direction(direction)
    
    def _notify_move(self):
        """Notify move callbacks."""
        for cb in self._move_callbacks:
            try:
                cb(self._cursor_x, self._cursor_y)
            except Exception as e:
                print(f"Button move callback error: {e}")
    
    def _notify_click(self, pressed: bool):
        """Notify click callbacks."""
        for cb in self._click_callbacks:
            try:
                cb(pressed)
            except Exception as e:
                print(f"Button click callback error: {e}")
    
    def _notify_direction(self, direction: str):
        """Notify direction callbacks."""
        for cb in self._direction_callbacks:
            try:
                cb(direction)
            except Exception as e:
                print(f"Button direction callback error: {e}")
    
    def on_move(self, callback: Callable[[int, int], None]):
        """Register move callback. Called with (x, y) position."""
        self._move_callbacks.append(callback)
    
    def on_click(self, callback: Callable[[bool], None]):
        """Register click callback. Called with pressed state."""
        self._click_callbacks.append(callback)
    
    def on_direction(self, callback: Callable[[str], None]):
        """Register direction callback. Called with 'up'/'down'/'left'/'right'."""
        self._direction_callbacks.append(callback)
    
    def get_state(self) -> ButtonState:
        """Get current button state."""
        with self._lock:
            return ButtonState(
                up=self._state.up,
                down=self._state.down,
                left=self._state.left,
                right=self._state.right,
                select=self._state.select
            )
    
    def get_delta(self) -> Tuple[int, int]:
        """Get and reset accumulated cursor movement."""
        with self._lock:
            dx, dy = self._cursor_x, self._cursor_y
            self._cursor_x = 0
            self._cursor_y = 0
            return dx, dy
    
    def is_clicked(self) -> bool:
        """Check if select button is currently pressed."""
        return self._state.select
    
    def reset(self):
        """Reset accumulated movement."""
        with self._lock:
            self._cursor_x = 0
            self._cursor_y = 0
    
    def shutdown(self):
        """Clean up GPIO."""
        self._running = False
        if self._repeat_thread:
            self._repeat_thread.join(timeout=1)
        
        if self.enabled:
            pins = [self.gpio_up, self.gpio_down, self.gpio_left,
                    self.gpio_right, self.gpio_select]
            for pin in pins:
                try:
                    GPIO.remove_event_detect(pin)
                except Exception:
                    pass
            GPIO.cleanup(pins)

