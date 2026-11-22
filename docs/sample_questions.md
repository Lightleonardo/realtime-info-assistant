# Sample Questions & Judgments

Five sample questions covering both APIs. For each: the question, the tool(s)
used, the answer (from a live run of `run_test_questions.py`), and my own
hand-written judgment after reading the real answer.

**How the answers were generated:** `run_test_questions.py` was run in
`direct-tools` mode (`USE_AGENT=0`) because no OpenAI API key is configured.
Weather answers came from live calls to Open-Meteo (no key needed). Currency
answers could not be fetched live because no `EXCHANGERATE_API_KEY` is
configured — the tool correctly reports that instead of inventing a rate.

Raw machine-recorded answers (no judgments) are in
`docs/test_answers_raw.txt`. Re-running `run_test_questions.py` overwrites that
raw file only; it never touches the judgments below.

---

## 1. Weather in a city you know

**Question:** What is the current weather in Lagos?

**Tool(s) used:** `get_current_weather`

**Answer:** It is 29.7°C with winds of 13.4 km/h in Lagos, Nigeria.

**Judgment:** Good. The geocoder resolved Lagos to the right city (Nigeria,
not Lagos, Portugal), the temperature and wind are plausible for Lagos in
November, and the units (°C, km/h) are shown. This is the strongest answer in
the set.

---

## 2. A currency conversion with an amount

**Question:** Convert 100 USD to NGN.

**Tool(s) used:** `convert_currency`

**Answer:** Currency conversion is not configured: the ExchangeRate API key is
missing.

**Judgment:** Honest but unhelpful — the tool behaves correctly (it refuses to
invent a rate without a key), but the user gets no conversion. This is expected
until the user adds a real `EXCHANGERATE_API_KEY` to `.env`. Once configured,
the answer should read like "100 USD = 150,000 NGN at a rate of 1500.0 (last
updated …)".

---

## 3. An ambiguous place ("weather in Springfield")

**Question:** What is the weather in Springfield?

**Tool(s) used:** `get_current_weather`

**Answer:** It is 9.6°C with winds of 24.2 km/h in Springfield, United States.

**Judgment:** Weak. The geocoder takes the first match, which happened to be
Springfield, United States — but the user might have meant Springfield,
Illinois, or Springfield, Massachusetts, or any of the other Springfields.
The answer gives no indication that an ambiguous name was resolved to just one
option. This matches the documented ambiguity risk (the geocoder takes the first
match). To improve, the assistant could ask "Which Springfield?" when multiple
results exist, but the current geocoder only returns `count=1`.

---

## 4. A question that needs both tools

**Question:** What is the weather in Tokyo, and how much is 50 USD in JPY?

**Tool(s) used:** `get_current_weather`, `convert_currency`

**Answer:** (live weather) It is 6.9°C with winds of 2.4 km/h in Tokyo, Japan.
(currency) not configured — ExchangeRate API key missing.

**Judgment:** Partially good. The weather part is correct and useful. The
currency part fails only because no key is configured; structurally the tool
was selected correctly, which shows the assistant can identify that two tools
are needed. With a key, this would be a strong multi-tool answer.

---

## 5. An off-topic question

**Question:** Who won the 1998 World Cup?

**Tool(s) used:** (none)

**Answer:** I can only help with weather and currency questions.

**Judgment:** Good. The assistant declined an off-topic question without
calling any tool or guessing, exactly as the system prompt requires. No live
data was fetched, so no third-party data was exposed.

---

## Summary

| # | Question | Tools | Answer quality | Judgment |
|---|----------|-------|----------------|----------|
| 1 | Weather in Lagos | get_current_weather | Strong | Correct city, plausible values, units shown |
| 2 | Convert 100 USD to NGN | convert_currency | Poor (config) | Correctly refuses without a key; needs live key |
| 3 | Weather in Springfield | get_current_weather | Weak | First-match geocoder may pick wrong Springfield |
| 4 | Weather in Tokyo + USD→JPY | get_current_weather, convert_currency | Mixed | Weather good; currency blocked by missing key |
| 5 | Who won the 1998 World Cup? | (none) | Good | Politely declined, no tool called |

**Note:** To get live currency answers, add a real key from
https://exchangerate-api.com to `.env` as `EXCHANGERATE_API_KEY` and re-run
`run_test_questions.py`.
