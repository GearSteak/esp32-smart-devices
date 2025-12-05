"""
Memory Match Game
Find matching pairs of cards.
"""

import random
import time
from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode


class MemoryApp(App):
    """Memory card matching game."""
    
    SYMBOLS = ['🍎', '🍊', '🍋', '🍇', '🍓', '🍒', '🥝', '🍑']
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='memory',
            name='Memory',
            icon='🧠',
            color='#9b59b6'
        )
        
        self.cols = 4
        self.rows = 4
        self.cards = []
        self.revealed = []
        self.matched = []
        self.first_pick = None
        self.second_pick = None
        self.cursor = [0, 0]
        self.moves = 0
        self.lock_until = 0
        self.won = False
    
    def on_enter(self):
        self._new_game()
    
    def on_exit(self):
        pass
    
    def _new_game(self):
        """Start a new game."""
        pairs = self.SYMBOLS[:(self.cols * self.rows) // 2]
        deck = pairs * 2
        random.shuffle(deck)
        
        self.cards = [deck[r * self.cols:(r + 1) * self.cols] for r in range(self.rows)]
        self.revealed = [[False] * self.cols for _ in range(self.rows)]
        self.matched = [[False] * self.cols for _ in range(self.rows)]
        self.first_pick = None
        self.second_pick = None
        self.cursor = [0, 0]
        self.moves = 0
        self.lock_until = 0
        self.won = False
    
    def on_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        if self.won:
            if event.code == KeyCode.ENTER:
                self._new_game()
            return True
        
        # Locked while showing mismatch
        if time.time() < self.lock_until:
            return True
        
        # Hide mismatched cards
        if self.first_pick and self.second_pick:
            r1, c1 = self.first_pick
            r2, c2 = self.second_pick
            if not self.matched[r1][c1]:
                self.revealed[r1][c1] = False
                self.revealed[r2][c2] = False
            self.first_pick = None
            self.second_pick = None
        
        if event.code == KeyCode.UP:
            self.cursor[0] = max(0, self.cursor[0] - 1)
        elif event.code == KeyCode.DOWN:
            self.cursor[0] = min(self.rows - 1, self.cursor[0] + 1)
        elif event.code == KeyCode.LEFT:
            self.cursor[1] = max(0, self.cursor[1] - 1)
        elif event.code == KeyCode.RIGHT:
            self.cursor[1] = min(self.cols - 1, self.cursor[1] + 1)
        elif event.code == KeyCode.ENTER:
            self._pick_card()
        elif event.char == 'n' or event.char == 'N':
            self._new_game()
        
        return True
    
    def _pick_card(self):
        """Pick current card."""
        r, c = self.cursor
        
        if self.revealed[r][c] or self.matched[r][c]:
            return
        
        self.revealed[r][c] = True
        
        if self.first_pick is None:
            self.first_pick = (r, c)
        else:
            self.second_pick = (r, c)
            self.moves += 1
            
            r1, c1 = self.first_pick
            r2, c2 = self.second_pick
            
            if self.cards[r1][c1] == self.cards[r2][c2]:
                # Match!
                self.matched[r1][c1] = True
                self.matched[r2][c2] = True
                self.first_pick = None
                self.second_pick = None
                
                # Check win
                if all(all(row) for row in self.matched):
                    self.won = True
            else:
                # Mismatch - show for a moment
                self.lock_until = time.time() + 1.0
    
    def draw(self, display: Display):
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width,
                    display.height - self.ui.STATUS_BAR_HEIGHT, fill='#1a1a1a')
        
        # Info
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 15, f"Moves: {self.moves}", 'white', 12)
        
        cell_size = 40  # Reduced for 240px height
        gap = 4
        grid_width = self.cols * cell_size + (self.cols - 1) * gap
        grid_height = self.rows * cell_size + (self.rows - 1) * gap
        offset_x = (display.width - grid_width) // 2
        offset_y = self.ui.STATUS_BAR_HEIGHT + 30
        
        for r in range(self.rows):
            for c in range(self.cols):
                x = offset_x + c * (cell_size + gap)
                y = offset_y + r * (cell_size + gap)
                
                is_cursor = (r == self.cursor[0] and c == self.cursor[1])
                
                if self.matched[r][c]:
                    display.rect(x, y, cell_size, cell_size, fill='#27ae60')
                    display.text(x + cell_size // 2, y + cell_size // 2,
                               self.cards[r][c], 'white', 20, 'mm')
                elif self.revealed[r][c]:
                    display.rect(x, y, cell_size, cell_size, fill='#f39c12')
                    display.text(x + cell_size // 2, y + cell_size // 2,
                               self.cards[r][c], 'white', 20, 'mm')
                else:
                    color = '#3498db' if is_cursor else '#2c3e50'
                    display.rect(x, y, cell_size, cell_size, fill=color)
                    display.text(x + cell_size // 2, y + cell_size // 2,
                               "?", '#888888', 18, 'mm')
                
                if is_cursor:
                    display.rect(x - 2, y - 2, cell_size + 4, cell_size + 4, 
                               color='#ffffff', width=2)
        
        # Win message
        if self.won:
            display.rect(30, display.height // 2 - 25, display.width - 60, 50,
                        fill='#000000', outline='white')
            display.text(display.width // 2, display.height // 2 - 5,
                        "🎉 YOU WIN!", '#00ff00', 16, 'mm')
            display.text(display.width // 2, display.height // 2 + 15,
                        f"Moves: {self.moves}", 'white', 12, 'mm')

