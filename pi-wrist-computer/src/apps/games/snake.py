"""
Snake Game

Classic Snake with trackball controls.
"""

from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode
import random
import time


class SnakeApp(App):
    """Snake game."""
    
    GRID_SIZE = 15
    CELL_SIZE = 14
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='snake',
            name='Snake',
            icon='🐍',
            color='#00ff00'
        )
        
        self.snake = []
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.food = (0, 0)
        self.score = 0
        self.high_score = 0
        self.game_over = False
        self.paused = False
        
        self.last_move = 0
        self.move_interval = 0.15
    
    def on_enter(self):
        self._new_game()
    
    def on_exit(self):
        pass
    
    def _new_game(self):
        """Start new game."""
        center = self.GRID_SIZE // 2
        self.snake = [(center, center), (center - 1, center), (center - 2, center)]
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.score = 0
        self.game_over = False
        self.paused = False
        self.last_move = time.time()
        self._spawn_food()
    
    def _spawn_food(self):
        """Spawn food at random position."""
        while True:
            x = random.randint(0, self.GRID_SIZE - 1)
            y = random.randint(0, self.GRID_SIZE - 1)
            if (x, y) not in self.snake:
                self.food = (x, y)
                break
    
    def _move_snake(self):
        """Move snake one step."""
        self.direction = self.next_direction
        
        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)
        
        # Check wall collision
        if (new_head[0] < 0 or new_head[0] >= self.GRID_SIZE or
            new_head[1] < 0 or new_head[1] >= self.GRID_SIZE):
            self.game_over = True
            if self.score > self.high_score:
                self.high_score = self.score
            return
        
        # Check self collision
        if new_head in self.snake:
            self.game_over = True
            if self.score > self.high_score:
                self.high_score = self.score
            return
        
        # Move snake
        self.snake.insert(0, new_head)
        
        # Check food
        if new_head == self.food:
            self.score += 10
            self._spawn_food()
            # Speed up slightly
            self.move_interval = max(0.05, self.move_interval - 0.005)
        else:
            self.snake.pop()
    
    def on_key(self, event: KeyEvent) -> bool:
        if self.game_over:
            if event.code == KeyCode.ENTER:
                self._new_game()
            elif event.code == KeyCode.ESC:
                self.ui.go_home()
            return True
        
        # Direction changes (prevent 180 turns)
        if event.code == KeyCode.UP and self.direction != (0, 1):
            self.next_direction = (0, -1)
            return True
        elif event.code == KeyCode.DOWN and self.direction != (0, -1):
            self.next_direction = (0, 1)
            return True
        elif event.code == KeyCode.LEFT and self.direction != (1, 0):
            self.next_direction = (-1, 0)
            return True
        elif event.code == KeyCode.RIGHT and self.direction != (-1, 0):
            self.next_direction = (1, 0)
            return True
        elif event.char == 'p' or event.char == 'P':
            self.paused = not self.paused
            return True
        elif event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        return False
    
    def update(self, dt: float):
        if self.game_over or self.paused:
            return
        
        now = time.time()
        if now - self.last_move >= self.move_interval:
            self.last_move = now
            self._move_snake()
    
    def draw(self, display: Display):
        # Background
        display.rect(0, self.ui.STATUS_BAR_HEIGHT,
                    display.width, display.height - self.ui.STATUS_BAR_HEIGHT,
                    fill='#0a1a0a')
        
        # Calculate grid position
        grid_size = self.GRID_SIZE * self.CELL_SIZE
        grid_x = (display.width - grid_size) // 2
        grid_y = self.ui.STATUS_BAR_HEIGHT + 25
        
        # Score
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 5, 
                    f'Score: {self.score}', 'white', 12)
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 5,
                    f'Best: {self.high_score}', '#888888', 11, 'rt')
        
        # Draw grid border
        display.rect(grid_x - 1, grid_y - 1,
                    grid_size + 2, grid_size + 2,
                    color='#333333')
        
        # Draw food
        fx = grid_x + self.food[0] * self.CELL_SIZE
        fy = grid_y + self.food[1] * self.CELL_SIZE
        display.rect(fx + 2, fy + 2, self.CELL_SIZE - 4, self.CELL_SIZE - 4,
                    fill='#ff4444')
        
        # Draw snake
        for i, (x, y) in enumerate(self.snake):
            px = grid_x + x * self.CELL_SIZE
            py = grid_y + y * self.CELL_SIZE
            
            if i == 0:
                # Head
                display.rect(px + 1, py + 1, self.CELL_SIZE - 2, self.CELL_SIZE - 2,
                            fill='#00ff00')
            else:
                # Body (slightly darker)
                display.rect(px + 2, py + 2, self.CELL_SIZE - 4, self.CELL_SIZE - 4,
                            fill='#00cc00')
        
        # Game over overlay
        if self.game_over:
            display.rect(grid_x, grid_y + grid_size // 2 - 25,
                        grid_size, 50, fill='#000000cc')
            display.text(grid_x + grid_size // 2, grid_y + grid_size // 2 - 10,
                        'GAME OVER', '#ff4444', 14, 'mm')
            display.text(grid_x + grid_size // 2, grid_y + grid_size // 2 + 10,
                        'Enter: Retry', '#888888', 11, 'mm')
        
        # Paused overlay
        if self.paused:
            display.rect(grid_x, grid_y + grid_size // 2 - 15,
                        grid_size, 30, fill='#000000cc')
            display.text(grid_x + grid_size // 2, grid_y + grid_size // 2,
                        'PAUSED', '#ffcc00', 14, 'mm')

