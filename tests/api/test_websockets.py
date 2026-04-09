import asyncio

import pytest
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from src.app.main import app


@pytest.mark.asyncio
async def test_websocket_accepts_connection():
    """Verify the WebSocket endpoint accepts a connection without errors."""
    async with AsyncClient(
        transport=ASGIWebSocketTransport(app=app), base_url="http://test"
    ) as client:
        async with aconnect_ws("/api/v1/tasks/ws/tsk_dummy", client) as ws:
            assert ws is not None
            # Wait for the first heartbeat ping, then exit cleanly.
            message = await asyncio.wait_for(ws.receive_text(), timeout=5.0)
            assert message == '{"type":"ping"}'