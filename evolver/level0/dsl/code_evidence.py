from __future__ import annotations

from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel, Field

EvidenceKind = Literal[
    "file_range",  # file + line range
    "symbol",  # Class/Method/Field reference
    "snippet",  # snippet code with location (file + lines + code)
    "commit",  # commit hash
    "note"  # textual note only
]


class CodeEvidenceItem(BaseModel):
    kind: EvidenceKind = Field(
        ...,
        description=(
            "Type of evidence pointer (file range, symbol reference, snippet, commit, or note)."
        ),
    )
    repo_path: Optional[str] = Field(
        default=None,
        max_length=512,
        description="Repository-relative path when evidence refers to code in this repo.",
    )
    file: Optional[str] = Field(
        default=None,
        max_length=512,
        description="File path for the evidence (relative or absolute, depending on producer).",
    )
    symbol: Optional[str] = Field(
        default=None,
        max_length=256,
        description=(
            "Qualified symbol reference (e.g., package.module.Class.method) when kind='symbol'."
        ),
    )
    line_range: Optional[Tuple[int, int]] = Field(
        default=None,
        description="Inclusive (start_line, end_line) range for file evidence when applicable.",
    )
    code: Optional[str] = Field(
        default=None,
        max_length=4000,
        description="Code snippet text when kind='snippet' (optionally with surrounding context).",
    )
    commit: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Commit hash when kind='commit'.",
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional confidence score for this evidence pointer (0..1).",
    )


class CodeEvidenceObservation(BaseModel):
    claim: str = Field(
        min_length=1,
        max_length=4000,
        description=(
            "Suspicion claim describing why this component is relevant to the investigated failure mode."
        ),
    )
    evidence: List[CodeEvidenceItem] = Field(
        min_length=1,
        max_length=16,
        description="Concrete pointers supporting the claim (file ranges, symbols, snippets, commits, notes).",
    )


class CodeEvidence(BaseModel):
    investigation_area: str = Field(..., min_length=1, max_length=128,
                                    description="Human-readable scope of investigation.")
    tracing_packages: List[str] = Field(..., min_length=1, max_length=256,
                                        description="Instrumented code packages to enable runtime tracing collection.")
    suspicious_components: List[CodeEvidenceObservation] = Field(min_length=1, max_length=32,
                                                                 description="List of suspicious classes/modules/methods with rationale and pointers (file paths, symbols).")
