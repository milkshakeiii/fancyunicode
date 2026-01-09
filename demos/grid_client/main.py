#!/usr/bin/env python3
"""
Multiplayer Grid Demo Client
Connects to grid_backend via WebSocket and renders with PyUnicodeGame.
"""

import pygame
import pyunicodegame
import sys
import argparse

from .config import GRID_WIDTH, GRID_HEIGHT
from .game_state import ClientState
from .network import NetworkClient, authenticate, get_or_create_zone
from .renderer import Renderer


def main():
    parser = argparse.ArgumentParser(description="Grid Demo Client")
    parser.add_argument("--username", "-u", default="player1", help="Username for auth")
    parser.add_argument("--password", "-p", default="password123", help="Password for auth")
    parser.add_argument("--zone", "-z", default="demo", help="Zone name to join")
    args = parser.parse_args()

    # Initialize game state
    state = ClientState()

    # Authenticate with server
    print(f"Authenticating as {args.username}...")
    auth_result = authenticate(args.username, args.password)
    if not auth_result:
        print("Authentication failed. Is the server running?")
        sys.exit(1)

    token, player_id = auth_result
    state.session_token = token
    state.player_id = player_id
    state.authenticated = True
    print(f"Authenticated! Player ID: {player_id}")

    # Get or create zone
    print(f"Setting up zone '{args.zone}'...")
    zone_id = get_or_create_zone(token, args.zone)
    if not zone_id:
        print("Failed to get/create zone. Make sure the server is running with debug mode.")
        sys.exit(1)

    print(f"Zone ID: {zone_id}")

    # Start network client
    network = NetworkClient(state)
    network.start()

    # Subscribe to zone
    network.send_subscribe(zone_id)

    # Create our player entity at center
    network.send_intent({
        "action": "create_entity",
        "x": GRID_WIDTH // 2,
        "y": GRID_HEIGHT // 2,
        "width": 1,
        "height": 1,
        "metadata": {"char": "@"}
    })

    # Initialize renderer
    renderer = Renderer(state)
    renderer.init_display()

    def find_my_entity() -> bool:
        """Find and set my entity ID based on owner_id."""
        for eid, entity in state.entities.items():
            if entity.owner_id == player_id:
                state.my_entity_id = eid
                return True
        return False

    def update(dt: float) -> None:
        """Update function called each frame."""
        # Try to find our entity if not yet found
        if not state.my_entity_id:
            find_my_entity()

        # Process any pending incoming messages (optional additional processing)
        while not network.incoming_queue.empty():
            try:
                network.incoming_queue.get_nowait()
            except Exception:
                break

    def render() -> None:
        """Render function called each frame."""
        renderer.render()

    def on_key(key) -> None:
        """Handle key presses."""
        if key == pygame.K_q:
            network.stop()
            pyunicodegame.quit()
        elif key == pygame.K_UP:
            network.send_move(0, -1)
        elif key == pygame.K_DOWN:
            network.send_move(0, 1)
        elif key == pygame.K_LEFT:
            network.send_move(-1, 0)
        elif key == pygame.K_RIGHT:
            network.send_move(1, 0)

    print("Starting game loop...")
    print("Controls: Arrow keys to move, Q to quit")

    try:
        pyunicodegame.run(update=update, render=render, on_key=on_key)
    finally:
        network.stop()


if __name__ == "__main__":
    main()
