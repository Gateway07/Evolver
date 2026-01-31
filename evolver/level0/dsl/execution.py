from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict

from evolver.level0.dsl.proposal import ProposalResult
from evolver.level0.dsl.scoring import Scoring, ScoringConfig
from evolver.level0.dsl.tracing import TracingSession


# ----------------------------
# Protocol (splits / sampling / control)
# ----------------------------

class SplitsConfig(BaseModel):
    """Split definition for experiment partitions."""
    type: str = Field("state_bins", description="TEST / VALIDATION / HOLDOUT")
    bins: str = Field(..., description="State code used for split bin (e.g. CA).")
    split_sql_template: str = Field(
        ...,
        description="Template producing split predicate for a given bin (wrapper expands {{STATE}}).",
    )


StrataBy = Literal["none", "city_id_bins", "state_bins"]


class StratificationConfig(BaseModel):
    """Deterministic stratification policy."""
    enabled: bool = Field(True)
    by: StrataBy = Field("city_id_bins")
    bins_count: int = Field(32, ge=1, le=1024)
    min_per_bin: int = Field(10, ge=0, le=1000000)
    max_per_bin: int = Field(60, ge=0, le=1000000)


class SamplingConfig(BaseModel):
    """Deterministic sampling and repeat policy."""

    sample_size: int = Field(1000, ge=1, le=1_000_000)
    seed: int = Field(1337, ge=0, le=2 ** 31 - 1)
    repeats: int = Field(3, ge=1, le=50)
    stratification: StratificationConfig


ControlPolicy = Literal["uniform_random_from_eligible_population"]


class ControlConfig(BaseModel):
    """Wrapper-generated control cohort semantics."""

    control_policy: ControlPolicy = Field("uniform_random_from_eligible_population")
    control_group_name_template: str = Field("CONTROL_uniform_{SPLIT}", min_length=1, max_length=128)
    control_sql: str = Field(
        "TRUE", min_length=1, max_length=4000,
        description="WHERE-suffix used for control cohort selection (eligibility+split still applied).",
    )


class ProtocolConfig(BaseModel):
    """End-to-end experiment protocol."""

    splits: SplitsConfig
    sampling: SamplingConfig
    control: ControlConfig


# ----------------------------
# Evaluator
# ----------------------------

class EvaluatorConfig(BaseModel):
    """REST evaluator endpoint configuration."""

    locale_parameter_name: str = Field("locale", min_length=1, max_length=64)
    evaluator_version: str = Field("v1", min_length=1, max_length=64)


# ----------------------------
# Tracing
# ----------------------------

class TracingConfig(BaseModel):
    """Tracing policy (header name + budgets + default keys)."""

    enabled: bool = Field(True)
    required: bool = Field(True)
    max_tracing_requests: int = Field(12, ge=0, le=10_000)
    trace_budget_ms: int = Field(20000, ge=0, le=600_000)


# ----------------------------
# Acceptance
# ----------------------------

class AcceptanceConfig(BaseModel):
    min_delta_notFoundRate: float = Field(0.05, ge=0.0, le=1.0)
    max_allowed_failedRate_increase: float = Field(0.10, ge=0.0, le=1.0)
    require_ci_excludes_zero: bool = Field(True)
    require_novelty: bool = Field(True)
    require_mechanism: bool = Field(True)
    require_holdout_confirm: bool = Field(True)
    stop_when_ready: bool = Field(True)


# ----------------------------
# Logging
# ----------------------------

LogEvent = Literal[
    "execute.start",
    "db_apply.start",
    "db_apply.done",
    "db_apply.fail",
    "evaluator.run.start",
    "evaluator.run.done",
    "evaluator.run.fail",
    "tracing.start",
    "tracing.done",
    "tracing.fail",
    "scoring.done",
    "decision.done",
    "execute.finish",
]


class LoggingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    structured_json_logs: bool = Field(True)
    log_dir_template: str = Field("runs/{iteration_id}/logs", min_length=1, max_length=256)
    artifact_dir_template: str = Field("runs/{iteration_id}/artifacts", min_length=1, max_length=256)
    events: List[LogEvent] = Field(default_factory=list)
    max_error_text_len: int = Field(2048, ge=128, le=100000)


class GatesConfig(BaseModel):
    """
    Immutable gates config used by wrapper execute().

    Key properties:
    - Wrapper-owned and deterministic
    - Includes experiment protocol, evaluator/tracing config, scoring + acceptance, and logging
    """
    version: str = Field("gates_v1", min_length=1, max_length=64)

    protocol: ProtocolConfig
    evaluator: EvaluatorConfig
    tracing: TracingConfig

    scoring: ScoringConfig
    acceptance: AcceptanceConfig
    logging: LoggingConfig


EvaluatorRunStatus = Literal["RUNNING", "COMPLETED", "FAILED"]


class EvaluatorRun(BaseModel):
    run_id: int
    status: EvaluatorRunStatus
    totalCount: int = Field(ge=0)
    failedCount: int = Field(ge=0)
    foundCount: int = Field(ge=0)
    partialFoundCount: int = Field(ge=0)
    totalDurationMs: int = Field(ge=0)
    totalBytes: int = Field(ge=0)
    searchDurationMs: int = Field(ge=0)
    error: Optional[str] = Field(default=None, max_length=4000)
    notFoundCount: int = Field(ge=0)
    notFoundRate: float = Field(ge=0, le=1)


class ExecutionEvidence(BaseModel):
    db_apply_report: Dict[str, Any] = Field(
        default_factory=dict,
        description="Result of applying db_manifest (created objects, errors, timings).",
    )
    evaluator_runs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Evaluator bundle output (aggregated metrics per cohort/stratum/repeat).",
    )
    tracing_sessions: List[TracingSession] = Field(
        default_factory=dict,
        description="Tracing bundle output (extracted variable tracings, breakpoint hit stats).",
    )


class Decision(BaseModel):
    status: Literal["ACCEPTED", "REJECTED", "ERROR"] = Field(..., description="High-level decision outcome.")
    is_ready: bool = Field(..., description="Stop condition for the loop: true if candidate meets acceptance criteria.")
    primary_reason: str = Field(..., min_length=1, max_length=256,
                                description="Deterministic primary reason for accept/reject (e.g., holdout_not_confirmed, safety_rejected).", )
    evidence: ExecutionEvidence
    score: Scoring = Field(...,
                           description="Per-gate evaluation results (effect, CI, novelty, mechanism, holdout, reproducibility).", )


class Experiment(BaseModel):
    round_index: int = Field(..., ge=1, description="Round index related in main loop logic.")
    iteration_id: str = Field(..., min_length=1, max_length=64,
                              description="Correlation id for tracing and evaluator calls.")
    proposal: ProposalResult
    decision: Decision
    best_index: Optional[int] = Field(..., description="Ref by round index to the best experiment.")
