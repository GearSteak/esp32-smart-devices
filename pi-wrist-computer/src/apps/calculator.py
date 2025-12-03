"""
Calculator Application

Scientific calculator with:
- Basic operations
- Scientific functions
- History
"""

from ..ui.framework import App, AppInfo, Rect
from ..ui.display import Display
from ..input.cardkb import KeyEvent, KeyCode
import math


class CalculatorApp(App):
    """Calculator application."""
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='calculator',
            name='Calc',
            icon='🔢',
            color='#00cc88'
        )
        
        self.display_value = '0'
        self.current_value = 0
        self.pending_op = None
        self.new_input = True
        self.history = []
        self.error = False
        
        # Button grid (for touch/cursor)
        self.buttons = [
            ['C', '(', ')', '/'],
            ['7', '8', '9', '*'],
            ['4', '5', '6', '-'],
            ['1', '2', '3', '+'],
            ['0', '.', '±', '='],
        ]
        
        self.selected_row = 0
        self.selected_col = 0
    
    def on_enter(self):
        self.display_value = '0'
        self.current_value = 0
        self.pending_op = None
        self.new_input = True
        self.error = False
    
    def on_exit(self):
        pass
    
    def on_key(self, event: KeyEvent) -> bool:
        # Direct character input
        if event.char:
            char = event.char
            
            # Numbers
            if char.isdigit():
                self._input_digit(char)
                return True
            
            # Operators
            if char in '+-*/':
                self._input_operator(char)
                return True
            
            # Decimal
            if char == '.':
                self._input_decimal()
                return True
            
            # Equals
            if char == '=' or event.code == KeyCode.ENTER:
                self._calculate()
                return True
            
            # Clear
            if char.upper() == 'C':
                self._clear()
                return True
            
            # Parentheses (for future expression parsing)
            if char in '()':
                return True
        
        # Arrow navigation
        if event.code == KeyCode.UP:
            if self.selected_row > 0:
                self.selected_row -= 1
            return True
        elif event.code == KeyCode.DOWN:
            if self.selected_row < len(self.buttons) - 1:
                self.selected_row += 1
            return True
        elif event.code == KeyCode.LEFT:
            if self.selected_col > 0:
                self.selected_col -= 1
            return True
        elif event.code == KeyCode.RIGHT:
            if self.selected_col < len(self.buttons[0]) - 1:
                self.selected_col += 1
            return True
        elif event.code == KeyCode.ENTER:
            self._press_button(self.buttons[self.selected_row][self.selected_col])
            return True
        elif event.code == KeyCode.BACKSPACE:
            self._backspace()
            return True
        elif event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        return False
    
    def _input_digit(self, digit: str):
        """Input a digit."""
        if self.error:
            self._clear()
        
        if self.new_input:
            self.display_value = digit
            self.new_input = False
        else:
            if self.display_value == '0':
                self.display_value = digit
            else:
                self.display_value += digit
    
    def _input_decimal(self):
        """Input decimal point."""
        if self.error:
            self._clear()
        
        if self.new_input:
            self.display_value = '0.'
            self.new_input = False
        elif '.' not in self.display_value:
            self.display_value += '.'
    
    def _input_operator(self, op: str):
        """Input an operator."""
        if self.error:
            return
        
        if self.pending_op and not self.new_input:
            self._calculate()
        
        self.current_value = float(self.display_value)
        self.pending_op = op
        self.new_input = True
    
    def _calculate(self):
        """Perform calculation."""
        if self.error or not self.pending_op:
            return
        
        try:
            operand = float(self.display_value)
            
            if self.pending_op == '+':
                result = self.current_value + operand
            elif self.pending_op == '-':
                result = self.current_value - operand
            elif self.pending_op == '*':
                result = self.current_value * operand
            elif self.pending_op == '/':
                if operand == 0:
                    raise ZeroDivisionError()
                result = self.current_value / operand
            else:
                result = operand
            
            # Format result
            if result == int(result):
                self.display_value = str(int(result))
            else:
                self.display_value = f"{result:.8g}"
            
            # Add to history
            expr = f"{self.current_value} {self.pending_op} {operand}"
            self.history.append(f"{expr} = {self.display_value}")
            if len(self.history) > 5:
                self.history.pop(0)
            
            self.current_value = result
            self.pending_op = None
            self.new_input = True
            
        except ZeroDivisionError:
            self.display_value = 'Error: /0'
            self.error = True
        except Exception as e:
            self.display_value = 'Error'
            self.error = True
    
    def _clear(self):
        """Clear calculator."""
        self.display_value = '0'
        self.current_value = 0
        self.pending_op = None
        self.new_input = True
        self.error = False
    
    def _backspace(self):
        """Delete last character."""
        if self.error:
            self._clear()
            return
        
        if len(self.display_value) > 1:
            self.display_value = self.display_value[:-1]
        else:
            self.display_value = '0'
            self.new_input = True
    
    def _toggle_sign(self):
        """Toggle positive/negative."""
        if self.error:
            return
        
        if self.display_value.startswith('-'):
            self.display_value = self.display_value[1:]
        elif self.display_value != '0':
            self.display_value = '-' + self.display_value
    
    def _press_button(self, button: str):
        """Handle button press from grid."""
        if button.isdigit():
            self._input_digit(button)
        elif button in '+-*/':
            self._input_operator(button)
        elif button == '.':
            self._input_decimal()
        elif button == '=':
            self._calculate()
        elif button == 'C':
            self._clear()
        elif button == '±':
            self._toggle_sign()
    
    def draw(self, display: Display):
        """Draw calculator."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT,
                    display.width, display.height - self.ui.STATUS_BAR_HEIGHT,
                    fill='#111111')
        
        # Display area
        display_y = self.ui.STATUS_BAR_HEIGHT + 5
        display_h = 50
        display.rect(10, display_y, display.width - 20, display_h,
                    fill='#1a1a1a', color='#333333')
        
        # Current operation
        if self.pending_op:
            op_text = f"{self.current_value:.8g} {self.pending_op}"
            display.text(display.width - 15, display_y + 12, op_text,
                        '#888888', 12, 'rt')
        
        # Result/input
        color = '#ff4444' if self.error else '#00ff88'
        display.text(display.width - 15, display_y + 32, 
                    self.display_value, color, 20, 'rt')
        
        # Button grid
        grid_y = display_y + display_h + 10
        btn_width = (display.width - 30) // 4
        btn_height = 38
        
        for row_idx, row in enumerate(self.buttons):
            for col_idx, btn in enumerate(row):
                x = 10 + col_idx * (btn_width + 5)
                y = grid_y + row_idx * (btn_height + 5)
                
                # Selection
                is_selected = (row_idx == self.selected_row and 
                              col_idx == self.selected_col)
                
                # Button colors
                if btn in '+-*/=':
                    bg = '#ff8800' if is_selected else '#cc6600'
                elif btn == 'C':
                    bg = '#cc4444' if is_selected else '#993333'
                else:
                    bg = '#0066cc' if is_selected else '#333333'
                
                display.rect(x, y, btn_width, btn_height, 
                            fill=bg, color='#444444' if not is_selected else '#0088ff')
                display.text(x + btn_width // 2, y + btn_height // 2,
                            btn, 'white', 16, 'mm')

