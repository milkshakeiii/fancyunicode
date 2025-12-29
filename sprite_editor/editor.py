#!/usr/bin/env python3
"""
Sprite & Scene Editor - A vim-like TUI editor for pyunicodegame

Two modes:
  SPRITE MODE - Create reusable sprite assets (characters, objects)
  SCENE MODE  - Compose scenes by placing sprites and static characters

Controls:
    NORMAL mode:  hjkl/arrows to move, i for insert, : for commands
    INSERT mode:  Type to place characters, Esc to return to NORMAL
    VISUAL mode:  v to start, hjkl to extend, y yank, d delete, r fill
    COMMAND mode: :w save, :q quit, :sprite name WxH, :scene WxH

    Exit modes:   Esc or Ctrl+[
"""

import pygame
import pyunicodegame
import unicodedata
import sys
import re
import os
from typing import Optional, List, Tuple

try:
    from . import models
    from .models import (
        state,
        ROOT_WIDTH, ROOT_HEIGHT, STATUS_HEIGHT,
        DEFAULT_CANVAS_WIDTH, DEFAULT_CANVAS_HEIGHT,
        DEFAULT_FG, CURSOR_BLINK_RATE,
        COLOR_PALETTE_FG, PALETTE_CATEGORIES, CATEGORY_HOTKEYS, KEY_TO_INDEX,
        EditorMode, Cell, SpriteFrame, AnimationFrame, AnimationDef,
        SpriteLibraryEntry, SpriteInstance,
        get_current_category_chars, get_all_library_sprites,
    )
    from .rendering import (
        render, generate_vicinity_chars, get_random_char,
        start_animation_preview, stop_animation_preview,
    )
    from .file_io import save_file, load_file, GENERATED_DIR
except ImportError:
    import models
    from models import (
        state,
        ROOT_WIDTH, ROOT_HEIGHT, STATUS_HEIGHT,
        DEFAULT_CANVAS_WIDTH, DEFAULT_CANVAS_HEIGHT,
        DEFAULT_FG, CURSOR_BLINK_RATE,
        COLOR_PALETTE_FG, PALETTE_CATEGORIES, CATEGORY_HOTKEYS, KEY_TO_INDEX,
        EditorMode, Cell, SpriteFrame, AnimationFrame, AnimationDef,
        SpriteLibraryEntry, SpriteInstance,
        get_current_category_chars, get_all_library_sprites,
    )
    from rendering import (
        render, generate_vicinity_chars, get_random_char,
        start_animation_preview, stop_animation_preview,
    )
    from file_io import save_file, load_file, GENERATED_DIR


# ============================================================================
# INPUT HANDLING
# ============================================================================

def on_key(key):
    """Handle keyboard input based on current mode"""
    if state.mode == EditorMode.HELP:
        # Page navigation in help
        if key in (pygame.K_LEFT, pygame.K_h):
            state.help_page = max(0, state.help_page - 1)
            return
        elif key in (pygame.K_RIGHT, pygame.K_l):
            state.help_page = min(1, state.help_page + 1)
            return
        # Close help on Esc, Enter, or other keys
        state.mode = EditorMode.NORMAL
        state.help_page = 0  # Reset to first page
        models.sprite_win.visible = True
        models.status_win.visible = True
        return
    if state.mode == EditorMode.NORMAL:
        handle_normal_mode(key)
    elif state.mode == EditorMode.INSERT:
        handle_insert_mode(key)
    elif state.mode == EditorMode.VISUAL:
        handle_visual_mode(key)
    elif state.mode == EditorMode.COMMAND:
        handle_command_mode(key)
    elif state.mode == EditorMode.PALETTE_CATEGORIES:
        handle_palette_categories(key)
    elif state.mode == EditorMode.PALETTE_QWERTY:
        handle_palette_qwerty(key)
    elif state.mode == EditorMode.PALETTE_CODEPOINT:
        handle_palette_codepoint(key)
    elif state.mode == EditorMode.ANIMATION_EDITOR:
        handle_animation_editor(key)
    elif state.mode == EditorMode.ANIMATION_PREVIEW:
        handle_animation_preview(key)
    elif state.mode == EditorMode.SPRITE_LIBRARY:
        handle_sprite_library(key)
    elif state.mode == EditorMode.SPRITE_PICKER:
        handle_sprite_picker(key)


def handle_sprite_library(key):
    """Handle keys in sprite library mode"""
    lib_paths = sorted(state.sprite_library.keys())

    if is_escape(key):
        state.mode = EditorMode.NORMAL
        models.sprite_win.visible = True
        models.status_win.visible = True
        return

    if key in (pygame.K_j, pygame.K_DOWN):
        if lib_paths:
            state.sprite_library_cursor = (state.sprite_library_cursor + 1) % len(lib_paths)

    elif key in (pygame.K_k, pygame.K_UP):
        if lib_paths:
            state.sprite_library_cursor = (state.sprite_library_cursor - 1) % len(lib_paths)

    elif key == pygame.K_d:
        # Unload selected library
        if lib_paths and 0 <= state.sprite_library_cursor < len(lib_paths):
            lib_path = lib_paths[state.sprite_library_cursor]
            unload_sprite_library(lib_path)
            if state.sprite_library_cursor >= len(state.sprite_library):
                state.sprite_library_cursor = max(0, len(state.sprite_library) - 1)

    elif key == pygame.K_n:
        # Switch to command mode to import
        state.mode = EditorMode.COMMAND
        state.command_buffer = "import "
        models.sprite_win.visible = True
        models.status_win.visible = True


def handle_sprite_picker(key):
    """Handle keys in sprite picker mode"""
    all_sprites = get_all_library_sprites()
    cols = 4

    if is_escape(key):
        state.mode = EditorMode.NORMAL
        models.sprite_win.visible = True
        models.status_win.visible = True
        return

    if key in (pygame.K_j, pygame.K_DOWN):
        if all_sprites:
            state.sprite_picker_cursor = min(len(all_sprites) - 1, state.sprite_picker_cursor + cols)

    elif key in (pygame.K_k, pygame.K_UP):
        if all_sprites:
            state.sprite_picker_cursor = max(0, state.sprite_picker_cursor - cols)

    elif key in (pygame.K_h, pygame.K_LEFT):
        if all_sprites:
            state.sprite_picker_cursor = max(0, state.sprite_picker_cursor - 1)

    elif key in (pygame.K_l, pygame.K_RIGHT):
        if all_sprites:
            state.sprite_picker_cursor = min(len(all_sprites) - 1, state.sprite_picker_cursor + 1)

    elif key == pygame.K_RETURN:
        # Select sprite
        if all_sprites and 0 <= state.sprite_picker_cursor < len(all_sprites):
            library_key, sprite_name, _ = all_sprites[state.sprite_picker_cursor]
            state.selected_library_sprite = library_key
            state.scene_tool = "sprite"
            state.mode = EditorMode.NORMAL
            models.sprite_win.visible = True
            models.status_win.visible = True
            state.set_status(f"Selected: {sprite_name}")


def handle_animation_preview(key):
    """Handle keys in animation preview mode"""
    if is_escape(key) or key == pygame.K_SPACE or key == pygame.K_q:
        # Stop animation and return to editor
        stop_animation_preview()
        state.animation_playing = False
        state.mode = EditorMode.ANIMATION_EDITOR
        models.sprite_win.visible = False
        models.status_win.visible = False


def handle_animation_editor(key):
    """Handle keys in animation editor mode"""
    anim_names = sorted(state.animations.keys()) if state.animations else []

    if is_escape(key):
        if state.anim_editor_mode == "edit":
            # Go back to list mode
            state.anim_editor_mode = "list"
            state.anim_editor_frame_cursor = 0
        else:
            # Exit animation editor
            state.mode = EditorMode.NORMAL
            models.sprite_win.visible = True
            models.status_win.visible = True
        return

    if state.anim_editor_mode == "list":
        # List mode navigation
        if key in (pygame.K_j, pygame.K_DOWN):
            if anim_names:
                state.anim_editor_cursor = (state.anim_editor_cursor + 1) % len(anim_names)
        elif key in (pygame.K_k, pygame.K_UP):
            if anim_names:
                state.anim_editor_cursor = (state.anim_editor_cursor - 1) % len(anim_names)

        elif key == pygame.K_n:
            # Create new animation
            # For now, create with a default name
            base_name = "anim"
            counter = 1
            while f"{base_name}{counter}" in state.animations:
                counter += 1
            new_name = f"{base_name}{counter}"
            state.animations[new_name] = AnimationDef(name=new_name, frames=[])
            state.set_status(f"Created animation: {new_name}")

        elif key == pygame.K_RETURN:
            # Enter edit mode for selected animation
            if anim_names and 0 <= state.anim_editor_cursor < len(anim_names):
                state.anim_editor_mode = "edit"
                state.anim_editor_frame_cursor = 0

        elif key == pygame.K_d:
            # Delete selected animation
            if anim_names and 0 <= state.anim_editor_cursor < len(anim_names):
                anim_name = anim_names[state.anim_editor_cursor]
                del state.animations[anim_name]
                if state.current_animation == anim_name:
                    state.current_animation = None
                state.anim_editor_cursor = max(0, state.anim_editor_cursor - 1)
                state.set_status(f"Deleted animation: {anim_name}")

        elif key == pygame.K_SPACE:
            # Preview selected animation in dedicated preview mode
            if anim_names and 0 <= state.anim_editor_cursor < len(anim_names):
                anim_name = anim_names[state.anim_editor_cursor]
                if state.animations[anim_name].frames:
                    state.current_animation = anim_name
                    state.animation_frame_idx = 0
                    state.animation_timer = 0
                    state.animation_playing = True
                    state.mode = EditorMode.ANIMATION_PREVIEW
                    start_animation_preview()
                else:
                    state.set_status("Animation has no frames")

    else:  # edit mode
        if not anim_names or state.anim_editor_cursor >= len(anim_names):
            return
        anim_name = anim_names[state.anim_editor_cursor]
        anim = state.animations[anim_name]

        if key in (pygame.K_j, pygame.K_DOWN):
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                # Shift+J: Decrease Y offset (move down visually)
                if anim.frames and 0 <= state.anim_editor_frame_cursor < len(anim.frames):
                    anim.frames[state.anim_editor_frame_cursor].offset_y += 1
                    state.modified = True
            else:
                # Navigate down in frame list
                if anim.frames:
                    state.anim_editor_frame_cursor = (state.anim_editor_frame_cursor + 1) % len(anim.frames)

        elif key in (pygame.K_k, pygame.K_UP):
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                # Shift+K: Increase Y offset (move up visually)
                if anim.frames and 0 <= state.anim_editor_frame_cursor < len(anim.frames):
                    anim.frames[state.anim_editor_frame_cursor].offset_y -= 1
                    state.modified = True
            else:
                # Navigate up in frame list
                if anim.frames:
                    state.anim_editor_frame_cursor = (state.anim_editor_frame_cursor - 1) % len(anim.frames)

        elif key == pygame.K_h:
            # Decrease X offset
            if anim.frames and 0 <= state.anim_editor_frame_cursor < len(anim.frames):
                anim.frames[state.anim_editor_frame_cursor].offset_x -= 1
                state.modified = True

        elif key == pygame.K_l:
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                # Shift+L: Toggle loop
                anim.loop = not anim.loop
                state.modified = True
                state.set_status(f"Loop: {'On' if anim.loop else 'Off'}")
            else:
                # Increase X offset
                if anim.frames and 0 <= state.anim_editor_frame_cursor < len(anim.frames):
                    anim.frames[state.anim_editor_frame_cursor].offset_x += 1
                    state.modified = True

        elif key == pygame.K_a:
            # Add current sprite frame to animation
            anim.frames.append(AnimationFrame(frame_index=state.current_frame))
            state.anim_editor_frame_cursor = len(anim.frames) - 1
            state.modified = True
            state.set_status(f"Added frame {state.current_frame + 1}")

        elif key == pygame.K_d:
            # Remove selected frame from animation
            if anim.frames and 0 <= state.anim_editor_frame_cursor < len(anim.frames):
                del anim.frames[state.anim_editor_frame_cursor]
                state.anim_editor_frame_cursor = max(0, min(state.anim_editor_frame_cursor, len(anim.frames) - 1))
                state.modified = True
                state.set_status("Frame removed")

        elif key == pygame.K_LEFTBRACKET:
            # Move frame earlier in sequence
            if anim.frames and state.anim_editor_frame_cursor > 0:
                i = state.anim_editor_frame_cursor
                anim.frames[i], anim.frames[i-1] = anim.frames[i-1], anim.frames[i]
                state.anim_editor_frame_cursor -= 1
                state.modified = True

        elif key == pygame.K_RIGHTBRACKET:
            # Move frame later in sequence
            if anim.frames and state.anim_editor_frame_cursor < len(anim.frames) - 1:
                i = state.anim_editor_frame_cursor
                anim.frames[i], anim.frames[i+1] = anim.frames[i+1], anim.frames[i]
                state.anim_editor_frame_cursor += 1
                state.modified = True

        elif key == pygame.K_0:
            # Reset offset to (0, 0)
            if anim.frames and 0 <= state.anim_editor_frame_cursor < len(anim.frames):
                anim.frames[state.anim_editor_frame_cursor].offset_x = 0
                anim.frames[state.anim_editor_frame_cursor].offset_y = 0
                state.modified = True
                state.set_status("Offset reset")

        elif key == pygame.K_EQUALS:
            # Increase animation duration
            anim.frame_duration = min(5.0, anim.frame_duration + 0.05)
            state.modified = True
            state.set_status(f"Duration: {anim.frame_duration:.2f}s/frame")

        elif key == pygame.K_MINUS:
            # Decrease animation duration
            anim.frame_duration = max(0.02, anim.frame_duration - 0.05)
            state.modified = True
            state.set_status(f"Duration: {anim.frame_duration:.2f}s/frame")

        elif key == pygame.K_SPACE:
            # Preview animation in dedicated preview mode
            if anim.frames:
                state.current_animation = anim_name
                state.animation_frame_idx = 0
                state.animation_timer = 0
                state.animation_playing = True
                state.mode = EditorMode.ANIMATION_PREVIEW
                start_animation_preview()
            else:
                state.set_status("Animation has no frames")

        elif pygame.K_1 <= key <= pygame.K_9:
            # Quick add frame by number
            frame_num = key - pygame.K_1
            if frame_num < len(state.frames):
                anim.frames.append(AnimationFrame(frame_index=frame_num))
                state.anim_editor_frame_cursor = len(anim.frames) - 1
                state.set_status(f"Added frame {frame_num + 1}")


def handle_normal_mode(key):
    """Handle keys in NORMAL mode"""
    # Check for pending multi-key sequences
    if state.pending_key:
        handle_multi_key(state.pending_key, key)
        state.pending_key = None
        return

    # Navigation
    if key in (pygame.K_h, pygame.K_LEFT):
        state.cursor_x -= 1
        state.clamp_cursor()
    elif key in (pygame.K_l, pygame.K_RIGHT):
        state.cursor_x += 1
        state.clamp_cursor()
    elif key in (pygame.K_k, pygame.K_UP):
        state.cursor_y -= 1
        state.clamp_cursor()
    elif key in (pygame.K_j, pygame.K_DOWN):
        state.cursor_y += 1
        state.clamp_cursor()

    # Line navigation
    elif key == pygame.K_0:
        state.cursor_x = 0
    elif key == pygame.K_4 and pygame.key.get_mods() & pygame.KMOD_SHIFT:  # $
        state.cursor_x = state.canvas_width - 1

    # Multi-key sequences
    elif key == pygame.K_g:
        state.pending_key = 'g'
    elif key == pygame.K_d:
        state.pending_key = 'd'
    elif key == pygame.K_y:
        state.pending_key = 'y'

    # Jump to bottom
    elif key == pygame.K_g and pygame.key.get_mods() & pygame.KMOD_SHIFT:  # G
        state.cursor_y = state.canvas_height - 1

    # Mode switches
    elif key == pygame.K_i:
        state.mode = EditorMode.INSERT
        state.set_status("-- INSERT --")
    elif key == pygame.K_a:
        state.cursor_x += 1
        state.clamp_cursor()
        state.mode = EditorMode.INSERT
    elif key == pygame.K_v:
        state.mode = EditorMode.VISUAL
        state.selection_start = (state.cursor_x, state.cursor_y)
        state.set_status("-- VISUAL --")
    elif key == pygame.K_SEMICOLON and pygame.key.get_mods() & pygame.KMOD_SHIFT:  # :
        state.mode = EditorMode.COMMAND
        state.command_buffer = ""

    # Actions
    elif key == pygame.K_x:
        # Delete character under cursor
        state.clear_cell(state.cursor_x, state.cursor_y)

    elif key == pygame.K_c and pygame.key.get_mods() & pygame.KMOD_SHIFT:
        # C = Pick color under cursor
        cell = state.get_cell(state.cursor_x, state.cursor_y)
        if cell:
            state.current_fg = cell.fg
            # Try to sync fg_color_idx with palette
            try:
                state.fg_color_idx = COLOR_PALETTE_FG.index(cell.fg)
            except ValueError:
                pass  # Color not in palette
            state.set_status(f"Picked color: {cell.fg}")

    elif key == pygame.K_c:
        # Pick character under cursor
        cell = state.get_cell(state.cursor_x, state.cursor_y)
        if cell:
            state.current_char = cell.char
            state.current_fg = cell.fg
            state.set_status(f"Picked: {cell.char}")

    elif key == pygame.K_f:
        # Cycle foreground color
        state.fg_color_idx = (state.fg_color_idx + 1) % len(COLOR_PALETTE_FG)
        state.current_fg = COLOR_PALETTE_FG[state.fg_color_idx]
        state.set_status(f"FG color: {state.fg_color_idx + 1}/{len(COLOR_PALETTE_FG)}")

    elif key == pygame.K_u:
        # Undo (placeholder - will implement in Phase 2)
        state.set_status("Undo not yet implemented")

    elif key == pygame.K_p:
        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
            # P = paste before
            if state.clipboard:
                paste_clipboard()
            else:
                state.set_status("Clipboard empty")
        else:
            # p = open palette (category screen)
            state.mode = EditorMode.PALETTE_CATEGORIES
            state.palette_cursor = 0
            state.palette_scroll = 0

    elif key == pygame.K_COMMA:
        # , = previous frame
        switch_frame(-1)

    elif key == pygame.K_PERIOD:
        # . = next frame
        switch_frame(1)

    elif key == pygame.K_TAB:
        # Tab = toggle animation playback
        toggle_animation_playback()

    elif key == pygame.K_LEFTBRACKET:
        # [ = decrement codepoint by 1, { = by 100
        shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
        step = 100 if shift else 1
        adjust_codepoint(-step)

    elif key == pygame.K_RIGHTBRACKET:
        # ] = increment codepoint by 1, } = by 100
        shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
        step = 100 if shift else 1
        adjust_codepoint(step)

    elif key == pygame.K_MINUS:
        # - = decrement codepoint by 10, _ = by 1000
        shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
        step = 1000 if shift else 10
        adjust_codepoint(-step)

    elif key == pygame.K_EQUALS:
        # = = increment codepoint by 10, + = by 1000
        shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
        step = 1000 if shift else 10
        adjust_codepoint(step)

    elif pygame.K_1 <= key <= pygame.K_9:
        # Quick select from recent chars (1-9)
        idx = key - pygame.K_1  # 0-8
        if idx < len(state.recent_chars):
            char = state.recent_chars[idx]
            state.current_char = char
            state.last_selected_codepoint = ord(char)
            state.set_status(f"Selected: {char}")

    elif key == pygame.K_SPACE:
        if state.editor_mode == "scene" and state.scene_tool == "sprite":
            # Place sprite instance
            place_sprite_at_cursor()
        else:
            # Stamp current character at cursor
            cell = Cell(char=state.current_char, fg=state.current_fg, bg=state.current_bg)
            state.set_cell(state.cursor_x, state.cursor_y, cell)
            # Add to recent chars
            if state.current_char in state.recent_chars:
                state.recent_chars.remove(state.current_char)
            state.recent_chars.insert(0, state.current_char)
            state.recent_chars = state.recent_chars[:40]
            # Move cursor by 2 for wide characters, 1 otherwise
            state.cursor_x += 2 if is_wide_char(state.current_char) else 1
            state.clamp_cursor()

    elif key == pygame.K_SLASH and pygame.key.get_mods() & pygame.KMOD_SHIFT:
        # ? = open help
        state.mode = EditorMode.HELP

    # Scene mode keybindings
    elif key == pygame.K_t and state.editor_mode == "scene":
        # t = toggle tool (char/sprite)
        if state.scene_tool == "char":
            state.scene_tool = "sprite"
            if state.selected_library_sprite:
                sprite_name = state.selected_library_sprite.split(':')[-1]
                state.set_status(f"Tool: Sprite ({sprite_name})")
            else:
                state.set_status("Tool: Sprite (none selected - press S)")
        else:
            state.scene_tool = "char"
            state.set_status("Tool: Character")

    elif key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_SHIFT and state.editor_mode == "scene":
        # S = open sprite picker
        if not state.sprite_library:
            state.set_status("No sprites loaded - use :import <file.py>")
        else:
            state.mode = EditorMode.SPRITE_PICKER
            state.sprite_picker_cursor = 0
            models.sprite_win.visible = False
            models.status_win.visible = False

    elif key == pygame.K_i and pygame.key.get_mods() & pygame.KMOD_SHIFT and state.editor_mode == "scene":
        # I = open library manager
        state.mode = EditorMode.SPRITE_LIBRARY
        state.sprite_library_cursor = 0
        models.sprite_win.visible = False
        models.status_win.visible = False

    elif key == pygame.K_d and pygame.key.get_mods() & pygame.KMOD_SHIFT and state.editor_mode == "scene":
        # D = delete sprite under cursor
        delete_sprite_at_cursor()

    elif key == pygame.K_a and state.editor_mode == "scene":
        # a = cycle animation on sprite under cursor
        sprite = get_sprite_at_cursor()
        if sprite:
            cycle_sprite_animation(sprite)
        else:
            state.set_status("No sprite at cursor")

    # File operations
    elif key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
        if state.file_path:
            save_file(state.file_path)
        else:
            state.mode = EditorMode.COMMAND
            state.command_buffer = "w "

    # Quit
    elif key == pygame.K_q:
        if state.modified:
            state.set_status("Unsaved changes! Use :q! to force quit")
        else:
            pyunicodegame.quit()


def handle_multi_key(first_key, second_key):
    """Handle multi-key sequences like gg, dd, yy"""
    if first_key == 'g' and second_key == pygame.K_g:
        # gg - go to top
        state.cursor_y = 0
        state.cursor_x = 0
    elif first_key == 'd' and second_key == pygame.K_d:
        # dd - delete line
        for x in range(state.canvas_width):
            state.clear_cell(x, state.cursor_y)
        state.set_status("Line deleted")
    elif first_key == 'y' and second_key == pygame.K_y:
        # yy - yank line
        state.clipboard = {}
        for x in range(state.canvas_width):
            cell = state.get_cell(x, state.cursor_y)
            if cell:
                state.clipboard[(x - state.cursor_x, 0)] = Cell(cell.char, cell.fg, cell.bg)
        state.set_status("Line yanked")


def is_escape(key) -> bool:
    """Check for Escape or Ctrl+[ (vim standard escape alternative)"""
    if key == pygame.K_ESCAPE:
        return True
    if key == pygame.K_LEFTBRACKET and pygame.key.get_mods() & pygame.KMOD_CTRL:
        return True
    return False


def on_event(event) -> bool:
    """Handle pygame events. Return True to consume (prevent default handling)."""
    if event.type == pygame.KEYDOWN:
        # Consume Escape to prevent pyunicodegame from quitting
        if event.key == pygame.K_ESCAPE:
            on_key(event.key)
            return True
    return False


def handle_insert_mode(key):
    """Handle keys in INSERT mode"""
    if is_escape(key):
        state.mode = EditorMode.NORMAL
        state.set_status("")
        return

    # Navigation in insert mode
    if key == pygame.K_LEFT:
        state.cursor_x -= 1
        state.clamp_cursor()
    elif key == pygame.K_RIGHT:
        state.cursor_x += 1
        state.clamp_cursor()
    elif key == pygame.K_UP:
        state.cursor_y -= 1
        state.clamp_cursor()
    elif key == pygame.K_DOWN:
        state.cursor_y += 1
        state.clamp_cursor()

    elif key == pygame.K_BACKSPACE:
        # Delete backward
        if state.cursor_x > 0:
            state.cursor_x -= 1
            state.clear_cell(state.cursor_x, state.cursor_y)

    elif key == pygame.K_RETURN:
        # Move to next line
        state.cursor_y += 1
        state.cursor_x = 0
        state.clamp_cursor()

    elif key == pygame.K_TAB:
        # Insert spaces
        for _ in range(4):
            place_current_char(' ')

    elif key == pygame.K_SPACE:
        # Space places the current palette character
        place_current_char(state.current_char)

    else:
        # Try to get the character from the key
        char = key_to_char(key)
        if char:
            place_current_char(char)


def handle_visual_mode(key):
    """Handle keys in VISUAL mode"""
    if is_escape(key):
        state.mode = EditorMode.NORMAL
        state.selection_start = None
        state.set_status("")
        return

    # Navigation extends selection
    if key in (pygame.K_h, pygame.K_LEFT):
        state.cursor_x -= 1
        state.clamp_cursor()
    elif key in (pygame.K_l, pygame.K_RIGHT):
        state.cursor_x += 1
        state.clamp_cursor()
    elif key in (pygame.K_k, pygame.K_UP):
        state.cursor_y -= 1
        state.clamp_cursor()
    elif key in (pygame.K_j, pygame.K_DOWN):
        state.cursor_y += 1
        state.clamp_cursor()

    # Actions on selection
    elif key == pygame.K_y:
        yank_selection()
        state.mode = EditorMode.NORMAL
        state.selection_start = None
    elif key in (pygame.K_d, pygame.K_x):
        delete_selection()
        state.mode = EditorMode.NORMAL
        state.selection_start = None
    elif key == pygame.K_r:
        fill_selection()
        state.mode = EditorMode.NORMAL
        state.selection_start = None


def select_char(char: str):
    """Select a character and return to normal mode"""
    state.current_char = char
    state.last_selected_codepoint = ord(char)
    # Add to recent
    if char in state.recent_chars:
        state.recent_chars.remove(char)
    state.recent_chars.insert(0, char)
    state.recent_chars = state.recent_chars[:40]
    state.mode = EditorMode.NORMAL
    models.sprite_win.visible = True
    models.status_win.visible = True
    state.set_status(f"Selected: {char} (Space to stamp)")


def handle_palette_categories(key):
    """Handle keys in PALETTE_CATEGORIES mode (category list screen)"""
    if is_escape(key):
        state.mode = EditorMode.NORMAL
        models.sprite_win.visible = True
        models.status_win.visible = True
        state.set_status("")
        return

    # Navigation
    if key in (pygame.K_j, pygame.K_DOWN):
        state.palette_category = min(len(PALETTE_CATEGORIES) - 1, state.palette_category + 1)
    elif key in (pygame.K_k, pygame.K_UP):
        state.palette_category = max(0, state.palette_category - 1)
    elif key in (pygame.K_EQUALS, pygame.K_PAGEUP):
        # Page up - skip 10 categories
        state.palette_category = max(0, state.palette_category - 10)
    elif key in (pygame.K_MINUS, pygame.K_PAGEDOWN):
        # Page down - skip 10 categories
        state.palette_category = min(len(PALETTE_CATEGORIES) - 1, state.palette_category + 10)

    # Select category -> go to QWERTY picker
    elif key == pygame.K_RETURN:
        state.mode = EditorMode.PALETTE_QWERTY

    # Vicinity - go to QWERTY picker with vicinity chars (use special index -1)
    elif key == pygame.K_v:
        state.palette_category = -1  # Special value for vicinity
        state.mode = EditorMode.PALETTE_QWERTY

    # Random character
    elif key == pygame.K_r:
        char = get_random_char()
        select_char(char)

    # Codepoint entry
    elif key == pygame.K_u:
        state.codepoint_buffer = ""
        state.mode = EditorMode.PALETTE_CODEPOINT

    else:
        # Check for category hotkeys (1-9, a-z except r/u/v, A-Z)
        char = None
        if pygame.K_1 <= key <= pygame.K_9:
            char = chr(key)  # '1' to '9'
        elif pygame.K_a <= key <= pygame.K_z:
            char = chr(key)  # 'a' to 'z'
            # Handle shift for uppercase
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                char = char.upper()

        if char and char not in ('r', 'u', 'v'):  # Skip special hotkeys
            # Find the category index for this hotkey
            try:
                idx = CATEGORY_HOTKEYS.index(char)
                if idx < len(PALETTE_CATEGORIES):
                    state.palette_category = idx
                    state.mode = EditorMode.PALETTE_QWERTY
            except ValueError:
                pass  # Hotkey not found


def handle_palette_qwerty(key):
    """Handle keys in PALETTE_QWERTY mode (keyboard picker screen)"""
    if is_escape(key):
        # Go back to category screen (reset vicinity mode)
        if state.palette_category == -1:
            state.palette_category = 0
        state.mode = EditorMode.PALETTE_CATEGORIES
        return

    # Check if key is in our keyboard mapping
    if key in KEY_TO_INDEX:
        idx = KEY_TO_INDEX[key]
        shift = pygame.key.get_mods() & pygame.KMOD_SHIFT

        # With shift, access chars 40-79
        if shift:
            idx += 40

        # Get current category chars (special handling for vicinity mode)
        if state.palette_category == -1:  # Vicinity mode
            cat_chars = generate_vicinity_chars(state.last_selected_codepoint, 80)
        else:
            cat_name, cat_chars = PALETTE_CATEGORIES[state.palette_category]

        if idx < len(cat_chars):
            char = cat_chars[idx]
            select_char(char)


def handle_palette_codepoint(key):
    """Handle keys in PALETTE_CODEPOINT mode (hex entry screen)"""
    if is_escape(key):
        # Go back to category screen
        state.mode = EditorMode.PALETTE_CATEGORIES
        state.codepoint_buffer = ""
        return

    # Enter confirms
    if key == pygame.K_RETURN:
        if state.codepoint_buffer:
            try:
                cp = int(state.codepoint_buffer, 16)
                if 0x20 <= cp <= 0x10FFFF:
                    char = chr(cp)
                    select_char(char)
                    state.codepoint_buffer = ""
                    return
            except (ValueError, OverflowError):
                pass
        state.set_status("Invalid codepoint")
        return

    # Backspace
    if key == pygame.K_BACKSPACE:
        if state.codepoint_buffer:
            state.codepoint_buffer = state.codepoint_buffer[:-1]
        return

    # Hex digits (0-9, a-f)
    char = None
    if pygame.K_0 <= key <= pygame.K_9:
        char = chr(key)
    elif pygame.K_a <= key <= pygame.K_f:
        char = chr(key)

    if char and len(state.codepoint_buffer) < 6:
        state.codepoint_buffer += char


def handle_command_mode(key):
    """Handle keys in COMMAND mode"""
    if is_escape(key):
        state.mode = EditorMode.NORMAL
        state.command_buffer = ""
        state.set_status("")
        return

    if key == pygame.K_RETURN:
        execute_command(state.command_buffer)
        state.command_buffer = ""
        # Only reset to NORMAL if command didn't change to a different mode
        if state.mode == EditorMode.COMMAND:
            state.mode = EditorMode.NORMAL
        return

    if key == pygame.K_BACKSPACE:
        if state.command_buffer:
            state.command_buffer = state.command_buffer[:-1]
        else:
            state.mode = EditorMode.NORMAL
        return

    # Add character to command buffer
    char = key_to_char(key)
    if char:
        state.command_buffer += char


def key_to_char(key) -> Optional[str]:
    """Convert pygame key to character, handling shift"""
    mods = pygame.key.get_mods()
    shift = mods & pygame.KMOD_SHIFT

    # Letter keys
    if pygame.K_a <= key <= pygame.K_z:
        char = chr(key)
        return char.upper() if shift else char

    # Number keys
    if pygame.K_0 <= key <= pygame.K_9:
        if shift:
            shift_chars = ")!@#$%^&*("
            return shift_chars[key - pygame.K_0]
        return chr(key)

    # Special characters
    special = {
        pygame.K_SPACE: ' ',
        pygame.K_MINUS: '_' if shift else '-',
        pygame.K_EQUALS: '+' if shift else '=',
        pygame.K_LEFTBRACKET: '{' if shift else '[',
        pygame.K_RIGHTBRACKET: '}' if shift else ']',
        pygame.K_BACKSLASH: '|' if shift else '\\',
        pygame.K_SEMICOLON: ':' if shift else ';',
        pygame.K_QUOTE: '"' if shift else "'",
        pygame.K_COMMA: '<' if shift else ',',
        pygame.K_PERIOD: '>' if shift else '.',
        pygame.K_SLASH: '?' if shift else '/',
        pygame.K_BACKQUOTE: '~' if shift else '`',
    }

    return special.get(key)


# ============================================================================
# EDITING OPERATIONS
# ============================================================================

def is_wide_char(char: str) -> bool:
    """Check if a character is wide (takes 2 cells in unifont) by measuring actual render width"""
    try:
        font_tuple = pyunicodegame._fonts.get('unifont')
        if font_tuple:
            font = font_tuple[0]  # Primary font
            cell_width = pyunicodegame._font_dimensions.get('unifont', (8, 16))[0]
            surf, _ = font.render(char, (255, 255, 255))
            return surf.get_width() > cell_width
    except:
        pass
    # Fallback to east_asian_width if font measurement fails
    width = unicodedata.east_asian_width(char)
    return width in ('W', 'F')


def place_current_char(char: str):
    """Place a character at cursor and advance (2 for wide chars)"""
    cell = Cell(char=char, fg=state.current_fg, bg=state.current_bg)
    state.set_cell(state.cursor_x, state.cursor_y, cell)
    # Move cursor by 2 for wide characters, 1 otherwise
    state.cursor_x += 2 if is_wide_char(char) else 1
    state.clamp_cursor()


def yank_selection():
    """Copy selection to clipboard"""
    if not state.selection_start:
        return

    sx, sy = state.selection_start
    min_x = min(sx, state.cursor_x)
    max_x = max(sx, state.cursor_x)
    min_y = min(sy, state.cursor_y)
    max_y = max(sy, state.cursor_y)

    state.clipboard = {}
    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            cell = state.get_cell(x, y)
            if cell:
                state.clipboard[(x - min_x, y - min_y)] = Cell(cell.char, cell.fg, cell.bg)

    count = len(state.clipboard)
    state.set_status(f"Yanked {count} cells")


def delete_selection():
    """Delete selection"""
    if not state.selection_start:
        return

    sx, sy = state.selection_start
    min_x = min(sx, state.cursor_x)
    max_x = max(sx, state.cursor_x)
    min_y = min(sy, state.cursor_y)
    max_y = max(sy, state.cursor_y)

    count = 0
    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            if state.get_cell(x, y):
                state.clear_cell(x, y)
                count += 1

    state.cursor_x = min_x
    state.cursor_y = min_y
    state.set_status(f"Deleted {count} cells")


def fill_selection():
    """Fill selection with current character"""
    if not state.selection_start:
        return

    sx, sy = state.selection_start
    min_x = min(sx, state.cursor_x)
    max_x = max(sx, state.cursor_x)
    min_y = min(sy, state.cursor_y)
    max_y = max(sy, state.cursor_y)

    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            cell = Cell(char=state.current_char, fg=state.current_fg, bg=state.current_bg)
            state.set_cell(x, y, cell)

    state.set_status(f"Filled with '{state.current_char}'")


def paste_clipboard():
    """Paste clipboard at cursor"""
    if not state.clipboard:
        return

    for (dx, dy), cell in state.clipboard.items():
        x = state.cursor_x + dx
        y = state.cursor_y + dy
        if 0 <= x < state.canvas_width and 0 <= y < state.canvas_height:
            state.set_cell(x, y, Cell(cell.char, cell.fg, cell.bg))

    state.set_status(f"Pasted {len(state.clipboard)} cells")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def adjust_codepoint(delta: int):
    """Adjust current character's codepoint by delta, with bounds checking."""
    code = ord(state.current_char)
    new_code = code + delta
    # Clamp to valid Unicode range (skip control chars below space)
    new_code = max(0x20, min(0x10FFFF, new_code))
    # Skip surrogate range (U+D800-U+DFFF) - these are invalid codepoints
    if 0xD800 <= new_code <= 0xDFFF:
        if delta > 0:
            new_code = 0xE000  # Skip forward past surrogates
        else:
            new_code = 0xD7FF  # Skip backward before surrogates
    state.current_char = chr(new_code)
    state.last_selected_codepoint = new_code
    state.set_status(f"U+{new_code:04X}: {state.current_char}")


def switch_frame(delta: int):
    """Switch to a different frame, saving current frame first."""
    if len(state.frames) <= 1 and delta != 0:
        state.set_status("Only 1 frame - use :frame to add more")
        return

    # Save current frame
    state.frames[state.current_frame].cells = dict(state.cells)

    # Calculate new frame index
    new_frame = (state.current_frame + delta) % len(state.frames)
    state.current_frame = new_frame

    # Load new frame
    state.cells = dict(state.frames[new_frame].cells)
    state.set_status(f"Frame {new_frame + 1}/{len(state.frames)}")


def toggle_animation_playback():
    """Toggle animation auto-playback on/off."""
    if len(state.frames) <= 1:
        state.set_status("Need multiple frames for animation")
        return

    state.animation_playing = not state.animation_playing
    state.animation_timer = 0.0

    if state.animation_playing:
        # If we have a selected animation, use its frame sequence
        if state.current_animation and state.current_animation in state.animations:
            anim = state.animations[state.current_animation]
            state.animation_frame_idx = 0
            state.set_status(f"Playing [{state.current_animation}] - Tab to stop")
        else:
            # Just cycle through all frames
            state.animation_frame_idx = state.current_frame
            state.set_status("Playing all frames - Tab to stop")
    else:
        state.set_status(f"Stopped at frame {state.current_frame + 1}/{len(state.frames)}")


# ============================================================================
# COMMAND EXECUTION
# ============================================================================

def execute_command(cmd: str):
    """Execute a : command"""
    cmd = cmd.strip()
    if not cmd:
        return

    # Parse command and arguments
    parts = cmd.split(maxsplit=1)
    command = parts[0]
    args = parts[1] if len(parts) > 1 else ""

    # Handle force modifier
    force = command.endswith('!')
    if force:
        command = command[:-1]

    # Execute command
    if command in ('w', 'write', 'save'):
        path = args if args else state.file_path
        if path:
            save_file(path)
        else:
            state.set_status("No file name. Use :w <filename>")

    elif command in ('q', 'quit'):
        if state.modified and not force:
            state.set_status("Unsaved changes! Use :q! to force quit")
        else:
            pyunicodegame.quit()

    elif command in ('wq', 'x'):
        path = args if args else state.file_path
        if path:
            save_file(path)
            pyunicodegame.quit()
        elif state.file_path:
            save_file(state.file_path)
            pyunicodegame.quit()
        else:
            state.set_status("No file name")

    elif command in ('e', 'edit', 'open'):
        if not args:
            state.set_status("Usage: :e <filename>")
        elif state.modified and not force:
            state.set_status("Unsaved changes! Use :e! to force")
        else:
            load_file(args, setup_sprite_window, load_sprite_library, refresh_all_scene_sprites)

    elif command == 'new':
        if state.modified and not force:
            state.set_status("Unsaved changes! Use :new! to force")
        else:
            new_canvas(args)

    elif command == 'sprite':
        if state.modified and not force:
            state.set_status("Unsaved changes! Use :sprite! to force")
        else:
            create_sprite(args)

    elif command in ('frame', 'f'):
        handle_frame_command(args)

    elif command == 'frames':
        # List all frames
        state.set_status(f"Frames: {len(state.frames)} (current: {state.current_frame + 1})")

    elif command in ('anim', 'animation', 'a'):
        handle_anim_command(args)

    elif command == 'set':
        handle_set_command(args)

    elif command == 'color':
        handle_color_command(args)

    elif command == 'help':
        state.mode = EditorMode.HELP

    elif command == 'scene':
        if state.modified and not force:
            state.set_status("Unsaved changes! Use :scene! to force")
        else:
            create_scene(args)

    elif command in ('import', 'i'):
        if not args:
            state.set_status("Usage: :import <sprite_file.py>")
        else:
            load_sprite_library(args)

    elif command == 'unimport':
        if not args:
            state.set_status("Usage: :unimport <sprite_file.py>")
        else:
            unload_sprite_library(args)

    elif command == 'library':
        if state.editor_mode != "scene":
            state.set_status("Library only available in scene mode")
        else:
            state.mode = EditorMode.SPRITE_LIBRARY
            models.sprite_win.visible = False
            models.status_win.visible = False

    elif command == 'tool':
        if state.editor_mode != "scene":
            state.set_status("Tool command only available in scene mode")
        elif args in ('char', 'character'):
            state.scene_tool = "char"
            state.set_status("Tool: Character")
        elif args in ('sprite', 'sprites'):
            state.scene_tool = "sprite"
            if not state.sprite_library:
                state.set_status("Tool: Sprite (no library loaded - use :import)")
            elif not state.selected_library_sprite:
                state.set_status("Tool: Sprite (press S to select)")
            else:
                state.set_status(f"Tool: Sprite ({state.selected_library_sprite})")
        else:
            state.set_status("Usage: :tool char|sprite")

    elif command.isdigit():
        # Go to line
        line = int(command) - 1
        state.cursor_y = max(0, min(state.canvas_height - 1, line))

    else:
        state.set_status(f"Unknown command: {command}")


def handle_set_command(args: str):
    """Handle :set commands"""
    if not args:
        state.set_status("Usage: :set width=N or :set height=N")
        return

    match = re.match(r'(\w+)\s*=\s*(\d+)', args)
    if match:
        prop, value = match.groups()
        value = int(value)

        if prop == 'width':
            state.canvas_width = max(10, min(200, value))
            state.set_status(f"Canvas width: {state.canvas_width}")
        elif prop == 'height':
            state.canvas_height = max(10, min(100, value))
            state.set_status(f"Canvas height: {state.canvas_height}")
        else:
            state.set_status(f"Unknown property: {prop}")
    else:
        state.set_status("Usage: :set property=value")


def handle_color_command(args: str):
    """Handle :color fg/bg #RRGGBB"""
    parts = args.split()
    if len(parts) < 2:
        state.set_status("Usage: :color fg #RRGGBB")
        return

    target, color_str = parts[0], parts[1]

    try:
        if color_str.startswith('#'):
            color_str = color_str[1:]
        r = int(color_str[0:2], 16)
        g = int(color_str[2:4], 16)
        b = int(color_str[4:6], 16)
    except (ValueError, IndexError):
        state.set_status("Invalid color (use #RRGGBB)")
        return

    if target == 'fg':
        state.current_fg = (r, g, b)
        state.set_status(f"FG: #{color_str.upper()}")
    elif target == 'bg':
        state.current_bg = (r, g, b)
        state.set_status(f"BG: #{color_str.upper()}")
    else:
        state.set_status("Use 'fg' or 'bg'")


def new_canvas(args: str):
    """Create a new empty canvas"""
    width, height = DEFAULT_CANVAS_WIDTH, DEFAULT_CANVAS_HEIGHT

    if args:
        match = re.match(r'(\d+)x(\d+)', args.lower())
        if match:
            width = int(match.group(1))
            height = int(match.group(2))

    state.cells.clear()
    state.canvas_width = width
    state.canvas_height = height
    state.cursor_x = 0
    state.cursor_y = 0
    state.file_path = None
    state.modified = False
    state.set_status(f"New canvas {width}x{height}")


def create_sprite(args: str):
    """Create a new sprite with :sprite name WxH"""
    if not args:
        state.set_status("Usage: :sprite name WxH  (e.g. :sprite hero 3x3)")
        return

    # Parse name and optional dimensions
    parts = args.split()
    name = parts[0]

    # Default to small sprite
    width, height = 8, 6

    if len(parts) > 1:
        match = re.match(r'(\d+)x(\d+)', parts[1].lower())
        if match:
            width = int(match.group(1))
            height = int(match.group(2))

    # Clamp dimensions
    width = max(1, min(64, width))
    height = max(1, min(32, height))

    # Reset state for new sprite
    state.editor_mode = "sprite"
    state.sprite_name = name
    state.cells.clear()
    state.frames = [SpriteFrame()]
    state.current_frame = 0
    state.canvas_width = width
    state.canvas_height = height
    state.cursor_x = 0
    state.cursor_y = 0
    state.file_path = None
    state.modified = False
    state.current_fg = DEFAULT_FG

    # Recreate sprite window with new dimensions
    setup_sprite_window()

    state.set_status(f"New sprite '{name}' {width}x{height}")


def create_scene(args: str):
    """Create a new scene with :scene WxH"""
    # Default to full root dimensions
    width, height = ROOT_WIDTH, ROOT_HEIGHT - STATUS_HEIGHT

    if args:
        match = re.match(r'(\d+)x(\d+)', args.lower())
        if match:
            width = int(match.group(1))
            height = int(match.group(2))

    # Clamp dimensions
    width = max(10, min(200, width))
    height = max(10, min(100, height))

    # Reset state for new scene
    state.editor_mode = "scene"
    state.sprite_name = ""
    state.cells.clear()
    state.frames = [SpriteFrame()]  # Single frame for scene
    state.current_frame = 0
    state.canvas_width = width
    state.canvas_height = height
    state.cursor_x = 0
    state.cursor_y = 0
    state.file_path = None
    state.modified = False
    state.current_fg = DEFAULT_FG

    # Clear scene-specific state
    state.sprite_library.clear()
    state.sprite_instances.clear()
    state.scene_tool = "char"
    state.selected_library_sprite = None
    state.instance_counter = 0

    # Recreate sprite window with new dimensions
    setup_sprite_window()

    state.set_status(f"New scene {width}x{height}")


def handle_frame_command(args: str):
    """Handle :frame command for animation frames"""
    args = args.strip()

    if not args:
        # Add new frame
        # Save current cells to current frame
        state.frames[state.current_frame].cells = dict(state.cells)

        # Create new frame
        new_frame = SpriteFrame()
        state.frames.append(new_frame)
        state.current_frame = len(state.frames) - 1
        state.cells.clear()
        state.modified = True

        state.set_status(f"Added frame {state.current_frame + 1} (total: {len(state.frames)})")

    elif args.isdigit():
        # Switch to frame N
        frame_num = int(args) - 1  # 1-indexed for user
        if 0 <= frame_num < len(state.frames):
            # Save current frame
            state.frames[state.current_frame].cells = dict(state.cells)

            # Load target frame
            state.current_frame = frame_num
            state.cells = dict(state.frames[frame_num].cells)

            state.set_status(f"Frame {frame_num + 1}/{len(state.frames)}")
        else:
            state.set_status(f"Invalid frame {args} (1-{len(state.frames)})")

    else:
        state.set_status("Usage: :frame [N] - add new frame or switch to frame N")


def handle_anim_command(args: str):
    """Handle :anim command for animation management"""
    args = args.strip()

    if not args:
        # Open animation editor
        state.mode = EditorMode.ANIMATION_EDITOR
        state.anim_editor_mode = "list"
        state.anim_editor_cursor = 0
        models.sprite_win.visible = False
        models.status_win.visible = False

    elif args.startswith('new '):
        # Create new animation with given name
        name = args[4:].strip()
        if not name:
            state.set_status("Usage: :anim new <name>")
        elif name in state.animations:
            state.set_status(f"Animation '{name}' already exists")
        else:
            state.animations[name] = AnimationDef(name=name, frames=[])
            state.set_status(f"Created animation: {name}")

    elif args.startswith('delete ') or args.startswith('del '):
        # Delete animation
        name = args.split(maxsplit=1)[1].strip() if ' ' in args else ""
        if not name:
            state.set_status("Usage: :anim delete <name>")
        elif name not in state.animations:
            state.set_status(f"Animation '{name}' not found")
        else:
            del state.animations[name]
            if state.current_animation == name:
                state.current_animation = None
            state.set_status(f"Deleted animation: {name}")

    elif args.startswith('play '):
        # Play specific animation
        name = args[5:].strip()
        if name not in state.animations:
            state.set_status(f"Animation '{name}' not found")
        elif not state.animations[name].frames:
            state.set_status(f"Animation '{name}' has no frames")
        else:
            state.current_animation = name
            toggle_animation_playback()

    elif args == 'stop':
        # Stop playing animation
        if state.animation_playing:
            state.animation_playing = False
            state.set_status("Animation stopped")
        else:
            state.set_status("No animation playing")

    elif args == 'list':
        # List all animations
        if state.animations:
            names = ", ".join(sorted(state.animations.keys()))
            state.set_status(f"Animations: {names}")
        else:
            state.set_status("No animations defined")

    else:
        # Try to select animation by name
        if args in state.animations:
            state.current_animation = args
            state.set_status(f"Selected animation: {args}")
        else:
            state.set_status("Usage: :anim [new|delete|play|list] <name>")


# ============================================================================
# SPRITE LIBRARY (Scene Mode)
# ============================================================================

GENERATED_DIR = "generated_files"


def load_sprite_library(path: str, base_dir: Optional[str] = None) -> bool:
    """Load a sprite definition file into the library.

    Args:
        path: Path to the .py sprite file (can be relative, .py extension optional)
        base_dir: Base directory for resolving relative paths (defaults to cwd)

    Returns:
        True if successful, False otherwise
    """
    # Add .py extension if missing
    if not path.endswith('.py'):
        path = path + '.py'

    # Resolve path
    if base_dir and not os.path.isabs(path):
        full_path = os.path.join(base_dir, path)
    else:
        full_path = os.path.abspath(path)

    # Try generated_files/ if not found
    if not os.path.exists(full_path) and not os.path.isabs(path):
        gen_path = os.path.join(GENERATED_DIR, path)
        if os.path.exists(gen_path):
            full_path = os.path.abspath(gen_path)

    # Store relative path for portability
    if state.file_path:
        scene_dir = os.path.dirname(os.path.abspath(state.file_path))
        try:
            rel_path = os.path.relpath(full_path, scene_dir)
        except ValueError:
            rel_path = full_path  # Different drives on Windows
    else:
        rel_path = path

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Execute the file to extract SPRITE_DEFS
        # Include pyunicodegame and pygame in namespace since sprite files import them
        namespace = {'pyunicodegame': pyunicodegame, 'pygame': pygame}
        exec(content, namespace)

        if 'SPRITE_DEFS' not in namespace:
            state.set_status(f"No SPRITE_DEFS in {path}")
            return False

        sprite_defs = namespace['SPRITE_DEFS']
        sprite_names = list(sprite_defs.keys())

        # Create library entry
        entry = SpriteLibraryEntry(
            file_path=rel_path,
            sprite_names=sprite_names,
            sprite_defs=sprite_defs
        )

        state.sprite_library[rel_path] = entry
        state.set_status(f"Imported: {rel_path} ({len(sprite_names)} sprites)")
        return True

    except FileNotFoundError:
        state.set_status(f"File not found: {path}")
        return False
    except Exception as e:
        state.set_status(f"Error loading {path}: {e}")
        return False


def unload_sprite_library(path: str):
    """Remove a sprite library from the loaded set."""
    if path in state.sprite_library:
        # Remove any instances using sprites from this library
        to_remove = [
            inst_id for inst_id, inst in state.sprite_instances.items()
            if inst.library_key.startswith(path + ":")
        ]
        for inst_id in to_remove:
            del state.sprite_instances[inst_id]

        del state.sprite_library[path]
        state.set_status(f"Unloaded: {path}")
    else:
        state.set_status(f"Library not loaded: {path}")


def create_scene_sprite(sprite_def: dict, x: int, y: int, initial_animation: Optional[str] = None):
    """Create a pyunicodegame sprite from a library sprite definition."""
    frames_data = sprite_def.get('frames', [{}])
    default_fg = tuple(sprite_def.get('default_fg', (255, 255, 255)))
    animations_data = sprite_def.get('animations', {})

    # Build pyunicodegame frames
    pug_frames = []
    for frame_data in frames_data:
        if 'chars' in frame_data:
            # 2D array format
            chars = frame_data.get('chars', [[]])
            fg_colors = frame_data.get('fg_colors', [[]])
            pug_frame = pyunicodegame.SpriteFrame(chars, fg_colors)
        else:
            # Empty frame
            pug_frame = pyunicodegame.SpriteFrame([[' ']], [[None]])
        pug_frames.append(pug_frame)

    if not pug_frames:
        pug_frames = [pyunicodegame.SpriteFrame([[' ']], [[None]])]

    # Create the sprite
    sprite = pyunicodegame.Sprite(pug_frames, fg=default_fg)
    sprite.x = x
    sprite.y = y

    # Add animations
    for anim_name, anim_data in animations_data.items():
        anim_frames = anim_data.get('frames', [])
        if not anim_frames:
            continue

        frame_indices = [f[0] for f in anim_frames]
        offsets = [(float(f[1]), float(f[2])) for f in anim_frames]
        frame_duration = anim_data.get('frame_duration', 0.2)
        loop = anim_data.get('loop', True)

        pug_anim = pyunicodegame.Animation(
            name=anim_name,
            frame_indices=frame_indices,
            frame_duration=frame_duration,
            offsets=offsets,
            loop=loop,
            offset_speed=50.0
        )
        sprite.add_animation(pug_anim)

    # Start initial animation
    if initial_animation and initial_animation in animations_data:
        sprite.play_animation(initial_animation)
    elif animations_data:
        # Default to 'idle' or first animation
        default_anim = 'idle' if 'idle' in animations_data else next(iter(animations_data))
        sprite.play_animation(default_anim)

    return sprite


def get_canvas_offset():
    """Get the (x, y) offset where the canvas is positioned on models.root."""
    avail_h = ROOT_HEIGHT - STATUS_HEIGHT
    sx = (ROOT_WIDTH - state.canvas_width) // 2
    sy = (avail_h - state.canvas_height) // 2
    return sx, sy


def add_scene_preview_sprite(instance_id: str, instance: SpriteInstance):
    """Create and add a preview sprite for a placed instance."""
    lib_path = instance.library_key.split(':')[0]
    sprite_name = instance.library_key.split(':')[1]

    if lib_path not in state.sprite_library:
        return

    sprite_def = state.sprite_library[lib_path].sprite_defs.get(sprite_name, {})
    if not sprite_def:
        return

    # Create the pyunicodegame sprite at canvas-relative position
    sprite = create_scene_sprite(sprite_def, instance.x, instance.y, instance.initial_animation)

    # Add to sprite window (not root)
    if models.sprite_win:
        models.sprite_win.add_sprite(sprite)

    state.scene_preview_sprites[instance_id] = sprite


def remove_scene_preview_sprite(instance_id: str):
    """Remove a preview sprite from the scene."""
    if instance_id in state.scene_preview_sprites:
        sprite = state.scene_preview_sprites[instance_id]
        if models.sprite_win:
            models.sprite_win.remove_sprite(sprite)
        del state.scene_preview_sprites[instance_id]


def refresh_all_scene_sprites():
    """Recreate all scene preview sprites (e.g., after loading a scene)."""
    # Remove existing preview sprites
    for instance_id in list(state.scene_preview_sprites.keys()):
        remove_scene_preview_sprite(instance_id)

    # Create new ones for all instances
    for instance_id, instance in state.sprite_instances.items():
        add_scene_preview_sprite(instance_id, instance)


def place_sprite_at_cursor():
    """Place a sprite instance at the cursor position"""
    if not state.selected_library_sprite:
        state.set_status("No sprite selected - press S to select")
        return

    library_key = state.selected_library_sprite
    lib_path = library_key.split(':')[0]
    sprite_name = library_key.split(':')[1]

    # Check library is still loaded
    if lib_path not in state.sprite_library:
        state.set_status(f"Sprite library unloaded: {lib_path}")
        state.selected_library_sprite = None
        return

    # Generate unique instance ID
    state.instance_counter += 1
    instance_id = f"{sprite_name}_{state.instance_counter:03d}"

    # Create instance
    instance = SpriteInstance(
        library_key=library_key,
        instance_id=instance_id,
        x=state.cursor_x,
        y=state.cursor_y,
        initial_animation=None
    )

    state.sprite_instances[instance_id] = instance

    # Create preview sprite
    add_scene_preview_sprite(instance_id, instance)

    state.modified = True
    state.set_status(f"Placed: {instance_id}")


def delete_sprite_at_cursor():
    """Delete any sprite instance at the cursor position"""
    # Find sprite at cursor
    for instance_id, instance in list(state.sprite_instances.items()):
        # Get sprite dimensions
        lib_path = instance.library_key.split(':')[0]
        sprite_name = instance.library_key.split(':')[1]

        if lib_path in state.sprite_library:
            sprite_def = state.sprite_library[lib_path].sprite_defs.get(sprite_name, {})
            w = sprite_def.get('width', 1)
            h = sprite_def.get('height', 1)
        else:
            w, h = 1, 1

        # Check if cursor is within sprite bounds
        if (instance.x <= state.cursor_x < instance.x + w and
            instance.y <= state.cursor_y < instance.y + h):
            # Remove preview sprite
            remove_scene_preview_sprite(instance_id)
            del state.sprite_instances[instance_id]
            state.modified = True
            state.set_status(f"Deleted: {instance_id}")
            return

    state.set_status("No sprite at cursor")


def get_sprite_at_cursor() -> Optional[SpriteInstance]:
    """Get sprite instance at cursor position, if any"""
    for instance_id, instance in state.sprite_instances.items():
        lib_path = instance.library_key.split(':')[0]
        sprite_name = instance.library_key.split(':')[1]

        if lib_path in state.sprite_library:
            sprite_def = state.sprite_library[lib_path].sprite_defs.get(sprite_name, {})
            w = sprite_def.get('width', 1)
            h = sprite_def.get('height', 1)
        else:
            w, h = 1, 1

        if (instance.x <= state.cursor_x < instance.x + w and
            instance.y <= state.cursor_y < instance.y + h):
            return instance

    return None


def cycle_sprite_animation(instance: SpriteInstance):
    """Cycle to the next animation for a sprite instance"""
    lib_path = instance.library_key.split(':')[0]
    sprite_name = instance.library_key.split(':')[1]

    if lib_path not in state.sprite_library:
        state.set_status("Sprite library not loaded")
        return

    sprite_def = state.sprite_library[lib_path].sprite_defs.get(sprite_name, {})
    animations = sprite_def.get('animations', {})

    if not animations:
        state.set_status(f"{sprite_name} has no animations")
        return

    anim_names = list(animations.keys())
    current = instance.initial_animation

    if current is None or current not in anim_names:
        # Set to first animation
        instance.initial_animation = anim_names[0]
    else:
        # Cycle to next
        idx = anim_names.index(current)
        next_idx = (idx + 1) % len(anim_names)
        instance.initial_animation = anim_names[next_idx]

    state.modified = True
    state.set_status(f"{instance.instance_id}: {instance.initial_animation}")


# ============================================================================
# UPDATE LOOP
# ============================================================================

def update(dt: float):
    """Update function called each frame"""
    # Update cursor blink
    state.cursor_blink_timer += dt
    if state.cursor_blink_timer >= CURSOR_BLINK_RATE:
        state.cursor_blink_timer = 0
        state.cursor_visible = not state.cursor_visible

    # In preview mode, pyunicodegame handles sprite updates automatically in its run loop
    if state.mode == EditorMode.ANIMATION_PREVIEW:
        # Still decay status message
        if state.status_message_time > 0:
            state.status_message_time -= dt
            if state.status_message_time <= 0:
                state.status_message = ""
        return  # Skip our own animation tick logic in preview mode

    # Update animation playback
    if state.animation_playing and len(state.frames) > 1:
        # Determine frame duration
        frame_duration = 0.2  # Default
        if state.current_animation and state.current_animation in state.animations:
            anim = state.animations[state.current_animation]
            frame_duration = anim.frame_duration

        state.animation_timer += dt
        if state.animation_timer >= frame_duration:
            state.animation_timer = 0

            # Save current frame
            state.frames[state.current_frame].cells = dict(state.cells)

            # Advance to next frame
            if state.current_animation and state.current_animation in state.animations:
                # Use animation's frame sequence
                anim = state.animations[state.current_animation]
                state.animation_frame_idx = (state.animation_frame_idx + 1) % len(anim.frames)
                anim_frame = anim.frames[state.animation_frame_idx]
                state.current_frame = anim_frame.frame_index % len(state.frames)
            else:
                # Cycle through all frames
                state.current_frame = (state.current_frame + 1) % len(state.frames)

            # Load new frame
            state.cells = dict(state.frames[state.current_frame].cells)

    # Note: Scene sprite updates are handled automatically by pyunicodegame's run loop

    # Decay status message
    if state.status_message_time > 0:
        state.status_message_time -= dt
        if state.status_message_time <= 0:
            state.status_message = ""


# ============================================================================
# MAIN
# ============================================================================

def setup_sprite_window():
    """Create or recreate the sprite editing window based on current dimensions"""
    # Remove old window if it exists
    try:
        pyunicodegame.remove_window("sprite")
    except:
        pass

    # Calculate centered position
    avail_h = ROOT_HEIGHT - STATUS_HEIGHT
    sx = (ROOT_WIDTH - state.canvas_width) // 2
    sy = (avail_h - state.canvas_height) // 2

    # Create sprite window
    models.sprite_win = pyunicodegame.create_window(
        "sprite",
        sx, sy,
        state.canvas_width, state.canvas_height,
        z_index=5,
        font_name="unifont",
        bg=(20, 20, 35, 255)
    )


def main():
    # Parse command line arguments
    file_to_load = None
    canvas_w = DEFAULT_CANVAS_WIDTH
    canvas_h = DEFAULT_CANVAS_HEIGHT

    for arg in sys.argv[1:]:
        # Check for dimension argument (WxH)
        match = re.match(r'^(\d+)x(\d+)$', arg.lower())
        if match:
            canvas_w = int(match.group(1))
            canvas_h = int(match.group(2))
        elif arg.startswith('-'):
            # Future: handle --width, --height flags
            pass
        else:
            # Assume it's a file
            file_to_load = arg

    # Set state dimensions
    state.canvas_width = canvas_w
    state.canvas_height = canvas_h

    # Initialize pyunicodegame with fixed root window size
    models.root = pyunicodegame.init(
        "Sprite & Scene Editor",
        width=ROOT_WIDTH,
        height=ROOT_HEIGHT,
        font_name="unifont",
        bg=(10, 10, 20, 255)
    )

    # Enable key repeat for codepoint navigation (delay 300ms, repeat 50ms)
    pygame.key.set_repeat(300, 50)

    # Create sprite editing window (centered)
    setup_sprite_window()

    # Create status bar window at bottom (high z-index)
    models.status_win = pyunicodegame.create_window(
        "status",
        0, ROOT_HEIGHT - STATUS_HEIGHT,
        ROOT_WIDTH, STATUS_HEIGHT,
        z_index=100,
        font_name="unifont",
        bg=(15, 15, 25, 255)
    )

    # Load file if specified
    if file_to_load:
        load_file(file_to_load, setup_sprite_window, load_sprite_library, refresh_all_scene_sprites)
    else:
        state.set_status(f":sprite name WxH to start | ? for help")

    # Run the editor
    pyunicodegame.run(update=update, render=render, on_key=on_key, on_event=on_event)


if __name__ == "__main__":
    main()
