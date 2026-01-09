#!/bin/bash
#
# Multiplayer Grid Demo Test Script
# Usage: ./test_multiplayer.sh [num_clients]
#
# Starts the backend server and launches N client windows.
# Default: 2 clients
#
# Requirements:
# - gridtickmultiplayer repo cloned alongside fancyunicode
# - Backend venv set up with dependencies
#

set -e

NUM_CLIENTS=${1:-2}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_ROOT="/home/henry/Documents/github/gridtickmultiplayer"
PYUNICODE_PATH="/home/henry/Documents/github/pyunicodegame/src"

echo "=== Multiplayer Grid Demo Test ==="
echo "Clients: $NUM_CLIENTS"
echo "Project root: $PROJECT_ROOT"
echo "Backend root: $BACKEND_ROOT"
echo ""

# Check backend repo exists
if [ ! -d "$BACKEND_ROOT" ]; then
    echo "ERROR: Backend repo not found at $BACKEND_ROOT"
    echo "Clone it with: gh repo clone milkshakeiii/gridtickmultiplayer"
    exit 1
fi

# Cleanup function
cleanup() {
    echo ""
    echo "Shutting down..."

    # Kill client processes
    if [ -n "$CLIENT_PIDS" ]; then
        for pid in $CLIENT_PIDS; do
            kill $pid 2>/dev/null || true
        done
    fi

    # Kill backend
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi

    echo "Done."
    exit 0
}

trap cleanup SIGINT SIGTERM

# Check if backend is already running
if lsof -i :8000 >/dev/null 2>&1; then
    echo "Port 8000 is in use. Stopping existing backend..."
    pkill -f "grid_backend.main" 2>/dev/null || true
    sleep 2
fi

# Start backend (using venv)
echo "Starting backend server..."
cd "$BACKEND_ROOT"
source venv/bin/activate
python -m grid_backend.main > /tmp/grid_backend_test.log 2>&1 &
BACKEND_PID=$!
deactivate  # Exit venv so clients use system Python

# Wait for backend to start
echo "Waiting for backend to start..."
for i in {1..10}; do
    if curl -s http://localhost:8000/docs >/dev/null 2>&1; then
        echo "Backend is ready!"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "ERROR: Backend failed to start. Check /tmp/grid_backend_test.log"
        cat /tmp/grid_backend_test.log | tail -20
        exit 1
    fi
    sleep 1
done

echo ""

# Launch clients (using system Python with pygame)
CLIENT_PIDS=""
cd "$PROJECT_ROOT"

for i in $(seq 1 $NUM_CLIENTS); do
    USERNAME="player$i"
    PASSWORD="testpass123"

    echo "Launching client $i ($USERNAME)..."

    PYTHONPATH="$PYUNICODE_PATH:$PYTHONPATH" /usr/bin/python3 -m demos.grid_client.main \
        -u "$USERNAME" \
        -p "$PASSWORD" &

    CLIENT_PIDS="$CLIENT_PIDS $!"

    # Small delay between client launches
    sleep 0.5
done

echo ""
echo "=== All clients launched ==="
echo "Backend PID: $BACKEND_PID"
echo "Client PIDs: $CLIENT_PIDS"
echo ""
echo "Controls:"
echo "  Arrow keys: Move"
echo "  Q: Quit client"
echo "  Ctrl+C: Stop all"
echo ""
echo "Backend log: /tmp/grid_backend_test.log"
echo ""

# Wait for all clients to exit
wait $CLIENT_PIDS 2>/dev/null || true

echo "All clients closed."
cleanup
