"""Tests for the battle system."""

import sys
sys.path.insert(0, '/Users/henry/Documents/github/fancyunicode')

from creature_collector_game.battle import (
    BattleLogic, Unit, UnitPrototype, Attack, AttackType, Side, Direction,
    ActionResult, BattleEvent, Grid, GRID_WIDTH, GRID_HEIGHT
)


# =============================================================================
# Test Fixtures
# =============================================================================

def make_melee_unit(name="Soldier", hp=10, defense=2, damage=5):
    """Create a basic melee unit prototype."""
    return UnitPrototype(
        name=name,
        max_hp=hp,
        defense=defense,
        dodge=1,
        resistance=0,
        attacks=[Attack("Sword", AttackType.MELEE, damage=damage)],
    )


def make_ranged_unit(name="Archer", hp=8, dodge=2, damage=4, range_min=2, range_max=4):
    """Create a basic ranged unit prototype."""
    return UnitPrototype(
        name=name,
        max_hp=hp,
        defense=0,
        dodge=dodge,
        resistance=1,
        attacks=[Attack("Bow", AttackType.RANGED, damage=damage,
                        range_min=range_min, range_max=range_max)],
    )


def make_magic_unit(name="Mage", hp=6, resistance=3, damage=6):
    """Create a basic magic unit prototype."""
    return UnitPrototype(
        name=name,
        max_hp=hp,
        defense=0,
        dodge=0,
        resistance=resistance,
        attacks=[Attack("Fireball", AttackType.MAGIC, damage=damage)],
    )


def make_crystal(hp=20):
    """Create an enemy control crystal."""
    return UnitPrototype(
        name="Crystal",
        max_hp=hp,
        defense=0,
        dodge=0,
        resistance=5,
        attacks=[],
    )


def make_summoner(name="Summoner", hp=8, max_pool=10, efficiency=3, research_eff=2):
    """Create a unit that can summon."""
    return UnitPrototype(
        name=name,
        max_hp=hp,
        defense=1,
        dodge=1,
        resistance=1,
        attacks=[Attack("Staff", AttackType.MELEE, damage=2)],
        research_efficiency=research_eff,
        max_summoning_pool=max_pool,
        summon_efficiency=efficiency,
    )


def make_summonable(name="Minion", hp=5, research_req=5, summon_cost=5):
    """Create a prototype that can be summoned."""
    return UnitPrototype(
        name=name,
        max_hp=hp,
        defense=1,
        dodge=1,
        resistance=1,
        attacks=[Attack("Claw", AttackType.MELEE, damage=3)],
        research_requirement=research_req,
        summoning_cost=summon_cost,
    )


def make_large_unit(name="Giant", hp=20, width=2, height=2):
    """Create a 2x2 unit."""
    return UnitPrototype(
        name=name,
        max_hp=hp,
        defense=4,
        dodge=0,
        resistance=2,
        attacks=[Attack("Stomp", AttackType.MELEE, damage=8)],
        width=width,
        height=height,
    )


# =============================================================================
# Test: Basic Battle Setup
# =============================================================================

def test_basic_battle_setup():
    """Test that a battle can be created with units on both sides."""
    print("=" * 60)
    print("TEST: Basic Battle Setup")
    print("=" * 60)

    soldier = make_melee_unit()
    crystal = make_crystal()

    player = soldier.create_unit("player", 3, 1, Side.PLAYER, is_king=True)
    enemy = crystal.create_unit("crystal", 3, 1, Side.ENEMY, is_king=True)

    battle = BattleLogic(
        player_units=[player],
        enemy_units=[enemy],
        player_king_id="player",
        enemy_king_id="crystal",
    )

    print(f"Current side: {battle.get_current_side().name}")
    print(f"Actions remaining: {battle.get_actions_remaining()}")
    print(f"Turn number: {battle.get_turn_number()}")
    print(f"Battle over: {battle.is_battle_over()}")
    print(f"Player units: {[u.name for u in battle.get_alive_units(Side.PLAYER)]}")
    print(f"Enemy units: {[u.name for u in battle.get_alive_units(Side.ENEMY)]}")

    assert battle.get_current_side() == Side.PLAYER
    assert battle.get_actions_remaining() == 3
    assert not battle.is_battle_over()
    print("\n✓ PASSED\n")


# =============================================================================
# Test: Melee Attack
# =============================================================================

def test_melee_attack():
    """Test melee attack targeting and damage."""
    print("=" * 60)
    print("TEST: Melee Attack")
    print("=" * 60)

    soldier = make_melee_unit(damage=5)
    crystal = make_crystal(hp=20)

    # Player at front (col 3), enemy at front (col 3)
    player = soldier.create_unit("player", 3, 1, Side.PLAYER, is_king=True)
    enemy = crystal.create_unit("crystal", 3, 1, Side.ENEMY, is_king=True)

    battle = BattleLogic([player], [enemy], "player", "crystal")

    # Check valid targets
    targets = battle.get_valid_attack_targets("player", 0)
    print(f"Valid melee targets: {targets}")

    # Crystal has 0 defense, soldier does 5 damage
    print(f"Crystal HP before: {battle.get_unit('crystal').current_hp}")

    result = battle.do_attack("player", 3, 1)
    print(f"Attack success: {result.success}")
    for event in result.events:
        print(f"  Event: {event.event_type} -> {event.data}")

    print(f"Crystal HP after: {battle.get_unit('crystal').current_hp}")
    print(f"Actions remaining: {battle.get_actions_remaining()}")

    assert result.success
    assert battle.get_unit("crystal").current_hp == 15  # 20 - 5 = 15
    assert battle.get_actions_remaining() == 2
    print("\n✓ PASSED\n")


# =============================================================================
# Test: Ranged Attack
# =============================================================================

def test_ranged_attack():
    """Test ranged attack with range constraints."""
    print("=" * 60)
    print("TEST: Ranged Attack")
    print("=" * 60)

    archer = make_ranged_unit(damage=4, range_min=2, range_max=5)
    crystal = make_crystal(hp=20)

    # Archer at back (col 0), crystal at back (col 0)
    # Global columns: player 0 = global 0, enemy 0 = global 7
    # Distance = 7
    player = archer.create_unit("player", 0, 1, Side.PLAYER, is_king=True)
    enemy = crystal.create_unit("crystal", 0, 1, Side.ENEMY, is_king=True)

    battle = BattleLogic([player], [enemy], "player", "crystal")

    targets = battle.get_valid_attack_targets("player", 0)
    print(f"Valid ranged targets (range 2-5): {targets}")
    print(f"  (Expecting columns within range - enemy back col 0 is distance 7)")

    # Try to attack - should fail because crystal is out of range
    result = battle.do_attack("player", 0, 1)
    print(f"Attack on out-of-range target: success={result.success}")
    print(f"  Error: {result.error_message}")

    # Now move crystal to front (col 3 = global 4, distance = 4)
    enemy2 = crystal.create_unit("crystal2", 3, 1, Side.ENEMY, is_king=True)
    battle2 = BattleLogic([player], [enemy2], "player", "crystal2")

    targets2 = battle2.get_valid_attack_targets("player", 0)
    print(f"\nWith enemy at front (col 3, distance 4):")
    print(f"Valid ranged targets: {targets2}")

    result2 = battle2.do_attack("player", 3, 1)
    print(f"Attack success: {result2.success}")
    for event in result2.events:
        print(f"  Event: {event.event_type} -> {event.data}")

    assert not result.success  # Out of range
    assert result2.success  # In range
    print("\n✓ PASSED\n")


# =============================================================================
# Test: Magic Attack (Column Hit)
# =============================================================================

def test_magic_attack():
    """Test magic attack hitting all units in mirror column."""
    print("=" * 60)
    print("TEST: Magic Attack (Column Hit)")
    print("=" * 60)

    mage = make_magic_unit(damage=6)
    soldier = make_melee_unit(hp=10, defense=0)  # 0 resistance
    crystal = make_crystal(hp=20)  # 5 resistance

    # Mage at col 2 (depth 2), targets mirror col 2 on enemy side
    player = mage.create_unit("player", 2, 1, Side.PLAYER, is_king=True)

    # Two enemies in column 2
    enemy1 = soldier.create_unit("enemy1", 2, 0, Side.ENEMY)
    enemy2 = soldier.create_unit("enemy2", 2, 2, Side.ENEMY)
    crystal_unit = crystal.create_unit("crystal", 3, 1, Side.ENEMY, is_king=True)

    battle = BattleLogic([player], [enemy1, enemy2, crystal_unit], "player", "crystal")

    targets = battle.get_valid_attack_targets("player", 0)
    print(f"Valid magic targets (mirror column): {targets}")
    print(f"  (Mage at col 2 targets enemy col 2)")

    print(f"\nEnemies in column 2:")
    print(f"  enemy1 at (2,0): HP={battle.get_unit('enemy1').current_hp}")
    print(f"  enemy2 at (2,2): HP={battle.get_unit('enemy2').current_hp}")

    # Magic hits all in column
    result = battle.do_attack("player", 2, 0)  # Target any cell in col 2
    print(f"\nMagic attack result: success={result.success}")
    for event in result.events:
        print(f"  Event: {event.event_type} -> {event.data}")

    print(f"\nAfter magic attack:")
    print(f"  enemy1 HP: {battle.get_unit('enemy1').current_hp}")
    print(f"  enemy2 HP: {battle.get_unit('enemy2').current_hp}")

    # Both should take 6 damage (0 resistance)
    assert battle.get_unit("enemy1").current_hp == 4  # 10 - 6
    assert battle.get_unit("enemy2").current_hp == 4  # 10 - 6
    print("\n✓ PASSED\n")


# =============================================================================
# Test: Unit Movement
# =============================================================================

def test_movement():
    """Test unit movement in all directions."""
    print("=" * 60)
    print("TEST: Unit Movement")
    print("=" * 60)

    soldier = make_melee_unit()
    crystal = make_crystal()

    # Player at center
    player = soldier.create_unit("player", 1, 1, Side.PLAYER, is_king=True)
    enemy = crystal.create_unit("crystal", 1, 1, Side.ENEMY, is_king=True)

    battle = BattleLogic([player], [enemy], "player", "crystal")

    print(f"Player starting position: ({player.x}, {player.y})")

    valid_dirs = battle.get_valid_move_directions("player")
    print(f"Valid move directions: {[d.name for d in valid_dirs]}")

    # Move east
    result = battle.do_move("player", Direction.EAST)
    print(f"\nMove EAST: success={result.success}")
    for event in result.events:
        print(f"  Event: {event.event_type} -> {event.data}")

    unit = battle.get_unit("player")
    print(f"Player new position: ({unit.x}, {unit.y})")

    assert unit.x == 2 and unit.y == 1
    print("\n✓ PASSED\n")


# =============================================================================
# Test: Movement Displacement
# =============================================================================

def test_movement_displacement():
    """Test that moving into another unit displaces it."""
    print("=" * 60)
    print("TEST: Movement Displacement")
    print("=" * 60)

    soldier = make_melee_unit()
    crystal = make_crystal()

    # Two player units adjacent
    player1 = soldier.create_unit("player1", 1, 1, Side.PLAYER, is_king=True)
    player2 = soldier.create_unit("player2", 2, 1, Side.PLAYER)
    enemy = crystal.create_unit("crystal", 1, 1, Side.ENEMY, is_king=True)

    battle = BattleLogic([player1, player2], [enemy], "player1", "crystal")

    print(f"player1 at ({player1.x}, {player1.y})")
    print(f"player2 at ({player2.x}, {player2.y})")

    # player1 moves east into player2's space
    result = battle.do_move("player1", Direction.EAST)
    print(f"\nplayer1 moves EAST into player2's space:")
    print(f"  success={result.success}")
    for event in result.events:
        print(f"  Event: {event.event_type} -> {event.data}")

    p1 = battle.get_unit("player1")
    p2 = battle.get_unit("player2")
    print(f"\nAfter displacement:")
    print(f"  player1 at ({p1.x}, {p1.y})")
    print(f"  player2 at ({p2.x}, {p2.y})")

    # player1 should be at (2,1), player2 displaced west to (1,1)
    # Wait, inverse direction is WEST for player2
    # Actually player1 moves east, so player2 is displaced in the inverse = west
    # But player1 was at (1,1), moving east would make it (2,1)
    # player2 was at (2,1), displaced west would be (1,1)
    assert p1.x == 2 and p1.y == 1
    assert p2.x == 1 and p2.y == 1
    print("\n✓ PASSED\n")


# =============================================================================
# Test: Large Unit (2x2)
# =============================================================================

def test_large_unit():
    """Test that large units occupy multiple cells."""
    print("=" * 60)
    print("TEST: Large Unit (2x2 footprint)")
    print("=" * 60)

    giant = make_large_unit(width=2, height=2)
    crystal = make_crystal()

    # Giant at (0,0) occupies (0,0), (1,0), (0,1), (1,1)
    player = giant.create_unit("giant", 0, 0, Side.PLAYER, is_king=True)
    enemy = crystal.create_unit("crystal", 1, 1, Side.ENEMY, is_king=True)

    battle = BattleLogic([player], [enemy], "giant", "crystal")

    unit = battle.get_unit("giant")
    cells = unit.get_occupied_cells()
    ref = unit.get_reference_cell()

    print(f"Giant at ({unit.x}, {unit.y}), size {unit.width}x{unit.height}")
    print(f"Occupied cells: {cells}")
    print(f"Reference cell (front-most, top-most): {ref}")

    # Check valid moves - should have limited options due to size
    valid_dirs = battle.get_valid_move_directions("giant")
    print(f"Valid move directions: {[d.name for d in valid_dirs]}")

    assert len(cells) == 4
    assert ref == (1, 0)  # Front-most column is 1, top row is 0
    print("\n✓ PASSED\n")


# =============================================================================
# Test: Research Action
# =============================================================================

def test_research():
    """Test research action accumulates team research pool."""
    print("=" * 60)
    print("TEST: Research Action")
    print("=" * 60)

    summoner = make_summoner(research_eff=3)
    soldier = make_melee_unit()
    crystal = make_crystal()

    player1 = summoner.create_unit("summoner", 0, 0, Side.PLAYER, is_king=True)
    player2 = soldier.create_unit("soldier", 1, 0, Side.PLAYER)  # No research eff
    enemy = crystal.create_unit("crystal", 1, 1, Side.ENEMY, is_king=True)

    battle = BattleLogic([player1, player2], [enemy], "summoner", "crystal")

    print(f"Summoner research_efficiency: {summoner.research_efficiency}")
    print(f"Soldier research_efficiency: {soldier.research_efficiency}")
    print(f"Potential research: {battle.get_potential_research()}")
    print(f"Current research pool: {battle.get_research_pool(Side.PLAYER)}")

    result = battle.do_research()
    print(f"\nResearch action: success={result.success}")
    for event in result.events:
        print(f"  Event: {event.event_type} -> {event.data}")

    print(f"Research pool after: {battle.get_research_pool(Side.PLAYER)}")

    assert battle.get_research_pool(Side.PLAYER) == 3
    print("\n✓ PASSED\n")


# =============================================================================
# Test: Summon Charge
# =============================================================================

def test_summon_charge():
    """Test summon charge action fills summoning pool."""
    print("=" * 60)
    print("TEST: Summon Charge Action")
    print("=" * 60)

    summoner = make_summoner(max_pool=10, efficiency=4)
    crystal = make_crystal()

    player = summoner.create_unit("summoner", 0, 0, Side.PLAYER, is_king=True)
    enemy = crystal.create_unit("crystal", 1, 1, Side.ENEMY, is_king=True)

    battle = BattleLogic([player], [enemy], "summoner", "crystal")

    unit = battle.get_unit("summoner")
    print(f"Summoner pool: {unit.current_summoning_pool}/{unit.prototype.max_summoning_pool}")
    print(f"Summon efficiency: {unit.prototype.summon_efficiency}")

    result = battle.do_summon_charge("summoner")
    print(f"\nSummon charge: success={result.success}")
    for event in result.events:
        print(f"  Event: {event.event_type} -> {event.data}")

    unit = battle.get_unit("summoner")
    print(f"Pool after: {unit.current_summoning_pool}/{unit.prototype.max_summoning_pool}")

    assert unit.current_summoning_pool == 4
    print("\n✓ PASSED\n")


# =============================================================================
# Test: Summon Unit
# =============================================================================

def test_summon():
    """Test summoning a new unit onto the battlefield."""
    print("=" * 60)
    print("TEST: Summon Unit")
    print("=" * 60)

    summoner_proto = make_summoner(max_pool=10, efficiency=10, research_eff=5)
    minion_proto = make_summonable(research_req=5, summon_cost=5)
    crystal = make_crystal()

    player = summoner_proto.create_unit("summoner", 1, 1, Side.PLAYER, is_king=True)
    enemy = crystal.create_unit("crystal", 1, 1, Side.ENEMY, is_king=True)

    battle = BattleLogic([player], [enemy], "summoner", "crystal")

    print("Step 1: Research to meet requirement")
    battle.do_research()
    print(f"  Research pool: {battle.get_research_pool(Side.PLAYER)}")

    print("\nStep 2: Charge summoning pool")
    battle.do_summon_charge("summoner")
    unit = battle.get_unit("summoner")
    print(f"  Summoning pool: {unit.current_summoning_pool}")

    print("\nStep 3: Check if can summon")
    can_summon = battle.can_summon("summoner", minion_proto)
    print(f"  Can summon minion: {can_summon}")

    spawn_locs = battle.get_valid_summon_locations("summoner", minion_proto)
    print(f"  Valid spawn locations: {spawn_locs}")

    print("\nStep 4: End turn (used 3 actions)")
    battle.end_turn()  # Switch to enemy
    battle.end_turn()  # Switch back to player

    print("\nStep 5: Summon the minion")
    result = battle.do_summon("summoner", minion_proto, spawn_locs[0][0], spawn_locs[0][1])
    print(f"  Summon success: {result.success}")
    for event in result.events:
        print(f"  Event: {event.event_type} -> {event.data}")

    player_units = battle.get_alive_units(Side.PLAYER)
    print(f"\nPlayer units after summon: {[u.name for u in player_units]}")

    # Verify summoning pool was consumed
    unit = battle.get_unit("summoner")
    print(f"Summoner pool after: {unit.current_summoning_pool} (cost was {minion_proto.summoning_cost})")

    assert len(player_units) == 2
    assert unit.current_summoning_pool == 5  # 10 - 5 = 5
    print("\n✓ PASSED\n")


# =============================================================================
# Test: Win Condition (Kill Crystal)
# =============================================================================

def test_win_condition():
    """Test that destroying the enemy king ends the battle."""
    print("=" * 60)
    print("TEST: Win Condition (Kill Crystal)")
    print("=" * 60)

    soldier = make_melee_unit(damage=10)
    crystal = make_crystal(hp=15)

    player = soldier.create_unit("player", 3, 1, Side.PLAYER, is_king=True)
    enemy = crystal.create_unit("crystal", 3, 1, Side.ENEMY, is_king=True)

    battle = BattleLogic([player], [enemy], "player", "crystal")

    print(f"Crystal HP: {battle.get_unit('crystal').current_hp}")

    # First attack
    result1 = battle.do_attack("player", 3, 1)
    print(f"\nAttack 1: Crystal HP = {battle.get_unit('crystal').current_hp}")
    print(f"  Battle over: {battle.is_battle_over()}")

    # Second attack - should kill
    result2 = battle.do_attack("player", 3, 1)
    print(f"\nAttack 2:")
    for event in result2.events:
        print(f"  Event: {event.event_type} -> {event.data}")

    print(f"\nBattle over: {battle.is_battle_over()}")
    print(f"Winner: {battle.get_winner().name if battle.get_winner() else 'None'}")

    assert battle.is_battle_over()
    assert battle.get_winner() == Side.PLAYER
    print("\n✓ PASSED\n")


# =============================================================================
# Test: Turn Structure
# =============================================================================

def test_turn_structure():
    """Test turn switching and action counting."""
    print("=" * 60)
    print("TEST: Turn Structure")
    print("=" * 60)

    soldier = make_melee_unit()
    crystal = make_crystal()

    player = soldier.create_unit("player", 3, 1, Side.PLAYER, is_king=True)
    enemy = crystal.create_unit("crystal", 3, 1, Side.ENEMY, is_king=True)

    battle = BattleLogic([player], [enemy], "player", "crystal")

    print(f"Turn {battle.get_turn_number()}, {battle.get_current_side().name}'s turn")
    print(f"Actions: {battle.get_actions_remaining()}")

    # Use all 3 actions
    battle.do_pass()
    print(f"After pass: {battle.get_actions_remaining()} actions")
    battle.do_pass()
    print(f"After pass: {battle.get_actions_remaining()} actions")
    battle.do_pass()
    print(f"After pass: {battle.get_actions_remaining()} actions")

    # Try to act with no actions
    result = battle.do_pass()
    print(f"\nPass with 0 actions: success={result.success}, error={result.error_message}")

    # End turn
    battle.end_turn()
    print(f"\nAfter end_turn:")
    print(f"  Turn {battle.get_turn_number()}, {battle.get_current_side().name}'s turn")
    print(f"  Actions: {battle.get_actions_remaining()}")

    assert battle.get_current_side() == Side.ENEMY
    assert battle.get_actions_remaining() == 3
    print("\n✓ PASSED\n")


# =============================================================================
# Run All Tests
# =============================================================================

def run_all_tests():
    """Run all tests."""
    tests = [
        test_basic_battle_setup,
        test_melee_attack,
        test_ranged_attack,
        test_magic_attack,
        test_movement,
        test_movement_displacement,
        test_large_unit,
        test_research,
        test_summon_charge,
        test_summon,
        test_win_condition,
        test_turn_structure,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ FAILED: {test.__name__}")
            print(f"  Error: {e}")
            failed += 1

    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        test_func = globals().get(test_name)
        if test_func:
            test_func()
        else:
            print(f"Unknown test: {test_name}")
    else:
        run_all_tests()
