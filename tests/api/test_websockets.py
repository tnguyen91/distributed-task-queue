import pytest
from httpx import ASGITransport
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from src.app.main import app


@pytest.mark.asyncio
async def test_websocket_accepts_connection():
    """Verify the WebSocket endpoint accepts a connection without errors."""
    transport = ASGIWebSocketTransport(app=app)
    async with aconnect_ws(
        "http://test/api/v1/tasks/ws/tsk_dummy",
        transport=transport,
    ) as ws:
        assert ws is not None