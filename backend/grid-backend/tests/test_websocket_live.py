"""
Live WebSocket tests that run against the actual server.
Run with: pytest tests/test_websocket_live.py -v -s
"""

import asyncio
import pytest
import httpx
import websockets
import json


SERVER_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"


@pytest.fixture
async def debug_token():
    """Get a debug token by logging in or registering."""
    async with httpx.AsyncClient() as client:
        # Try to login first
        resp = await client.post(
            f"{SERVER_URL}/api/auth/login",
            json={"username": "ws_test_user", "password": "testpass123"}
        )
        if resp.status_code == 200:
            return resp.json()["token"]

        # If login fails, register
        resp = await client.post(
            f"{SERVER_URL}/api/auth/register",
            json={"username": "ws_test_user", "password": "testpass123"}
        )
        if resp.status_code == 201:
            # Login after registration
            resp = await client.post(
                f"{SERVER_URL}/api/auth/login",
                json={"username": "ws_test_user", "password": "testpass123"}
            )
            return resp.json()["token"]

        raise Exception(f"Failed to get token: {resp.text}")


@pytest.fixture
async def zone_id(debug_token):
    """Create a test zone."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SERVER_URL}/api/zones",
            headers={"Authorization": f"Bearer {debug_token}"},
            json={"name": "ws_test_zone", "width": 100, "height": 100}
        )
        if resp.status_code == 201:
            return resp.json()["id"]
        elif resp.status_code == 409:  # Zone already exists
            # Get existing zone
            resp = await client.get(
                f"{SERVER_URL}/api/zones",
                headers={"Authorization": f"Bearer {debug_token}"}
            )
            zones = resp.json()
            for z in zones:
                if z["name"] == "ws_test_zone":
                    return z["id"]
        raise Exception(f"Failed to create zone: {resp.text}")


@pytest.mark.asyncio
async def test_websocket_connection(debug_token):
    """Test WebSocket connection with valid token."""
    uri = f"{WS_URL}?token={debug_token}"
    async with websockets.connect(uri) as ws:
        assert ws.open
        print("WebSocket connected successfully!")


@pytest.mark.asyncio
async def test_websocket_subscribe_to_zone(debug_token, zone_id):
    """Test subscribing to a zone via WebSocket."""
    uri = f"{WS_URL}?token={debug_token}"
    async with websockets.connect(uri) as ws:
        # Send subscribe message
        subscribe_msg = {"type": "subscribe", "zone_id": zone_id}
        await ws.send(json.dumps(subscribe_msg))
        print(f"Sent subscribe: {subscribe_msg}")

        # Wait for response
        response = await asyncio.wait_for(ws.recv(), timeout=5.0)
        data = json.loads(response)
        print(f"Received: {data}")

        assert data["type"] == "subscribed"
        assert data["zone_id"] == zone_id
        print("Subscription successful!")


@pytest.mark.asyncio
async def test_websocket_receive_tick_update(debug_token, zone_id):
    """Test receiving tick updates after subscribing."""
    uri = f"{WS_URL}?token={debug_token}"
    async with websockets.connect(uri) as ws:
        # Subscribe first
        await ws.send(json.dumps({"type": "subscribe", "zone_id": zone_id}))
        response = await asyncio.wait_for(ws.recv(), timeout=5.0)
        data = json.loads(response)
        assert data["type"] == "subscribed"

        # Wait for tick update
        try:
            tick_response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            tick_data = json.loads(tick_response)
            print(f"Tick update received: {tick_data}")
            assert tick_data["type"] == "tick"
            assert "tick_number" in tick_data
        except asyncio.TimeoutError:
            pytest.fail("No tick update received within 5 seconds")
