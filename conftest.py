"""Pytest configuration shared by all the tests.

The tests never call the real APIs. Instead, we swap in a fake transport so
every HTTP call is predictable and works without a network connection.
"""

import httpx
import tools


class MockTransport:
    """Puts a fake transport in place of tools._transport, then puts it back."""

    def __init__(self, handler):
        self.handler = handler
        self.original = None

    def __enter__(self):
        self.original = tools._transport
        tools._transport = httpx.MockTransport(self.handler)
        return self

    def __exit__(self, *exc_info):
        tools._transport = self.original


try:
    import pytest

    @pytest.fixture
    def mock_transport():
        """Give each test a fake transport it can use and throw away."""

        return MockTransport

except ImportError:
    # If pytest isn't installed, this file still imports fine.
    pass
