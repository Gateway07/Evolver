# AGENTS.md - AI Agent Constitution

This document is the **stable operating constitution** for any CLI LLM agent running inside this repository.  
All about **tooling contracts/runbooks**, **safety/policy constraints**, and **signature canonicalization rules**,
**artifact formats**, **task objectives**.

On startup, also mandatory to load:

- [curl skill](skills/curl/SKILL.md),
- [postgresql-psql skill](skills/postgresql-psql/SKILL.md),
- [continuity_prompt.md](prompts/continuity_prompt.md).
- [Tracing API](skills/curl/tracing.md).

## 1) Tooling contracts & runbooks

Agents MUST use tools only through the documented skill interfaces. Do not “freestyle” direct calls that bypass
guardrails.

### 1.0 pwsh (PowerShell 7.5.4) - use PowerShell as main shell tool.

### 1.1 curl.exe — [curl skill](skills/curl/SKILL.md)

### 1.2 psql.exe — [postgresql-psql skill](skills/postgresql-psql/SKILL.md)

### 1.3 Signature tool for Agent usage

All signatures MUST be computed by the wrapper. Use the repository tool `agents/scripts/signature_tool.py`

Usage:

- JSON DSL (hypothesis_dsl, theory_dsl):
    - `python agents/scripts/signature_tool.py json --file path/to/dsl.json`
    - Or pipe: `type path\to\dsl.json | python agents/scripts/signature_tool.py json`
- SQL WHERE-suffix (group_sql):
    - `python agents/scripts/signature_tool.py sql --file path/to/group_sql.txt --uppercase-keywords`
    - Or pipe: `type path\to\group_sql.txt | python agents/scripts/signature_tool.py sql --uppercase-keywords`

The tool prints the signature hex digest by default. Use `--print-canonical` to emit both the digest and canonical form.

### 1.5 Stateless execution + artifact continuity contract - see [continuity_prompt.md](prompts/continuity_prompt.md)

---

## 2) Safety and policy constraints

### 2.1 Network policy

- Allowed hosts: `localhost`, `127.0.0.1`
- Do not call external network resources.
- Do not follow redirects to non-local destinations.

### 2.2 Database policy

#### Read-only baseline

- Treat `osmand.*` as **immutable truth / ground data**.
- Do not run:
    - `DROP`, `TRUNCATE`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE` in `osmand` schema
    - any function/procedure that could mutate state
- Default mode is **READ-ONLY**:
    - no DDL/DML against `osmand.*` schema
    - no schema modifications unless explicitly allowed under the **Theory schema policy** below
- All queries must:
    - be deterministic (avoid `now()`/`random()` unless explicitly allowed)
    - include limits when sampling
    - avoid unbounded cross joins or accidental full scans unless required and justified

#### Theory schema policy (controlled writes)

DB writes are allowed only under ALL these conditions:

1) **Schema isolation**

- All created entities must be in a non-osmand schema, e.g.:
    - `theory_{theory_name}_{sig8}_v{N}` (final naming rules come from OpenEvolve prompt)
- Never create objects in `osmand`.

2) **Immutability**

- No `CREATE OR REPLACE` for theory objects.
- Once created, a theory schema is immutable. Improvements create a new schema/version.

3) **Default objects**

- Allowed by default: `VIEW`
- `MATERIALIZED VIEW` only if explicitly enabled by prompt/config and refresh is deterministic.

4) **No label leakage**

- Theory schemas used for prediction/mechanism must not depend on:
    - `osmand.run`, `osmand.run_result`
    - any tables derived from run outputs
- (If post-hoc analysis views are needed, they must be placed in a separate analysis schema and never used for
  prediction.)

5) **Resource limits**

- Avoid creating views that cause runaway planning/execution (e.g., deeply nested subqueries without bounds).
- Respect any wrapper-enforced timeouts and row limits.

### 2.3 SQL safety rules (for WHERE-suffixes and canonical queries)

- A “group_sql” is a **WHERE-suffix** only:
    - must not contain `;`
    - must not contain comments (`--`, `/* */`)
    - must not contain DDL/DML keywords (`DROP/DELETE/UPDATE/INSERT/ALTER/CREATE/TRUNCATE/COPY/CALL/DO`)
- Prefer referencing `osmand.address` via a stable alias `a` in group_sql contexts.

### 2.4 Tracing safety

- Breakpoints must be limited to what’s necessary.
- Avoid dumping sensitive data (if any).
- Always cleanup tracing sessions when done:
    - call `DELETE /tracing/{tracingId}` when the run is complete (unless the prompt asks to keep it for debugging).

## 2.5 Read-only queries

- Use `SELECT` and CTEs for:
    - feature stats (token/prefix counts)
    - stratified sampling sets
    - aggregation of `run_result` to compute metrics (when allowed by prompt)