from __future__ import annotations

from typing import List, Optional, Union

from pydantic import Field

from .base import DslBaseModel, JsonDict


class CiReportEffectSize(DslBaseModel):
    type: str = Field(max_length=64)
    value: float
    definition: Optional[str] = Field(default=None, max_length=4000)


class CiReportCi(DslBaseModel):
    level: float = Field(ge=0.5, le=0.999)
    low: float
    high: float
    method: str = Field(max_length=64)
    params: Optional[JsonDict] = None


class CiReportReproducibility(DslBaseModel):
    repeat_runs: int = Field(ge=1, le=50)
    run_ids: List[Union[int, str]] = Field(min_length=1)
    variance_notes: Optional[str] = Field(default=None, max_length=4000)


class CiReportDecision(DslBaseModel):
    accepted: bool
    reason: str = Field(max_length=4000)


class CiReportEntry(DslBaseModel):
    hypothesis_id: str = Field(max_length=128)
    metric: str = Field(max_length=64)
    effect_size: CiReportEffectSize
    ci: CiReportCi
    reproducibility: CiReportReproducibility
    decision: CiReportDecision


class CiReport(DslBaseModel):
    schema_version: str = Field(pattern=r"^[0-9]+\.[0-9]+$")
    entries: List[CiReportEntry] = Field(min_length=1, max_length=256)
