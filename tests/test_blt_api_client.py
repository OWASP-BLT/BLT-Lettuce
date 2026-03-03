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
