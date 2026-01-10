from __future__ import annotations

from typing import Dict, List, Literal, Optional, Union

from pydantic import Field

from .base import DslAllowExtraModel, DslBaseModel, JsonDict
from .code_evidence import CodeEvidence
from .db_manifest import DbManifestApplyReport
from .surrogate_index import SurrogateIndex


TheoryType = Literal["RULE_MODEL", "SCORING_MODEL", "SQL_RULES", "PIPELINE_MODEL"]

InputValueType = Literal["string", "int", "float", "bool", "json"]

FeatureValueType = Literal["string", "int", "float", "bool"]

ModelOutput = Literal[
    "predict_notfound",
    "predict_reason_family",
    "risk_score",
    "candidate_count_est",
]

ValidationMetric = Literal[
    "AUC",
    "F1",
    "precision",
    "recall",
    "brier",
    "calibration_slope",
    "topk_lift",
]


class TheoryInput(DslBaseModel):
    name: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    source: str = Field(max_length=256)
    type: Optional[InputValueType] = None
    notes: Optional[str] = Field(default=None, max_length=2000)


class TheoryFeature(DslBaseModel):
    expr: str = Field(min_length=1, max_length=20000)
    type: FeatureValueType
    notes: Optional[str] = Field(default=None, max_length=2000)


class TheoryModelComplexity(DslBaseModel):
    num_features: int = Field(ge=1, le=1024)
    num_steps: int = Field(ge=1, le=1024)
    description: Optional[str] = Field(default=None, max_length=2000)


class TheoryModel(DslBaseModel):
    outputs: List[ModelOutput] = Field(min_length=1)
    logic: List[JsonDict] = Field(min_length=1, max_length=256)
    parameters: Optional[Dict[str, Union[float, str, bool]]] = None
    complexity: TheoryModelComplexity


class TheoryValidation(DslBaseModel):
    protocol: JsonDict
    metrics: List[ValidationMetric] = Field(min_length=1)
    acceptance: JsonDict


class TheorySignatures(DslBaseModel):
    theory_signature: Optional[str] = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class TheoryDsl(DslBaseModel):
    schema_version: str = Field(pattern=r"^[0-9]+\.[0-9]+$")
    theory_id: str = Field(min_length=1, max_length=128)
    theory_name: str = Field(min_length=1, max_length=64)
    theory_type: TheoryType
    axioms: List[str] = Field(min_length=1)
    scope: JsonDict
    inputs: List[TheoryInput] = Field(min_length=1, max_length=64)
    features: Dict[str, TheoryFeature] = Field(min_length=1)
    model: TheoryModel
    validation: TheoryValidation
    signatures: Optional[TheorySignatures] = None


class TheoryTracingLinks(DslBaseModel):
    tracing_plan_ref: Optional[str] = Field(default=None, max_length=512)
    tracing_sessions_ref: Optional[str] = Field(default=None, max_length=512)


class Theory(DslBaseModel):
    theory_dsl: TheoryDsl
    code_evidence: CodeEvidence
    surrogate_index: SurrogateIndex
    db_materialization: DbManifestApplyReport
    tracing_links: Optional[TheoryTracingLinks] = None
