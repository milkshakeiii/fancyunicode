#!/usr/bin/env python3
"""
Chute Runner - Main Entry Point

A gate-runner dungeon crawl powered by a compact factory.
Build injectors and machines to feed action chutes in real time,
survive the gate sequence, and expand your layout between runs.

Usage:
    python main.py

Controls:
    Arrow keys: Move cursor
    1-4: Place belt (→←↑↓)
    5: Place splitter
    6: Place injector (T to cycle chute target)
    7-0,-,=: Place machines (Smelter, Press, Loom, Forge, Armory, Lockbench)
    Q,W,E: Place sources (Ore, Fiber, Oil)
    Space/Enter: Place selected building
    X/Delete: Remove building
    S: Start run early (skip remaining pre-run time)
    Escape: Quit
"""
import sys
from pathlib import Path

# Add pyunicodegame to path
pyunicodegame_path = Path("/home/henry/Documents/github/pyunicodegame/src")
if pyunicodegame_path.exists():
    sys.path.insert(0, str(pyunicodegame_path))

# Add this directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import pygame
import pyunicodegame

from gameplay.game import Game, GamePhase
from gameplay.level import create_test_level, create_tutorial_level
from ui.renderer import Renderer, SCREEN_WIDTH, SCREEN_HEIGHT
from ui.input_handler import InputHandler


def main():
    """Main entry point."""
    print("Chute Runner - Starting...")
    print(__doc__)

    # Create game with tutorial level for testing
    level = create_tutorial_level()
    game = Game(level=level)

    # Initialize pyunicodegame
    root = pyunicodegame.init(
        "Chute Runner",
        width=SCREEN_WIDTH,
        height=SCREEN_HEIGHT,
        bg=(15, 15, 20, 255)
    )

    # Create renderer and input handler
    renderer = Renderer(game)
    renderer.init_windows()

    input_handler = InputHandler(game, renderer)

    # Track if we should quit
    should_quit = False

    def update(dt: float):
        """Update game state."""
        nonlocal should_quit

        # Update game logic
        events = game.update(dt)

        # Handle events (could trigger sounds, effects, etc.)
        for event in events:
            pass  # UI reactions could go here

        # Handle held keys
        input_handler.handle_held_keys(dt)

    def render():
        """Render game state."""
        renderer.render()

    def on_key(key: int):
        """Handle key press."""
        nonlocal should_quit
        should_quit = input_handler.handle_key(key)
        if should_quit:
            pyunicodegame.quit()

    # Run game loop
    print("Starting game loop...")
    print("Press Escape to quit")
    pyunicodegame.run(update=update, render=render, on_key=on_key)


if __name__ == "__main__":
    main()
