"""WebSocket client running in a background thread."""

import json
import threading
import queue
from typing import Optional

import requests
import websocket

from .config import WS_URL, API_URL, RECONNECT_DELAY_SECONDS
from .game_state import ClientState


class NetworkClient:
    """
    Manages WebSocket connection in a background thread.
    Uses queues to communicate with the main game thread.
    """

    def __init__(self, state: ClientState):
        self.state = state

        # Thread-safe message queues
        self.outgoing_queue: queue.Queue = queue.Queue()
        self.incoming_queue: queue.Queue = queue.Queue()

        # Thread management
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # WebSocket connection
        self._ws: Optional[websocket.WebSocketApp] = None

    def start(self) -> None:
        """Start the network thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_network_thread, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the network thread."""
        self._stop_event.set()
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run_network_thread(self) -> None:
        """Entry point for the network thread - handles reconnection."""
        import time

        while not self._stop_event.is_set():
            try:
                self._connect_and_run()
            except Exception as e:
                self.state.set_status(f"Error: {e}")
                self.state.connected = False

            if not self._stop_event.is_set():
                self.state.set_status(f"Reconnecting in {RECONNECT_DELAY_SECONDS}s...")
                time.sleep(RECONNECT_DELAY_SECONDS)

    def _connect_and_run(self) -> None:
        """Connect to WebSocket and handle messages."""
        if not self.state.session_token:
            self.state.set_status("No session token")
            import time
            time.sleep(1)
            return

        ws_url = f"{WS_URL}?token={self.state.session_token}"
        self.state.set_status("Connecting...")

        def on_open(ws):
            self.state.connected = True
            self.state.set_status("Connected")
            # Start sender thread
            sender = threading.Thread(target=self._send_loop, daemon=True)
            sender.start()

        def on_message(ws, message):
            try:
                data = json.loads(message)
                msg_type = data.get("type")

                if msg_type == "tick":
                    self.state.update_from_tick(data)
                elif msg_type == "subscribed":
                    self.state.subscribed_zone = data.get("zone_id")
                    zone_short = data.get("zone_id", "")[:8]
                    self.state.set_status(f"In zone {zone_short}...")
                elif msg_type == "error":
                    self.state.set_status(f"Error: {data.get('message')}")
                elif msg_type == "intent_received":
                    pass  # Acknowledged

                # Also queue for main thread processing if needed
                self.incoming_queue.put(data)
            except json.JSONDecodeError:
                pass

        def on_error(ws, error):
            self.state.set_status(f"WS Error: {error}")

        def on_close(ws, close_status_code, close_msg):
            self.state.connected = False
            self.state.set_status("Disconnected")

        self._ws = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )

        # This blocks until the connection closes
        self._ws.run_forever()

    def _send_loop(self) -> None:
        """Send queued messages to server."""
        while self.state.connected and not self._stop_event.is_set():
            try:
                message = self.outgoing_queue.get(timeout=0.1)
                if self._ws and self.state.connected:
                    self._ws.send(json.dumps(message))
            except queue.Empty:
                continue
            except Exception:
                break

    # Public API for main thread

    def send_subscribe(self, zone_id: str) -> None:
        """Queue a zone subscription request."""
        self.outgoing_queue.put({
            "type": "subscribe",
            "zone_id": zone_id
        })

    def send_intent(self, data: dict) -> None:
        """Queue a player intent."""
        self.outgoing_queue.put({
            "type": "intent",
            "data": data
        })

    def send_move(self, dx: int, dy: int) -> None:
        """Convenience: send a move intent."""
        if self.state.my_entity_id:
            self.send_intent({
                "action": "move",
                "entity_id": self.state.my_entity_id,
                "dx": dx,
                "dy": dy
            })


def authenticate(username: str, password: str) -> Optional[tuple[str, str]]:
    """
    Authenticate with the server via REST API.
    Returns (token, player_id) or None on failure.
    """
    # Try to register first (in case new user)
    try:
        requests.post(
            f"{API_URL}/auth/register",
            json={"username": username, "password": password},
            timeout=5
        )
    except requests.RequestException:
        pass

    # Login
    try:
        resp = requests.post(
            f"{API_URL}/auth/login",
            json={"username": username, "password": password},
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            return data["token"], data["player_id"]
    except requests.RequestException as e:
        print(f"Login failed: {e}")

    return None


def get_or_create_zone(token: str, zone_name: str = "demo") -> Optional[str]:
    """
    Get a zone by name or create it if it doesn't exist.
    Returns zone_id or None.
    """
    headers = {"Authorization": f"Bearer {token}"}

    try:
        # List zones
        resp = requests.get(f"{API_URL}/zones", headers=headers, timeout=5)
        if resp.status_code == 200:
            zones = resp.json().get("zones", [])
            for z in zones:
                if z["name"] == zone_name:
                    return z["id"]

        # Try to create zone (requires debug role)
        resp = requests.post(
            f"{API_URL}/zones",
            headers=headers,
            json={"name": zone_name, "width": 60, "height": 35},
            timeout=5
        )
        if resp.status_code == 201:
            return resp.json()["id"]

    except requests.RequestException as e:
        print(f"Zone setup failed: {e}")

    return None
