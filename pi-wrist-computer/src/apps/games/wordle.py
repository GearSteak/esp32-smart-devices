"""
Wordle Game
Word guessing game with 6 attempts.
"""

import random
from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode


# Common 5-letter words
WORDS = [
    'about', 'above', 'abuse', 'actor', 'acute', 'admit', 'adopt', 'adult', 'after', 'again',
    'agent', 'agree', 'ahead', 'alarm', 'album', 'alert', 'alien', 'align', 'alike', 'alive',
    'allow', 'alone', 'along', 'alter', 'among', 'angel', 'anger', 'angle', 'angry', 'apart',
    'apple', 'apply', 'arena', 'argue', 'arise', 'armor', 'array', 'arrow', 'aside', 'asset',
    'avoid', 'award', 'aware', 'awful', 'badge', 'basic', 'basis', 'beach', 'beast', 'began',
    'begin', 'being', 'below', 'bench', 'berry', 'birth', 'black', 'blade', 'blame', 'blank',
    'blast', 'blaze', 'bleed', 'blend', 'bless', 'blind', 'block', 'blood', 'board', 'bonus',
    'boost', 'booth', 'bound', 'brain', 'brand', 'brass', 'brave', 'bread', 'break', 'breed',
    'brick', 'bride', 'brief', 'bring', 'broad', 'broke', 'brown', 'brush', 'build', 'bunch',
    'burst', 'buyer', 'cabin', 'cable', 'camel', 'canal', 'candy', 'cargo', 'carry', 'carve',
    'catch', 'cause', 'chain', 'chair', 'chaos', 'charm', 'chart', 'chase', 'cheap', 'check',
    'chess', 'chest', 'chief', 'child', 'china', 'chose', 'chunk', 'claim', 'class', 'clean',
    'clear', 'climb', 'clock', 'close', 'cloth', 'cloud', 'coach', 'coast', 'coral', 'count',
    'court', 'cover', 'crack', 'craft', 'crash', 'crazy', 'cream', 'creek', 'crime', 'crisp',
    'cross', 'crowd', 'crown', 'crude', 'crush', 'curve', 'cycle', 'daily', 'dairy', 'dance',
    'death', 'debug', 'delay', 'delta', 'dense', 'depot', 'depth', 'diary', 'dirty', 'disco',
    'ditch', 'doubt', 'draft', 'drain', 'drama', 'drank', 'drawn', 'dream', 'dress', 'dried',
    'drift', 'drill', 'drink', 'drive', 'drown', 'dying', 'eager', 'early', 'earth', 'eight',
    'elbow', 'elder', 'elect', 'elite', 'empty', 'enemy', 'enjoy', 'enter', 'entry', 'equal',
    'error', 'essay', 'event', 'every', 'exact', 'exist', 'extra', 'faint', 'fairy', 'faith',
    'false', 'fancy', 'fatal', 'fault', 'favor', 'feast', 'fence', 'fetus', 'fever', 'fewer',
    'fiber', 'field', 'fifth', 'fifty', 'fight', 'final', 'first', 'fixed', 'flame', 'flash',
    'fleet', 'flesh', 'float', 'flood', 'floor', 'flour', 'fluid', 'flush', 'focus', 'force',
    'forge', 'forth', 'forum', 'found', 'frame', 'frank', 'fraud', 'fresh', 'front', 'frost',
    'fruit', 'fully', 'giant', 'given', 'glass', 'globe', 'glory', 'grace', 'grade', 'grain',
    'grand', 'grant', 'grape', 'grasp', 'grass', 'grave', 'great', 'green', 'greet', 'grief',
    'grill', 'gross', 'group', 'grove', 'grown', 'guard', 'guess', 'guest', 'guide', 'guild',
    'habit', 'happy', 'harsh', 'heart', 'heath', 'heavy', 'hello', 'hence', 'hobby', 'honey',
    'honor', 'horse', 'hotel', 'house', 'human', 'humor', 'ideal', 'image', 'imply', 'index',
    'inner', 'input', 'intro', 'issue', 'japan', 'joint', 'judge', 'juice', 'knife', 'knock',
    'known', 'label', 'labor', 'large', 'laser', 'later', 'laugh', 'layer', 'learn', 'lease',
    'least', 'leave', 'legal', 'lemon', 'level', 'light', 'limit', 'linen', 'liver', 'lobby',
    'local', 'lodge', 'logic', 'loose', 'lorry', 'total', 'touch', 'tough', 'tower', 'track',
    'trade', 'train', 'trash', 'treat', 'trend', 'trial', 'tribe', 'trick', 'truck', 'truly',
    'trunk', 'trust', 'truth', 'twice', 'twist', 'ultra', 'uncle', 'under', 'union', 'unity',
    'until', 'upper', 'upset', 'urban', 'usual', 'valid', 'value', 'video', 'virus', 'visit',
    'vital', 'vivid', 'vocal', 'voice', 'waste', 'watch', 'water', 'weigh', 'weird', 'whale',
    'wheat', 'wheel', 'where', 'which', 'while', 'white', 'whole', 'whose', 'woman', 'world',
    'worry', 'worse', 'worst', 'worth', 'would', 'wound', 'write', 'wrong', 'wrote', 'yield',
    'young', 'youth', 'zebra', 'piano', 'pizza', 'quiet', 'queen', 'quest', 'quick', 'quote',
]


class WordleApp(App):
    """Wordle word guessing game."""
    
    MAX_GUESSES = 6
    WORD_LENGTH = 5
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='wordle',
            name='Wordle',
            icon='📝',
            color='#6aaa64'
        )
        
        self.target_word = ''
        self.guesses = []
        self.current_guess = ''
        self.game_over = False
        self.won = False
        self.message = ''
        self.used_letters = {}  # letter -> 'correct', 'present', 'absent'
    
    def on_enter(self):
        self._new_game()
    
    def on_exit(self):
        pass
    
    def _new_game(self):
        """Start a new game."""
        self.target_word = random.choice(WORDS).upper()
        self.guesses = []
        self.current_guess = ''
        self.game_over = False
        self.won = False
        self.message = ''
        self.used_letters = {}
    
    def _check_guess(self):
        """Check the current guess."""
        if len(self.current_guess) != self.WORD_LENGTH:
            self.message = "Not enough letters"
            return
        
        guess = self.current_guess.upper()
        
        # Check if it's a valid word (or just accept it for simplicity)
        if guess.lower() not in WORDS and len(guess) == 5:
            # Accept any 5-letter combo for flexibility
            pass
        
        result = []
        target_chars = list(self.target_word)
        
        # First pass: check correct positions
        for i, char in enumerate(guess):
            if char == self.target_word[i]:
                result.append('correct')
                target_chars[i] = None
                self.used_letters[char] = 'correct'
            else:
                result.append(None)
        
        # Second pass: check present letters
        for i, char in enumerate(guess):
            if result[i] is None:
                if char in target_chars:
                    result[i] = 'present'
                    target_chars[target_chars.index(char)] = None
                    if self.used_letters.get(char) != 'correct':
                        self.used_letters[char] = 'present'
                else:
                    result[i] = 'absent'
                    if char not in self.used_letters:
                        self.used_letters[char] = 'absent'
        
        self.guesses.append((guess, result))
        self.current_guess = ''
        self.message = ''
        
        if guess == self.target_word:
            self.won = True
            self.game_over = True
            self.message = ["Genius!", "Magnificent!", "Impressive!", "Splendid!", "Great!", "Phew!"][len(self.guesses) - 1]
        elif len(self.guesses) >= self.MAX_GUESSES:
            self.game_over = True
            self.message = f"The word was: {self.target_word}"
    
    def on_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        if self.game_over:
            if event.code == KeyCode.ENTER:
                self._new_game()
            return True
        
        if event.code == KeyCode.ENTER:
            self._check_guess()
        elif event.code == KeyCode.BACKSPACE:
            if self.current_guess:
                self.current_guess = self.current_guess[:-1]
                self.message = ''
        elif event.char and event.char.isalpha() and len(self.current_guess) < self.WORD_LENGTH:
            self.current_guess += event.char.upper()
            self.message = ''
        
        return True
    
    def draw(self, display: Display):
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width,
                    display.height - self.ui.STATUS_BAR_HEIGHT, fill='#121213')
        
        # Title
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 12, 
                    "WORDLE", 'white', 14, 'mm')
        
        # Grid
        cell_size = 32
        gap = 4
        grid_width = self.WORD_LENGTH * (cell_size + gap) - gap
        grid_x = (display.width - grid_width) // 2
        grid_y = self.ui.STATUS_BAR_HEIGHT + 30
        
        colors = {
            'correct': '#538d4e',
            'present': '#b59f3b', 
            'absent': '#3a3a3c',
            'empty': '#121213',
            'tbd': '#3a3a3c'
        }
        
        for row in range(self.MAX_GUESSES):
            for col in range(self.WORD_LENGTH):
                x = grid_x + col * (cell_size + gap)
                y = grid_y + row * (cell_size + gap)
                
                if row < len(self.guesses):
                    letter, results = self.guesses[row][0][col], self.guesses[row][1][col]
                    color = colors[results]
                    display.rect(x, y, cell_size, cell_size, fill=color)
                    display.text(x + cell_size // 2, y + cell_size // 2, letter, 'white', 18, 'mm')
                elif row == len(self.guesses):
                    # Current guess row
                    if col < len(self.current_guess):
                        display.rect(x, y, cell_size, cell_size, fill='#3a3a3c', outline='#565758')
                        display.text(x + cell_size // 2, y + cell_size // 2, 
                                   self.current_guess[col], 'white', 18, 'mm')
                    else:
                        display.rect(x, y, cell_size, cell_size, outline='#3a3a3c')
                else:
                    display.rect(x, y, cell_size, cell_size, outline='#3a3a3c')
        
        # Keyboard
        kb_y = grid_y + self.MAX_GUESSES * (cell_size + gap) + 15
        rows = ['QWERTYUIOP', 'ASDFGHJKL', 'ZXCVBNM']
        
        for row_idx, row in enumerate(rows):
            row_width = len(row) * 20
            start_x = (display.width - row_width) // 2
            
            for i, letter in enumerate(row):
                x = start_x + i * 20
                y = kb_y + row_idx * 25
                
                status = self.used_letters.get(letter, 'empty')
                color = colors.get(status, '#818384')
                
                display.rect(x, y, 18, 22, fill=color)
                display.text(x + 9, y + 11, letter, 'white', 10, 'mm')
        
        # Message
        if self.message:
            display.text(display.width // 2, display.height - 25,
                        self.message, '#ffffff' if self.won else '#888888', 12, 'mm')
        
        # Game over hint
        if self.game_over:
            display.text(display.width // 2, display.height - 10,
                        "Press ENTER to play again", '#666666', 9, 'mm')

