# realtime-info-assistant

A small assistant that answers live weather and currency questions by calling
the right API tool — never guessing numbers.

## What it does

You ask a question in plain English, and the assistant decides whether to fetch
live weather or live currency data, calls the appropriate tool, and reports the
answer along with which tool was used (so you can verify it identified the right
API). It declines off-topic questions instead of making things up.

Example interactions:

- "What is the weather in Lagos?" → calls Open-Meteo, returns temperature,
  wind, and units.
- "Convert 100 USD to NGN." → calls ExchangeRate-API, returns the amount, both
  currency codes, the rate, and when the rate was last updated.

## Which two APIs, and why

| API | Purpose | Why |
|-----|---------|-----|
| [Open-Meteo](https://open-meteo.com) (Geocoding + Forecast) | Weather | Completely free, no API key required, returns current temperature and wind with units. |
| [ExchangeRate-API](https://exchangerate-api.com) | Currency | Free tier available, returns conversion rate, result, and last-updated time. |

## How to get both keys

1. **Open-Meteo** — no key needed; works out of the box.
2. **ExchangeRate-API** — sign up for a free key at
   https://exchangerate-api.com. The free tier is capped at 1,500 requests per
   month.

## Setup

```powershell
# Clone / open the repo
cd realtime-info-assistant

# Create and activate the virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Copy the example env file and fill in your keys
copy .env.example .env
# Then edit .env and replace the placeholders with real values:
#   OPENAI_API_KEY=sk-...
#   EXCHANGERATE_API_KEY=your-real-key

# Install dependencies
pip install -r requirements.txt
```

`OPENAI_BASE_URL` is optional — leave it unset to talk to OpenAI directly, or
set it to `https://openrouter.ai/api/v1` to use OpenRouter (the assistant sends
OpenRouter-friendly `HTTP-Referer` and `X-Title` headers when a base URL is
configured).

**Important:** `.env` is gitignored and must never be committed. Only
`.env.example` (with placeholders) is committed. No real key is ever committed
to this repository.

## How to run

```powershell
.venv\Scripts\Activate.ps1
python agent.py
```

Then type your question at the prompt. Press `Ctrl+C` or `Ctrl+D` to exit.

## How to test

All tests are offline — they never call the real APIs or the real language
model. HTTP calls are faked with `httpx.MockTransport`, and the LLM is replaced
with a fake tool-calling model.

```powershell
.venv\Scripts\Activate.ps1
pytest
```

To re-record live sample answers (requires your own `EXCHANGERATE_API_KEY`):

```powershell
$env:EXCHANGERATE_API_KEY="your-real-key"
python run_test_questions.py
```

This writes raw answers + tools used to `docs/test_answers_raw.txt`; it never
overwrites your hand-written judgments in `docs/sample_questions.md`.

## File table

| Path | Purpose |
|------|---------|
| `agent.py` | Agent entry point: builds the LLM, runs `create_agent`, handles errors, extracts tools used, and provides the `main()` input loop. |
| `tools.py` | The two tools (`get_current_weather`, `convert_currency`), the `ApiProblem` exception, the HTTP helper `_get`, and the `TOOLS` list. |
| `conftest.py` | Shared `MockTransport` fixture so tests never hit the network. |
| `tests/test_tools.py` | Offline tests for both tools (success, validation, errors, key safety, descriptions). |
| `tests/test_agent.py` | Offline tests for the agent (tool call + answer, empty question, recursion guard). |
| `run_test_questions.py` | Records sample-question answers + tools used to a raw file. |
| `requirements.txt` | Pinned direct dependencies. |
| `.env.example` | Placeholder environment variables (no real keys). |
| `.gitignore` | Ignores `.env`, `.venv/`, caches, OS files, and `steps.docx`. |
| `docs/api_exploration.md` | Live API shapes observed during Step 2 (success and failure JSON). |
| `docs/sample_questions.md` | 5 sample questions with answers and hand-written judgments. |
| `docs/error_handling_evidence.md` | One row per failure case: trigger, what the user saw, real vs simulated. |
| `docs/api_limitations_and_risks.md` | Freshness, weather source, quota, ambiguity, model risk, third-party risk, privacy, key risks, cost. |
| `README.md` | This file. |

## Python version

Developed and tested on **Python 3.13.13**.

## Security

No real API key is committed to this repository. `.env` is gitignored, and the
HTTP helper deliberately strips URLs and keys from any error message before
showing it to the user.
