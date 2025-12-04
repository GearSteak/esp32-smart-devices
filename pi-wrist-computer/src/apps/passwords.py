"""
Password Manager App
Local KeePass vault viewer with pykeepass.
"""

import os
from typing import Optional, List, Dict
from src.ui.display import Display
from src.input.cardkb import KeyEvent, KeyCode

# Try to import pykeepass
try:
    from pykeepass import PyKeePass
    PYKEEPASS_AVAILABLE = True
except ImportError:
    PYKEEPASS_AVAILABLE = False


class PasswordEntry:
    """Represents a password entry."""
    
    def __init__(self, title: str, username: str, password: str, url: str = "", notes: str = ""):
        self.title = title
        self.username = username
        self.password = password
        self.url = url
        self.notes = notes


class PasswordsApp:
    """
    Password Manager
    
    Reads/writes local KeePass .kdbx files.
    Supports viewing, adding, editing, and deleting entries.
    """
    
    def __init__(self, ui):
        self.ui = ui
        self.vault_path = os.path.expanduser("~/vault.kdbx")
        self.kp: Optional[PyKeePass] = None
        self.entries: List[PasswordEntry] = []
        self.groups: List[str] = []
        self.kp_entries = []  # Raw KeePass entries
        
        self.mode = 'unlock'  # unlock, groups, entries, detail, edit, new, new_vault
        self.master_password = ""
        self.password_visible = False
        self.selected_index = 0
        self.scroll_offset = 0
        self.current_group = None
        self.current_group_obj = None
        self.current_entry: Optional[PasswordEntry] = None
        self.current_kp_entry = None  # Raw KeePass entry
        self.error_message = ""
        self.show_password = False
        
        # Password input state
        self.input_buffer = ""
        self.cursor_pos = 0
        
        # Edit mode state
        self.edit_fields = ['title', 'username', 'password', 'url', 'notes']
        self.edit_field_index = 0
        self.edit_data = {}
        self.editing_field = False  # Currently typing in a field
    
    def on_enter(self):
        """Called when app becomes active."""
        if not PYKEEPASS_AVAILABLE:
            self.error_message = "pykeepass not installed\npip install pykeepass"
            self.mode = 'error'
            return
        
        if not os.path.exists(self.vault_path):
            # Offer to create new vault
            self.mode = 'new_vault'
            self.input_buffer = ""
            return
        
        if self.kp:
            self.mode = 'groups'
        else:
            self.mode = 'unlock'
            self.input_buffer = ""
    
    def on_exit(self):
        """Called when leaving app."""
        # Clear sensitive data
        self.input_buffer = ""
        self.show_password = False
    
    def handle_input(self, event: KeyEvent) -> bool:
        """Handle input events."""
        if event.type != 'press':
            return False
        
        if self.mode == 'error':
            if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
                self.ui.go_back()
                return True
            return False
        
        if self.mode == 'unlock':
            return self._handle_unlock_input(event)
        elif self.mode == 'new_vault':
            return self._handle_new_vault_input(event)
        elif self.mode == 'groups':
            return self._handle_groups_input(event)
        elif self.mode == 'entries':
            return self._handle_entries_input(event)
        elif self.mode == 'detail':
            return self._handle_detail_input(event)
        elif self.mode == 'edit' or self.mode == 'new':
            return self._handle_edit_input(event)
        
        return False
    
    def _handle_new_vault_input(self, event: KeyEvent) -> bool:
        """Handle new vault creation input."""
        if event.code == KeyCode.ESC:
            self.ui.go_back()
            return True
        elif event.code == KeyCode.BACKSPACE:
            if self.input_buffer:
                self.input_buffer = self.input_buffer[:-1]
            else:
                self.ui.go_back()
            return True
        elif event.code == KeyCode.ENTER:
            if len(self.input_buffer) >= 4:
                self._create_new_vault()
            else:
                self.error_message = "Password too short (min 4)"
            return True
        elif event.char and len(event.char) == 1:
            self.input_buffer += event.char
            return True
        return False
    
    def _create_new_vault(self):
        """Create a new KeePass vault."""
        try:
            from pykeepass import create_database
            self.kp = create_database(self.vault_path, password=self.input_buffer)
            
            # Create a default group
            self.kp.add_group(self.kp.root_group, 'Passwords')
            self.kp.save()
            
            self._load_groups()
            self.mode = 'groups'
            self.error_message = ""
            self.input_buffer = ""
        except Exception as e:
            self.error_message = f"Failed: {str(e)[:25]}"
    
    def _handle_unlock_input(self, event: KeyEvent) -> bool:
        """Handle unlock screen input."""
        if event.code == KeyCode.ESC:
            self.ui.go_back()
            return True
        elif event.code == KeyCode.BACKSPACE:
            if self.input_buffer:
                self.input_buffer = self.input_buffer[:-1]
            else:
                self.ui.go_back()
            return True
        elif event.code == KeyCode.ENTER:
            self._try_unlock()
            return True
        elif event.char and len(event.char) == 1:
            self.input_buffer += event.char
            return True
        
        return False
    
    def _handle_groups_input(self, event: KeyEvent) -> bool:
        """Handle groups screen input."""
        if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            # Lock and go back
            self.kp = None
            self.entries = []
            self.groups = []
            self.ui.go_back()
            return True
        
        if event.code == KeyCode.UP:
            self.selected_index = max(0, self.selected_index - 1)
            return True
        elif event.code == KeyCode.DOWN:
            self.selected_index = min(len(self.groups) - 1, self.selected_index + 1)
            return True
        elif event.code == KeyCode.ENTER:
            if self.groups:
                self.current_group = self.groups[self.selected_index]
                self._load_entries()
                self.mode = 'entries'
                self.selected_index = 0
            return True
        elif event.char == 'l' or event.char == 'L':
            # Lock vault
            self.kp = None
            self.entries = []
            self.groups = []
            self.mode = 'unlock'
            self.input_buffer = ""
            return True
        
        return False
    
    def _handle_entries_input(self, event: KeyEvent) -> bool:
        """Handle entries screen input."""
        if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self.mode = 'groups'
            self.selected_index = 0
            return True
        
        if event.code == KeyCode.UP:
            self.selected_index = max(0, self.selected_index - 1)
            self._adjust_scroll()
            return True
        elif event.code == KeyCode.DOWN:
            self.selected_index = min(len(self.entries) - 1, self.selected_index + 1)
            self._adjust_scroll()
            return True
        elif event.code == KeyCode.ENTER:
            if self.entries:
                self.current_entry = self.entries[self.selected_index]
                self.current_kp_entry = self.kp_entries[self.selected_index]
                self.mode = 'detail'
                self.show_password = False
            return True
        elif event.char == 'n' or event.char == 'N':
            # New entry
            self._start_new_entry()
            return True
        
        return False
    
    def _handle_detail_input(self, event: KeyEvent) -> bool:
        """Handle detail screen input."""
        if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self.mode = 'entries'
            self.current_entry = None
            self.current_kp_entry = None
            self.show_password = False
            return True
        
        if event.char == 'p' or event.char == 'P':
            # Toggle password visibility
            self.show_password = not self.show_password
            return True
        elif event.char == 'e' or event.char == 'E':
            # Edit entry
            self._start_edit_entry()
            return True
        elif event.char == 'd' or event.char == 'D' or event.code == KeyCode.DELETE:
            # Delete entry
            self._delete_entry()
            return True
        
        return False
    
    def _handle_edit_input(self, event: KeyEvent) -> bool:
        """Handle edit/new entry input."""
        if self.editing_field:
            # Currently typing in a field
            if event.code == KeyCode.ENTER:
                self.editing_field = False
                return True
            elif event.code == KeyCode.ESC:
                # Cancel field edit, restore original
                field = self.edit_fields[self.edit_field_index]
                if self.mode == 'edit' and self.current_entry:
                    self.edit_data[field] = getattr(self.current_entry, field, '')
                else:
                    self.edit_data[field] = ''
                self.editing_field = False
                return True
            elif event.code == KeyCode.BACKSPACE:
                field = self.edit_fields[self.edit_field_index]
                self.edit_data[field] = self.edit_data[field][:-1]
                return True
            elif event.char and len(event.char) == 1:
                field = self.edit_fields[self.edit_field_index]
                self.edit_data[field] += event.char
                return True
            return False
        
        # Not editing a field - navigation mode
        if event.code == KeyCode.ESC or event.code == KeyCode.BACKSPACE:
            self.mode = 'entries' if self.mode == 'new' else 'detail'
            return True
        elif event.code == KeyCode.UP:
            self.edit_field_index = max(0, self.edit_field_index - 1)
            return True
        elif event.code == KeyCode.DOWN:
            self.edit_field_index = min(len(self.edit_fields), self.edit_field_index + 1)
            return True
        elif event.code == KeyCode.ENTER:
            if self.edit_field_index == len(self.edit_fields):
                # Save button
                self._save_entry()
            else:
                # Start editing field
                self.editing_field = True
            return True
        elif event.char == 'g' or event.char == 'G':
            # Generate random password
            self._generate_password()
            return True
        
        return False
    
    def _start_new_entry(self):
        """Start creating a new entry."""
        self.mode = 'new'
        self.edit_field_index = 0
        self.editing_field = False
        self.edit_data = {
            'title': '',
            'username': '',
            'password': '',
            'url': '',
            'notes': ''
        }
    
    def _start_edit_entry(self):
        """Start editing current entry."""
        if not self.current_entry:
            return
        
        self.mode = 'edit'
        self.edit_field_index = 0
        self.editing_field = False
        self.edit_data = {
            'title': self.current_entry.title,
            'username': self.current_entry.username,
            'password': self.current_entry.password,
            'url': self.current_entry.url,
            'notes': self.current_entry.notes
        }
    
    def _generate_password(self):
        """Generate a random password."""
        import random
        import string
        
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(random.choice(chars) for _ in range(16))
        self.edit_data['password'] = password
    
    def _save_entry(self):
        """Save the entry (new or edited)."""
        if not self.kp:
            return
        
        try:
            if self.mode == 'new':
                # Create new entry
                group = self.current_group_obj or self.kp.root_group
                self.kp.add_entry(
                    group,
                    self.edit_data['title'] or 'Untitled',
                    self.edit_data['username'],
                    self.edit_data['password'],
                    url=self.edit_data['url'],
                    notes=self.edit_data['notes']
                )
            else:
                # Update existing entry
                if self.current_kp_entry:
                    self.current_kp_entry.title = self.edit_data['title'] or 'Untitled'
                    self.current_kp_entry.username = self.edit_data['username']
                    self.current_kp_entry.password = self.edit_data['password']
                    self.current_kp_entry.url = self.edit_data['url']
                    self.current_kp_entry.notes = self.edit_data['notes']
            
            self.kp.save()
            self._load_entries()  # Refresh list
            self.mode = 'entries'
            self.error_message = ""
            
        except Exception as e:
            self.error_message = f"Save failed: {str(e)[:20]}"
    
    def _delete_entry(self):
        """Delete the current entry."""
        if not self.kp or not self.current_kp_entry:
            return
        
        try:
            self.kp.delete_entry(self.current_kp_entry)
            self.kp.save()
            self._load_entries()
            self.mode = 'entries'
            self.current_entry = None
            self.current_kp_entry = None
            self.selected_index = min(self.selected_index, len(self.entries) - 1)
            self.selected_index = max(0, self.selected_index)
        except Exception as e:
            self.error_message = f"Delete failed: {str(e)[:20]}"
    
    def _try_unlock(self):
        """Try to unlock the vault."""
        try:
            self.kp = PyKeePass(self.vault_path, password=self.input_buffer)
            self._load_groups()
            self.mode = 'groups'
            self.error_message = ""
            self.input_buffer = ""  # Clear password from memory
            self.selected_index = 0
        except Exception as e:
            self.error_message = "Wrong password"
            self.input_buffer = ""
    
    def _load_groups(self):
        """Load groups from vault."""
        if not self.kp:
            return
        
        self.groups = []
        for group in self.kp.groups:
            if group.name and group.name != 'Root':
                self.groups.append(group.name)
        
        # Add "All Entries" option
        self.groups.insert(0, "📁 All Entries")
        
        if not self.groups:
            self.groups = ["📁 All Entries"]
    
    def _load_entries(self):
        """Load entries for current group."""
        if not self.kp:
            return
        
        self.entries = []
        self.kp_entries = []
        
        if self.current_group == "📁 All Entries":
            kp_entries = self.kp.entries
            self.current_group_obj = self.kp.root_group
        else:
            group = self.kp.find_groups(name=self.current_group, first=True)
            self.current_group_obj = group
            kp_entries = group.entries if group else []
        
        for entry in kp_entries:
            self.entries.append(PasswordEntry(
                title=entry.title or "Untitled",
                username=entry.username or "",
                password=entry.password or "",
                url=entry.url or "",
                notes=entry.notes or ""
            ))
            self.kp_entries.append(entry)
    
    def _adjust_scroll(self):
        """Adjust scroll to keep selection visible."""
        max_visible = 8
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + max_visible:
            self.scroll_offset = self.selected_index - max_visible + 1
    
    def draw(self, display: Display):
        """Draw the password manager interface."""
        if self.mode == 'error':
            self._draw_error(display)
        elif self.mode == 'unlock':
            self._draw_unlock(display)
        elif self.mode == 'new_vault':
            self._draw_new_vault(display)
        elif self.mode == 'groups':
            self._draw_groups(display)
        elif self.mode == 'entries':
            self._draw_entries(display)
        elif self.mode == 'detail':
            self._draw_detail(display)
        elif self.mode == 'edit' or self.mode == 'new':
            self._draw_edit(display)
    
    def _draw_error(self, display: Display):
        """Draw error screen."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width, 28, fill='#500000')
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 14,
                    "🔒 PASSWORD VAULT", 'white', 14, 'mm')
        
        display.text(display.width // 2, display.height // 2 - 20,
                    "Error", '#ff0000', 16, 'mm')
        display.text(display.width // 2, display.height // 2 + 10,
                    self.error_message, '#888888', 12, 'mm')
        display.text(display.width // 2, display.height // 2 + 40,
                    "Press ESC to go back", '#666666', 10, 'mm')
    
    def _draw_unlock(self, display: Display):
        """Draw unlock screen."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width, 28, fill='#1a1a2e')
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 14,
                    "🔒 UNLOCK VAULT", 'white', 14, 'mm')
        
        center_y = display.height // 2
        
        # Lock icon
        display.text(display.width // 2, center_y - 50, "🔐", 'white', 32, 'mm')
        
        # Password field
        display.rect(20, center_y - 5, display.width - 40, 35, fill='#2a2a3e', outline='#444466')
        
        masked = "•" * len(self.input_buffer)
        if masked:
            display.text(30, center_y + 10, masked, 'white', 16, 'lm')
        else:
            display.text(30, center_y + 10, "Enter master password...", '#666666', 12, 'lm')
        
        # Cursor
        cursor_x = 30 + len(masked) * 10
        display.rect(cursor_x, center_y, 2, 25, fill='white')
        
        # Error message
        if self.error_message:
            display.text(display.width // 2, center_y + 50, self.error_message, '#ff4444', 12, 'mm')
        
        # Help
        display.text(display.width // 2, display.height - 20,
                    "⏎ Unlock  ESC Cancel", '#666666', 10, 'mm')
    
    def _draw_new_vault(self, display: Display):
        """Draw new vault creation screen."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width, 28, fill='#1a3a1a')
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 14,
                    "🔐 CREATE NEW VAULT", 'white', 14, 'mm')
        
        center_y = display.height // 2
        
        display.text(display.width // 2, center_y - 60, "No vault found", '#888888', 12, 'mm')
        display.text(display.width // 2, center_y - 40, "Create a new one?", '#888888', 12, 'mm')
        
        # Password field
        display.text(20, center_y - 15, "Master Password:", '#888888', 10)
        display.rect(20, center_y, display.width - 40, 35, fill='#2a3a2e', outline='#446644')
        
        masked = "•" * len(self.input_buffer)
        if masked:
            display.text(30, center_y + 15, masked, 'white', 16, 'lm')
        else:
            display.text(30, center_y + 15, "Min 4 characters...", '#666666', 12, 'lm')
        
        # Cursor
        cursor_x = 30 + len(masked) * 10
        display.rect(cursor_x, center_y + 5, 2, 25, fill='white')
        
        # Error/hint
        if self.error_message:
            display.text(display.width // 2, center_y + 50, self.error_message, '#ff4444', 12, 'mm')
        else:
            display.text(display.width // 2, center_y + 50, f"Length: {len(self.input_buffer)}", '#666666', 10, 'mm')
        
        display.text(display.width // 2, display.height - 20,
                    "⏎ Create  ESC Cancel", '#666666', 10, 'mm')
    
    def _draw_groups(self, display: Display):
        """Draw groups screen."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width, 28, fill='#1a1a2e')
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 14,
                    "🔓 VAULT UNLOCKED", '#00ff00', 14, 'mm')
        
        content_y = self.ui.STATUS_BAR_HEIGHT + 35
        
        for i, group in enumerate(self.groups):
            y = content_y + i * 30
            
            if y > display.height - 50:
                break
            
            selected = (i == self.selected_index)
            if selected:
                display.rect(0, y - 2, display.width, 28, fill='#2a2a3e')
            
            icon = "📁" if "All" not in group else "📂"
            display.text(15, y + 10, icon, 'white', 14)
            display.text(40, y + 10, group.replace("📁 ", ""), 'white' if selected else '#888888', 14)
        
        # Help
        display.text(display.width // 2, display.height - 15,
                    "⏎ Open  L:Lock  ESC Back", '#666666', 10, 'mm')
    
    def _draw_entries(self, display: Display):
        """Draw entries screen."""
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width, 28, fill='#1a1a2e')
        group_name = self.current_group.replace("📁 ", "") if self.current_group else "Entries"
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 14,
                    f"📁 {group_name[:20]}", 'white', 14, 'mm')
        
        content_y = self.ui.STATUS_BAR_HEIGHT + 35
        
        if not self.entries:
            display.text(display.width // 2, display.height // 2,
                        "No entries", '#666666', 14, 'mm')
            return
        
        max_visible = 8
        for i in range(max_visible):
            entry_idx = self.scroll_offset + i
            if entry_idx >= len(self.entries):
                break
            
            entry = self.entries[entry_idx]
            y = content_y + i * 28
            
            selected = (entry_idx == self.selected_index)
            if selected:
                display.rect(0, y - 2, display.width, 26, fill='#2a2a3e')
            
            display.text(10, y + 8, "🔑", 'white', 12)
            display.text(35, y + 6, entry.title[:25], 'white' if selected else '#888888', 12)
            if entry.username:
                display.text(35, y + 18, entry.username[:30], '#666666', 9)
        
        # Scroll indicator
        if len(self.entries) > max_visible:
            scroll_pct = self.scroll_offset / (len(self.entries) - max_visible)
            scroll_y = content_y + int(scroll_pct * (display.height - content_y - 60))
            display.rect(display.width - 4, scroll_y, 3, 20, fill='#444444')
        
        # Help
        display.text(display.width // 2, display.height - 15,
                    "⏎:View  N:New  ESC:Back", '#666666', 10, 'mm')
    
    def _draw_detail(self, display: Display):
        """Draw entry detail screen."""
        if not self.current_entry:
            return
        
        entry = self.current_entry
        
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width, 28, fill='#1a1a2e')
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 14,
                    f"🔑 {entry.title[:20]}", 'white', 14, 'mm')
        
        content_y = self.ui.STATUS_BAR_HEIGHT + 40
        line_height = 32
        
        # Username
        display.text(10, content_y, "Username:", '#888888', 10)
        display.text(10, content_y + 12, entry.username or "(none)", 'white', 12)
        
        # Password
        display.text(10, content_y + line_height, "Password:", '#888888', 10)
        if self.show_password:
            display.text(10, content_y + line_height + 12, entry.password or "(none)", '#00ff00', 12)
        else:
            display.text(10, content_y + line_height + 12, "••••••••", '#ffaa00', 12)
        
        # URL
        if entry.url:
            display.text(10, content_y + line_height * 2, "URL:", '#888888', 10)
            display.text(10, content_y + line_height * 2 + 12, entry.url[:35], '#6688ff', 11)
        
        # Notes preview
        if entry.notes:
            display.text(10, content_y + line_height * 3, "Notes:", '#888888', 10)
            display.text(10, content_y + line_height * 3 + 12, entry.notes[:40] + "...", '#aaaaaa', 10)
        
        # Show/hide password hint
        hint = "P:Show/Hide  E:Edit  D:Delete"
        display.text(display.width // 2, display.height - 15, hint, '#666666', 10, 'mm')
    
    def _draw_edit(self, display: Display):
        """Draw edit/new entry screen."""
        title = "NEW ENTRY" if self.mode == 'new' else "EDIT ENTRY"
        display.rect(0, self.ui.STATUS_BAR_HEIGHT, display.width, 28, fill='#1a2a1a')
        display.text(display.width // 2, self.ui.STATUS_BAR_HEIGHT + 14,
                    f"✏️ {title}", 'white', 14, 'mm')
        
        content_y = self.ui.STATUS_BAR_HEIGHT + 40
        field_height = 38
        
        field_labels = {
            'title': 'Title',
            'username': 'Username', 
            'password': 'Password',
            'url': 'URL',
            'notes': 'Notes'
        }
        
        for i, field in enumerate(self.edit_fields):
            y = content_y + i * field_height
            selected = (i == self.edit_field_index)
            editing = selected and self.editing_field
            
            # Field background
            if editing:
                display.rect(5, y, display.width - 10, field_height - 4, fill='#2a3a2a', outline='#44aa44')
            elif selected:
                display.rect(5, y, display.width - 10, field_height - 4, fill='#2a2a3a', outline='#4444aa')
            
            # Label
            display.text(10, y + 8, field_labels[field] + ":", '#888888', 10)
            
            # Value
            value = self.edit_data.get(field, '')
            if field == 'password' and not editing:
                display_value = '•' * len(value) if value else ''
            else:
                display_value = value[:30] if len(value) > 30 else value
            
            color = '#00ff00' if editing else ('white' if selected else '#cccccc')
            display.text(10, y + 22, display_value or '(empty)', color if display_value else '#666666', 12)
            
            # Cursor when editing
            if editing:
                cursor_x = 10 + len(display_value) * 7
                display.rect(cursor_x, y + 14, 2, 16, fill='#00ff00')
        
        # Save button
        save_y = content_y + len(self.edit_fields) * field_height
        save_selected = (self.edit_field_index == len(self.edit_fields))
        
        if save_selected:
            display.rect(40, save_y, display.width - 80, 30, fill='#0066cc')
        else:
            display.rect(40, save_y, display.width - 80, 30, fill='#333333', outline='#555555')
        
        display.text(display.width // 2, save_y + 15, "💾 SAVE", 'white', 14, 'mm')
        
        # Help
        help_text = "Type to edit" if self.editing_field else "⏎:Edit/Save G:GenPwd ESC:Back"
        display.text(display.width // 2, display.height - 12, help_text, '#666666', 9, 'mm')

