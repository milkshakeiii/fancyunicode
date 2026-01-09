"""Configuration constants for the grid client."""

# Server configuration
SERVER_HOST = "localhost"
SERVER_PORT = 8000
WS_URL = f"ws://{SERVER_HOST}:{SERVER_PORT}/ws"
API_URL = f"http://{SERVER_HOST}:{SERVER_PORT}/api"

# Display configuration
GRID_WIDTH = 60
GRID_HEIGHT = 35
WINDOW_TITLE = "Grid Demo - Multiplayer"
BG_COLOR = (20, 20, 30, 255)

# Player visuals - different characters for different players
PLAYER_CHARS = ["@", "P", "O", "X", "*", "#", "&", "%"]

# Colors for OTHER players (not self) - no green to avoid confusion with self
PLAYER_COLORS = [
    (100, 200, 255),   # Cyan
    (255, 100, 100),   # Red
    (255, 255, 100),   # Yellow
    (255, 100, 255),   # Magenta
    (255, 180, 100),   # Orange
    (180, 100, 255),   # Purple
    (255, 150, 150),   # Light red
    (150, 200, 255),   # Light blue
]

# Self color - distinct bright white/cyan
SELF_COLOR = (200, 255, 200)  # Light green-white, clearly different

# Network
RECONNECT_DELAY_SECONDS = 3.0
