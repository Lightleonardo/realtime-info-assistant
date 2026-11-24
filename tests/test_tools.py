"""Tests for tools.py.

None of these tests touch the real network. Every HTTP call goes through a fake
transport, so the tests are fast and work offline.
"""

import os
import httpx

import tools

API_KEY = "test-key-123"


def _install(handler):
    """Swap in a fake transport and return a function to put the real one back."""
    original = tools._transport
    tools._transport = httpx.MockTransport(handler)

    def restore():
        tools._transport = original

    return restore


def _uninstall(restore):
    restore()

def test_weather_success():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        if "search" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "name": "Lagos",
                            "latitude": 6.45,
                            "longitude": 3.4,
                            "country": "Nigeria",
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "current": {
                    "temperature_2m": 30.5,
                    "wind_speed_10m": 12.6,
                },
                "current_units": {
                    "temperature_2m": "°C",
                    "wind_speed_10m": "km/h",
                },
            },
        )

    restore = _install(handler)
    try:
        result = tools.get_current_weather.func("Lagos")
    finally:
        _uninstall(restore)

    assert "30.5" in result
    assert "12.6" in result
    assert "Lagos" in result
    assert "/search" in calls[0]
    assert "/forecast" in calls[1]


# ---------------------------------------------------------------------------
# Weather: unknown city
# ---------------------------------------------------------------------------

def test_weather_unknown_city():
    restore = _install(lambda request: httpx.Response(200, json={"generationtime_ms": 0.1}))
    try:
        result = tools.get_current_weather.func("Nowhereville")
    finally:
        _uninstall(restore)
    assert "couldn't find a place called Nowhereville" in result


# ---------------------------------------------------------------------------
# Weather: empty city (no HTTP request made)
# ---------------------------------------------------------------------------

def test_weather_empty_city_makes_no_request():
    called = []

    def handler(request):
        called.append(True)
        raise AssertionError("no request should be made for an empty city")

    restore = _install(handler)
    try:
        result = tools.get_current_weather.func("")
    finally:
        _uninstall(restore)
    assert called == []
    assert "Please provide a city name" in result


def test_weather_whitespace_city_makes_no_request():
    called = []

    def handler(request):
        called.append(True)
        raise AssertionError("no request should be made for a blank city")

    restore = _install(handler)
    try:
        result = tools.get_current_weather.func("   ")
    finally:
        _uninstall(restore)
    assert called == []
    assert "Please provide a city name" in result



# ---------------------------------------------------------------------------
# Weather: timeout
# ---------------------------------------------------------------------------

def test_weather_timeout():
    restore = _install(
        lambda request: (_ for _ in ()).throw(httpx.TimeoutException("read timed out"))
    )
    try:
        result = tools.get_current_weather.func("Lagos")
    finally:
        _uninstall(restore)
    assert "took too long" in result


# ---------------------------------------------------------------------------
# Weather: unreachable network
# ---------------------------------------------------------------------------

def test_weather_unreachable_network():
    restore = _install(
        lambda request: (_ for _ in ()).throw(httpx.ConnectError("fail"))
    )
    try:
        result = tools.get_current_weather.func("Lagos")
    finally:
        _uninstall(restore)
    assert "Could not reach the service" in result


# ---------------------------------------------------------------------------
# Weather: 5xx response
# ---------------------------------------------------------------------------

def test_weather_5xx():
    def handler(request):
        if "search" in str(request.url):
            return httpx.Response(
                200,
                json={"results": [{"name": "Lagos", "latitude": 6.45, "longitude": 3.4, "country": "Nigeria"}]},
            )
        return httpx.Response(500, json={"error": "server error"})

    restore = _install(handler)
    try:
        result = tools.get_current_weather.func("Lagos")
    finally:
        _uninstall(restore)
    assert "service is unavailable" in result.lower()


# ---------------------------------------------------------------------------
# Weather: body that isn't JSON
# ---------------------------------------------------------------------------

def test_weather_non_json_body():
    restore = _install(lambda request: httpx.Response(200, content="not json"))
    try:
        result = tools.get_current_weather.func("Lagos")
    finally:
        _uninstall(restore)
    assert "could not read" in result.lower()




# ---------------------------------------------------------------------------
# Currency: success
# ---------------------------------------------------------------------------

def test_currency_success():
    os.environ["EXCHANGERATE_API_KEY"] = API_KEY
    try:
        restore = _install(
            lambda request: httpx.Response(
                200,
                json={
                    "result": "success",
                    "conversion_rate": 1500.0,
                    "conversion_result": 150000.0,
                    "time_last_update_utc": "2026-11-22",
                },
            )
        )
        try:
            result = tools.convert_currency.func(100, "USD", "NGN")
        finally:
            _uninstall(restore)
        assert "100 USD = 150000.0 NGN" in result
        assert "1500.0" in result
        assert "2026-11-22" in result
    finally:
        os.environ.pop("EXCHANGERATE_API_KEY", None)


# ---------------------------------------------------------------------------
# Currency: bad code validation (no request)
# ---------------------------------------------------------------------------

def test_currency_bad_from_code():
    called = []

    def handler(request):
        called.append(True)
        raise AssertionError("no request should be made for a bad code")

    restore = _install(handler)
    try:
        result = tools.convert_currency.func(100, "dollars", "NGN")
    finally:
        _uninstall(restore)
    assert called == []
    assert "not a valid currency code" in result.lower()


def test_currency_bad_to_code():
    called = []

    def handler(request):
        called.append(True)
        raise AssertionError("no request should be made for a bad code")

    restore = _install(handler)
    try:
        result = tools.convert_currency.func(100, "USD", "xy")
    finally:
        _uninstall(restore)
    assert called == []
    assert "not a valid currency code" in result.lower()


# ---------------------------------------------------------------------------
# Currency: invalid amount (no request)
# ---------------------------------------------------------------------------

def test_currency_negative_amount():
    called = []

    def handler(request):
        called.append(True)
        raise AssertionError("no request should be made for a negative amount")

    restore = _install(handler)
    try:
        result = tools.convert_currency.func(-5, "USD", "NGN")
    finally:
        _uninstall(restore)
    assert called == []
    assert "positive" in result.lower()


def test_currency_zero_amount():
    called = []

    def handler(request):
        called.append(True)
        raise AssertionError("no request should be made for zero amount")

    restore = _install(handler)
    try:
        result = tools.convert_currency.func(0, "USD", "NGN")
    finally:
        _uninstall(restore)
    assert called == []
    assert "positive" in result.lower()


# ---------------------------------------------------------------------------
# Currency: missing key
# ---------------------------------------------------------------------------

def test_currency_missing_key():
    os.environ.pop("EXCHANGERATE_API_KEY", None)
    try:
        result = tools.convert_currency.func(100, "USD", "NGN")
    finally:
        os.environ.pop("EXCHANGERATE_API_KEY", None)
    assert "missing" in result.lower()


# ---------------------------------------------------------------------------
# Currency: documented error types
# ---------------------------------------------------------------------------

def test_currency_error_types():
    error_cases = [
        ("bad-key", "invalid"),
        ("invalid-key", "invalid"),
        ("missing-key", "missing"),
        ("inactive-key", "inactive"),
        ("quota-reached", "quota"),
        ("rate-limit-reached", "rate-limit"),
    ]
    for error_type, expected_word in error_cases:
        os.environ["EXCHANGERATE_API_KEY"] = API_KEY
        try:
            restore = _install(
                lambda request: httpx.Response(
                    200, json={"result": "error", "error-type": error_type}
                )
            )
            try:
                result = tools.convert_currency.func(100, "USD", "NGN")
            finally:
                _uninstall(restore)
            assert expected_word in result.lower(), f"{error_type}: {result!r}"
        finally:
            os.environ.pop("EXCHANGERATE_API_KEY", None)


# ---------------------------------------------------------------------------
# Currency: unknown error type (catch-all)
# ---------------------------------------------------------------------------

def test_currency_unknown_error_type():
    os.environ["EXCHANGERATE_API_KEY"] = API_KEY
    try:
        restore = _install(
            lambda request: httpx.Response(
                200, json={"result": "error", "error-type": "weird-thing"}
            )
        )
        try:
            result = tools.convert_currency.func(100, "USD", "NGN")
        finally:
            _uninstall(restore)
        assert "failed" in result.lower() or "weird-thing" in result
    finally:
        os.environ.pop("EXCHANGERATE_API_KEY", None)


# ---------------------------------------------------------------------------
# Currency: 429 rate limit
# ---------------------------------------------------------------------------

def test_currency_429():
    os.environ["EXCHANGERATE_API_KEY"] = API_KEY
    try:
        restore = _install(lambda request: httpx.Response(429, text="too many"))
        try:
            result = tools.convert_currency.func(100, "USD", "NGN")
        finally:
            _uninstall(restore)
        assert "rate-limiting" in result.lower() or "rate limit" in result.lower()
    finally:
        os.environ.pop("EXCHANGERATE_API_KEY", None)


# ---------------------------------------------------------------------------
# Key never appears in returned messages
# ---------------------------------------------------------------------------

def test_key_never_leaks_into_messages():
    """Even when a mocked failure would include the full URL, the key must not
    show up in any user-visible message.
    """
    os.environ["EXCHANGERATE_API_KEY"] = API_KEY
    try:
        restore = _install(lambda request: httpx.Response(429, text="too many"))
        try:
            result = tools.convert_currency.func(100, "USD", "NGN")
        finally:
            _uninstall(restore)
        assert API_KEY not in result
        assert "exchangerate-api.com" not in result.lower()
    finally:
        os.environ.pop("EXCHANGERATE_API_KEY", None)


# ---------------------------------------------------------------------------
# Tool descriptions are non-trivial
# ---------------------------------------------------------------------------

def test_tool_descriptions_non_trivial():
    for tool in tools.TOOLS:
        desc = tool.description
        assert desc is not None
        assert len(desc.strip()) > 20, f"{tool.name} description too short: {desc!r}"