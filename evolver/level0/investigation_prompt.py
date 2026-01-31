from evolver.level0 import CodeEvidence


def investigate(area: str, tracing_packages: dict[str, list[str]]) -> CodeEvidence:
    """
# Mandatory code investigation + tracing grounding
You MUST NOT propose a Theory purely from data correlations. For every accepted Theory candidate, MUST follow:

## Step C1) Code investigation (required)
- Identify and inspect the code
- Output in Theory:
    - `code_evidence.targets[]`: list of files/classes/methods inspected
    - `code_evidence.observations[]`: concrete behavioral statements derived from code reading

## Step C2) Tracing confirmation (required)
- For each key Mechanism claim, run at least `{MECH_MIN_TRACING_RUNS}` traced requests and record:
    - breakpoints JSON used
    - tracing header used (deployment-specific)
    - key runtime variables observed
- The Theory MUST state at least one confirmed alignment between surrogate features and runtime variables.

## Tracing API (Discovery mechanism via runtime variables)
Use [tracing.md](../../skills/curl/tracing.md) to observe runtime variables and validate/derive experiment and theory
hypotheses without unit-tests.

### Tracing usage (required)
1. Use tracing to observe:
- actual candidate set size
- pruning threshold/topN behavior
- intermediate variables output
- ranking scores per candidate

2. Then refine DSL minimally (keep interpretability):
- add candidate count estimation
- add rule that approximates “topN pruning”
- optionally predict reason_family aligned with runtime failures

## Evaluator (Objective Measurements)

### Endpoint `GET http://localhost:8080/admin/search-test/search-by-sql`

### Request
- Body: **SQL WHERE-suffix** (e.g., `id < 100`)
- Header (required when tracing): `X-TRACING_MDC_KEY: {tracingId}`

### Response (JSON, aggregated)
Evaluator returns aggregated metrics used for scoring candidates:
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

    :param tracing_packages:dict[str, list[str]] - list of packages for tracing per project
    :param area: area of investigation
    :return: list of (full class name, method name, line of code number) tuples
    """
    pass
