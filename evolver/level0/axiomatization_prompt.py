def axiomatization():
    """
# Axiom A0 — “Reality” of ground-truth is the following tables/views in [app_ddl.md](../app_ddl.md)
- `app.city(id, name, state, country, lat, lon)`
- `app.street(id, name, city_id, lat, lon)`
- `app.house(id, name, street_id, lat, lon)`
- `app.address` (materialized view): canonical address strings + ids + lat/lon
- `app.stop_word` (stop-words)
- `app.run` (aggregated metrics per run)
- `app.run_result` (per-address results: found, error, duration, etc.)

# Axiom A1 — Canonical address universe
- `app.address` is the **fixed continuum** of canonical, valid addresses.

# Axiom A2 — NotFound is an application error
- Any `NotFound` result for a canonical address from `app.address` is **an error of the application/index**.

# Axiom A3 — Counterexamples are selected via SQL WHERE-suffix
- A “counterexample generator” is always a **valid SQL WHERE-suffix** that selects a subset of rows from
  `app.address`.
- The evaluator endpoint executes the suffix after `WHERE` (no full SELECT statements).
- Do NOT include `;` or any DDL/DML.

# Axiom A4 — The evaluator is the system under test
- You do not need to create unit-tests.
- You measure reality via the evaluator REST endpoint (aggregated metrics + run artifacts in DB).

# Axiom A5 — Database write policy (schema discipline)

1) **Immutability** (Read-only baseline)
    - Treat `app.*` as **immutable truth / ground data**.
    - All created entities must be in a non-app schema, e.g.:
        - `theory_{theory_name}_{sig8}_v{N}` (final naming rules come from OpenEvolve prompt)
    - Never create objects in `app`.
    - No `CREATE OR REPLACE` for theory objects.
    - Once created, a theory schema is immutable. Improvements create a new schema/version.
    - you MAY create new DB entities ONLY to represent and accelerate Theory (Mechanism) computation, under strict
      rules:
        1) New schemas MUST be separate from `app`, named:
            - `theory-{theory_name}-{sig8}-v{N}` (naming convention; wrapper computes N)
        2) Schemas are IMMUTABLE once created (no CREATE OR REPLACE; no mutation).
        3) Default allowed objects: VIEW only.
            - MATERIALIZED VIEW only if explicitly enabled and refresh is deterministic.
        4) Theory schemas used for prediction MUST NOT depend on `app.run` or `app.run_result` (no label leakage).
        5) L0 MUST output `theory_manifest.sql` (ordered DDL for created objects) and `theory_signature`.
        6) If schema exists for same theory_signature → reuse; otherwise create a new one.

    - Do not run:
        - `DROP`, `TRUNCATE`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE` in `app` schema
        - any function/procedure that could mutate state
    - Default mode is **READ-ONLY**:
        - no DDL/DML against `app.*` schema
        - no schema modifications unless explicitly allowed under the **Theory schema policy** below
    - All queries must:
        - be deterministic (avoid `now()`/`random()` unless explicitly allowed)
        - include limits when sampling
        - avoid unbounded cross joins or accidental full scans unless required and justified
2) **Default objects**
    - Allowed by default: `VIEW`
    - `MATERIALIZED VIEW` only if explicitly enabled by prompt/config and refresh is deterministic.
3) **Resource limits**
    - Avoid creating views that cause runaway planning/execution (e.g., deeply nested subqueries without bounds).
    - Respect any wrapper-enforced timeouts and row limits.
4) **Group_sql**
    - Theory schemas used for prediction/mechanism must not depend on:
        - `app.run`, `app.run_result`
        - any tables derived from run outputs
    - A “group_sql” is a **WHERE-suffix** only:
        - must not contain `;`
        - must not contain comments (`--`, `/* */`)
        - must not contain DDL/DML keywords (`DROP/DELETE/UPDATE/INSERT/ALTER/CREATE/TRUNCATE/COPY/CALL/DO`)
    - Prefer referencing `app.address` via a stable alias `a` in group_sql contexts.
    - Use `SELECT` and CTEs for:
        - feature stats (token/prefix counts)
        - stratified sampling sets
        - aggregation of `run_result` to compute metrics (when allowed by prompt)
    """
    pass
