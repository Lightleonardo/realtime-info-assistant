# API Limitations and Risks

This document lists the known limitations and risks of the realtime-info-assistant,
covering both the Open-Meteo weather/geocoding APIs and the ExchangeRate-API
currency API, plus the language model that powers the agent.

## 1. Freshness — currency rates are daily, not live

ExchangeRate-API updates its rates once per day. When the assistant reports a
"current" rate, it means the latest daily rate published by the service — not a
live, streaming market quote. The rate can also differ from what a bank, bureau
de change, or street-market cashier actually offers you, since those providers
add their own margins and fees.

## 2. Weather data comes from a service, not a local station

Open-Meteo's `"current"` values (temperature, wind speed, etc.) are produced by
an underlying weather model/service. They may not match a local weather station
at the exact location you asked about, and they are not a substitute for
official weather warnings or forecasts used for safety-critical decisions.

## 3. Quota — free currency tier is capped

The free ExchangeRate-API tier is limited to **1,500 requests per month**.
Every currency conversion the assistant performs consumes one request. If the
quota is exhausted, the tool returns an error ("quota reached") rather than a
conversion. Heavy use of the assistant could exhaust the monthly quota quickly.

## 4. Ambiguity — the geocoder takes the first match

The Open-Meteo geocoder returns the first matching place for a name query. For
common place names (for example, "Springfield" exists in many U.S. states), it
may resolve to a city you did not mean. The assistant does not ask for
disambiguation; it simply reports the weather for the first result it receives.

## 5. Model risk — the model might answer from memory

The language model could answer a weather or currency question from its
training data instead of calling a tool, which would produce stale or invented
numbers. The system prompt explicitly forbids this ("always use a tool for live
data and never guess numbers"), but it is a guideline, not a guarantee. This is
why the assistant reports which tool was used, so you can verify that live data
was fetched.

## 6. Third-party risk — both APIs can change or disappear

The assistant depends on two external APIs (Open-Meteo and ExchangeRate-API)
that are outside our control. Either provider can change its endpoints, response
shape, pricing, or terms of service at any time, or shut down entirely. A
real-world example is Frankfurter's v1 API, which was deprecated yet kept
available — providers sometimes keep old versions running for a while, but they
can also remove them without notice. The assistant would need code changes to
adapt to a new API version or provider.

## 7. Privacy — city names and amounts go to third parties

When you ask about the weather in a city or a currency conversion, the city
name, currency codes, and amount are sent to Open-Meteo and/or ExchangeRate-API.
Treat those details as shared with third parties; do not ask about sensitive or
private locations or amounts.

## 8. Key risks — a key in a URL can leak

The ExchangeRate-API key is embedded in the request URL
(`https://v6.exchangerate-api.com/v6/{KEY}/pair/...`). URLs can appear in
server logs, proxy logs, browser history, and error messages. The assistant's
HTTP helper strips URLs and keys from error messages (`from None` drops the
chained exception, and `ApiProblem` messages never contain URLs or keys), but
the key still travels in the request itself and may be logged by intermediaries
or by the API provider. Rotate your key if you suspect it has been logged or
exposed.

## 9. Cost — every question costs a language-model call

Each question you ask the assistant costs at least one language-model call
(and potentially several, if the model calls tools in a loop). There is no free
tier for the model itself; you pay for every inference. Keep questions focused
to avoid unnecessary cost, and note the `recursion_limit` guard (set to 8) that
prevents a confused model from calling tools endlessly.
