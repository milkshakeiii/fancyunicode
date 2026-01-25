"""
Game constants - all magic numbers in one place.
NO UI DEPENDENCIES.
"""

# =============================================================================
# FACTORY GRID
# =============================================================================
FACTORY_WIDTH = 32   # cells
FACTORY_HEIGHT = 12  # cells

# =============================================================================
# TIMING (all in seconds)
# =============================================================================
BELT_SPEED = 2.0              # cells per second (0.5s per cell)
MACHINE_TIME_SIMPLE = 1.0     # single-input recipes
MACHINE_TIME_COMPLEX = 1.5    # dual-input recipes
INJECTOR_CYCLE = 0.4          # seconds per transfer
SOURCE_RATE = 1.0             # items per second when extracted

GATE_SPACING = 5.0            # seconds between gates
PRE_RUN_TIME = 30.0           # seconds to build before run starts

# =============================================================================
# COMBAT
# =============================================================================
RUNNER_HP = 100
RUNNER_SPEED = 1.0            # arbitrary units per second
TRAP_DAMAGE_PER_MISSING = 5   # HP lost per missing shield

# =============================================================================
# CHUTES
# =============================================================================
CHUTE_CAPACITY = 20           # max items per chute

# =============================================================================
# TOP LANE
# =============================================================================
TOP_LANE_LENGTH = 100.0       # arbitrary units for runner to traverse
GATE_ZONE_WIDTH = 5.0         # width of gate activation zone
