from __future__ import annotations

from typing import Any, Dict, List, Literal, Tuple, Optional

from pydantic import BaseModel, Field, constr

# ----------------------------
# Scoring
# ----------------------------

EffectType = Literal[
    "difference_of_proportions",
    "ratio_of_proportions",
    "odds_ratio",
    "log_odds_ratio",
    "difference_in_means",
    "ratio_of_means",
    "log_ratio_of_means",
]

EffectAggregation = Literal[
    "pooled_over_repeats",
    "mean_of_run_rates",
    "median_of_run_rates",
    "weighted_by_control_total",
    "macro_average",
    "worst_stratum",
    "holdout_primary",
]


class EffectSizeConfig(BaseModel):
    type: EffectType = Field("difference_of_proportions", description="Effect size computation type.")
    primary_comparison: Literal["treatment_vs_control"] = Field("treatment_vs_control")
    aggregation: EffectAggregation = Field("pooled_over_repeats",
                                           description="Aggregation strategy across repeats/strata/partitions.")
    metric: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Metric name used for effect size (e.g., notFoundRate, failedRate, meanSearchMs).",
    )


class EffectSizeReport(BaseModel):
    config: EffectSizeConfig
    p_treatment: Optional[float] = Field(default=None, description="Treatment rate (for proportion metrics).")
    p_control: Optional[float] = Field(default=None, description="Control rate (for proportion metrics).")
    delta: Optional[float] = Field(default=None,
                                   description="Difference (treatment - control) for difference-type effects.")
    ratio: Optional[float] = Field(default=None, description="Ratio (treatment/control) for ratio-type effects.")
    repeat_runs_used: int = Field(..., ge=0, description="Number of repeats used in aggregation.")


class ConfidenceIntervalConfig(BaseModel):
    method: Literal["bootstrap_by_strata", "wilson", "normal_approx"] = Field("bootstrap_by_strata", min_length=1,
                                                                              max_length=128, description="CI method.")
    confidence: int = Field(0.95, gt=0.5, lt=1.0, description="Confidence level (e.g., 0.95).")
    resamples: Optional[int] = Field(2000, ge=100, le=200000, description="Bootstrap resamples if applicable.")
    seed: int = Field(1337, ge=0, le=2 ** 31 - 1,
                      description="Seed used for CI computation if stochastic method is used (must be fixed).")
    require_ci_excludes_zero_for_accept: bool = Field(True)


class ConfidenceIntervalReport(BaseModel):
    config: ConfidenceIntervalConfig
    low: float = Field(..., description="Lower bound.")
    high: float = Field(..., description="Upper bound.")


class ReproducibilityConfig(BaseModel):
    require_repeats: int = Field(3, ge=1, le=50)
    require_same_direction_all_repeats: bool = Field(True)
    max_allowed_repeat_variance: int = Field(0.04, ge=0.0, le=1.0)


class NoveltyConfig(BaseModel):
    enabled: bool = Field(True)
    required: bool = Field(True)
    sources: List[Literal["reason_family_clusters", "feature_region_bins", "high_failure_strata"]] = Field(...,
                                                                                                           description="Sources of novelty")
    min_new_reason_fraction: float = Field(0.05, ge=0.0, le=1.0)
    min_new_region_fraction: float = Field(0.05, ge=0.0, le=1.0)
    top_k_to_report: float = Field(8, ge=1, le=100)


class NoveltyReport(BaseModel):
    config: NoveltyConfig
    score: float = Field(...,
                         description="Deterministic novelty score derived from new reason families / new regions.", )
    passes_gate: bool = Field(..., description="Whether novelty gate passed under stable_gates.")
    new_reason_fraction: Optional[float] = Field(None,
                                                 description="Fraction of failures belonging to new reason families.")
    new_region_fraction: Optional[float] = Field(None, description="Fraction of failures in new feature-space regions.")
    new_reason_families: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Top new reason-family ids with counts.",
    )
    new_feature_regions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Top new region ids with counts.",
    )
    new_high_failure_strata: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="New high-failure (state/city_bin) strata.",
    )


class ComplexityPenaltyConfig(BaseModel):
    max_objects: int = Field(12, ge=0, le=10_000)
    max_joins_per_group_sql: int = Field(4, ge=0, le=50)
    max_manifest_kb: int = Field(64, ge=1, le=1024)


class ComplexityPenaltyReport(BaseModel):
    config: ComplexityPenaltyConfig
    objects_created_count: int = Field(...,
                                       description="Count of created objects (views, materialization views, tables)")
    created_views_count: int = Field(..., description="Count of created views")
    created_mv_count: int = Field(..., description="Count of created materialization views")
    created_tables_count: int = Field(..., description="Count of created tables")
    manifest_size_kb: int = Field(..., description="Size of manifest in KB")
    estimated_join_complexity: int = Field(..., description="joins per group_sql")
    estimated_query_cost_class: Literal["LOW", "MED", "HIGH"] = Field(..., description="LOW/MED/HIGH or numeric")
    passes_complexity_gate: bool = Field(..., description="Whether complexity gate passed under penalty gates.")
    penalty_score: float = Field(..., description="Penalty score based on surrogate/manifest complexity penalty.")


class TraceAlignmentConfig(BaseModel):
    required: bool = Field(True)
    min_correlation: float = Field(0.2, ge=-1.0, le=1.0)
    compare_features_to_trace_keys: List[
        Tuple[constr(min_length=1, max_length=64), constr(min_length=1, max_length=128)]] = Field(
        default_factory=list,
        description="Pairs like ('df_head', 'candidate_streets_count').",
    )


class TraceAlignmentReport(BaseModel):
    config: TraceAlignmentConfig
    correlation_stats: Dict[str, Any] = Field(
        default_factory=dict,
        description="Correlation stats for each feature (correlations/contrasts).",
    )


class MechanismConfig(BaseModel):
    enabled: bool = Field(True)
    required: bool = Field(True)
    min_holdout_lift_topk: float = Field(1.2, gt=0.0, le=1000.0)


class MechanismReport(BaseModel):
    config: MechanismConfig
    mechanism_total_score: float = Field(..., description="Deterministic combined score for mechanism quality.")
    passes_mechanism_gate: bool = Field(..., description="Whether mechanism gate passed under stable_gates.")
    holdout_lift_topk: Optional[float] = Field(None, description="Top-K lift on holdout for theory risk score.")
    trace_alignment: TraceAlignmentReport = Field(...,
                                                  description="Trace alignment metrics (correlations/contrasts).")
    complexity_penalty: Optional[ComplexityPenaltyReport] = Field(None,
                                                                  description="Penalty based on surrogate/manifest complexity.")


class RankingConfig(BaseModel):
    rank_score_formula: str = Field(..., min_length=4, max_length=512,
                                    description="Documented stable formula (string) for scalar ranking used by wrapper.",
                                    )
    tie_breakers: List[str] = Field(min_length=1, max_length=64)
    rounding_decimals: int = Field(4, ge=0, le=8)


class RankingReport(BaseModel):
    config: RankingConfig
    rank_score: float = Field(..., description="Stable scalar rank score computed by wrapper for best selection.")


class ScoringConfig(BaseModel):
    effect_size: EffectSizeConfig
    confidence_intervals: ConfidenceIntervalConfig
    reproducibility: ReproducibilityConfig

    novelty: NoveltyConfig
    mechanism: MechanismConfig
    complexity_penalty: ComplexityPenaltyConfig
    trace_alignment: TraceAlignmentConfig

    ranking: RankingConfig


class Scoring(BaseModel):
    effect_sizes: List[EffectSizeReport] = Field(
        default_factory=list,
        description="Effect size summaries for selected metrics.",
    )
    confidence_intervals: List[ConfidenceIntervalReport] = Field(
        default_factory=list,
        description="Confidence intervals matching effect sizes.",
    )
    novelty: Optional[NoveltyReport] = Field(default=None, description="Novelty scoring summary.")
    mechanism: Optional[MechanismReport] = Field(default=None, description="Mechanism quality scoring summary.")
    ranking: RankingReport = Field(..., description="Scalar ranking.")
