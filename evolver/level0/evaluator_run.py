from __future__ import annotations

from typing import Dict, List, Literal, Optional, Union

from pydantic import Field

from .base import DslBaseModel, JsonStrDict


EvaluatorRequestMethod = Literal["GET"]

EvaluatorRunStatus = Literal["RUNNING", "COMPLETED", "FAILED"]


class EvaluatorRunRequest(DslBaseModel):
    method: EvaluatorRequestMethod
    url: str = Field(max_length=512)
    get_with_body: Literal[True]
    body_where_suffix: str = Field(max_length=20000)
    headers: Optional[JsonStrDict] = None


class EvaluatorRunResponseAggregates(DslBaseModel):
    status: EvaluatorRunStatus
    totalCount: int = Field(ge=0)
    failedCount: int = Field(ge=0)
    foundCount: int = Field(ge=0)
    partialFoundCount: int = Field(ge=0)
    totalDurationMs: int = Field(ge=0)
    totalBytes: int = Field(ge=0)
    searchDurationMs: int = Field(ge=0)
    error: Optional[str] = Field(default=None, max_length=4000)


class EvaluatorRunDerived(DslBaseModel):
    notFoundCount: int = Field(ge=0)
    notFoundRate: float = Field(ge=0, le=1)


class EvaluatorRun(DslBaseModel):
    run_id: Union[int, str]
    group_name: str = Field(max_length=128)
    request: EvaluatorRunRequest
    response_aggregates: EvaluatorRunResponseAggregates
    derived: EvaluatorRunDerived
