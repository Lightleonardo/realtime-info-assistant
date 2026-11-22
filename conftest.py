"""Pytest configuration and shared fixtures for the realtime-info-assistant tests.

Tests never hit the real APIs.  The ``mock_transport`` fixture replaces
``tools._transport`` with an ``httpx.MockTransport`` so every HTTP call made by
the tools is deterministic and offline.
"""

import httpx
import tools


def _response(status=200, json=None, content=None, text=None):
    return httpx.Response(status, json=json, content=content, text=text)


class MockTransport:
    """Context-managed replacement for ``tools._transport``."""

    def __init__(self, handler):
        self.handler = handler
        self.original = None

    def __enter__(self):
        self.original = tools._transport
        tools._transport = httpx.MockTransport(self.handler)
        return self

    def __exit__(self, *exc_info):
        tools._transport = self.original


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

try:
    import pytest  # noqa: F401  (only needed when running under pytest)

    @pytest.fixture
    def mock_transport():
        """Yield a context manager that installs a MockTransport for the test.

        Usage::

            def test_something(mock_transport):
                with mock_transport(lambda request: httpx.Response(200, json={...})):
                    ...

        The transport is restored to its previous value afterwards.
        """
        return MockTransport

except ImportError:
    # pytest not installed; the module still imports cleanly.
    pass
