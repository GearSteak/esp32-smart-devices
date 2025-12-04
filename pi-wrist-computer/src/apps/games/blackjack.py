"""
Blackjack Game
Classic 21 card game against dealer.
"""

import random
from ...ui.framework import App, AppInfo
from ...ui.display import Display
from ...input.cardkb import KeyEvent, KeyCode


class BlackjackApp(App):
    """Blackjack card game."""
    
    SUITS = ['♠', '♥', '♦', '♣']
    RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='blackjack',
            name='Blackjack',
            icon='🃏',
            color='#27ae60'
        )
        
        self.deck = []
        self.player_hand = []
        self.dealer_hand = []
        self.chips = 100
        self.bet = 10
        self.state = 'betting'  # betting, playing, dealer, result
        self.result = ''
    
    def on_enter(self):
        self._new_round()
    
    def _new_round(self):
        """Start a new round."""
        self.deck = [(r, s) for r in self.RANKS for s in self.SUITS]
        random.shuffle(self.deck)
        self.player_hand = []
        self.dealer_hand = []
        self.state = 'betting'
        self.result = ''
    
    def _deal(self):
        """Deal initial cards."""
        self.player_hand = [self._draw(), self._draw()]
        self.dealer_hand = [self._draw(), self._draw()]
        self.state = 'playing'
        
        if self._hand_value(self.player_hand) == 21:
            self._stand()
    
    def _draw(self):
        """Draw a card from deck."""
        return self.deck.pop() if self.deck else ('A', '♠')
    
    def _card_value(self, rank: str) -> int:
        """Get value of a card."""
        if rank in ['J', 'Q', 'K']:
            return 10
        elif rank == 'A':
            return 11
        return int(rank)
    
    def _hand_value(self, hand: list) -> int:
        """Calculate hand value, handling aces."""
        value = sum(self._card_value(r) for r, s in hand)
        aces = sum(1 for r, s in hand if r == 'A')
        
        while value > 21 and aces:
            value -= 10
            aces -= 1
        
        return value
    
    def _hit(self):
        """Player takes a card."""
        self.player_hand.append(self._draw())
        if self._hand_value(self.player_hand) > 21:
            self._end_round('bust')
    
    def _stand(self):
        """Player stands, dealer plays."""
        self.state = 'dealer'
        
        while self._hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(self._draw())
        
        player_val = self._hand_value(self.player_hand)
        dealer_val = self._hand_value(self.dealer_hand)
        
        if dealer_val > 21:
            self._end_round('dealer_bust')
        elif player_val > dealer_val:
            self._end_round('win')
        elif dealer_val > player_val:
            self._end_round('lose')
        else:
            self._end_round('push')
    
    def _end_round(self, result: str):
        """End the round."""
        self.state = 'result'
        self.result = result
        
        if result == 'win' or result == 'dealer_bust':
            self.chips += self.bet
        elif result == 'lose' or result == 'bust':
            self.chips -= self.bet
        # push = tie, no change
    
    def on_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        
        if self.state == 'betting':
            if event.code == KeyCode.UP:
                self.bet = min(self.chips, self.bet + 5)
            elif event.code == KeyCode.DOWN:
                self.bet = max(5, self.bet - 5)
            elif event.code == KeyCode.ENTER:
                if self.chips >= self.bet:
                    self._deal()
        
        elif self.state == 'playing':
            if event.char == 'h' or event.char == 'H' or event.code == KeyCode.LEFT:
                self._hit()
            elif event.char == 's' or event.char == 'S' or event.code == KeyCode.RIGHT:
                self._stand()
        
        elif self.state == 'result':
            if event.code == KeyCode.ENTER:
                if self.chips <= 0:
                    self.chips = 100  # Reset
                self._new_round()
        
        return True
    
    def _draw_card(self, display: Display, x: int, y: int, card: tuple, hidden: bool = False):
        """Draw a card."""
        width, height = 35, 50
        
        if hidden:
            display.rect(x, y, width, height, fill='#0066aa', outline='white')
            display.text(x + width // 2, y + height // 2, "?", 'white', 20, 'mm')
        else:
            rank, suit = card
            display.rect(x, y, width, height, fill='white', outline='#888888')
            color = '#ff0000' if suit in ['♥', '♦'] else '#000000'
            display.text(x + width // 2, y + 15, rank, color, 14, 'mm')
            display.text(x + width // 2, y + 35, suit, color, 16, 'mm')
    
    def draw(self, display: Display):
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width,
                    display.height - self.ui.STATUS_BAR_HEIGHT, fill='#0d5c0d')
        
        # Chips and bet
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 15, f"💰 ${self.chips}", '#ffff00', 12)
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 15, 
                    f"Bet: ${self.bet}", 'white', 12, 'rt')
        
        if self.state == 'betting':
            display.text(display.width // 2, display.height // 2 - 20,
                        "Place Your Bet", 'white', 18, 'mm')
            display.text(display.width // 2, display.height // 2 + 10,
                        f"${self.bet}", '#ffff00', 24, 'mm')
            display.text(display.width // 2, display.height // 2 + 45,
                        "↑↓ to change, ENTER to deal", '#888888', 10, 'mm')
        else:
            # Dealer's hand
            display.text(10, self.ui.STATUS_BAR_HEIGHT + 35, "Dealer:", '#888888', 10)
            for i, card in enumerate(self.dealer_hand):
                hidden = (i == 1 and self.state == 'playing')
                self._draw_card(display, 10 + i * 40, self.ui.STATUS_BAR_HEIGHT + 50, card, hidden)
            
            if self.state != 'playing':
                val = self._hand_value(self.dealer_hand)
                display.text(180, self.ui.STATUS_BAR_HEIGHT + 70, str(val), 'white', 14)
            
            # Player's hand
            display.text(10, self.ui.STATUS_BAR_HEIGHT + 120, "You:", '#888888', 10)
            for i, card in enumerate(self.player_hand):
                self._draw_card(display, 10 + i * 40, self.ui.STATUS_BAR_HEIGHT + 135, card)
            
            val = self._hand_value(self.player_hand)
            display.text(180, self.ui.STATUS_BAR_HEIGHT + 155, str(val), 
                        '#ff0000' if val > 21 else 'white', 14)
            
            # Controls or result
            if self.state == 'playing':
                display.text(display.width // 2, display.height - 30,
                            "[H]it  [S]tand", 'white', 14, 'mm')
            elif self.state == 'result':
                msgs = {
                    'win': ('YOU WIN! 🎉', '#00ff00'),
                    'lose': ('You Lose', '#ff0000'),
                    'bust': ('BUST! 💥', '#ff0000'),
                    'dealer_bust': ('Dealer Busts! 🎉', '#00ff00'),
                    'push': ('Push (Tie)', '#ffff00'),
                }
                msg, color = msgs.get(self.result, ('', 'white'))
                display.text(display.width // 2, display.height - 45, msg, color, 16, 'mm')
                display.text(display.width // 2, display.height - 20,
                            "ENTER for next round", '#888888', 10, 'mm')

