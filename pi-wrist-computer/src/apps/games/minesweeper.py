"""
Minesweeper Game
Classic mine-finding puzzle game.
"""

import random
from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode


class MinesweeperApp(App):
    """Minesweeper game."""
    
    # Difficulty presets
    DIFFICULTIES = {
        'easy': (8, 10, 10),      # cols, rows, mines
        'medium': (12, 16, 30),
        'hard': (16, 20, 60),
    }
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='minesweeper',
            name='Minesweeper',
            icon='💣',
            color='#888888'
        )
        
        self.difficulty = 'easy'
        self.cols, self.rows, self.mine_count = self.DIFFICULTIES[self.difficulty]
        self.cell_size = 16
        
        self.grid = []
        self.revealed = []
        self.flagged = []
        self.cursor_x = 0
        self.cursor_y = 0
        self.game_over = False
        self.won = False
        self.first_click = True
    
    def on_enter(self):
        self._new_game()
    
    def _new_game(self):
        """Start a new game."""
        self.cols, self.rows, self.mine_count = self.DIFFICULTIES[self.difficulty]
        self.grid = [[0] * self.cols for _ in range(self.rows)]
        self.revealed = [[False] * self.cols for _ in range(self.rows)]
        self.flagged = [[False] * self.cols for _ in range(self.rows)]
        self.cursor_x = self.cols // 2
        self.cursor_y = self.rows // 2
        self.game_over = False
        self.won = False
        self.first_click = True
    
    def _place_mines(self, safe_x: int, safe_y: int):
        """Place mines avoiding the first click location."""
        positions = [(x, y) for x in range(self.cols) for y in range(self.rows)
                    if abs(x - safe_x) > 1 or abs(y - safe_y) > 1]
        
        mine_positions = random.sample(positions, min(self.mine_count, len(positions)))
        
        for x, y in mine_positions:
            self.grid[y][x] = -1  # -1 = mine
        
        # Calculate numbers
        for y in range(self.rows):
            for x in range(self.cols):
                if self.grid[y][x] == -1:
                    continue
                count = 0
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < self.cols and 0 <= ny < self.rows:
                            if self.grid[ny][nx] == -1:
                                count += 1
                self.grid[y][x] = count
    
    def _reveal(self, x: int, y: int):
        """Reveal a cell."""
        if not (0 <= x < self.cols and 0 <= y < self.rows):
            return
        if self.revealed[y][x] or self.flagged[y][x]:
            return
        
        self.revealed[y][x] = True
        
        if self.grid[y][x] == -1:
            self.game_over = True
            return
        
        if self.grid[y][x] == 0:
            # Flood fill for empty cells
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    self._reveal(x + dx, y + dy)
        
        self._check_win()
    
    def _check_win(self):
        """Check if player has won."""
        for y in range(self.rows):
            for x in range(self.cols):
                if self.grid[y][x] != -1 and not self.revealed[y][x]:
                    return
        self.won = True
        self.game_over = True
    
    def on_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        if self.game_over:
            if event.code == KeyCode.ENTER:
                self._new_game()
            return True
        
        if event.code == KeyCode.UP:
            self.cursor_y = max(0, self.cursor_y - 1)
        elif event.code == KeyCode.DOWN:
            self.cursor_y = min(self.rows - 1, self.cursor_y + 1)
        elif event.code == KeyCode.LEFT:
            self.cursor_x = max(0, self.cursor_x - 1)
        elif event.code == KeyCode.RIGHT:
            self.cursor_x = min(self.cols - 1, self.cursor_x + 1)
        elif event.code == KeyCode.ENTER:
            if self.first_click:
                self._place_mines(self.cursor_x, self.cursor_y)
                self.first_click = False
            self._reveal(self.cursor_x, self.cursor_y)
        elif event.char == 'f' or event.char == 'F' or event.char == ' ':
            if not self.revealed[self.cursor_y][self.cursor_x]:
                self.flagged[self.cursor_y][self.cursor_x] = not self.flagged[self.cursor_y][self.cursor_x]
        elif event.char == 'n' or event.char == 'N':
            self._new_game()
        elif event.char == 'd' or event.char == 'D':
            # Cycle difficulty
            diffs = list(self.DIFFICULTIES.keys())
            idx = diffs.index(self.difficulty)
            self.difficulty = diffs[(idx + 1) % len(diffs)]
            self._new_game()
        
        return True
    
    def draw(self, display: Display):
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width, 
                    display.height - self.ui.STATUS_BAR_HEIGHT, fill='#1a1a1a')
        
        # Calculate offset to center grid
        grid_width = self.cols * self.cell_size
        grid_height = self.rows * self.cell_size
        offset_x = (display.width - grid_width) // 2
        offset_y = self.ui.STATUS_BAR_HEIGHT + 25
        
        # Header
        flags_used = sum(row.count(True) for row in self.flagged)
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 12, 
                    f"💣{self.mine_count - flags_used}", 'white', 12)
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 12,
                    self.difficulty.upper(), '#888888', 10, 'rt')
        
        # Draw grid
        colors = ['#888888', '#0000ff', '#008000', '#ff0000', '#000080', 
                 '#800000', '#008080', '#000000', '#808080']
        
        for y in range(self.rows):
            for x in range(self.cols):
                px = offset_x + x * self.cell_size
                py = offset_y + y * self.cell_size
                
                is_cursor = (x == self.cursor_x and y == self.cursor_y)
                
                if self.revealed[y][x]:
                    display.rect(px, py, self.cell_size - 1, self.cell_size - 1, fill='#333333')
                    if self.grid[y][x] == -1:
                        display.text(px + self.cell_size // 2, py + self.cell_size // 2,
                                   '💥', 'white', 10, 'mm')
                    elif self.grid[y][x] > 0:
                        display.text(px + self.cell_size // 2, py + self.cell_size // 2,
                                   str(self.grid[y][x]), colors[self.grid[y][x]], 10, 'mm')
                else:
                    color = '#0066cc' if is_cursor else '#666666'
                    display.rect(px, py, self.cell_size - 1, self.cell_size - 1, fill=color)
                    if self.flagged[y][x]:
                        display.text(px + self.cell_size // 2, py + self.cell_size // 2,
                                   '🚩', 'red', 8, 'mm')
        
        # Game over overlay
        if self.game_over:
            display.rect(30, display.height // 2 - 30, display.width - 60, 60, 
                        fill='#000000', outline='white')
            msg = "🎉 YOU WIN!" if self.won else "💥 GAME OVER"
            display.text(display.width // 2, display.height // 2 - 10, msg, 
                        '#00ff00' if self.won else '#ff0000', 16, 'mm')
            display.text(display.width // 2, display.height // 2 + 15,
                        "Press ENTER to play again", '#888888', 10, 'mm')
        
        # Help
        display.text(display.width // 2, display.height - 10,
                    "⏎:Dig F:Flag D:Difficulty", '#555555', 9, 'mm')

