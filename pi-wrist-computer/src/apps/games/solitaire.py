"""
Solitaire (Klondike) Game

Classic card solitaire with trackball controls.
"""

from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode
import random


# Card suits and colors
SUITS = ['♠', '♥', '♦', '♣']
SUIT_COLORS = {'♠': '#ffffff', '♥': '#ff4444', '♦': '#ff4444', '♣': '#ffffff'}
RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']


class Card:
    """Playing card."""
    
    def __init__(self, suit: str, rank: str):
        self.suit = suit
        self.rank = rank
        self.face_up = False
    
    @property
    def color(self) -> str:
        return 'red' if self.suit in ['♥', '♦'] else 'black'
    
    @property
    def value(self) -> int:
        return RANKS.index(self.rank)
    
    def __repr__(self):
        return f"{self.rank}{self.suit}"


class SolitaireApp(App):
    """Solitaire game."""
    
    CARD_WIDTH = 26
    CARD_HEIGHT = 32
    CARD_OVERLAP = 10  # Reduced for 240px height
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='solitaire',
            name='Solitaire',
            icon='🃏',
            color='#228b22'
        )
        
        self.tableau = [[] for _ in range(7)]  # 7 columns
        self.foundations = [[] for _ in range(4)]  # 4 suit piles
        self.stock = []  # Draw pile
        self.waste = []  # Drawn cards
        
        self.selected_pile = None
        self.selected_index = None
        
        # Cursor position
        self.cursor_col = 0  # 0-6 for tableau, 7 for stock, 8-11 for foundations
        self.cursor_row = 0
        
        self.moves = 0
        self.won = False
    
    def on_enter(self):
        self._new_game()
    
    def on_exit(self):
        pass
    
    def _new_game(self):
        """Deal a new game."""
        # Create deck
        deck = [Card(suit, rank) for suit in SUITS for rank in RANKS]
        random.shuffle(deck)
        
        # Deal tableau
        self.tableau = [[] for _ in range(7)]
        for col in range(7):
            for row in range(col + 1):
                card = deck.pop()
                if row == col:
                    card.face_up = True
                self.tableau[col].append(card)
        
        # Remaining cards go to stock
        self.stock = deck
        self.waste = []
        
        self.foundations = [[] for _ in range(4)]
        self.selected_pile = None
        self.selected_index = None
        self.cursor_col = 0
        self.cursor_row = 0
        self.moves = 0
        self.won = False
    
    def _draw_from_stock(self):
        """Draw a card from stock."""
        if self.stock:
            card = self.stock.pop()
            card.face_up = True
            self.waste.append(card)
            self.moves += 1
        elif self.waste:
            # Flip waste back to stock
            self.stock = self.waste[::-1]
            for card in self.stock:
                card.face_up = False
            self.waste = []
    
    def _can_place_on_tableau(self, card: Card, pile: list) -> bool:
        """Check if card can be placed on tableau pile."""
        if not pile:
            return card.rank == 'K'
        
        top = pile[-1]
        if not top.face_up:
            return False
        
        # Must be opposite color and one rank lower
        return (card.color != top.color and card.value == top.value - 1)
    
    def _can_place_on_foundation(self, card: Card, pile: list) -> bool:
        """Check if card can be placed on foundation pile."""
        if not pile:
            return card.rank == 'A'
        
        top = pile[-1]
        # Must be same suit and one rank higher
        return (card.suit == top.suit and card.value == top.value + 1)
    
    def _try_move_to_foundation(self, card: Card, source_pile: list) -> bool:
        """Try to move a card to its foundation."""
        for foundation in self.foundations:
            if self._can_place_on_foundation(card, foundation):
                source_pile.remove(card)
                foundation.append(card)
                self.moves += 1
                return True
        return False
    
    def _select_card(self):
        """Select card at cursor or perform action."""
        if self.cursor_col == 7:  # Stock
            self._draw_from_stock()
            return
        
        if self.cursor_col >= 8:  # Foundations (can't select from here)
            return
        
        pile = self.tableau[self.cursor_col]
        if not pile:
            return
        
        # Find card at cursor row
        visible_cards = [c for c in pile if c.face_up]
        if self.cursor_row >= len(visible_cards):
            return
        
        card_idx = len(pile) - len(visible_cards) + self.cursor_row
        
        if self.selected_pile is None:
            # Select this card and all below
            self.selected_pile = self.cursor_col
            self.selected_index = card_idx
        else:
            # Try to move selected cards here
            self._try_move()
    
    def _try_move(self):
        """Try to move selected cards to cursor position."""
        if self.selected_pile is None:
            return
        
        source = self.tableau[self.selected_pile]
        cards_to_move = source[self.selected_index:]
        
        if not cards_to_move:
            self.selected_pile = None
            return
        
        target_col = self.cursor_col
        
        if target_col < 7:  # Move to tableau
            target = self.tableau[target_col]
            if self._can_place_on_tableau(cards_to_move[0], target):
                # Move cards
                target.extend(cards_to_move)
                del source[self.selected_index:]
                
                # Flip top card of source
                if source and not source[-1].face_up:
                    source[-1].face_up = True
                
                self.moves += 1
        
        self.selected_pile = None
        self.selected_index = None
        self._check_win()
    
    def _auto_move_to_foundation(self):
        """Try to auto-move a card to foundation."""
        # Check waste
        if self.waste:
            card = self.waste[-1]
            if self._try_move_to_foundation(card, self.waste):
                self._check_win()
                return True
        
        # Check tableau
        for pile in self.tableau:
            if pile and pile[-1].face_up:
                card = pile[-1]
                for foundation in self.foundations:
                    if self._can_place_on_foundation(card, foundation):
                        pile.remove(card)
                        foundation.append(card)
                        if pile and not pile[-1].face_up:
                            pile[-1].face_up = True
                        self.moves += 1
                        self._check_win()
                        return True
        
        return False
    
    def _check_win(self):
        """Check if all foundations are complete."""
        self.won = all(len(f) == 13 for f in self.foundations)
    
    def on_key(self, event: KeyEvent) -> bool:
        if self.won:
            if event.code == KeyCode.ENTER:
                self._new_game()
            elif event.code == KeyCode.ESC:
                self.ui.go_home()
            return True
        
        if event.code == KeyCode.LEFT:
            self.cursor_col = max(0, self.cursor_col - 1)
            self.cursor_row = 0
            return True
        elif event.code == KeyCode.RIGHT:
            self.cursor_col = min(11, self.cursor_col + 1)
            self.cursor_row = 0
            return True
        elif event.code == KeyCode.UP:
            if self.cursor_col < 7:
                pile = self.tableau[self.cursor_col]
                visible = len([c for c in pile if c.face_up])
                self.cursor_row = max(0, self.cursor_row - 1)
            return True
        elif event.code == KeyCode.DOWN:
            if self.cursor_col < 7:
                pile = self.tableau[self.cursor_col]
                visible = len([c for c in pile if c.face_up])
                self.cursor_row = min(visible - 1, self.cursor_row + 1) if visible else 0
            return True
        elif event.code == KeyCode.ENTER or event.code == KeyCode.SPACE:
            self._select_card()
            return True
        elif event.char == 'f' or event.char == 'F':
            self._auto_move_to_foundation()
            return True
        elif event.char == 'r' or event.char == 'R':
            self._new_game()
            return True
        elif event.code == KeyCode.ESC:
            if self.selected_pile is not None:
                self.selected_pile = None
                self.selected_index = None
            else:
                self.ui.go_home()
            return True
        
        return False
    
    def on_click(self, x: int, y: int) -> bool:
        # TODO: Calculate clicked card from position
        return False
    
    def draw(self, display: Display):
        # Background
        display.rect(0, self.ui.STATUS_BAR_HEIGHT,
                    display.width, display.height - self.ui.STATUS_BAR_HEIGHT,
                    fill='#0a3d0a')
        
        # Header
        display.text(5, self.ui.STATUS_BAR_HEIGHT + 3, 
                    f'Moves: {self.moves}', '#aaffaa', 10)
        
        # Draw stock (top-left area)
        stock_x = 5
        stock_y = self.ui.STATUS_BAR_HEIGHT + 18
        
        # Stock pile
        if self.stock:
            self._draw_card_back(display, stock_x, stock_y)
        else:
            display.rect(stock_x, stock_y, self.CARD_WIDTH, self.CARD_HEIGHT,
                        color='#2a5a2a')
        
        if self.cursor_col == 7:
            display.rect(stock_x - 2, stock_y - 2,
                        self.CARD_WIDTH + 4, self.CARD_HEIGHT + 4,
                        color='#ffff00', width=2)
        
        # Waste pile
        waste_x = stock_x + self.CARD_WIDTH + 5
        if self.waste:
            self._draw_card(display, self.waste[-1], waste_x, stock_y)
        
        # Foundations (top right area)
        for i, foundation in enumerate(self.foundations):
            fx = display.width - 5 - (4 - i) * (self.CARD_WIDTH + 3)
            fy = stock_y
            
            if foundation:
                self._draw_card(display, foundation[-1], fx, fy)
            else:
                display.rect(fx, fy, self.CARD_WIDTH, self.CARD_HEIGHT,
                            color='#2a5a2a')
                display.text(fx + self.CARD_WIDTH // 2, fy + self.CARD_HEIGHT // 2,
                            SUITS[i], '#2a5a2a', 16, 'mm')
            
            if self.cursor_col == 8 + i:
                display.rect(fx - 2, fy - 2,
                            self.CARD_WIDTH + 4, self.CARD_HEIGHT + 4,
                            color='#ffff00', width=2)
        
        # Tableau
        tableau_y = stock_y + self.CARD_HEIGHT + 8
        col_width = (display.width - 10) // 7
        
        for col, pile in enumerate(self.tableau):
            x = 5 + col * col_width
            
            if not pile:
                display.rect(x, tableau_y, self.CARD_WIDTH, self.CARD_HEIGHT,
                            color='#2a5a2a')
            else:
                face_down_count = len([c for c in pile if not c.face_up])
                
                # Draw face-down cards (stacked tightly)
                for i in range(face_down_count):
                    y = tableau_y + i * 3
                    self._draw_card_back(display, x, y)
                
                # Draw face-up cards
                face_up_start = tableau_y + face_down_count * 3
                for i, card in enumerate(c for c in pile if c.face_up):
                    y = face_up_start + i * self.CARD_OVERLAP
                    
                    is_selected = (self.selected_pile == col and 
                                  self.selected_index is not None and
                                  i >= self.selected_index - face_down_count)
                    
                    self._draw_card(display, card, x, y, is_selected)
            
            # Cursor highlight
            if self.cursor_col == col:
                visible_count = len([c for c in pile if c.face_up])
                if visible_count > 0:
                    face_down_count = len(pile) - visible_count
                    cursor_y = (tableau_y + face_down_count * 3 + 
                               self.cursor_row * self.CARD_OVERLAP)
                else:
                    cursor_y = tableau_y
                
                display.rect(x - 2, cursor_y - 2,
                            self.CARD_WIDTH + 4, self.CARD_HEIGHT + 4,
                            color='#ffff00', width=2)
        
        # Win overlay
        if self.won:
            display.rect(20, display.height // 2 - 30,
                        display.width - 40, 60, fill='#000000cc')
            display.text(display.width // 2, display.height // 2 - 10,
                        'YOU WIN! 🎉', '#ffcc00', 18, 'mm')
            display.text(display.width // 2, display.height // 2 + 15,
                        f'Moves: {self.moves}', 'white', 12, 'mm')
        
        # Controls hint
        if not self.won:
            display.text(display.width // 2, display.height - 8,
                        'Enter:Select | F:AutoMove | R:New', '#2a5a2a', 9, 'mm')
    
    def _draw_card(self, display: Display, card: Card, x: int, y: int, 
                   selected: bool = False):
        """Draw a face-up card."""
        # Ensure card is valid
        if not card or not hasattr(card, 'rank') or not hasattr(card, 'suit'):
            return
        
        bg = '#ffff88' if selected else '#ffffff'
        display.rect(x, y, self.CARD_WIDTH, self.CARD_HEIGHT, fill=bg, color='#000000')
        
        color = SUIT_COLORS.get(card.suit, '#000000')
        # Rank and suit - ensure text fits
        rank = str(card.rank) if card.rank else '?'
        suit = card.suit if card.suit else '?'
        text = f"{rank}{suit}"
        # Use larger font and ensure it's visible
        display.text(x + 3, y + 4, text, color, 10)
    
    def _draw_card_back(self, display: Display, x: int, y: int):
        """Draw a face-down card."""
        display.rect(x, y, self.CARD_WIDTH, self.CARD_HEIGHT, 
                    fill='#0044aa', color='#000000')
        # Pattern
        display.rect(x + 3, y + 3, self.CARD_WIDTH - 6, self.CARD_HEIGHT - 6,
                    color='#6688cc')

