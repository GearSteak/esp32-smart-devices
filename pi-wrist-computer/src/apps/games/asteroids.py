"""
Asteroids Game
Classic space shooter with rotation.
"""

import time
import math
import random
from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode


class AsteroidsApp(App):
    """Asteroids arcade game."""
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='asteroids',
            name='Asteroids',
            icon='☄️',
            color='#888888'
        )
        
        self.ship_x = 0
        self.ship_y = 0
        self.ship_angle = 0
        self.ship_vx = 0
        self.ship_vy = 0
        self.bullets = []
        self.asteroids = []
        self.score = 0
        self.lives = 3
        self.game_over = False
        self.last_update = 0
        self.thrusting = False
    
    def on_enter(self):
        self._new_game()
    
    def _new_game(self):
        """Start a new game."""
        self.ship_x = self.ui.display.width // 2
        self.ship_y = self.ui.display.height // 2
        self.ship_angle = -90
        self.ship_vx = 0
        self.ship_vy = 0
        self.bullets = []
        self.asteroids = []
        self.score = 0
        self.lives = 3
        self.game_over = False
        self.thrusting = False
        
        # Spawn asteroids
        for _ in range(5):
            self._spawn_asteroid(3)
    
    def _spawn_asteroid(self, size: int, x: float = None, y: float = None):
        """Spawn an asteroid."""
        if x is None:
            x = random.randint(0, self.ui.display.width)
        if y is None:
            y = random.randint(self.ui.STATUS_BAR_HEIGHT, self.ui.display.height)
        
        angle = random.uniform(0, 360)
        speed = random.uniform(0.5, 2) / size
        
        self.asteroids.append({
            'x': x, 'y': y,
            'vx': math.cos(math.radians(angle)) * speed,
            'vy': math.sin(math.radians(angle)) * speed,
            'size': size,
            'radius': size * 8
        })
    
    def _shoot(self):
        """Fire a bullet."""
        if len(self.bullets) < 5:
            angle = math.radians(self.ship_angle)
            self.bullets.append({
                'x': self.ship_x,
                'y': self.ship_y,
                'vx': math.cos(angle) * 8,
                'vy': math.sin(angle) * 8,
                'life': 30
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
            self.ship_angle -= 15
        elif event.code == KeyCode.RIGHT:
            self.ship_angle += 15
        elif event.code == KeyCode.UP:
            self.thrusting = True
        elif event.code == KeyCode.ENTER or event.char == ' ':
            self._shoot()
        
        return True
    
    def _update(self):
        """Update game state."""
        if self.game_over:
            return
        
        now = time.time()
        if now - self.last_update < 0.03:
            return
        self.last_update = now
        
        # Ship thrust
        if self.thrusting:
            angle = math.radians(self.ship_angle)
            self.ship_vx += math.cos(angle) * 0.3
            self.ship_vy += math.sin(angle) * 0.3
            self.thrusting = False
        
        # Ship friction
        self.ship_vx *= 0.98
        self.ship_vy *= 0.98
        
        # Ship movement with wrap
        self.ship_x = (self.ship_x + self.ship_vx) % self.ui.display.width
        self.ship_y = (self.ship_y + self.ship_vy - self.ui.STATUS_BAR_HEIGHT) % \
                      (self.ui.display.height - self.ui.STATUS_BAR_HEIGHT) + self.ui.STATUS_BAR_HEIGHT
        
        # Bullets
        for bullet in self.bullets[:]:
            bullet['x'] += bullet['vx']
            bullet['y'] += bullet['vy']
            bullet['life'] -= 1
            
            if bullet['life'] <= 0:
                self.bullets.remove(bullet)
                continue
            
            # Wrap
            bullet['x'] %= self.ui.display.width
            bullet['y'] = (bullet['y'] - self.ui.STATUS_BAR_HEIGHT) % \
                         (self.ui.display.height - self.ui.STATUS_BAR_HEIGHT) + self.ui.STATUS_BAR_HEIGHT
        
        # Asteroids
        for ast in self.asteroids:
            ast['x'] = (ast['x'] + ast['vx']) % self.ui.display.width
            ast['y'] = (ast['y'] + ast['vy'] - self.ui.STATUS_BAR_HEIGHT) % \
                      (self.ui.display.height - self.ui.STATUS_BAR_HEIGHT) + self.ui.STATUS_BAR_HEIGHT
        
        # Bullet-asteroid collision
        for bullet in self.bullets[:]:
            for ast in self.asteroids[:]:
                dx = bullet['x'] - ast['x']
                dy = bullet['y'] - ast['y']
                if dx * dx + dy * dy < ast['radius'] * ast['radius']:
                    if bullet in self.bullets:
                        self.bullets.remove(bullet)
                    self.asteroids.remove(ast)
                    self.score += 100 * ast['size']
                    
                    # Split asteroid
                    if ast['size'] > 1:
                        self._spawn_asteroid(ast['size'] - 1, ast['x'], ast['y'])
                        self._spawn_asteroid(ast['size'] - 1, ast['x'], ast['y'])
                    break
        
        # Ship-asteroid collision
        for ast in self.asteroids:
            dx = self.ship_x - ast['x']
            dy = self.ship_y - ast['y']
            if dx * dx + dy * dy < (ast['radius'] + 8) ** 2:
                self.lives -= 1
                self.ship_x = self.ui.display.width // 2
                self.ship_y = self.ui.display.height // 2
                self.ship_vx = 0
                self.ship_vy = 0
                if self.lives <= 0:
                    self.game_over = True
                break
        
        # Level complete
        if not self.asteroids:
            for _ in range(5):
                self._spawn_asteroid(3)
    
    def draw(self, display: Display):
        self._update()
        
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width,
                    display.height - self.ui.STATUS_BAR_HEIGHT, fill='#000000')
        
        # HUD
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 12, f"{self.score}", 'white', 12)
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 12,
                    "▲" * self.lives, '#00ff00', 12, 'rt')
        
        # Asteroids
        for ast in self.asteroids:
            display.circle(int(ast['x']), int(ast['y']), int(ast['radius']), 
                          color='#888888', width=2)
        
        # Ship (triangle)
        angle = math.radians(self.ship_angle)
        # Draw as text for simplicity
        display.text(int(self.ship_x), int(self.ship_y), '▲', '#00ff00', 16, 'mm')
        
        # Bullets
        for bullet in self.bullets:
            display.circle(int(bullet['x']), int(bullet['y']), 2, fill='#ffffff')
        
        # Game over
        if self.game_over:
            display.rect(40, display.height // 2 - 25, display.width - 80, 50,
                        fill='#000000', outline='white')
            display.text(display.width // 2, display.height // 2 - 5,
                        "GAME OVER", '#ff0000', 16, 'mm')
            display.text(display.width // 2, display.height // 2 + 15,
                        f"Score: {self.score}", 'white', 12, 'mm')

