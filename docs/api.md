# REST API

Base URL for local development: `http://127.0.0.1:5001`. The API is stateless and read-only. Requests use JSON; no API key or account is required locally.

## Response contract

Successful versioned endpoints return `{"data": ..., "meta": {...}}`. Client errors return `{"error":{"code":"validation_error","message":"...","request_id":"..."}}`. Every response includes `X-Request-ID` for correlation. Status codes: 400 invalid input/JSON, 404 unknown endpoint/destination, 405 unsupported method, 413 body over 16 KiB, 415 non-JSON POST, 500 unexpected server failure. Internal exception messages are not exposed.

## Endpoints

| Method | Path | Behavior |
|---|---|---|
| GET | `/health` | Readiness: fitted catalogue and record count. |
| GET | `/api/v1/options` | Supported interests, states/location labels, regions, seasons, cost tiers, and default weights. |
| GET | `/api/v1/destinations` | Filtered, paginated, unique-name discovery. |
| GET | `/api/v1/destinations/{id}` | Destination facts, advisory text, permits, and original itinerary for an exact source variant. |
| POST | `/api/v1/recommendations` | Personalized hybrid or content-based ranking and component breakdowns. |
| POST | `/api/v1/itineraries` | Deterministic day-by-day draft using only source attractions/activities. |

### Discovery filters

`q` searches names, state/location, and experience descriptions. Optional `state`, `region`, `interest`, `season`, `max_daily_budget`, `budget_tier`, and `days` filter eligible source variants before duplicate suppression and pagination. State/region are case-insensitive exact matches; interests are normalized exact tags. Budget discovery requires the **upper** endpoint to fit. Season requires a best-season match without an avoid match; days must fall within the source minimum/maximum range.

`page` defaults to 1 (range 1–1000); `limit` defaults to 12 (range 1–100). `meta` contains `total`, `page`, and `limit`. Unknown/repeated parameters are rejected. Empty results return 200 with an empty list.

```sh
curl 'http://127.0.0.1:5001/api/v1/destinations?interest=beach&season=winter&max_daily_budget=4000&days=3'
```

### Recommendations

```sh
curl -X POST http://127.0.0.1:5001/api/v1/recommendations \
  -H 'Content-Type: application/json' \
  -d '{"model":"hybrid","interests":["beach","nature"],"daily_budget":3000,"budget_tier":"budget","season":"winter","trip_days":3,"top_n":5}'
```

| Field | Type / limits | Default |
|---|---|---|
| `model` | `hybrid` or `content` | `hybrid` |
| `selected_destination` | Original numeric ID, or nonempty exact name ≤120 characters | omitted |
| `interests` | List of ≤20 nonempty phrases, each ≤60 characters | omitted |
| `daily_budget` | Finite number 1–1,000,000, INR daily source-estimate units | omitted |
| `budget_tier` | `budget`, `mid-range`, `luxury` | `budget` |
| `season` | `winter`, `summer`, `spring`, `autumn`, `monsoon`, `post monsoon`; `fall` aliases autumn | omitted |
| `trip_days` | Finite number 0.5–30 | omitted |
| `top_n` | Integer 1–20 | 5 |
| `strict_filters` | Boolean | false |
| `state`, `region` | Nonempty exact location label | omitted |
| `weights` | Partial map of hybrid component weights, each finite 0–100 | model defaults |

Unknown fields, nulls, booleans in numeric fields, and invalid values are rejected. Content mode requires a destination or usable interest text and rejects hybrid weights. Geography is always a filter. Budget/season/duration affect hybrid scoring; content mode uses them only with strict filtering. Strict filters require budget covering the **lower** endpoint, a best season with no avoid match, and days within the source range; these do not guarantee costs at the upper endpoint. Interest matching remains soft. All variants of the selected name are excluded; each result uses one highest-scoring eligible variant per normalized name.

Each result contains `destination` (summary), `score`, and `breakdown`. Hybrid breakdown keys are `content`, `popularity`, `interests`, `budget`, `season`, `duration`; each has `score`, effective `weight`, and `contribution`. Contributions sum to the final score. Omitted preferences deactivate their weights; remaining weights normalize to one. Default weights are 0.30/0.10/0.20/0.15/0.15/0.10 respectively. Scores are matching utilities, not probabilities. An empty hybrid profile gives a popularity-only ranking. Unknown interests may still produce hybrid results through other components; response metadata includes a warning when no terms are recognized. Fewer than five eligible results is valid.

### Itineraries

```sh
curl -X POST http://127.0.0.1:5001/api/v1/itineraries \
  -H 'Content-Type: application/json' \
  -d '{"destination_id":1,"days":3,"budget_tier":"budget","interests":["beach"]}'
```

Require `destination_id` (positive integer source ID) and `days` (integer 1–14); optionally accept `budget_tier` and `interests`. The result includes `days` (title, unique attractions, activities), multiplied `estimated_cost`, original `source_itinerary`, permits, considerations, and warnings. Interest phrases prioritize matching source items. Day assignment is deterministic and not route-optimized; empty days are flexible time. Confirm opening hours, transport, permits, and prices. Costs exclude unverified origin transport and do not assert a per-person basis.

## Configuration and deployment

See [.env.example](../.env.example). CORS allows only configured origins; no credentialed wildcard origin is enabled. Logs record generated request IDs, method, route pattern, status, and timing, without bodies/query strings/headers. Use HTTPS, a reverse proxy with rate limits, and a production WSGI server before public deployment. The local development server is not a production host.
