from __future__ import annotations

from typing import List

from pydantic import Field

from .base import DslBaseModel


class HypothesisSignatureEntry(DslBaseModel):
    hypothesis_id: str = Field(max_length=128)
    hypothesis_signature: str = Field(pattern=r"^[a-f0-9]{64}$")


class GroupSignatureEntry(DslBaseModel):
    name: str = Field(max_length=128)
    group_signature: str = Field(pattern=r"^[a-f0-9]{64}$")


class TheorySignatureEntry(DslBaseModel):
    theory_id: str = Field(max_length=128)
    theory_signature: str = Field(pattern=r"^[a-f0-9]{64}$")


class SignatureReportSignatures(DslBaseModel):
    hypotheses: List[HypothesisSignatureEntry]
    groups: List[GroupSignatureEntry]
    theories: List[TheorySignatureEntry]


class SignatureReport(DslBaseModel):
    schema_version: str = Field(pattern=r"^[0-9]+\.[0-9]+$")
    canonicalization_version: str = Field(min_length=1, max_length=64)
    signatures: SignatureReportSignatures
