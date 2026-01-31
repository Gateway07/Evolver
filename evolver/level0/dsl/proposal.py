from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Proposal(BaseModel):
    name: str = Field(
        ..., min_length=1, max_length=256, description="Human-readable name for this proposal."
    )


class Hypothesis(Proposal):
    dsl: Dict[str, Any] = Field(
        ...,
        description=(
            "Canonical hypothesis DSL JSON describing claim, metrics, expected effect, "
            "and links to group/theory."
        ),
    )


class QueryDefinition(Proposal):
    group_sql: str = Field(
        ...,
        min_length=1,
        max_length=20000,
        description=(
            "Canonical concrete address cohort selector expressed as a SQL WHERE-suffix "
            "predicate over alias 'a' (osmand.address)."
        ),
    )


class Theory(Proposal):
    dsl: Dict[str, Any] = Field(
        ...,
        description=(
            "Canonical Theory DSL (JSON) defining surrogate objects, features, risk score "
            "expressions, and claims."
        ),
    )
    schema_name: Optional[str] = Field(
        default=None,
        max_length=512,
        description=(
            "Versioned schema name derived by wrapper: 'theory${schema_name}${sig[:8]}$vN'."
        ),
    )
    manifest_sql: List[str] = Field(
        default_factory=list,
        max_length=512,
        description="SQL DDL/DML statements that create surrogate objects in the schema.",
    )
    query_defs: List[QueryDefinition] = Field(
        default_factory=list,
        max_length=256,
        description="Treatment query definitions (WHERE-suffix SQL).",
    )


class TracingPlan(Proposal):
    breakpoints: List[Dict[str, Any]] = Field(default_factory=list, max_length=256,
                                              description="Structured breakpoint requests (class/method, condition, captured vars).", )
    budget: Dict[str, Any] = Field(
        default_factory=dict,
        description="Limits for tracing calls (max requests, max duration).",
    )


class ProposalResult(BaseModel):
    hypotheses: List[Hypothesis] = Field(
        default_factory=list,
        max_length=16,
        description="Hypotheses list proposed in this round.",
    )
    theory: Theory = Field(...,
                           description="Mechanism theory explaining failure mode + surrogate feature specification.")
    tracing_plan: TracingPlan = Field(..., description="Tracing plan intent for runtime variable extraction.")
