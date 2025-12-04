"""
Hangman Game
Guess the word letter by letter.
"""

import random
from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode


WORDS = [
    'python', 'computer', 'keyboard', 'monitor', 'algorithm', 'database',
    'network', 'software', 'hardware', 'internet', 'browser', 'program',
    'variable', 'function', 'compiler', 'developer', 'application',
    'raspberry', 'arduino', 'circuit', 'voltage', 'current', 'resistor',
    'capacitor', 'transistor', 'display', 'sensor', 'bluetooth', 'wireless',
    'elephant', 'giraffe', 'penguin', 'dolphin', 'butterfly', 'mountain',
    'ocean', 'forest', 'desert', 'island', 'volcano', 'rainbow', 'thunder',
    'adventure', 'mystery', 'fantasy', 'science', 'history', 'geography',
]


class HangmanApp(App):
    """Hangman word guessing game."""
    
    MAX_WRONG = 6
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='hangman',
            name='Hangman',
            icon='😵',
            color='#e74c3c'
        )
        
        self.word = ''
        self.guessed = set()
        self.wrong_guesses = 0
        self.game_over = False
        self.won = False
    
    def on_enter(self):
        self._new_game()
    
    def _new_game(self):
        """Start a new game."""
        self.word = random.choice(WORDS).upper()
        self.guessed = set()
        self.wrong_guesses = 0
        self.game_over = False
        self.won = False
    
    def _guess(self, letter: str):
        """Make a guess."""
        letter = letter.upper()
        if letter in self.guessed or not letter.isalpha():
            return
        
        self.guessed.add(letter)
        
        if letter not in self.word:
            self.wrong_guesses += 1
            if self.wrong_guesses >= self.MAX_WRONG:
                self.game_over = True
        else:
            # Check win
            if all(c in self.guessed for c in self.word):
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
        
        if event.char and event.char.isalpha():
            self._guess(event.char)
        
        return True
    
    def _draw_hangman(self, display: Display, x: int, y: int):
        """Draw the hangman figure."""
        # Gallows
        display.rect(x + 10, y + 100, 60, 3, fill='#8b4513')
        display.rect(x + 35, y + 10, 3, 90, fill='#8b4513')
        display.rect(x + 35, y + 10, 40, 3, fill='#8b4513')
        display.rect(x + 70, y + 10, 3, 15, fill='#8b4513')
        
        if self.wrong_guesses >= 1:
            # Head
            display.circle(x + 71, y + 35, 12, color='white', width=2)
        
        if self.wrong_guesses >= 2:
            # Body
            display.rect(x + 70, y + 47, 2, 30, fill='white')
        
        if self.wrong_guesses >= 3:
            # Left arm
            display.rect(x + 55, y + 50, 15, 2, fill='white')
        
        if self.wrong_guesses >= 4:
            # Right arm
            display.rect(x + 72, y + 50, 15, 2, fill='white')
        
        if self.wrong_guesses >= 5:
            # Left leg
            display.rect(x + 60, y + 77, 12, 2, fill='white')
        
        if self.wrong_guesses >= 6:
            # Right leg
            display.rect(x + 72, y + 77, 12, 2, fill='white')
    
    def draw(self, display: Display):
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width,
                    display.height - self.ui.STATUS_BAR_HEIGHT, fill='#1a1a1a')
        
        # Draw hangman
        self._draw_hangman(display, 10, self.ui.STATUS_BAR_HEIGHT + 10)
        
        # Wrong count
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 20,
                    f"{self.wrong_guesses}/{self.MAX_WRONG}", '#ff0000', 12, 'rt')
        
        # Word display
        word_y = self.ui.STATUS_BAR_HEIGHT + 130
        displayed = ''
        for c in self.word:
            if c in self.guessed:
                displayed += c + ' '
            else:
                displayed += '_ '
        
        display.text(display.width // 2, word_y, displayed.strip(), 'white', 18, 'mm')
        
        # Keyboard
        kb_y = word_y + 35
        rows = ['QWERTYUIOP', 'ASDFGHJKL', 'ZXCVBNM']
        
        for row_idx, row in enumerate(rows):
            row_width = len(row) * 20
            start_x = (display.width - row_width) // 2
            
            for i, letter in enumerate(row):
                x = start_x + i * 20
                y = kb_y + row_idx * 22
                
                if letter in self.guessed:
                    if letter in self.word:
                        color = '#00aa00'
                    else:
                        color = '#aa0000'
                else:
                    color = '#444444'
                
                display.rect(x, y, 18, 20, fill=color)
                display.text(x + 9, y + 10, letter, 'white', 10, 'mm')
        
        # Game over
        if self.game_over:
            display.rect(20, display.height // 2 - 30, display.width - 40, 60,
                        fill='#000000', outline='white')
            if self.won:
                display.text(display.width // 2, display.height // 2 - 10,
                            "🎉 YOU WIN!", '#00ff00', 16, 'mm')
            else:
                display.text(display.width // 2, display.height // 2 - 10,
                            "GAME OVER", '#ff0000', 16, 'mm')
                display.text(display.width // 2, display.height // 2 + 10,
                            f"Word: {self.word}", '#888888', 12, 'mm')

