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
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Tuple, Optional, List
import sys
import re
import random


# ============================================================================
# CONSTANTS
# ============================================================================

# Root window size (fixed, contains everything)
ROOT_WIDTH = 60
ROOT_HEIGHT = 24

# Status bar at bottom
STATUS_HEIGHT = 3  # Status bar + command line + mini palette

# Default sprite canvas size
DEFAULT_CANVAS_WIDTH = 8
DEFAULT_CANVAS_HEIGHT = 6

DEFAULT_FG = (255, 255, 255)
DEFAULT_BG = None
CURSOR_BLINK_RATE = 0.5  # seconds

# Colors
COLOR_NORMAL = (100, 200, 100)
COLOR_INSERT = (100, 100, 255)
COLOR_VISUAL = (255, 200, 100)
COLOR_COMMAND = (255, 255, 100)
COLOR_PALETTE = (200, 100, 255)
COLOR_STATUS_DIM = (100, 100, 120)
COLOR_STATUS_BRIGHT = (200, 200, 220)
COLOR_CURSOR = (255, 255, 0)
COLOR_CURSOR_INSERT = (100, 200, 255)

# Predefined color palette for cycling
COLOR_PALETTE_FG = [
    (255, 255, 255),  # White
    (255, 100, 100),  # Red
    (100, 255, 100),  # Green
    (100, 100, 255),  # Blue
    (255, 255, 100),  # Yellow
    (255, 100, 255),  # Magenta
    (100, 255, 255),  # Cyan
    (255, 200, 100),  # Orange
    (200, 100, 255),  # Purple
    (150, 150, 150),  # Gray
]

# Character palette categories (name, characters) - each should have 41+ entries for shift support
PALETTE_CATEGORIES = [
    ('Recent', []),  # Populated dynamically
    # Box drawing - combine related sets (41+ each)
    ('Box Light', list('─│┌┐└┘├┤┬┴┼╌╎┄┆┈┊') + [chr(0x2500 + i) for i in range(40, 64)]),
    ('Box Heavy', list('━┃┏┓┗┛┣┫┳┻╋╍╏┅┇┉┋') + [chr(0x2500 + i) for i in range(56, 80)]),
    ('Box Double', list('═║╔╗╚╝╠╣╦╩╬') + [chr(0x2550 + i) for i in range(11, 44)]),
    ('Box Round', list('╭╮╯╰') + list('─│┌┐└┘├┤┬┴┼━┃┏┓┗┛┣┫┳┻╋═║╔╗╚╝╠╣╦╩╬╌╍╎╏')),
    ('Box Mixed', list('╒╓╔╕╖╗╘╙╚╛╜╝╞╟╠╡╢╣╤╥╦╧╨╩╪╫╬') + list('╭╮╯╰─│┌┐└┘├┤┬┴┼')),
    # Block elements - extend with more
    ('Blocks', list('▀▁▂▃▄▅▆▇█▉▊▋▌▍▎▏░▒▓') + [chr(0x2580 + i) for i in range(20, 32)] + list('▖▗▘▙▚▛▜▝▞▟')),
    ('Quadrants', list('▖▗▘▙▚▛▜▝▞▟') + list('░▒▓█▀▄▌▐▬▭▮▯▰▱◼◻◾◽■□▢▣▤▥▦▧▨▩▪▫▰▱')),
    # Geometric shapes - extend ranges
    ('Geometric', list('■□▢▣▤▥▦▧▨▩●○◐◑◒◓◔◕◖◗◘◙◚◛◜◝◞◟◠◡◢◣◤◥◦◧◨◩◪◫◬◭◮')),
    ('Triangles', list('▲△▴▵▶▷▸▹►▻◀◁◂◃◄◅▼▽▾▿') + list('◢◣◤◥◸◹◺◿◁▷◅▻◄►⏴⏵⏶⏷🔺🔻🔼🔽')),
    ('Diamonds', list('◆◇◈◊❖⬥⬦⬧⬨◇◆') + list('⬩⬪⬫⬬⬭⬮⬯⟐⟡⧫⧪⧩⧨') + list('♦♢🔶🔷🔸🔹💎💠◈◊❖') + list('⯁⯂⟠⟡⬖⬗⬘⬙')),
    ('Stars', list('★☆✦✧✩✪✫✬✭✮✯✰✱✲✳✴✵✶✷✸✹') + list('✺✻✼✽✾✿❀❁❂❃❄❅❆❇❈❉❊❋⭐⭑⭒')),
    ('Arrows', list('←↑→↓↔↕↖↗↘↙↚↛↜↝↞↟↠↡↢↣↤↥↦↧↨↩↪↫↬↭↮↯↰↱↲↳↴↵↶↷↸↹')),
    ('Math', list('±×÷≠≤≥≈∞∑∏√∫∂∇∈∉∩∪⊂⊃⊄⊅⊆⊇⊈⊉⊊⊋∀∃∄∅∆∇∴∵∷∸∼∽∾∿')),
    ('Greek', list('αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ')),
    ('Symbols', list('♠♡♢♣♤♥♦♧♔♕♖♗♘♙♚♛♜♝♞♟') + list('☮☯☸☠☢☣⚛⚔⚖⚗⚙⚚⚜⚝⚠⚡⚢⚣⚤⚥⚦')),
    ('Music', list('♩♪♫♬♭♮♯𝄞𝄢') + [chr(0x1D100 + i) for i in range(32)] + list('🎵🎶🎷🎸🎹🎺🎻')),
    ('Weather', list('☀☁☂☃☄☽☾⛅⛈') + list('🌤🌥🌦🌧🌨🌩🌪🌫🌬❄☔⚡🌡🌈🌀🌊💧💨🔥⛄☃️🌞🌝🌚🌑🌒🌓🌔🌕🌖🌗🌘')),
    ('Zodiac', list('♈♉♊♋♌♍♎♏♐♑♒♓') + list('⛎☉☽♁♃♄♅♆♇☿♀♂⚳⚴⚵⚶⚷⚸⚹⚺⚻⚼⛢☊☋☌☍⚕⚘⚚⚛')),
    ('Misc', list('·•°※†‡§¶©®™℃℉№℗℠℡™⁂⁃⁄⁒⁓⁕⁖⁘⁙⁚⁛⁜⁝⁞‖‗†‡•‣․‥…‧‰‱′″‴‵‶‷')),
    ('Braille', [chr(0x2800 + i) for i in range(80)]),
    ('Sextants', [chr(0x1FB00 + i) for i in range(48)]),
    ('Wedges', [chr(0x1FB3C + i) for i in range(44)]),
    ('Octants', [chr(0x1CC00 + i) for i in range(80)]),
    ('Legacy', [chr(0x1CC00 + (i * 704 // 81)) for i in range(81)]),  # Legacy Computing Supplement spread
    ('Lines', list('╱╲╳⌒⌓─━│┃╌╍╎╏┄┅┆┇┈┉┊┋') + list('⎯⎸⎹⎺⎻⎼⎽─━│┃┄┅┆┇┈┉┊┋╌╍╎╏—–―‾')),
    ('Dingbats', [chr(0x2700 + i) for i in range(80)]),
    ('Emoji Face', list('😀😁😂🤣😃😄😅😆😉😊😋😎😍😘🥰😗😙🥲😚☺😌😛😜🤪😝🤑🤗🤭🤫🤔🤐🤨😐😑😶🫥😏😒🙄😬😮😯')),
    ('Emoji Hand', list('👍👎👌✌🤞🤟🤙👋🖐✋👏🙌🤲🙏🤝💪🦾🖕✍🤳💅🦵🦶👂🦻👃👶🧒👦👧🧑👱👀👁👃👄💋🦷🦴💀☠')),
    ('Animals', list('🐀🐁🐂🐃🐄🐅🐆🐇🐈🐉🐊🐋🐌🐍🐎🐏🐐🐑🐒🐓🐔🐕🐖🐗🐘🐙🐚🐛🐜🐝🐞🐟🐠🐡🐢🐣🐤🐥🐦🐧🐨🐩🐪🐫🐬🐭🐮🐯🐰🐱🐲🐳🐴🐵🐶🐷🐸🐹🐺🐻🐼🐽🐾🦁🦂🦃🦄🦅🦆🦇🦈🦉🦊🦋🦌🦍🦎🦏🦐')),
    ('Plants', list('🌲🌳🌴🌵🌷🌸🌹🌺🌻🌼🌽🌾🌿🍀🍁🍂🍃🍄🍅🍆🍇🍈🍉🍊🍋🍌🍍🍎🍏🍐🍑🍒🍓🥝🥥🥑🥔🥕🥒🌶🥬🥦')),
    # Note: Vicinity is handled as a special option, not in this list
]

# Generate category hotkeys: 1-9, then a-z (skip r, u, v which are special)
def generate_category_hotkeys():
    """Generate hotkey list for categories"""
    hotkeys = []
    # Numbers 1-9
    for i in range(1, 10):
        hotkeys.append(str(i))
    # Letters a-z, skipping r, u, v (used for special commands)
    for c in 'abcdefghijklmnopqstwxyz':  # skip r, u, v
        hotkeys.append(c)
    # Uppercase if we need more
    for c in 'ABCDEFGHIJKLMNOPQSTWXYZ':
        hotkeys.append(c)
    return hotkeys

CATEGORY_HOTKEYS = generate_category_hotkeys()

# QWERTY keyboard layout for character picker
KEYBOARD_ROWS = [
    # Row 1: number row (11 keys)
    ['`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
    # Row 2: QWERTY row (10 keys)
    ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
    # Row 3: home row (10 keys)
    ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';'],
    # Row 4: bottom row (9 keys)
    ['z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.'],
]

# Flatten keyboard layout for indexing
KEYBOARD_KEYS = [key for row in KEYBOARD_ROWS for key in row]  # 40 keys total

# Map pygame key constants to keyboard index
KEY_TO_INDEX = {
    pygame.K_BACKQUOTE: 0, pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3,
    pygame.K_4: 4, pygame.K_5: 5, pygame.K_6: 6, pygame.K_7: 7,
    pygame.K_8: 8, pygame.K_9: 9, pygame.K_0: 10,
    pygame.K_q: 11, pygame.K_w: 12, pygame.K_e: 13, pygame.K_r: 14,
    pygame.K_t: 15, pygame.K_y: 16, pygame.K_u: 17, pygame.K_i: 18,
    pygame.K_o: 19, pygame.K_p: 20,
    pygame.K_a: 21, pygame.K_s: 22, pygame.K_d: 23, pygame.K_f: 24,
    pygame.K_g: 25, pygame.K_h: 26, pygame.K_j: 27, pygame.K_k: 28,
    pygame.K_l: 29, pygame.K_SEMICOLON: 30,
    pygame.K_z: 31, pygame.K_x: 32, pygame.K_c: 33, pygame.K_v: 34,
    pygame.K_b: 35, pygame.K_n: 36, pygame.K_m: 37, pygame.K_COMMA: 38,
    pygame.K_PERIOD: 39,
}

# Unicode ranges for random character selection
RANDOM_UNICODE_RANGES = [
    (0x2500, 0x257F),   # Box Drawing
    (0x2580, 0x259F),   # Block Elements
    (0x25A0, 0x25FF),   # Geometric Shapes
    (0x2600, 0x26FF),   # Misc Symbols
    (0x2700, 0x27BF),   # Dingbats
    (0x2800, 0x28FF),   # Braille
    (0x1FB00, 0x1FBFF), # Legacy Computing
    (0x1CC00, 0x1CEFF), # Legacy Computing Supplement
]


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class EditorMode(Enum):
    NORMAL = auto()
    INSERT = auto()
    VISUAL = auto()
    COMMAND = auto()
    PALETTE_CATEGORIES = auto()  # Category list screen
    PALETTE_QWERTY = auto()      # QWERTY character picker
    PALETTE_CODEPOINT = auto()   # Codepoint entry mode
    LINE = auto()
    BOX = auto()
    HELP = auto()
    ANIMATION_EDITOR = auto()    # Animation assembly screen
    ANIMATION_PREVIEW = auto()   # Full-screen animation preview


@dataclass
class Cell:
    char: str = ' '
    fg: Tuple[int, int, int] = field(default_factory=lambda: DEFAULT_FG)
    bg: Optional[Tuple[int, int, int]] = None

    def is_empty(self) -> bool:
        return self.char == ' ' and self.fg == DEFAULT_FG and self.bg is None

    def to_dict(self) -> dict:
        return {'char': self.char, 'fg': self.fg, 'bg': self.bg}

    @staticmethod
    def from_dict(d: dict) -> 'Cell':
        return Cell(char=d['char'], fg=tuple(d['fg']), bg=tuple(d['bg']) if d.get('bg') else None)


@dataclass
class SpriteFrame:
    """A single frame of a sprite (for animation)"""
    cells: Dict[Tuple[int, int], Cell] = field(default_factory=dict)

    def to_dict(self, width: int, height: int) -> dict:
        """Convert to serializable format with 2D arrays"""
        chars = [[' ' for _ in range(width)] for _ in range(height)]
        fg_colors = [[None for _ in range(width)] for _ in range(height)]

        for (x, y), cell in self.cells.items():
            if 0 <= x < width and 0 <= y < height:
                chars[y][x] = cell.char
                if cell.fg != DEFAULT_FG:
                    fg_colors[y][x] = cell.fg

        return {'chars': chars, 'fg_colors': fg_colors}

    @staticmethod
    def from_dict(d: dict) -> 'SpriteFrame':
        """Load from serialized format"""
        frame = SpriteFrame()
        chars = d.get('chars', [])
        fg_colors = d.get('fg_colors', [])

        for y, row in enumerate(chars):
            for x, char in enumerate(row):
                if char != ' ':
                    fg = DEFAULT_FG
                    if y < len(fg_colors) and x < len(fg_colors[y]) and fg_colors[y][x]:
                        fg = tuple(fg_colors[y][x])
                    frame.cells[(x, y)] = Cell(char=char, fg=fg)

        return frame


@dataclass
class AnimationFrame:
    """Single frame in an animation with optional pixel offset"""
    frame_index: int  # Index into sprite's frames list
    offset_x: int = 0  # Pixel offset for lunges, jumps, etc.
    offset_y: int = 0


@dataclass
class AnimationDef:
    """Named animation sequence"""
    name: str
    frames: List['AnimationFrame'] = field(default_factory=list)  # Frames with offsets
    frame_duration: float = 0.2  # Seconds per frame
    loop: bool = True


@dataclass
class SpriteData:
    """Complete sprite definition (may contain multiple frames)"""
    name: str
    width: int
    height: int
    frames: List[SpriteFrame] = field(default_factory=lambda: [SpriteFrame()])
    animations: Dict[str, AnimationDef] = field(default_factory=dict)
    default_fg: Tuple[int, int, int] = field(default_factory=lambda: DEFAULT_FG)

    def to_dict(self) -> dict:
        """Convert to serializable format for SPRITE_DEFS"""
        result = {
            'width': self.width,
            'height': self.height,
            'default_fg': self.default_fg,
            'frames': [f.to_dict(self.width, self.height) for f in self.frames],
        }
        if self.animations:
            result['animations'] = {
                name: {
                    'frames': [(af.frame_index, af.offset_x, af.offset_y) for af in anim.frames],
                    'frame_duration': anim.frame_duration,
                    'loop': anim.loop,
                }
                for name, anim in self.animations.items()
            }
        return result

    @staticmethod
    def from_dict(name: str, d: dict) -> 'SpriteData':
        """Load from SPRITE_DEFS format"""
        sprite = SpriteData(
            name=name,
            width=d.get('width', 3),
            height=d.get('height', 3),
            default_fg=tuple(d.get('default_fg', DEFAULT_FG)),
        )
        sprite.frames = [SpriteFrame.from_dict(f) for f in d.get('frames', [{}])]
        # Load animations
        if 'animations' in d:
            for anim_name, anim_data in d['animations'].items():
                anim_frames = [
                    AnimationFrame(frame_index=f[0], offset_x=f[1], offset_y=f[2])
                    for f in anim_data.get('frames', [])
                ]
                sprite.animations[anim_name] = AnimationDef(
                    name=anim_name,
                    frames=anim_frames,
                    frame_duration=anim_data.get('frame_duration', 0.2),
                    loop=anim_data.get('loop', True),
                )
        return sprite


@dataclass
class EditorState:
    # Editor mode: "sprite" or "scene"
    editor_mode: str = "sprite"

    # Vim mode
    mode: EditorMode = EditorMode.NORMAL

    # Canvas/sprite dimensions
    cells: Dict[Tuple[int, int], Cell] = field(default_factory=dict)
    canvas_width: int = DEFAULT_CANVAS_WIDTH
    canvas_height: int = DEFAULT_CANVAS_HEIGHT

    # Sprite mode state
    sprite_name: str = "untitled"
    current_frame: int = 0
    frames: List[SpriteFrame] = field(default_factory=lambda: [SpriteFrame()])

    # Cursor
    cursor_x: int = 0
    cursor_y: int = 0

    # Viewport (for scrolling)
    viewport_x: int = 0
    viewport_y: int = 0

    # Current drawing state
    current_char: str = '#'
    current_fg: Tuple[int, int, int] = field(default_factory=lambda: DEFAULT_FG)
    current_bg: Optional[Tuple[int, int, int]] = None
    fg_color_idx: int = 0

    # Selection (VISUAL mode)
    selection_start: Optional[Tuple[int, int]] = None

    # Clipboard
    clipboard: Optional[Dict[Tuple[int, int], Cell]] = None

    # Command line
    command_buffer: str = ""

    # File state
    file_path: Optional[str] = None
    modified: bool = False

    # Status message
    status_message: str = ""
    status_message_time: float = 0.0

    # Cursor blink
    cursor_visible: bool = True
    cursor_blink_timer: float = 0.0

    # For multi-key sequences (like gg, dd)
    pending_key: Optional[str] = None

    # Palette state
    palette_category: int = 0
    palette_cursor: int = 0
    palette_scroll: int = 0
    recent_chars: List[str] = field(default_factory=list)
    last_selected_codepoint: int = 0x2500  # For vicinity mode
    codepoint_buffer: str = ""             # For typing codepoints

    # Animation state
    animations: Dict[str, AnimationDef] = field(default_factory=dict)
    current_animation: Optional[str] = None  # Currently selected animation name
    animation_playing: bool = False          # Whether animation is auto-playing
    animation_timer: float = 0.0             # For frame timing
    animation_frame_idx: int = 0             # Current position in animation sequence

    # Animation editor state
    anim_editor_cursor: int = 0              # Selected animation in list
    anim_editor_frame_cursor: int = 0        # Selected frame within animation
    anim_editor_mode: str = "list"           # "list" or "edit"

    def get_cell(self, x: int, y: int) -> Optional[Cell]:
        return self.cells.get((x, y))

    def set_cell(self, x: int, y: int, cell: Cell):
        if cell.is_empty():
            self.cells.pop((x, y), None)
        else:
            self.cells[(x, y)] = cell
        self.modified = True

    def clear_cell(self, x: int, y: int):
        if (x, y) in self.cells:
            del self.cells[(x, y)]
            self.modified = True

    def clamp_cursor(self):
        self.cursor_x = max(0, min(self.canvas_width - 1, self.cursor_x))
        self.cursor_y = max(0, min(self.canvas_height - 1, self.cursor_y))

    def set_status(self, msg: str):
        self.status_message = msg
        self.status_message_time = 10.0  # Show for 10 seconds


# ============================================================================
# GLOBAL STATE
# ============================================================================

state = EditorState()
root = None           # Root window (background)
sprite_win = None     # Sprite editing window
status_win = None     # Status bar window (high z-index)
preview_sprite = None # Pyunicodegame sprite for animation preview


# ============================================================================
# MODE DISPLAY
# ============================================================================

MODE_DISPLAY = {
    EditorMode.NORMAL: ("-- NORMAL --", COLOR_NORMAL),
    EditorMode.INSERT: ("-- INSERT --", COLOR_INSERT),
    EditorMode.VISUAL: ("-- VISUAL --", COLOR_VISUAL),
    EditorMode.COMMAND: (":", COLOR_COMMAND),
    EditorMode.PALETTE_CATEGORIES: ("-- PALETTE --", COLOR_PALETTE),
    EditorMode.PALETTE_QWERTY: ("-- PALETTE --", COLOR_PALETTE),
    EditorMode.PALETTE_CODEPOINT: ("-- CODEPOINT --", COLOR_PALETTE),
    EditorMode.LINE: ("-- LINE --", (100, 255, 255)),
    EditorMode.BOX: ("-- BOX --", (255, 100, 200)),
    EditorMode.HELP: ("-- HELP --", (255, 255, 255)),
    EditorMode.ANIMATION_EDITOR: ("-- ANIMATION --", (255, 150, 50)),
    EditorMode.ANIMATION_PREVIEW: ("-- PREVIEW --", (100, 255, 100)),
}


# ============================================================================
# RENDERING
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
    root.put_string(sx, sy, '┌' + '─' * state.canvas_width + '┐', frame_color)
    root.put_string(sx, sy + box_h - 1, '└' + '─' * state.canvas_width + '┘', frame_color)

    # Sides
    for y in range(1, box_h - 1):
        root.put(sx, sy + y, '│', frame_color)
        root.put(sx + box_w - 1, sy + y, '│', frame_color)


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
                sprite_win.put(vx, vy, '█', cell.bg)
            sprite_win.put(vx, vy, cell.char, cell.fg)

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
                sprite_win.put(cx, cy, '█', COLOR_CURSOR_INSERT)
                if char_under != ' ':
                    sprite_win.put(cx, cy, char_under, (0, 0, 0))
            else:
                # Underline-style cursor in normal mode
                sprite_win.put(cx, cy, '▁', COLOR_CURSOR)

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
                    sprite_win.put(vx, vy, char if char != ' ' else '░', COLOR_VISUAL)


def get_current_category_chars():
    """Get the current category name and chars, handling vicinity mode."""
    if state.palette_category == -1:  # Vicinity mode
        return "Vicinity", generate_vicinity_chars(state.last_selected_codepoint, 80)
    elif 0 <= state.palette_category < len(PALETTE_CATEGORIES):
        return PALETTE_CATEGORIES[state.palette_category]
    else:
        return "Unknown", []


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


def render_mini_palette():
    """Render the mini palette bar above status on status window"""
    palette_row = 0  # First row of status window
    w = ROOT_WIDTH

    # Show recent chars (1-9 to select)
    recent = state.recent_chars[:9]
    if recent:
        preview = ''.join(recent)
        status_win.put_string(1, palette_row, "Recent:", COLOR_STATUS_DIM)
        status_win.put_string(9, palette_row, preview, state.current_fg)
    else:
        status_win.put_string(1, palette_row, "(no recent chars)", COLOR_STATUS_DIM)

    # Show hint with codepoint on right side
    code = ord(state.current_char)
    hint = f"U+{code:04X} [p]alette"
    status_win.put_string(w - len(hint) - 1, palette_row, hint, (80, 80, 100))


def render_status_bar():
    """Render the status bar on status window"""
    status_row = 1  # Second row of status window (after mini palette)
    w = ROOT_WIDTH

    # Editor mode indicator (SPRITE or SCENE)
    if state.editor_mode == "sprite":
        editor_mode_text = "SPRITE"
        editor_mode_color = (100, 200, 255)
    else:
        editor_mode_text = "SCENE"
        editor_mode_color = (200, 255, 100)
    status_win.put_string(0, status_row, editor_mode_text, editor_mode_color)

    # Vim mode indicator
    mode_text, mode_color = MODE_DISPLAY[state.mode]
    status_win.put_string(8, status_row, mode_text, mode_color)

    # Position
    pos_text = f"{state.cursor_x},{state.cursor_y}"
    status_win.put_string(22, status_row, pos_text, COLOR_STATUS_DIM)

    # Frame info (sprite mode only)
    if state.editor_mode == "sprite" and len(state.frames) > 1:
        frame_text = f"F{state.current_frame + 1}/{len(state.frames)}"
        if state.animation_playing:
            if state.current_animation:
                frame_text = f"[{state.current_animation}] {frame_text} ▶"
            else:
                frame_text = f"{frame_text} ▶"
            status_win.put_string(30, status_row, frame_text, (100, 255, 100))
        else:
            status_win.put_string(30, status_row, frame_text, (150, 150, 200))

    # Current character with color indicator (adjust position based on frame text)
    char_pos = 50 if state.animation_playing and state.current_animation else 40 if len(state.frames) > 1 else 32
    status_win.put(char_pos, status_row, state.current_char, state.current_fg)

    # Sprite name or file path (right-aligned, leave room for char display)
    if state.editor_mode == "sprite":
        name_text = f"{state.sprite_name} {state.canvas_width}x{state.canvas_height}"
    else:
        name_text = state.file_path if state.file_path else "[untitled]"

    if state.modified:
        name_text += "[+]"

    # Right-align name
    name_x = w - len(name_text) - 1
    status_win.put_string(name_x, status_row, name_text, COLOR_STATUS_DIM)

    # Status message (temporary) - on next row
    if state.status_message and state.status_message_time > 0:
        msg_x = (w - len(state.status_message)) // 2
        status_win.put_string(msg_x, status_row + 1, state.status_message, COLOR_STATUS_BRIGHT)


def render_command_line():
    """Render the command line input on status window"""
    cmd_row = 2  # Third row of status window
    w = ROOT_WIDTH

    # Draw prompt and buffer
    prompt = ":"
    status_win.put_string(0, cmd_row, prompt + state.command_buffer, COLOR_COMMAND)

    # Cursor at end of input
    cursor_x = len(prompt) + len(state.command_buffer)
    status_win.put(cursor_x, cmd_row, '█', COLOR_COMMAND)


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


def render_palette_categories():
    """Render the category selection screen (Screen 1)"""
    # Hide other windows during palette
    sprite_win.visible = False
    status_win.visible = False

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
            root.put(x, y, ' ', (20, 20, 30))

    # Title
    title = "CHARACTER PALETTE"
    root.put_string((w - len(title)) // 2, 1, title, title_color)
    root.put_string(0, 2, "═" * w, (60, 60, 80))

    # Update dynamic categories
    PALETTE_CATEGORIES[0] = ('Recent', state.recent_chars[:40])

    # Clamp category to valid range
    if state.palette_category < 0:
        state.palette_category = 0
    elif state.palette_category >= len(PALETTE_CATEGORIES):
        state.palette_category = len(PALETTE_CATEGORIES) - 1

    # Calculate visible range for scrolling
    visible_rows = h - 8  # Leave room for header, special options, and footer
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
        root.put_string(2, y, f"{hotkey}-", hotkey_color)

        # Selection indicator
        if is_selected:
            root.put(5, y, '▶', selected_color)
            name_color = selected_color
        else:
            name_color = normal_color

        # Category name
        root.put_string(7, y, cat_name[:12].ljust(12), name_color)

        # Preview chars (first 18)
        preview = ''.join(cat_chars[:18]) if cat_chars else "(empty)"
        root.put_string(20, y, preview[:36], preview_color)

        y += 1

    # Special options row (fixed position above footer)
    special_y = h - 4
    root.put_string(2, special_y, "─" * 54, (60, 60, 80))
    special_y += 1

    # Vicinity option
    root.put_string(2, special_y, "[v]icinity", heading_color)

    # Random and Codepoint on same line
    root.put_string(24, special_y, "[r]andom", heading_color)
    root.put_string(36, special_y, "[u] U+codepoint", heading_color)

    # Footer
    root.put_string(0, h - 2, "═" * w, (60, 60, 80))
    footer = "j/k =/- hotkey  Enter:select  Esc:cancel"
    root.put_string((w - len(footer)) // 2, h - 1, footer, (100, 100, 120))


def render_palette_qwerty():
    """Render the QWERTY keyboard picker (Screen 2)"""
    # Hide other windows
    sprite_win.visible = False
    status_win.visible = False

    w, h = ROOT_WIDTH, ROOT_HEIGHT
    title_color = (100, 200, 255)
    key_color = (80, 80, 100)
    char_color = (200, 200, 255)
    empty_color = (50, 50, 60)

    # Background
    for y in range(h):
        for x in range(w):
            root.put(x, y, ' ', (20, 20, 30))

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
    root.put_string(2, 1, title, title_color)
    root.put_string(w - 6, 1, "[Esc]", (100, 100, 120))
    root.put_string(0, 2, "═" * w, (60, 60, 80))

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
            root.put(x + 1, y, key, key_color)

            # Draw character (centered)
            if char:
                root.put(x + 1, y + 1, char, char_color)
            else:
                root.put(x + 1, y + 1, '·', empty_color)

            char_idx += 1
            x += cell_width

    # Show shift hint if more chars available
    if len(cat_chars) > 40:
        if shift_held:
            shift_hint = "Release Shift for chars 1-40"
        else:
            shift_hint = f"Hold Shift for chars 41-{min(80, len(cat_chars))}"
        root.put_string(4, start_y + 13, shift_hint, (150, 150, 180))

    # Current character info
    info_y = h - 4
    root.put_string(4, info_y, f"Current: {state.current_char}", (150, 200, 150))
    code = ord(state.current_char)
    root.put_string(20, info_y, f"U+{code:04X}", (120, 120, 140))

    # Footer
    root.put_string(0, h - 2, "═" * w, (60, 60, 80))
    footer = "Press key to select   Hold Shift for more   Esc:back"
    root.put_string((w - len(footer)) // 2, h - 1, footer, (100, 100, 120))


def render_palette_codepoint():
    """Render the codepoint entry screen"""
    # Hide other windows
    sprite_win.visible = False
    status_win.visible = False

    w, h = ROOT_WIDTH, ROOT_HEIGHT
    title_color = (100, 200, 255)

    # Background
    for y in range(h):
        for x in range(w):
            root.put(x, y, ' ', (20, 20, 30))

    # Title
    title = "ENTER CODEPOINT"
    root.put_string((w - len(title)) // 2, 1, title, title_color)
    root.put_string(0, 2, "═" * w, (60, 60, 80))

    # Input prompt
    prompt_y = h // 2 - 2
    root.put_string(10, prompt_y, "Enter hex codepoint:", (180, 180, 180))

    # Input field
    input_y = prompt_y + 2
    root.put_string(10, input_y, "U+", (150, 150, 200))
    root.put_string(12, input_y, state.codepoint_buffer.upper().ljust(6, '_'), (100, 255, 100))
    root.put(12 + len(state.codepoint_buffer), input_y, '█', (100, 255, 100))

    # Preview character if valid
    if state.codepoint_buffer:
        try:
            cp = int(state.codepoint_buffer, 16)
            if 0x20 <= cp <= 0x10FFFF:
                char = chr(cp)
                root.put_string(10, input_y + 2, "Preview: ", (150, 150, 180))
                root.put(19, input_y + 2, char, (200, 200, 255))
        except (ValueError, OverflowError):
            root.put_string(10, input_y + 2, "Invalid codepoint", (255, 100, 100))

    # Footer
    root.put_string(0, h - 2, "═" * w, (60, 60, 80))
    footer = "0-9, a-f: type   Enter: select   Esc: cancel"
    root.put_string((w - len(footer)) // 2, h - 1, footer, (100, 100, 120))


def render_help_overlay():
    """Render full-screen help overlay"""
    # Hide other windows during help
    sprite_win.visible = False
    status_win.visible = False

    w, h = ROOT_WIDTH, ROOT_HEIGHT
    title_color = (100, 200, 255)
    heading_color = (255, 200, 100)
    key_color = (100, 255, 100)
    desc_color = (180, 180, 180)

    # Background
    for y in range(h):
        for x in range(w):
            root.put(x, y, ' ', (30, 30, 40))

    # Title
    title = "SPRITE & SCENE EDITOR - HELP"
    root.put_string((w - len(title)) // 2, 1, title, title_color)
    root.put_string(0, 2, "═" * w, (60, 60, 80))

    # Left column: x=2-28, right column: x=31-58
    # Keys at col+2, descriptions at col+12

    y = 4
    # Navigation
    root.put_string(2, y, "NAVIGATION", heading_color); y += 1
    root.put_string(4, y, "hjkl", key_color); root.put_string(14, y, "Move cursor", desc_color); y += 1
    root.put_string(4, y, "0 / $", key_color); root.put_string(14, y, "Line start/end", desc_color); y += 1
    root.put_string(4, y, "gg / G", key_color); root.put_string(14, y, "Top/bottom", desc_color); y += 2

    # Drawing
    root.put_string(2, y, "DRAWING", heading_color); y += 1
    root.put_string(4, y, "Space", key_color); root.put_string(14, y, "Stamp char", desc_color); y += 1
    root.put_string(4, y, "i", key_color); root.put_string(14, y, "Insert mode", desc_color); y += 1
    root.put_string(4, y, "x", key_color); root.put_string(14, y, "Delete char", desc_color); y += 1
    root.put_string(4, y, "c", key_color); root.put_string(14, y, "Pick char", desc_color); y += 1
    root.put_string(4, y, "f", key_color); root.put_string(14, y, "Cycle color", desc_color); y += 2

    # Palette - right column
    y2 = 4
    root.put_string(31, y2, "PALETTE (p)", heading_color); y2 += 1
    root.put_string(33, y2, "j/k", key_color); root.put_string(44, y2, "Navigate cats", desc_color); y2 += 1
    root.put_string(33, y2, "Enter", key_color); root.put_string(44, y2, "QWERTY picker", desc_color); y2 += 1
    root.put_string(33, y2, "r", key_color); root.put_string(44, y2, "Random char", desc_color); y2 += 1
    root.put_string(33, y2, "u", key_color); root.put_string(44, y2, "U+codepoint", desc_color); y2 += 2

    # Visual mode
    root.put_string(31, y2, "VISUAL MODE", heading_color); y2 += 1
    root.put_string(33, y2, "v", key_color); root.put_string(44, y2, "Start select", desc_color); y2 += 1
    root.put_string(33, y2, "y", key_color); root.put_string(44, y2, "Yank (copy)", desc_color); y2 += 1
    root.put_string(33, y2, "d", key_color); root.put_string(44, y2, "Delete", desc_color); y2 += 1
    root.put_string(33, y2, "r", key_color); root.put_string(44, y2, "Fill with char", desc_color); y2 += 1
    root.put_string(33, y2, "P", key_color); root.put_string(44, y2, "Paste yanked", desc_color); y2 += 2

    # Commands
    root.put_string(31, y2, "COMMANDS", heading_color); y2 += 1
    root.put_string(33, y2, ":sprite N WxH", key_color); root.put_string(48, y2, "New sprite", desc_color); y2 += 1
    root.put_string(33, y2, ":w file", key_color); root.put_string(48, y2, "Save", desc_color); y2 += 1
    root.put_string(33, y2, ":q :wq", key_color); root.put_string(48, y2, "Quit", desc_color); y2 += 1
    root.put_string(33, y2, ":frame", key_color); root.put_string(48, y2, "Add frame", desc_color); y2 += 1
    root.put_string(33, y2, ":anim", key_color); root.put_string(48, y2, "Animation editor", desc_color); y2 += 1

    # Animation (continued in left column)
    root.put_string(2, y, "ANIMATION", heading_color); y += 1
    root.put_string(4, y, ", .", key_color); root.put_string(14, y, "Prev/next frame", desc_color); y += 1
    root.put_string(4, y, "Tab", key_color); root.put_string(14, y, "Play/stop anim", desc_color); y += 1

    # Footer
    root.put_string(0, h - 2, "═" * w, (60, 60, 80))
    footer = "Press any key to close"
    root.put_string((w - len(footer)) // 2, h - 1, footer, (150, 150, 150))


def render_animation_editor():
    """Render full-screen animation assembly editor"""
    # Hide other windows during animation editor
    sprite_win.visible = False
    status_win.visible = False

    w, h = ROOT_WIDTH, ROOT_HEIGHT
    title_color = (255, 150, 50)
    heading_color = (255, 200, 100)
    selected_color = (100, 255, 100)
    normal_color = (180, 180, 180)
    dim_color = (100, 100, 120)

    # Background
    for y in range(h):
        for x in range(w):
            root.put(x, y, ' ', (30, 30, 40))

    # Title
    title = "ANIMATION EDITOR"
    root.put_string((w - len(title)) // 2, 1, title, title_color)
    root.put_string(0, 2, "═" * w, (60, 60, 80))

    # Get list of animations
    anim_names = sorted(state.animations.keys()) if state.animations else []

    if state.anim_editor_mode == "list":
        # Left side: Animation list
        root.put_string(2, 4, "ANIMATIONS", heading_color)
        root.put_string(2, 5, "─" * 20, dim_color)

        if not anim_names:
            root.put_string(2, 7, "(no animations)", dim_color)
            root.put_string(2, 8, "Press 'n' to create", dim_color)
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
                root.put_string(2, y, f"{prefix} {name}", color)
                root.put_string(20, y, f"{frame_count}f {loop_indicator}", dim_color)

        # Right side: Selected animation details
        root.put_string(32, 4, "DETAILS", heading_color)
        root.put_string(32, 5, "─" * 25, dim_color)

        if anim_names and 0 <= state.anim_editor_cursor < len(anim_names):
            anim_name = anim_names[state.anim_editor_cursor]
            anim = state.animations[anim_name]
            root.put_string(32, 7, f"Name: {anim_name}", normal_color)
            root.put_string(32, 8, f"Duration: {anim.frame_duration:.2f}s/frame", normal_color)
            root.put_string(32, 9, f"Loop: {'Yes' if anim.loop else 'No'}", normal_color)
            root.put_string(32, 10, f"Frames: {len(anim.frames)}", normal_color)

            # Show frame sequence
            root.put_string(32, 12, "Sequence:", heading_color)
            seq = " ".join(f"F{af.frame_index+1}" + (f"({af.offset_x},{af.offset_y})" if af.offset_x or af.offset_y else "")
                         for af in anim.frames[:8])
            if len(anim.frames) > 8:
                seq += "..."
            root.put_string(32, 13, seq[:26], dim_color)
        else:
            root.put_string(32, 7, "(select an animation)", dim_color)

    else:  # edit mode
        # Show frame editing for selected animation
        if anim_names and 0 <= state.anim_editor_cursor < len(anim_names):
            anim_name = anim_names[state.anim_editor_cursor]
            anim = state.animations[anim_name]

            root.put_string(2, 4, f"EDITING: {anim_name}", heading_color)
            # Show duration and loop status
            root.put_string(25, 4, f"Duration: {anim.frame_duration:.2f}s", normal_color)
            root.put_string(45, 4, f"Loop: {'ON' if anim.loop else 'OFF'}", selected_color if anim.loop else dim_color)
            root.put_string(2, 5, "─" * 56, dim_color)

            # Show frames in animation
            root.put_string(2, 7, "FRAMES IN ANIMATION", heading_color)
            root.put_string(2, 8, "Frame   Offset", dim_color)
            if not anim.frames:
                root.put_string(2, 10, "(empty - press 1-9 to add frames)", dim_color)
            for i, af in enumerate(anim.frames):
                y = 10 + i
                if y >= h - 6:
                    break
                is_selected = i == state.anim_editor_frame_cursor
                color = selected_color if is_selected else normal_color
                prefix = ">" if is_selected else " "
                offset_str = f"({af.offset_x:+d},{af.offset_y:+d})"
                root.put_string(2, y, f"{prefix} F{af.frame_index + 1}", color)
                root.put_string(10, y, offset_str, color)

            # Show available sprite frames on right
            root.put_string(32, 7, f"SPRITE FRAMES (1-{min(len(state.frames), 9)})", heading_color)
            for i in range(min(len(state.frames), 9)):
                marker = "+" if any(af.frame_index == i for af in anim.frames) else " "
                root.put_string(32, 9 + i, f"{marker} {i+1}: Frame {i + 1}", dim_color)

    # Controls at bottom
    root.put_string(0, h - 5, "═" * w, (60, 60, 80))
    if state.anim_editor_mode == "list":
        root.put_string(2, h - 4, "j/k:Navigate  n:New  Enter:Edit  d:Delete  Space:Preview  Esc:Close", dim_color)
    else:
        root.put_string(2, h - 4, "1-9:Add frame  a:Add current  d:Remove  j/k:Select  [/]:Reorder", dim_color)
        root.put_string(2, h - 3, "h/l:X offset  J/K:Y offset (shift)  0:Reset offset", dim_color)
        root.put_string(2, h - 2, "+/-:Duration  L:Loop toggle  Space:Preview  Esc:Back", dim_color)


def start_animation_preview():
    """Create real pyunicodegame sprite for animation preview"""
    global preview_sprite

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
    preview_sprite = pyunicodegame.Sprite(pug_frames, fg=DEFAULT_FG)

    # Center it on screen
    center_x = (ROOT_WIDTH - state.canvas_width) // 2
    center_y = (ROOT_HEIGHT - state.canvas_height) // 2
    preview_sprite.x = center_x
    preview_sprite.y = center_y
    preview_sprite._teleport_pending = True

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
    preview_sprite.add_animation(pug_anim)
    preview_sprite.play_animation(anim_def.name)

    # Add to root window for rendering
    root.add_sprite(preview_sprite)


def stop_animation_preview():
    """Clean up animation preview sprite"""
    global preview_sprite

    if preview_sprite and root:
        root.remove_sprite(preview_sprite)
        preview_sprite = None


def render_animation_preview():
    """Render full-screen animation preview using real pyunicodegame sprite"""
    sprite_win.visible = False
    status_win.visible = False

    w, h = ROOT_WIDTH, ROOT_HEIGHT

    # Clear background - the sprite will render on top automatically
    for y in range(h):
        for x in range(w):
            root.put(x, y, ' ', (20, 20, 30))

    # Show help at bottom
    help_text = "Press Space/Esc/Q to exit preview"
    root.put_string((w - len(help_text)) // 2, h - 1, help_text, (100, 100, 120))


# ============================================================================
# INPUT HANDLING
# ============================================================================

def on_key(key):
    """Handle keyboard input based on current mode"""
    if state.mode == EditorMode.HELP:
        # Any key closes help
        state.mode = EditorMode.NORMAL
        sprite_win.visible = True
        status_win.visible = True
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


def handle_animation_preview(key):
    """Handle keys in animation preview mode"""
    if is_escape(key) or key == pygame.K_SPACE or key == pygame.K_q:
        # Stop animation and return to editor
        stop_animation_preview()
        state.animation_playing = False
        state.mode = EditorMode.ANIMATION_EDITOR
        sprite_win.visible = False
        status_win.visible = False


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
            sprite_win.visible = True
            status_win.visible = True
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
            else:
                # Navigate down in frame list
                if anim.frames:
                    state.anim_editor_frame_cursor = (state.anim_editor_frame_cursor + 1) % len(anim.frames)

        elif key in (pygame.K_k, pygame.K_UP):
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                # Shift+K: Increase Y offset (move up visually)
                if anim.frames and 0 <= state.anim_editor_frame_cursor < len(anim.frames):
                    anim.frames[state.anim_editor_frame_cursor].offset_y -= 1
            else:
                # Navigate up in frame list
                if anim.frames:
                    state.anim_editor_frame_cursor = (state.anim_editor_frame_cursor - 1) % len(anim.frames)

        elif key == pygame.K_h:
            # Decrease X offset
            if anim.frames and 0 <= state.anim_editor_frame_cursor < len(anim.frames):
                anim.frames[state.anim_editor_frame_cursor].offset_x -= 1

        elif key == pygame.K_l:
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                # Shift+L: Toggle loop
                anim.loop = not anim.loop
                state.set_status(f"Loop: {'On' if anim.loop else 'Off'}")
            else:
                # Increase X offset
                if anim.frames and 0 <= state.anim_editor_frame_cursor < len(anim.frames):
                    anim.frames[state.anim_editor_frame_cursor].offset_x += 1

        elif key == pygame.K_a:
            # Add current sprite frame to animation
            anim.frames.append(AnimationFrame(frame_index=state.current_frame))
            state.anim_editor_frame_cursor = len(anim.frames) - 1
            state.set_status(f"Added frame {state.current_frame + 1}")

        elif key == pygame.K_d:
            # Remove selected frame from animation
            if anim.frames and 0 <= state.anim_editor_frame_cursor < len(anim.frames):
                del anim.frames[state.anim_editor_frame_cursor]
                state.anim_editor_frame_cursor = max(0, min(state.anim_editor_frame_cursor, len(anim.frames) - 1))
                state.set_status("Frame removed")

        elif key == pygame.K_LEFTBRACKET:
            # Move frame earlier in sequence
            if anim.frames and state.anim_editor_frame_cursor > 0:
                i = state.anim_editor_frame_cursor
                anim.frames[i], anim.frames[i-1] = anim.frames[i-1], anim.frames[i]
                state.anim_editor_frame_cursor -= 1

        elif key == pygame.K_RIGHTBRACKET:
            # Move frame later in sequence
            if anim.frames and state.anim_editor_frame_cursor < len(anim.frames) - 1:
                i = state.anim_editor_frame_cursor
                anim.frames[i], anim.frames[i+1] = anim.frames[i+1], anim.frames[i]
                state.anim_editor_frame_cursor += 1

        elif key == pygame.K_0:
            # Reset offset to (0, 0)
            if anim.frames and 0 <= state.anim_editor_frame_cursor < len(anim.frames):
                anim.frames[state.anim_editor_frame_cursor].offset_x = 0
                anim.frames[state.anim_editor_frame_cursor].offset_y = 0
                state.set_status("Offset reset")

        elif key == pygame.K_EQUALS:
            # Increase animation duration
            anim.frame_duration = min(5.0, anim.frame_duration + 0.05)
            state.set_status(f"Duration: {anim.frame_duration:.2f}s")

        elif key == pygame.K_MINUS:
            # Decrease animation duration
            anim.frame_duration = max(0.02, anim.frame_duration - 0.05)
            state.set_status(f"Duration: {anim.frame_duration:.2f}s")

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
    sprite_win.visible = True
    status_win.visible = True
    state.set_status(f"Selected: {char} (Space to stamp)")


def handle_palette_categories(key):
    """Handle keys in PALETTE_CATEGORIES mode (category list screen)"""
    if is_escape(key):
        state.mode = EditorMode.NORMAL
        sprite_win.visible = True
        status_win.visible = True
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
            load_file(args)

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

    elif command == 'frame':
        handle_frame_command(args)

    elif command == 'frames':
        # List all frames
        state.set_status(f"Frames: {len(state.frames)} (current: {state.current_frame + 1})")

    elif command in ('anim', 'animation'):
        handle_anim_command(args)

    elif command == 'set':
        handle_set_command(args)

    elif command == 'color':
        handle_color_command(args)

    elif command == 'help':
        state.mode = EditorMode.HELP

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
        sprite_win.visible = False
        status_win.visible = False

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
# FILE I/O (Python Code Format)
# ============================================================================

def save_file(path: str):
    """Save as executable Python code (sprite or scene format)"""
    if not path.endswith('.py'):
        path += '.py'

    try:
        # Save current cells to current frame before saving
        if state.editor_mode == "sprite":
            state.frames[state.current_frame].cells = dict(state.cells)
            code = generate_sprite_code(path)
        else:
            code = generate_scene_code(path)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(code)

        state.file_path = path
        state.modified = False
        state.set_status(f"Saved: {path}")
    except Exception as e:
        state.set_status(f"Error saving: {e}")


def generate_sprite_code(filename: str) -> str:
    """Generate sprite library Python code with SPRITE_DEFS"""
    lines = [
        '#!/usr/bin/env python3',
        '"""',
        f'Sprite Library - Generated by scene_editor',
        '"""',
        '',
        'import pyunicodegame',
        '',
        '',
        '# Sprite definitions for editor reload and runtime use',
        'SPRITE_DEFS = {',
    ]

    # Build sprite definition
    sprite_name = state.sprite_name
    lines.append(f"    {repr(sprite_name)}: {{")
    lines.append(f"        'width': {state.canvas_width},")
    lines.append(f"        'height': {state.canvas_height},")
    lines.append(f"        'default_fg': {state.current_fg},")
    lines.append("        'frames': [")

    # Add each frame
    for frame_idx, frame in enumerate(state.frames):
        frame_dict = frame.to_dict(state.canvas_width, state.canvas_height)

        lines.append("            {")
        # Format chars as 2D array
        lines.append("                'chars': [")
        for row in frame_dict['chars']:
            row_repr = '[' + ', '.join(repr(c) for c in row) + ']'
            lines.append(f"                    {row_repr},")
        lines.append("                ],")

        # Format fg_colors (only include non-None values for readability)
        lines.append("                'fg_colors': [")
        for row in frame_dict['fg_colors']:
            row_repr = '[' + ', '.join(str(c) if c else 'None' for c in row) + ']'
            lines.append(f"                    {row_repr},")
        lines.append("                ],")
        lines.append("            },")

    lines.append("        ],")

    # Add animations if any
    if state.animations:
        lines.append("        'animations': {")
        for anim_name, anim in sorted(state.animations.items()):
            # 3-tuple: (frame_index, offset_x, offset_y)
            frames_repr = ', '.join(
                f"({af.frame_index}, {af.offset_x}, {af.offset_y})"
                for af in anim.frames
            )
            lines.append(f"            {repr(anim_name)}: {{")
            lines.append(f"                'frames': [{frames_repr}],")
            lines.append(f"                'frame_duration': {anim.frame_duration},")
            lines.append(f"                'loop': {anim.loop},")
            lines.append("            },")
        lines.append("        },")

    lines.append("    },")
    lines.append("}")
    lines.append("")
    lines.append("")

    # Add helper function
    lines.extend([
        "def create_sprite(name: str, x: int, y: int):",
        '    """Create a pyunicodegame sprite from definition."""',
        "    defn = SPRITE_DEFS[name]",
        "    frame = defn['frames'][0]",
        "    pattern = '\\n'.join(''.join(row) for row in frame['chars'])",
        "    sprite = pyunicodegame.create_sprite(pattern, x, y, fg=defn['default_fg'])",
        "    # Add additional frames if present",
        "    for f in defn['frames'][1:]:",
        "        pattern = '\\n'.join(''.join(row) for row in f['chars'])",
        "        sprite.add_frame(pattern)",
        "    return sprite",
        "",
        "",
    ])

    # Add demo main function
    lines.extend([
        "def main():",
        f'    """Demo: display the sprite"""',
        f"    root = pyunicodegame.init(",
        f'        "Sprite: {sprite_name}",',
        f"        width={max(20, state.canvas_width + 4)},",
        f"        height={max(10, state.canvas_height + 4)},",
        f"        bg=(10, 10, 20, 255)",
        f"    )",
        "",
        f"    sprite = create_sprite({repr(sprite_name)}, 2, 2)",
        "    root.add_sprite(sprite)",
        "",
        "    def on_key(key):",
        "        import pygame",
        "        if key == pygame.K_q:",
        "            pyunicodegame.quit()",
        "",
        "    pyunicodegame.run(on_key=on_key)",
        "",
        "",
        'if __name__ == "__main__":',
        '    main()',
        '',
    ])

    return '\n'.join(lines)


def generate_scene_code(filename: str) -> str:
    """Generate executable Python code for the scene"""
    lines = [
        '#!/usr/bin/env python3',
        '"""',
        f'Scene: {filename} - Generated by scene_editor',
        '"""',
        '',
        'import pygame',
        'import pyunicodegame',
        '',
        '',
        'def render_scene(window):',
        '    """Render the scene to a window"""',
    ]

    # Group cells by row for cleaner output
    rows = {}
    for (x, y), cell in sorted(state.cells.items()):
        if y not in rows:
            rows[y] = []
        rows[y].append((x, cell))

    if rows:
        for y in sorted(rows.keys()):
            lines.append(f'    # Row {y}')
            for x, cell in rows[y]:
                char_repr = repr(cell.char)
                fg_repr = str(cell.fg)
                if cell.bg:
                    lines.append(f'    window.put({x}, {y}, {char_repr}, {fg_repr})  # bg: {cell.bg}')
                else:
                    lines.append(f'    window.put({x}, {y}, {char_repr}, {fg_repr})')
    else:
        lines.append('    pass  # Empty scene')

    lines.extend([
        '',
        '',
        'def main():',
        f'    root = pyunicodegame.init(',
        f'        "Scene",',
        f'        width={state.canvas_width},',
        f'        height={state.canvas_height},',
        f'        bg=(10, 10, 20, 255)',
        f'    )',
        '',
        '    def render():',
        '        render_scene(root)',
        '',
        '    def on_key(key):',
        '        if key == pygame.K_q:',
        '            pyunicodegame.quit()',
        '',
        '    pyunicodegame.run(render=render, on_key=on_key)',
        '',
        '',
        '# Scene metadata for editor reload',
        '_SCENE_META = {',
        f"    'width': {state.canvas_width},",
        f"    'height': {state.canvas_height},",
        "    'cells': {",
    ])

    # Add cell data for reloading
    for (x, y), cell in sorted(state.cells.items()):
        char_repr = repr(cell.char)
        fg_repr = str(cell.fg)
        bg_repr = str(cell.bg) if cell.bg else 'None'
        lines.append(f"        ({x}, {y}): {{'char': {char_repr}, 'fg': {fg_repr}, 'bg': {bg_repr}}},")

    lines.extend([
        '    }',
        '}',
        '',
        '',
        'if __name__ == "__main__":',
        '    main()',
        '',
    ])

    return '\n'.join(lines)


def load_file(path: str):
    """Load sprite or scene from Python file"""
    if not path.endswith('.py'):
        path += '.py'

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Execute file to get metadata
        namespace = {}
        exec(content, namespace)

        # Check if it's a sprite file (has SPRITE_DEFS)
        if 'SPRITE_DEFS' in namespace:
            load_sprite_from_defs(path, namespace['SPRITE_DEFS'])
            return

        # Otherwise try scene format (_SCENE_META)
        if '_SCENE_META' not in namespace:
            state.set_status("No SPRITE_DEFS or _SCENE_META found")
            return

        meta = namespace['_SCENE_META']

        # Load canvas dimensions
        state.editor_mode = "scene"
        state.canvas_width = meta.get('width', DEFAULT_CANVAS_WIDTH)
        state.canvas_height = meta.get('height', DEFAULT_CANVAS_HEIGHT)

        # Load cells
        state.cells.clear()
        for (x, y), cell_data in meta.get('cells', {}).items():
            cell = Cell(
                char=cell_data['char'],
                fg=tuple(cell_data['fg']),
                bg=tuple(cell_data['bg']) if cell_data.get('bg') else None
            )
            state.cells[(x, y)] = cell

        state.file_path = path
        state.modified = False
        state.cursor_x = 0
        state.cursor_y = 0
        state.set_status(f"Loaded scene: {path} ({len(state.cells)} cells)")

    except FileNotFoundError:
        state.set_status(f"File not found: {path}")
    except Exception as e:
        state.set_status(f"Error loading: {e}")


def load_sprite_from_defs(path: str, sprite_defs: dict):
    """Load a sprite from SPRITE_DEFS format"""
    if not sprite_defs:
        state.set_status("SPRITE_DEFS is empty")
        return

    # Load the first sprite (or could be enhanced to let user choose)
    sprite_name = list(sprite_defs.keys())[0]
    defn = sprite_defs[sprite_name]

    state.editor_mode = "sprite"
    state.sprite_name = sprite_name
    state.canvas_width = defn.get('width', 8)
    state.canvas_height = defn.get('height', 6)
    state.current_fg = tuple(defn.get('default_fg', DEFAULT_FG))

    # Recreate sprite window with loaded dimensions
    setup_sprite_window()

    # Load frames
    state.frames = []
    for frame_data in defn.get('frames', [{}]):
        frame = SpriteFrame.from_dict(frame_data)
        state.frames.append(frame)

    if not state.frames:
        state.frames = [SpriteFrame()]

    # Load animations
    state.animations.clear()
    if 'animations' in defn:
        for anim_name, anim_data in defn['animations'].items():
            anim_frames = [
                AnimationFrame(frame_index=f[0], offset_x=f[1], offset_y=f[2])
                for f in anim_data.get('frames', [])
            ]
            state.animations[anim_name] = AnimationDef(
                name=anim_name,
                frames=anim_frames,
                frame_duration=anim_data.get('frame_duration', 0.2),
                loop=anim_data.get('loop', True),
            )

    # Load first frame into cells
    state.current_frame = 0
    state.cells = dict(state.frames[0].cells)

    state.file_path = path
    state.modified = False
    state.cursor_x = 0
    state.cursor_y = 0

    frame_info = f", {len(state.frames)} frames" if len(state.frames) > 1 else ""
    anim_info = f", {len(state.animations)} anims" if state.animations else ""
    state.set_status(f"Loaded sprite: {sprite_name} {state.canvas_width}x{state.canvas_height}{frame_info}{anim_info}")


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

    # In preview mode, use pyunicodegame's sprite animation system
    if state.mode == EditorMode.ANIMATION_PREVIEW and root:
        root.update_sprites(dt)
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
    global sprite_win

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
    sprite_win = pyunicodegame.create_window(
        "sprite",
        sx, sy,
        state.canvas_width, state.canvas_height,
        z_index=5,
        font_name="unifont",
        bg=(20, 20, 35, 255)
    )


def main():
    global root, state, sprite_win, status_win

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
    root = pyunicodegame.init(
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
    status_win = pyunicodegame.create_window(
        "status",
        0, ROOT_HEIGHT - STATUS_HEIGHT,
        ROOT_WIDTH, STATUS_HEIGHT,
        z_index=100,
        font_name="unifont",
        bg=(15, 15, 25, 255)
    )

    # Load file if specified
    if file_to_load:
        load_file(file_to_load)
    else:
        state.set_status(f":sprite name WxH to start | ? for help")

    # Run the editor
    pyunicodegame.run(update=update, render=render, on_key=on_key, on_event=on_event)


if __name__ == "__main__":
    main()
