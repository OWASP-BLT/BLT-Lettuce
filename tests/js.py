"""
Mock/stub module for Cloudflare Worker 'js' runtime imports.

This module provides mock implementations of Cloudflare runtime objects
that are normally available in the Cloudflare Workers environment but are
not available during local testing.
"""


class Headers(dict):
    """Mock implementation of Cloudflare Headers object."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Response:
    """Mock implementation of Cloudflare Response object."""

    def __init__(self, body=None, status=200, headers=None):
        self.body = body
        self.status = status
        self.headers = Headers(headers or {})
        self.ok = 200 <= status < 300

    async def text(self):
        return self.body if isinstance(self.body, str) else ""

    async def json(self):
        import json
        return json.loads(self.body) if isinstance(self.body, str) else {}


async def fetch(url, *args, **kwargs):
    """Mock implementation of fetch function."""
    # Return a basic mock response
    return Response(status=200)


class Object:
    """Mock implementation of JavaScript Object."""

    @staticmethod
    def keys(obj):
        if isinstance(obj, dict):
            return list(obj.keys())
        return []

    @staticmethod
    def values(obj):
        if isinstance(obj, dict):
            return list(obj.values())
        return []
