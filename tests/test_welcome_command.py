from unittest.mock import MagicMock
import sys

# Mock Cloudflare Workers 'js' module
js_mock = MagicMock()
sys.modules['js'] = js_mock

import pytest
from unittest.mock import AsyncMock, patch


def make_env(slack_token="xoxb-test", signing_secret="test-secret"):
    """Create a mock environment object."""
    env = MagicMock()
    env.SLACK_TOKEN = slack_token
    env.SIGNING_SECRET = signing_secret
    env.STATS_KV = AsyncMock()
    env.STATS_KV.getWithMetadata = AsyncMock(return_value=None)
    env.STATS_KV.put = AsyncMock()
    return env


@pytest.mark.asyncio
async def test_welcome_command_success():
    """Test /welcome command sends welcome message to user."""
    from src.worker import handle_welcome_command

    env = make_env()
    body = {"command": "/welcome", "user_id": "U123456"}

    with patch("src.worker.open_conversation", new_callable=AsyncMock) as mock_open, \
         patch("src.worker.send_slack_message", new_callable=AsyncMock) as mock_send, \
         patch("src.worker.increment_commands", new_callable=AsyncMock):

        mock_open.return_value = {"ok": True, "channel": {"id": "D123456"}}
        mock_send.return_value = {"ok": True}

        result = await handle_welcome_command(env, body)

        assert result["ok"] is True
        mock_open.assert_called_once_with(env, "U123456")
        mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_welcome_command_no_user_id():
    """Test /welcome command returns error when no user_id provided."""
    from src.worker import handle_welcome_command

    env = make_env()
    body = {"command": "/welcome"}

    result = await handle_welcome_command(env, body)

    assert result["ok"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_welcome_command_dm_fails():
    """Test /welcome command handles DM open failure gracefully."""
    from src.worker import handle_welcome_command

    env = make_env()
    body = {"command": "/welcome", "user_id": "U123456"}

    with patch("src.worker.open_conversation", new_callable=AsyncMock) as mock_open, \
         patch("src.worker.increment_commands", new_callable=AsyncMock):

        mock_open.return_value = {"ok": False, "error": "channel_not_found"}

        result = await handle_welcome_command(env, body)

        assert result["ok"] is False
        assert "error" in result