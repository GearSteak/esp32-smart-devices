"""
15 Puzzle Game
Sliding tile puzzle.
"""

import random
from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode


class Puzzle15App(App):
    """15 Puzzle sliding tile game."""
    
    SIZE = 4
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='puzzle15',
            name='15 Puzzle',
            icon='🧩',
            color='#3498db'
        )
        
        self.tiles = []
        self.empty_pos = (3, 3)
        self.moves = 0
        self.won = False
    
    def on_enter(self):
        self._new_game()
    
    def on_exit(self):
        pass
    
    def _new_game(self):
        """Start a new game."""
        # Create solved state
        self.tiles = [[r * self.SIZE + c + 1 for c in range(self.SIZE)] for r in range(self.SIZE)]
        self.tiles[3][3] = 0
        self.empty_pos = (3, 3)
        self.moves = 0
        self.won = False
        
        # Shuffle by making random valid moves
        for _ in range(100):
            directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            random.shuffle(directions)
            for dr, dc in directions:
                nr, nc = self.empty_pos[0] + dr, self.empty_pos[1] + dc
                if 0 <= nr < self.SIZE and 0 <= nc < self.SIZE:
                    self._swap(nr, nc)
                    break
        
        self.moves = 0
    
    def _swap(self, row: int, col: int):
        """Swap tile with empty space."""
        er, ec = self.empty_pos
        self.tiles[er][ec] = self.tiles[row][col]
        self.tiles[row][col] = 0
        self.empty_pos = (row, col)
        self.moves += 1
    
    def _check_win(self):
        """Check if puzzle is solved."""
        expected = 1
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                if r == self.SIZE - 1 and c == self.SIZE - 1:
                    if self.tiles[r][c] != 0:
                        return False
                elif self.tiles[r][c] != expected:
                    return False
                expected += 1
        return True
    
    def on_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        if self.won:
            if event.code == KeyCode.ENTER:
                self._new_game()
            return True
        
        er, ec = self.empty_pos
        
        # Move tile into empty space
        if event.code == KeyCode.UP and er < self.SIZE - 1:
            self._swap(er + 1, ec)
        elif event.code == KeyCode.DOWN and er > 0:
            self._swap(er - 1, ec)
        elif event.code == KeyCode.LEFT and ec < self.SIZE - 1:
            self._swap(er, ec + 1)
        elif event.code == KeyCode.RIGHT and ec > 0:
            self._swap(er, ec - 1)
        elif event.char == 'n' or event.char == 'N':
            self._new_game()
        
        if not self.won and self._check_win():
            self.won = True
        
        return True
    
    def draw(self, display: Display):
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width,
                    display.height - self.ui.STATUS_BAR_HEIGHT, fill='#1a1a1a')
        
        # Info
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 15, f"Moves: {self.moves}", 'white', 12)
        
        cell_size = 42  # Reduced for 240px height
        grid_size = self.SIZE * cell_size
        offset_x = (display.width - grid_size) // 2
        offset_y = self.ui.STATUS_BAR_HEIGHT + 30
        
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                x = offset_x + c * cell_size
                y = offset_y + r * cell_size
                tile = self.tiles[r][c]
                
                if tile == 0:
                    display.rect(x + 2, y + 2, cell_size - 4, cell_size - 4, fill='#333333')
                else:
                    # Color based on correct position
                    correct_r, correct_c = (tile - 1) // self.SIZE, (tile - 1) % self.SIZE
                    if (r, c) == (correct_r, correct_c):
                        color = '#27ae60'
                    else:
                        color = '#2980b9'
                    
                    display.rect(x + 2, y + 2, cell_size - 4, cell_size - 4, fill=color)
                    display.text(x + cell_size // 2, y + cell_size // 2,
                               str(tile), 'white', 18, 'mm')
        
        # Win message
        if self.won:
            display.rect(30, display.height // 2 - 25, display.width - 60, 50,
                        fill='#000000', outline='white')
            display.text(display.width // 2, display.height // 2 - 5,
                        "🎉 SOLVED!", '#00ff00', 16, 'mm')
            display.text(display.width // 2, display.height // 2 + 15,
                        f"Moves: {self.moves}", 'white', 12, 'mm')
        
        # Help
        display.text(display.width // 2, display.height - 10,
                    "Arrow keys to slide tiles", '#555555', 9, 'mm')

