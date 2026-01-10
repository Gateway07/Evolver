from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import Field

from .base import DslBaseModel, JsonDict
from .group_definition import GroupDefinition


HypothesisType = Literal[
    "DIFF_RATE",
    "RATE_THRESHOLD",
    "RATIO",
    "MONOTONIC_TREND",
    "RANK_ORDER",
    "MULTI_GROUP",
]

HypothesisMetric = Literal[
    "notFoundRate",
    "foundRate",
    "failedRate",
    "partialFoundRate",
    "totalDurationMs",
    "searchDurationMs",
    "totalBytes",
]

EffectSizeType = Literal[
    "difference_of_proportions",
    "ratio_of_proportions",
    "odds_ratio",
    "trend_slope",
]

CiMethod = Literal[
    "bootstrap_by_strata",
    "wilson_score",
    "normal_approx",
    "clopper_pearson",
    "custom",
]

NoveltyKind = Literal["reason_family", "feature_bin", "region"]

ExpectedEffectDirection = Literal["increase", "decrease", "no_change", "unknown"]


class HypothesisScope(DslBaseModel):
    app_version: Optional[str] = Field(default=None, max_length=128)
    index_build_id: Optional[str] = Field(default=None, max_length=128)
    locale: Optional[str] = Field(default=None, max_length=64)
    notes: Optional[str] = Field(default=None, max_length=4000)


class HypothesisGroupRoles(DslBaseModel):
    treatment: Optional[str] = None
    control: Optional[str] = None
    baseline: Optional[str] = None
    comparators: Optional[List[str]] = None


class HypothesisStratification(DslBaseModel):
    stratify_by: List[str] = Field(min_length=1)
    split_policy: Optional[JsonDict] = None
    control_protocol: Optional[JsonDict] = None


class HypothesisClaimCompare(DslBaseModel):
    group_a: str
    group_b: str


class HypothesisClaim(DslBaseModel):
    compare: Optional[HypothesisClaimCompare] = None
    delta_min: Optional[float] = None
    delta_max: Optional[float] = None
    rate_min: Optional[float] = Field(default=None, ge=0, le=1)
    rate_max: Optional[float] = Field(default=None, ge=0, le=1)
    confidence_level: float = Field(default=0.95, ge=0.5, le=0.999)
    notes: Optional[str] = Field(default=None, max_length=4000)


class HypothesisEvaluationEffectSize(DslBaseModel):
    type: EffectSizeType
    definition: Optional[str] = Field(default=None, max_length=4000)


class HypothesisEvaluationCiBootstrap(DslBaseModel):
    resamples: int = Field(default=2000, ge=100, le=20000)
    seed: Optional[int] = None


class HypothesisEvaluationCi(DslBaseModel):
    method: CiMethod
    bootstrap: Optional[HypothesisEvaluationCiBootstrap] = None
    notes: Optional[str] = Field(default=None, max_length=4000)


class HypothesisEvaluationReproducibility(DslBaseModel):
    repeat_runs: int = Field(ge=1, le=50)
    accept_if_ci_supports_claim: bool = True
    notes: Optional[str] = Field(default=None, max_length=4000)


class HypothesisEvaluationAcceptanceGate(DslBaseModel):
    require_novelty: bool = False
    novelty_kind: Optional[List[NoveltyKind]] = None
    notes: Optional[str] = Field(default=None, max_length=4000)


class HypothesisEvaluation(DslBaseModel):
    effect_size: HypothesisEvaluationEffectSize
    ci: HypothesisEvaluationCi
    reproducibility: HypothesisEvaluationReproducibility
    acceptance_gate: Optional[HypothesisEvaluationAcceptanceGate] = None


class HypothesisExpectedEffect(DslBaseModel):
    direction: Optional[ExpectedEffectDirection] = None
    min_effect_size: Optional[float] = None
    notes: Optional[str] = Field(default=None, max_length=2000)


class HypothesisSignatures(DslBaseModel):
    hypothesis_signature: Optional[str] = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class Hypothesis(DslBaseModel):
    schema_version: str = Field(pattern=r"^[0-9]+\.[0-9]+$")
    hypothesis_id: str = Field(min_length=1, max_length=128)
    type: HypothesisType
    axioms: List[str] = Field(min_length=1)
    metric: HypothesisMetric
    groups: List[GroupDefinition] = Field(min_length=1, max_length=8)
    stratification: HypothesisStratification
    claim: HypothesisClaim
    evaluation: HypothesisEvaluation

    scope: Optional[HypothesisScope] = None
    feature_family: Optional[str] = Field(default=None, max_length=128)
    group_roles: Optional[HypothesisGroupRoles] = None
    expected_effect: Optional[HypothesisExpectedEffect] = None
    signatures: Optional[HypothesisSignatures] = None
