# Animation/Multiframe Sprite Feature Implementation Plan

## Overview
Add support for named animation sequences in the sprite editor, with frame cycling during editing and animation playback in scene mode.

## Key Files
- `/Users/henry/Documents/github/fancyunicode/demos/scene_editor.py` (main file, all changes here)

## Data Structures

### 1. New `AnimationDef` dataclass (add after `SpriteFrame` ~line 241)
```python
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
    frames: List[AnimationFrame]  # Frames with offsets
    frame_duration: float = 0.2  # Seconds per frame
    loop: bool = True
```

### 2. Update `SpriteData` (line 243)
Add `animations: Dict[str, AnimationDef]` field to store named animations.

### 3. Update `EditorState` (line 275)
Add:
- `animations: Dict[str, AnimationDef]` - animation definitions
- `current_animation: Optional[str]` - currently selected animation name
- `animation_playing: bool` - whether animation is auto-playing
- `animation_timer: float` - for frame timing
- `animation_frame_idx: int` - current position in animation sequence

## New Editor Mode

### 4. Add `ANIMATION_EDITOR` mode to `EditorMode` enum (line 177)
Full-screen mode for assembling animations from frames.

## Frame Navigation (Normal Mode)

### 5. Add frame navigation keys in `handle_normal_mode()`
- `<` (Shift+comma): Previous frame
- `>` (Shift+period): Next frame
- `Tab`: Toggle animation playback (cycle through frames automatically)

## Animation Editor Screen

### 6. Add `render_animation_editor()` function
Full-screen overlay showing:
- Left column: List of all frames as thumbnails (mini previews)
- Right side: Current animation sequence being edited
  - Each frame shows: frame number, offset (x,y), mini preview at offset position
- Bottom: Controls and help

### 7. Add `handle_animation_editor()` function
Key bindings:
- `n`: New animation (prompts for name)
- `j/k`: Navigate animation list
- `Enter`: Edit selected animation
- `a`: Add current frame to animation
- `d`: Remove frame from animation
- `[/]`: Reorder frames in sequence
- `+/-`: Adjust frame duration
- `l`: Toggle loop
- `h/l` or arrow keys: Adjust selected frame's X offset (for lunges)
- `Shift+j/k` or Shift+arrows: Adjust selected frame's Y offset (for jumps)
- `0`: Reset offset to (0,0)
- `Space`: Preview animation
- `Esc`: Return to normal mode

## Commands

### 8. Add new commands in `handle_command()`
- `:anim` or `:animation` - Open animation editor screen
- `:anim new <name>` - Create new animation
- `:anim delete <name>` - Delete animation
- `:anim play <name>` - Preview animation in editor

## Rendering Updates

### 9. Update `render_status_bar()` (line 556)
Show current animation name and playback state when animation is playing.

### 10. Add animation playback in main loop
When `animation_playing` is True, advance frames based on timer.

## File Format Updates

### 11. Update `SpriteData.to_dict()` and `from_dict()`
Serialize/deserialize animations dictionary.

### 12. Update `generate_sprite_code()` (~line 1830)
Include animation definitions in generated code with per-frame offsets:
```python
sprite.add_animation("walk", [
    (0, 0, 0),   # (frame_index, offset_x, offset_y)
    (1, 2, 0),   # Slight lunge forward
    (2, 0, 0),
    (1, 2, 0),
], duration=0.15, loop=True)
sprite.add_animation("jump", [
    (0, 0, 0),   # Ground
    (1, 0, -4),  # Rising
    (2, 0, -8),  # Peak
    (1, 0, -4),  # Falling
    (0, 0, 0),   # Land
], duration=0.1, loop=False)
```

## Scene Mode Support

### 13. Scene mode animation playback
- When placing animated sprites in scene, store reference to sprite + animation name
- In scene render loop, auto-advance animation frames
- `Tab` key toggles animation pause/play in scene mode

## Implementation Order

1. Add `AnimationDef` dataclass and update `SpriteData`/`EditorState`
2. Add frame navigation keys (`<`/`>`) in normal mode
3. Add `Tab` toggle for auto-play frame cycling
4. Add `ANIMATION_EDITOR` mode and render function
5. Add animation editor key handling
6. Add `:anim` commands
7. Update save/load to persist animations
8. Add scene mode animation playback

## Status Bar Updates
- Show `F1/3` (current frame/total) in status bar (already exists)
- When animation playing: show `[walk] F2/4 (2,0) >` (animation name, frame position, offset, playing indicator)
- In animation editor: show selected frame's offset as `Offset: (2, -4)` with live preview
