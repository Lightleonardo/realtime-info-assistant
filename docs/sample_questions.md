# Sample Questions & Judgments

Five sample questions covering both APIs. For each: the question, the tool(s)
used, the answer (from a live run of `run_test_questions.py` in `agent` mode),
and my own hand-written judgment after reading the real answer.

**How the answers were generated:** `run_test_questions.py` was run in
`agent` mode (`USE_AGENT=1`) against a real language model via OpenRouter
(model: `nvidia/nemotron-3.5-lightning:free`). Weather answers came from live
calls to Open-Meteo (no key needed). Currency answers came from live calls to
ExchangeRate-API using the configured `EXCHANGERATE_API_KEY`.

Raw machine-recorded answers (no judgments) are in
`docs/test_answers_raw.txt`. Re-running `run_test_questions.py` overwrites that
raw file only; it never touches the judgments below.

---

## 1. Weather in a city you know

**Question:** What is the current weather in Lagos?

**Tool(s) used:** `get_current_weather`

**Answer:** The current weather in Lagos is 28.5°C with winds of 6.0 km/h.

**Judgment:** Good. The geocoder resolved Lagos to the right city (Nigeria),
the temperature and wind are plausible, and the units (°C, km/h) are shown.
This is the strongest answer in the set.

---

## 2. A currency conversion with an amount

**Question:** Convert 100 USD to NGN.

**Tool(s) used:** `convert_currency`

**Answer:** 100 USD is equal to **136,778.18 NGN** at an exchange rate of
1 USD = 1,367.7818 NGN (rates last updated on Thu 26 Nov 2026).

**Judgment:** Good. The assistant correctly identified that a currency tool
was needed, called ExchangeRate-API, and returned the amount, both currency
codes, the rate, and the last-updated timestamp. The rate (≈1,368 NGN per USD)
is plausible for November 2026.

---

## 3. An ambiguous place ("weather in Springfield")

**Question:** What is the weather in Springfield?

**Tool(s) used:** `get_current_weather`

**Answer:** The current weather in Springfield, United States is -2.0°C with
winds around 18.2 km/h.

**Judgment:** Weak. The geocoder takes the first match, which resolved to
Springfield, United States — but the user might have meant Springfield,
Illinois, or Springfield, Massachusetts, or any of the other Springfields.
The answer gives no indication that an ambiguous name was resolved to just one
option. This matches the documented ambiguity risk.

---

## 4. A question that needs both tools

**Question:** What is the weather in Tokyo, and how much is 50 USD in JPY?

**Tool(s) used:** `get_current_weather`, `convert_currency`

**Answer:** Weather in Tokyo: It's 12.1°C with winds of 2.3 km/h in Tokyo,
Japan.

Currency conversion: 50 USD = 7,958.73 JPY (rate ≈ 159.17 JPY per USD,
last updated on Thu 26 Nov 2026).

**Judgment:** Good. The assistant correctly identified that two different
tools were needed and called both. The weather answer is accurate for Tokyo,
and the currency conversion shows both the result and the rate. This
demonstrates the core requirement: the assistant identified the appropriate
API tools for a multi-part question.

---

## 5. An off-topic question

**Question:** Who won the 1998 World Cup?

**Tool(s) used:** (none)

**Answer:** I'm sorry, but I can only help with live weather and currency
questions. I don't have information about sports events like the 1998 World
Cup. Let me know if you need weather or currency data!

**Judgment:** Good. The assistant declined an off-topic question without
calling any tool or guessing, exactly as the system prompt requires. No live
data was fetched, so no third-party data was exposed.

---

## Summary

| # | Question | Tools | Answer quality | Judgment |
|---|----------|-------|----------------|----------|
| 1 | Weather in Lagos | get_current_weather | Strong | Correct city, plausible values, units shown |
| 2 | Convert 100 USD to NGN | convert_currency | Good | Correct rate, result, and last-updated timestamp |
| 3 | Weather in Springfield | get_current_weather | Weak | First-match geocoder may pick wrong Springfield |
| 4 | Weather in Tokyo + USD→JPY | get_current_weather, convert_currency | Good | Both tools selected correctly |
| 5 | Who won the 1998 World Cup? | (none) | Good | Politely declined, no tool called |
