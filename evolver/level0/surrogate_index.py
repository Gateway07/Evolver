from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import Field

from .base import DslBaseModel


LadderLevel = Literal["L1", "L2", "L3", "L4"]


class SurrogateBuildBudget(DslBaseModel):
    max_objects: int = Field(ge=1, le=1000)
    max_materialized_views: int = Field(ge=0, le=50)
    notes: Optional[str] = Field(default=None, max_length=2000)


class SurrogatePerformanceEvidence(DslBaseModel):
    expensive_queries: Optional[List[str]] = Field(default=None, max_length=32)
    explain_refs: Optional[List[str]] = Field(default=None, max_length=32)


class SurrogateIndex(DslBaseModel):
    ladder_level: LadderLevel
    theory_schema_name: str = Field(min_length=1, max_length=128)
    objects_used: List[str] = Field(min_length=1, max_length=256)
    invariants: List[str] = Field(min_length=1, max_length=128)
    build_budget: SurrogateBuildBudget
    performance_evidence: Optional[SurrogatePerformanceEvidence] = None
