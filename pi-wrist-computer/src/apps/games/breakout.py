"""
Breakout Game
Classic brick-breaking game.
"""

import time
import random
import math
from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode


class BreakoutApp(App):
    """Breakout brick-breaking game."""
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='breakout',
            name='Breakout',
            icon='🧱',
            color='#ff6b6b'
        )
        
        self.paddle_width = 50
        self.paddle_height = 8
        self.ball_size = 6
        self.brick_rows = 5
        self.brick_cols = 10
        self.brick_height = 12
        
        self.paddle_x = 0
        self.ball_x = 0
        self.ball_y = 0
        self.ball_dx = 0
        self.ball_dy = 0
        self.bricks = []
        self.score = 0
        self.lives = 3
        self.game_over = False
        self.won = False
        self.last_update = 0
    
    def on_enter(self):
        self._new_game()
    
    def on_exit(self):
        pass
    
    def _new_game(self):
        """Start a new game."""
        self.paddle_x = (self.ui.display.width - self.paddle_width) // 2
        self._reset_ball()
        self._create_bricks()
        self.score = 0
        self.lives = 3
        self.game_over = False
        self.won = False
    
    def _reset_ball(self):
        """Reset ball position."""
        self.ball_x = self.ui.display.width // 2
        self.ball_y = self.ui.display.height - 60
        angle = random.uniform(-0.5, 0.5)
        speed = 5
        self.ball_dx = math.sin(angle) * speed
        self.ball_dy = -math.cos(angle) * speed
    
    def _create_bricks(self):
        """Create brick grid."""
        self.bricks = []
        brick_width = (self.ui.display.width - 20) // self.brick_cols
        colors = ['#ff0000', '#ff8800', '#ffff00', '#00ff00', '#0088ff']
        
        for row in range(self.brick_rows):
            for col in range(self.brick_cols):
                self.bricks.append({
                    'x': 10 + col * brick_width,
                    'y': self.ui.STATUS_BAR_HEIGHT + 30 + row * self.brick_height,
                    'width': brick_width - 2,
                    'height': self.brick_height - 2,
                    'color': colors[row % len(colors)],
                    'points': (self.brick_rows - row) * 10
                })
    
    def on_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        if self.game_over:
            if event.code == KeyCode.ENTER:
                self._new_game()
            return True
        
        if event.code == KeyCode.LEFT:
            self.paddle_x = max(0, self.paddle_x - 15)
        elif event.code == KeyCode.RIGHT:
            self.paddle_x = min(self.ui.display.width - self.paddle_width, self.paddle_x + 15)
        elif event.char == 'n' or event.char == 'N':
            self._new_game()
        
        return True
    
    def _update(self):
        """Update game state."""
        if self.game_over:
            return
        
        now = time.time()
        if now - self.last_update < 0.02:
            return
        self.last_update = now
        
        # Move ball
        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy
        
        # Wall collisions
        if self.ball_x <= 0 or self.ball_x >= self.ui.display.width - self.ball_size:
            self.ball_dx = -self.ball_dx
            self.ball_x = max(0, min(self.ui.display.width - self.ball_size, self.ball_x))
        
        if self.ball_y <= self.ui.STATUS_BAR_HEIGHT:
            self.ball_dy = -self.ball_dy
            self.ball_y = self.ui.STATUS_BAR_HEIGHT
        
        # Paddle collision
        paddle_y = self.ui.display.height - 30
        if (self.ball_y + self.ball_size >= paddle_y and
            self.ball_y < paddle_y + self.paddle_height and
            self.paddle_x <= self.ball_x + self.ball_size // 2 <= self.paddle_x + self.paddle_width):
            
            # Calculate bounce angle based on hit position
            hit_pos = (self.ball_x + self.ball_size // 2 - self.paddle_x) / self.paddle_width
            angle = (hit_pos - 0.5) * 1.2
            speed = math.sqrt(self.ball_dx ** 2 + self.ball_dy ** 2) * 1.01
            self.ball_dx = math.sin(angle) * speed
            self.ball_dy = -abs(math.cos(angle) * speed)
            self.ball_y = paddle_y - self.ball_size
        
        # Ball out of bounds
        if self.ball_y >= self.ui.display.height:
            self.lives -= 1
            if self.lives <= 0:
                self.game_over = True
            else:
                self._reset_ball()
        
        # Brick collisions
        for brick in self.bricks[:]:
            if (brick['x'] <= self.ball_x + self.ball_size and
                self.ball_x <= brick['x'] + brick['width'] and
                brick['y'] <= self.ball_y + self.ball_size and
                self.ball_y <= brick['y'] + brick['height']):
                
                self.bricks.remove(brick)
                self.score += brick['points']
                self.ball_dy = -self.ball_dy
                
                if not self.bricks:
                    self.won = True
                    self.game_over = True
                break
    
    def draw(self, display: Display):
        self._update()
        
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width,
                    display.height - self.ui.STATUS_BAR_HEIGHT, fill='#1a1a1a')
        
        # Score and lives
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 12, f"Score: {self.score}", 'white', 12)
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 12,
                    "❤" * self.lives, '#ff0000', 12, 'rt')
        
        # Bricks
        for brick in self.bricks:
            display.rect(brick['x'], brick['y'], brick['width'], brick['height'],
                        fill=brick['color'])
        
        # Paddle
        paddle_y = display.height - 30
        display.rect(self.paddle_x, paddle_y, self.paddle_width, self.paddle_height, fill='white')
        
        # Ball
        display.rect(int(self.ball_x), int(self.ball_y), self.ball_size, self.ball_size, fill='#ffff00')
        
        # Game over
        if self.game_over:
            display.rect(40, display.height // 2 - 25, display.width - 80, 50,
                        fill='#000000', outline='white')
            msg = "🎉 YOU WIN!" if self.won else "GAME OVER"
            display.text(display.width // 2, display.height // 2 - 5,
                        msg, '#00ff00' if self.won else '#ff0000', 16, 'mm')
            display.text(display.width // 2, display.height // 2 + 15,
                        f"Score: {self.score}", 'white', 12, 'mm')

