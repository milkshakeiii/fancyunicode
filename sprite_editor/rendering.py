"""
Sprite & Scene Editor - Rendering functions
"""

import pygame
import pyunicodegame
import random

try:
    from . import models
    from .models import (
        state,
        ROOT_WIDTH, ROOT_HEIGHT, STATUS_HEIGHT,
        DEFAULT_FG, COLOR_VISUAL, COLOR_CURSOR, COLOR_CURSOR_INSERT,
        COLOR_STATUS_DIM, COLOR_STATUS_BRIGHT, COLOR_COMMAND,
        PALETTE_CATEGORIES, CATEGORY_HOTKEYS, KEYBOARD_ROWS, KEY_TO_INDEX,
        RANDOM_UNICODE_RANGES,
        EditorMode, MODE_DISPLAY,
        get_all_library_sprites,
    )
except ImportError:
    import models
    from models import (
        state,
        ROOT_WIDTH, ROOT_HEIGHT, STATUS_HEIGHT,
        DEFAULT_FG, COLOR_VISUAL, COLOR_CURSOR, COLOR_CURSOR_INSERT,
        COLOR_STATUS_DIM, COLOR_STATUS_BRIGHT, COLOR_COMMAND,
        PALETTE_CATEGORIES, CATEGORY_HOTKEYS, KEYBOARD_ROWS, KEY_TO_INDEX,
        RANDOM_UNICODE_RANGES,
        EditorMode, MODE_DISPLAY,
        get_all_library_sprites,
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_vicinity_chars(center_codepoint: int, count: int = 40) -> list:
    """Get chars near a codepoint."""
    chars = []
    for offset in range(-count // 2, count // 2 + 1):
        cp = center_codepoint + offset
        if 0x20 <= cp <= 0x10FFFF and cp != center_codepoint:
            try:
                char = chr(cp)
                chars.append(char)
            except (ValueError, OverflowError):
                pass
    return chars[:count]


def get_random_char() -> str:
    """Get random character from interesting Unicode ranges."""
    for _ in range(100):  # Max attempts
        range_start, range_end = random.choice(RANDOM_UNICODE_RANGES)
        cp = random.randint(range_start, range_end)
        try:
            return chr(cp)
        except (ValueError, OverflowError):
            continue
    return '?'  # Fallback


# ============================================================================
# MAIN RENDERING
# ============================================================================

def render():
    """Main render function called each frame"""
    # Full-screen overlays take over everything
    if state.mode == EditorMode.HELP:
        render_help_overlay()
        return
    if state.mode == EditorMode.PALETTE_CATEGORIES:
        render_palette_categories()
        return
    if state.mode == EditorMode.PALETTE_QWERTY:
        render_palette_qwerty()
        return
    if state.mode == EditorMode.PALETTE_CODEPOINT:
        render_palette_codepoint()
        return
    if state.mode == EditorMode.ANIMATION_EDITOR:
        render_animation_editor()
        return
    if state.mode == EditorMode.ANIMATION_PREVIEW:
        render_animation_preview()
        return
    if state.mode == EditorMode.SPRITE_LIBRARY:
        render_sprite_library()
        return
    if state.mode == EditorMode.SPRITE_PICKER:
        render_sprite_picker()
        return

    # Draw border/frame on root window around sprite area
    render_sprite_frame()

    # Draw sprite content on sprite window
    render_canvas()

    # Draw UI on status window
    render_mini_palette()
    render_status_bar()
    if state.mode == EditorMode.COMMAND:
        render_command_line()


def render_sprite_frame():
    """Draw a frame around the sprite editing area on root window"""
    # Calculate sprite window position (centered in available space)
    avail_h = ROOT_HEIGHT - STATUS_HEIGHT
    sx = (ROOT_WIDTH - state.canvas_width) // 2 - 1
    sy = (avail_h - state.canvas_height) // 2 - 1

    # Draw box around sprite area
    box_w = state.canvas_width + 2
    box_h = state.canvas_height + 2
    frame_color = (60, 60, 80)

    # Top and bottom
    models.root.put_string(sx, sy, '┌' + '─' * state.canvas_width + '┐', frame_color)
    models.root.put_string(sx, sy + box_h - 1, '└' + '─' * state.canvas_width + '┘', frame_color)

    # Sides
    for y in range(1, box_h - 1):
        models.root.put(sx, sy + y, '│', frame_color)
        models.root.put(sx + box_w - 1, sy + y, '│', frame_color)


def render_canvas():
    """Render the canvas area with all cells and cursor on sprite window"""
    # Draw all cells
    for (x, y), cell in state.cells.items():
        # Check if in viewport
        vx = x - state.viewport_x
        vy = y - state.viewport_y
        if 0 <= vx < state.canvas_width and 0 <= vy < state.canvas_height:
            if cell.bg:
                # Draw background first
                models.sprite_win.put(vx, vy, '█', cell.bg)
            models.sprite_win.put(vx, vy, cell.char, cell.fg)

    # Draw cursor
    cx = state.cursor_x - state.viewport_x
    cy = state.cursor_y - state.viewport_y

    if 0 <= cx < state.canvas_width and 0 <= cy < state.canvas_height:
        if state.cursor_visible or state.mode == EditorMode.INSERT:
            # Get character under cursor
            cell = state.get_cell(state.cursor_x, state.cursor_y)
            char_under = cell.char if cell else ' '

            if state.mode == EditorMode.INSERT:
                # Block cursor in insert mode
                models.sprite_win.put(cx, cy, '█', COLOR_CURSOR_INSERT)
                if char_under != ' ':
                    models.sprite_win.put(cx, cy, char_under, (0, 0, 0))
            else:
                # Underline-style cursor in normal mode
                models.sprite_win.put(cx, cy, '▁', COLOR_CURSOR)

    # Sprites are rendered by pyunicodegame via models.root.update_sprites()
    # We don't need to manually render them here anymore

    # Draw selection highlight in VISUAL mode
    if state.mode == EditorMode.VISUAL and state.selection_start:
        sx, sy = state.selection_start
        min_x = min(sx, state.cursor_x)
        max_x = max(sx, state.cursor_x)
        min_y = min(sy, state.cursor_y)
        max_y = max(sy, state.cursor_y)

        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                vx = x - state.viewport_x
                vy = y - state.viewport_y
                if 0 <= vx < state.canvas_width and 0 <= vy < state.canvas_height:
                    cell = state.get_cell(x, y)
                    char = cell.char if cell else ' '
                    # Highlight with inverted colors
                    models.sprite_win.put(vx, vy, char if char != ' ' else '░', COLOR_VISUAL)


def render_mini_palette():
    """Render the mini palette bar above status on status window"""
    palette_row = 0  # First row of status window
    w = ROOT_WIDTH

    # Show recent chars (1-9 to select)
    recent = state.recent_chars[:9]
    if recent:
        preview = ''.join(recent)
        models.status_win.put_string(1, palette_row, "Recent:", COLOR_STATUS_DIM)
        models.status_win.put_string(9, palette_row, preview, state.current_fg)
    else:
        models.status_win.put_string(1, palette_row, "(no recent chars)", COLOR_STATUS_DIM)

    # Show hint with codepoint on right side
    code = ord(state.current_char)
    hint = f"U+{code:04X} [p]alette"
    models.status_win.put_string(w - len(hint) - 1, palette_row, hint, (80, 80, 100))


def render_status_bar():
    """Render the status bar on status window"""
    status_row = 1  # Second row of status window (after mini palette)
    w = ROOT_WIDTH

    # Editor mode indicator (SPRITE or SCENE)
    if state.editor_mode == "sprite":
        editor_mode_text = "SPRITE"
        editor_mode_color = (100, 200, 255)
    else:
        # Scene mode - show tool indicator
        if state.scene_tool == "sprite":
            tool_name = state.selected_library_sprite.split(':')[1] if state.selected_library_sprite else "?"
            editor_mode_text = f"SCENE[{tool_name}]"
        else:
            editor_mode_text = "SCENE[char]"
        editor_mode_color = (200, 255, 100)
    models.status_win.put_string(0, status_row, editor_mode_text, editor_mode_color)

    # Vim mode indicator - position after editor mode text
    mode_text, mode_color = MODE_DISPLAY[state.mode]
    mode_pos = len(editor_mode_text) + 1
    models.status_win.put_string(mode_pos, status_row, mode_text, mode_color)

    # Position
    pos_text = f"{state.cursor_x},{state.cursor_y}"
    pos_x = max(22, mode_pos + len(mode_text) + 1)
    models.status_win.put_string(pos_x, status_row, pos_text, COLOR_STATUS_DIM)

    # Frame info (sprite mode only)
    if state.editor_mode == "sprite" and len(state.frames) > 1:
        frame_text = f"F{state.current_frame + 1}/{len(state.frames)}"
        if state.animation_playing:
            if state.current_animation:
                frame_text = f"[{state.current_animation}] {frame_text} ▶"
            else:
                frame_text = f"{frame_text} ▶"
            models.status_win.put_string(30, status_row, frame_text, (100, 255, 100))
        else:
            models.status_win.put_string(30, status_row, frame_text, (150, 150, 200))

    # Current character with color indicator (adjust position based on frame text)
    char_pos = 50 if state.animation_playing and state.current_animation else 40 if len(state.frames) > 1 else 32
    models.status_win.put(char_pos, status_row, state.current_char, state.current_fg)

    # Sprite name or file path (right-aligned, leave room for char display)
    if state.editor_mode == "sprite":
        name_text = f"{state.sprite_name} {state.canvas_width}x{state.canvas_height}"
    else:
        name_text = state.file_path if state.file_path else "[untitled]"

    if state.modified:
        name_text += "[+]"

    # Right-align name
    name_x = w - len(name_text) - 1
    models.status_win.put_string(name_x, status_row, name_text, COLOR_STATUS_DIM)

    # Status message (temporary) - on next row
    if state.status_message and state.status_message_time > 0:
        msg_x = (w - len(state.status_message)) // 2
        models.status_win.put_string(msg_x, status_row + 1, state.status_message, COLOR_STATUS_BRIGHT)


def render_command_line():
    """Render the command line input on status window"""
    cmd_row = 2  # Third row of status window
    w = ROOT_WIDTH

    # Draw prompt and buffer
    prompt = ":"
    models.status_win.put_string(0, cmd_row, prompt + state.command_buffer, COLOR_COMMAND)

    # Cursor at end of input
    cursor_x = len(prompt) + len(state.command_buffer)
    models.status_win.put(cursor_x, cmd_row, '█', COLOR_COMMAND)


# ============================================================================
# PALETTE SCREENS
# ============================================================================

def render_palette_categories():
    """Render the category selection screen (Screen 1)"""
    # Hide other windows during palette
    models.sprite_win.visible = False
    models.status_win.visible = False

    w, h = ROOT_WIDTH, ROOT_HEIGHT
    title_color = (100, 200, 255)
    heading_color = (255, 200, 100)
    selected_color = (100, 255, 100)
    normal_color = (180, 180, 180)
    preview_color = (150, 150, 200)
    hotkey_color = (200, 200, 100)

    # Background
    for y in range(h):
        for x in range(w):
            models.root.put(x, y, ' ', (20, 20, 30))

    # Title
    title = "CHARACTER PALETTE"
    models.root.put_string((w - len(title)) // 2, 1, title, title_color)
    models.root.put_string(0, 2, "═" * w, (60, 60, 80))

    # Update dynamic categories
    PALETTE_CATEGORIES[0] = ('Recent', state.recent_chars[:40])

    # Clamp category to valid range
    if state.palette_category < 0:
        state.palette_category = 0
    elif state.palette_category >= len(PALETTE_CATEGORIES):
        state.palette_category = len(PALETTE_CATEGORIES) - 1

    # Calculate visible range for scrolling
    # y starts at 4, breaks at h-6, so actual visible = h - 10
    visible_rows = h - 10
    max_scroll = max(0, len(PALETTE_CATEGORIES) - visible_rows)
    scroll_offset = max(0, min(state.palette_category - visible_rows // 2, max_scroll))

    # Draw categories with hotkeys
    y = 4
    for i in range(scroll_offset, min(scroll_offset + visible_rows, len(PALETTE_CATEGORIES))):
        if y >= h - 6:
            break
        cat_name, cat_chars = PALETTE_CATEGORIES[i]
        is_selected = (i == state.palette_category)

        # Hotkey prefix
        hotkey = CATEGORY_HOTKEYS[i] if i < len(CATEGORY_HOTKEYS) else '?'
        models.root.put_string(2, y, f"{hotkey}-", hotkey_color)

        # Selection indicator
        if is_selected:
            models.root.put(5, y, '▶', selected_color)
            name_color = selected_color
        else:
            name_color = normal_color

        # Category name
        models.root.put_string(7, y, cat_name[:12].ljust(12), name_color)

        # Preview chars (first 18)
        preview = ''.join(cat_chars[:18]) if cat_chars else "(empty)"
        models.root.put_string(20, y, preview[:36], preview_color)

        y += 1

    # Special options row (fixed position above footer)
    special_y = h - 4
    models.root.put_string(2, special_y, "─" * 54, (60, 60, 80))
    special_y += 1

    # Vicinity option
    models.root.put_string(2, special_y, "[v]icinity", heading_color)

    # Random and Codepoint on same line
    models.root.put_string(24, special_y, "[r]andom", heading_color)
    models.root.put_string(36, special_y, "[u] U+codepoint", heading_color)

    # Footer
    models.root.put_string(0, h - 2, "═" * w, (60, 60, 80))
    footer = "j/k =/- hotkey  Enter:select  Esc:cancel"
    models.root.put_string((w - len(footer)) // 2, h - 1, footer, (100, 100, 120))


def render_palette_qwerty():
    """Render the QWERTY keyboard picker (Screen 2)"""
    # Hide other windows
    models.sprite_win.visible = False
    models.status_win.visible = False

    w, h = ROOT_WIDTH, ROOT_HEIGHT
    title_color = (100, 200, 255)
    key_color = (80, 80, 100)
    char_color = (200, 200, 255)
    empty_color = (50, 50, 60)

    # Background
    for y in range(h):
        for x in range(w):
            models.root.put(x, y, ' ', (20, 20, 30))

    # Get current category (special handling for vicinity mode)
    if state.palette_category == -1:  # Vicinity mode
        cat_name = "Vicinity"
        cat_chars = generate_vicinity_chars(state.last_selected_codepoint, 80)
    else:
        cat_name, cat_chars = PALETTE_CATEGORIES[state.palette_category]

    # Check if shift is held to show extended range
    shift_held = pygame.key.get_mods() & pygame.KMOD_SHIFT
    char_offset = 40 if shift_held and len(cat_chars) > 40 else 0

    # Title
    if shift_held and len(cat_chars) > 40:
        title = f"{cat_name} ({len(cat_chars)} chars) [SHIFT: 41-{min(80, len(cat_chars))}]"
    else:
        title = f"{cat_name} ({len(cat_chars)} chars)"
    models.root.put_string(2, 1, title, title_color)
    models.root.put_string(w - 6, 1, "[Esc]", (100, 100, 120))
    models.root.put_string(0, 2, "═" * w, (60, 60, 80))

    # Draw QWERTY keyboard layout
    # Each key cell is 4 chars wide: "│ X │"
    cell_width = 4
    start_y = 4
    char_idx = char_offset

    row_offsets = [4, 5, 6, 7]  # Indent for each row

    for row_idx, row in enumerate(KEYBOARD_ROWS):
        x = row_offsets[row_idx]
        y = start_y + row_idx * 3

        for key in row:
            # Get character for this position
            char = cat_chars[char_idx] if char_idx < len(cat_chars) else None

            # Draw key label (small, above)
            models.root.put(x + 1, y, key, key_color)

            # Draw character (centered)
            if char:
                models.root.put(x + 1, y + 1, char, char_color)
            else:
                models.root.put(x + 1, y + 1, '·', empty_color)

            char_idx += 1
            x += cell_width

    # Show shift hint if more chars available
    if len(cat_chars) > 40:
        if shift_held:
            shift_hint = "Release Shift for chars 1-40"
        else:
            shift_hint = f"Hold Shift for chars 41-{min(80, len(cat_chars))}"
        models.root.put_string(4, start_y + 13, shift_hint, (150, 150, 180))

    # Current character info
    info_y = h - 4
    models.root.put_string(4, info_y, f"Current: {state.current_char}", (150, 200, 150))
    code = ord(state.current_char)
    models.root.put_string(20, info_y, f"U+{code:04X}", (120, 120, 140))

    # Footer
    models.root.put_string(0, h - 2, "═" * w, (60, 60, 80))
    footer = "Press key to select   Hold Shift for more   Esc:back"
    models.root.put_string((w - len(footer)) // 2, h - 1, footer, (100, 100, 120))


def render_palette_codepoint():
    """Render the codepoint entry screen"""
    # Hide other windows
    models.sprite_win.visible = False
    models.status_win.visible = False

    w, h = ROOT_WIDTH, ROOT_HEIGHT
    title_color = (100, 200, 255)

    # Background
    for y in range(h):
        for x in range(w):
            models.root.put(x, y, ' ', (20, 20, 30))

    # Title
    title = "ENTER CODEPOINT"
    models.root.put_string((w - len(title)) // 2, 1, title, title_color)
    models.root.put_string(0, 2, "═" * w, (60, 60, 80))

    # Input prompt
    prompt_y = h // 2 - 2
    models.root.put_string(10, prompt_y, "Enter hex codepoint:", (180, 180, 180))

    # Input field
    input_y = prompt_y + 2
    models.root.put_string(10, input_y, "U+", (150, 150, 200))
    models.root.put_string(12, input_y, state.codepoint_buffer.upper().ljust(6, '_'), (100, 255, 100))
    models.root.put(12 + len(state.codepoint_buffer), input_y, '█', (100, 255, 100))

    # Preview character if valid
    if state.codepoint_buffer:
        try:
            cp = int(state.codepoint_buffer, 16)
            if 0x20 <= cp <= 0x10FFFF:
                char = chr(cp)
                models.root.put_string(10, input_y + 2, "Preview: ", (150, 150, 180))
                models.root.put(19, input_y + 2, char, (200, 200, 255))
        except (ValueError, OverflowError):
            models.root.put_string(10, input_y + 2, "Invalid codepoint", (255, 100, 100))

    # Footer
    models.root.put_string(0, h - 2, "═" * w, (60, 60, 80))
    footer = "0-9, a-f: type   Enter: select   Esc: cancel"
    models.root.put_string((w - len(footer)) // 2, h - 1, footer, (100, 100, 120))


# ============================================================================
# HELP OVERLAY
# ============================================================================

def render_help_overlay():
    """Render full-screen help overlay with pagination"""
    # Hide other windows during help
    models.sprite_win.visible = False
    models.status_win.visible = False

    w, h = ROOT_WIDTH, ROOT_HEIGHT
    title_color = (100, 200, 255)
    heading_color = (255, 200, 100)
    key_color = (100, 255, 100)
    desc_color = (180, 180, 180)
    dim_color = (100, 100, 120)

    # Background
    for y in range(h):
        for x in range(w):
            models.root.put(x, y, ' ', (30, 30, 40))

    # Title with page indicator
    total_pages = 2
    page_num = state.help_page + 1
    if state.help_page == 0:
        title = "HELP - GENERAL"
    else:
        title = "HELP - SCENE MODE"
    models.root.put_string((w - len(title)) // 2, 1, title, title_color)

    # Page indicator
    page_ind = f"[{page_num}/{total_pages}]"
    models.root.put_string(w - len(page_ind) - 1, 1, page_ind, dim_color)

    models.root.put_string(0, 2, "═" * w, (60, 60, 80))

    if state.help_page == 0:
        # PAGE 1: General controls (left column ends before 31)
        y = 4
        models.root.put_string(2, y, "NAVIGATION", heading_color); y += 1
        models.root.put_string(4, y, "hjkl", key_color); models.root.put_string(12, y, "Move cursor", desc_color); y += 1
        models.root.put_string(4, y, "0 / $", key_color); models.root.put_string(12, y, "Line start/end", desc_color); y += 1
        models.root.put_string(4, y, "gg / G", key_color); models.root.put_string(12, y, "Top/bottom", desc_color); y += 2

        models.root.put_string(2, y, "DRAWING", heading_color); y += 1
        models.root.put_string(4, y, "Space", key_color); models.root.put_string(12, y, "Stamp char", desc_color); y += 1
        models.root.put_string(4, y, "i", key_color); models.root.put_string(12, y, "Insert mode", desc_color); y += 1
        models.root.put_string(4, y, "x", key_color); models.root.put_string(12, y, "Delete char", desc_color); y += 1
        models.root.put_string(4, y, "c", key_color); models.root.put_string(12, y, "Pick char under", desc_color); y += 1
        models.root.put_string(4, y, "C", key_color); models.root.put_string(12, y, "Pick color under", desc_color); y += 1
        models.root.put_string(4, y, "f", key_color); models.root.put_string(12, y, "Cycle FG color", desc_color); y += 2

        models.root.put_string(2, y, "ANIMATION", heading_color); y += 1
        models.root.put_string(4, y, ", .", key_color); models.root.put_string(12, y, "Prev/next frame", desc_color); y += 1
        models.root.put_string(4, y, "Tab", key_color); models.root.put_string(12, y, "Play/stop", desc_color); y += 1

        # Right column starts at 31
        y2 = 4
        models.root.put_string(31, y2, "PALETTE (p)", heading_color); y2 += 1
        models.root.put_string(33, y2, "j/k", key_color); models.root.put_string(41, y2, "Navigate", desc_color); y2 += 1
        models.root.put_string(33, y2, "Enter", key_color); models.root.put_string(41, y2, "QWERTY mode", desc_color); y2 += 1
        models.root.put_string(33, y2, "r", key_color); models.root.put_string(41, y2, "Random char", desc_color); y2 += 1
        models.root.put_string(33, y2, "u", key_color); models.root.put_string(41, y2, "Codepoint", desc_color); y2 += 2

        models.root.put_string(31, y2, "VISUAL MODE (v)", heading_color); y2 += 1
        models.root.put_string(33, y2, "y", key_color); models.root.put_string(41, y2, "Yank", desc_color); y2 += 1
        models.root.put_string(33, y2, "d", key_color); models.root.put_string(41, y2, "Delete", desc_color); y2 += 1
        models.root.put_string(33, y2, "r", key_color); models.root.put_string(41, y2, "Fill", desc_color); y2 += 1
        models.root.put_string(33, y2, "P", key_color); models.root.put_string(41, y2, "Paste", desc_color); y2 += 2

        models.root.put_string(31, y2, "COMMANDS", heading_color); y2 += 1
        models.root.put_string(33, y2, ":sprite", key_color); models.root.put_string(42, y2, "New sprite", desc_color); y2 += 1
        models.root.put_string(33, y2, ":w :q", key_color); models.root.put_string(42, y2, "Save/quit", desc_color); y2 += 1
        models.root.put_string(33, y2, ":frame", key_color); models.root.put_string(42, y2, "Add frame", desc_color); y2 += 1
        models.root.put_string(33, y2, ":anim", key_color); models.root.put_string(42, y2, "Anim editor", desc_color); y2 += 1

    else:
        # PAGE 2: Scene mode (left column ends before 31)
        y = 4
        models.root.put_string(2, y, "SCENE KEYS", heading_color); y += 1
        models.root.put_string(4, y, "t", key_color); models.root.put_string(12, y, "Toggle tool", desc_color); y += 1
        models.root.put_string(4, y, "S", key_color); models.root.put_string(12, y, "Sprite picker", desc_color); y += 1
        models.root.put_string(4, y, "I", key_color); models.root.put_string(12, y, "Library mgr", desc_color); y += 1
        models.root.put_string(4, y, "D", key_color); models.root.put_string(12, y, "Delete sprite", desc_color); y += 1
        models.root.put_string(4, y, "a", key_color); models.root.put_string(12, y, "Cycle anim", desc_color); y += 1
        models.root.put_string(4, y, "Space", key_color); models.root.put_string(12, y, "Place", desc_color); y += 2

        models.root.put_string(2, y, "SCENE COMMANDS", heading_color); y += 1
        models.root.put_string(4, y, ":scene WxH", key_color); y += 1
        models.root.put_string(4, y, ":import path", key_color); y += 1
        models.root.put_string(4, y, ":unimport path", key_color); y += 1
        models.root.put_string(4, y, ":library", key_color); y += 1
        models.root.put_string(4, y, ":tool char|sprite", key_color); y += 1

        # Right column starts at 31
        y2 = 4
        models.root.put_string(31, y2, "SPRITE PICKER", heading_color); y2 += 1
        models.root.put_string(33, y2, "hjkl", key_color); models.root.put_string(41, y2, "Navigate", desc_color); y2 += 1
        models.root.put_string(33, y2, "Enter", key_color); models.root.put_string(41, y2, "Select", desc_color); y2 += 1
        models.root.put_string(33, y2, "Esc", key_color); models.root.put_string(41, y2, "Cancel", desc_color); y2 += 2

        models.root.put_string(31, y2, "LIBRARY MANAGER", heading_color); y2 += 1
        models.root.put_string(33, y2, "j/k", key_color); models.root.put_string(41, y2, "Navigate", desc_color); y2 += 1
        models.root.put_string(33, y2, "d", key_color); models.root.put_string(41, y2, "Unload", desc_color); y2 += 1
        models.root.put_string(33, y2, "Esc", key_color); models.root.put_string(41, y2, "Close", desc_color); y2 += 2

        models.root.put_string(31, y2, "WORKFLOW", heading_color); y2 += 1
        models.root.put_string(33, y2, "1.", dim_color); models.root.put_string(36, y2, ":scene 40x30", desc_color); y2 += 1
        models.root.put_string(33, y2, "2.", dim_color); models.root.put_string(36, y2, ":import file.py", desc_color); y2 += 1
        models.root.put_string(33, y2, "3.", dim_color); models.root.put_string(36, y2, "S pick, Space", desc_color); y2 += 1
        models.root.put_string(33, y2, "4.", dim_color); models.root.put_string(36, y2, ":w level.py", desc_color); y2 += 1

    # Footer
    models.root.put_string(0, h - 2, "═" * w, (60, 60, 80))
    footer = "←/→ or h/l: switch page  |  Esc/Enter: close"
    models.root.put_string((w - len(footer)) // 2, h - 1, footer, (150, 150, 150))


# ============================================================================
# ANIMATION EDITOR & PREVIEW
# ============================================================================

def render_animation_editor():
    """Render full-screen animation assembly editor"""
    # Hide other windows during animation editor
    models.sprite_win.visible = False
    models.status_win.visible = False

    w, h = ROOT_WIDTH, ROOT_HEIGHT
    title_color = (255, 150, 50)
    heading_color = (255, 200, 100)
    selected_color = (100, 255, 100)
    normal_color = (180, 180, 180)
    dim_color = (100, 100, 120)

    # Background
    for y in range(h):
        for x in range(w):
            models.root.put(x, y, ' ', (30, 30, 40))

    # Title
    title = "ANIMATION EDITOR"
    models.root.put_string((w - len(title)) // 2, 1, title, title_color)
    models.root.put_string(0, 2, "═" * w, (60, 60, 80))

    # Get list of animations
    anim_names = sorted(state.animations.keys()) if state.animations else []

    if state.anim_editor_mode == "list":
        # Left side: Animation list
        models.root.put_string(2, 4, "ANIMATIONS", heading_color)
        models.root.put_string(2, 5, "─" * 20, dim_color)

        if not anim_names:
            models.root.put_string(2, 7, "(no animations)", dim_color)
            models.root.put_string(2, 8, "Press 'n' to create", dim_color)
        else:
            for i, name in enumerate(anim_names):
                y = 7 + i
                if y >= h - 4:
                    break
                anim = state.animations[name]
                is_selected = i == state.anim_editor_cursor
                color = selected_color if is_selected else normal_color
                prefix = ">" if is_selected else " "
                frame_count = len(anim.frames)
                loop_indicator = "⟳" if anim.loop else "→"
                models.root.put_string(2, y, f"{prefix} {name}", color)
                models.root.put_string(20, y, f"{frame_count}f {loop_indicator}", dim_color)

        # Right side: Selected animation details
        models.root.put_string(32, 4, "DETAILS", heading_color)
        models.root.put_string(32, 5, "─" * 25, dim_color)

        if anim_names and 0 <= state.anim_editor_cursor < len(anim_names):
            anim_name = anim_names[state.anim_editor_cursor]
            anim = state.animations[anim_name]
            models.root.put_string(32, 7, f"Name: {anim_name}", normal_color)
            models.root.put_string(32, 8, f"Duration: {anim.frame_duration:.2f}s/frame", normal_color)
            models.root.put_string(32, 9, f"Loop: {'Yes' if anim.loop else 'No'}", normal_color)
            models.root.put_string(32, 10, f"Frames: {len(anim.frames)}", normal_color)

            # Show frame sequence
            models.root.put_string(32, 12, "Sequence:", heading_color)
            seq = " ".join(f"F{af.frame_index+1}" + (f"({af.offset_x},{af.offset_y})" if af.offset_x or af.offset_y else "")
                         for af in anim.frames[:8])
            if len(anim.frames) > 8:
                seq += "..."
            models.root.put_string(32, 13, seq[:26], dim_color)
        else:
            models.root.put_string(32, 7, "(select an animation)", dim_color)

    else:  # edit mode
        # Show frame editing for selected animation
        if anim_names and 0 <= state.anim_editor_cursor < len(anim_names):
            anim_name = anim_names[state.anim_editor_cursor]
            anim = state.animations[anim_name]

            models.root.put_string(2, 4, f"EDITING: {anim_name}", heading_color)
            # Show duration and loop status
            models.root.put_string(25, 4, f"{anim.frame_duration:.2f}s/frame", normal_color)
            models.root.put_string(45, 4, f"Loop: {'ON' if anim.loop else 'OFF'}", selected_color if anim.loop else dim_color)
            models.root.put_string(2, 5, "─" * 56, dim_color)

            # Show frames in animation
            models.root.put_string(2, 7, "FRAMES IN ANIMATION", heading_color)
            models.root.put_string(2, 8, "Frame   Offset", dim_color)
            if not anim.frames:
                models.root.put_string(2, 10, "(empty - press 1-9 to add frames)", dim_color)
            for i, af in enumerate(anim.frames):
                y = 10 + i
                if y >= h - 6:
                    break
                is_selected = i == state.anim_editor_frame_cursor
                color = selected_color if is_selected else normal_color
                prefix = ">" if is_selected else " "
                offset_str = f"({af.offset_x:+d},{af.offset_y:+d})"
                models.root.put_string(2, y, f"{prefix} F{af.frame_index + 1}", color)
                models.root.put_string(10, y, offset_str, color)

            # Show available sprite frames on right
            models.root.put_string(32, 7, f"SPRITE FRAMES (1-{min(len(state.frames), 9)})", heading_color)
            for i in range(min(len(state.frames), 9)):
                marker = "+" if any(af.frame_index == i for af in anim.frames) else " "
                models.root.put_string(32, 9 + i, f"{marker} {i+1}: Frame {i + 1}", dim_color)

    # Controls at bottom
    models.root.put_string(0, h - 5, "═" * w, (60, 60, 80))
    if state.anim_editor_mode == "list":
        models.root.put_string(2, h - 4, "j/k:Navigate  n:New  Enter:Edit  d:Delete  Space:Preview  Esc:Close", dim_color)
    else:
        models.root.put_string(2, h - 4, "1-9:Add frame  a:Add current  d:Remove  j/k:Select  [/]:Reorder", dim_color)
        models.root.put_string(2, h - 3, "h/l:X offset  J/K:Y offset (shift)  0:Reset offset", dim_color)
        models.root.put_string(2, h - 2, "+/-:Duration  L:Loop toggle  Space:Preview  Esc:Back", dim_color)


def start_animation_preview():
    """Create real pyunicodegame sprite for animation preview"""
    if not state.current_animation or state.current_animation not in state.animations:
        return

    anim_def = state.animations[state.current_animation]
    if not anim_def.frames:
        return

    # Convert our frames to pyunicodegame SpriteFrame objects
    pug_frames = []
    for our_frame in state.frames:
        # Build 2D char and color arrays
        chars = []
        fg_colors = []
        for y in range(state.canvas_height):
            char_row = []
            color_row = []
            for x in range(state.canvas_width):
                cell = our_frame.cells.get((x, y))
                if cell:
                    char_row.append(cell.char)
                    color_row.append(cell.fg)
                else:
                    char_row.append(' ')
                    color_row.append(None)
            chars.append(char_row)
            fg_colors.append(color_row)

        pug_frame = pyunicodegame.SpriteFrame(chars, fg_colors)
        pug_frames.append(pug_frame)

    # Create the sprite
    models.preview_sprite = pyunicodegame.Sprite(pug_frames, fg=DEFAULT_FG)

    # Center it on screen
    center_x = (ROOT_WIDTH - state.canvas_width) // 2
    center_y = (ROOT_HEIGHT - state.canvas_height) // 2
    models.preview_sprite.x = center_x
    models.preview_sprite.y = center_y
    models.preview_sprite._teleport_pending = True

    # Build animation from our AnimationDef
    frame_indices = [af.frame_index for af in anim_def.frames]
    offsets = [(float(af.offset_x), float(af.offset_y)) for af in anim_def.frames]

    pug_anim = pyunicodegame.Animation(
        name=anim_def.name,
        frame_indices=frame_indices,
        frame_duration=anim_def.frame_duration,
        offsets=offsets,
        loop=anim_def.loop,
        offset_speed=50.0  # Smooth interpolation for offsets
    )
    models.preview_sprite.add_animation(pug_anim)
    models.preview_sprite.play_animation(anim_def.name)

    # Add to root window for rendering
    models.root.add_sprite(models.preview_sprite)


def stop_animation_preview():
    """Clean up animation preview sprite"""
    if models.preview_sprite and models.root:
        models.root.remove_sprite(models.preview_sprite)
        models.preview_sprite = None


def render_animation_preview():
    """Render full-screen animation preview using real pyunicodegame sprite"""
    models.sprite_win.visible = False
    models.status_win.visible = False

    w, h = ROOT_WIDTH, ROOT_HEIGHT

    # Clear background - the sprite will render on top automatically
    for y in range(h):
        for x in range(w):
            models.root.put(x, y, ' ', (20, 20, 30))

    # Show help at bottom
    help_text = "Press Space/Esc/Q to exit preview"
    models.root.put_string((w - len(help_text)) // 2, h - 1, help_text, (100, 100, 120))


# ============================================================================
# SPRITE LIBRARY & PICKER
# ============================================================================

def render_sprite_library():
    """Render full-screen sprite library manager"""
    models.sprite_win.visible = False
    models.status_win.visible = False

    w, h = ROOT_WIDTH, ROOT_HEIGHT
    title_color = (100, 200, 255)
    heading_color = (150, 220, 255)
    selected_color = (100, 255, 100)
    normal_color = (180, 180, 180)
    dim_color = (100, 100, 120)

    # Background
    for y in range(h):
        for x in range(w):
            models.root.put(x, y, ' ', (25, 30, 40))

    # Title
    title = "SPRITE LIBRARY"
    models.root.put_string((w - len(title)) // 2, 1, title, title_color)
    models.root.put_string(0, 2, "═" * w, (60, 60, 80))

    # Get list of loaded libraries
    lib_paths = sorted(state.sprite_library.keys())

    if not lib_paths:
        models.root.put_string(2, 5, "(no sprite files loaded)", dim_color)
        models.root.put_string(2, 7, "Use :import <file.py> to load sprites", dim_color)
    else:
        models.root.put_string(2, 4, "LOADED FILES", heading_color)
        models.root.put_string(2, 5, "─" * 40, dim_color)

        y = 7
        for i, lib_path in enumerate(lib_paths):
            if y >= h - 5:
                break

            entry = state.sprite_library[lib_path]
            is_selected = i == state.sprite_library_cursor
            color = selected_color if is_selected else normal_color
            prefix = ">" if is_selected else " "

            models.root.put_string(2, y, f"{prefix} {lib_path}", color)
            y += 1

            # Show sprite names in this library
            for sprite_name in entry.sprite_names[:5]:  # Limit display
                if y >= h - 5:
                    break
                sprite_def = entry.sprite_defs.get(sprite_name, {})
                sw = sprite_def.get('width', '?')
                sh = sprite_def.get('height', '?')
                nf = len(sprite_def.get('frames', []))
                models.root.put_string(6, y, f"• {sprite_name} ({sw}x{sh}, {nf}f)", dim_color)
                y += 1

            if len(entry.sprite_names) > 5:
                models.root.put_string(6, y, f"  ... and {len(entry.sprite_names) - 5} more", dim_color)
                y += 1

            y += 1  # Spacing between libraries

    # Controls at bottom
    models.root.put_string(0, h - 4, "═" * w, (60, 60, 80))
    models.root.put_string(2, h - 3, "j/k:Navigate  d:Unload  n:Import new  Esc:Close", dim_color)
    models.root.put_string(2, h - 2, f"Loaded: {len(lib_paths)} files, {len(get_all_library_sprites())} sprites", dim_color)


def render_sprite_picker():
    """Render sprite picker grid for placement"""
    models.sprite_win.visible = False
    models.status_win.visible = False

    w, h = ROOT_WIDTH, ROOT_HEIGHT
    title_color = (255, 200, 100)
    selected_color = (100, 255, 100)
    normal_color = (180, 180, 180)
    dim_color = (100, 100, 120)

    # Background
    for y in range(h):
        for x in range(w):
            models.root.put(x, y, ' ', (30, 30, 35))

    # Title
    title = "SELECT SPRITE"
    models.root.put_string((w - len(title)) // 2, 1, title, title_color)
    models.root.put_string(0, 2, "═" * w, (60, 60, 80))

    # Get all sprites
    all_sprites = get_all_library_sprites()

    if not all_sprites:
        models.root.put_string(2, 5, "(no sprites available)", dim_color)
        models.root.put_string(2, 7, "Use :import <file.py> to load sprites", dim_color)
    else:
        # Display as a grid
        cols = 4
        cell_width = 14
        start_y = 4

        for i, (library_key, sprite_name, sprite_def) in enumerate(all_sprites):
            if start_y + (i // cols) * 4 >= h - 5:
                break

            col = i % cols
            row = i // cols
            x = 2 + col * cell_width
            y = start_y + row * 4

            is_selected = i == state.sprite_picker_cursor
            color = selected_color if is_selected else normal_color

            # Draw selection box
            if is_selected:
                models.root.put_string(x, y, "┌" + "─" * 10 + "┐", selected_color)
                models.root.put_string(x, y + 2, "└" + "─" * 10 + "┘", selected_color)
                models.root.put(x, y + 1, "│", selected_color)
                models.root.put(x + 11, y + 1, "│", selected_color)

            # Show first char of sprite as preview
            first_frame = sprite_def.get('frames', [{}])[0]
            chars = first_frame.get('chars', [[]])
            if chars and chars[0]:
                preview_char = chars[0][0] if chars[0][0] != ' ' else '?'
            else:
                preview_char = '?'

            models.root.put(x + 5, y + 1, preview_char, color)

            # Sprite name (truncated)
            name_display = sprite_name[:10]
            models.root.put_string(x + 1, y + 3, name_display, dim_color if not is_selected else normal_color)

    # Controls at bottom
    models.root.put_string(0, h - 4, "═" * w, (60, 60, 80))
    models.root.put_string(2, h - 3, "hjkl:Navigate  Enter:Select  Esc:Cancel", dim_color)
    if all_sprites and 0 <= state.sprite_picker_cursor < len(all_sprites):
        lib_key, name, _ = all_sprites[state.sprite_picker_cursor]
        models.root.put_string(2, h - 2, f"Selected: {name} from {lib_key.split(':')[0]}", normal_color)
