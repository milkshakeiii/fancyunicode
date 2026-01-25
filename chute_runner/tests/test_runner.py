"""
Tests for runner and gate system.
"""
import pytest
from gameplay.runner import (
    Runner, Gate, GateSequence, GateType, GateState,
    GateResult, create_gate
)
from gameplay.chutes import ChuteBank
from gameplay.items import ItemType
from gameplay.constants import RUNNER_HP, RUNNER_SPEED, TOP_LANE_LENGTH, TRAP_DAMAGE_PER_MISSING


class TestRunner:
    """Tests for Runner class."""

    def test_runner_initial_state(self):
        """Runner starts with correct initial state."""
        runner = Runner()
        assert runner.hp == RUNNER_HP
        assert runner.position == 0.0
        assert runner.is_alive
        assert not runner.finished

    def test_runner_advances(self):
        """Runner advances over time."""
        runner = Runner()
        runner.update(1.0)
        assert runner.position == pytest.approx(RUNNER_SPEED * 1.0)

    def test_runner_finishes(self):
        """Runner finishes when reaching end."""
        runner = Runner()

        # Move to end
        runner.update(TOP_LANE_LENGTH / RUNNER_SPEED + 1)

        assert runner.position == TOP_LANE_LENGTH
        assert runner.finished

    def test_runner_stops_when_finished(self):
        """Runner doesn't move after finishing."""
        runner = Runner()
        runner.position = TOP_LANE_LENGTH
        runner.finished = True

        runner.update(1.0)
        assert runner.position == TOP_LANE_LENGTH

    def test_runner_takes_damage(self):
        """Runner takes damage correctly."""
        runner = Runner()
        runner.take_damage(30)

        assert runner.hp == RUNNER_HP - 30
        assert runner.is_alive

    def test_runner_dies(self):
        """Runner dies when HP reaches 0."""
        runner = Runner()
        runner.take_damage(RUNNER_HP)

        assert runner.hp == 0
        assert not runner.is_alive

    def test_runner_kill(self):
        """Runner can be killed instantly."""
        runner = Runner()
        runner.kill()

        assert runner.hp == 0
        assert not runner.is_alive

    def test_runner_stops_when_dead(self):
        """Dead runner doesn't move."""
        runner = Runner()
        runner.kill()

        runner.update(1.0)
        assert runner.position == 0.0

    def test_runner_hp_ratio(self):
        """HP ratio is calculated correctly."""
        runner = Runner()
        assert runner.hp_ratio == 1.0

        runner.take_damage(RUNNER_HP // 2)
        assert runner.hp_ratio == 0.5

    def test_runner_progress_ratio(self):
        """Progress ratio is calculated correctly."""
        runner = Runner()
        assert runner.progress_ratio == 0.0

        runner.position = TOP_LANE_LENGTH / 2
        assert runner.progress_ratio == 0.5


class TestGate:
    """Tests for Gate class."""

    def test_create_gate(self):
        """Gates can be created with convenience function."""
        gate = create_gate(GateType.MONSTER, position=10.0, swords=5)

        assert gate.gate_type == GateType.MONSTER
        assert gate.position == 10.0
        assert gate.demands[ItemType.SWORD] == 5
        assert gate.state == GateState.UPCOMING

    def test_gate_zone(self):
        """Gate zone calculations are correct."""
        gate = create_gate(GateType.MONSTER, position=10.0, swords=5)

        assert gate.zone_start == 10.0
        assert gate.zone_end > gate.zone_start


class TestGateResolution:
    """Tests for gate resolution mechanics."""

    def test_monster_gate_success(self):
        """Monster gate succeeds when swords available."""
        gate = create_gate(GateType.MONSTER, position=10.0, swords=5)
        bank = ChuteBank()

        # Fill chute with enough swords
        for _ in range(5):
            bank.add_item(ItemType.SWORD)

        result = gate.resolve(bank)

        assert result.success
        assert result.damage_taken == 0
        assert result.items_consumed[ItemType.SWORD] == 5
        assert bank.get_count(ItemType.SWORD) == 0
        assert gate.state == GateState.PASSED

    def test_monster_gate_partial(self):
        """Monster gate deals damage for missing swords."""
        gate = create_gate(GateType.MONSTER, position=10.0, swords=5)
        bank = ChuteBank()

        # Only 3 swords available
        for _ in range(3):
            bank.add_item(ItemType.SWORD)

        result = gate.resolve(bank)

        assert not result.success
        assert result.damage_taken == 2  # 5-3 = 2 missing
        assert result.items_consumed[ItemType.SWORD] == 3
        assert result.items_missing[ItemType.SWORD] == 2

    def test_trap_gate_success(self):
        """Trap gate succeeds when shields available."""
        gate = create_gate(GateType.TRAP, position=10.0, shields=4)
        bank = ChuteBank()

        for _ in range(4):
            bank.add_item(ItemType.SHIELD)

        result = gate.resolve(bank)

        assert result.success
        assert result.damage_taken == 0

    def test_trap_gate_damage(self):
        """Trap gate deals 5 damage per missing shield."""
        gate = create_gate(GateType.TRAP, position=10.0, shields=4)
        bank = ChuteBank()

        # Only 1 shield
        bank.add_item(ItemType.SHIELD)

        result = gate.resolve(bank)

        assert not result.success
        assert result.damage_taken == 3 * TRAP_DAMAGE_PER_MISSING  # 3 missing
        assert result.items_missing[ItemType.SHIELD] == 3

    def test_door_gate_success(self):
        """Door gate succeeds when keys available."""
        gate = create_gate(GateType.DOOR, position=10.0, keys=2)
        bank = ChuteBank()

        bank.add_item(ItemType.KEY)
        bank.add_item(ItemType.KEY)

        result = gate.resolve(bank)

        assert result.success
        assert not result.instant_death
        assert result.damage_taken == 0

    def test_door_gate_instant_death(self):
        """Door gate causes instant death when keys missing."""
        gate = create_gate(GateType.DOOR, position=10.0, keys=2)
        bank = ChuteBank()

        # Only 1 key
        bank.add_item(ItemType.KEY)

        result = gate.resolve(bank)

        assert not result.success
        assert result.instant_death
        assert result.items_missing[ItemType.KEY] == 1


class TestGateSequence:
    """Tests for GateSequence class."""

    def test_gates_sorted_by_position(self):
        """Gates are sorted by position."""
        gates = [
            create_gate(GateType.MONSTER, position=30.0, swords=3),
            create_gate(GateType.TRAP, position=10.0, shields=2),
            create_gate(GateType.DOOR, position=20.0, keys=1),
        ]
        seq = GateSequence(gates)

        positions = [g.position for g in seq.gates]
        assert positions == [10.0, 20.0, 30.0]

    def test_get_current_gate(self):
        """get_current_gate returns next unresolved gate."""
        gates = [
            create_gate(GateType.MONSTER, position=10.0, swords=1),
            create_gate(GateType.TRAP, position=20.0, shields=1),
        ]
        seq = GateSequence(gates)

        current = seq.get_current_gate()
        assert current.position == 10.0

        # Mark first as passed
        gates[0].state = GateState.PASSED
        current = seq.get_current_gate()
        assert current.position == 20.0

    def test_get_upcoming_gates(self):
        """get_upcoming_gates returns preview."""
        gates = [
            create_gate(GateType.MONSTER, position=10.0, swords=1),
            create_gate(GateType.TRAP, position=20.0, shields=1),
            create_gate(GateType.DOOR, position=30.0, keys=1),
        ]
        seq = GateSequence(gates)

        upcoming = seq.get_upcoming_gates(2)
        assert len(upcoming) == 2
        assert upcoming[0].position == 10.0
        assert upcoming[1].position == 20.0

    def test_check_and_resolve(self):
        """check_and_resolve resolves gates when runner enters zone."""
        gates = [
            create_gate(GateType.MONSTER, position=10.0, swords=3),
        ]
        seq = GateSequence(gates)

        runner = Runner()
        bank = ChuteBank()
        for _ in range(3):
            bank.add_item(ItemType.SWORD)

        # Runner hasn't reached gate yet
        runner.position = 5.0
        result = seq.check_and_resolve(runner, bank)
        assert result is None

        # Runner enters gate zone
        runner.position = 10.0
        result = seq.check_and_resolve(runner, bank)

        assert result is not None
        assert result.success
        assert gates[0].state == GateState.PASSED

    def test_check_and_resolve_applies_damage(self):
        """check_and_resolve applies damage to runner."""
        gates = [
            create_gate(GateType.TRAP, position=10.0, shields=5),
        ]
        seq = GateSequence(gates)

        runner = Runner()
        bank = ChuteBank()
        # No shields available

        runner.position = 10.0
        result = seq.check_and_resolve(runner, bank)

        # 5 missing shields * 5 damage = 25 damage
        assert runner.hp == RUNNER_HP - 25

    def test_check_and_resolve_door_kills(self):
        """check_and_resolve kills runner on failed door."""
        gates = [
            create_gate(GateType.DOOR, position=10.0, keys=1),
        ]
        seq = GateSequence(gates)

        runner = Runner()
        bank = ChuteBank()
        # No keys

        runner.position = 10.0
        seq.check_and_resolve(runner, bank)

        assert not runner.is_alive

    def test_all_passed(self):
        """all_passed returns correct state."""
        gates = [
            create_gate(GateType.MONSTER, position=10.0, swords=1),
            create_gate(GateType.TRAP, position=20.0, shields=1),
        ]
        seq = GateSequence(gates)

        assert not seq.all_passed()

        gates[0].state = GateState.PASSED
        assert not seq.all_passed()

        gates[1].state = GateState.PASSED
        assert seq.all_passed()
