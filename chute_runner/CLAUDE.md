# Chute Runner - Claude Code Context

## ========================================
## CRITICAL ARCHITECTURAL GOAL
## ========================================

```
+------------------------------------------------------------------+
|                                                                  |
|   THE GAMEPLAY MODULE MUST BE COMPLETELY ENCAPSULATED AND        |
|   DECOUPLED FROM ALL UI DETAILS.                                 |
|                                                                  |
|   - The `gameplay/` module contains ALL game logic               |
|   - It has ZERO dependencies on pyunicodegame, pygame, or UI     |
|   - It can be fully tested with pure Python unit tests           |
|   - The UI layer is a THIN ADAPTER that renders gameplay state   |
|                                                                  |
|   TESTS MUST DEMONSTRATE END-TO-END GAMEPLAY:                    |
|   - Factory production chains working                            |
|   - Items flowing through belts and machines                     |
|   - Chutes filling from factory output                           |
|   - Runner advancing through gates                               |
|   - Gates consuming from chutes                                  |
|   - Win/lose conditions triggering                               |
|                                                                  |
|   DO NOT COMPROMISE ON THIS. REFER BACK TO THIS GOAL OFTEN.      |
|                                                                  |
+------------------------------------------------------------------+
```

## Architecture

```
chute_runner/
├── gameplay/          # PURE PYTHON - NO UI DEPENDENCIES
│   ├── game.py        # Main Game class orchestrating everything
│   ├── grid.py        # Factory grid
│   ├── entities.py    # Belt, Machine, Injector, Source, Splitter
│   ├── items.py       # Item types and recipes
│   ├── chutes.py      # Chute system
│   ├── runner.py      # Runner and gates
│   └── level.py       # Level definitions
│
├── tests/             # THOROUGH END-TO-END TESTS
│   ├── test_grid.py
│   ├── test_entities.py
│   ├── test_chutes.py
│   ├── test_runner.py
│   └── test_game.py   # Full end-to-end gameplay tests
│
├── ui/                # THIN ADAPTER - pyunicodegame rendering
│   ├── renderer.py    # Reads gameplay state, renders to windows
│   ├── input.py       # Translates key presses to gameplay commands
│   └── sprites.py     # Sprite loading and management
│
└── main.py            # Entry point - wires gameplay + UI together
```

## Key Design Rules

1. **gameplay/ imports NOTHING from ui/** - Ever. No exceptions.
2. **Game class exposes state as plain data** - UI reads it to render.
3. **Game class accepts commands as method calls** - UI translates input.
4. **All timing is via `update(dt)`** - No real clocks in gameplay.
5. **Tests run without any display** - Pure logic verification.

## Running Tests

```bash
cd chute_runner
python -m pytest tests/ -v
```

## Running the Game

```bash
cd chute_runner
python main.py
```
