"""
Battle logic module for the creature collector game.

This module provides pure game logic for the battle system,
separated from UI/rendering concerns.

Example usage:
    from creature_collector_game.battle import (
        BattleLogic, Unit, UnitPrototype, Attack, AttackType, Side, Direction
    )

    # Create unit prototypes
    soldier = UnitPrototype(
        name="Soldier",
        max_hp=10,
        defense=2,
        dodge=1,
        resistance=0,
        attacks=[Attack("Sword", AttackType.MELEE, damage=5)],
    )

    # Create units
    player_king = soldier.create_unit("player", 1, 1, Side.PLAYER, is_king=True)
    enemy_crystal = UnitPrototype(
        name="Crystal", max_hp=20, defense=0, dodge=0, resistance=5, attacks=[]
    ).create_unit("crystal", 1, 1, Side.ENEMY, is_king=True)

    # Start battle
    battle = BattleLogic(
        player_units=[player_king],
        enemy_units=[enemy_crystal],
        player_king_id="player",
        enemy_king_id="crystal",
    )

    # Execute actions
    result = battle.do_attack("player", 1, 1)
    if result.success:
        for event in result.events:
            print(f"{event.event_type}: {event.data}")
"""

# Core models
from .models import (
    Unit,
    UnitPrototype,
    Attack,
    AttackType,
    ActionType,
    Side,
    Direction,
    ActionResult,
    BattleEvent,
)

# Main controller
from .battle_logic import BattleLogic

# State (for advanced usage)
from .battle_state import BattleState, Team

# Grid utilities (for advanced usage)
from .grid import Grid, GRID_WIDTH, GRID_HEIGHT

__all__ = [
    # Core models
    "Unit",
    "UnitPrototype",
    "Attack",
    "AttackType",
    "ActionType",
    "Side",
    "Direction",
    "ActionResult",
    "BattleEvent",
    # Main controller
    "BattleLogic",
    # State
    "BattleState",
    "Team",
    # Grid
    "Grid",
    "GRID_WIDTH",
    "GRID_HEIGHT",
]
