# API Exploration

This document records what each API returns (success and failure shapes), the real JSON fields needed, and how each failure looks. Real keys are **not** included; placeholder `YOUR-KEY` is used where a key is required.

## 1. Open-Meteo Geocoding API

### Base URL
`https://geocoding-api.open-meteo.com/v1/search`

### Successful call (Lagos)
```
GET https://geocoding-api.open-meteo.com/v1/search?name=Lagos&count=1&language=en&format=json
```

Response (HTTP 200):
```json
{
  "results": [
    {
      "id": 2332459,
      "name": "Lagos",
      "latitude": 6.45407,
      "longitude": 3.39467,
      "elevation": 11,
      "feature_code": "PPLA2",
      "country_code": "NG",
      "admin1_id": 2332453,
      "timezone": "Africa/Lagos",
      "population": 15388000,
      "country_id": 2328926,
      "country": "Nigeria",
      "admin1": "Lagos"
    }
  ],
  "generationtime_ms": 0.11885166
}
```

**Fields we need:** `results[0].latitude`, `results[0].longitude`, `results[0].name`, `results[0].country`, `results[0].timezone`.

### Failure: unknown place (Nowhereville)
```
GET https://geocoding-api.open-meteo.com/v1/search?name=Nowhereville&count=1&language=en&format=json
```

Response (HTTP 200):
```json
{
  "generationtime_ms": 0.10609627
}
```

**Error shape:** HTTP status is 200 (success), but the JSON body has **no `results` key** (or an empty `results`). The error is communicated **in the JSON body only**, not the HTTP status. Our tool must check `data.get("results")` and treat a missing/empty list as "couldn't find a place called…".

## 2. Open-Meteo Forecast API

### Base URL
`https://api.open-meteo.com/v1/forecast`

### Successful call (Lagos coordinates)
```
GET https://api.open-meteo.com/v1/forecast?latitude=6.45&longitude=3.4&current=temperature_2m,wind_speed_10m&timezone=auto
```

Response (HTTP 200):
```json
{
  "latitude": 6.4323373,
  "longitude": 3.3948028,
  "generationtime_ms": 0.026106834411621094,
  "utc_offset_seconds": 3600,
  "timezone": "Africa/Lagos",
  "timezone_abbreviation": "GMT+1",
  "elevation": 5,
  "current_units": {
    "time": "iso8601",
    "interval": "seconds",
    "temperature_2m": "°C",
    "wind_speed_10m": "km/h"
  },
  "current": {
    "time": "2026-11-22T14:30",
    "interval": 900,
    "temperature_2m": 30.5,
    "wind_speed_10m": 12.6
  }
}
```

**Fields we need:** `current.temperature_2m`, `current.wind_speed_10m`, `current_units.temperature_2m`, `current_units.wind_speed_10m`, plus `latitude`/`longitude`/`timezone` for the readable sentence.

### Failure: server error / missing current
Not triggered against the live API (Open-Meteo returned 200). Per the steps, if the server returns a 5xx or `current` is missing, return a "service unavailable" message. This path is covered by unit tests with mocked responses (see Step 5).

## 3. ExchangeRate-API Currency API

### Base URL
`https://v6.exchangerate-api.com/v6/YOUR-KEY/pair/{FROM}/{TO}/{AMOUNT}`

You must obtain a free key at https://exchangerate-api.com and put it in `.env` (never committed).

### Live call with dummy key (auth failure)
```
GET https://v6.exchangerate-api.com/v6/dummy-key/pair/USD/NGN/100
```

Result: **HTTP 403 Forbidden**. No JSON body was readable through the fetcher.

**Error shape:** A bad/missing key is communicated **via HTTP status (403)**. Our tool reads `EXCHANGERATE_API_KEY` from the environment and returns a clear "missing key" message before making any request; a 403 from the live API should surface as an authentication problem.

### Failure: nonsense currency code / bad amount
Not triggered against the live API (auth blocks the request without a real key). Per the steps, we validate locally first:
- Currency codes must be exactly three letters (e.g. "dollars" rejected with a helpful message).
- Amount must be a positive, finite number.

Then we check the JSON body for `result == "error"` (not just HTTP status), map known `error-type` values to friendly messages, and use a catch-all for unknown ones. These paths are covered by unit tests with mocked responses (see Step 5).

### Fields we need (on success)
Expected success shape (from provider docs): `conversion_rate` and `conversion_result`, plus the time the rate was last updated. Return a sentence with the amount, both codes, the rate, and when the rate was last updated.

## 4. Summary of error shapes

| API | Trigger | HTTP status | JSON body signal | Where the error shows |
|-----|---------|-------------|------------------|----------------------|
| Geocoding | Unknown place | 200 | missing/empty `results` | JSON body only |
| Forecast | 5xx / missing `current` | 5xx (expected) | `current` absent | HTTP status + body |
| Currency | Bad/missing key | 403 (observed) | n/a | HTTP status |
| Currency | Bad `error-type` | varies | `result == "error"` | JSON body |

**Key takeaway:** Do not rely only on HTTP status. The geocoder reports "not found" with HTTP 200 plus an empty JSON body, so the tool must inspect the JSON. The currency API reports auth failure via HTTP 403, so the tool must handle non-200 statuses too.

## Next step
Get your own free key at https://exchangerate-api.com, add it to `.env` as `EXCHANGERATE_API_KEY`, then run a live currency call to confirm the success JSON shape before writing `tools.py` (Step 3).