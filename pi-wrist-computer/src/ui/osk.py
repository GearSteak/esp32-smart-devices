"""
On-Screen Keyboard (OSK)
Reusable keyboard for text input on devices without full keyboard.

Supports:
- Joystick/arrow key navigation
- Multiple layouts (qwerty, numeric, symbols)
- Shift/caps lock
- Predictive text hints (optional)
"""

from typing import Optional, Callable, List
from .display import Display
from ..input.cardkb import KeyEvent, KeyCode


class OnScreenKeyboard:
    """
    On-Screen Keyboard widget.
    
    Usage:
        osk = OnScreenKeyboard(callback=my_callback)
        osk.show()
        
        # In your input handler:
        if osk.visible:
            osk.handle_input(event)
        
        # In your draw:
        osk.draw(display, y_position)
    """
    
    # Keyboard layouts
    LAYOUTS = {
        'qwerty': [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', "'"],
            ['⇧', 'z', 'x', 'c', 'v', 'b', 'n', 'm', '⌫', '⏎'],
            ['123', ' ', '.', '@', '←', '→'],
        ],
        'qwerty_shift': [
            ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')'],
            ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
            ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', '"'],
            ['⇧', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', '⌫', '⏎'],
            ['123', ' ', ',', '?', '←', '→'],
        ],
        'numeric': [
            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            ['-', '/', ':', ';', '(', ')', '$', '&', '@', '"'],
            ['.', ',', '?', '!', "'", '`', '~', '*', '+', '='],
            ['ABC', ' ', '⌫', '⏎'],
        ],
        'symbols': [
            ['[', ']', '{', '}', '#', '%', '^', '*', '+', '='],
            ['_', '\\', '|', '~', '<', '>', '€', '£', '¥', '•'],
            ['.', ',', '?', '!', "'", '"', '-', '/', ':', ';'],
            ['ABC', ' ', '⌫', '⏎'],
        ],
    }
    
    # Special key widths (multiplier)
    KEY_WIDTHS = {
        '⇧': 1.5, '⌫': 1.5, '⏎': 1.5,
        ' ': 4, '123': 1.5, 'ABC': 1.5,
        '←': 1, '→': 1,
    }
    
    def __init__(self, 
                 callback: Optional[Callable[[str], None]] = None,
                 on_submit: Optional[Callable[[str], None]] = None,
                 on_cancel: Optional[Callable[[], None]] = None,
                 initial_text: str = "",
                 placeholder: str = "",
                 max_length: int = 100,
                 password_mode: bool = False):
        """
        Initialize OSK.
        
        Args:
            callback: Called on each character input with current text
            on_submit: Called when Enter is pressed
            on_cancel: Called when cancelled (ESC)
            initial_text: Starting text
            placeholder: Placeholder when empty
            max_length: Maximum text length
            password_mode: Show dots instead of text
        """
        self.callback = callback
        self.on_submit = on_submit
        self.on_cancel = on_cancel
        self.text = initial_text
        self.placeholder = placeholder
        self.max_length = max_length
        self.password_mode = password_mode
        
        self.visible = False
        self.current_layout = 'qwerty'
        self.shift_active = False
        self.cursor_row = 1  # Start on letter row
        self.cursor_col = 0
        self.text_cursor = len(initial_text)
        
        # Animation state
        self.key_flash = None
        self.flash_time = 0
    
    def show(self, initial_text: str = None):
        """Show the keyboard."""
        self.visible = True
        if initial_text is not None:
            self.text = initial_text
            self.text_cursor = len(initial_text)
        self.cursor_row = 1
        self.cursor_col = 0
    
    def hide(self):
        """Hide the keyboard."""
        self.visible = False
    
    def get_current_layout(self) -> List[List[str]]:
        """Get the current keyboard layout."""
        if self.current_layout == 'qwerty' and self.shift_active:
            return self.LAYOUTS['qwerty_shift']
        return self.LAYOUTS.get(self.current_layout, self.LAYOUTS['qwerty'])
    
    def handle_input(self, event: KeyEvent) -> bool:
        """
        Handle input event.
        
        Returns True if event was consumed.
        """
        if not self.visible:
            return False
        
        if event.type != 'press':
            return True
        
        layout = self.get_current_layout()
        
        # Navigation
        if event.code == KeyCode.UP:
            self.cursor_row = max(0, self.cursor_row - 1)
            self._clamp_cursor_col()
            return True
        
        elif event.code == KeyCode.DOWN:
            self.cursor_row = min(len(layout) - 1, self.cursor_row + 1)
            self._clamp_cursor_col()
            return True
        
        elif event.code == KeyCode.LEFT:
            if self.cursor_col > 0:
                self.cursor_col -= 1
            elif self.cursor_row > 0:
                self.cursor_row -= 1
                self.cursor_col = len(layout[self.cursor_row]) - 1
            return True
        
        elif event.code == KeyCode.RIGHT:
            if self.cursor_col < len(layout[self.cursor_row]) - 1:
                self.cursor_col += 1
            elif self.cursor_row < len(layout) - 1:
                self.cursor_row += 1
                self.cursor_col = 0
            return True
        
        elif event.code == KeyCode.ENTER:
            self._press_key()
            return True
        
        elif event.code == KeyCode.ESC:
            if self.on_cancel:
                self.on_cancel()
            self.hide()
            return True
        
        elif event.code == KeyCode.BACKSPACE:
            self._backspace()
            return True
        
        # Direct character input (for hardware keyboard)
        elif event.char and len(event.char) == 1:
            self._insert_char(event.char)
            return True
        
        return True
    
    def _clamp_cursor_col(self):
        """Keep cursor column within bounds of current row."""
        layout = self.get_current_layout()
        max_col = len(layout[self.cursor_row]) - 1
        self.cursor_col = min(self.cursor_col, max_col)
    
    def _press_key(self):
        """Press the currently selected key."""
        layout = self.get_current_layout()
        key = layout[self.cursor_row][self.cursor_col]
        
        # Flash effect
        self.key_flash = (self.cursor_row, self.cursor_col)
        
        # Handle special keys
        if key == '⇧':
            self.shift_active = not self.shift_active
        elif key == '⌫':
            self._backspace()
        elif key == '⏎':
            if self.on_submit:
                self.on_submit(self.text)
            self.hide()
        elif key == '123':
            self.current_layout = 'numeric'
            self.cursor_row = min(self.cursor_row, len(self.LAYOUTS['numeric']) - 1)
            self._clamp_cursor_col()
        elif key == 'ABC':
            self.current_layout = 'qwerty'
            self.cursor_row = min(self.cursor_row, len(self.LAYOUTS['qwerty']) - 1)
            self._clamp_cursor_col()
        elif key == '←':
            self.text_cursor = max(0, self.text_cursor - 1)
        elif key == '→':
            self.text_cursor = min(len(self.text), self.text_cursor + 1)
        elif key == ' ':
            self._insert_char(' ')
        else:
            self._insert_char(key)
            # Auto-unshift after typing a letter
            if self.shift_active and key.isalpha():
                self.shift_active = False
    
    def _insert_char(self, char: str):
        """Insert a character at cursor position."""
        if len(self.text) >= self.max_length:
            return
        
        self.text = self.text[:self.text_cursor] + char + self.text[self.text_cursor:]
        self.text_cursor += 1
        
        if self.callback:
            self.callback(self.text)
    
    def _backspace(self):
        """Delete character before cursor."""
        if self.text_cursor > 0:
            self.text = self.text[:self.text_cursor - 1] + self.text[self.text_cursor:]
            self.text_cursor -= 1
            
            if self.callback:
                self.callback(self.text)
    
    def draw(self, display: Display, y: int, height: int = None):
        """
        Draw the keyboard.
        
        Args:
            display: Display to draw on
            y: Y position to start drawing
            height: Height available (auto-calculated if None)
        """
        if not self.visible:
            return
        
        import time
        
        # Clear flash after short time
        if self.key_flash and time.time() - self.flash_time > 0.1:
            self.key_flash = None
        
        layout = self.get_current_layout()
        w = display.width
        
        if height is None:
            height = display.height - y
        
        # Background
        display.rect(0, y, w, height, fill='#1a1a2e')
        
        # Text input field
        field_height = 30
        display.rect(5, y + 5, w - 10, field_height, fill='#2a2a4e', outline='#4a4a6e')
        
        # Display text or placeholder
        if self.text:
            display_text = '•' * len(self.text) if self.password_mode else self.text
            # Show cursor
            if len(display_text) > 25:
                # Scroll to show cursor
                start = max(0, self.text_cursor - 20)
                display_text = display_text[start:start + 25]
            display.text(10, y + 20, display_text, 'white', 12, 'lm')
            
            # Cursor line
            cursor_x = 10 + min(self.text_cursor, 25) * 7
            display.rect(cursor_x, y + 10, 2, 18, fill='#ffffff')
        else:
            display.text(10, y + 20, self.placeholder, '#666666', 12, 'lm')
        
        # Calculate key dimensions
        keyboard_y = y + field_height + 10
        available_height = height - field_height - 15
        row_height = min(35, available_height // len(layout))
        
        # Draw keyboard rows
        for row_idx, row in enumerate(layout):
            row_y = keyboard_y + row_idx * row_height
            
            # Calculate total width units for this row
            total_units = sum(self.KEY_WIDTHS.get(k, 1) for k in row)
            key_unit = (w - 10) / total_units
            
            x = 5
            for col_idx, key in enumerate(row):
                key_width = int(key_unit * self.KEY_WIDTHS.get(key, 1)) - 2
                
                # Key appearance
                is_selected = (row_idx == self.cursor_row and col_idx == self.cursor_col)
                is_flashed = (self.key_flash == (row_idx, col_idx))
                is_special = key in ['⇧', '⌫', '⏎', '123', 'ABC', '←', '→']
                is_shift_active = (key == '⇧' and self.shift_active)
                
                if is_flashed:
                    bg_color = '#00ff00'
                elif is_selected:
                    bg_color = '#0066cc'
                elif is_shift_active:
                    bg_color = '#cc6600'
                elif is_special:
                    bg_color = '#3a3a5e'
                else:
                    bg_color = '#2a2a4e'
                
                display.rect(int(x), row_y, key_width, row_height - 4, fill=bg_color)
                
                # Key label
                label = key
                if key == ' ':
                    label = 'space'
                
                text_color = 'white' if is_selected or is_flashed else '#cccccc'
                font_size = 10 if len(label) > 1 else 14
                
                display.text(int(x) + key_width // 2, row_y + (row_height - 4) // 2,
                           label, text_color, font_size, 'mm')
                
                x += key_width + 2
        
        # Instructions
        display.text(w // 2, y + height - 8,
                    "Arrows:Move  Enter:Select  Esc:Cancel", '#555555', 8, 'mm')


class TextInputDialog:
    """
    Full-screen text input dialog using OSK.
    
    Usage:
        dialog = TextInputDialog(
            title="Enter Name",
            on_submit=lambda text: print(f"Got: {text}"),
            on_cancel=lambda: print("Cancelled")
        )
        dialog.show()
    """
    
    def __init__(self, 
                 title: str = "Enter Text",
                 initial_text: str = "",
                 placeholder: str = "Type here...",
                 on_submit: Callable[[str], None] = None,
                 on_cancel: Callable[[], None] = None,
                 password_mode: bool = False,
                 max_length: int = 100):
        
        self.title = title
        self.visible = False
        
        self._on_submit = on_submit
        self._on_cancel = on_cancel
        
        self.osk = OnScreenKeyboard(
            initial_text=initial_text,
            placeholder=placeholder,
            on_submit=self._handle_submit,
            on_cancel=self._handle_cancel,
            password_mode=password_mode,
            max_length=max_length
        )
    
    def show(self, initial_text: str = None):
        """Show the dialog."""
        self.visible = True
        self.osk.show(initial_text)
    
    def hide(self):
        """Hide the dialog."""
        self.visible = False
        self.osk.hide()
    
    def _handle_submit(self, text: str):
        """Handle submit from OSK."""
        self.visible = False
        if self._on_submit:
            self._on_submit(text)
    
    def _handle_cancel(self):
        """Handle cancel from OSK."""
        self.visible = False
        if self._on_cancel:
            self._on_cancel()
    
    def handle_input(self, event: KeyEvent) -> bool:
        """Handle input, returns True if consumed."""
        if not self.visible:
            return False
        return self.osk.handle_input(event)
    
    def draw(self, display: Display, status_bar_height: int = 22):
        """Draw the dialog."""
        if not self.visible:
            return
        
        # Background overlay
        display.rect(0, 0, display.width, display.height, fill='#000000')
        
        # Title
        display.text(display.width // 2, status_bar_height + 15,
                    self.title, 'white', 16, 'mm')
        
        # OSK
        self.osk.draw(display, status_bar_height + 35)
    
    @property
    def text(self) -> str:
        """Get current text."""
        return self.osk.text

