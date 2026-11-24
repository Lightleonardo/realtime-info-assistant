import math
import os

import httpx
from langchain_core.tools import tool

# How long we wait for an API to answer before giving up.
TIMEOUT_SECONDS = 10.0

# Tests can swap this out for a fake transport so we never hit the real network.
_transport = None


class ApiProblem(Exception):
    """An error whose message is safe to show the user (no URLs, no keys)."""


def _get(url, params=None):
    """Make an HTTP GET request and return (status_code, json_body).

    We wrap everything in try/except so that network problems, timeouts, and
    bad JSON all turn into a friendly ApiProblem instead of a scary traceback.
    The `from None` part drops the original exception so we don't accidentally
    leak a URL (which might contain an API key) into the error message.
    """
    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS, transport=_transport) as client:
            response = client.get(url, params=params)
    except httpx.TimeoutException:
        # Timeouts are a kind of request error, so we catch them first so the
        # right message shows up.
        raise ApiProblem("The service took too long to respond. Please try again.") from None
    except httpx.RequestError:
        raise ApiProblem("Could not reach the service. Check your connection and try again.") from None

    # The currency API sometimes tells us about problems via HTTP status (like
    # 429 for rate limiting), so we check that before reading the body.
    if response.status_code == 429:
        raise ApiProblem("The service is rate-limiting requests. Please wait and try again.")

    try:
        return response.status_code, response.json()
    except ValueError:
        raise ApiProblem("The service returned data I could not read.") from None


@tool
def get_current_weather(city: str) -> str:
    """Get the current weather for a city.

    Use this when the user asks about weather or temperature in a place.
    Pass in a city name like "Lagos". You'll get back a readable sentence with
    the place, temperature, wind, and units. If the city isn't found or the
    weather service is down, you get an error message instead.
    """
    # Don't waste a request on an empty city name.
    if not city or not city.strip():
        return "Please provide a city name."

    city = city.strip()

    # Turn the city name into latitude/longitude.
    try:
        status, data = _get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
        )
    except ApiProblem as exc:
        return str(exc)

    results = data.get("results")
    if not results:
        return f"couldn't find a place called {city}."

    place = results[0]
    latitude = place["latitude"]
    longitude = place["longitude"]
    place_name = place["name"]
    country = place.get("country", "")

    # Fetch the current forecast for those coordinates.
    try:
        status, data = _get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,wind_speed_10m",
                "timezone": "auto",
            },
        )
    except ApiProblem as exc:
        return str(exc)

    # A 5xx or missing `current` means the weather service isn't usable.
    if status >= 500 or "current" not in data:
        return "The weather service is unavailable right now. Please try again later."

    current = data["current"]
    temperature = current["temperature_2m"]
    wind_speed = current["wind_speed_10m"]
    temp_unit = data["current_units"]["temperature_2m"]
    wind_unit = data["current_units"]["wind_speed_10m"]

    return (
        f"It is {temperature}{temp_unit} with winds of {wind_speed}{wind_unit} "
        f"in {place_name}, {country}."
    )


@tool
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert an amount from one currency to another.

    Use this when the user asks to convert money between currencies. Pass in
    the amount and two three-letter currency codes (like USD and NGN). You get
    back a sentence with the amount, both codes, the rate, and when the rate
    was last updated. Bad inputs, a missing key, or a failed conversion all
    give you an error message instead.
    """
    # Make sure the currency codes look right before we ever call the API.
    if not (isinstance(from_currency, str) and len(from_currency) == 3 and from_currency.isalpha()):
        return (
            f"'{from_currency}' is not a valid currency code. "
            "Use a three-letter code such as USD."
        )
    if not (isinstance(to_currency, str) and len(to_currency) == 3 and to_currency.isalpha()):
        return (
            f"'{to_currency}' is not a valid currency code. "
            "Use a three-letter code such as NGN."
        )

    # The amount has to be a real, positive number.
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        return "Amount must be a number."
    if not math.isfinite(amount) or amount <= 0:
        return "Amount must be a positive number."

    # We need the API key from the environment before we can call the service.
    api_key = os.environ.get("EXCHANGERATE_API_KEY")
    if not api_key:
        return (
            "Currency conversion is not configured: "
            "the ExchangeRate API key is missing."
        )

    # Call the ExchangeRate API. Any network trouble gets caught by _get and
    # turned into a friendly message.
    try:
        status, data = _get(
            f"https://v6.exchangerate-api.com/v6/{api_key}/pair/"
            f"{from_currency}/{to_currency}/{amount}"
        )
    except ApiProblem as exc:
        return str(exc)

    # The API sometimes reports errors in the JSON body even when the HTTP
    # status looks fine, so we check `result == "error"` here.
    if data.get("result") == "error":
        error_type = data.get("error-type", "unknown")
        friendly = {
            "bad-key": "The ExchangeRate API key is invalid.",
            "invalid-key": "The ExchangeRate API key is invalid.",
            "missing-key": "The ExchangeRate API key is missing.",
            "inactive-key": "The ExchangeRate API key is inactive.",
            "quota-reached": "The ExchangeRate API quota has been reached.",
            "rate-limit-reached": "The ExchangeRate API is rate-limiting requests.",
        }
        return friendly.get(
            error_type, f"Currency conversion failed ({error_type})."
        )

    rate = data["conversion_rate"]
    result = data["conversion_result"]
    updated = data.get("time_last_update_utc", "recently")

    return (
        f"{amount} {from_currency} = {result} {to_currency} "
        f"at a rate of {rate} (last updated {updated})."
    )


TOOLS = [get_current_weather, convert_currency]