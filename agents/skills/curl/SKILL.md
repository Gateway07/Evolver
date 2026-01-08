# curl.exe

## Contract
- Use `curl.exe` via the provided wrapper (preferred) or skill.
- Only call **localhost** endpoints unless explicitly allowed by the OpenEvolve prompt.
- For endpoints that require **GET with body**, always use explicit method and binary body:
  - `-X GET`
  - `--data-binary "<payload>"` (or `--data-raw` if explicitly allowed)
- Always set `Content-Type` when sending JSON:
  - `-H "Content-Type: application/json"`

## Runbook: Evaluator call (GET with body)
- Endpoint: defined by the OpenEvolve prompt (typically `/admin/search-test/search-by-sql`)
- Payload: a SQL **WHERE-suffix** string (no full SELECT; no semicolons; no comments)
- Use:
  - `curl -i -X GET "<URL>" --data-binary "<WHERE-suffix>"`

## Runbook: Tracing lifecycle (see [@tracing.md])
Tracing uses a **tracingId** for breakpoints/logs, and experiments produce a separate **runId** (DB record). Keep them distinct.

1) Cleanup:
- `DELETE http://localhost:8080/tracing/{tracingId}`

2) Set breakpoints:
- `POST http://localhost:8080/tracing/{tracingId}/points`
- JSON body: array of breakpoint definitions (exact shape defined by tracing skill / runbook)

3) Run traced experiment request(s):
- Only endpoints under `/admin/search-test/*` are traced.
- A tracing header MUST be provided on traced requests:
  - Either `X-TRACING_MDC_KEY: {tracingId}` or `X-RUN_MDC_KEY: {tracingId}`
  - The correct header name is deployment-specific and must be selected by the wrapper/config.

4) Fetch logs:
- `GET http://localhost:8080/tracing/{tracingId}/logs`
- Include the same tracing header used in step (3).

> Note: The OpenEvolve prompt will define what tracing variables to collect and how they feed mechanism hypotheses.