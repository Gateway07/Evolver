# AGENTS.md — Codex CLI Constitution (Stable Rules)

This document is the **stable operating constitution** for any CLI LLM agent (Codex CLI now, Claude Code CLI later)
running inside this repository.  
It defines **tooling contracts/runbooks**, **safety/policy constraints**, and **signature canonicalization rules**.  
Anything about **artifact formats**, **task objectives**, **hypothesis DSL schemas**, **scoring**, and **what to output** belongs in the **OpenEvolve prompt** (e.g. `prompts/l1/prompt.md`).

---

## 0) Repo map and entry points

### Project roots

- `osmand/` — main Java application code and related modules.
- `tools/` — Java application code and related modules.
- `prompts/` — OpenEvolve prompts (L1/L0) and examples.

### Canonical documents

- OpenEvolve prompts live under: `prompts/`
- Tool skills live under: `skills/`
- Signature canonicalization utility: `scripts/canonicalize.py` (or equivalent)

---

## 1) Tooling contracts & runbooks

Agents MUST use tools only through the repository’s tool wrappers (or through the documented skill interfaces). Do not
“freestyle” direct calls that bypass guardrails.

### 1.1 curl.exe — [curl skill](skills/curl/SKILL.md)

### 1.2 psql.exe — [postgresql-psql skill](skills/postgresql-psql/SKILL.md)

### 1.3 Pluggable CLI LLM clients (Codex CLI, Claude Code CLI)

#### Contract

- The orchestrator (OpenEvolve/OptiLLM) provides:
    - the current prompt file path (e.g., `prompts/l1/prompt.md`)
    - run config (thresholds, topK, repeats, holdout split)
    - locations for output artifacts (`artifacts/...`)
- The agent must:
    - load and follow this `AGENTS.md` first
    - then follow the OpenEvolve prompt for the current task

#### Runbook: Swapping CLI clients

- Tooling invocation MUST be independent of the LLM client:
    - all system actions go through wrappers/skills
- The agent’s role is planning + emitting tool calls + producing output artifacts as specified by the OpenEvolve prompt.

---

## 2) Safety and policy constraints

### 2.1 Network policy

- Allowed hosts: `localhost`, `127.0.0.1`
- Allowed ports: as specified in OpenEvolve prompt (default: `8080`)
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

---

## 3) Signature canonicalization rules

All signatures MUST be computed by the **wrapper** (not by the LLM).  
Signature algorithm: `sha256(canonical_form)`.

### 3.1 Canonicalization for JSON DSL

Used for:

- `hypothesis_dsl`
- `theory_dsl` (mechanism model)

Rules:

1) UTF-8 encoding.
2) Deterministic key ordering (lexicographic) at all object levels.
3) Minified JSON (no insignificant whitespace).
4) Numbers:
    - use JSON numbers (not strings) when numeric
    - forbid `NaN`, `Infinity`, `-Infinity`
5) Strings:
    - normalize newlines to `\n`
    - trim leading/trailing whitespace where semantics do not require it
6) Arrays preserve order; if a set is intended, the DSL must sort explicitly.

### 3.2 Canonicalization for SQL WHERE-suffix (`group_sql`)

Used for:

- `group_signature`

Rules:

1) Reject unsafe constructs:
    - no `;`, no multiple statements, no comments, no DDL/DML keywords.
2) Normalize whitespace:
    - collapse whitespace runs to single spaces
    - trim ends
3) Normalize keyword casing:
    - uppercase SQL keywords (`AND`, `OR`, `IN`, `SELECT`, `FROM`, `ORDER BY`, `LIMIT`, etc.)
4) Identifier casing:
    - preserve quoted identifier case
    - otherwise treat identifiers as lower-case
5) Parentheses:
    - preserve as written unless AST canonicalization is enabled.

If the wrapper supports a SQL AST parser (preferred):

- sort commutative boolean operands (`AND` and `OR`) by their serialized canonical form
- sort pure-literal `IN (...)` lists where semantics permit

### 3.3 Canonicalization for Theory SQL-rule DSL (if you choose SQL instead of JSON)

If `theory_dsl` is represented as SQL-rule DSL, the wrapper must:

- apply SQL canonicalization rules (similar to above)
- hash the full canonical rule set (including object definitions if used)

### 3.4 Canonical signature fields

- `group_signature = sha256(canonical_sql(group_sql))`
- `hypothesis_signature = sha256(canonical_json(hypothesis_dsl))`
- `theory_signature = sha256(canonical_json(theory_dsl))` (or canonical SQL-rule DSL)

---

## 4) Notes on what belongs elsewhere

- **Artifact formats** (exact JSON output schema, required fields, filenames, where to write files) are defined in:
    - the OpenEvolve prompt (`prompts/l1/prompt.md`), not in this file.
- **Objective functions**, scoring weights, thresholds, holdout split definition, acceptance gates:
    - belong to OpenEvolve prompt.

---

## 5) Compliance

Agents must treat these rules as **non-overridable** unless the repository owners update `AGENTS.md`.  
If the OpenEvolve prompt conflicts with this constitution, **AGENTS.md wins** and the agent must surface the conflict in
its output notes.
