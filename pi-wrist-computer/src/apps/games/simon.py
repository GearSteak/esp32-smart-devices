"""
Simon Says Game
Memory pattern game.
"""

import time
import random
from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode


class SimonApp(App):
    """Simon Says memory game."""
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='simon',
            name='Simon',
            icon='🔔',
            color='#9b59b6'
        )
        
        self.colors = ['red', 'green', 'blue', 'yellow']
        self.color_values = {
            'red': '#ff0000',
            'green': '#00ff00',
            'blue': '#0000ff',
            'yellow': '#ffff00'
        }
        self.dim_values = {
            'red': '#660000',
            'green': '#006600',
            'blue': '#000066',
            'yellow': '#666600'
        }
        
        self.sequence = []
        self.player_pos = 0
        self.showing_sequence = False
        self.show_index = 0
        self.show_time = 0
        self.highlighted = None
        self.game_over = False
        self.score = 0
        self.high_score = 0
        self.state = 'waiting'  # waiting, showing, input
    
    def on_enter(self):
        self._new_game()
    
    def on_exit(self):
        pass
    
    def _new_game(self):
        """Start a new game."""
        self.sequence = []
        self.player_pos = 0
        self.showing_sequence = False
        self.game_over = False
        self.score = 0
        self.state = 'waiting'
        self.highlighted = None
    
    def _add_to_sequence(self):
        """Add a new color to the sequence."""
        self.sequence.append(random.choice(self.colors))
        self.show_index = 0
        self.showing_sequence = True
        self.state = 'showing'
        self.show_time = time.time() + 0.5
    
    def _check_input(self, color: str):
        """Check player input."""
        if color == self.sequence[self.player_pos]:
            self.player_pos += 1
            self.highlighted = color
            
            if self.player_pos >= len(self.sequence):
                self.score = len(self.sequence)
                if self.score > self.high_score:
                    self.high_score = self.score
                self.player_pos = 0
                self._add_to_sequence()
        else:
            self.game_over = True
            if self.score > self.high_score:
                self.high_score = self.score
    
    def on_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        if self.game_over:
            if event.code == KeyCode.ENTER:
                self._new_game()
            return True
        
        if self.state == 'waiting':
            if event.code == KeyCode.ENTER:
                self._add_to_sequence()
            return True
        
        if self.state != 'input':
            return True
        
        # Map keys to colors
        key_map = {
            'r': 'red', 'R': 'red',
            'g': 'green', 'G': 'green',
            'b': 'blue', 'B': 'blue',
            'y': 'yellow', 'Y': 'yellow',
        }
        
        # Also map arrow keys
        if event.code == KeyCode.UP:
            self._check_input('red')
        elif event.code == KeyCode.RIGHT:
            self._check_input('green')
        elif event.code == KeyCode.DOWN:
            self._check_input('blue')
        elif event.code == KeyCode.LEFT:
            self._check_input('yellow')
        elif event.char in key_map:
            self._check_input(key_map[event.char])
        
        return True
    
    def _update(self):
        """Update sequence display."""
        if self.state != 'showing':
            if self.highlighted and time.time() > self.show_time:
                self.highlighted = None
            return
        
        now = time.time()
        if now < self.show_time:
            return
        
        if self.show_index < len(self.sequence):
            self.highlighted = self.sequence[self.show_index]
            self.show_index += 1
            self.show_time = now + 0.6
        else:
            self.highlighted = None
            self.state = 'input'
            self.player_pos = 0
    
    def draw(self, display: Display):
        self._update()
        
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width,
                    display.height - self.ui.STATUS_BAR_HEIGHT, fill='#1a1a1a')
        
        # Score
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 15,
                    f"Score: {self.score}", 'white', 14, 'mm')
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 15,
                    f"Best: {self.high_score}", '#888888', 10, 'rt')
        
        # Simon buttons (cross pattern)
        center_x = display.width // 2
        center_y = display.height // 2 + 10
        size = 50
        gap = 5
        
        positions = {
            'red': (center_x, center_y - size - gap),      # Top
            'green': (center_x + size + gap, center_y),    # Right
            'blue': (center_x, center_y + size + gap),     # Bottom
            'yellow': (center_x - size - gap, center_y),   # Left
        }
        
        for color, (x, y) in positions.items():
            if color == self.highlighted:
                fill = self.color_values[color]
            else:
                fill = self.dim_values[color]
            
            display.rect(x - size // 2, y - size // 2, size, size, fill=fill)
        
        # Key hints
        display.text(center_x, center_y - size - gap, "↑", 'white', 12, 'mm')
        display.text(center_x + size + gap, center_y, "→", 'white', 12, 'mm')
        display.text(center_x, center_y + size + gap, "↓", 'white', 12, 'mm')
        display.text(center_x - size - gap, center_y, "←", 'white', 12, 'mm')
        
        # State message
        if self.state == 'waiting':
            display.text(display.width // 2, display.height - 30,
                        "Press ENTER to start", '#888888', 12, 'mm')
        elif self.state == 'showing':
            display.text(display.width // 2, display.height - 30,
                        "Watch the pattern...", '#ffff00', 12, 'mm')
        elif self.state == 'input':
            display.text(display.width // 2, display.height - 30,
                        f"Your turn! ({self.player_pos + 1}/{len(self.sequence)})", '#00ff00', 12, 'mm')
        
        # Game over
        if self.game_over:
            display.rect(30, display.height // 2 - 30, display.width - 60, 60,
                        fill='#000000', outline='white')
            display.text(display.width // 2, display.height // 2 - 10,
                        "GAME OVER", '#ff0000', 16, 'mm')
            display.text(display.width // 2, display.height // 2 + 10,
                        f"Score: {self.score}", 'white', 12, 'mm')

