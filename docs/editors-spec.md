## Text & CSV Editor Specification

### Goals
- Provide lightweight, keyboard-friendly editing tools for TXT/Markdown-like prose and structured CSV data directly on the transparent OLED.
- Support BLE HID keyboards, partner ESP32 remote keypad, and on-device gestures for navigation.
- Persist documents on the microSD card with autosave snapshots, version tagging, and metadata for sync.

### Word/Text Processor
- **Document format**: UTF-8 plain text with optional front-matter metadata (`title`, `lang`, `revision`).
- **Editing model**: Rope buffer (for low RAM churn) with cursor + selection states. Undo stack limited to 32 actions to preserve memory.
- **Views**:
  - Draft view: full-screen text with line wrapping, adjustable font scale.
  - Focus view: highlights active sentence; dims rest for translation focus.
  - Translation overlay: displays bilingual translation of selected text via Translation task feed.
- **Input handling**:
  - Keyboard shortcuts for navigation (Emacs/Vim-inspired), macros triggered via partner ESP32 commands.
  - Gesture strip for vertical scroll/page.
  - Quick palette (Ctrl+Space) for commands (search, replace, jump to heading).
- **Storage**:
  - Autosave every 60 s or on context switch.
  - Versions stored as diff patches (binary delta) under `.meta/`.
  - Metadata index in JSON: `{ "path": "...", "title": "...", "lang": "...", "updated": 1732691123 }`.

### CSV Editor
- **Grid model**: sparse 2D structure with row/column virtualization to fit 128×64 display (miniature viewport).
- **Navigation**: arrow/WASD keys move cell; partner device can send macro commands (jump column, apply formula).
- **Editing**:
  - Inline edit overlay for cell (max 32 chars) with type hints (text, number, date).
  - Formula assist via phone companion: send selected range, compute summary, return condensed result.
- **Operations**:
  - Insert/delete rows, reorder columns, filter simple criteria (equals, contains).
  - Quick stats panel (min/max/avg/count) computed on-device for small ranges.
  - Export selected range to clipboard (BLE HID) or push to phone via BLE file channel.
- **Storage**:
  - Backed by CSV on SD; streaming parser to avoid loading entire file.
  - Snapshot-based undo (per 10 operations) with diff metadata.

### Shared Services
- **Document Manager** component handles SD IO, metadata index, autosave timers, and conflict detection.
- **UI Layer** receives render instructions from editor components (off-screen buffer with glyph caching).
- **Event Bus**:
  - `EDITOR_EVENT_INPUT`, `EDITOR_EVENT_SELECTION`, `EDITOR_EVENT_SAVE`.
  - `CONTROL_EVENT_MACRO` from partner device, routed through Control Link module.
- **Security**: Optional PIN-locked documents; encryption handled at Storage layer.

### Joystick Integration
- See `docs/joystick-control.md` for hardware + UX mapping.
- Control Link publishes `JoystickEvent` packets; editors subscribe via `text_editor_handle_joystick` and `csv_editor_handle_joystick`.
- Layer logic:
  - Layer 1 (`TEXT_EDITOR`): joystick axes map to cursor movement/scroll (accelerated).
  - Layer 2 (`CSV_EDITOR`): axes step through cells; button press toggles edit mode.
  - Layer 0/default: events broadcast to both editors for shared commands (e.g., document switch).
- Button gestures (double, long press) surface as macros that open palettes, switch modes, or trigger exports.

### Dependencies
- FreeRTOS + message queues for cross-task communication.
- SDMMC + FatFS for file operations; `esp_littlefs` optional for configs.
- Partner ESP32 control link (BLE) for remote macros and sensor-driven context.
