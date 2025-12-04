"""
Dice Roller Application

D&D style dice roller with:
- Standard dice (d4, d6, d8, d10, d12, d20, d100)
- Multiple dice rolls (2d6, 4d8, etc.)
- Modifiers (+5, -2, etc.)
- Roll history
- Custom dice
"""

from ..ui.framework import App, AppInfo, Rect
from ..ui.display import Display
from ..input.cardkb import KeyEvent, KeyCode
import random
from datetime import datetime


class DiceApp(App):
    """Dice roller for tabletop games."""
    
    DICE_TYPES = [4, 6, 8, 10, 12, 20, 100]
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='dice',
            name='Dice',
            icon='🎲',
            color='#9b59b6'
        )
        
        # Current selection
        self.selected_dice = 5  # Index for d20
        self.num_dice = 1
        self.modifier = 0
        
        # Roll history
        self.history = []  # List of {'dice': 'd20', 'rolls': [15], 'total': 15, 'mod': 0}
        
        # State
        self.mode = 'select'  # 'select', 'result', 'history'
        self.last_result = None
        
        # Animation
        self.rolling = False
        self.roll_frames = 0
    
    def on_enter(self):
        self.mode = 'select'
    
    def on_exit(self):
        pass
    
    def _roll_dice(self):
        """Roll the selected dice."""
        dice_type = self.DICE_TYPES[self.selected_dice]
        rolls = [random.randint(1, dice_type) for _ in range(self.num_dice)]
        total = sum(rolls) + self.modifier
        
        self.last_result = {
            'dice': f'{self.num_dice}d{dice_type}',
            'rolls': rolls,
            'total': total,
            'modifier': self.modifier,
            'time': datetime.now().strftime('%H:%M')
        }
        
        # Add to history
        self.history.insert(0, self.last_result)
        if len(self.history) > 20:
            self.history.pop()
        
        self.mode = 'result'
        self.rolling = False
    
    def _start_roll(self):
        """Start roll animation."""
        self.rolling = True
        self.roll_frames = 10
    
    def on_key(self, event: KeyEvent) -> bool:
        if self.mode == 'select':
            return self._handle_select_key(event)
        elif self.mode == 'result':
            return self._handle_result_key(event)
        elif self.mode == 'history':
            return self._handle_history_key(event)
        return False
    
    def _handle_select_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.LEFT:
            if self.selected_dice > 0:
                self.selected_dice -= 1
            return True
        elif event.code == KeyCode.RIGHT:
            if self.selected_dice < len(self.DICE_TYPES) - 1:
                self.selected_dice += 1
            return True
        elif event.code == KeyCode.UP:
            self.num_dice = min(20, self.num_dice + 1)
            return True
        elif event.code == KeyCode.DOWN:
            self.num_dice = max(1, self.num_dice - 1)
            return True
        elif event.char == '+' or event.char == '=':
            self.modifier += 1
            return True
        elif event.char == '-':
            self.modifier -= 1
            return True
        elif event.char == '0':
            self.modifier = 0
            return True
        elif event.code == KeyCode.ENTER or event.code == KeyCode.SPACE:
            self._start_roll()
            return True
        elif event.char == 'h' or event.char == 'H':
            if self.history:
                self.mode = 'history'
            return True
        elif event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        # Quick dice shortcuts
        shortcuts = {'1': 0, '2': 1, '3': 2, '4': 3, '5': 4, '6': 5, '7': 6}
        if event.char in shortcuts:
            self.selected_dice = shortcuts[event.char]
            return True
        
        return False
    
    def _handle_result_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ENTER or event.code == KeyCode.SPACE:
            self._start_roll()  # Roll again
            return True
        elif event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self.mode = 'select'
            return True
        elif event.char == 'h' or event.char == 'H':
            self.mode = 'history'
            return True
        return False
    
    def _handle_history_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self.mode = 'select'
            return True
        elif event.char == 'c' or event.char == 'C':
            self.history = []
            self.mode = 'select'
            return True
        return False
    
    def update(self, dt: float):
        """Update roll animation."""
        if self.rolling and self.roll_frames > 0:
            self.roll_frames -= 1
            if self.roll_frames == 0:
                self._roll_dice()
    
    def draw(self, display: Display):
        """Draw dice roller."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT,
                    display.width, display.height - self.ui.STATUS_BAR_HEIGHT,
                    fill='#1a0a2e')
        
        if self.mode == 'select':
            self._draw_select(display)
        elif self.mode == 'result':
            self._draw_result(display)
        elif self.mode == 'history':
            self._draw_history(display)
    
    def _draw_select(self, display: Display):
        """Draw dice selection screen."""
        # Title
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 15,
                    'Dice Roller', 'white', 16, 'mm')
        
        # Dice selector
        y = self.ui.STATUS_BAR_HEIGHT + 50
        dice_width = 32
        total_width = len(self.DICE_TYPES) * dice_width
        start_x = (display.width - total_width) // 2
        
        for i, dice in enumerate(self.DICE_TYPES):
            x = start_x + i * dice_width + dice_width // 2
            selected = (i == self.selected_dice)
            
            if selected:
                display.circle(x, y, 18, fill='#9b59b6')
            
            display.text(x, y, f'd{dice}', 
                        'white' if selected else '#888888', 
                        12 if dice < 100 else 10, 'mm')
        
        # Number of dice
        y += 50
        display.text(display.width // 2, y, f'{self.num_dice}', 'white', 32, 'mm')
        display.text(display.width // 2, y + 25, '↑/↓ Number of dice', '#666666', 10, 'mm')
        
        # Modifier
        y += 55
        mod_str = f'+{self.modifier}' if self.modifier >= 0 else str(self.modifier)
        mod_color = '#00ff00' if self.modifier > 0 else ('#ff4444' if self.modifier < 0 else '#888888')
        display.text(display.width // 2, y, f'Modifier: {mod_str}', mod_color, 14, 'mm')
        display.text(display.width // 2, y + 18, '+/- to adjust, 0 to reset', '#666666', 9, 'mm')
        
        # Current formula
        y += 40
        dice_type = self.DICE_TYPES[self.selected_dice]
        formula = f'{self.num_dice}d{dice_type}'
        if self.modifier != 0:
            formula += f' {mod_str}'
        display.rect(40, y, display.width - 80, 30, fill='#2a1a3e', color='#9b59b6')
        display.text(display.width // 2, y + 15, formula, '#9b59b6', 16, 'mm')
        
        # Roll button hint
        display.text(display.width // 2, display.height - 35,
                    'ENTER to Roll', '#888888', 12, 'mm')
        display.text(display.width // 2, display.height - 18,
                    'H: History | 1-7: Quick select', '#555555', 9, 'mm')
    
    def _draw_result(self, display: Display):
        """Draw roll result."""
        if self.rolling:
            # Animation
            display.text(display.width // 2, display.height // 2,
                        '🎲', 'white', 48, 'mm')
            rand_num = random.randint(1, self.DICE_TYPES[self.selected_dice])
            display.text(display.width // 2, display.height // 2 + 50,
                        str(rand_num), '#888888', 24, 'mm')
            return
        
        if not self.last_result:
            return
        
        result = self.last_result
        
        # Dice type
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 20,
                    result['dice'], '#9b59b6', 18, 'mm')
        
        # Big total
        total = result['total']
        display.text(display.width // 2, display.height // 2 - 10,
                    str(total), 'white', 56, 'mm')
        
        # Individual rolls
        if len(result['rolls']) > 1:
            rolls_str = ' + '.join(str(r) for r in result['rolls'][:8])
            if len(result['rolls']) > 8:
                rolls_str += '...'
            display.text(display.width // 2, display.height // 2 + 40,
                        f'({rolls_str})', '#888888', 11, 'mm')
        
        # Modifier
        if result['modifier'] != 0:
            mod_str = f"+{result['modifier']}" if result['modifier'] > 0 else str(result['modifier'])
            display.text(display.width // 2, display.height // 2 + 60,
                        f'Modifier: {mod_str}', '#666666', 11, 'mm')
        
        # Critical indicators for d20
        if result['dice'] == '1d20' and len(result['rolls']) == 1:
            roll = result['rolls'][0]
            if roll == 20:
                display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 45,
                            '⭐ CRITICAL! ⭐', '#ffcc00', 14, 'mm')
            elif roll == 1:
                display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 45,
                            '💀 Critical Fail 💀', '#ff4444', 14, 'mm')
        
        # Controls
        display.text(display.width // 2, display.height - 30,
                    'ENTER: Roll Again | ESC: Back', '#666666', 10, 'mm')
        display.text(display.width // 2, display.height - 15,
                    'H: History', '#555555', 9, 'mm')
    
    def _draw_history(self, display: Display):
        """Draw roll history."""
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 10,
                    'Roll History', 'white', 14, 'mm')
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 10,
                    'C: Clear', '#666666', 9, 'rt')
        
        if not self.history:
            display.text(display.width // 2, display.height // 2,
                        'No rolls yet', '#666666', 12, 'mm')
            return
        
        y = self.ui.STATUS_BAR_HEIGHT + 30
        item_height = 28
        max_visible = (display.height - y - 20) // item_height
        
        for i, roll in enumerate(self.history[:max_visible]):
            item_y = y + i * item_height
            
            # Time
            display.text(10, item_y + 5, roll['time'], '#666666', 9)
            
            # Dice
            display.text(50, item_y + 5, roll['dice'], '#9b59b6', 11)
            
            # Result
            display.text(display.width - 10, item_y + 5, 
                        str(roll['total']), 'white', 14, 'rt')

