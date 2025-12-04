"""
TTRPG Character Sheet Application

Manage character sheets for tabletop RPGs:
- D&D 5e
- Shadowdark
- Custom/Generic
"""

from ..ui.framework import App, AppInfo, Rect
from ..ui.display import Display
from ..input.cardkb import KeyEvent, KeyCode
from . import ttrpg_data
import json
import os
import random
import threading


class TTRPGApp(App):
    """TTRPG character sheet manager."""
    
    SYSTEMS = ['dnd5e', 'shadowdark', 'generic']
    
    SYSTEM_INFO = {
        'dnd5e': {
            'name': 'D&D 5e',
            'stats': ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA'],
            'fields': ['name', 'class', 'race', 'level', 'hp', 'max_hp', 'ac', 'speed', 'proficiency'],
        },
        'shadowdark': {
            'name': 'Shadowdark',
            'stats': ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA'],
            'fields': ['name', 'ancestry', 'class', 'level', 'hp', 'max_hp', 'ac', 'title'],
        },
        'generic': {
            'name': 'Generic',
            'stats': ['STAT1', 'STAT2', 'STAT3', 'STAT4', 'STAT5', 'STAT6'],
            'fields': ['name', 'type', 'level', 'hp', 'max_hp'],
        }
    }
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='ttrpg',
            name='TTRPG',
            icon='⚔',
            color='#c0392b'
        )
        
        # Character data
        self.characters = []
        self.selected_char = 0
        
        # Current character being viewed/edited
        self.current_char = None
        
        # State
        self.mode = 'menu'  # 'menu', 'list', 'view', 'edit', 'new', 'roll', 'reference'
        self.view_tab = 0  # 0=stats, 1=info, 2=notes, 3=inventory
        self.edit_field = 0
        self.edit_value = ""
        
        # Roll result
        self.last_roll = None
        
        # Reference state
        self.ref_system = 0  # 0=D&D 5e, 1=Shadowdark
        self.ref_category = 0  # varies by system
        self.ref_items = []
        self.ref_selected = 0
        self.ref_scroll = 0
        self.ref_detail = None
        self.ref_detail_scroll = 0
        self.search_query = ""
        self.search_results = []
        self.searching = False
        
        # Reference categories per system
        self.ref_categories = {
            0: ['Spells', 'Races', 'Cond.', 'Items', 'Search'],  # D&D 5e
            1: ['Ancestry', 'Classes', 'Spells', 'Items'],  # Shadowdark
        }
        
        self._load_characters()
    
    def _load_characters(self):
        """Load characters from disk."""
        path = os.path.expanduser('~/.piwrist_characters.json')
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    self.characters = json.load(f)
        except Exception:
            self.characters = []
    
    def _save_characters(self):
        """Save characters to disk."""
        path = os.path.expanduser('~/.piwrist_characters.json')
        try:
            with open(path, 'w') as f:
                json.dump(self.characters, f, indent=2)
        except Exception as e:
            print(f"Error saving characters: {e}")
    
    def _new_character(self, system: str) -> dict:
        """Create a new blank character."""
        sys_info = self.SYSTEM_INFO.get(system, self.SYSTEM_INFO['generic'])
        
        char = {
            'system': system,
            'stats': {stat: 10 for stat in sys_info['stats']},
            'notes': '',
            'inventory': [],
        }
        
        # Add system-specific fields
        for field in sys_info['fields']:
            if field in ['level', 'hp', 'max_hp', 'ac', 'speed', 'proficiency']:
                char[field] = 0 if field != 'level' else 1
            else:
                char[field] = ''
        
        return char
    
    def _get_modifier(self, stat_value: int) -> int:
        """Calculate stat modifier (D&D style)."""
        return (stat_value - 10) // 2
    
    def _format_modifier(self, mod: int) -> str:
        """Format modifier with sign."""
        return f"+{mod}" if mod >= 0 else str(mod)
    
    def _roll_stat_check(self, stat: str):
        """Roll a d20 + stat modifier."""
        if not self.current_char:
            return
        
        stat_value = self.current_char.get('stats', {}).get(stat, 10)
        modifier = self._get_modifier(stat_value)
        roll = random.randint(1, 20)
        total = roll + modifier
        
        self.last_roll = {
            'stat': stat,
            'roll': roll,
            'modifier': modifier,
            'total': total,
            'crit': roll == 20,
            'fumble': roll == 1
        }
        self.mode = 'roll'
    
    def on_enter(self):
        self.mode = 'menu'
        self._load_characters()
    
    def on_exit(self):
        self._save_characters()
    
    def on_key(self, event: KeyEvent) -> bool:
        if self.mode == 'menu':
            return self._handle_menu_key(event)
        elif self.mode == 'list':
            return self._handle_list_key(event)
        elif self.mode == 'view':
            return self._handle_view_key(event)
        elif self.mode == 'edit':
            return self._handle_edit_key(event)
        elif self.mode == 'new':
            return self._handle_new_key(event)
        elif self.mode == 'roll':
            return self._handle_roll_key(event)
        elif self.mode == 'reference':
            return self._handle_reference_key(event)
        return False
    
    def _handle_menu_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.UP:
            self.edit_field = max(0, self.edit_field - 1)
            return True
        elif event.code == KeyCode.DOWN:
            self.edit_field = min(1, self.edit_field + 1)
            return True
        elif event.code == KeyCode.ENTER:
            if self.edit_field == 0:
                self.mode = 'list'
            else:
                self.mode = 'reference'
                self.ref_category = 0
                self._load_reference_category()
            self.edit_field = 0
            return True
        elif event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        return False
    
    def _handle_list_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.UP:
            if self.selected_char > 0:
                self.selected_char -= 1
            return True
        elif event.code == KeyCode.DOWN:
            if self.selected_char < len(self.characters) - 1:
                self.selected_char += 1
            return True
        elif event.code == KeyCode.ENTER:
            if self.characters:
                self.current_char = self.characters[self.selected_char]
                self.view_tab = 0
                self.mode = 'view'
            return True
        elif event.char == 'n' or event.char == 'N':
            self.mode = 'new'
            self.edit_field = 0  # System selection
            return True
        elif event.char == 'd' or event.char == 'D':
            if self.characters:
                self.characters.pop(self.selected_char)
                self._save_characters()
                if self.selected_char >= len(self.characters):
                    self.selected_char = max(0, len(self.characters) - 1)
            return True
        elif event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self.mode = 'menu'
            return True
        return False
    
    def _load_reference_category(self):
        """Load items for current reference category."""
        self.ref_items = []
        self.ref_selected = 0
        self.ref_scroll = 0
        self.ref_detail = None
        
        if self.ref_system == 0:  # D&D 5e
            if self.ref_category == 0:  # Spells
                spells = ttrpg_data.get_all_srd_spells()
                self.ref_items = [(k, v) for k, v in sorted(spells.items(), key=lambda x: (x[1]['level'], x[1]['name']))]
            elif self.ref_category == 1:  # Races
                races = ttrpg_data.get_all_srd_races()
                self.ref_items = [(k, v) for k, v in sorted(races.items(), key=lambda x: x[1]['name'])]
            elif self.ref_category == 2:  # Conditions
                conditions = ttrpg_data.get_all_conditions()
                self.ref_items = [(k, v) for k, v in sorted(conditions.items(), key=lambda x: x[1]['name'])]
            elif self.ref_category == 3:  # Items
                items = ttrpg_data.get_all_srd_items()
                self.ref_items = [(k, v) for k, v in sorted(items.items(), key=lambda x: x[1]['name'])]
            elif self.ref_category == 4:  # Search
                self.ref_items = []
        
        elif self.ref_system == 1:  # Shadowdark
            if self.ref_category == 0:  # Ancestries
                ancestries = ttrpg_data.get_shadowdark_ancestries()
                self.ref_items = [(k, v) for k, v in sorted(ancestries.items(), key=lambda x: x[1]['name'])]
            elif self.ref_category == 1:  # Classes
                classes = ttrpg_data.get_shadowdark_classes()
                self.ref_items = [(k, v) for k, v in sorted(classes.items(), key=lambda x: x[1]['name'])]
            elif self.ref_category == 2:  # Spells (use D&D for now, could add SD specific)
                spells = ttrpg_data.get_all_srd_spells()
                self.ref_items = [(k, v) for k, v in sorted(spells.items(), key=lambda x: (x[1]['level'], x[1]['name']))]
            elif self.ref_category == 3:  # Items (Shadowdark specific)
                items = ttrpg_data.get_shadowdark_items()
                self.ref_items = [(k, v) for k, v in sorted(items.items(), key=lambda x: x[1]['name'])]
    
    def _handle_reference_key(self, event: KeyEvent) -> bool:
        # If viewing detail
        if self.ref_detail:
            if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
                self.ref_detail = None
                return True
            elif event.code == KeyCode.UP:
                self.ref_detail_scroll = max(0, self.ref_detail_scroll - 1)
                return True
            elif event.code == KeyCode.DOWN:
                self.ref_detail_scroll += 1
                return True
            return True
        
        # Search mode
        if self.ref_category == 4:
            if event.code == KeyCode.ESC:
                if self.search_query:
                    self.search_query = ""
                    self.search_results = []
                else:
                    self.mode = 'menu'
                return True
            elif event.code == KeyCode.BACKSPACE:
                if self.search_query:
                    self.search_query = self.search_query[:-1]
                return True
            elif event.code == KeyCode.ENTER:
                if self.search_results and self.ref_selected < len(self.search_results):
                    self.ref_detail = self.search_results[self.ref_selected]
                    self.ref_detail_scroll = 0
                elif self.search_query:
                    self._do_online_search()
                return True
            elif event.code == KeyCode.UP:
                if self.search_results:
                    self.ref_selected = max(0, self.ref_selected - 1)
                return True
            elif event.code == KeyCode.DOWN:
                if self.search_results:
                    self.ref_selected = min(len(self.search_results) - 1, self.ref_selected + 1)
                return True
            elif event.code == KeyCode.LEFT:
                self.ref_category = 3
                self._load_reference_category()
                return True
            elif event.char:
                self.search_query += event.char
                return True
            return True
        
        # Category browsing
        if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self.mode = 'menu'
            return True
        elif event.code == KeyCode.LEFT:
            self.ref_category = max(0, self.ref_category - 1)
            self._load_reference_category()
            return True
        elif event.code == KeyCode.RIGHT:
            max_cat = len(self.ref_categories.get(self.ref_system, [])) - 1
            self.ref_category = min(max_cat, self.ref_category + 1)
            self._load_reference_category()
            return True
        elif event.char == 's' or event.char == 'S':
            # Switch game system
            self.ref_system = (self.ref_system + 1) % 2
            self.ref_category = 0
            self._load_reference_category()
            return True
        elif event.code == KeyCode.UP:
            if self.ref_selected > 0:
                self.ref_selected -= 1
                if self.ref_selected < self.ref_scroll:
                    self.ref_scroll = self.ref_selected
            return True
        elif event.code == KeyCode.DOWN:
            if self.ref_selected < len(self.ref_items) - 1:
                self.ref_selected += 1
            return True
        elif event.code == KeyCode.ENTER:
            if self.ref_items and self.ref_selected < len(self.ref_items):
                self.ref_detail = self.ref_items[self.ref_selected][1]
                self.ref_detail_scroll = 0
            return True
        return False
    
    def _do_online_search(self):
        """Perform online search via Open5e API."""
        if not self.search_query or self.searching:
            return
        
        self.searching = True
        self.search_results = []
        
        def search_thread():
            try:
                # Search spells first
                results = ttrpg_data.Open5eAPI.search_spells(self.search_query)
                for r in results[:10]:
                    self.search_results.append({
                        'name': r.get('name', 'Unknown'),
                        'type': 'Spell',
                        'level': r.get('level', '?'),
                        'description': r.get('desc', ''),
                        'school': r.get('school', ''),
                        'casting_time': r.get('casting_time', ''),
                        'range': r.get('range', ''),
                        'duration': r.get('duration', ''),
                    })
                
                # Search monsters
                monsters = ttrpg_data.Open5eAPI.search_monsters(self.search_query)
                for m in monsters[:5]:
                    self.search_results.append({
                        'name': m.get('name', 'Unknown'),
                        'type': 'Monster',
                        'cr': m.get('cr', '?'),
                        'hp': m.get('hit_points', '?'),
                        'ac': m.get('armor_class', '?'),
                        'description': m.get('desc', ''),
                    })
            except Exception as e:
                print(f"Search error: {e}")
            finally:
                self.searching = False
        
        thread = threading.Thread(target=search_thread, daemon=True)
        thread.start()
    
    def _handle_view_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self._save_characters()
            self.mode = 'list'
            return True
        elif event.code == KeyCode.LEFT:
            self.view_tab = max(0, self.view_tab - 1)
            return True
        elif event.code == KeyCode.RIGHT:
            self.view_tab = min(3, self.view_tab + 1)
            return True
        elif event.char == 'e' or event.char == 'E':
            self.mode = 'edit'
            self.edit_field = 0
            return True
        elif event.code == KeyCode.UP and self.view_tab == 0:
            # Quick HP adjustment
            if self.current_char:
                self.current_char['hp'] = min(
                    self.current_char.get('max_hp', 999),
                    self.current_char.get('hp', 0) + 1
                )
            return True
        elif event.code == KeyCode.DOWN and self.view_tab == 0:
            if self.current_char:
                self.current_char['hp'] = max(0, self.current_char.get('hp', 0) - 1)
            return True
        
        # Stat roll shortcuts (1-6 for stats)
        if event.char and event.char.isdigit() and self.view_tab == 0:
            idx = int(event.char) - 1
            if self.current_char:
                sys_info = self.SYSTEM_INFO.get(self.current_char.get('system', 'generic'))
                stats = sys_info['stats']
                if 0 <= idx < len(stats):
                    self._roll_stat_check(stats[idx])
            return True
        
        return False
    
    def _handle_edit_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            self.mode = 'view'
            return True
        elif event.code == KeyCode.UP:
            self.edit_field = max(0, self.edit_field - 1)
            return True
        elif event.code == KeyCode.DOWN:
            self.edit_field += 1
            return True
        elif event.code == KeyCode.LEFT or event.code == KeyCode.RIGHT:
            # Adjust numeric values
            if self.current_char:
                self._adjust_field(event.code == KeyCode.RIGHT)
            return True
        elif event.code == KeyCode.ENTER:
            # Edit text field
            return True
        elif event.code == KeyCode.BACKSPACE:
            # Delete char from text field
            self._edit_field_backspace()
            return True
        elif event.char:
            self._edit_field_char(event.char)
            return True
        return False
    
    def _adjust_field(self, increase: bool):
        """Adjust numeric field value."""
        if not self.current_char:
            return
        
        sys_info = self.SYSTEM_INFO.get(self.current_char.get('system', 'generic'))
        stats = sys_info['stats']
        fields = sys_info['fields']
        
        # Determine which field we're on
        if self.edit_field < len(stats):
            # Stat adjustment
            stat = stats[self.edit_field]
            current = self.current_char['stats'].get(stat, 10)
            if increase:
                self.current_char['stats'][stat] = min(30, current + 1)
            else:
                self.current_char['stats'][stat] = max(1, current - 1)
        else:
            # Field adjustment
            field_idx = self.edit_field - len(stats)
            if field_idx < len(fields):
                field = fields[field_idx]
                if field in ['level', 'hp', 'max_hp', 'ac', 'speed', 'proficiency']:
                    current = self.current_char.get(field, 0)
                    if increase:
                        self.current_char[field] = current + 1
                    else:
                        self.current_char[field] = max(0, current - 1)
    
    def _edit_field_char(self, char: str):
        """Add character to text field."""
        if not self.current_char:
            return
        
        sys_info = self.SYSTEM_INFO.get(self.current_char.get('system', 'generic'))
        stats = sys_info['stats']
        fields = sys_info['fields']
        
        field_idx = self.edit_field - len(stats)
        if field_idx >= 0 and field_idx < len(fields):
            field = fields[field_idx]
            if field not in ['level', 'hp', 'max_hp', 'ac', 'speed', 'proficiency']:
                self.current_char[field] = self.current_char.get(field, '') + char
    
    def _edit_field_backspace(self):
        """Delete char from text field."""
        if not self.current_char:
            return
        
        sys_info = self.SYSTEM_INFO.get(self.current_char.get('system', 'generic'))
        stats = sys_info['stats']
        fields = sys_info['fields']
        
        field_idx = self.edit_field - len(stats)
        if field_idx >= 0 and field_idx < len(fields):
            field = fields[field_idx]
            if field not in ['level', 'hp', 'max_hp', 'ac', 'speed', 'proficiency']:
                current = self.current_char.get(field, '')
                if current:
                    self.current_char[field] = current[:-1]
    
    def _handle_new_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            self.mode = 'list'
            return True
        elif event.code == KeyCode.LEFT:
            self.edit_field = max(0, self.edit_field - 1)
            return True
        elif event.code == KeyCode.RIGHT:
            self.edit_field = min(len(self.SYSTEMS) - 1, self.edit_field + 1)
            return True
        elif event.code == KeyCode.ENTER:
            # Create new character with selected system
            system = self.SYSTEMS[self.edit_field]
            new_char = self._new_character(system)
            self.characters.append(new_char)
            self.selected_char = len(self.characters) - 1
            self.current_char = new_char
            self._save_characters()
            self.mode = 'edit'
            self.edit_field = 0
            return True
        return False
    
    def _handle_roll_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC or event.code == KeyCode.ENTER or event.code == KeyCode.BACKSPACE:
            self.mode = 'view'
            return True
        return False
    
    def draw(self, display: Display):
        """Draw TTRPG app."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT,
                    display.width, display.height - self.ui.STATUS_BAR_HEIGHT,
                    fill='#1a0a0a')
        
        if self.mode == 'menu':
            self._draw_menu(display)
        elif self.mode == 'list':
            self._draw_list(display)
        elif self.mode == 'view':
            self._draw_view(display)
        elif self.mode == 'edit':
            self._draw_edit(display)
        elif self.mode == 'new':
            self._draw_new(display)
        elif self.mode == 'roll':
            self._draw_roll(display)
        elif self.mode == 'reference':
            self._draw_reference(display)
    
    def _draw_menu(self, display: Display):
        """Draw main TTRPG menu."""
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 30,
                    '⚔ TTRPG ⚔', '#c0392b', 20, 'mm')
        
        y = self.ui.STATUS_BAR_HEIGHT + 80
        
        options = [
            ('📋', 'Characters', f'{len(self.characters)} saved'),
            ('📚', 'Reference', 'Spells, Items, Rules'),
        ]
        
        for i, (icon, name, sub) in enumerate(options):
            selected = (i == self.edit_field)
            
            if selected:
                display.rect(20, y, display.width - 40, 55, fill='#c0392b')
            else:
                display.rect(20, y, display.width - 40, 55, fill='#2a1a1a')
            
            display.text(45, y + 20, icon, 'white', 22, 'mm')
            display.text(75, y + 15, name, 'white', 16, 'lm')
            display.text(75, y + 35, sub, '#888888', 10, 'lm')
            
            y += 65
    
    def _draw_list(self, display: Display):
        """Draw character list."""
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 12,
                    'Characters', 'white', 16, 'mm')
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 12,
                    'N:New D:Del', '#666666', 9, 'rm')
        
        if not self.characters:
            display.text(display.width // 2, display.height // 2,
                        'No characters', '#666666', 14, 'mm')
            display.text(display.width // 2, display.height // 2 + 20,
                        'Press N to create one', '#555555', 11, 'mm')
            return
        
        y = self.ui.STATUS_BAR_HEIGHT + 35
        item_height = 45
        
        for i, char in enumerate(self.characters):
            selected = (i == self.selected_char)
            
            if selected:
                display.rect(10, y, display.width - 20, item_height - 3, fill='#c0392b')
            else:
                display.rect(10, y, display.width - 20, item_height - 3, fill='#2a1a1a')
            
            # Name
            name = char.get('name', 'Unnamed')[:20]
            display.text(20, y + 10, name, 'white', 14)
            
            # System and class
            system = self.SYSTEM_INFO.get(char.get('system', 'generic'), {}).get('name', 'Generic')
            char_class = char.get('class', char.get('ancestry', ''))[:15]
            level = char.get('level', 1)
            sub_text = f"{system} - Lvl {level} {char_class}"
            display.text(20, y + 28, sub_text, '#aaaaaa', 10)
            
            y += item_height
    
    def _draw_view(self, display: Display):
        """Draw character view."""
        if not self.current_char:
            return
        
        char = self.current_char
        sys_info = self.SYSTEM_INFO.get(char.get('system', 'generic'))
        
        # Header
        name = char.get('name', 'Unnamed')[:18]
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 8, name, 'white', 14)
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 8, 'E:Edit', '#666666', 9, 'rm')
        
        # Tabs
        tabs = ['Stats', 'Info', 'Notes', 'Items']
        tab_width = display.width // 4
        tab_y = self.ui.STATUS_BAR_HEIGHT + 28
        
        for i, tab in enumerate(tabs):
            x = i * tab_width
            selected = (i == self.view_tab)
            if selected:
                display.rect(x, tab_y, tab_width, 20, fill='#c0392b')
            display.text(x + tab_width // 2, tab_y + 10, tab, 
                        'white' if selected else '#888888', 10, 'mm')
        
        content_y = tab_y + 25
        
        if self.view_tab == 0:
            self._draw_stats_tab(display, content_y)
        elif self.view_tab == 1:
            self._draw_info_tab(display, content_y)
        elif self.view_tab == 2:
            self._draw_notes_tab(display, content_y)
        elif self.view_tab == 3:
            self._draw_inventory_tab(display, content_y)
    
    def _draw_stats_tab(self, display: Display, y: int):
        """Draw stats tab."""
        char = self.current_char
        sys_info = self.SYSTEM_INFO.get(char.get('system', 'generic'))
        stats = sys_info['stats']
        
        # HP bar
        hp = char.get('hp', 0)
        max_hp = char.get('max_hp', 1)
        hp_pct = hp / max(1, max_hp)
        
        display.text(10, y, f'HP: {hp}/{max_hp}', 'white', 12)
        display.rect(80, y, display.width - 90, 14, color='#444444')
        hp_color = '#00ff00' if hp_pct > 0.5 else ('#ffcc00' if hp_pct > 0.25 else '#ff4444')
        if hp_pct > 0:
            display.rect(81, y + 1, int((display.width - 92) * hp_pct), 12, fill=hp_color)
        display.text(display.width // 2 + 30, y + 7, '↑/↓ adjust', '#555555', 8, 'mm')
        y += 25
        
        # Stats grid (2 columns)
        col_width = (display.width - 20) // 2
        
        for i, stat in enumerate(stats):
            col = i % 2
            row = i // 2
            
            x = 10 + col * col_width
            stat_y = y + row * 35
            
            value = char.get('stats', {}).get(stat, 10)
            mod = self._get_modifier(value)
            mod_str = self._format_modifier(mod)
            
            # Stat box
            display.rect(x, stat_y, col_width - 10, 30, fill='#2a1a1a', color='#444444')
            display.text(x + 5, stat_y + 8, stat, '#c0392b', 10)
            display.text(x + col_width - 15, stat_y + 8, str(value), 'white', 12, 'rt')
            display.text(x + col_width - 15, stat_y + 20, mod_str, '#888888', 10, 'rt')
            
            # Roll hint
            display.text(x + 5, stat_y + 20, f'{i+1}', '#555555', 8)
        
        # AC and other combat stats
        y += (len(stats) // 2 + 1) * 35
        ac = char.get('ac', 10)
        display.text(10, y, f'AC: {ac}', '#888888', 11)
        
        if 'speed' in char:
            display.text(70, y, f'Speed: {char["speed"]}', '#888888', 11)
    
    def _draw_info_tab(self, display: Display, y: int):
        """Draw info tab."""
        char = self.current_char
        sys_info = self.SYSTEM_INFO.get(char.get('system', 'generic'))
        
        fields = sys_info['fields']
        
        for field in fields:
            if field in ['hp', 'max_hp']:
                continue
            
            value = char.get(field, '')
            label = field.replace('_', ' ').title()
            
            display.text(10, y, f'{label}:', '#888888', 10)
            display.text(10, y + 14, str(value)[:30] or '-', 'white', 12)
            y += 35
    
    def _draw_notes_tab(self, display: Display, y: int):
        """Draw notes tab."""
        char = self.current_char
        notes = char.get('notes', '')
        
        lines = notes.split('\n')
        for line in lines[:10]:
            display.text(10, y, line[:38], 'white', 10)
            y += 14
    
    def _draw_inventory_tab(self, display: Display, y: int):
        """Draw inventory tab."""
        char = self.current_char
        inventory = char.get('inventory', [])
        
        if not inventory:
            display.text(display.width // 2, y + 30, 'No items', '#666666', 12, 'mm')
            return
        
        for item in inventory[:8]:
            display.text(15, y, f'• {item[:35]}', 'white', 10)
            y += 18
    
    def _draw_edit(self, display: Display):
        """Draw edit mode."""
        if not self.current_char:
            return
        
        char = self.current_char
        sys_info = self.SYSTEM_INFO.get(char.get('system', 'generic'))
        stats = sys_info['stats']
        fields = sys_info['fields']
        
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 10,
                    'Edit Character', 'white', 14, 'mm')
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 10,
                    '←/→ adjust', '#666666', 9, 'rm')
        
        y = self.ui.STATUS_BAR_HEIGHT + 30
        item_height = 25
        item_idx = 0
        
        # Stats
        for stat in stats:
            selected = (self.edit_field == item_idx)
            value = char.get('stats', {}).get(stat, 10)
            
            if selected:
                display.rect(5, y, display.width - 10, item_height - 2, fill='#c0392b')
            
            display.text(10, y + 6, stat, 'white', 11)
            display.text(display.width - 15, y + 6, str(value), 'white', 12, 'rt')
            
            y += item_height
            item_idx += 1
        
        y += 10
        
        # Fields
        for field in fields:
            selected = (self.edit_field == item_idx)
            value = char.get(field, '')
            label = field.replace('_', ' ').title()
            
            if selected:
                display.rect(5, y, display.width - 10, item_height - 2, fill='#c0392b')
            
            display.text(10, y + 6, label + ':', '#888888', 10)
            display.text(display.width - 15, y + 6, str(value)[:15], 'white', 11, 'rt')
            
            y += item_height
            item_idx += 1
    
    def _draw_new(self, display: Display):
        """Draw new character system selection."""
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 20,
                    'Select Game System', 'white', 16, 'mm')
        
        y = self.ui.STATUS_BAR_HEIGHT + 60
        
        for i, system in enumerate(self.SYSTEMS):
            selected = (i == self.edit_field)
            sys_info = self.SYSTEM_INFO[system]
            
            if selected:
                display.rect(20, y, display.width - 40, 45, fill='#c0392b')
            else:
                display.rect(20, y, display.width - 40, 45, fill='#2a1a1a')
            
            display.text(display.width // 2, y + 22, sys_info['name'], 'white', 16, 'mm')
            y += 55
        
            display.text(display.width // 2, display.height - 25,
                    'Enter to select', '#666666', 11, 'mm')
    
    def _draw_reference(self, display: Display):
        """Draw reference browser."""
        # System indicator
        system_names = ['D&D 5e', 'Shadowdark']
        system_name = system_names[self.ref_system]
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width, 18, fill='#1a0a0a')
        display.text(5, self.ui.STATUS_BAR_HEIGHT + 9, system_name, '#c0392b', 10, 'lm')
        display.text(display.width - 5, self.ui.STATUS_BAR_HEIGHT + 9, 'S:Switch', '#666666', 8, 'rm')
        
        # Category tabs
        categories = self.ref_categories.get(self.ref_system, [])
        tab_width = display.width // max(len(categories), 1)
        tab_y = self.ui.STATUS_BAR_HEIGHT + 18
        
        for i, cat in enumerate(categories):
            x = i * tab_width
            selected = (i == self.ref_category)
            if selected:
                display.rect(x, tab_y, tab_width, 20, fill='#c0392b')
            display.text(x + tab_width // 2, tab_y + 10,
                        cat, 'white' if selected else '#666666', 9, 'mm')
        
        content_y = self.ui.STATUS_BAR_HEIGHT + 40
        
        # Detail view
        if self.ref_detail:
            self._draw_reference_detail(display, content_y)
            return
        
        # Search mode (D&D only, category 4)
        if self.ref_system == 0 and self.ref_category == 4:
            self._draw_search(display, content_y)
            return
        
        # List view
        if not self.ref_items:
            display.text(display.width // 2, display.height // 2,
                        'No items', '#666666', 12, 'mm')
            return
        
        item_height = 30
        max_visible = (display.height - content_y - 10) // item_height
        
        # Adjust scroll
        if self.ref_selected >= self.ref_scroll + max_visible:
            self.ref_scroll = self.ref_selected - max_visible + 1
        
        for i in range(max_visible):
            idx = self.ref_scroll + i
            if idx >= len(self.ref_items):
                break
            
            key, item = self.ref_items[idx]
            y = content_y + i * item_height
            selected = (idx == self.ref_selected)
            
            if selected:
                display.rect(5, y, display.width - 10, item_height - 2, fill='#c0392b')
            
            name = item.get('name', key)[:22]
            display.text(10, y + 8, name, 'white', 11)
            
            # Sub info based on category and system
            if self.ref_system == 0:  # D&D 5e
                if self.ref_category == 0:  # Spells
                    level = item.get('level', 0)
                    level_str = 'Cantrip' if level == 0 else f'Lvl {level}'
                    display.text(display.width - 10, y + 8, level_str, '#888888', 10, 'rt')
                elif self.ref_category == 1:  # Races
                    speed = item.get('speed', 30)
                    display.text(display.width - 10, y + 8, f'{speed} ft', '#888888', 10, 'rt')
                elif self.ref_category == 3:  # Items
                    item_type = item.get('type', '')[:10]
                    display.text(display.width - 10, y + 8, item_type, '#888888', 10, 'rt')
            elif self.ref_system == 1:  # Shadowdark
                if self.ref_category == 1:  # Classes
                    hit_die = item.get('hit_die', '?')
                    display.text(display.width - 10, y + 8, hit_die, '#888888', 10, 'rt')
    
    def _draw_reference_detail(self, display: Display, start_y: int):
        """Draw reference item detail."""
        item = self.ref_detail
        if not item:
            return
        
        # Name
        name = item.get('name', 'Unknown')
        display.text(10, start_y + 5, name, '#c0392b', 14)
        
        y = start_y + 25
        line_height = 14
        max_lines = (display.height - y - 20) // line_height
        
        lines = []
        
        # Build content based on type
        if 'level' in item:  # Spell
            level = item.get('level', 0)
            level_str = 'Cantrip' if level == 0 else f'Level {level}'
            lines.append(f"{level_str} {item.get('school', '')}")
            lines.append(f"Cast: {item.get('casting_time', '?')}")
            lines.append(f"Range: {item.get('range', '?')}")
            lines.append(f"Duration: {item.get('duration', '?')}")
            lines.append('')
        elif 'traits' in item:  # Race/Ancestry
            if 'speed' in item:
                lines.append(f"Speed: {item.get('speed', 30)} ft")
            if 'size' in item:
                lines.append(f"Size: {item.get('size', 'Medium')}")
            lines.append('')
            lines.append('Traits:')
            for trait in item.get('traits', []):
                # Word wrap traits
                words = trait.split()
                line = ''
                for word in words:
                    if len(line) + len(word) > 35:
                        lines.append(f'  {line}')
                        line = word
                    else:
                        line = f'{line} {word}' if line else word
                if line:
                    lines.append(f'  {line}')
        elif 'hit_die' in item:  # Shadowdark Class
            lines.append(f"Hit Die: {item.get('hit_die', '?')}")
            lines.append(f"Weapons: {item.get('weapons', '?')}")
            lines.append(f"Armor: {item.get('armor', '?')}")
            lines.append('')
            lines.append('Features:')
            for feature in item.get('features', []):
                words = feature.split()
                line = ''
                for word in words:
                    if len(line) + len(word) > 35:
                        lines.append(f'  {line}')
                        line = word
                    else:
                        line = f'{line} {word}' if line else word
                if line:
                    lines.append(f'  {line}')
        elif 'effects' in item:  # Condition
            for effect in item.get('effects', []):
                words = effect.split()
                line = ''
                for word in words:
                    if len(line) + len(word) > 38:
                        lines.append(f'• {line}')
                        line = word
                    else:
                        line = f'{line} {word}' if line else word
                if line:
                    lines.append(f'• {line}')
        elif 'type' in item:  # Item (D&D or Shadowdark)
            lines.append(f"Type: {item.get('type', '?')}")
            if 'rarity' in item:
                lines.append(f"Rarity: {item.get('rarity', '?')}")
            if 'cost' in item:
                lines.append(f"Cost: {item.get('cost', '?')}")
            if 'damage' in item:
                lines.append(f"Damage: {item.get('damage', '?')}")
            if 'ac' in item:
                lines.append(f"AC: {item.get('ac', '?')}")
            if 'weight' in item:
                lines.append(f"Weight: {item.get('weight', '?')}")
            if 'slots' in item:
                lines.append(f"Gear Slots: {item.get('slots', '?')}")
            if item.get('attunement'):
                lines.append("⚡ Requires Attunement")
            if item.get('properties'):
                lines.append(f"Props: {', '.join(item['properties'])}")
        
        # Description
        desc = item.get('description', '')
        if desc:
            lines.append('')
            words = desc.split()
            line = ''
            for word in words:
                if len(line) + len(word) > 38:
                    lines.append(line)
                    line = word
                else:
                    line = f'{line} {word}' if line else word
            if line:
                lines.append(line)
        
        # Display with scroll
        visible = lines[self.ref_detail_scroll:self.ref_detail_scroll + max_lines]
        for line in visible:
            display.text(10, y, line[:40], 'white', 10)
            y += line_height
        
        # Scroll indicator
        if len(lines) > max_lines:
            display.text(display.width - 10, display.height - 15,
                        f'{self.ref_detail_scroll + 1}/{len(lines)}', '#666666', 9, 'rt')
        
        display.text(10, display.height - 15, 'ESC: Back', '#666666', 9)
    
    def _draw_search(self, display: Display, start_y: int):
        """Draw search interface."""
        # Search box
        display.rect(10, start_y, display.width - 20, 30, fill='#2a1a1a', color='#c0392b')
        display.text(15, start_y + 8, 'Search:', '#888888', 10)
        query_display = self.search_query[-20:] if len(self.search_query) > 20 else self.search_query
        display.text(70, start_y + 8, query_display + '_', 'white', 11)
        
        y = start_y + 40
        
        if self.searching:
            display.text(display.width // 2, y + 30, 'Searching...', '#888888', 12, 'mm')
            return
        
        if not self.search_results:
            display.text(display.width // 2, y + 30, 'Type and press Enter', '#666666', 11, 'mm')
            display.text(display.width // 2, y + 50, 'to search Open5e', '#666666', 10, 'mm')
            return
        
        # Results
        item_height = 35
        max_visible = (display.height - y - 10) // item_height
        
        for i, result in enumerate(self.search_results[:max_visible]):
            ry = y + i * item_height
            selected = (i == self.ref_selected)
            
            if selected:
                display.rect(5, ry, display.width - 10, item_height - 2, fill='#c0392b')
            
            name = result.get('name', '?')[:25]
            rtype = result.get('type', '?')
            display.text(10, ry + 8, name, 'white', 11)
            display.text(10, ry + 22, rtype, '#888888', 9)
            
            if rtype == 'Spell':
                display.text(display.width - 10, ry + 12, f"Lvl {result.get('level', '?')}", '#888888', 10, 'rt')
            elif rtype == 'Monster':
                display.text(display.width - 10, ry + 12, f"CR {result.get('cr', '?')}", '#888888', 10, 'rt')
    
    def _draw_roll(self, display: Display):
        """Draw roll result."""
        if not self.last_roll:
            return
        
        roll = self.last_roll
        
        # Stat name
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 30,
                    f'{roll["stat"]} Check', '#c0392b', 16, 'mm')
        
        # Big result
        total = roll['total']
        display.text(display.width // 2, display.height // 2 - 10,
                    str(total), 'white', 56, 'mm')
        
        # Breakdown
        mod_str = self._format_modifier(roll['modifier'])
        breakdown = f'd20({roll["roll"]}) {mod_str}'
        display.text(display.width // 2, display.height // 2 + 35,
                    breakdown, '#888888', 12, 'mm')
        
        # Critical indicators
        if roll['crit']:
            display.text(display.width // 2, display.height // 2 + 60,
                        '⭐ NATURAL 20! ⭐', '#ffcc00', 14, 'mm')
        elif roll['fumble']:
            display.text(display.width // 2, display.height // 2 + 60,
                        '💀 NATURAL 1 💀', '#ff4444', 14, 'mm')
        
        display.text(display.width // 2, display.height - 25,
                    'Press any key', '#666666', 10, 'mm')

