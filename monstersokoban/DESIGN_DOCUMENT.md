# MonsterSokoban: Game Design Document

> A cooperative crafting game with traditional roguelike aesthetics where players control monsters in a persistent 2D grid world, pushing items around like Sokoban to craft goods for the betterment of monsterkind.

**Version**: 1.0  
**Date**: January 2026  
**Engine**: pyunicodegame (16x16 unifont unicode tiles)  
**Backend**: gridtickmultiplayer (1-second tick rate)

---

## Table of Contents

1. [Vision Statement](#1-vision-statement)
2. [Core Design Pillars](#2-core-design-pillars)
3. [Technical Foundation](#3-technical-foundation)
4. [World Design](#4-world-design)
5. [Monster System](#5-monster-system)
6. [Movement & Pushing Mechanics](#6-movement--pushing-mechanics)
7. [Crafting System](#7-crafting-system)
8. [Visual Effects Design](#8-visual-effects-design)
9. [UI/UX Design](#9-uiux-design)
10. [Multiplayer & Persistence](#10-multiplayer--persistence)
11. [User Journeys (100+)](#11-user-journeys)
12. [Future Considerations](#12-future-considerations)

---

## 1. Vision Statement

MonsterSokoban reimagines the MonsterMakers crafting economy as a physical, spatial experience. Instead of abstract menus and inventory management, players literally push items around a persistent world, deposit materials into crafting tables by shoving them in, and transport goods by loading wagons and pulling them across the map.

**The Core Fantasy**: You ARE a monster worker in a collectivist monster society. You physically gather resources, push them to workshops, and watch your crafted goods contribute to the greater good of monsterkind.

**Key Differentiators**:
- **Physical Item Presence**: Every item exists as a 1x1 cell object in the world
- **Sokoban-as-UI**: The puzzle-pushing mechanics ARE the interface
- **Minimal Menus**: Almost everything happens in-world via spatial interaction
- **Cooperative Persistence**: Changes you make persist for all players
- **Monster Switching**: Control one monster, leave others on batch tasks

---

## 2. Core Design Pillars

### 2.1 Physicality Over Abstraction
- Items aren't inventory entries - they're objects you push
- Crafting isn't a menu - it's pushing ingredients into a table
- Transport isn't instant - you load wagons and pull them

### 2.2 Readable at a Glance
- Quality visible through color tiers and badges
- Active processes shown via particles and light
- Monster status conveyed through sprites and auras

### 2.3 Cooperative, Not Competitive
- Shared resources benefit everyone
- Contributions tracked through shares
- Renown earned collectively

### 2.4 Depth Through Constraints
- Limited pushing (can only push, not pull items)
- Spatial puzzles emerge from workshop layouts
- Strategic planning required for efficient production chains

### 2.5 Respect for Time
- 1-second tick provides thinking time
- Batch tasks let you multitask across monsters
- Progression is meaningful but not punishing

---

## 3. Technical Foundation

### 3.1 Rendering (pyunicodegame)

**Cell Size**: 16x16 pixels (unifont duospace)  
**Resolution**: 80x50 cells (1280x800 pixels)  
**Frame Rate**: 60 FPS visuals, 1-second game ticks

**Key Features Used**:
- `Sprite` with `lerp_speed` for smooth item movement
- `EffectSprite` with velocity/drag/fade for feedback particles  
- `EffectSpriteEmitter` for continuous effects (crafting stations)
- `Light` with shadow casting for controlled monster aura
- `Window.set_bloom()` for highlighting important elements
- Multiple windows with `fixed=True` for UI panels

### 3.2 Backend (gridtickmultiplayer)

**Tick Rate**: 1000ms (1 second)  
**Architecture**: Authoritative server, intent-based actions  
**Persistence**: SQLite with zone/entity model

**Entity Model**:
```
Entity {
  id: UUID
  zone_id: UUID
  owner_id: UUID (monster's commune)
  x, y: int (cell position)
  metadata: {
    type: "item" | "monster" | "workshop" | "wagon"
    subtype: string (specific item/monster type)
    quality: float
    durability: int
    state: string (for workshops/wagons)
    ...
  }
}
```

### 3.3 Intent System

All player actions are submitted as intents, processed on tick:

```json
// Movement intent
{"action": "move", "monster_id": "...", "direction": "north"}

// Push intent  
{"action": "push", "monster_id": "...", "direction": "east"}

// Interact intent (context-dependent)
{"action": "interact", "monster_id": "...", "target_id": "..."}

// Monster switch intent
{"action": "switch_control", "to_monster_id": "..."}

// Batch task assignment
{"action": "assign_batch", "monster_id": "...", "task_type": "...", "params": {...}}
```

---

## 4. World Design

### 4.1 World Structure

```
OVERLAND MAP (zoomed out)
+------------------------------------------+
|  [City A]----road----[City B]            |
|      |                   |               |
|    road              [City C]            |
|      |                   |               |
|  [City D]----road--------+               |
+------------------------------------------+

CITY VIEW (16x16 to 64x64 cells)
+------------------------------------------+
|  [Workshop Area]  [Central Storage]      |
|       W  W  W           S                |
|                                          |
|  [Raw Resource Loc]    [Residential]     |
|       R  R  R           M M M            |
|                                          |
|  [Drop-off]        [Road to other city]  |
|       D                  ->              |
+------------------------------------------+
```

### 4.2 Zone Types

| Zone Type | Function | Contents |
|-----------|----------|----------|
| **City** | Container for local zones | Workshop areas, storage, housing |
| **Workshop Area** | Crafting production | Deployed workshops, work items |
| **Raw Resource Location** | Resource gathering | Trees, mines, fields |
| **Central Storage** | Inter-city transport hub | Goods in transit |
| **Drop-off** | Scoring location | Accepts tagged goods |
| **Road** | Between-city travel | Wagons, travelers |

### 4.3 Cell Contents

Each cell can contain:
- **Empty** (floor tile, passable)
- **Wall** (impassable, blocks light)
- **Item** (pushable 1x1 object)
- **Monster** (controlled or NPC)
- **Workshop** (2x2 or 3x3, immobile after deployment)
- **Wagon** (2x3, movable when pulled)
- **Environmental** (trees, rocks, water - may be harvestable)

### 4.4 Visual Layers

```
z-index structure:
0-9:     Ground/floor tiles (parallax depth=2.0)
10-19:   Items on ground
20-29:   Workshops, wagons, furniture  
30-39:   Monsters
40-49:   Effects, particles
50-59:   Speech bubbles, floating indicators
100+:    UI panels (fixed=True)
```

---

## 5. Monster System

### 5.1 Monster Types (from MonsterMakers)

| Type | Symbol | STR | DEX | CON | INT | WIS | CHA | Specialty |
|------|--------|-----|-----|-----|-----|-----|-----|-----------|
| **Cyclops** | `C` | 18 | 10 | 16 | 10 | 10 | 10 | Heavy lifting, quantity |
| **Elf** | `E` | 10 | 16 | 10 | 18 | 10 | 10 | Precision, learning |
| **Goblin** | `G` | 10 | 18 | 10 | 10 | 10 | 16 | Speed, charisma |
| **Orc** | `O` | 16 | 10 | 18 | 10 | 10 | 10 | Durability, transport |
| **Troll** | `T` | 18 | 10 | 16 | 10 | 10 | 10 | Massive capacity |

### 5.2 Visual Representation

**Controlled Monster**:
- Bright sprite with character symbol
- Pulsing light aura (radius 8, follow_sprite=monster)
- Subtle foot particle emitter (spawn_rate=2)

```python
# Controlled monster aura
control_light = pyunicodegame.create_light(
    x=monster.x, y=monster.y,
    radius=8, color=(100, 200, 255),
    intensity=0.8, falloff=1.5,
    follow_sprite=monster_sprite
)

control_particles = pyunicodegame.create_emitter(
    x=monster.x, y=monster.y,
    chars=".", colors=[(100, 200, 255)],
    spawn_rate=2, speed=0.5, arc=360,
    drag=0.9, fade_time=0.8, max_particles=8
)
```

**Idle Monster**:
- Dimmed sprite color (70% brightness)
- Small `Z` or `...` indicator above head
- No aura

**Busy Monster (Batch Task)**:
- Normal brightness
- Task icon above head (`hammer`, `crate`, `wagon`)
- Progress indicator: `o` -> `O` -> `@`

### 5.3 Monster Abilities

**Pushing Power** (based on STR):
- STR 10: Push 1 light item
- STR 14: Push 1 medium item or 2 light items in a row
- STR 18: Push 1 heavy item or 3 items in a row

**Movement Speed** (based on DEX):
- DEX 10: 1 cell per 2 ticks
- DEX 14: 1 cell per tick  
- DEX 18: 1 cell per tick + occasional 2-cell burst

**Carry Capacity** (for wagons, based on CON):
- CON 10: Pull wagon at half speed
- CON 16: Pull wagon at full speed
- CON 18: Pull wagon + slight speed bonus

### 5.4 Skill System (Simplified from MonsterMakers)

**Transferable Skills** (3 chosen at creation):
1. Mathematics
2. Science
3. Engineering
4. Writing
5. Visual Art
6. Music
7. Handcrafts
8. Athletics
9. Outdoorsmonstership
10. Social

**Applied Skills** (learned through doing):
- Crafting: Dishes, Baking, Brewing, Furniture, Blacksmithing, etc.
- Resource: Gathering, Chopping, Mining, Harvesting
- Transport: Hauling, Wagon Driving

**Specific Skills** (per item type):
- Each unique recipe has its own mastery track

---

## 6. Movement & Pushing Mechanics

### 6.1 Basic Movement

**Controls** (keyboard):
- Arrow keys / WASD: Move in 4 directions
- Space: Interact with adjacent cell
- Tab: Cycle through controllable monsters
- Hold Shift + Direction: Push mode

**Tick-Based Movement**:
1. Player inputs direction
2. Ghost preview shows intended destination
3. On tick: Movement resolves, preview becomes reality
4. Visual lerp smooths transition (lerp_speed=6)

### 6.2 Pushing Mechanics

**Push Rules** (Sokoban-style):
- Monster can only PUSH, not PULL items
- Push in cardinal directions only
- Items push in a chain (A pushes B pushes C)
- Blocked if any item in chain hits wall/workshop/water

**Push Visual Feedback**:

```python
# Successful push - dust particles behind item
def on_push_success(item_sprite, direction):
    opposite = get_opposite(direction)
    pyunicodegame.create_emitter(
        x=item_sprite.x, y=item_sprite.y,
        chars=".", colors=[(120, 100, 80)],
        spawn_rate=20, emitter_duration=0.1,
        speed=2, direction=opposite, arc=60,
        drag=0.7, fade_time=0.3, max_particles=8
    )

# Blocked push - bounce back + red X
def on_push_blocked(monster_sprite, direction):
    # Micro-shake animation
    monster_sprite.play_animation("blocked_shake")
    
    # Red X indicator on blocked cell
    blocked_cell = get_cell_in_direction(monster, direction)
    flash = pyunicodegame.create_effect(
        "X", x=blocked_cell.x, y=blocked_cell.y,
        fg=(255, 80, 80), fade_time=0.3
    )
```

### 6.3 Special Push Interactions

**Pushing into Workshop**:
- Valid ingredient -> suction particles, item disappears, slot fills
- Invalid ingredient -> bounce back, red flash
- Full workshop -> bounce back, workshop shakes

**Pushing onto Wagon**:
- Items stack on wagon (visual stacking)
- Wagon shows load indicator
- Over capacity -> item slides off other side

**Pushing into Water**:
- Items float or sink based on type
- Some items become "wet" (tag added)
- Logs become bridges

### 6.4 Wagon Mechanics

**Loading**:
1. Position wagon adjacent to items
2. Push items onto wagon (2x3 cells)
3. Items stack visually (up to capacity)

**Pulling**:
1. Monster moves adjacent to wagon hitch (front cell)
2. Interact to "attach"
3. Movement now pulls wagon behind
4. Slower movement based on load

**Visual States**:
- Empty wagon: Simple outline
- Loaded wagon: Stacked item sprites
- Moving wagon: Dust trail particles
- Attached: Visible "chain" between monster and hitch

---

## 7. Crafting System

### 7.1 Workshop Types

| Workshop | Size | Crafts | Visual Theme |
|----------|------|--------|--------------|
| **Workbench** | 2x2 | Basic items, furniture | Wood grain, simple |
| **Forge** | 3x3 | Metal items, tools | Orange glow, sparks |
| **Kitchen** | 2x3 | Food, dishes | Steam, warmth |
| **Loom** | 2x2 | Textiles, clothing | Thread particles |
| **Alchemy Table** | 2x2 | Potions, enchanting | Mystical glow, bubbles |
| **Kiln** | 2x2 | Pottery, glass | Heat shimmer |

### 7.2 Crafting Flow

**Phase 0: Goal Setting (Recording Starts)**
1. Monster interacts with workshop
2. Recipe selection menu appears (speech bubble style)
3. Player selects desired output (e.g., "Iron Ingot")
4. UI shows required ingredients with counts
5. **Recording begins** - all movements tracked from this point
6. Workshop shows "goal badge" indicating target recipe

**Phase 1: Ingredient Fetching**
1. Monster travels to Dispensers in Storage zones
2. Push ingredients from dispensers (dispenser auto-replenishes if stock remains)
3. Push items back toward workshop
4. All movement and push actions recorded

**Phase 2: Ingredient Deposit**
1. Push each ingredient into workshop input cells
2. Visual: Slot glyphs change `o` -> `O` as filled
3. Valid recipe detected -> workshop ready indicator
4. Deposit sequence recorded

**Phase 3: Initiation**
1. Monster interacts with workshop to start craft
2. Workshop enters RUNNING state
3. **Recording paused** - craft processing is automatic

**Phase 4: Processing**
1. RUNNING state persists for `production_time` ticks
2. Visual: Continuous particle effects, pulsing light
3. Progress shown via 4-corner indicators
4. Monster free to wait or move (movements during wait NOT recorded)

**Phase 5: Completion**
1. Timer expires -> COMPLETE state
2. Burst particles, flash effect
3. Output item appears adjacent to workshop
4. Monster gains skill XP
5. **Recording ends** - full craft cycle captured
6. Prompt appears: "Press [R] to repeat this craft"

### 7.3 Crafting Visual Effects

**RUNNING State**:
```python
# Forge example - sparks and glow
forge_light = pyunicodegame.create_light(
    x=forge.x+1, y=forge.y+1,  # Center of 3x3
    radius=10, color=(255, 150, 50),
    intensity=0.6, falloff=1.2,
    casts_shadows=True
)

forge_sparks = pyunicodegame.create_emitter(
    x=forge.x+1, y=forge.y,
    chars="*.", colors=[(255, 200, 50), (255, 150, 30)],
    spawn_rate=8, speed=4, direction=90, arc=40,
    drag=0.4, fade_time=0.6, max_particles=20
)
```

**COMPLETE State**:
```python
# Completion burst
def on_craft_complete(workshop):
    # Flash light
    completion_light = pyunicodegame.create_light(
        x=workshop.x+1, y=workshop.y+1,
        radius=12, color=(255, 255, 200),
        intensity=2.0, falloff=0.5
    )
    # Fade light over 0.5s (in update loop)
    
    # Burst particles
    pyunicodegame.create_emitter(
        x=workshop.x+1, y=workshop.y+1,
        chars="*+.", colors=[(255, 255, 100), (255, 200, 50)],
        spawn_rate=50, emitter_duration=0.15,
        speed=8, direction=0, arc=360,
        drag=0.3, fade_time=0.7, max_particles=30
    )
```

**Progress Indicators**:
```
Workshop corners show progress:
[0-25%]   ·  ·    [25-50%]  :  ·    [50-75%]  :  :    [75-100%] *  :
          ·  ·              ·  :              :  :               :  *
```

### 7.4 Recipe Visualization

Recipes are discovered through:
1. **In-world recipe books** (pushable items that show recipes when examined)
2. **NPC hints** via speech bubbles
3. **Experimentation** (try combinations, learn from failures)

**Recipe Display** (in info panel when examining workshop):
```
+------------------------+
| FORGE: Iron Sword      |
|------------------------|
| Inputs:                |
|  [O] Iron Ingot x2     |
|  [O] Wood Handle x1    |
| Tools:                 |
|  [ ] Hammer (adj)      |
| Time: 30 ticks         |
+------------------------+
```

### 7.5 Recording & Repeat System

The recording system enables batch crafting by capturing a complete craft cycle and replaying it.

#### 7.5.1 What Gets Recorded

| Action Type | Data Captured | Example |
|-------------|---------------|---------|
| **Movement** | Direction per tick | `[N, N, E, E, E, N]` |
| **Push** | Direction + expected item type | `push E, expect "iron_ore"` |
| **Deposit** | Workshop slot + item type | `deposit slot 1, "iron_ore"` |
| **Initiate** | Workshop ID | `start craft at workshop_123` |

**NOT Recorded**:
- Movement during craft processing (waiting is optional)
- Looking around / camera movement
- Menu interactions after goal is set

#### 7.5.2 Recording Data Structure

```python
CraftRecording = {
    "workshop_id": "forge_001",
    "recipe": "iron_ingot",
    "actions": [
        {"type": "move", "direction": "north"},
        {"type": "move", "direction": "north"},
        {"type": "move", "direction": "east"},
        {"type": "push", "direction": "west", "expect_item": "iron_ore"},
        {"type": "move", "direction": "south"},
        # ... path back to workshop ...
        {"type": "deposit", "slot": 0, "item_type": "iron_ore"},
        {"type": "move", "direction": "north"},
        {"type": "push", "direction": "west", "expect_item": "coal"},
        # ... etc ...
        {"type": "deposit", "slot": 1, "item_type": "coal"},
        {"type": "initiate"}
    ],
    "recorded_at": "2026-01-09T12:00:00Z"
}
```

#### 7.5.3 Repeat Execution

When player presses **[R]** to repeat:

1. **Validation**: Check monster is at workshop, no active recording
2. **Playback Start**: Monster enters "autopilot" mode
3. **Action Execution**: Each recorded action executed per tick
4. **Push Validation**: Before each push, verify expected item type is present
5. **Loop**: On craft completion, restart from first action
6. **Termination**: Stop on any failure condition

#### 7.5.4 Repeat Stop Conditions

| Condition | Visual Feedback | Recovery |
|-----------|-----------------|----------|
| **Dispenser empty** | Red flash on empty cell, speech bubble "Out of [item]!" | Restock dispenser, press [R] again |
| **Path blocked** | Monster bumps, red X particles | Clear obstruction, press [R] again |
| **Push wrong item** | Red flash, "Expected [X], found [Y]" | Manual intervention required |
| **Workshop occupied** | Workshop shows busy indicator | Wait or reassign |
| **Player interrupts** | Any movement key pressed | Recording preserved, can resume |

#### 7.5.5 Repeat Visual Feedback

**During Autopilot**:
```python
# Monster has distinct "working" aura during repeat
autopilot_indicator = pyunicodegame.create_light(
    x=monster.x, y=monster.y,
    radius=3, color=(100, 255, 100),  # Green = automated
    intensity=0.4, falloff=1.0
)

# Status badge above monster
status_sprite = pyunicodegame.create_sprite(
    "[A]",  # A = Autopilot
    x=monster.x, y=monster.y - 1,
    fg=(100, 255, 100),
    z_index=55
)
```

**Repeat Counter**:
```
Monster speech bubble during repeat:
+------------------+
| Crafting... 3/∞  |  ← Shows completed cycles
| [■■■□□] 60%      |  ← Current cycle progress
+------------------+
```

#### 7.5.6 Recording Management

Players can:
- **[R]** - Start/resume repeat of last recording
- **[Shift+R]** - Clear recording, start fresh
- **[Esc]** - Stop current repeat (recording preserved)

Recordings are stored **per monster per workshop**:
- Each monster remembers one recording per workshop
- Switching monsters doesn't lose recordings
- Recordings persist across sessions

#### 7.5.7 Edge Cases

| Situation | Behavior |
|-----------|----------|
| Monster pushed during repeat | Repeat stops, "Interrupted!" |
| Workshop destroyed during repeat | Repeat stops, recording invalidated |
| Item despawns mid-push | Repeat stops at that action |
| Server tick during playback | Actions queued, executed in order |
| Multiple monsters same workshop | Second monster waits for workshop |

---

## 8. Visual Effects Design

### 8.1 Quality Tier System

| Quality Range | Tier Name | Badge | Color Scheme | Effects |
|---------------|-----------|-------|--------------|---------|
| 0.00 - 0.19 | Poor | `·` | Gray/Brown | None |
| 0.20 - 0.49 | Common | `o` | White/Neutral | None |
| 0.50 - 0.79 | Good | `O` | Light Blue | None |
| 0.80 - 1.09 | Fine | `*` | Green | Subtle shimmer |
| 1.10+ | Masterwork | `@` | Gold | Emissive=True, sparkles |

**Implementation**:
```python
def get_quality_visual(quality):
    if quality < 0.20:
        return {"badge": ".", "fg": (120, 100, 80), "emissive": False}
    elif quality < 0.50:
        return {"badge": "o", "fg": (200, 200, 200), "emissive": False}
    elif quality < 0.80:
        return {"badge": "O", "fg": (150, 200, 255), "emissive": False}
    elif quality < 1.10:
        return {"badge": "*", "fg": (100, 255, 100), "emissive": False}
    else:
        return {"badge": "@", "fg": (255, 215, 0), "emissive": True}
```

**Masterwork Sparkle Effect**:
```python
masterwork_sparkle = pyunicodegame.create_emitter(
    x=item.x, y=item.y,
    chars=".", colors=[(255, 255, 200), (255, 215, 0)],
    spawn_rate=1, speed=1, arc=360,
    drag=0.9, fade_time=1.0, max_particles=4
)
```

### 8.2 Durability Visualization

| Durability % | Visual Change |
|--------------|---------------|
| 100-70% | Normal appearance |
| 70-40% | Slightly desaturated fg, occasional spark on use |
| 40-10% | Warning badge `!`, visible wear lines |
| <10% | Flicker effect, critical badge `!!` |

**Wear Effect on Use**:
```python
def on_tool_use(tool, durability_percent):
    if durability_percent < 0.70:
        # Chip particle
        pyunicodegame.create_effect(
            ".", x=tool.x, y=tool.y,
            vx=random.uniform(-2, 2), vy=random.uniform(-1, 0),
            fg=(100, 100, 100), drag=0.6, fade_time=0.3
        )
```

### 8.3 Lighting Design

**Ambient Lighting by Zone**:
```python
# Outdoor daytime
window.set_lighting(enabled=True, ambient=(80, 80, 90))

# Indoor workshop
window.set_lighting(enabled=True, ambient=(40, 40, 50))

# Night
window.set_lighting(enabled=True, ambient=(15, 15, 25))

# Underground
window.set_lighting(enabled=True, ambient=(10, 10, 15))
```

**Dynamic Lights**:
- Controlled monster: Bright, cool (100, 200, 255)
- Active forge: Warm, flickering (255, 150, 50)
- Torch/lamp: Warm, steady (255, 200, 100)
- Magic effect: Cool, pulsing (150, 100, 255)

### 8.4 Bloom Configuration

```python
# Default bloom (subtle)
window.set_bloom(enabled=True, threshold=220, blur_scale=2, intensity=0.5)

# Important event bloom (crafting complete, masterwork created)
window.set_bloom(enabled=True, threshold=180, blur_scale=4, intensity=1.2)

# Night mode bloom (more visible lights)
window.set_bloom(enabled=True, threshold=200, blur_scale=3, intensity=0.8)
```

### 8.5 Animation Patterns

**Item Slide** (push):
- `lerp_speed=8` (cells per second)
- Duration: ~125ms for 1 cell

**Workshop Deposit Suction**:
```python
deposit_suction = pyunicodegame.create_emitter(
    x=workshop_center_x, y=workshop_center_y,
    chars=".", colors=[(200, 200, 255)],
    spawn_rate=30, emitter_duration=0.1,
    speed=4, direction=inward, arc=90,  # toward center
    drag=0.5, fade_time=0.25, max_particles=15
)
```

**Monster Walk Cycle**:
```python
walk_animation = pyunicodegame.create_animation(
    "walk",
    frame_indices=[0, 1, 0, 2],
    frame_duration=0.15,
    offsets=[(0, 0), (0, -2), (0, 0), (0, -2)],  # Slight bob
    loop=True,
    offset_speed=50
)
```

---

## 9. UI/UX Design

### 9.1 Screen Layout

```
+------------------+----------------------------------------+
| OBJECT DETAIL    |                                        |
| (12 cells wide)  |                                        |
|                  |                                        |
+------------------+              GAME WORLD                |
| MONSTER SKILLS   |              (56 x 50 cells)           |
| (12 cells wide)  |                                        |
|                  |                                        |
+------------------+                                        |
|                  |                                        |
| (empty space or  |                                        |
|  minimap later)  |                                        |
+------------------+----------------------------------------+
```

### 9.2 Object Detail Panel

**Window Setup**:
```python
detail_panel = pyunicodegame.create_window(
    "detail", x=0, y=0, width=12, height=15,
    z_index=100, font_name="unifont",
    bg=(20, 20, 30, 240), fixed=True
)
```

**Content Layout**:
```
+------------+
|[icon] Name |
|------------|
| Type: Item |
| Tags: ore  |
|       metal|
|------------|
| Quality:   |
|  [***--]   |
|  "Fine"    |
|------------|
| Durability:|
|  [====--]  |
|  78/100    |
|------------|
| Weight: 5kg|
| Value: 120 |
+------------+
```

### 9.3 Monster Skills Panel

**Window Setup**:
```python
skills_panel = pyunicodegame.create_window(
    "skills", x=0, y=16, width=12, height=18,
    z_index=100, font_name="unifont",
    bg=(20, 20, 30, 240), fixed=True
)
```

**Content Layout**:
```
+------------+
| [G] Grunk  |
| Goblin Lv3 |
|------------|
| STR: 12    |
| DEX: 18 ++ |
| CON: 10    |
| INT: 10    |
| WIS: 10    |
| CHA: 16 +  |
|------------|
| Skills:    |
| Blacksmith |
|  [***--]   |
| Hauling    |
|  [****-]   |
| Mining     |
|  [**---]   |
|------------|
| [More...]  |
+------------+
```

**Contextual Skills**:
- When examining a workshop, show skills relevant to that craft
- When examining an item, show skills used to create similar items
- Default: Show highest-level skills

### 9.4 Speech Bubble System

**Bubble Types**:
| Type | Trigger | Duration | Priority |
|------|---------|----------|----------|
| Tutorial | First-time action | Until dismissed | 1 (highest) |
| Error | Failed action | 3s | 2 |
| Hint | Proximity to goal | 5s | 3 |
| Status | Task complete | 4s | 4 |
| Chatter | Random NPC | 6s | 5 (lowest) |

**Bubble Rendering**:
```python
def create_speech_bubble(speaker, text, bubble_type):
    # Calculate bubble size
    lines = wrap_text(text, max_width=20)
    height = len(lines) + 2  # +2 for border
    width = max(len(line) for line in lines) + 4  # +4 for border and padding
    
    # Build bubble pattern
    pattern = build_bubble_pattern(lines, width, height)
    
    bubble_sprite = pyunicodegame.create_sprite(
        pattern,
        x=speaker.x, y=speaker.y - height - 1,
        fg=get_bubble_color(bubble_type),
        z_index=55
    )
    
    # Pop-in animation
    bubble_sprite.add_animation(
        pyunicodegame.create_animation(
            "pop_in",
            frame_indices=[0],  # Single frame but with offset
            offsets=[(0, 4), (0, 2), (0, 0)],
            frame_duration=0.08,
            loop=False,
            offset_speed=100
        )
    )
    bubble_sprite.play_animation("pop_in")
    
    return bubble_sprite
```

**Bubble Pattern Builder**:
```
Tutorial bubble (blue):
+--------------------+
| Press SPACE to     |
| interact with      |
| the workshop!      |
+--------+-----------+
         |
        [@]

Error bubble (red):
+--------------------+
| Cannot push here!  |
| Path is blocked.   |
+--------+-----------+
         |
        [G]
```

### 9.5 Interaction Affordances

**Highlight Valid Targets**:
When player is adjacent to pushable item:
```python
# Dim glow on valid push directions
for direction in valid_push_directions:
    target_cell = get_adjacent(player, direction)
    highlight = pyunicodegame.create_sprite(
        ".", x=target_cell.x, y=target_cell.y,
        fg=(100, 255, 100), emissive=True, z_index=5
    )
```

**Workshop Input Slots**:
```
Empty slot:     o  (dim)
Valid deposit:  O  (bright, pulsing)
Filled slot:    @  (solid)
Invalid:        x  (red, brief)
```

### 9.6 Tick Feedback

**Intent Preview**:
```python
# Ghost sprite showing intended action result
def show_intent_preview(action, target_position):
    ghost = pyunicodegame.create_sprite(
        get_action_glyph(action),
        x=target_position.x, y=target_position.y,
        fg=(255, 255, 255, 128),  # Semi-transparent
        z_index=45
    )
    return ghost

# On tick resolution
def on_tick_resolve(intent, success):
    if success:
        # Quick flash to confirm
        pyunicodegame.create_effect(
            ".", x=intent.target.x, y=intent.target.y,
            fg=(100, 255, 100), fade_time=0.15
        )
    else:
        # Rejection burst
        pyunicodegame.create_emitter(
            x=intent.target.x, y=intent.target.y,
            chars="x", colors=[(255, 80, 80)],
            spawn_rate=10, emitter_duration=0.1,
            speed=3, arc=360, fade_time=0.3
        )
```

### 9.7 Dispenser Interface

Dispensers are storage cells that auto-replenish when items are pushed away.

**Visual States**:
```
Stocked (5+ items):    [Fe]     Normal color
Low (2-4 items):       [Fe]     Dimmer, subtle pulse  
Critical (1 item):     [Fe]!    Warning badge, orange tint
Empty (0 items):       [ ]      Gray outline only
```

**Inventory Display** (on hover/examine):
```
+------------------+
| DISPENSER        |
|------------------|
| Iron Ore         |
| [■■■■■■□□□□] 6   |  ← 6 of 10 capacity
|                  |
| Auto-replenish   |
+------------------+
```

**Replenish Animation**:
```python
def on_item_pushed_from_dispenser(dispenser, item_pushed):
    remaining = dispenser.inventory.get(item_pushed.type, 0)
    
    if remaining > 0:
        dispenser.inventory[item_pushed.type] -= 1
        
        # Small delay for visual clarity
        schedule(0.15, lambda: spawn_replenish(dispenser, item_pushed.type))

def spawn_replenish(dispenser, item_type):
    # Create new item at dispenser position
    new_item = create_item(item_type, dispenser.x, dispenser.y)
    
    # Rise-up animation (starts below, rises to surface)
    new_item.sprite.y_offset = 8  # 8 pixels below
    new_item.sprite.lerp_to(y_offset=0, speed=40)
    
    # Pop particles
    pyunicodegame.create_emitter(
        x=dispenser.x, y=dispenser.y,
        chars=".", colors=[(180, 180, 200)],
        spawn_rate=8, emitter_duration=0.1,
        speed=2, direction=90, arc=120,  # Upward burst
        drag=0.7, fade_time=0.3, max_particles=6
    )
```

**Dispenser Stocking** (manual process):
1. Push item toward dispenser cell
2. If item type matches or dispenser is empty, item is absorbed
3. Dispenser inventory count increases
4. Visual: Item slides in, brief flash, count updates

**Stocking Visual**:
```python
def on_item_pushed_to_dispenser(dispenser, item):
    if dispenser.can_accept(item):
        # Item absorbed animation
        item.sprite.lerp_to(x=dispenser.x, y=dispenser.y, speed=12)
        
        # On arrival, absorb
        schedule(0.1, lambda: absorb_item(dispenser, item))
        
        # Flash effect
        pyunicodegame.create_emitter(
            x=dispenser.x, y=dispenser.y,
            chars="+", colors=[(100, 255, 100)],
            spawn_rate=15, emitter_duration=0.1,
            speed=3, arc=360, fade_time=0.25
        )
    else:
        # Rejection - wrong item type
        bounce_back(item)
        show_error_bubble(dispenser, "Wrong item type!")
```

**Dispenser Placement**:
- Found in **Storage zones** within cities
- Typically organized by item category (ores, wood, fibers, etc.)
- Players cannot create/move dispensers (fixed infrastructure)

---

## 10. Multiplayer & Persistence

### 10.1 Player Session

- Each player controls a **Commune** (account)
- Commune owns multiple **Monsters**
- Only ONE monster controlled at a time per player
- Other monsters can be assigned **Batch Tasks**

### 10.2 World Persistence

**Persistent Elements**:
- All placed items and their positions
- Workshop states and contents
- Monster positions and skills
- Crafted goods and their ownership

**Session Elements** (reset on disconnect):
- Currently controlled monster (released to idle)
- Pending intents (cancelled)
- Ghost previews (cleared)

### 10.3 Fog of War / Visibility

**Option A: Full Visibility**
- All players see entire zone
- Simple, encourages cooperation

**Option B: Monster-Based FOV** (recommended)
- Each player sees what their monsters see
- Idle monsters provide static vision
- Encourages distributed monster placement

```python
def get_player_state(zone_id, player_id, full_state):
    commune = get_commune_for_player(player_id)
    monsters = get_monsters_for_commune(commune)
    
    visible_cells = set()
    for monster in monsters:
        visible_cells.update(
            compute_fov(monster.x, monster.y, vision_radius=12)
        )
    
    # Filter full_state to only visible cells
    return filter_state_to_visible(full_state, visible_cells)
```

### 10.4 Cooperative Mechanics

**Shared Resources**:
- All items in world are available to all communes
- Checkout system prevents conflicts (1 hour reserve)
- Share system tracks contributions

**Contribution Tracking**:
- When item is crafted, all contributors get shares
- Contributors: gatherer, tool maker, transporter, crafter
- On drop-off (scoring), renown distributed by shares

### 10.5 Real-Time Sync

**WebSocket Messages**:
```json
// Server -> Client: Zone state update (every tick)
{
  "type": "tick",
  "tick_number": 12345,
  "state": {
    "entities": [...],
    "events": [
      {"type": "craft_complete", "workshop_id": "...", "output_id": "..."},
      {"type": "item_moved", "item_id": "...", "from": [x,y], "to": [x,y]},
      ...
    ]
  }
}

// Client -> Server: Intent submission
{
  "type": "intent",
  "data": {"action": "push", "monster_id": "...", "direction": "north"}
}
```

---

## 11. User Journeys

### Core Loop Journeys (1-20)

#### Journey 1: First Login
1. Player creates account
2. Commune created with 10,000 starting renown
3. Tutorial zone loads
4. First monster (Goblin) introduced via speech bubble
5. Camera centers on controlled monster
6. Control aura activates around Goblin
7. "Use arrow keys to move" tutorial bubble appears
8. Player moves monster, sees smooth lerp
9. "You can push objects! Try pushing that log" bubble
10. Player pushes log, sees dust particles
11. "Great! Now push it into the workshop" bubble
12. Player pushes log into workbench
13. Suction particles, slot fills
14. "Press SPACE to start crafting" bubble
15. Player starts craft, sees progress effects
16. Craft completes, burst particles
17. "Your first item! Check the left panel for details"
18. Player examines item in detail panel
19. "Now find the drop-off to score your item"
20. Player pushes item to drop-off, earns renown

#### Journey 2: Basic Movement
1. Player presses UP arrow
2. Ghost preview appears one cell north
3. Next tick resolves, monster moves
4. Lerp animation smooths transition
5. Walk animation plays (bob offset)
6. Repeat for all four directions
7. Player tries to walk into wall
8. Ghost preview shows blocked (red tint)
9. Tick resolves, no movement
10. Player finds open path
11. Walking through doorway
12. Entering new room/area
13. Visibility updates (FOV if enabled)
14. Ambient lighting changes
15. Different floor tiles visible

#### Journey 3: Pushing Single Item
1. Player moves adjacent to log
2. "Pushable" indicator appears on log
3. Player presses SHIFT+direction toward log
4. Intent preview shows log moving
5. Tick resolves, log slides one cell
6. Dust particles emit from log's origin
7. Monster position unchanged (push in place)
8. Player pushes log again
9. Log slides another cell
10. Continues until log hits wall
11. Blocked push animation (log shakes)
12. Player repositions to push different direction

#### Journey 4: Chain Pushing
1. Player sees two logs in a row
2. Pushes from behind first log
3. Both logs move (chain push)
4. Third item in path (rock - heavy)
5. Push blocked - cannot push through rock
6. Red X on rock
7. Player repositions
8. Pushes rock alone (heavy, maybe slower)
9. Clears path
10. Returns to chain-push logs

#### Journey 5: Workshop Discovery
1. Player explores workshop area
2. Various workshops visible (different glyphs/colors)
3. Player walks adjacent to forge
4. Detail panel updates automatically
5. Shows: "Forge - Metalworking"
6. Shows: "Available recipes: Iron Sword, Steel Plate..."
7. Player presses SPACE to interact
8. Recipe list expands in panel
9. Shows required inputs for selected recipe
10. Player notes needed materials
11. Leaves to gather materials

#### Journey 6: Gathering Raw Materials
1. Player travels to forest zone
2. Trees visible (green `T` or similar)
3. Player moves adjacent to tree
4. Detail panel: "Oak Tree - Choppable"
5. Required tool: Axe (shown in panel)
6. Player has axe in adjacent cell
7. Interacts with tree
8. Chopping animation (particles fly)
9. Progress shown (corner indicators)
10. Tree "falls" - becomes pushable log
11. Player pushes log toward workshop

#### Journey 7: Complete Crafting Cycle
1. Player has gathered: 2x Iron Ore, 1x Coal
2. Pushes Iron Ore into Forge (slot 1)
3. Suction effect, slot shows filled
4. Pushes second Iron Ore (slot 2)
5. Pushes Coal (fuel slot)
6. All slots filled - "Ready" indicator
7. Required tool: Tongs (checks adjacency)
8. Tongs present - all requirements met
9. Player interacts to start
10. Forge enters RUNNING state
11. Orange glow intensifies
12. Spark particles begin
13. Progress corners light up
14. Monster can leave (batch task assigned)
15. Player switches to different monster
16. Time passes (ticks)
17. Completion notification appears
18. Iron Ingot appears adjacent to forge
19. Original monster gains Smelting XP

#### Journey 8: Monster Switching
1. Player controls Goblin (main crafter)
2. Starts a long craft at forge
3. Opens monster list (M key)
4. Sees: Goblin (Busy), Cyclops (Idle), Elf (Idle)
5. Selects Cyclops
6. Camera pans to Cyclops location
7. Control aura transfers to Cyclops
8. Goblin shows "hammer" icon (busy)
9. Player now controls Cyclops
10. Can do other tasks while Goblin crafts

#### Journey 9: Wagon Loading
1. Player positions wagon near items
2. Wagon is 2x3 cells, hitch at front
3. Player pushes first item onto wagon
4. Item appears "on" wagon (stacked sprite)
5. Load indicator updates (1/6)
6. Pushes more items onto wagon
7. Visual stacking shows cargo
8. At capacity (6/6), items bounce off
9. Player moves to hitch cell
10. Interacts to "attach"
11. Chain link visual appears
12. Movement now pulls wagon behind

#### Journey 10: Wagon Transport
1. Wagon attached, loaded with goods
2. Player moves north
3. Monster moves north
4. Wagon follows (pulled) with slight delay
5. Slower movement due to load
6. Dust trail behind wagon
7. Navigating through doorways
8. Careful positioning required (wagon is 2x3)
9. Arrival at destination
10. Interact to "detach"
11. Chain disappears
12. Push items off wagon into storage

#### Journey 11: Drop-off and Scoring
1. Player has high-quality crafted item
2. Pushes item to drop-off zone
3. Drop-off accepts items with matching tags
4. Item enters drop-off cell
5. Special scoring animation
6. Item glows, rises slightly
7. Burst of renown particles (gold)
8. Item disappears
9. "+150 Renown" floats up
10. Commune renown increases
11. All share-holders notified
12. Share distribution shown in log

#### Journey 12: Skill Progression
1. Monster completes many smithing tasks
2. Blacksmithing skill increases
3. Visual notification: "Blacksmithing: ** -> ***"
4. Skills panel updates
5. Higher skill = better quality outputs
6. Also slightly faster crafting
7. Specific skill (Iron Sword) increases too
8. Eventually: "Iron Sword Mastery!"
9. Special bonus for that exact recipe
10. Monster becomes specialized

#### Journey 13: Tool Degradation
1. Player uses hammer repeatedly
2. Durability decreases with each use
3. At 70%, tool shows wear visual
4. At 40%, warning badge appears
5. "Tool wearing out!" speech bubble
6. At 10%, critical warning
7. Flicker effect on tool
8. Player must craft/find replacement
9. Tool breaks (0% durability)
10. Disappears with poof particles
11. Craft fails if no tool present

#### Journey 14: Workshop Deployment
1. Player crafts a new workshop (Loom)
2. Workshop appears as heavy item
3. Cannot be pushed (too heavy to move)
4. Must be deployed in workshop area
5. Player uses wagon to transport
6. Arrives at workshop area
7. Finds open 2x2 space
8. Unloads workshop item
9. Interacts to "deploy"
10. Workshop anchors in place
11. Now immovable and functional
12. Gains task slots for production

#### Journey 15: Recipe Discovery
1. Player finds recipe book (item in world)
2. Pushes book to reading spot
3. Interacts with book
4. Recipe panel opens
5. New recipe revealed: "Enchanted Ring"
6. Required inputs shown
7. Required workshop: Alchemy Table
8. Recipe saved to commune knowledge
9. Book remains for others to use
10. Player plans to gather ingredients

#### Journey 16: NPC Interaction
1. Player encounters NPC monster
2. NPC has speech bubble indicator
3. Player moves adjacent
4. NPC's bubble appears
5. "Have you tried the old mine? Good iron there!"
6. Hint about resource location
7. Player thanks (interact again)
8. NPC responds
9. Dialogue ends
10. NPC returns to idle

#### Journey 17: Cooperative Crafting
1. Player A gathers ore
2. Player B transports ore to forge
3. Player C smelts ore into ingots
4. Player D crafts ingots into sword
5. Player E transports sword to drop-off
6. Item scored
7. Renown distributed:
   - Player A: 15% (gathering)
   - Player B: 10% (first transport)
   - Player C: 25% (smelting)
   - Player D: 35% (final craft)
   - Player E: 15% (delivery)
8. All communes benefit

#### Journey 18: Quality Optimization
1. Player wants masterwork item
2. Checks monster skills (high blacksmithing)
3. Uses high-quality inputs
4. Uses high-quality tools
5. Monster has matching transferable skills
6. Starts craft
7. Quality roll occurs at completion
8. Result: 1.15 quality (Masterwork!)
9. Golden glow effect
10. Sparkle particles on item
11. Emissive badge visible
12. Much higher value at drop-off

#### Journey 19: Workshop Queue
1. Large workshop has 3 task slots
2. Player starts craft in slot 1
3. Starts different craft in slot 2
4. Third craft in slot 3
5. Workshop shows all three as RUNNING
6. Different progress indicators
7. Slot 2 completes first
8. Output appears
9. Slot 2 now available
10. Player can queue another craft

#### Journey 20: Upkeep Payment
1. 28 days pass in-game
2. Upkeep due notification
3. System calculates upkeep cost
4. Based on total monster value
5. Automatically deducted from renown
6. Minimum 200 renown preserved
7. If insufficient, partial payment
8. Monsters may leave if unpaid (future mechanic)
9. Player motivated to score items
10. Economic loop reinforced

### Exploration Journeys (21-40)

#### Journey 21: Discovering New Zone
1. Player reaches edge of current zone
2. Exit indicator visible
3. Moves into exit cell
4. Loading transition (brief fade)
5. New zone loads
6. Camera adjusts to new area
7. Different ambient lighting
8. New terrain types visible
9. Unexplored areas foggy (if FOV enabled)
10. Monster's vision reveals terrain

#### Journey 22: Finding Hidden Resource
1. Player exploring forest
2. Notices unusual terrain pattern
3. Pushes aside bushes (pushable)
4. Reveals hidden cave entrance
5. Enters cave zone
6. Dark ambient (requires light)
7. Monster's aura provides vision
8. Rare ore deposits visible
9. Higher quality materials here
10. Risk/reward for exploration

#### Journey 23: Environmental Hazards
1. Player encounters water cells
2. Cannot walk on deep water
3. Must build bridge (logs)
4. Pushes logs into water
5. Log floats, becomes bridge tile
6. Can now walk across
7. Bridge remains for other players
8. Alternative: finds shallow crossing
9. Some items sink in water
10. Strategic routing required

#### Journey 24: City Navigation
1. Player arrives at new city
2. Unfamiliar layout
3. Signs/posts provide hints
4. "Workshop District ->" 
5. Player follows signs
6. Discovers specialized workshops
7. Better quality potential here
8. Different NPCs with new hints
9. Central storage location noted
10. Drop-off location marked

#### Journey 25: Inter-City Travel
1. Player needs resource from distant city
2. Prepares wagon with trade goods
3. Travels to city edge
4. Road zone connects cities
5. Long travel time (multiple ticks)
6. Encounters along road (maybe)
7. Arrives at destination city
8. Unloads goods at central storage
9. Gathers needed resources
10. Return journey

#### Journey 26: Weather Effects (Future)
1. Weather system active
2. Rain begins
3. Visual rain particles
4. Outdoor lighting dims
5. Some resources affected
6. Crafting outdoors harder?
7. Indoor workshops unaffected
8. Rain stops
9. Wet items (temporary tag)
10. Atmosphere enhanced

#### Journey 27: Day/Night Cycle
1. Time advances in-game
2. Ambient lighting shifts
3. Day: bright, full color
4. Dusk: orange tint
5. Night: dark, requires lights
6. Torches become important
7. Some monsters work better at night?
8. Dawn: gradual brightening
9. Cycle affects gameplay rhythm
10. Sleep/rest mechanic (future)

#### Journey 28: Finding NPC Village
1. Player discovers NPC settlement
2. Multiple NPC monsters
3. Each has different role
4. Shopkeeper, blacksmith, guard, etc.
5. Can trade with shopkeeper
6. Can learn from craftsman
7. Guard provides quest hints
8. Village has unique resources
9. Reputation system (future)
10. Return visits beneficial

#### Journey 29: Underground Exploration
1. Player enters mine shaft
2. Very dark ambient
3. Monster aura essential
4. Torches can be placed
5. Deep ore veins visible
6. Higher quality, rare materials
7. Cave-in hazards (future)
8. Navigation more difficult
9. Map memory helpful
10. Rewarding exploration

#### Journey 30: Resource Node Depletion
1. Player harvests ore node
2. Node depletes over time
3. Visual change: rich -> depleted
4. Eventually exhausted
5. Must find new nodes
6. Encourages exploration
7. Nodes respawn slowly
8. Balance of exploitation
9. Sustainable harvesting
10. World changes over time

### Social Journeys (31-50)

#### Journey 31: Seeing Another Player
1. Another player's monster visible
2. Different control aura color
3. Name label above monster
4. Can observe their actions
5. See their pushes, crafts
6. Coordination possible
7. No direct interference
8. Shared world collaboration
9. Emergent teamwork
10. Social presence felt

#### Journey 32: Collaborative Transport
1. Heavy item requires two monsters
2. Player A positions on one side
3. Player B on opposite side
4. Coordinated push (same tick)
5. Item moves successfully
6. Neither could do alone
7. Communication via bubbles
8. "Push on 3!" type coordination
9. Reward for teamwork
10. Social mechanic

#### Journey 33: Resource Sharing
1. Player A has excess ore
2. Player B needs ore
3. Player A pushes ore to shared area
4. Player B retrieves
5. Both benefit
6. No direct trading menu
7. Physical sharing in world
8. Trust-based system
9. Commune cooperation
10. Shared prosperity

#### Journey 34: Leaving Items for Others
1. Player crafts extra tools
2. Leaves near workshop entrance
3. Labels area (sign mechanic?)
4. "Free tools"
5. Other players find them
6. Take what they need
7. Contribution tracked (shares)
8. Community resource pool
9. Altruistic gameplay
10. Positive-sum economics

#### Journey 35: Workshop Scheduling
1. Popular workshop, limited slots
2. Multiple players want access
3. First-come, first-served
4. Queue forms naturally
5. Players wait nearby
6. Slot frees up
7. Next player claims it
8. No formal queue system
9. Social norms emerge
10. Potential for friction (future moderation)

#### Journey 36: Teaching New Players
1. Experienced player sees newbie
2. Newbie struggling with mechanic
3. Experienced approaches
4. Speech bubble: "Need help?"
5. Demonstrates technique
6. Newbie observes
7. Speech bubble: "Try it now"
8. Newbie succeeds
9. Both benefit (mentor XP?)
10. Community building

#### Journey 37: Organized Event (Future)
1. Server-wide event announced
2. "Great Harvest Festival"
3. Special drop-off opened
4. Bonus renown for specific items
5. Players coordinate production
6. Commune competes/cooperates
7. Leaderboard visible
8. Event concludes
9. Winners announced
10. Rewards distributed

#### Journey 38: Guild/Commune Politics (Future)
1. Commune grows large
2. Multiple members
3. Role assignments emerge
4. Gatherers, crafters, transporters
5. Internal communication
6. Resource management
7. Collective goals
8. Disputes resolved
9. Leadership roles
10. Social complexity

#### Journey 39: Marketplace (Future)
1. Dedicated market zone
2. Players display goods
3. Price tags (renown)
4. Browsing other stalls
5. Purchase via interaction
6. Renown transfers
7. Item changes ownership
8. Auction mechanic?
9. Economic gameplay
10. Player-driven economy

#### Journey 40: Reputation System (Future)
1. Helpful actions tracked
2. Reputation score accumulates
3. Visible on monster profile
4. High reputation = trust
5. Access to better opportunities
6. Negative actions decrease
7. Reputation decay over time
8. Encourages ongoing participation
9. Community moderation
10. Social incentives

### Advanced Gameplay Journeys (41-60)

#### Journey 41: Tech Tree Progression
1. Basic recipes available
2. Craft intermediate item
3. Unlocks new recipe tier
4. "Steel Unlocked!"
5. Steel recipes now available
6. Requires smelting mastery
7. Multi-step progression
8. Specialization choices
9. Team needs variety
10. Long-term goals

#### Journey 42: Mastering a Craft
1. Player focuses on blacksmithing
2. Repeated crafting
3. Skill increases incrementally
4. Quality outputs improve
5. Speed increases slightly
6. Specific item mastery
7. "Master Blacksmith" title
8. Recognition from NPCs
9. Access to master recipes
10. Pride in achievement

#### Journey 43: Quality vs Quantity Tradeoff
1. High-quality items: slower, valuable
2. Bulk items: faster, less valuable
3. Player chooses strategy
4. Market demands vary
5. Sometimes bulk is better
6. Sometimes quality wins
7. Monster stats influence choice
8. Goblin: fast bulk producer
9. Elf: slow quality producer
10. Strategic workforce composition

#### Journey 44: Supply Chain Optimization
1. Player analyzes production
2. Bottleneck identified
3. Not enough raw materials
4. Assigns monster to gathering
5. Transport time too long
6. Moves workshop closer
7. Tool breakage slowing things
8. Crafts more tools
9. Efficiency improves
10. Continuous optimization

#### Journey 45: Multi-Step Recipe
1. Complex item: Enchanted Armor
2. Requires: Steel Plate + Magic Gem + Fine Leather
3. Steel Plate requires: Steel Ingot + Hammer
4. Steel Ingot requires: Iron + Coal + Flux
5. Magic Gem requires: Raw Gem + Enchanting
6. Fine Leather requires: Hide + Tanning
7. Multiple workshops needed
8. Multiple monsters assigned
9. Coordination required
10. Final assembly satisfying

#### Journey 46: Rare Resource Hunt
1. Recipe requires rare material
2. Not available in local zones
3. Must explore distant areas
4. Maps/hints from NPCs
5. Long journey undertaken
6. Special zone discovered
7. Rare resource found
8. Limited quantity
9. Careful extraction
10. Triumphant return

#### Journey 47: Workshop Upgrade (Future)
1. Basic workshop at limit
2. Upgrade path available
3. Requires rare materials
4. Requires high skill
5. Upgrade crafted
6. Applied to workshop
7. Workshop improves
8. More task slots
9. Better quality bonus
10. Investment pays off

#### Journey 48: Monster Specialization
1. Monster leveled in one skill
2. Other skills lagging
3. Decision: generalist or specialist?
4. Player chooses specialist
5. Focus all tasks on one skill
6. Becomes master of craft
7. Other tasks for other monsters
8. Team composition matters
9. Specialists cooperate
10. Division of labor

#### Journey 49: Forgetting Mechanic
1. Monster hasn't practiced skill
2. Forgetting accumulates
3. Skill value decreases
4. "Blacksmithing rusty!"
5. Must practice to recover
6. Use it or lose it
7. Encourages active play
8. Can't hoard all skills
9. Strategic skill maintenance
10. Realistic limitation

#### Journey 50: Equipment System
1. Monster can wear equipment
2. Equipment crafted like other items
3. Gloves: +1 STR
4. Glasses: +1 INT
5. Equipment has durability
6. Must be replaced eventually
7. Equipment slots limited
8. Fitting capacity limits
9. Strategic equipment choices
10. Customization depth

### Combat/Challenge Journeys (51-65)

*Note: Combat is not a primary focus but could be added*

#### Journey 51: Environmental Threat (Future)
1. Cave collapse warning
2. Timer starts
3. Must evacuate zone
4. Push critical items out
5. Help other monsters escape
6. Race against clock
7. Success or failure
8. Consequences either way
9. Tension and stakes
10. Dynamic event

#### Journey 52: Resource Competition (Future)
1. Rare resource spawns
2. Multiple players converge
3. First to reach claims it
4. Spatial racing
5. Pushing obstacles
6. Clever pathing wins
7. Fair competition
8. Winner takes prize
9. No hard feelings
10. Try again next time

#### Journey 53: Defensive Building (Future)
1. Hostile creatures exist
2. Can damage workshops
3. Must build defenses
4. Walls block movement
5. Traps deter enemies
6. Cooperative defense
7. Resource investment
8. Protection of shared assets
9. Community responsibility
10. Strategic placement

#### Journey 54: Escort Mission (Future)
1. NPC needs escort
2. Valuable cargo
3. Dangerous route
4. Player accompanies
5. Threats along way
6. Must protect NPC
7. Arrival at destination
8. Reward earned
9. Relationship improved
10. Quest variation

#### Journey 55: Time-Limited Challenge
1. Special event posted
2. "Craft 10 swords in 1 hour"
3. Timer starts
4. Focused production
5. Optimizing workflow
6. Racing against clock
7. Success threshold
8. Rewards for completion
9. Bonus for exceeding
10. Competitive/cooperative hybrid

### Failure/Recovery Journeys (56-70)

#### Journey 56: Craft Failure
1. Craft attempt made
2. Quality roll fails
3. Poor quality output
4. Less valuable
5. Can still use/sell
6. Learning experience
7. Try again with better inputs
8. Skill increases anyway
9. Not devastating
10. Progress continues

#### Journey 57: Resource Shortage
1. Needed resource unavailable
2. Must find alternative
3. Trade with other players
4. Explore new areas
5. Substitute material
6. Different recipe approach
7. Problem-solving
8. Flexibility required
9. Not game-ending
10. Adaptation encouraged

#### Journey 58: Tool Breakage Mid-Craft
1. Craft in progress
2. Tool durability runs out
3. Tool breaks
4. Craft pauses
5. Must replace tool
6. Craft can resume
7. No progress lost
8. Time lost only
9. Lesson learned
10. Always check durability

#### Journey 59: Monster Overworked
1. Monster working continuously
2. Fatigue system (future)
3. Efficiency decreasing
4. Must rest
5. Switch to different monster
6. Recovery over time
7. Balance work/rest
8. Multiple monsters helpful
9. Workforce management
10. Realistic limitation

#### Journey 60: Lost Item
1. Item pushed into water
2. Item sinks (non-float type)
3. Item lost
4. Consequence of carelessness
5. Must craft replacement
6. More careful next time
7. Water cells dangerous
8. Strategic awareness
9. Loss isn't devastating
10. Game continues

#### Journey 61: Workshop Destroyed (Future)
1. Event damages workshop
2. Workshop reduced to rubble
3. Items inside lost
4. Significant setback
5. Must rebuild
6. Community helps
7. Lessons learned
8. Better defenses next time
9. Recovery possible
10. Resilience tested

#### Journey 62: Monster Death (Future, if implemented)
1. Hazardous situation
2. Monster takes fatal damage
3. Monster removed from game
4. Inventory lost
5. Skills lost
6. Emotional impact
7. New monster recruited
8. Renown cost
9. Starting from scratch
10. High stakes, careful play

#### Journey 63: Economic Hardship
1. Renown running low
2. Upkeep approaching
3. Must score items quickly
4. Focus on valuable outputs
5. Efficiency crucial
6. Trade for quick gains
7. Survive the month
8. Economic pressure
9. Motivates productivity
10. Recovery possible

#### Journey 64: Stuck Item
1. Item pushed into corner
2. Cannot retrieve
3. Must push from different angle
4. Sokoban puzzle moment
5. Think through solution
6. Reposition monster
7. Chain push required
8. Puzzle solved
9. Item freed
10. Satisfying resolution

#### Journey 65: Connection Loss
1. Network disconnected
2. Monster returns to idle
3. Pending actions lost
4. Reconnection
5. Resume where left off
6. World persisted
7. No major loss
8. Others continued playing
9. Seamless recovery
10. Robust system

### Mastery Journeys (66-80)

#### Journey 66: Perfect Quality Run
1. Set goal: all masterwork
2. Select best monster
3. Gather premium materials
4. Use highest quality tools
5. Optimal workshop
6. Execute craft
7. Quality roll
8. Masterwork achieved!
9. Golden glow
10. Maximum value

#### Journey 67: Speed Record
1. Time a craft from start to finish
2. Optimize every step
3. Minimize travel
4. Pre-position materials
5. Fast monster (high DEX)
6. Execute flawlessly
7. Record time achieved
8. Personal best
9. Compare with others
10. Speedrunning element

#### Journey 68: Complete Tech Tree
1. All basic recipes crafted
2. All intermediate unlocked
3. All advanced recipes done
4. Master-level recipes
5. Legendary items
6. Every recipe completed
7. Completionist achievement
8. Long-term goal
9. Many hours invested
10. Ultimate satisfaction

#### Journey 69: Monster Collection
1. All monster types owned
2. Cyclops, Elf, Goblin, Orc, Troll
3. Each specialized differently
4. Full workforce
5. Any task covered
6. Optimal composition
7. Management challenge
8. Pokémon-like collection
9. Monster variety
10. Diverse gameplay

#### Journey 70: Legendary Item Craft
1. Rarest recipe discovered
2. Requires multiple rare materials
3. Requires master skill
4. Requires special workshop
5. Long preparation
6. Many intermediate steps
7. Final craft initiated
8. Suspenseful wait
9. Legendary quality achieved
10. Ultimate achievement

#### Journey 71: Self-Sufficient Commune
1. All resources gatherable locally
2. All workshops owned
3. All recipe tiers accessible
4. No external dependencies
5. Closed-loop production
6. Efficient operation
7. Independence achieved
8. Commune milestone
9. Others seek partnership
10. Economic power

#### Journey 72: Trade Empire (Future)
1. Surplus production
2. Regular exports to others
3. Import rare materials
4. Trade agreements
5. Economic influence
6. Market maker
7. Wealth accumulation
8. Renown leader
9. Gameplay expansion
10. Endgame content

#### Journey 73: Teaching Others
1. Become recognized expert
2. New players seek advice
3. Guide them through basics
4. Share secrets
5. Community role
6. Mentor satisfaction
7. Legacy building
8. Knowledge transfer
9. Community strength
10. Social recognition

#### Journey 74: World Shaping
1. Long-term player
2. Workshops placed strategically
3. Bridges built
4. Paths created
5. Infrastructure contributed
6. World reflects effort
7. Others benefit
8. Lasting impact
9. Sense of ownership
10. World building

#### Journey 75: Event Leadership
1. Server event announced
2. Coordinate response
3. Assign roles to volunteers
4. Manage production chain
5. Hit event targets
6. Lead to victory
7. Recognition earned
8. Leadership skills
9. Community hero
10. Memorable experience

### Edge Case Journeys (76-90)

#### Journey 76: Accidental Push
1. Wrong direction pressed
2. Valuable item pushed wrong way
3. Cannot undo (tick resolved)
4. Must fix manually
5. Push it back
6. Takes extra time
7. Frustration, then resolution
8. Learn to be careful
9. Preview system helps
10. Forgiving but consequential

#### Journey 77: Interrupted Craft
1. Long craft in progress
2. Player must leave (IRL)
3. Disconnect from game
4. Monster goes idle
5. Craft continues (batch task)
6. Player returns later
7. Craft completed while away
8. Output waiting
9. Offline progression
10. Respectful of time

#### Journey 78: Workshop Blocked
1. Workshop entrance blocked
2. Item accidentally placed there
3. Cannot access workshop
4. Must remove obstruction
5. Push item away
6. Workshop accessible again
7. Design consideration
8. Clear pathways important
9. Spatial management
10. Player responsibility

#### Journey 79: Tick Timing
1. Action submitted end of tick
2. Uncertain if processed
3. Tick resolves
4. Action didn't make it
5. Must submit again
6. Latency consideration
7. Learn tick rhythm
8. Submit earlier
9. System behaves predictably
10. Skill element

#### Journey 80: Spawn Point Crowded
1. Multiple players spawn
2. Starting area congested
3. Must navigate out
4. Temporary inconvenience
5. Move to open areas
6. World is large
7. Crowding subsides
8. Design consideration
9. Spawn distribution
10. Not game-breaking

### Emotional/Atmospheric Journeys (81-100)

#### Journey 81: First Masterwork Pride
1. Long effort invested
2. High quality achieved
3. Masterwork badge glows
4. Personal accomplishment
5. Screenshot moment
6. Share with friends
7. Display in home
8. Emotional reward
9. Intrinsic motivation
10. Core experience

#### Journey 82: Cooperative Triumph
1. Group project completed
2. Required many players
3. Coordinated effort
4. Challenges overcome
5. Final product amazing
6. Shared celebration
7. Community bonding
8. Memorable moment
9. Social reward
10. Player retention

#### Journey 83: Relaxing Routine
1. Log in daily
2. Check on crafts
3. Gather some resources
4. Start new crafts
5. Pleasant routine
6. Meditative gameplay
7. Stress relief
8. Comfortable familiar
9. Habitual engagement
10. Lifestyle game

#### Journey 84: Discovery Wonder
1. Exploring unknown area
2. Unexpected find
3. "What is this?"
4. Examine closely
5. New mechanic learned
6. Sense of wonder
7. World feels big
8. Mysteries remain
9. Exploration rewarded
10. Engagement deepened

#### Journey 85: Creative Expression
1. Workshop area customizable
2. Player arranges layout
3. Aesthetic choices
4. Personal style
5. Others admire
6. Self-expression
7. Beyond pure efficiency
8. Art in organization
9. Identity in world
10. Creative outlet

#### Journey 86: Mentorship Pride
1. Helped new player
2. They succeeded
3. Visible in their actions
4. Gratitude expressed
5. "Thank you!"
6. Pay it forward mentality
7. Community growth
8. Personal impact
9. Emotional connection
10. Long-term relationship

#### Journey 87: Economic Recovery
1. Was struggling
2. Renown was low
3. Worked hard
4. Made smart trades
5. Recovered fully
6. Sense of accomplishment
7. Problem-solving rewarded
8. Agency felt
9. Not hand-held
10. Player skill matters

#### Journey 88: Seasonal Atmosphere
1. Holiday event active
2. Decorations in world
3. Special items available
4. Festive mood
5. Community participation
6. Limited-time content
7. Urgency to participate
8. Shared experience
9. Memories created
10. Seasonal engagement

#### Journey 89: Late Night Session
1. Playing after hours
2. Fewer players online
3. Quieter world
4. Night lighting active
5. Different atmosphere
6. Reflective gameplay
7. Personal time
8. Intimate with game
9. Peaceful
10. Varied experience

#### Journey 90: Achievement Unlocked
1. System tracks milestones
2. Achievement notification
3. "First Craft!", "100 Items!", etc.
4. Progress visible
5. Goals to aim for
6. Completionist appeal
7. External motivation
8. Shareable
9. Collection element
10. Long-term engagement

### Special Journeys (91-110)

#### Journey 91: Tutorial Completion
1. All tutorial steps done
2. Training wheels off
3. Full game access
4. Sense of readiness
5. World opens up
6. Confident to explore
7. Foundation established
8. Reference available
9. Learning accomplished
10. Game truly begins

#### Journey 92: Monster Aging Benefit
1. Monster created 30 days ago
2. Age bonus activates
3. +1 to all stats
4. Visual maturity?
5. Reward for loyalty
6. Investment pays off
7. 60-day bonus coming
8. Long-term thinking
9. Monster attachment
10. Retention mechanism

#### Journey 93: Share Distribution
1. Complex item scored
2. Many contributors
3. Share breakdown shown
4. Each contribution valued
5. Fair distribution
6. Transparency
7. Encourages participation
8. No free riding
9. Visible fairness
10. Trust in system

#### Journey 94: Workshop Competition
1. Multiple players want same slot
2. Tension builds
3. First to act gets it
4. Graceful losing
5. Try another workshop
6. Natural resolution
7. No hard feelings
8. Social norm established
9. Self-regulation
10. Healthy competition

#### Journey 95: Recipe Experimentation
1. Unknown combination tried
2. Not a valid recipe
3. Nothing produced
4. Ingredients returned
5. Experiment failed
6. Try different combination
7. Discovery process
8. Learning by doing
9. No permanent loss
10. Encourages exploration

#### Journey 96: Mass Production
1. Set up assembly line
2. Multiple monsters assigned
3. Continuous production
4. Optimization achieved
5. Output rate high
6. Efficient use of time
7. Industrial satisfaction
8. Commune prosperity
9. Scalable system
10. Strategic mastery

#### Journey 97: Helping Stranger
1. See struggling player
2. Offer assistance
3. No prior relationship
4. Pure altruism
5. Problem solved
6. Gratitude exchanged
7. Possible new friend
8. Community spirit
9. Emergent kindness
10. Best of multiplayer

#### Journey 98: Returning After Break
1. Took time off
2. Return to game
3. World evolved
4. New features maybe
5. Monsters still there
6. Crafts completed while away
7. Welcome back feeling
8. Catch up on changes
9. Community remembers
10. Re-engagement

#### Journey 99: Grand Finale Craft
1. Ultimate challenge
2. Requires everything learned
3. All systems utilized
4. Peak of skill
5. Maximum effort
6. Legendary result
7. Ultimate satisfaction
8. Game "completed"
9. But more to do
10. Endless depth

#### Journey 100: New Player Joins Your World
1. Fresh player appears
2. You're the veteran now
3. Opportunity to help
4. Pass on knowledge
5. Community grows
6. Cycle continues
7. Living world
8. Meaningful contribution
9. Legacy established
10. The loop completes

### Bonus Journeys (101-110)

#### Journey 101: Finding Easter Egg
1. Exploring obscure area
2. Hidden reference found
3. Developer message
4. Fun discovery
5. Share with community
6. "Did you know...?"
7. World feels handcrafted
8. Attention to detail
9. Delight factor
10. Memorable moment

#### Journey 102: Bug Report Contribution
1. Encounter unexpected behavior
2. Document issue
3. Report to developers
4. Contribution acknowledged
5. Fix implemented
6. Credited in notes
7. Community involvement
8. Game improves
9. Ownership feeling
10. Positive cycle

#### Journey 103: Suggesting Feature
1. Have great idea
2. Share with community
3. Discussion ensues
4. Developers notice
5. Feature considered
6. Eventually implemented
7. "My idea made it!"
8. Player agency
9. Collaborative development
10. Investment deepened

#### Journey 104: Watching Craft Complete
1. Nothing to do but wait
2. Watching workshop work
3. Particles, lights, progress
4. Anticipation building
5. Completion approaching
6. Final moments
7. Burst of effects
8. Output appears
9. Satisfying moment
10. Aesthetic pleasure

#### Journey 105: Organizing Storage
1. Storage area messy
2. Items scattered
3. Take time to organize
4. Push items into rows
5. Group by type
6. Label areas
7. Aesthetically pleasing
8. Functional improvement
9. Personal satisfaction
10. Digital tidying

#### Journey 106: Creating Pixel Art
1. Using colored items
2. Arrange in pattern
3. Create picture/design
4. Creative expression
5. Others admire
6. Screenshot worthy
7. Emergent gameplay
8. Not intended but possible
9. Player creativity
10. Community showcase

#### Journey 107: Building Maze
1. Using walls/items
2. Create elaborate layout
3. Challenge for others
4. Maze navigation
5. Emergent minigame
6. Community participation
7. Builder satisfaction
8. Creative outlet
9. World as canvas
10. Player-generated content

#### Journey 109: Celebrating Milestone
1. Community achievement
2. "10,000th item crafted!"
3. Celebration event
4. Special effects
5. Developer acknowledgment
6. Community pride
7. Shared accomplishment
8. Screenshot moments
9. Social media sharing
10. Marketing opportunity

### Batch System Journeys (111-115)

#### Journey 111: First Batch Setup
1. Goblin at Forge, selects "Iron Ingot"
2. UI shows: "Need 2x Iron Ore, 1x Coal"
3. Recording indicator appears (red dot)
4. Walk to Storage zone
5. Find Iron Ore dispensers
6. Push first Iron Ore toward Forge
7. Push second Iron Ore
8. Find Coal dispenser
9. Push Coal back to Forge
10. Deposit all three into Forge slots
11. Initiate craft
12. Forge runs, Ingot produced
13. Recording complete prompt: "Press [R] to repeat"
14. Understanding dawns - automation unlocked!
15. Press [R], watch Goblin retrace steps automatically

#### Journey 112: Repeat Craft Loop Running
1. Monster in autopilot mode
2. Green [A] badge above head
3. Walks to first dispenser automatically
4. Pushes Iron Ore (dispenser replenishes behind)
5. Continues to second dispenser
6. Continues to Coal dispenser
7. Returns to Forge with all items
8. Deposits in same order as recorded
9. Craft initiates
10. Speech bubble: "Crafting... 3/∞ [■■■□□]"
11. Output appears, monster loops
12. Player free to control other monsters
13. Check back later - pile of Ingots!
14. Efficient batch production achieved
15. Time to set up more craft chains

#### Journey 113: Batch Stops - Dispenser Empty
1. Monster in repeat loop
2. Has made 15 Iron Ingots
3. Walks to Iron Ore dispenser
4. Dispenser shows [ ] - empty!
5. Push action fails
6. Red flash on dispenser cell
7. Speech bubble: "Out of Iron Ore!"
8. Monster exits autopilot mode
9. Green badge disappears
10. Player notified (subtle alert)
11. Check Storage - need to restock
12. Push more Iron Ore to dispenser
13. Dispenser count increases
14. Return to Forge, press [R]
15. Batch resumes from recording start

#### Journey 114: Batch Interrupted - Path Blocked
1. Monster repeating Lumber -> Plank cycle
2. Another player pushed item into path
3. Monster reaches obstruction
4. Cannot continue recorded movement
5. Bump animation, red X particles
6. Speech bubble: "Path blocked!"
7. Autopilot stops
8. Monster waits at obstruction
9. Player investigates
10. Sees misplaced Barrel in path
11. Push Barrel out of the way
12. Return to Workshop, press [R]
13. Batch resumes
14. Lesson: keep paths clear!
15. Consider dedicated craft corridors

#### Journey 115: Restocking Dispensers
1. Storage zone nearly empty
2. Multiple dispensers showing [!] warning
3. Time to restock from resource nodes
4. Control gathering-focused monster (Goblin)
5. Travel to Forest
6. Gather Wood from trees
7. Push Wood back toward city
8. Navigate to Storage zone
9. Push Wood toward Wood dispenser
10. Wood absorbed, count increases
11. Flash effect confirms stocking
12. Repeat for other materials
13. Dispensers healthy again
14. Other monsters' batches can continue
15. Supply chain management gameplay

---

## 12. Future Considerations

### 12.1 Potential Expansions
- Combat system (defend workshops from creatures)
- Weather and seasons
- Monster breeding/genetics
- Player housing
- Formal guild system
- PvP economic competition
- Story/quest system
- Achievements system

### 12.2 Technical Scalability
- Zone instancing for population
- Database sharding
- Load balancing across servers
- Mobile client (reduced visuals)

### 12.3 Monetization (If applicable)
- Cosmetic monster skins
- Custom commune banners
- Bonus monster slots
- No pay-to-win mechanics

### 12.4 Community Features
- In-game chat (text bubbles)
- Forum integration
- Wiki support
- Streaming tools

---

## Appendix A: Keyboard Controls

| Key | Action |
|-----|--------|
| Arrow Keys / WASD | Move |
| Shift + Direction | Push |
| Space | Interact |
| Tab | Cycle monsters |
| M | Monster list |
| I | Inventory/Info toggle |
| Esc | Menu/Cancel/Stop Repeat |
| Enter | Confirm |
| 1-9 | Quick monster select |
| R | Repeat last craft recording |
| Shift+R | Clear recording, start fresh |
| ? | Help |

## Appendix B: Visual Glossary

| Symbol | Meaning |
|--------|---------|
| `@` | Player's controlled monster |
| `G,E,C,O,T` | Monster types |
| `+` | Workshop |
| `W` | Wagon |
| `.` | Floor |
| `#` | Wall |
| `~` | Water |
| `T` | Tree |
| `*` | Ore node |
| `o,O` | Items (various) |

## Appendix C: Color Palette

| Use | RGB | Hex |
|-----|-----|-----|
| Player aura | (100, 200, 255) | #64C8FF |
| Forge glow | (255, 150, 50) | #FF9632 |
| Valid action | (100, 255, 100) | #64FF64 |
| Blocked action | (255, 80, 80) | #FF5050 |
| Masterwork gold | (255, 215, 0) | #FFD700 |
| Common white | (200, 200, 200) | #C8C8C8 |
| Poor gray | (120, 100, 80) | #786450 |

---

*End of Design Document*
