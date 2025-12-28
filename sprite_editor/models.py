"""
Sprite & Scene Editor - Data models, constants, and global state
"""

import pygame
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Tuple, Optional, List, Any


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
    SPRITE_LIBRARY = auto()      # Sprite library management (scene mode)
    SPRITE_PICKER = auto()       # Sprite picker for placement (scene mode)


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
class SpriteLibraryEntry:
    """Reference to an external sprite definition file"""
    file_path: str              # Path to .py sprite file (relative to scene)
    sprite_names: List[str] = field(default_factory=list)  # Names within SPRITE_DEFS
    sprite_defs: dict = field(default_factory=dict)  # Cached SPRITE_DEFS from file


@dataclass
class SpriteInstance:
    """A placed sprite in the scene"""
    library_key: str            # "path/to/file.py:sprite_name"
    instance_id: str            # Unique ID (e.g., "hero_001")
    x: int
    y: int
    initial_animation: Optional[str] = None


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

    # Scene mode state
    sprite_library: Dict[str, SpriteLibraryEntry] = field(default_factory=dict)  # Loaded sprite files
    sprite_instances: Dict[str, SpriteInstance] = field(default_factory=dict)    # Placed sprites in scene
    scene_tool: str = "char"                        # "char" or "sprite"
    selected_library_sprite: Optional[str] = None   # Current sprite to place (library_key)
    sprite_library_cursor: int = 0                  # Cursor in library list
    sprite_picker_cursor: int = 0                   # Cursor in sprite picker
    instance_counter: int = 0                       # For generating unique instance IDs
    scene_preview_sprites: Dict[str, Any] = field(default_factory=dict)  # pyunicodegame sprites for scene preview
    help_page: int = 0                              # Current help page (0=general, 1=scene)

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
    EditorMode.SPRITE_LIBRARY: ("-- LIBRARY --", (100, 200, 255)),
    EditorMode.SPRITE_PICKER: ("-- SPRITES --", (255, 200, 100)),
}


# ============================================================================
# HELPER FUNCTIONS (used by both rendering and input handling)
# ============================================================================

def get_current_category_chars():
    """Get the current category name and chars, handling vicinity mode."""
    try:
        from .rendering import generate_vicinity_chars
    except ImportError:
        from rendering import generate_vicinity_chars
    if state.palette_category == -1:  # Vicinity mode
        return "Vicinity", generate_vicinity_chars(state.last_selected_codepoint, 80)
    elif 0 <= state.palette_category < len(PALETTE_CATEGORIES):
        return PALETTE_CATEGORIES[state.palette_category]
    else:
        return "Unknown", []


def get_all_library_sprites() -> List[Tuple[str, str, dict]]:
    """Get all sprites from all loaded libraries.

    Returns:
        List of (library_key, sprite_name, sprite_def) tuples
    """
    result = []
    for lib_path, entry in state.sprite_library.items():
        for sprite_name in entry.sprite_names:
            library_key = f"{lib_path}:{sprite_name}"
            sprite_def = entry.sprite_defs[sprite_name]
            result.append((library_key, sprite_name, sprite_def))
    return result
