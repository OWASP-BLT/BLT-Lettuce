import asyncio
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


def load_worker_module():
    module_path = Path(__file__).resolve().parents[1] / "src" / "worker.py"
    spec = importlib.util.spec_from_file_location("blt_lettuce_worker", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load worker module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WORKER = load_worker_module()


class FakeResponse:
    def __init__(self, status=200, payload=None, json_error=None):
        self.status = status
        self.ok = 200 <= status < 300
        self._payload = payload if payload is not None else {}
        self._json_error = json_error

    async def json(self):
        if self._json_error is not None:
            raise self._json_error
        return self._payload


class BltApiClientTests(unittest.IsolatedAsyncioTestCase):
    def test_build_blt_api_url_adds_default_prefix(self):
        url = WORKER.build_blt_api_url(
            "https://blt.example.com",
            "projects/least-members-channel/",
        )
        self.assertEqual(
            url, "https://blt.example.com/api/v1/projects/least-members-channel/"
        )

    def test_build_blt_api_url_does_not_duplicate_prefix(self):
        url = WORKER.build_blt_api_url(
            "https://blt.example.com",
            "api/v1/projects/least-members-channel/",
        )
        self.assertEqual(
            url, "https://blt.example.com/api/v1/projects/least-members-channel/"
        )

    def test_build_blt_auth_header_defaults_to_token_scheme(self):
        header = WORKER.build_blt_auth_header("abc123")
        self.assertEqual(header, {"Authorization": "Token abc123"})

    def test_build_blt_auth_header_preserves_explicit_scheme(self):
        header = WORKER.build_blt_auth_header("Bearer abc123")
        self.assertEqual(header, {"Authorization": "Bearer abc123"})

    async def test_blt_get_returns_json_on_success(self):
        env = SimpleNamespace(
            BLT_API_BASE_URL="https://blt.example.com", BLT_API_TOKEN="abc123"
        )
        fake_fetch = AsyncMock(
            return_value=FakeResponse(payload={"slack_channel": "project-api"})
        )

        with patch.object(WORKER, "fetch", fake_fetch):
            result = await WORKER.blt_get(
                env,
                "projects/least-members-channel/",
                timeout_seconds=5,
            )

        self.assertEqual(result, {"slack_channel": "project-api"})
        args, _kwargs = fake_fetch.await_args
        self.assertEqual(
            args[0], "https://blt.example.com/api/v1/projects/least-members-channel/"
        )
        self.assertEqual(args[1]["method"], "GET")
        self.assertEqual(args[1]["headers"]["Authorization"], "Token abc123")

    async def test_blt_get_returns_none_for_non_200(self):
        env = SimpleNamespace(
            BLT_API_BASE_URL="https://blt.example.com", BLT_API_TOKEN="abc123"
        )
        fake_fetch = AsyncMock(
            return_value=FakeResponse(status=404, payload={"detail": "not found"})
        )

        with patch.object(WORKER, "fetch", fake_fetch):
            result = await WORKER.blt_get(
                env,
                "projects/least-members-channel/",
                timeout_seconds=5,
            )

        self.assertIsNone(result)

    async def test_blt_get_returns_none_for_invalid_json(self):
        env = SimpleNamespace(
            BLT_API_BASE_URL="https://blt.example.com", BLT_API_TOKEN="abc123"
        )
        fake_fetch = AsyncMock(
            return_value=FakeResponse(status=200, json_error=ValueError("bad json"))
        )

        with patch.object(WORKER, "fetch", fake_fetch):
            result = await WORKER.blt_get(
                env,
                "projects/least-members-channel/",
                timeout_seconds=5,
            )

        self.assertIsNone(result)

    async def test_blt_get_returns_none_on_timeout(self):
        env = SimpleNamespace(
            BLT_API_BASE_URL="https://blt.example.com", BLT_API_TOKEN="abc123"
        )

        async def slow_fetch(*_args, **_kwargs):
            await asyncio.sleep(0.05)
            return FakeResponse(payload={"slack_channel": "project-api"})

        with patch.object(WORKER, "fetch", AsyncMock(side_effect=slow_fetch)):
            result = await WORKER.blt_get(
                env,
                "projects/least-members-channel/",
                timeout_seconds=0.001,
            )

        self.assertIsNone(result)

    async def test_get_least_members_channel_returns_none_when_field_missing(self):
        env = SimpleNamespace(
            BLT_API_BASE_URL="https://blt.example.com", BLT_API_TOKEN="abc123"
        )

        with patch.object(WORKER, "blt_get", AsyncMock(return_value={"project": "x"})):
            result = await WORKER.get_least_members_channel(env)

        self.assertIsNone(result)

    async def test_contribute_sends_message_to_contribute_channel_when_set(self):
        """Test that contribute message handler sends to configured contribute channel."""
        env = SimpleNamespace(
            CONTRIBUTE_ID="C123456",
            SLACK_TOKEN="xoxb-token",
        )
        event = {
            "type": "message",
            "text": "I want to contribute to this project",
            "user": "U789",
            "channel": "C999",
            "channel_type": "channel",
            "subtype": None,
        }

        mock_bot_id = AsyncMock(return_value="U_BOT")
        mock_send_message = AsyncMock(return_value={"ok": True})

        with patch.object(WORKER, "get_bot_user_id", mock_bot_id):
            with patch.object(WORKER, "send_slack_message", mock_send_message):
                result = await WORKER.handle_message_event(env, event)

        # Verify the handler recognized the contribute keyword
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "contribute_response")

        # Verify message was sent to the contribute channel with mention of user
        mock_send_message.assert_called_once()
        call_args = mock_send_message.call_args
        self.assertEqual(call_args[0][1], "C123456")  # channel argument
        self.assertIn("<@U789>", call_args[0][2])  # message text should mention user
        self.assertIn("contributing", call_args[0][2].lower())

    async def test_contribute_handler_with_no_contribute_id_configured(self):
        """Test fallback behavior when CONTRIBUTE_ID is not configured."""
        env = SimpleNamespace(
            SLACK_TOKEN="xoxb-token",
            # CONTRIBUTE_ID not set, should use default (None)
        )
        event = {
            "type": "message",
            "text": "how can I contribute?",
            "user": "U789",
            "channel": "C999",
            "channel_type": "channel",
            "subtype": None,
        }

        mock_bot_id = AsyncMock(return_value="U_BOT")
        mock_send_message = AsyncMock(return_value={"ok": False})

        with patch.object(WORKER, "get_bot_user_id", mock_bot_id):
            with patch.object(WORKER, "send_slack_message", mock_send_message):
                result = await WORKER.handle_message_event(env, event)

        # Verify the handler recognized the contribute keyword
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "contribute_response")

        # When contribute_id is None, the message should be sent to None
        # The actual channeling behavior depends on send_slack_message implementation
        mock_send_message.assert_called_once()
        call_args = mock_send_message.call_args
        self.assertIsNone(call_args[0][1])  # channel should be None

    async def test_contribute_ignores_message_without_contribute_keyword(self):
        """Test that non-contribute messages are not handled by contribute logic."""
        env = SimpleNamespace(
            CONTRIBUTE_ID="C123456",
            SLACK_TOKEN="xoxb-token",
        )
        event = {
            "type": "message",
            "text": "This is just a regular message",
            "user": "U789",
            "channel": "C999",
            "channel_type": "channel",
            "subtype": None,
        }

        mock_bot_id = AsyncMock(return_value="U_BOT")
        mock_send_message = AsyncMock(return_value={"ok": True})

        with patch.object(WORKER, "get_bot_user_id", mock_bot_id):
            with patch.object(WORKER, "send_slack_message", mock_send_message):
                result = await WORKER.handle_message_event(env, event)

        # send_slack_message should not be called for non-contribute messages
        # (unless it's for other message handling logic)
        # The result action should NOT be "contribute_response"
        if "action" in result:
            self.assertNotEqual(result.get("action"), "contribute_response")
