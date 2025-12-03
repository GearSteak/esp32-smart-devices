"""
Notes Application

Simple note-taking app with:
- Create/edit/delete notes
- Text editing with CardKB
- Save to filesystem
"""

from ..ui.framework import App, AppInfo, Rect, TextInput, ListBox
from ..ui.display import Display
from ..input.cardkb import KeyEvent, KeyCode
import os
import json
from datetime import datetime


class NotesApp(App):
    """Notes application."""
    
    def __init__(self, ui):
        super().__init__(ui)
        self.info = AppInfo(
            id='notes',
            name='Notes',
            icon='📝',
            color='#ffcc00'
        )
        
        self.notes_dir = ui.config.get('paths', {}).get('notes', './data/notes')
        self.notes = []  # List of {'id', 'title', 'content', 'modified'}
        self.selected_index = 0
        
        self.mode = 'list'  # 'list', 'view', 'edit'
        self.current_note = None
        self.edit_buffer = ''
        self.cursor_pos = 0
        self.scroll_offset = 0
    
    def on_enter(self):
        """Load notes."""
        self._ensure_dir()
        self._load_notes()
        self.mode = 'list'
    
    def on_exit(self):
        """Save current note if editing."""
        if self.mode == 'edit' and self.current_note:
            self._save_note()
    
    def _ensure_dir(self):
        """Ensure notes directory exists."""
        os.makedirs(self.notes_dir, exist_ok=True)
    
    def _load_notes(self):
        """Load all notes from disk."""
        self.notes = []
        
        try:
            for filename in os.listdir(self.notes_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.notes_dir, filename)
                    with open(filepath, 'r') as f:
                        note = json.load(f)
                        note['id'] = filename[:-5]  # Remove .json
                        self.notes.append(note)
        except Exception as e:
            print(f"Error loading notes: {e}")
        
        # Sort by modified date
        self.notes.sort(key=lambda n: n.get('modified', ''), reverse=True)
    
    def _save_note(self):
        """Save current note to disk."""
        if not self.current_note:
            return
        
        self.current_note['content'] = self.edit_buffer
        self.current_note['modified'] = datetime.now().isoformat()
        
        # Generate title from first line
        lines = self.edit_buffer.split('\n')
        self.current_note['title'] = lines[0][:30] if lines else 'Untitled'
        
        filepath = os.path.join(self.notes_dir, f"{self.current_note['id']}.json")
        with open(filepath, 'w') as f:
            json.dump({
                'title': self.current_note['title'],
                'content': self.current_note['content'],
                'modified': self.current_note['modified']
            }, f)
    
    def _create_note(self):
        """Create a new note."""
        note_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.current_note = {
            'id': note_id,
            'title': 'New Note',
            'content': '',
            'modified': datetime.now().isoformat()
        }
        self.notes.insert(0, self.current_note)
        self.edit_buffer = ''
        self.cursor_pos = 0
        self.mode = 'edit'
    
    def _delete_note(self, note):
        """Delete a note."""
        filepath = os.path.join(self.notes_dir, f"{note['id']}.json")
        try:
            os.remove(filepath)
            self.notes.remove(note)
            if self.selected_index >= len(self.notes):
                self.selected_index = max(0, len(self.notes) - 1)
        except Exception as e:
            print(f"Error deleting note: {e}")
    
    def on_key(self, event: KeyEvent) -> bool:
        if self.mode == 'list':
            return self._handle_list_key(event)
        elif self.mode == 'view':
            return self._handle_view_key(event)
        elif self.mode == 'edit':
            return self._handle_edit_key(event)
        return False
    
    def _handle_list_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.UP:
            if self.selected_index > 0:
                self.selected_index -= 1
            return True
        elif event.code == KeyCode.DOWN:
            if self.selected_index < len(self.notes) - 1:
                self.selected_index += 1
            return True
        elif event.code == KeyCode.ENTER:
            if self.notes:
                self.current_note = self.notes[self.selected_index]
                self.edit_buffer = self.current_note.get('content', '')
                self.cursor_pos = len(self.edit_buffer)
                self.mode = 'view'
            return True
        elif event.char == 'n' or event.char == 'N':
            self._create_note()
            return True
        elif event.code == KeyCode.DEL and self.notes:
            self._delete_note(self.notes[self.selected_index])
            return True
        elif event.code == KeyCode.ESC:
            self.ui.go_home()
            return True
        return False
    
    def _handle_view_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ENTER or event.char == 'e':
            self.mode = 'edit'
            return True
        elif event.code == KeyCode.UP:
            if self.scroll_offset > 0:
                self.scroll_offset -= 1
            return True
        elif event.code == KeyCode.DOWN:
            self.scroll_offset += 1
            return True
        elif event.code == KeyCode.ESC:
            self.mode = 'list'
            self.scroll_offset = 0
            return True
        return False
    
    def _handle_edit_key(self, event: KeyEvent) -> bool:
        if event.code == KeyCode.ESC:
            self._save_note()
            self.mode = 'view'
            return True
        elif event.code == KeyCode.BACKSPACE:
            if self.cursor_pos > 0:
                self.edit_buffer = (self.edit_buffer[:self.cursor_pos-1] + 
                                   self.edit_buffer[self.cursor_pos:])
                self.cursor_pos -= 1
            return True
        elif event.code == KeyCode.DEL:
            if self.cursor_pos < len(self.edit_buffer):
                self.edit_buffer = (self.edit_buffer[:self.cursor_pos] + 
                                   self.edit_buffer[self.cursor_pos+1:])
            return True
        elif event.code == KeyCode.LEFT:
            if self.cursor_pos > 0:
                self.cursor_pos -= 1
            return True
        elif event.code == KeyCode.RIGHT:
            if self.cursor_pos < len(self.edit_buffer):
                self.cursor_pos += 1
            return True
        elif event.code == KeyCode.ENTER:
            self.edit_buffer = (self.edit_buffer[:self.cursor_pos] + '\n' + 
                               self.edit_buffer[self.cursor_pos:])
            self.cursor_pos += 1
            return True
        elif event.char:
            self.edit_buffer = (self.edit_buffer[:self.cursor_pos] + 
                               event.char + 
                               self.edit_buffer[self.cursor_pos:])
            self.cursor_pos += 1
            return True
        return False
    
    def draw(self, display: Display):
        """Draw notes screen."""
        # Background
        display.rect(0, self.ui.STATUS_BAR_HEIGHT,
                    display.width, display.height - self.ui.STATUS_BAR_HEIGHT,
                    fill='#111111')
        
        if self.mode == 'list':
            self._draw_list(display)
        elif self.mode == 'view':
            self._draw_view(display)
        elif self.mode == 'edit':
            self._draw_edit(display)
    
    def _draw_list(self, display: Display):
        """Draw note list."""
        # Title bar
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 5, 'Notes', 'white', 16)
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 5,
                    'N: New', '#666666', 12, 'rt')
        
        if not self.notes:
            display.text(display.width // 2, display.height // 2,
                        'No notes yet', '#666666', 14, 'mm')
            display.text(display.width // 2, display.height // 2 + 20,
                        'Press N to create one', '#666666', 12, 'mm')
            return
        
        # List items
        item_height = 40
        start_y = self.ui.STATUS_BAR_HEIGHT + 30
        visible = (display.height - start_y) // item_height
        
        for i in range(min(visible, len(self.notes))):
            note = self.notes[i]
            y = start_y + i * item_height
            selected = (i == self.selected_index)
            
            if selected:
                display.rect(5, y, display.width - 10, item_height - 2,
                            fill='#0066cc')
            
            # Title
            title = note.get('title', 'Untitled')[:25]
            display.text(15, y + 10, title, 'white', 14)
            
            # Preview
            content = note.get('content', '')
            preview = content.replace('\n', ' ')[:35]
            display.text(15, y + 26, preview, '#888888', 11)
    
    def _draw_view(self, display: Display):
        """Draw note view."""
        if not self.current_note:
            return
        
        # Title bar
        title = self.current_note.get('title', 'Note')[:20]
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 5, title, 'white', 16)
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 5,
                    'E: Edit | ESC: Back', '#666666', 10, 'rt')
        
        # Content area
        content = self.current_note.get('content', '')
        lines = content.split('\n')
        
        line_height = 16
        start_y = self.ui.STATUS_BAR_HEIGHT + 30
        max_lines = (display.height - start_y - 10) // line_height
        
        # Apply scroll
        visible_lines = lines[self.scroll_offset:self.scroll_offset + max_lines]
        
        for i, line in enumerate(visible_lines):
            y = start_y + i * line_height
            # Truncate long lines
            display.text(10, y, line[:35], 'white', 12)
    
    def _draw_edit(self, display: Display):
        """Draw note editor."""
        # Title bar
        display.text(10, self.ui.STATUS_BAR_HEIGHT + 5, 'Editing', '#ffcc00', 14)
        display.text(display.width - 10, self.ui.STATUS_BAR_HEIGHT + 5,
                    'ESC: Save', '#666666', 10, 'rt')
        
        # Edit area background
        edit_y = self.ui.STATUS_BAR_HEIGHT + 25
        edit_h = display.height - edit_y - 5
        display.rect(5, edit_y, display.width - 10, edit_h,
                    fill='#1a1a1a', color='#333333')
        
        # Content with cursor
        lines = self.edit_buffer.split('\n')
        line_height = 16
        max_lines = (edit_h - 10) // line_height
        
        # Find cursor line
        cursor_line = 0
        pos = 0
        for i, line in enumerate(lines):
            if pos + len(line) >= self.cursor_pos:
                cursor_line = i
                break
            pos += len(line) + 1
        
        # Scroll to cursor
        start_line = max(0, cursor_line - max_lines + 2)
        
        for i, line in enumerate(lines[start_line:start_line + max_lines]):
            y = edit_y + 5 + i * line_height
            display.text(10, y, line[:32], 'white', 12)
            
            # Draw cursor
            actual_line = start_line + i
            if actual_line == cursor_line:
                # Calculate cursor position in line
                line_start = sum(len(l) + 1 for l in lines[:actual_line])
                cursor_in_line = self.cursor_pos - line_start
                cursor_x = 10 + cursor_in_line * 7
                display.line(cursor_x, y, cursor_x, y + line_height - 2, '#ffcc00')

