# Chute Runner MVP Implementation Plan

This plan produces a playable prototype with placeholder art, ready for real sprites.

---

## Target Scope

### Included
- 3 gate types: Monster, Trap, Door
- 3 chutes: Swords, Shields, Keys
- 6 machines: Smelter, Press, Loom, Forge, Armory, Lockbench
- 3 sources: Ore, Fiber, Oil
- Infrastructure: Belt, Injector, Splitter
- 30-second pre-run build phase, then real-time gate sequence

### Excluded (post-MVP)
- Spell seal, Hunger, Boss gates
- Spell charge, Food chutes
- Runeforge, Capacitor, Kitchen, Recycler machines
- Crystal source
- Merger, Overflow sink
- Meta-progression, unlocks, saving

---

## Constants

```python
# Screen layout (cells)
SCREEN_WIDTH = 48
SCREEN_HEIGHT = 24
TOP_LANE_HEIGHT = 6
FACTORY_HEIGHT = 12
CHUTE_BANK_WIDTH = 16
FACTORY_WIDTH = SCREEN_WIDTH - CHUTE_BANK_WIDTH  # 32

# Timing
BELT_SPEED = 2.0          # cells/second
MACHINE_TIME_SIMPLE = 1.0  # seconds (single input)
MACHINE_TIME_COMPLEX = 1.5 # seconds (dual input)
INJECTOR_CYCLE = 0.4       # seconds per transfer
SOURCE_RATE = 1.0          # items/second when extracted
GATE_SPACING = 5.0         # seconds between gates
PRE_RUN_TIME = 30.0        # seconds to build before run starts

# Combat
RUNNER_HP = 100
TRAP_DAMAGE_PER_MISSING = 5
# Doors: binary pass/fail (instant)
# Monsters: consume swords as DPS (1 sword = 1 damage dealt)
```

---

## Phase 1: Core Framework

### 1.1 Project Setup
- [ ] Create `chute_runner/main.py` entry point
- [ ] Create `chute_runner/constants.py` with values above
- [ ] Create `chute_runner/game_state.py` for central state management
- [ ] Set up pyunicodegame window structure:
  - Root window (48×24)
  - Top lane window (48×6, z=0)
  - Factory window (32×12, z=0)
  - Chute bank window (16×18, z=0, fixed)
  - Cursor/UI overlay (z=10)

### 1.2 Game Loop Shell
- [ ] Implement `update(dt)` with game phase state machine:
  - `PRE_RUN`: countdown timer, building allowed
  - `RUNNING`: gates active, factory running
  - `GAME_OVER`: win/lose screen
- [ ] Implement `render()` calling sub-renderers for each window
- [ ] Implement `on_key()` dispatching to current phase handler

---

## Phase 2: Factory Grid

### 2.1 Grid Data Model
- [ ] Create `chute_runner/factory/grid.py`
- [ ] `Grid` class: 2D array of cells (32×12)
- [ ] `Cell` class: holds entity reference or None
- [ ] Entity base class with `update(dt)` and `render()` methods

### 2.2 Belts
- [ ] Create `chute_runner/factory/belt.py`
- [ ] `Belt` entity: direction (UP/DOWN/LEFT/RIGHT), item slot
- [ ] Belt rendering: directional arrows (→ ← ↑ ↓) or placeholder sprite
- [ ] Belt logic: move item to next belt/entity every `1/BELT_SPEED` seconds
- [ ] Handle belt chains (item flows through connected belts)

### 2.3 Sources
- [ ] Create `chute_runner/factory/source.py`
- [ ] `Source` entity: resource type (ore/fiber/oil), internal buffer
- [ ] Sources produce 1 item per second into buffer (max buffer: 5)
- [ ] Rendering: placeholder icon per resource type

### 2.4 Machines
- [ ] Create `chute_runner/factory/machine.py`
- [ ] `Machine` base class: input slots, output slot, recipe, progress timer
- [ ] Machine states: IDLE, WORKING, OUTPUT_FULL
- [ ] Implement 6 machine types with recipes:
  | Machine | Inputs | Output | Time |
  |---------|--------|--------|------|
  | Smelter | 1 Ore | 1 Plate | 1.0s |
  | Press | 1 Plate | 1 Blade | 1.0s |
  | Loom | 1 Fiber | 1 Wrap | 1.0s |
  | Forge | 1 Blade, 1 Wrap | 1 Sword | 1.5s |
  | Armory | 1 Wrap, 1 Plate | 1 Shield | 1.5s |
  | Lockbench | 1 Plate, 1 Oil | 1 Key | 1.5s |
- [ ] Rendering: placeholder letter/icon per machine type

### 2.5 Injectors
- [ ] Create `chute_runner/factory/injector.py`
- [ ] `Injector` entity: source position, target position, cycle timer
- [ ] Injector can pull from: Source buffer, Machine output, Belt
- [ ] Injector can push to: Machine input, Belt, Chute intake
- [ ] Rendering: arrow showing transfer direction

### 2.6 Splitters
- [ ] Create `chute_runner/factory/splitter.py`
- [ ] `Splitter` entity: alternates output between two directions
- [ ] Rendering: Y-shaped placeholder

---

## Phase 3: Chute System

### 3.1 Chute Data Model
- [ ] Create `chute_runner/chutes.py`
- [ ] `Chute` class: resource type, capacity (20), current fill, pull rate
- [ ] `ChuteBank` class: manages 3 chutes (Swords, Shields, Keys)

### 3.2 Chute Rendering
- [ ] Vertical gauge bar per chute (fill level visualization)
- [ ] Chute icon/label at top
- [ ] Intake port indicator at bottom (where injectors feed)
- [ ] Color coding: green (>50%), yellow (20-50%), red (<20%)

### 3.3 Chute Integration
- [ ] Injectors can target chute intakes
- [ ] Top lane pulls from chutes during gate consumption

---

## Phase 4: Top Lane (Gate Runner)

### 4.1 Runner
- [ ] Create `chute_runner/runner/runner.py`
- [ ] `Runner` class: x position, HP, speed
- [ ] Runner auto-advances left-to-right at constant speed
- [ ] Rendering: placeholder sprite, HP bar above

### 4.2 Gates
- [ ] Create `chute_runner/runner/gate.py`
- [ ] `Gate` base class: x position, demands dict, state (UPCOMING/ACTIVE/PASSED)
- [ ] Gate types:
  | Type | Demand | Failure |
  |------|--------|---------|
  | Monster | N swords | Unspent monster HP damages runner |
  | Trap | N shields | 5 damage per missing shield |
  | Door | N keys | Instant death if unmet |
- [ ] Rendering: gate icon + demand bars

### 4.3 Gate Sequence
- [ ] Create `chute_runner/runner/level.py`
- [ ] `Level` class: list of gates with spawn times
- [ ] Hardcoded test level for MVP (10-15 gates)
- [ ] Gate preview: show next 2 gates with demand counts

### 4.4 Combat Resolution
- [ ] When runner enters gate zone, gate becomes ACTIVE
- [ ] Active gate drains from matching chutes instantly
- [ ] Calculate damage/success based on what was available
- [ ] Apply damage to runner HP
- [ ] Check for game over (HP <= 0 or door failed)

---

## Phase 5: Build Mode & Controls

### 5.1 Cursor System
- [ ] Create `chute_runner/ui/cursor.py`
- [ ] Cursor position on factory grid
- [ ] Arrow keys move cursor
- [ ] Visual highlight on current cell

### 5.2 Building Placement
- [ ] Create `chute_runner/ui/build_menu.py`
- [ ] Number keys select building type:
  | Key | Building |
  |-----|----------|
  | 1 | Belt (→) |
  | 2 | Belt (←) |
  | 3 | Belt (↑) |
  | 4 | Belt (↓) |
  | 5 | Splitter |
  | 6 | Injector |
  | 7 | Smelter |
  | 8 | Press |
  | 9 | Loom |
  | 0 | Forge |
  | - | Armory |
  | = | Lockbench |
  | Q | Ore Source |
  | W | Fiber Source |
  | E | Oil Source |
- [ ] Space places selected building at cursor
- [ ] X deletes building at cursor
- [ ] R rotates injector target direction

### 5.3 Injector Targeting
- [ ] After placing injector, prompt for target direction
- [ ] Visual line showing injector reach/target
- [ ] Tab cycles through valid targets in range

### 5.4 HUD
- [ ] Create `chute_runner/ui/hud.py`
- [ ] Display current phase (PRE_RUN countdown / RUNNING)
- [ ] Display runner HP
- [ ] Display selected building type
- [ ] Mini-legend for controls

---

## Phase 6: Game Flow

### 6.1 Pre-Run Phase
- [ ] 30-second countdown displayed
- [ ] Full building controls active
- [ ] Factory runs (items flow) but gates don't start
- [ ] Chutes can fill up before run begins

### 6.2 Run Phase
- [ ] Gates begin spawning per level sequence
- [ ] Building still allowed (real-time)
- [ ] Runner advances, gates activate, chutes drain

### 6.3 End Conditions
- [ ] Win: runner reaches end of gate sequence
- [ ] Lose: HP reaches 0 or door gate failed
- [ ] Display outcome screen with stats
- [ ] Press any key to restart

---

## Phase 7: Placeholder Art

### 7.1 Factory Sprites (16×16 PNG placeholders)
- [ ] `sprites/belt_right.png` (and 3 other directions)
- [ ] `sprites/splitter.png`
- [ ] `sprites/injector.png`
- [ ] `sprites/source_ore.png`
- [ ] `sprites/source_fiber.png`
- [ ] `sprites/source_oil.png`
- [ ] `sprites/machine_smelter.png`
- [ ] `sprites/machine_press.png`
- [ ] `sprites/machine_loom.png`
- [ ] `sprites/machine_forge.png`
- [ ] `sprites/machine_armory.png`
- [ ] `sprites/machine_lockbench.png`

### 7.2 Item Sprites (8×8 PNG placeholders)
- [ ] `sprites/item_ore.png`
- [ ] `sprites/item_fiber.png`
- [ ] `sprites/item_oil.png`
- [ ] `sprites/item_plate.png`
- [ ] `sprites/item_blade.png`
- [ ] `sprites/item_wrap.png`
- [ ] `sprites/item_sword.png`
- [ ] `sprites/item_shield.png`
- [ ] `sprites/item_key.png`

### 7.3 Runner & Gate Sprites
- [ ] `sprites/runner.png` (16×16)
- [ ] `sprites/gate_monster.png` (16×32)
- [ ] `sprites/gate_trap.png` (16×32)
- [ ] `sprites/gate_door.png` (16×32)

### 7.4 UI Elements
- [ ] `sprites/chute_frame.png`
- [ ] `sprites/hp_bar.png`
- [ ] `sprites/demand_icon_sword.png` (and shield, key)

---

## Phase 8: Polish & Tuning

### 8.1 Visual Feedback
- [ ] Injector pulse animation when transferring
- [ ] Machine progress bar
- [ ] Chute fill animation (items dropping in)
- [ ] Gate demand bars depleting
- [ ] Damage flash on runner

### 8.2 Audio Placeholders
- [ ] (Optional) Placeholder SFX hooks for: placement, transfer, gate pass, damage, win, lose

### 8.3 Balance Tuning
- [ ] Playtest gate demands vs production rates
- [ ] Adjust timing constants as needed
- [ ] Ensure first level is winnable with simple factory layout

---

## File Structure

```
chute_runner/
├── DESIGN.md              # Full design doc
├── MVP_PLAN.md            # This file
├── main.py                # Entry point
├── constants.py           # All magic numbers
├── game_state.py          # Central state machine
├── factory/
│   ├── __init__.py
│   ├── grid.py            # Grid and Cell classes
│   ├── entity.py          # Base entity class
│   ├── belt.py
│   ├── source.py
│   ├── machine.py
│   ├── injector.py
│   └── splitter.py
├── runner/
│   ├── __init__.py
│   ├── runner.py
│   ├── gate.py
│   └── level.py
├── chutes.py
├── ui/
│   ├── __init__.py
│   ├── cursor.py
│   ├── build_menu.py
│   └── hud.py
├── sprites/               # Placeholder PNGs
│   └── ...
└── levels/
    └── test_level.py      # Hardcoded first level
```

---

## Implementation Order

1. **Phase 1** — Get windows rendering, game loop running
2. **Phase 2.1-2.2** — Grid + Belts (items moving on screen)
3. **Phase 2.3-2.4** — Sources + Machines (production working)
4. **Phase 2.5** — Injectors (connect everything)
5. **Phase 3** — Chutes (factory output has somewhere to go)
6. **Phase 5** — Build controls (player can construct factory)
7. **Phase 4** — Runner + Gates (actual gameplay)
8. **Phase 6** — Game flow (win/lose conditions)
9. **Phase 7** — Placeholder art (visual clarity)
10. **Phase 8** — Polish

---

## Success Criteria

The MVP is complete when:
- [x] Player can place all 6 machine types, belts, injectors, sources
- [ ] Items flow through factory: source → machine → machine → chute
- [ ] Runner auto-advances through gate sequence
- [ ] Gates consume from chutes and deal damage on failure
- [ ] Player can win by meeting all gate demands
- [ ] Player can lose by running out of HP or failing a door
- [ ] All entities have placeholder sprites (no raw Unicode fallback)
