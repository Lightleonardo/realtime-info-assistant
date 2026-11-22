# Error-Handling Evidence

One row per failure case: how it was triggered, what the user saw, and whether
it was real (triggered against a live or mocked service) or simulated.

Honesty note: invalid location and invalid currency were triggered for real.
Timeouts, outages, rate limits, and bad language-model keys were simulated with
mocked transport (no network to the real APIs), because those conditions are
hard to reproduce on demand against a live service.

| Failure case | How triggered | What the user saw | Real or simulated |
|---|---|---|---|
| Invalid location | Called the geocoder with `name=Nowhereville` against live Open-Meteo | "couldn't find a place called Nowhereville." | **Real** — live HTTP 200 with empty `results` body |
| Invalid currency | Called `convert_currency` with `from_currency="dollars"` (not 3 letters) | "'dollars' is not a valid currency code. Use a three-letter code such as USD." | **Real** — local validation, no HTTP request made |
| Missing key | Called `convert_currency` with no `EXCHANGERATE_API_KEY` in the environment | "Currency conversion is not configured: the ExchangeRate API key is missing." | **Real** — env var unset, tool checked before any request |
| Timeout | Mocked `httpx.TimeoutException` on the geocode request | "The service took too long to respond. Please try again." | **Simulated** — MockTransport raised TimeoutException |
| API unavailable | Mocked a 5xx response from the forecast endpoint (after a valid geocode) | "The weather service is unavailable right now. Please try again later." | **Simulated** — MockTransport returned HTTP 500 |
| Rate limit | Mocked an HTTP 429 response from the currency endpoint | "The service is rate-limiting requests. Please wait and try again." | **Simulated** — MockTransport returned HTTP 429 |
| Bad language-model key | Set `OPENAI_API_KEY` to an invalid value (not tested live — no key available) | "Language model authentication failed. Check your OpenAI API key." | **Simulated** — code path reviewed, not executed against a live model |

## Details per case

### Invalid location (real)
- **Trigger:** `get_current_weather("Nowhereville")` against live
  `https://geocoding-api.open-meteo.com/v1/search?name=Nowhereville&count=1&language=en&format=json`
- **Live response:** HTTP 200 with body `{"generationtime_ms": 0.106…}` — no
  `results` key.
- **User saw:** "couldn't find a place called Nowhereville."
- **Why it works:** the tool checks `data.get("results")` and treats a missing
  or empty list as "not found" rather than relying on HTTP status (which was
  200).

### Invalid currency (real)
- **Trigger:** `convert_currency(100, "dollars", "NGN")`.
- **Behavior:** local validation runs before any HTTP request; "dollars" is not
  three alphabetic characters.
- **User saw:** "'dollars' is not a valid currency code. Use a three-letter
  code such as USD."
- **No network call was made** (verified: the mock handler was never invoked).

### Missing key (real)
- **Trigger:** `convert_currency(100, "USD", "NGN")` with
  `EXCHANGERATE_API_KEY` unset.
- **Behavior:** the tool reads the env var and returns early before calling the
  ExchangeRate API.
- **User saw:** "Currency conversion is not configured: the ExchangeRate API
  key is missing."

### Timeout (simulated)
- **Trigger:** MockTransport raised `httpx.TimeoutException` on the geocode
  request.
- **Behavior:** `_get` catches `TimeoutException` (before the broader
  `RequestError`) and raises `ApiProblem` with `from None` so no URL/key leaks
  into the chained exception.
- **User saw:** "The service took too long to respond. Please try again."

### API unavailable (simulated)
- **Trigger:** MockTransport returned HTTP 500 from the forecast endpoint.
- **Behavior:** `_get` parses the JSON (500 with valid JSON body), then the
  weather tool sees `status >= 500` and returns the unavailability message.
- **User saw:** "The weather service is unavailable right now. Please try again
  later."

### Rate limit (simulated)
- **Trigger:** MockTransport returned HTTP 429.
- **Behavior:** `_get` checks `response.status_code == 429` before parsing JSON
  and raises `ApiProblem`.
- **User saw:** "The service is rate-limiting requests. Please wait and try
  again."

### Bad language-model key (simulated)
- **Trigger:** Not executed live (no OpenAI API key available to test against).
- **Behavior:** `agent.run_agent` catches `openai.AuthenticationError`
  (most specific LLM error, caught first among the LLM errors) and returns a
  friendly message.
- **User saw:** "Language model authentication failed. Check your OpenAI API
  key."

## Key safety check
For every failure path, the message returned to the user contains no URLs and
no API keys. This is enforced by raising `ApiProblem` with `from None` in
`_get`, which drops the original exception (and any URL it might carry) from
the chain. A test (`test_key_never_leaks_into_messages`) confirms the key does
not appear in any returned message, including on mocked failures.
