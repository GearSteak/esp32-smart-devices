"""
2048 Game

Slide tiles to combine and reach 2048.
"""

from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode
import random


# Tile colors
TILE_COLORS = {
    0: '#1a1a2e',
    2: '#eee4da',
    4: '#ede0c8',
    8: '#f2b179',
    16: '#f59563',
    32: '#f67c5f',
    64: '#f65e3b',
    128: '#edcf72',
    256: '#edcc61',
    512: '#edc850',
    1024: '#edc53f',
    2048: '#edc22e',
}

TILE_TEXT_COLORS = {
    2: '#776e65',
    4: '#776e65',
}


class Game2048App(App):
    """2048 game."""
    
    GRID_SIZE = 4
    CELL_SIZE = 42  # Reduced to fit 240px height
    CELL_GAP = 4
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='2048',
            name='2048',
            icon='🔢',
            color='#edc22e'
        )
        
        self.grid = [[0] * 4 for _ in range(4)]
        self.score = 0
        self.best_score = 0
        self.game_over = False
        self.won = False
    
    def on_enter(self):
        self._new_game()
    
    def on_exit(self):
        pass
    
    def _new_game(self):
        """Start new game."""
        self.grid = [[0] * 4 for _ in range(4)]
        self.score = 0
        self.game_over = False
        self.won = False
        self._spawn_tile()
        self._spawn_tile()
    
    def _spawn_tile(self):
        """Spawn a new tile (2 or 4)."""
        empty = [(r, c) for r in range(4) for c in range(4) if self.grid[r][c] == 0]
        if empty:
            r, c = random.choice(empty)
            self.grid[r][c] = 4 if random.random() < 0.1 else 2
    
    def _slide_row(self, row: list) -> tuple:
        """Slide and merge a row to the left. Returns (new_row, points)."""
        # Remove zeros
        tiles = [t for t in row if t > 0]
        
        # Merge
        merged = []
        points = 0
        skip = False
        
        for i, tile in enumerate(tiles):
            if skip:
                skip = False
                continue
            
            if i + 1 < len(tiles) and tiles[i + 1] == tile:
                merged_value = tile * 2
                merged.append(merged_value)
                points += merged_value
                skip = True
                
                if merged_value == 2048 and not self.won:
                    self.won = True
            else:
                merged.append(tile)
        
        # Pad with zeros
        merged.extend([0] * (4 - len(merged)))
        return merged, points
    
    def _move(self, direction: str) -> bool:
        """Move tiles. Returns True if anything moved."""
        old_grid = [row[:] for row in self.grid]
        points = 0
        
        if direction == 'left':
            for r in range(4):
                self.grid[r], pts = self._slide_row(self.grid[r])
                points += pts
        
        elif direction == 'right':
            for r in range(4):
                self.grid[r], pts = self._slide_row(self.grid[r][::-1])
                points += pts
                self.grid[r] = self.grid[r][::-1]
        
        elif direction == 'up':
            for c in range(4):
                col = [self.grid[r][c] for r in range(4)]
                new_col, pts = self._slide_row(col)
                points += pts
                for r in range(4):
                    self.grid[r][c] = new_col[r]
        
        elif direction == 'down':
            for c in range(4):
                col = [self.grid[r][c] for r in range(3, -1, -1)]
                new_col, pts = self._slide_row(col)
                points += pts
                for r in range(4):
                    self.grid[3 - r][c] = new_col[r]
        
        self.score += points
        if self.score > self.best_score:
            self.best_score = self.score
        
        # Check if grid changed
        moved = self.grid != old_grid
        
        if moved:
            self._spawn_tile()
            self._check_game_over()
        
        return moved
    
    def _check_game_over(self):
        """Check if no moves are possible."""
        # Check for empty cells
        for row in self.grid:
            if 0 in row:
                return
        
        # Check for possible merges
        for r in range(4):
            for c in range(4):
                val = self.grid[r][c]
                # Check right
                if c < 3 and self.grid[r][c + 1] == val:
                    return
                # Check down
                if r < 3 and self.grid[r + 1][c] == val:
                    return
        
        self.game_over = True
    
    def on_key(self, event: KeyEvent) -> bool:
        if self.game_over:
            if event.code == KeyCode.ENTER:
                self._new_game()
            elif event.code == KeyCode.ESC:
                self.ui.go_home()
            return True
        
        if event.code == KeyCode.UP:
            self._move('up')
            return True
        elif event.code == KeyCode.DOWN:
            self._move('down')
            return True
        elif event.code == KeyCode.LEFT:
            self._move('left')
            return True
        elif event.code == KeyCode.RIGHT:
            self._move('right')
            return True
        elif event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        elif event.char == 'r' or event.char == 'R':
            self._new_game()
            return True
        
        return False
    
    def draw(self, display: Display):
        # Background
        display.rect(0, self.ui.STATUS_BAR_HEIGHT,
                    display.width, display.height - self.ui.STATUS_BAR_HEIGHT,
                    fill='#0f0f1a')
        
        # Calculate grid position
        grid_total = self.GRID_SIZE * self.CELL_SIZE + (self.GRID_SIZE + 1) * self.CELL_GAP
        grid_x = (display.width - grid_total) // 2
        grid_y = self.ui.STATUS_BAR_HEIGHT + 28  # Reduced top margin
        
        # Scores (compact)
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 5, 
                    f'Score: {self.score}', 'white', 11)
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 5,
                    f'Best: {self.best_score}', '#888888', 11, 'rt')
        
        # Grid background
        display.rect(grid_x, grid_y, grid_total, grid_total,
                    fill='#2d2d44', color='#3d3d54')
        
        # Draw tiles
        for r in range(4):
            for c in range(4):
                value = self.grid[r][c]
                
                x = grid_x + self.CELL_GAP + c * (self.CELL_SIZE + self.CELL_GAP)
                y = grid_y + self.CELL_GAP + r * (self.CELL_SIZE + self.CELL_GAP)
                
                # Tile background
                bg_color = TILE_COLORS.get(value, '#3c3a32')
                display.rect(x, y, self.CELL_SIZE, self.CELL_SIZE,
                            fill=bg_color, color=bg_color)
                
                # Tile value
                if value > 0:
                    text_color = TILE_TEXT_COLORS.get(value, 'white')
                    
                    # Adjust font size for large numbers
                    if value < 100:
                        size = 20
                    elif value < 1000:
                        size = 16
                    else:
                        size = 12
                    
                    display.text(x + self.CELL_SIZE // 2, 
                                y + self.CELL_SIZE // 2,
                                str(value), text_color, size, 'mm')
        
        # Win message
        if self.won and not self.game_over:
            display.rect(grid_x, grid_y + grid_total // 2 - 20,
                        grid_total, 40, fill='#00000088')
            display.text(grid_x + grid_total // 2, grid_y + grid_total // 2,
                        'YOU WIN! 🎉', '#edc22e', 16, 'mm')
        
        # Game over overlay
        if self.game_over:
            display.rect(grid_x, grid_y + grid_total // 2 - 30,
                        grid_total, 60, fill='#000000cc')
            display.text(grid_x + grid_total // 2, grid_y + grid_total // 2 - 10,
                        'GAME OVER', '#ff4444', 16, 'mm')
            display.text(grid_x + grid_total // 2, grid_y + grid_total // 2 + 12,
                        'Enter: Retry', '#888888', 12, 'mm')
        
        # Controls hint
        display.text(display.width // 2, display.height - 15,
                    '↑↓←→: Move | R: Restart', '#555555', 10, 'mm')

