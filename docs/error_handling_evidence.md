# Error-Handling Evidence

One row per failure case: how it was triggered, what the user saw, and whether
it was real (triggered against a live or mocked service) or simulated.

Honesty note: invalid location, invalid currency, wrong currency key,
unsupported currency code, and both missing-key checks were triggered for real
(the currency and geocoder cases against the live APIs; the missing-key cases as
local/startup checks). Timeouts, outages (5xx), and malformed responses were
simulated with mocked transport, because those conditions are hard to reproduce
on demand against a live service. The bad language-model key was triggered for
real by running the assistant with an invalid key.

| Failure case | How triggered | What the user saw | Real or simulated |
|---|---|---|---|
| Invalid location | Called the geocoder with `name=Nowhereville` against live Open-Meteo | "couldn't find a place called Nowhereville." | **Real** — live HTTP 200 with empty `results` body |
| Invalid currency | Called `convert_currency` with `from_currency="dollars"` (not 3 letters) | "'dollars' is not a valid currency code. Use a three-letter code such as USD." | **Real** — local validation, no HTTP request made |
| Missing key (currency) | Called `convert_currency` with no `EXCHANGERATE_API_KEY` in the environment | "Currency conversion is not configured: the ExchangeRate API key is missing." | **Real** — env var unset, tool checked before any request |
| Wrong currency key | Called `convert_currency` with an invalid `EXCHANGERATE_API_KEY` against live ExchangeRate-API | "The ExchangeRate API key is invalid." | **Real** — live HTTP 403 with `error-type: "invalid-key"` |
| Missing key (startup) | Ran `python agent.py` with no `OPENAI_API_KEY` set | "Error: OPENAI_API_KEY is not set. Copy .env.example to .env and fill it in." | **Real** — env var checked at startup |
| Bad language-model key | Ran the agent with an invalid `OPENAI_API_KEY` | "Language model authentication failed. Check your OpenAI API key." | **Real** — executed against OpenRouter with an invalid key |
| Timeout | Mocked `httpx.TimeoutException` on the geocode request | "The service took too long to respond. Please try again." | **Simulated** — MockTransport raised TimeoutException |
| API unavailable (geocoder 5xx) | Mocked HTTP 503 from the geocoding endpoint | "The weather service is unavailable right now. Please try again later." | **Simulated** — MockTransport returned HTTP 503 |
| API unavailable (currency 5xx) | Mocked HTTP 503 from the currency endpoint | "The currency service is unavailable right now. Please try again later." | **Simulated** — MockTransport returned HTTP 503 |
| Malformed 200 response | Mocked HTTP 200 with missing `conversion_rate` / `conversion_result` | "The currency service returned an unexpected response." | **Simulated** — MockTransport returned 200 with incomplete JSON |
| Unsupported currency code | Called `convert_currency` with `to_currency="XYZ"` against live ExchangeRate-API | "One of those currency codes isn't supported." | **Real** — live HTTP 404 with `error-type: "unsupported-code"` |
| Rate limit | Mocked an HTTP 429 response from the currency endpoint | "The service is rate-limiting requests. Please wait and try again." | **Simulated** — MockTransport returned HTTP 429 |

## Details per case

### Invalid location (real)
- **Trigger:** `get_current_weather("Nowhereville")` against live
  `https://geocoding-api.open-meteo.com/v1/search?name=Nowhereville&count=1&language=en&format=json`.
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

### Missing key — currency (real)
- **Trigger:** `convert_currency(100, "USD", "NGN")` with
  `EXCHANGERATE_API_KEY` unset.
- **Behavior:** the tool reads the env var and returns early before calling the
  ExchangeRate API.
- **User saw:** "Currency conversion is not configured: the ExchangeRate API
  key is missing."

### Wrong currency key (real)
- **Trigger:** `convert_currency(100, "USD", "NGN")` with an invalid
  `EXCHANGERATE_API_KEY` against the live ExchangeRate-API (raw response in
  `docs/api_exploration.md`).
- **Live response:** HTTP 403 with body
  `{"result": "error", "error-type": "invalid-key", …}`.
- **User saw:** "The ExchangeRate API key is invalid."
- **Why it works:** the tool reads `error-type` from the JSON body and maps
  `invalid-key` to a friendly message.

### Missing key — startup (real)
- **Trigger:** `python agent.py` with `OPENAI_API_KEY` unset.
- **Behavior:** `main()` checks the env var before building the LLM and exits
  with a friendly message.
- **User saw:** "Error: OPENAI_API_KEY is not set. Copy .env.example to .env
  and fill it in."

### Bad language-model key (real)
- **Trigger:** Ran `python agent.py` with `OPENAI_API_KEY` set to an invalid
  value (not a real OpenRouter key).
- **Behavior:** `agent.run_agent` catches `openai.AuthenticationError` (the most
  specific LLM error, caught first) and returns a friendly message.
- **User saw:** "Language model authentication failed. Check your OpenAI API
  key."
- **Note:** the agent never got as far as calling a tool — the LLM rejected the
  key before generating any tool calls.

### Timeout (simulated)
- **Trigger:** MockTransport raised `httpx.TimeoutException` on the geocode
  request.
- **Behavior:** `_get` catches `TimeoutException` (before the broader
  `RequestError`) and raises `ApiProblem` with `from None` so no URL/key leaks
  into the chained exception.
- **User saw:** "The service took too long to respond. Please try again."

### API unavailable — geocoder 5xx (simulated)
- **Trigger:** MockTransport returned HTTP 503 from the geocoding endpoint.
- **Behavior:** `get_current_weather` checks `status >= 500` on the geocode call
  and returns the unavailability message.
- **User saw:** "The weather service is unavailable right now. Please try again
  later."
- **Why it matters:** without this check, a 5xx outage would be reported as
  "couldn't find a place called X" — a bad city, not a bad service.

### API unavailable — currency 5xx (simulated)
- **Trigger:** MockTransport returned HTTP 503 from the currency endpoint.
- **Behavior:** after the `result == "error"` branch, `convert_currency` checks
  `status >= 500 or data.get("result") != "success"` and returns the
  unavailability message.
- **User saw:** "The currency service is unavailable right now. Please try again
  later."
- **Why it matters:** without this check, a 5xx would propagate as an uncaught
  exception through LangChain's tool node.

### Malformed 200 response (simulated)
- **Trigger:** MockTransport returned HTTP 200 with `{"result": "success"}` —
  missing `conversion_rate` and `conversion_result`.
- **Behavior:** the tool checks `data.get("conversion_rate")` and
  `data.get("conversion_result")`; if either is `None`, it returns the
  unexpected-response message.
- **User saw:** "The currency service returned an unexpected response."
- **Why it matters:** without the `.get()` guards, a missing field would raise an
  uncaught `KeyError` inside LangChain's tool node.

### Unsupported currency code (real)
- **Trigger:** `convert_currency(100, "USD", "XYZ")` against the live
  ExchangeRate-API.
- **Live response:** HTTP 404 with body
  `{"result": "error", "error-type": "unsupported-code", …}`.
- **User saw:** "One of those currency codes isn't supported."
- **Why it works:** the tool maps `unsupported-code` to a friendly message in
  its error-type lookup table.

### Rate limit (simulated)
- **Trigger:** MockTransport returned HTTP 429.
- **Behavior:** `_get` checks `response.status_code == 429` before parsing JSON
  and raises `ApiProblem`.
- **User saw:** "The service is rate-limiting requests. Please wait and try
  again."

## Key safety check
For every failure path, the message returned to the user contains no URLs and
no API keys. This is enforced by raising `ApiProblem` with `from None` in
`_get`, which drops the original exception (and any URL it might carry) from the
chain. A test (`test_key_never_leaks_into_messages`) confirms the key does not
appear in any returned message, including on mocked failures.
