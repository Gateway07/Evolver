from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import Field

from .base import DslBaseModel
from .ci_report import CiReport
from .db_manifest import DbManifestApplyReport
from .evaluator_run import EvaluatorRun
from .group_definition import GroupDefinition
from .hypothesis import Hypothesis
from .signature_report import SignatureReport
from .theory import Theory
from .tracing_session import TracingSession


class IterationInfo(DslBaseModel):
    id: str = Field(min_length=1, max_length=128)
    timestamp_utc: datetime
    locale: str = Field(min_length=1, max_length=64)
    prompt_ref: Optional[str] = Field(default=None, max_length=512)
    notes: Optional[str] = Field(default=None, max_length=20000)


class ExperimentInfo(DslBaseModel):
    hypotheses: List[Hypothesis] = Field(min_length=1, max_length=64)
    group_catalog: List[GroupDefinition] = Field(min_length=1, max_length=256)
    tracing_session: TracingSession = Field(
        description="Tracing sessions; mandatory when tracing is used."
    )


class TheoryInfo(DslBaseModel):
    theories: List[Theory] = Field(min_length=1, max_length=16)


class ResultOutputEnvelope(DslBaseModel):
    schema_version: str = Field(pattern=r"^[0-9]+\.[0-9]+$")
    iteration: IterationInfo
    experiment: ExperimentInfo
    theory: TheoryInfo
    signature_report: SignatureReport
    evaluator_runs: List[EvaluatorRun] = Field(min_length=1, max_length=100000)
    ci_report: CiReport
    db_manifest: DbManifestApplyReport
