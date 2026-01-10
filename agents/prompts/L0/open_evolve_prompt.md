# OpenEvolve L0 Prompt — Counterexample Discovery + Theory Modeling (Address Search)

This prompt defines the **Level L0** OpenEvolve loop for discovering **systematic NotFound counterexamples** in an
core address-search Java application (`android`). Analyze application code to understand the search process and identify
potential sources of errors/bugs and producing the following **artifacts** as final JSON object which MUST conform to
the Pydantic root model `evolver.level0.result_output.ResultOutputEnvelope`
in [result_output.py](../../../evolver/level0/result_output.py).:
On startup, also mandatory to load:

- [osmand_ddl.md](../osmand_ddl.md)
-

## Repo map

### Project roots

- `android/` — Main Java application code for investigation and core search functionality (search index building and
  search itself).
- `tools/` — Supplementary Tools Java application code and related modules.

## Axioms (Non-negotiable)

### Axiom A0 — Canonical address universe

- `osmand.address` is the **fixed continuum** of canonical, valid addresses.

### Axiom A1 — NotFound is an application error

- Any `NotFound` result for a canonical address from `osmand.address` is **an error of the application/index**.

### Axiom A2 — Counterexamples are selected via SQL WHERE-suffix

- A “counterexample generator” is always a **valid SQL WHERE-suffix** that selects a subset of rows from
  `osmand.address`.
- The evaluator endpoint executes the suffix after `WHERE` (no full SELECT statements).
- Do NOT include `;` or any DDL/DML.

### Axiom A3 — The evaluator is the system under test

- You do not need to create unit-tests at L0.
- You measure reality via the evaluator REST endpoint (aggregated metrics + run artifacts in DB).

## Database “Test Reality” (Read-only "osmand" schema)

You have the following key objects (not exhaustive): [osmand_ddl.md](../osmand_ddl.md)

- `osmand.city(id, name, state, country, lat, lon)`
- `osmand.street(id, name, city_id, lat, lon)`
- `osmand.house(id, name, street_id, lat, lon)`
- `osmand.address` (materialized view): canonical address strings + ids + lat/lon
- `osmand.stop_word` (stop-words)
- `osmand.run` (aggregated metrics per run)
- `osmand.run_result` (per-address results: found, error, duration, etc.)

## Evaluator (Objective Measurements)

### Endpoint

`GET http://localhost:8080/admin/search-test/search-by-sql`

### Request

- Body: **SQL WHERE-suffix** (e.g., `id < 100`)
- Header (required when tracing): `X-TRACING_MDC_KEY: {tracingId}`

### Response (JSON, aggregated)

Evaluator returns aggregated metrics used for scoring L0 candidates:
`runId, error, status, totalCount, failedCount, foundCount, partialFoundCount, totalDurationMs, totalBytes, searchDurationMs`

### Derived quantities

Your goal to maximize:

1. Main objective: `notFoundRate = notFoundCount / max(totalCount, 1)` where
   `notFoundCount = totalCount - foundCount - failedCount - partialFoundCount`.
2. Cost proxies: `searchDurationMs / totalDurationMs`. Bigger `searchDurationMs` and `totalBytes` means performance
   problem and can be considered as a cost.
3. (MANDATORY) Effect size vs CONTROL under the SAME stratification:
    - `Δ = p(group) - p(control)` with a confidence interval (CI).
4. (MANDATORY) Reproducibility: stable Δ and CI support across repeated runs.

## Tracing API (Discovery mechanism via runtime variables)

Use [tracing.md](../../skills/curl/tracing.md) to observe runtime variables and validate/derive experiment and theory
hypotheses without unit-tests.

### Tracing usage

1. Use tracing to observe:

- actual candidate set size
- pruning threshold/topN behavior
- intermediate variables output
- ranking scores per candidate

2. Then refine DSL minimally (keep interpretability):

- add candidate count estimation
- add rule that approximates “topN pruning”
- optionally predict reason_family aligned with runtime failures

## Mandatory code investigation + tracing grounding (NOT OPTIONAL)

L0 MUST NOT propose a Theory purely from data correlations. For every accepted Theory candidate, MUST follow:

### Step C1) Code investigation (required)

- Identify and inspect the code
- Output in Theory:
    - `code_evidence.targets[]`: list of files/classes/methods inspected (placeholders allowed)
    - `code_evidence.observations[]`: concrete behavioral statements derived from code reading

### Step C2) Tracing confirmation (required)

- For each key Mechanism claim, run at least `{MECH_MIN_TRACING_RUNS}` traced requests and record:
    - breakpoints JSON used
    - tracing header used (deployment-specific)
    - key runtime variables observed
- The Theory MUST state at least one confirmed alignment between surrogate features and runtime variables.

## L0 Output Contract (MUST produce Experiment & Theory artifacts)

For each L0 iteration, you MUST return a single JSON object (as text) with two top-level sections:

1) **Experiment Model** (reality-backed “truth” about where the system fails)
2) **Theory Model** (a formal, executable, higher-level theory that explains *why* it fails, simpler than Java code)
   You MUST operate within the axioms, database schema, tracing workflow, application code and evaluator. See below L0
   Output Contract for more details.

### 1) Experiment (facts-observation model to answer what and where questions)

Includes:

- `group_definition`:
    - `group_sql` (canonical WHERE-suffix)
    - `group_signature` (hash of normalized group DSL/AST; REQUIRED)
    - `stratification` (e.g., by `city_id`, and optionally `state/country` splits; placeholder)
    - `implies` (list of signatures this group implies / refines; placeholder)
- `hypotheses[]` MUST be in DSL JSON form (NOT freeform SQL text):
    - Each hypothesis MUST include:
        - `hypothesis_dsl` (canonical JSON)
        - `hypothesis_signature` (hash of canonical JSON; REQUIRED)
        - `group_signature` references
        - `metric`, `claim`, `effect_size`, `ci_method`, `reproducibility_plan`
    - Purpose:
        - deduplicate hypotheses
        - build/refine an `implies` graph
        - compare “stronger/weaker” statements over time
- `acceptance_gate` results:
    - reproducibility across multiple runs
    - novelty by `res_error` clustering and/or feature-space bins
- `evaluator_metrics` (aggregated JSON from evaluator)
- `run_db_refs` (how to find the run in `osmand.run` / `osmand.run_result`; placeholder)

### 2) Theory (mechanism-explanation model to answer why question)

Includes:

- `theory_dsl` (formal, executable mechanism model; REQUIRED)
    - MAY be represented as structured JSON DSL or canonical SQL-rules DSL
    - MUST include `theory_signature = sha256(canonical(theory_dsl))`
    - MUST include `theory_name` (human-readable, sanitized slug; placeholder rules)
    - MUST include `theory_schema_name` if DB entities are created (see DB policy below)
- `theory_predictions`:
    - what features drive NotFound
    - expected monotonic relationships (e.g., collision ↑ → NotFoundRate ↑)
- `theory_validation_plan`:
    - (MANDATORY) evaluate predictive power on HOLDOUT states/countries (split policy REQUIRED)
    - (MANDATORY) avoid selection bias with a FIXED evaluation protocol independent of selected groups:
        - `holdout_control_sample`: stratified random by `city_id`
        - `holdout_feature_bins`: fixed bins (e.g., collision quantiles, token length buckets)
    - L0 MUST NOT do active “group search” on HOLDOUT; HOLDOUT is scoring-only.
- `tracing_evidence`:
    - tracingId(s), experiment runId(s)
    - key traced variables used to justify/fit the theory
    - trace log references

## Surrogate model build (REQUIRED Mechanism sub-artifact)

To prevent shallow “explanations” that do not match real runtime behavior, every Theory MUST include a **surrogate model
build** artifact that approximates (at least partially) the application’s index logic in a formal system.

The Theory output MUST include:

1) `surrogate_index` (object) with:
    - `level`: one of `{SURROGATE_LADDER_LEVELS}` (see Complexity Ladder below)
    - `feature_views`: list of surrogate feature definitions used by the mechanism
    - `invariants`: explicit claims (e.g., collision ↑ ⇒ candidate explosion ↑ ⇒ pruning risk ↑)
2) If DB materialization is used:
    - `db_materialization.policy` and `db_materialization.manifest_sql` MUST be provided (immutable build manifest)
    - `db_materialization.objects` MUST list created views/materialized views and their dependencies
3) `surrogate_validation` (object):
    - `trace_alignment`: which traced variables correlate with which surrogate features
    - `holdout_scoring`: theory metrics on holdout (scoring-only)

## Multi-objective L0 Goals (Optimize both Experiment & Theory)

L0 is a **multi-objective search**:

### Objective E (Experiment discovery quality)

Maximize:

- `notFoundRate(group)` on the selected group
- `effect_size Δ` vs a control/baseline group under the SAME stratification
- reproducibility (stable Δ and/or CI excluding 0 across repeated runs)
- novelty/coverage: new `res_error` clusters or new bins in feature-space
- cost: evaluator runtime/bytes (`searchDurationMs`, `totalBytes`)

Minimize:

- redundancy: groups that duplicate existing accepted groups

### Objective T (Theory model quality)

## Mechanism Quality Objectives (HARD REQUIREMENTS)

The Mechanism/Theory output is only admissible if it meets ALL requirements below. These are not “nice to have”; they
are acceptance gates.

### T1) Predictive generalization on HOLDOUT (required)

- The theory MUST achieve measurable predictive value on HOLDOUT data under a FIXED protocol (scoring-only holdout).
- Metrics to report (choose at least two; exact thresholds are placeholders): `{MECH_METRICS}` e.g. AUC, F1, top-k lift,
  calibration slope.
- HOLDOUT evaluation MUST NOT involve active group search or optimization. (HOLDOUT is scoring only.)

### T2) Explanatory compression / reuse (required)

- The theory MUST explain multiple accepted Reality facts using a shared feature basis:
    - at least `{MECH_MIN_FACTS_EXPLAINED}` accepted groups/hypotheses (placeholder, e.g. 3)
    - with consistent monotonicity/causal direction claims.

### T3) Tracing alignment (required)

- The theory MUST be grounded by at least `{MECH_MIN_TRACING_RUNS}` tracing sessions (placeholder, e.g. 1–3),
  and MUST demonstrate at least one validated relationship between:
    - surrogate/mechanism features (e.g., collision score, estimated candidate count) AND
    - traced runtime variables (e.g., candidate list size, pruning thresholds, normalization outputs).

### T4) Bounded interpretability (required)

- The theory MUST remain interpretable:
    - max features: `{MECH_MAX_FEATURES}` (placeholder)
    - max steps/rules: `{MECH_MAX_STEPS}` (placeholder)
- Any increase in complexity MUST be justified by improved holdout metrics and/or new reason-family coverage.

## Methodology Requirements (MUST be reflected in your candidates)

### Strict definitions + stratification (“frequent/rare”)

- “Frequent” and “rare” MUST be defined by explicit SQL-derived ranks/quantiles over the continuum.
- Stratify comparisons minimally by `city_id` (required), optionally by `state/country` for train/val/holdout split.
- Never claim “frequent vs rare” without specifying:
    - the feature (token/prefix4)
    - the statistic (count of addresses, count of occurrences)
    - the cut (topK, quantile, threshold)

### Effect size + statistical check (CI)

For each hypothesis comparing two groups A/B:

- report:
    - `pA, pB`
    - `Δ = pA - pB`
    - confidence interval for Δ (bootstrap by strata or proportion CI; placeholder)
- acceptance requires Δ to be stable and CI to support the claim (threshold placeholder).

### Group definition (SQL generator) + group_sql/signature/implies

- `group_sql` MUST be a canonical WHERE-suffix over `osmand.address` (alias `a` recommended).
- `group_signature` MUST be computed as hash(normalized group DSL/AST).
- `implies` records set inclusion/refinement relations:
    - e.g., `topK=10` implies `topK=100` if both are defined by the same ordering rule.

## Signature canonicalization rules (REQUIRED)

All signatures MUST be computed by the wrapper (not by the LLM) as: `sha256(canonical_form)`

### Canonicalization for JSON DSL (hypothesis_dsl, theory_dsl)

Used for: `hypothesis_dsl` and `theory_dsl` with these rules:

1) UTF-8 encoding.
2) Deterministic key ordering (lexicographic) at all object levels.
3) No insignificant whitespace (minified JSON).
4) Normalize numbers:
    - Use JSON numbers (not strings) when semantically numeric.
    - Disallow `NaN`, `Infinity`, `-Infinity`.
5) Normalize strings:
    - Trim leading/trailing whitespace where semantics do not require it.
    - Normalize newlines to `\n`.
6) Arrays preserve order (order is semantic). If a set is intended, sort it explicitly in the DSL.

### Canonicalization for group_sql (WHERE-suffix) and SQL-rule DSL (if used for theory_dsl)

Used for: `group_signature` with these rules:

1) Reject non-WHERE-suffix constructs:
    - No `;`, no multiple statements, no DDL/DML (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, `TRUNCATE`,
      `COPY`, `CALL`, `DO`).
    - No comments (`--`, `/*`, `*/`).
2) Normalize whitespace:
    - Collapse runs of whitespace to single spaces.
    - Trim leading/trailing whitespace.
3) Normalize keyword casing:
    - Uppercase SQL keywords (`AND`, `OR`, `IN`, `SELECT`, `FROM`, `WHERE`, `ORDER BY`, `LIMIT`, etc.).
4) Normalize identifier casing:
    - Preserve identifier case only when quoted; otherwise treat as lower-case.
5) Canonical parenthesization:
    - Preserve parentheses as written (do not attempt semantic rewriting unless AST parsing is available).
6) If the wrapper supports SQL AST parsing (preferred):
    - Canonicalize commutative boolean clauses by sorting `AND` operands (and `OR` operands) by their serialized form.
    - Canonicalize `IN (...)` lists by sorting literals when semantics permit (only for pure literal lists).

### Signature fields

- `group_signature = sha256(group_sql)`
- `hypothesis_signature = sha256(hypothesis_dsl)`
- `theory_signature = sha256(theory_dsl)`

### Accept into “reality” only reproducible and/or novel

A candidate group/hypothesis is admitted as an accepted “fact” only if:

- reproduced on multiple runs (configurable N)
- AND (new reason cluster OR new feature-space region/bin OR stronger refinement with higher effect size)

## Database write policy for L0 (schema discipline)

- The `osmand` schema is READ-ONLY for L0.
- L0 SHOULD prefer CTEs and derived queries.
- L0 MAY create new DB entities ONLY to represent and accelerate Theory (Mechanism) computation, under strict rules:
    1) New schemas MUST be separate from `osmand`, named:
        - `theory-{theory_name}-{sig8}-v{N}` (naming convention; wrapper computes N; placeholder)
    2) Schemas are IMMUTABLE once created (no CREATE OR REPLACE; no mutation).
    3) Default allowed objects: VIEW only.
        - MATERIALIZED VIEW only if explicitly enabled (placeholder) and refresh is deterministic.
    4) Theory schemas used for prediction MUST NOT depend on `osmand.run` or `osmand.run_result` (no label leakage).
    5) L0 MUST output `theory_manifest.sql` (ordered DDL for created objects) and `theory_signature`.
    6) If schema exists for same theory_signature → reuse; otherwise create a new one.

## Theory Build Budget (REQUIRED)

To keep surrogate builds practical and reproducible, every Theory that uses DB materialization MUST respect:

- Max theory schemas created per iteration: `{BUDGET_MAX_SCHEMAS}` (placeholder, e.g. 1)
- Max objects per theory schema: `{BUDGET_MAX_OBJECTS}` (placeholder, e.g. 20)
- Max materialized views per theory schema: `{BUDGET_MAX_MV}` (placeholder, e.g. 0–2)
- Each object MUST have deterministic definitions (no `now()`, no `random()`, no dependence on run tables for
  prediction).
- If performance is a concern, provide `performance_evidence`: top expensive query signatures and (optional) `EXPLAIN`
  excerpts (placeholders allowed)

## Complexity Ladder for surrogate mechanisms (REQUIRED)

Every Theory MUST declare a ladder level and SHOULD advance only when necessary.

Levels (in increasing sophistication):

#0: Pure group_sql filters over `osmand.address` (Reality only; insufficient for Mechanism acceptance by itself).
#1: Derived feature views (tokenization/normalization + prefix transforms).
#2: Frequency statistics (df/idf-like tables or views: head/tail df, min-tail-df, stop-words).
#3: Candidate-size surrogate + pruning approximation (estimated candidate explosion, top-N truncation logic).
#4: Multi-stage mechanism with reason_family mapping aligned to tracing (predicts both NotFound risk and reason
families).

Rules:

- A Theory intended for acceptance MUST be at least #1.
- To claim pruning/top-N behavior, you MUST be #3+ and show tracing alignment.

## How to Run the Example (Operational sequence)

0. (Required) Code investigation.
1. (Required) Decide surrogate ladder level (#1–4) and define surrogate features/invariants.
2. Use psql.exe to compute features/samples using CTEs/derived queries (preferred).
3. If needed for Theory acceleration, create IMMUTABLE theory schema objects (views; optional materialized views) under
   the DB write policy and build budget above.
4. Use psql.exe to generate candidate group_sql (WHERE-suffix) and CONTROL sampling SQL (stratified by city_id).
5. (Required) Call evaluator with curl.exe:
6. Repeat runs for reproducibility checks (REPEAT_RUNS).
5. Cluster res_error from osmand.run_result into reason_family (placeholder rules).
7. (Required) Tracing for Theory acceptance:

- create tracing tracingId, set breakpoints, run traced evaluator requests, fetch logs
- extract runtime variables to validate surrogate invariants and mechanism claims

7. Decide acceptance into reality:

- reproducible Δ and/or strong NotFoundRate
- plus novelty in reasons or feature-space

8. Output both artifacts (Experiment & Theory models) per the contract above.