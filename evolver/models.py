from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class IterationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    timestamp_utc: str
    locale: str
    prompt_ref: str | None = None
    notes: str | None = None


class ExperimentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hypotheses: list[dict[str, Any]]
    group_catalog: list[dict[str, Any]]
    tracing_session: dict[str, Any]


class TheoryContainerModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theories: list[dict[str, Any]]


class L1OutputEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    iteration: IterationModel
    experiment: ExperimentModel
    theory: TheoryContainerModel
    signature_report: dict[str, Any]
    evaluator_runs: list[dict[str, Any]]
    ci_report: dict[str, Any]
    db_manifest: dict[str, Any]
