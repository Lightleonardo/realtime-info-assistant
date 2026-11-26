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

### Live success call (USD → NGN)
```
GET https://v6.exchangerate-api.com/v6/YOUR-KEY/pair/USD/NGN/100
```

Response (HTTP 200) — real key redacted:
```json
{
  "result": "success",
  "documentation": "https://www.exchangerate-api.com/docs",
  "terms_of_use": "https://www.exchangerate-api.com/terms",
  "time_last_update_unix": 1795651201,
  "time_last_update_utc": "Thu, 26 Nov 2026 00:00:01 +0000",
  "time_next_update_unix": 1795737601,
  "time_next_update_utc": "Fri, 27 Nov 2026 00:00:01 +0000",
  "base_code": "USD",
  "target_code": "NGN",
  "conversion_rate": 1367.7818,
  "conversion_result": 136778.18
}
```

**Fields we need:** `conversion_rate`, `conversion_result`, `time_last_update_utc` (or `time_last_update_unix`), plus `base_code` and `target_code`.

### Live failure: wrong key
```
GET https://v6.exchangerate-api.com/v6/wrong-key-123/pair/USD/NGN/100
```

Response (HTTP 403):
```json
{
  "result": "error",
  "documentation": "https://www.exchangerate-api.com/docs",
  "terms-of-use": "https://www.exchangerate-api.com/terms",
  "error-type": "invalid-key"
}
```

**Error shape:** HTTP 403 with `result == "error"` and `error-type == "invalid-key"` in the JSON body. Both the HTTP status and the body signal the problem.

### Live failure: unsupported currency code (XYZ)
```
GET https://v6.exchangerate-api.com/v6/YOUR-KEY/pair/USD/XYZ/100
```

Response (HTTP 404):
```json
{
  "result": "error",
  "documentation": "https://www.exchangerate-api.com/docs",
  "terms-of-use": "https://www.exchangerate-api.com/terms",
  "error-type": "unsupported-code"
}
```

**Error shape:** HTTP 404 with `result == "error"` and `error-type == "unsupported-code"` in the JSON body. Our tool maps `unsupported-code` to a friendly message.

### Local validation (before any request)
Currency codes must be exactly three letters (e.g. `"dollars"` rejected with a helpful message). Amount must be a positive, finite number. These checks run before any HTTP request, so no network call is made for obviously bad input.

### Fields we need (on success)
`conversion_rate`, `conversion_result`, `time_last_update_utc`. Return a sentence with the amount, both codes, the rate, and when the rate was last updated.

## 4. Summary of error shapes

| API | Trigger | HTTP status | JSON body signal | Where the error shows |
|-----|---------|-------------|------------------|----------------------|
| Geocoding | Unknown place | 200 | missing/empty `results` | JSON body only |
| Forecast | 5xx / missing `current` | 5xx (expected) | `current` absent | HTTP status + body |
| Currency | Bad/missing key | 403 (observed) | `result == "error"`, `error-type` | HTTP status + JSON body |
| Currency | Unsupported code | 404 (observed) | `result == "error"`, `error-type == "unsupported-code"` | HTTP status + JSON body |
| Currency | Local validation failure | n/a (no request) | n/a | Local check, no HTTP |

**Key takeaway:** Do not rely only on HTTP status. The geocoder reports "not found" with HTTP 200 plus an empty JSON body, so the tool must inspect the JSON. The currency API reports auth failure and unsupported codes via non-200 HTTP status **and** `result == "error"` in the JSON body, so the tool must handle both.
