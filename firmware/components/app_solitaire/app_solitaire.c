/**
 * @file app_solitaire.c
 * @brief Klondike Solitaire Game Implementation
 */

#include "app_solitaire.h"
#include "ui.h"
#include "display.h"
#include "sprites.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "esp_random.h"
#include <string.h>
#include <stdlib.h>

static const char *TAG = "solitaire";

/* ============================================================================
 * Card Definitions
 * ============================================================================ */

#define NUM_SUITS 4
#define NUM_RANKS 13
#define DECK_SIZE 52

typedef enum {
    SUIT_HEARTS = 0,
    SUIT_DIAMONDS,
    SUIT_CLUBS,
    SUIT_SPADES,
} suit_t;

typedef struct {
    uint8_t rank;       /* 1-13 (A, 2-10, J, Q, K) */
    uint8_t suit;       /* 0-3 */
    bool face_up;
} card_t;

/* ============================================================================
 * Game State
 * ============================================================================ */

#define MAX_TABLEAU_SIZE 20

typedef struct {
    card_t cards[MAX_TABLEAU_SIZE];
    int count;
} pile_t;

static pile_t s_stock;              /* Draw pile */
static pile_t s_waste;              /* Drawn cards */
static pile_t s_foundation[4];      /* Ace piles */
static pile_t s_tableau[7];         /* Main columns */

static int s_cursor_x = 0;          /* 0-6 for tableau, 7 for waste, 8-11 for foundation */
static int s_cursor_y = 0;          /* Position within pile */
static int s_held_from_x = -1;      /* Source pile of held cards */
static int s_held_from_y = -1;
static bool s_holding = false;

static bool s_won = false;
static uint32_t s_moves = 0;
static uint32_t s_start_time = 0;

/* ============================================================================
 * Card Helpers
 * ============================================================================ */

static const char *rank_str(int rank)
{
    static const char *ranks[] = {"?", "A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"};
    return (rank >= 1 && rank <= 13) ? ranks[rank] : "?";
}

static const char *suit_str(int suit)
{
    static const char *suits[] = {"H", "D", "C", "S"};  /* Hearts, Diamonds, Clubs, Spades */
    return (suit >= 0 && suit < 4) ? suits[suit] : "?";
}

static bool is_red(int suit)
{
    return suit == SUIT_HEARTS || suit == SUIT_DIAMONDS;
}

static bool can_stack_tableau(const card_t *top, const card_t *bottom)
{
    /* Must be opposite colors and descending rank */
    if (!top || !bottom) return false;
    if (is_red(top->suit) == is_red(bottom->suit)) return false;
    return top->rank == bottom->rank + 1;
}

static bool can_stack_foundation(const card_t *card, const pile_t *foundation)
{
    if (!card) return false;
    
    if (foundation->count == 0) {
        return card->rank == 1;  /* Only aces on empty foundation */
    }
    
    const card_t *top = &foundation->cards[foundation->count - 1];
    return card->suit == top->suit && card->rank == top->rank + 1;
}

/* ============================================================================
 * Game Logic
 * ============================================================================ */

static void shuffle_deck(card_t *deck)
{
    /* Fisher-Yates shuffle */
    for (int i = DECK_SIZE - 1; i > 0; i--) {
        int j = esp_random() % (i + 1);
        card_t tmp = deck[i];
        deck[i] = deck[j];
        deck[j] = tmp;
    }
}

static void new_game(void)
{
    ESP_LOGI(TAG, "Starting new game");
    
    /* Create and shuffle deck */
    card_t deck[DECK_SIZE];
    int idx = 0;
    for (int s = 0; s < NUM_SUITS; s++) {
        for (int r = 1; r <= NUM_RANKS; r++) {
            deck[idx].suit = s;
            deck[idx].rank = r;
            deck[idx].face_up = false;
            idx++;
        }
    }
    shuffle_deck(deck);
    
    /* Clear all piles */
    memset(&s_stock, 0, sizeof(s_stock));
    memset(&s_waste, 0, sizeof(s_waste));
    memset(s_foundation, 0, sizeof(s_foundation));
    memset(s_tableau, 0, sizeof(s_tableau));
    
    /* Deal to tableau */
    idx = 0;
    for (int col = 0; col < 7; col++) {
        for (int row = 0; row <= col; row++) {
            s_tableau[col].cards[row] = deck[idx++];
            s_tableau[col].cards[row].face_up = (row == col);
        }
        s_tableau[col].count = col + 1;
    }
    
    /* Remaining cards go to stock */
    while (idx < DECK_SIZE) {
        s_stock.cards[s_stock.count++] = deck[idx++];
    }
    
    s_cursor_x = 0;
    s_cursor_y = 0;
    s_holding = false;
    s_held_from_x = -1;
    s_won = false;
    s_moves = 0;
    s_start_time = esp_timer_get_time() / 1000000;
}

static void draw_from_stock(void)
{
    if (s_stock.count == 0) {
        /* Flip waste back to stock */
        while (s_waste.count > 0) {
            card_t card = s_waste.cards[--s_waste.count];
            card.face_up = false;
            s_stock.cards[s_stock.count++] = card;
        }
    } else {
        /* Draw one card */
        card_t card = s_stock.cards[--s_stock.count];
        card.face_up = true;
        s_waste.cards[s_waste.count++] = card;
    }
    s_moves++;
}

static pile_t *get_current_pile(void)
{
    if (s_cursor_x < 7) return &s_tableau[s_cursor_x];
    if (s_cursor_x == 7) return &s_waste;
    if (s_cursor_x >= 8 && s_cursor_x <= 11) return &s_foundation[s_cursor_x - 8];
    return NULL;
}

static card_t *get_top_card(pile_t *pile)
{
    if (!pile || pile->count == 0) return NULL;
    return &pile->cards[pile->count - 1];
}

static void try_auto_move_to_foundation(void)
{
    pile_t *pile = get_current_pile();
    card_t *card = get_top_card(pile);
    if (!card || !card->face_up) return;
    
    for (int f = 0; f < 4; f++) {
        if (can_stack_foundation(card, &s_foundation[f])) {
            s_foundation[f].cards[s_foundation[f].count++] = *card;
            pile->count--;
            
            /* Flip new top card if needed */
            if (pile->count > 0 && !pile->cards[pile->count - 1].face_up) {
                pile->cards[pile->count - 1].face_up = true;
            }
            
            s_moves++;
            break;
        }
    }
}

static void try_move_cards(int to_x)
{
    if (!s_holding || s_held_from_x < 0) return;
    
    pile_t *from = (s_held_from_x < 7) ? &s_tableau[s_held_from_x] : 
                   (s_held_from_x == 7) ? &s_waste : 
                   &s_foundation[s_held_from_x - 8];
    
    pile_t *to = (to_x < 7) ? &s_tableau[to_x] : 
                 (to_x == 7) ? &s_waste : 
                 &s_foundation[to_x - 8];
    
    if (!from || !to || from == to) {
        s_holding = false;
        return;
    }
    
    int num_cards = from->count - s_held_from_y;
    if (num_cards <= 0) {
        s_holding = false;
        return;
    }
    
    card_t *moving = &from->cards[s_held_from_y];
    
    /* Check if move is valid */
    bool valid = false;
    
    if (to_x < 7) {
        /* Moving to tableau */
        if (to->count == 0) {
            valid = (moving->rank == 13);  /* Only kings on empty */
        } else {
            card_t *target = get_top_card(to);
            valid = can_stack_tableau(target, moving);
        }
    } else if (to_x >= 8 && to_x <= 11) {
        /* Moving to foundation - single cards only */
        if (num_cards == 1) {
            valid = can_stack_foundation(moving, to);
        }
    }
    
    if (valid) {
        /* Move cards */
        for (int i = 0; i < num_cards; i++) {
            to->cards[to->count++] = from->cards[s_held_from_y + i];
        }
        from->count -= num_cards;
        
        /* Flip new top card */
        if (from->count > 0 && !from->cards[from->count - 1].face_up) {
            from->cards[from->count - 1].face_up = true;
        }
        
        s_moves++;
    }
    
    s_holding = false;
}

static bool check_win(void)
{
    for (int f = 0; f < 4; f++) {
        if (s_foundation[f].count != 13) return false;
    }
    return true;
}

/* ============================================================================
 * App Callbacks
 * ============================================================================ */

static void on_enter(void)
{
    ESP_LOGI(TAG, "Solitaire entered");
    if (!s_won && s_moves == 0) {
        new_game();
    }
}

static void on_exit(void)
{
    ESP_LOGI(TAG, "Solitaire exited");
}

static void on_input(int8_t x, int8_t y, uint8_t buttons)
{
    static uint32_t last_nav = 0;
    uint32_t now = esp_timer_get_time() / 1000;
    
    if (s_won) {
        if (buttons & (UI_BTN_PRESS | UI_BTN_BACK)) {
            new_game();
        }
        return;
    }
    
    if (buttons & UI_BTN_BACK) {
        if (s_holding) {
            s_holding = false;
        } else {
            ui_go_back();
        }
        return;
    }
    
    /* Navigation */
    if (now - last_nav > 150) {
        if (x > 30) {
            s_cursor_x = (s_cursor_x + 1) % 12;
            last_nav = now;
        } else if (x < -30) {
            s_cursor_x = (s_cursor_x - 1 + 12) % 12;
            last_nav = now;
        }
        
        pile_t *pile = get_current_pile();
        if (pile && y < -30 && s_cursor_y < pile->count - 1) {
            s_cursor_y++;
            last_nav = now;
        } else if (y > 30 && s_cursor_y > 0) {
            s_cursor_y--;
            last_nav = now;
        }
    }
    
    /* Actions */
    if (buttons & UI_BTN_PRESS) {
        if (s_cursor_x == 7 && s_waste.count == 0 && s_stock.count == 0) {
            /* Nothing to do */
        } else if (!s_holding) {
            pile_t *pile = get_current_pile();
            if (pile && pile->count > 0) {
                int card_idx = pile->count - 1 - s_cursor_y;
                if (card_idx >= 0 && pile->cards[card_idx].face_up) {
                    s_holding = true;
                    s_held_from_x = s_cursor_x;
                    s_held_from_y = card_idx;
                }
            }
        } else {
            try_move_cards(s_cursor_x);
        }
    }
    
    if (buttons & UI_BTN_DOUBLE) {
        draw_from_stock();
    }
    
    if (buttons & UI_BTN_LONG) {
        try_auto_move_to_foundation();
    }
    
    /* Check for win */
    if (check_win()) {
        s_won = true;
        ui_notify_simple("You Win!");
    }
}

static void on_render(void)
{
    int y = UI_STATUS_BAR_HEIGHT + 2;
    
    if (s_won) {
        display_draw_string(30, 25, "YOU WIN!", COLOR_WHITE, 1);
        uint32_t elapsed = (esp_timer_get_time() / 1000000) - s_start_time;
        display_printf(20, 40, COLOR_WHITE, 1, "Time: %d:%02d", elapsed / 60, elapsed % 60);
        display_printf(20, 52, COLOR_WHITE, 1, "Moves: %d", s_moves);
        return;
    }
    
    /* Top row: Stock, Waste, gap, Foundations */
    int card_w = 14;
    int card_h = 10;
    int gap = 2;
    
    /* Stock (leftmost) */
    int sx = 2;
    if (s_stock.count > 0) {
        display_draw_rect(sx, y, card_w, card_h, COLOR_WHITE);
        display_draw_string(sx + 3, y + 1, "#", COLOR_WHITE, 1);
    } else {
        display_draw_rect(sx, y, card_w, card_h, COLOR_WHITE);
    }
    if (s_cursor_x == 7 && s_waste.count == 0) {
        display_fill_rect(sx, y, card_w, card_h, COLOR_INVERSE);
    }
    
    /* Waste */
    int wx = sx + card_w + gap;
    if (s_waste.count > 0) {
        card_t *c = get_top_card(&s_waste);
        display_draw_rect(wx, y, card_w, card_h, COLOR_WHITE);
        display_printf(wx + 1, y + 1, COLOR_WHITE, 1, "%s%s", rank_str(c->rank), suit_str(c->suit));
    }
    if (s_cursor_x == 7 && s_waste.count > 0) {
        display_draw_rect(wx - 1, y - 1, card_w + 2, card_h + 2, COLOR_WHITE);
    }
    
    /* Foundations */
    for (int f = 0; f < 4; f++) {
        int fx = 70 + f * (card_w + gap);
        display_draw_rect(fx, y, card_w, card_h, COLOR_WHITE);
        
        if (s_foundation[f].count > 0) {
            card_t *c = get_top_card(&s_foundation[f]);
            display_printf(fx + 1, y + 1, COLOR_WHITE, 1, "%s%s", rank_str(c->rank), suit_str(c->suit));
        } else {
            display_draw_string(fx + 3, y + 1, suit_str(f), COLOR_WHITE, 1);
        }
        
        if (s_cursor_x == 8 + f) {
            display_draw_rect(fx - 1, y - 1, card_w + 2, card_h + 2, COLOR_WHITE);
        }
    }
    
    y += card_h + 4;
    
    /* Tableau */
    int col_w = DISPLAY_WIDTH / 7;
    int card_overlap = 6;
    
    for (int col = 0; col < 7; col++) {
        int cx = col * col_w + 2;
        pile_t *pile = &s_tableau[col];
        
        if (pile->count == 0) {
            display_draw_rect(cx, y, card_w, card_h, COLOR_WHITE);
            if (s_cursor_x == col) {
                display_fill_rect(cx, y, card_w, card_h, COLOR_INVERSE);
            }
        } else {
            for (int i = 0; i < pile->count; i++) {
                int cy = y + i * card_overlap;
                card_t *c = &pile->cards[i];
                
                if (c->face_up) {
                    display_draw_rect(cx, cy, card_w, card_h, COLOR_WHITE);
                    display_printf(cx + 1, cy + 1, COLOR_WHITE, 1, "%s%s", 
                                  rank_str(c->rank), suit_str(c->suit));
                } else {
                    display_fill_rect(cx, cy, card_w, card_h, COLOR_WHITE);
                }
                
                /* Highlight selection */
                if (s_cursor_x == col && pile->count - 1 - s_cursor_y == i) {
                    display_draw_rect(cx - 1, cy - 1, card_w + 2, card_h + 2, COLOR_WHITE);
                }
                
                /* Holding indicator */
                if (s_holding && s_held_from_x == col && i >= s_held_from_y) {
                    display_draw_pixel(cx + card_w - 2, cy + 1, COLOR_INVERSE);
                }
            }
        }
    }
}

static void on_tick(uint32_t dt_ms)
{
    (void)dt_ms;
}

/* ============================================================================
 * App Definition
 * ============================================================================ */

const ui_app_t app_solitaire = {
    .id = "solitaire",
    .name = "Cards",
    .icon = ICON_SOLITAIRE,
    .on_enter = on_enter,
    .on_exit = on_exit,
    .on_input = on_input,
    .on_render = on_render,
    .on_tick = on_tick,
};

