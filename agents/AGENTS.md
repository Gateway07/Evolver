# AGENTS.md — Codex CLI Constitution

This document defines **tooling contracts/runbooks**, **safety/policy constraints**, and **signature canonicalization
rules**, **artifact formats**, **task objectives**, **hypothesis DSL schemas**, **scoring**, and **what to output**.

## 1) Tooling contracts & runbooks

Agents MUST use tools only through the documented skill interfaces. Do not “freestyle” direct calls that bypass
guardrails.

### 1.0 pwsh (PowerShell 7.5.4) - use PowerShell as main shell tool.

### 1.1 curl.exe — [curl skill](skills/curl/SKILL.md)

### 1.2 psql.exe — [postgresql-psql skill](skills/postgresql-psql/SKILL.md)

### 1.3 Pluggable CLI LLM clients (Codex CLI, Claude Code CLI)

#### Contract

- The orchestrator (OpenEvolve) provides:
    - the more specific prompt [open_evolve_prompt.md](prompts/open_evolve_prompt.md) which you should follow mandatory.
    - locations for output artifacts (`artifacts/...`).
- The agent must follow the OpenEvolve prompt for the current task.

### 1.4 Signature tool for Agent usage

All signatures MUST be computed by the wrapper (not by the LLM). Use the repository tool:

- `agents/scripts/signature_tool.py`

Usage:

- JSON DSL (hypothesis_dsl, theory_dsl):
    - `python agents/scripts/signature_tool.py json --file path/to/dsl.json`
    - Or pipe: `type path\to\dsl.json | python agents/scripts/signature_tool.py json`
- SQL WHERE-suffix (group_sql):
    - `python agents/scripts/signature_tool.py sql --file path/to/group_sql.txt --uppercase-keywords`
    - Or pipe: `type path\to\group_sql.txt | python agents/scripts/signature_tool.py sql --uppercase-keywords`

The tool prints the signature hex digest by default. Use `--print-canonical` to emit both the digest and canonical form.

### 1.5 Stateless execution + artifact continuity contract

The CLI agent MUST implement the following artifact contract in Continuity Ledger (compaction-safe) style.
Maintain a single Continuity Ledger for this workspace in [CONTINUITY.md](prompts/CONTINUITY.md). The ledger is the
canonical session briefing designed to survive stateful context compaction; do not rely on earlier chat text unless it’s
reflected in the ledger.

Ledger artifacts versioning storage:

- Use per-version folders: `artifacts/<version_id>/FACTS.diff`
- Append-only registry with small state summary per <version_id>: `artifacts/registry.json`

#### How the ledger works

- At the start of every assistant turn: read CONTINUITY.md, update it to reflect the latest
  goal/constraints/decisions/state, then proceed with the work.
- Update CONTINUITY.md again whenever any of these change: goal, constraints/assumptions, key decisions, progress
  state (Done/Now/Next), or important tool outcomes.
- Keep it short and stable: facts only, no transcripts. Prefer bullets. Mark uncertainty as UNCONFIRMED (never guess).
- If you notice missing recall or a compaction/summary event: refresh/rebuild the ledger from visible context, mark
  gaps AGENTS.md ask up to 1–3 targeted questions, then continue.
- CONTINUITY.md is for long-running continuity across compaction (the “what/why/current state”), not a step-by-step task
  list.
- Keep them consistent: when the plan or state changes, update the ledger at the intent/progress level (not every
  micro-step).

#### How versioning works

Use a separate “ledger versioning” mechanism when you need to change established facts/decisions in a way that should be
auditable over time (as opposed to routine progress updates).

- If some part of `CONTINUITY.md` needs changes in a versioning context, record the change as a facts diff artifact:
    - Create a new per-version folder: `artifacts/<version_id>/`
    - Write a single file: `artifacts/<version_id>/FACTS.diff`

`FACTS.diff` is Git diff format file to show difference between new and old version of changed CONTINUITY.md parts.

Maintain an append-only registry entry per `version_id` in `artifacts/registry.json`. Each entry should include:

- `version_id`
- `timestamp_utc`
- `author` (e.g., `assistant`, `user`)
- `facts_diff_path` (points to `artifacts/<version_id>/FACTS.diff`)
- `summary` (1–3 lines) is a short, human-readable summary of what changed in the ledger and why. Use bullet points.
  Reference the affected ledger section(s) (e.g., “Key decisions”, “Constraints/Assumptions”).
  Include the reason and any supporting evidence pointers (file paths, artifact paths, run ids).

#### In replies

- Begin with a brief “Ledger Snapshot” (Goal + Now/Next + Open Questions). Print the full ledger only when it materially
  changes or when the user asks.

#### CONTINUITY.md format (keep headings)

- Goal (incl. success criteria):
- Constraints/Assumptions:
- Key decisions:
- State/Done/Now/Next:
- Open questions (UNCONFIRMED if needed):
- Working set (files/ids/commands):

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