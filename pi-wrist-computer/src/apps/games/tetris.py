"""
Tetris Game

Classic Tetris with trackball controls:
- Left/Right: Move piece
- Up: Rotate
- Down: Soft drop
- Click: Hard drop
"""

from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode
import random
import time


# Tetromino shapes
SHAPES = {
    'I': [(0, 0), (0, 1), (0, 2), (0, 3)],
    'O': [(0, 0), (0, 1), (1, 0), (1, 1)],
    'T': [(0, 1), (1, 0), (1, 1), (1, 2)],
    'S': [(0, 1), (0, 2), (1, 0), (1, 1)],
    'Z': [(0, 0), (0, 1), (1, 1), (1, 2)],
    'J': [(0, 0), (1, 0), (1, 1), (1, 2)],
    'L': [(0, 2), (1, 0), (1, 1), (1, 2)],
}

COLORS = {
    'I': '#00ffff',
    'O': '#ffff00',
    'T': '#aa00ff',
    'S': '#00ff00',
    'Z': '#ff0000',
    'J': '#0000ff',
    'L': '#ff8800',
}


class TetrisApp(App):
    """Tetris game."""
    
    GRID_WIDTH = 10
    GRID_HEIGHT = 20
    CELL_SIZE = 12
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='tetris',
            name='Tetris',
            icon='▦',
            color='#00ffff'
        )
        
        self.grid = []
        self.current_piece = None
        self.current_shape = None
        self.current_x = 0
        self.current_y = 0
        
        self.score = 0
        self.level = 1
        self.lines = 0
        self.game_over = False
        self.paused = False
        
        self.last_drop = 0
        self.drop_interval = 0.8
    
    def on_enter(self):
        """Start new game."""
        self._new_game()
    
    def on_exit(self):
        pass
    
    def _new_game(self):
        """Initialize new game."""
        self.grid = [[None] * self.GRID_WIDTH for _ in range(self.GRID_HEIGHT)]
        self.score = 0
        self.level = 1
        self.lines = 0
        self.game_over = False
        self.paused = False
        self.last_drop = time.time()
        self.drop_interval = 0.8
        self._spawn_piece()
    
    def _spawn_piece(self):
        """Spawn a new piece."""
        shape_name = random.choice(list(SHAPES.keys()))
        self.current_shape = shape_name
        self.current_piece = SHAPES[shape_name].copy()
        self.current_x = self.GRID_WIDTH // 2 - 2
        self.current_y = 0
        
        # Check game over
        if not self._valid_position(0, 0):
            self.game_over = True
    
    def _valid_position(self, dx: int, dy: int) -> bool:
        """Check if current piece can move to new position."""
        for py, px in self.current_piece:
            new_x = self.current_x + px + dx
            new_y = self.current_y + py + dy
            
            if new_x < 0 or new_x >= self.GRID_WIDTH:
                return False
            if new_y >= self.GRID_HEIGHT:
                return False
            if new_y >= 0 and self.grid[new_y][new_x] is not None:
                return False
        
        return True
    
    def _lock_piece(self):
        """Lock current piece into grid."""
        for py, px in self.current_piece:
            y = self.current_y + py
            x = self.current_x + px
            if 0 <= y < self.GRID_HEIGHT:
                self.grid[y][x] = self.current_shape
        
        self._clear_lines()
        self._spawn_piece()
    
    def _clear_lines(self):
        """Clear completed lines."""
        lines_cleared = 0
        y = self.GRID_HEIGHT - 1
        
        while y >= 0:
            if all(cell is not None for cell in self.grid[y]):
                del self.grid[y]
                self.grid.insert(0, [None] * self.GRID_WIDTH)
                lines_cleared += 1
            else:
                y -= 1
        
        if lines_cleared > 0:
            self.lines += lines_cleared
            # Scoring: 40, 100, 300, 1200 for 1, 2, 3, 4 lines
            points = [0, 40, 100, 300, 1200][lines_cleared] * self.level
            self.score += points
            
            # Level up every 10 lines
            new_level = self.lines // 10 + 1
            if new_level > self.level:
                self.level = new_level
                self.drop_interval = max(0.1, 0.8 - (self.level - 1) * 0.08)
    
    def _rotate(self):
        """Rotate current piece."""
        if self.current_shape == 'O':
            return  # O doesn't rotate
        
        # Rotate 90 degrees clockwise
        old_piece = self.current_piece.copy()
        max_y = max(p[0] for p in self.current_piece)
        
        self.current_piece = [(px, max_y - py) for py, px in self.current_piece]
        
        # Check if valid, otherwise revert
        if not self._valid_position(0, 0):
            self.current_piece = old_piece
    
    def _move(self, dx: int, dy: int):
        """Move piece if valid."""
        if self._valid_position(dx, dy):
            self.current_x += dx
            self.current_y += dy
            return True
        return False
    
    def _hard_drop(self):
        """Drop piece instantly."""
        while self._move(0, 1):
            self.score += 2
        self._lock_piece()
    
    def on_key(self, event: KeyEvent) -> bool:
        if self.game_over:
            if event.code == KeyCode.ENTER:
                self._new_game()
            elif event.code == KeyCode.ESC:
                self.ui.go_home()
            return True
        
        if event.code == KeyCode.LEFT:
            self._move(-1, 0)
            return True
        elif event.code == KeyCode.RIGHT:
            self._move(1, 0)
            return True
        elif event.code == KeyCode.UP:
            self._rotate()
            return True
        elif event.code == KeyCode.DOWN:
            if self._move(0, 1):
                self.score += 1
            return True
        elif event.code == KeyCode.SPACE or event.char == ' ':
            self._hard_drop()
            return True
        elif event.char == 'p' or event.char == 'P':
            self.paused = not self.paused
            return True
        elif event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        return False
    
    def on_click(self, x: int, y: int) -> bool:
        if not self.game_over and not self.paused:
            self._hard_drop()
        return True
    
    def update(self, dt: float):
        if self.game_over or self.paused:
            return
        
        now = time.time()
        if now - self.last_drop >= self.drop_interval:
            self.last_drop = now
            if not self._move(0, 1):
                self._lock_piece()
    
    def draw(self, display: Display):
        # Background
        display.rect(0, self.ui.STATUS_BAR_HEIGHT,
                    display.width, display.height - self.ui.STATUS_BAR_HEIGHT,
                    fill='#0a0a0a')
        
        # Calculate grid position
        grid_width = self.GRID_WIDTH * self.CELL_SIZE
        grid_height = self.GRID_HEIGHT * self.CELL_SIZE
        grid_x = (display.width - grid_width) // 2
        grid_y = self.ui.STATUS_BAR_HEIGHT + 5
        
        # Draw grid border
        display.rect(grid_x - 2, grid_y - 2, 
                    grid_width + 4, grid_height + 4,
                    color='#333333')
        
        # Draw locked pieces
        for y in range(self.GRID_HEIGHT):
            for x in range(self.GRID_WIDTH):
                if self.grid[y][x]:
                    color = COLORS.get(self.grid[y][x], '#ffffff')
                    px = grid_x + x * self.CELL_SIZE
                    py = grid_y + y * self.CELL_SIZE
                    display.rect(px, py, self.CELL_SIZE - 1, self.CELL_SIZE - 1,
                                fill=color)
        
        # Draw current piece
        if self.current_piece and not self.game_over:
            color = COLORS.get(self.current_shape, '#ffffff')
            for py, px in self.current_piece:
                x = grid_x + (self.current_x + px) * self.CELL_SIZE
                y = grid_y + (self.current_y + py) * self.CELL_SIZE
                if y >= grid_y:
                    display.rect(x, y, self.CELL_SIZE - 1, self.CELL_SIZE - 1,
                                fill=color)
        
        # Score panel
        panel_x = grid_x + grid_width + 10
        panel_y = grid_y
        
        display.text(panel_x, panel_y, 'Score', '#888888', 10)
        display.text(panel_x, panel_y + 12, str(self.score), 'white', 12)
        
        display.text(panel_x, panel_y + 35, 'Level', '#888888', 10)
        display.text(panel_x, panel_y + 47, str(self.level), 'white', 12)
        
        display.text(panel_x, panel_y + 70, 'Lines', '#888888', 10)
        display.text(panel_x, panel_y + 82, str(self.lines), 'white', 12)
        
        # Game over overlay
        if self.game_over:
            display.rect(grid_x, grid_y + grid_height // 2 - 25,
                        grid_width, 50, fill='#000000aa')
            display.text(grid_x + grid_width // 2, grid_y + grid_height // 2 - 10,
                        'GAME OVER', '#ff4444', 14, 'mm')
            display.text(grid_x + grid_width // 2, grid_y + grid_height // 2 + 10,
                        'Enter: Retry', '#888888', 11, 'mm')
        
        # Paused overlay
        if self.paused:
            display.rect(grid_x, grid_y + grid_height // 2 - 15,
                        grid_width, 30, fill='#000000aa')
            display.text(grid_x + grid_width // 2, grid_y + grid_height // 2,
                        'PAUSED', '#ffcc00', 14, 'mm')

