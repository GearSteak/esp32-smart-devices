"""
Space Invaders Game
Classic arcade shooter.
"""

import time
import random
from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode


class InvadersApp(App):
    """Space Invaders arcade game."""
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='invaders',
            name='Invaders',
            icon='👾',
            color='#00ff00'
        )
        
        self.player_x = 0
        self.player_width = 20
        self.bullets = []
        self.alien_bullets = []
        self.aliens = []
        self.alien_dir = 1
        self.alien_speed = 1
        self.score = 0
        self.lives = 3
        self.game_over = False
        self.won = False
        self.last_update = 0
        self.last_alien_shot = 0
    
    def on_enter(self):
        self._new_game()
    
    def on_exit(self):
        pass
    
    def _new_game(self):
        """Start a new game."""
        self.player_x = self.ui.display.width // 2 - self.player_width // 2
        self.bullets = []
        self.alien_bullets = []
        self.aliens = []
        self.alien_dir = 1
        self.alien_speed = 1
        self.score = 0
        self.lives = 3
        self.game_over = False
        self.won = False
        
        # Create alien grid
        for row in range(4):
            for col in range(8):
                self.aliens.append({
                    'x': 20 + col * 25,
                    'y': self.ui.STATUS_BAR_HEIGHT + 30 + row * 25,
                    'type': row
                })
    
    def _shoot(self):
        """Player shoots."""
        if len(self.bullets) < 3:
            self.bullets.append({
                'x': self.player_x + self.player_width // 2,
                'y': self.ui.display.height - 35
            })
    
    def _alien_shoot(self):
        """Random alien shoots."""
        if not self.aliens or time.time() - self.last_alien_shot < 1:
            return
        
        if random.random() < 0.02:
            alien = random.choice(self.aliens)
            self.alien_bullets.append({
                'x': alien['x'] + 8,
                'y': alien['y'] + 15
            })
            self.last_alien_shot = time.time()
    
    def on_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        if self.game_over:
            if event.code == KeyCode.ENTER:
                self._new_game()
            return True
        
        if event.code == KeyCode.LEFT:
            self.player_x = max(0, self.player_x - 10)
        elif event.code == KeyCode.RIGHT:
            self.player_x = min(self.ui.display.width - self.player_width, self.player_x + 10)
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
        
        # Move bullets
        self.bullets = [b for b in self.bullets if b['y'] > self.ui.STATUS_BAR_HEIGHT]
        for bullet in self.bullets:
            bullet['y'] -= 8
        
        # Move alien bullets
        self.alien_bullets = [b for b in self.alien_bullets if b['y'] < self.ui.display.height]
        for bullet in self.alien_bullets:
            bullet['y'] += 4
        
        # Move aliens
        move_down = False
        for alien in self.aliens:
            alien['x'] += self.alien_dir * self.alien_speed
            if alien['x'] <= 5 or alien['x'] >= self.ui.display.width - 20:
                move_down = True
        
        if move_down:
            self.alien_dir *= -1
            for alien in self.aliens:
                alien['y'] += 10
                if alien['y'] > self.ui.display.height - 50:
                    self.game_over = True
        
        # Bullet-alien collisions
        for bullet in self.bullets[:]:
            for alien in self.aliens[:]:
                if (alien['x'] < bullet['x'] < alien['x'] + 16 and
                    alien['y'] < bullet['y'] < alien['y'] + 16):
                    self.bullets.remove(bullet)
                    self.aliens.remove(alien)
                    self.score += 10 * (4 - alien['type'])
                    break
        
        # Alien bullet-player collisions
        player_y = self.ui.display.height - 25
        for bullet in self.alien_bullets[:]:
            if (self.player_x < bullet['x'] < self.player_x + self.player_width and
                player_y < bullet['y'] < player_y + 15):
                self.alien_bullets.remove(bullet)
                self.lives -= 1
                if self.lives <= 0:
                    self.game_over = True
        
        # Win check
        if not self.aliens:
            self.won = True
            self.game_over = True
        
        # Alien shooting
        self._alien_shoot()
    
    def draw(self, display: Display):
        self._update()
        
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width,
                    display.height - self.ui.STATUS_BAR_HEIGHT, fill='#000000')
        
        # Score and lives
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 12, f"Score: {self.score}", 'white', 10)
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 12,
                    "❤" * self.lives, '#ff0000', 10, 'rt')
        
        # Aliens
        alien_chars = ['👾', '👽', '🛸', '👻']
        for alien in self.aliens:
            display.text(alien['x'] + 8, alien['y'] + 8, 
                        alien_chars[alien['type']], '#00ff00', 14, 'mm')
        
        # Player
        player_y = display.height - 25
        display.text(self.player_x + self.player_width // 2, player_y + 7, 
                    '🚀', 'white', 16, 'mm')
        
        # Bullets
        for bullet in self.bullets:
            display.rect(int(bullet['x']) - 1, int(bullet['y']), 2, 8, fill='#ffff00')
        
        # Alien bullets
        for bullet in self.alien_bullets:
            display.rect(int(bullet['x']) - 1, int(bullet['y']), 2, 8, fill='#ff0000')
        
        # Game over
        if self.game_over:
            display.rect(40, display.height // 2 - 25, display.width - 80, 50,
                        fill='#000000', outline='white')
            msg = "🎉 VICTORY!" if self.won else "GAME OVER"
            display.text(display.width // 2, display.height // 2 - 5,
                        msg, '#00ff00' if self.won else '#ff0000', 16, 'mm')
            display.text(display.width // 2, display.height // 2 + 15,
                        f"Score: {self.score}", 'white', 12, 'mm')

