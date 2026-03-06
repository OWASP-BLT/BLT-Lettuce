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
async def test_welcome_command_no_user_id():
    """Test /welcome command returns error when no user_id provided."""
    from src.worker import handle_welcome_command
    env = make_env()
    body = {"command": "/welcome"}
    result = await handle_welcome_command(env, body)
    assert result["ok"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_welcome_command_with_response_url():
    """Test /welcome command uses response_url when provided."""
    from src.worker import handle_welcome_command
    env = make_env()
    body = {
        "command": "/welcome",
        "user_id": "U123456",
        "response_url": "https://hooks.slack.com/commands/test"
    }
    with patch("src.worker.send_to_response_url", new_callable=AsyncMock) as mock_response_url, \
         patch("src.worker.increment_commands", new_callable=AsyncMock):
        mock_response_url.return_value = None
        result = await handle_welcome_command(env, body)
        assert result["ok"] is True
        mock_response_url.assert_called_once_with(
            "https://hooks.slack.com/commands/test", "U123456"
        )


@pytest.mark.asyncio
async def test_welcome_command_without_response_url():
    """Test /welcome command falls back to DM when response_url is missing."""
    from src.worker import handle_welcome_command
    env = make_env()
    body = {"command": "/welcome", "user_id": "U123456"}
    with patch("src.worker.send_welcome_dm", new_callable=AsyncMock) as mock_dm, \
         patch("src.worker.increment_commands", new_callable=AsyncMock):
        mock_dm.return_value = {"ok": True}
        result = await handle_welcome_command(env, body)
        assert result["ok"] is True
        mock_dm.assert_called_once_with(env, "U123456")


@pytest.mark.asyncio
async def test_welcome_command_slack_api_error():
    """Test /welcome command handles Slack API errors gracefully."""
    from src.worker import handle_welcome_command
    env = make_env()
    body = {"command": "/welcome", "user_id": "U123456"}
    with patch("src.worker.send_welcome_dm", new_callable=AsyncMock) as mock_dm, \
         patch("src.worker.increment_commands", new_callable=AsyncMock):
        mock_dm.return_value = {"ok": False, "error": "slack_api_error"}
        result = await handle_welcome_command(env, body)
        assert result["ok"] is False