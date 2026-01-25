"""
Level definitions - predefined gate sequences.
NO UI DEPENDENCIES.
"""
from typing import List

from .runner import Gate, GateSequence, GateType, create_gate
from .items import ItemType
from .constants import GATE_SPACING


def create_test_level() -> GateSequence:
    """
    Create the MVP test level.

    A sequence of 10 gates with escalating difficulty:
    - Early gates: simple, low demands
    - Mid gates: mixed types, higher demands
    - Late gates: challenging combinations
    """
    gates: List[Gate] = []

    # Gate 1: Easy monster (5 swords)
    gates.append(create_gate(GateType.MONSTER, position=10.0, swords=5))

    # Gate 2: Easy trap (3 shields)
    gates.append(create_gate(GateType.TRAP, position=20.0, shields=3))

    # Gate 3: First door (1 key)
    gates.append(create_gate(GateType.DOOR, position=30.0, keys=1))

    # Gate 4: Medium monster (8 swords)
    gates.append(create_gate(GateType.MONSTER, position=40.0, swords=8))

    # Gate 5: Medium trap (5 shields)
    gates.append(create_gate(GateType.TRAP, position=50.0, shields=5))

    # Gate 6: Door (2 keys)
    gates.append(create_gate(GateType.DOOR, position=60.0, keys=2))

    # Gate 7: Hard monster (12 swords)
    gates.append(create_gate(GateType.MONSTER, position=70.0, swords=12))

    # Gate 8: Hard trap (8 shields)
    gates.append(create_gate(GateType.TRAP, position=80.0, shields=8))

    # Gate 9: Door (3 keys)
    gates.append(create_gate(GateType.DOOR, position=88.0, keys=3))

    # Gate 10: Final monster (10 swords)
    gates.append(create_gate(GateType.MONSTER, position=95.0, swords=10))

    return GateSequence(gates)


def create_tutorial_level() -> GateSequence:
    """
    A very easy level for learning the mechanics.
    """
    gates: List[Gate] = []

    # Just 3 simple gates
    gates.append(create_gate(GateType.MONSTER, position=25.0, swords=3))
    gates.append(create_gate(GateType.TRAP, position=50.0, shields=2))
    gates.append(create_gate(GateType.DOOR, position=75.0, keys=1))

    return GateSequence(gates)


def create_sword_only_level() -> GateSequence:
    """
    Level with only monster gates - good for testing sword production.
    """
    gates: List[Gate] = []

    for i in range(5):
        position = 20.0 + i * 18.0
        swords = 3 + i * 2  # 3, 5, 7, 9, 11
        gates.append(create_gate(GateType.MONSTER, position=position, swords=swords))

    return GateSequence(gates)
