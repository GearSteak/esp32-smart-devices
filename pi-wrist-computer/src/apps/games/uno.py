"""
UNO Card Game
Classic card game against CPU opponents.
"""

import random
from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode


class UnoApp(App):
    """UNO card game."""
    
    COLORS = ['red', 'yellow', 'green', 'blue']
    COLOR_HEX = {'red': '#ff0000', 'yellow': '#ffff00', 'green': '#00aa00', 'blue': '#0066ff', 'wild': '#222222'}
    NUMBERS = list(range(10)) + list(range(1, 10))  # 0 once, 1-9 twice
    SPECIALS = ['skip', 'reverse', '+2']
    WILDS = ['wild', 'wild+4']
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='uno',
            name='UNO',
            icon='🎴',
            color='#ff0000'
        )
        
        self.deck = []
        self.discard = []
        self.player_hand = []
        self.cpu_hands = [[], [], []]  # 3 CPU players
        self.current_player = 0  # 0 = human
        self.direction = 1
        self.current_color = None
        self.selected_card = 0
        self.state = 'playing'  # playing, choose_color, game_over
        self.winner = None
        self.must_draw = 0
        self.message = ""
        self.scroll_offset = 0
    
    def on_enter(self):
        self._new_game()
    
    def _new_game(self):
        """Start a new game."""
        self._create_deck()
        random.shuffle(self.deck)
        
        # Deal 7 cards each
        self.player_hand = [self._draw_card() for _ in range(7)]
        self.cpu_hands = [[self._draw_card() for _ in range(7)] for _ in range(3)]
        
        # Start discard pile
        while True:
            card = self._draw_card()
            if card['type'] == 'number':
                self.discard = [card]
                self.current_color = card['color']
                break
            self.deck.append(card)
            random.shuffle(self.deck)
        
        self.current_player = 0
        self.direction = 1
        self.selected_card = 0
        self.state = 'playing'
        self.winner = None
        self.must_draw = 0
        self.message = ""
        self.scroll_offset = 0
    
    def _create_deck(self):
        """Create a full UNO deck."""
        self.deck = []
        
        for color in self.COLORS:
            # Number cards
            self.deck.append({'type': 'number', 'color': color, 'value': 0})
            for num in range(1, 10):
                self.deck.append({'type': 'number', 'color': color, 'value': num})
                self.deck.append({'type': 'number', 'color': color, 'value': num})
            
            # Special cards (2 each)
            for special in self.SPECIALS:
                self.deck.append({'type': 'special', 'color': color, 'value': special})
                self.deck.append({'type': 'special', 'color': color, 'value': special})
        
        # Wild cards (4 each)
        for _ in range(4):
            self.deck.append({'type': 'wild', 'color': 'wild', 'value': 'wild'})
            self.deck.append({'type': 'wild', 'color': 'wild', 'value': 'wild+4'})
    
    def _draw_card(self):
        """Draw a card from deck."""
        if not self.deck:
            # Reshuffle discard pile
            top = self.discard[-1]
            self.deck = self.discard[:-1]
            self.discard = [top]
            random.shuffle(self.deck)
        return self.deck.pop() if self.deck else None
    
    def _can_play(self, card: dict) -> bool:
        """Check if card can be played."""
        if card['type'] == 'wild':
            return True
        if card['color'] == self.current_color:
            return True
        top = self.discard[-1]
        if card['type'] == 'number' and top['type'] == 'number':
            if card['value'] == top['value']:
                return True
        if card['type'] == 'special' and top['type'] == 'special':
            if card['value'] == top['value']:
                return True
        return False
    
    def _play_card(self, hand: list, card_idx: int) -> bool:
        """Play a card from hand."""
        card = hand[card_idx]
        if not self._can_play(card):
            return False
        
        hand.pop(card_idx)
        self.discard.append(card)
        
        # Handle card effects
        if card['type'] == 'wild':
            if card['value'] == 'wild+4':
                self.must_draw = 4
            if self.current_player == 0:
                self.state = 'choose_color'
                return True
            else:
                self.current_color = random.choice(self.COLORS)
        else:
            self.current_color = card['color']
        
        if card['type'] == 'special':
            if card['value'] == 'skip':
                self._next_player()
            elif card['value'] == 'reverse':
                self.direction *= -1
                if len([h for h in [self.player_hand] + self.cpu_hands if h]) == 2:
                    pass  # In 2 player, reverse acts like skip
            elif card['value'] == '+2':
                self.must_draw = 2
        
        return True
    
    def _next_player(self):
        """Move to next player."""
        self.current_player = (self.current_player + self.direction) % 4
    
    def _cpu_turn(self):
        """CPU plays their turn."""
        hand = self.cpu_hands[self.current_player - 1]
        
        # Must draw?
        if self.must_draw > 0:
            for _ in range(self.must_draw):
                card = self._draw_card()
                if card:
                    hand.append(card)
            self.must_draw = 0
            self._next_player()
            return
        
        # Find playable card
        playable = [(i, c) for i, c in enumerate(hand) if self._can_play(c)]
        
        if playable:
            # Prefer non-wild cards
            non_wild = [(i, c) for i, c in playable if c['type'] != 'wild']
            if non_wild:
                idx, _ = random.choice(non_wild)
            else:
                idx, _ = random.choice(playable)
            
            self._play_card(hand, idx)
            
            # Check win
            if not hand:
                self.winner = f"CPU {self.current_player}"
                self.state = 'game_over'
                return
        else:
            # Draw card
            card = self._draw_card()
            if card:
                hand.append(card)
                if self._can_play(card):
                    self._play_card(hand, len(hand) - 1)
        
        self._next_player()
    
    def on_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        if self.state == 'game_over':
            if event.code == KeyCode.ENTER:
                self._new_game()
            return True
        
        if self.state == 'choose_color':
            color_map = {
                'r': 'red', 'R': 'red',
                'y': 'yellow', 'Y': 'yellow',
                'g': 'green', 'G': 'green',
                'b': 'blue', 'B': 'blue',
            }
            if event.code == KeyCode.LEFT:
                colors = self.COLORS
                idx = colors.index(self.current_color) if self.current_color in colors else 0
                self.current_color = colors[(idx - 1) % 4]
            elif event.code == KeyCode.RIGHT:
                colors = self.COLORS
                idx = colors.index(self.current_color) if self.current_color in colors else 0
                self.current_color = colors[(idx + 1) % 4]
            elif event.char in color_map:
                self.current_color = color_map[event.char]
                self.state = 'playing'
                self._next_player()
            elif event.code == KeyCode.ENTER and self.current_color:
                self.state = 'playing'
                self._next_player()
            return True
        
        if self.current_player != 0:
            # CPU turn
            self._cpu_turn()
            return True
        
        # Player turn
        if self.must_draw > 0:
            if event.code == KeyCode.ENTER:
                for _ in range(self.must_draw):
                    card = self._draw_card()
                    if card:
                        self.player_hand.append(card)
                self.must_draw = 0
                self.message = f"Drew {self.must_draw} cards"
                self._next_player()
            return True
        
        max_visible = 6
        if event.code == KeyCode.LEFT:
            self.selected_card = max(0, self.selected_card - 1)
            if self.selected_card < self.scroll_offset:
                self.scroll_offset = self.selected_card
        elif event.code == KeyCode.RIGHT:
            self.selected_card = min(len(self.player_hand) - 1, self.selected_card + 1)
            if self.selected_card >= self.scroll_offset + max_visible:
                self.scroll_offset = self.selected_card - max_visible + 1
        elif event.code == KeyCode.ENTER:
            if self.player_hand:
                if self._play_card(self.player_hand, self.selected_card):
                    self.selected_card = min(self.selected_card, len(self.player_hand) - 1)
                    self.selected_card = max(0, self.selected_card)
                    self.message = ""
                    
                    if not self.player_hand:
                        self.winner = "You"
                        self.state = 'game_over'
                        return True
                    
                    if self.state == 'playing':
                        self._next_player()
                else:
                    self.message = "Can't play that!"
        elif event.char == 'd' or event.char == 'D':
            # Draw a card
            card = self._draw_card()
            if card:
                self.player_hand.append(card)
                self.message = "Drew a card"
                if not self._can_play(card):
                    self._next_player()
                else:
                    self.selected_card = len(self.player_hand) - 1
                    self.scroll_offset = max(0, self.selected_card - max_visible + 1)
        
        return True
    
    def _draw_card_visual(self, display: Display, x: int, y: int, card: dict, 
                          selected: bool = False, small: bool = False):
        """Draw a card."""
        w = 25 if small else 35
        h = 35 if small else 50
        
        color = self.COLOR_HEX.get(card['color'], '#222222')
        
        if selected:
            display.rect(x - 2, y - 2, w + 4, h + 4, fill='#ffffff')
        
        display.rect(x, y, w, h, fill=color, outline='white')
        
        # Card content
        if card['type'] == 'number':
            text = str(card['value'])
        elif card['type'] == 'special':
            symbols = {'skip': '⊘', 'reverse': '⟲', '+2': '+2'}
            text = symbols.get(card['value'], '?')
        else:
            text = 'W' if card['value'] == 'wild' else '+4'
        
        size = 10 if small else 14
        display.text(x + w // 2, y + h // 2, text, 'white', size, 'mm')
    
    def draw(self, display: Display):
        # Process CPU turns
        while self.current_player != 0 and self.state == 'playing':
            self._cpu_turn()
        
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width,
                    display.height - self.ui.STATUS_BAR_HEIGHT, fill='#1a5f1a')
        
        # CPU hands (show card counts)
        cpu_y = self.ui.STATUS_BAR_HEIGHT + 15
        for i, hand in enumerate(self.cpu_hands):
            x = 20 + i * 75
            active = (self.current_player == i + 1)
            display.text(x, cpu_y, f"CPU{i+1}", '#ffff00' if active else '#888888', 10)
            display.text(x, cpu_y + 15, f"🎴×{len(hand)}", 'white', 10)
        
        # Discard pile
        if self.discard:
            self._draw_card_visual(display, display.width // 2 - 20, 
                                   self.ui.STATUS_BAR_HEIGHT + 55, self.discard[-1])
        
        # Current color indicator
        display.text(display.width // 2 + 30, self.ui.STATUS_BAR_HEIGHT + 75,
                    "●", self.COLOR_HEX.get(self.current_color, '#888888'), 20)
        
        # Player's hand
        hand_y = display.height - 70
        display.text(10, hand_y - 15, "Your hand:", '#888888', 10)
        
        max_visible = 6
        card_width = 38
        
        # Scroll indicators
        if self.scroll_offset > 0:
            display.text(5, hand_y + 20, "◀", '#ffff00', 12)
        if self.scroll_offset + max_visible < len(self.player_hand):
            display.text(display.width - 10, hand_y + 20, "▶", '#ffff00', 12)
        
        for i in range(max_visible):
            card_idx = self.scroll_offset + i
            if card_idx >= len(self.player_hand):
                break
            
            card = self.player_hand[card_idx]
            x = 15 + i * card_width
            selected = (card_idx == self.selected_card)
            
            self._draw_card_visual(display, x, hand_y, card, selected)
        
        # Message
        if self.message:
            display.text(display.width // 2, display.height - 15,
                        self.message, '#ffff00', 10, 'mm')
        else:
            display.text(display.width // 2, display.height - 15,
                        "←→:Select ⏎:Play D:Draw", '#888888', 9, 'mm')
        
        # Choose color overlay
        if self.state == 'choose_color':
            display.rect(30, display.height // 2 - 40, display.width - 60, 80,
                        fill='#000000', outline='white')
            display.text(display.width // 2, display.height // 2 - 25,
                        "Choose Color:", 'white', 14, 'mm')
            
            for i, color in enumerate(self.COLORS):
                x = 50 + i * 45
                selected = (color == self.current_color)
                display.rect(x, display.height // 2 - 5, 35, 30,
                           fill=self.COLOR_HEX[color],
                           outline='white' if selected else None)
                display.text(x + 17, display.height // 2 + 10,
                           color[0].upper(), 'white', 12, 'mm')
        
        # Game over
        if self.state == 'game_over':
            display.rect(30, display.height // 2 - 30, display.width - 60, 60,
                        fill='#000000', outline='white')
            if self.winner == "You":
                display.text(display.width // 2, display.height // 2 - 10,
                            "🎉 UNO! YOU WIN!", '#00ff00', 16, 'mm')
            else:
                display.text(display.width // 2, display.height // 2 - 10,
                            f"{self.winner} wins!", '#ff0000', 16, 'mm')
            display.text(display.width // 2, display.height // 2 + 15,
                        "ENTER to play again", '#888888', 10, 'mm')

