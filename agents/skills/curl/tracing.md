# Tracing Curl Skill — Workflow & Safety Rules

## How AI Agent should use Tracing API

- creating a new tracing run (cleanup)
- configuring tracing breakpoints
- executing single or multiply by SQL search-test requests with tracing enabled
- fetching the resulting tracing logs

Steps:

1. Generate tracingId, for example "tracing-2025-12-06-001" and clean up previous run:
   curl -i -X DELETE "http://localhost:8080/tracing/tracing-2025-12-06-001"

2. Setup new breakpoints:
   curl -i -X POST "http://localhost:8080/tracing/tracing-2025-12-06-001/points" -H "Content-Type: application/json"
   --data-raw "[{\"className\":\"net.app.search.SearchUICore\",\"line\":660,\"watchExpr\":[\"#text\"],\"condition\":
   null,\"hitCondition\":null,\"enabled\":\"true\",\"logMessage\":null,\"options\":{\"vars\":{},\"expr\":
   {},\"maxDepth\":3}}]"

3. Call Search Test REST API and add 'X-TRACING_MDC_KEY' header with corresponding tracingId value. Tracing is enabled
   only for requests under /admin/search-test/* where two REST are available:

- to search single address
  curl -i -X "http://localhost:8080/admin/search-test/search?query=330%203rd%20clermont&lat=28.5604574&lon=-81.7604685"
  -H "X-TRACING_MDC_KEY: tracing-2025-12-06-001"
  which returns JSON with actual search results (coordinates, distance, address, etc.)
- to search multiple addresses by using suffix SQL after WHERE keyword
  curl -i -X GET "http://localhost:8080/admin/search-test/search-by-sql" -H "X-TRACING_MDC_KEY: tracing-2025-12-06-001"
  --data-raw "id < 100"
  which returns JSON with aggregated metrics (runId, error, status, totalCount, failedCount, foundCount,
  partialFoundCount, totalDurationMs, totalBytes, searchDurationMs) to calculate objective criteria.
  All intercepted calls will be traced.

4. After calling address search get tracings:
   curl -i -X GET "http://localhost:8080/tracing/{tracingId}/logs" -H "X-TRACING_MDC_KEY: tracing-2025-12-06-001"

See JSON list of tracings (timestamp, class/method, expression calculations, duration, stacktrace, etc.) in the
response.

## Safety & policy rules

### Allowed host/port

- ✅ Only `http://localhost:8080`
- ❌ Any other host/port MUST be rejected
- ❌ No redirects (do not allow `--location`; treat redirect responses as failure)

### Allowed paths

- ✅ `/tracing/{tracingId}`
- ✅ `/tracing/{tracingId}/points`
- ✅ `/tracing/{tracingId}/logs`
- ✅ `/admin/search-test/search`
- ✅ `/admin/search-test/search-by-sql`
- ❌ Any other path MUST be rejected

### Mandatory headers

- For `search_single`, `search_by_sql`, and `get_logs`:
    - MUST include `X-TRACING_MDC_KEY: {tracingId}` :contentReference[oaicite:13]{index=13}
- For `set_points`:
    - MUST include `Content-Type: application/json` :contentReference[oaicite:14]{index=14}

### Request body rules

- `set_points`:
    - Body MUST be a JSON array of breakpoint objects.
    - Reject if body is not valid JSON.
- `search_by_sql`:
    - Body MUST be a short SQL **WHERE-suffix** string (e.g. `id < 100`). :contentReference[oaicite:15]{index=15}
    - Reject if it contains:
        - `;` (multi-statement)
        - DDL/DML keywords like: `drop`, `delete`, `update`, `insert`, `alter`, `create`, `truncate`, `copy`, `call`,
          `do`
        - comment tokens: `--`, `/*`, `*/`
    - Reject if the string is empty or exceeds a configured length limit.

### Timeouts and size limits

- Enforce conservative defaults (unless overridden within strict bounds):
    - Connect timeout: **≤ 5s**
    - Total timeout: **≤ 600s**
- Enforce response size cap:
    - Default maximum: **2 MB**
    - If exceeded, truncate and set `truncated=true` in the result (and keep full body only if explicitly allowed by
      policy).

### Curl flag restrictions

- MUST disallow any user-provided curl flags, especially:
    - `--proxy`, `-x`
    - `--resolve`
    - `--interface`
    - `--unix-socket`
    - `--config`
    - `--output` to arbitrary paths
    - any `file://` or other non-http(s) scheme usage