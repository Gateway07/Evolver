from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import Field

from .base import DslBaseModel


CodeTargetKind = Literal["java", "kotlin", "gradle", "other"]

EvidenceType = Literal["code_snippet_ref", "symbol_ref", "commit_ref", "note"]


class CodeEvidenceTarget(DslBaseModel):
    kind: CodeTargetKind
    repo_path: str = Field(min_length=1, max_length=512)
    symbols: Optional[List[str]] = Field(default=None, max_length=128)
    commit: Optional[str] = Field(default=None, max_length=64)
    notes: Optional[str] = Field(default=None, max_length=4000)


class CodeEvidenceItem(DslBaseModel):
    type: EvidenceType
    file: Optional[str] = Field(default=None, max_length=512)
    symbol: Optional[str] = Field(default=None, max_length=256)
    lines: Optional[str] = Field(default=None, max_length=64)
    text: Optional[str] = Field(default=None, max_length=4000)


class CodeObservationLinks(DslBaseModel):
    surrogate_objects: Optional[List[str]] = None
    mechanism_features: Optional[List[str]] = None
    tracing_variables: Optional[List[str]] = None


class CodeEvidenceObservation(DslBaseModel):
    id: str = Field(max_length=64)
    claim: str = Field(min_length=1, max_length=4000)
    evidence: List[CodeEvidenceItem] = Field(min_length=1, max_length=16)
    links: Optional[CodeObservationLinks] = None


class CodeEvidence(DslBaseModel):
    targets: List[CodeEvidenceTarget] = Field(min_length=1, max_length=64)
    observations: List[CodeEvidenceObservation] = Field(min_length=1, max_length=256)
