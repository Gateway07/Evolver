from __future__ import annotations

from typing import Annotated, Dict, List, Literal, Optional

from pydantic import Field

from evolver.level0.base_model import DslBaseModel, JsonStrDict

SpelExpression = Annotated[
    str,
    Field(
        min_length=1,
        max_length=2000,
        description=(
            """Spring Expression Language (SpEL) expression. The evaluation context uses: root object = 'this' 
            (the intercepted instance); variables: method parameters by name; 'return' is available for AFTER 
            expressions (method result); 'throw' is available for ON_ERROR expressions (exception). The evaluated 
            value is serialized using the configured Options (container size limits, object field representation, 
            and max depth)."""
        ),
    ),
]

ObjectRepresentation = Literal[
    "PUBLIC_FIELDS",
    "DECLARED_FIELDS",
    "DECLARED_FIELDS_WITH_GETTERS",
]


class TracingOptions(DslBaseModel):
    sizeLimitPerContainerClass: Optional[Dict[str, int]] = Field(
        default=None,
        description=(
            """Container/array size limiting rules used when rendering values. Key: fully-qualified Java class name of 
            the container type (e.g. java.util.List, java.util.Map). Value semantics: if a class key is absent, the 
            adapter defaults to limiting that container class to 10 elements/entries; if present and value < 0, 
            traversal stops for that container (it is not expanded); if present and value >= 0, expansion is 
            limited to that many elements/entries."""
        ),
    )
    objectRepresentationPerClass: Optional[Dict[str, ObjectRepresentation]] = Field(
        default=None,
        description=(
            "Overrides for how specific object types are represented. Key: fully-qualified Java class name. Value: "
            "representation mode. If null or empty, the adapter uses its default object rendering strategy."
        ),
    )
    maxDepthLimit: int = Field(
        ge=0,
        le=64,
        description=(
            "Maximum traversal depth for object graphs when converting values to a JSON-safe representation. Once the "
            "depth limit is reached, nested values are truncated/stopped to avoid runaway recursion and excessive "
            "output."
        ),
    )


class BreakPoint(DslBaseModel):
    className: str = Field(
        min_length=1,
        max_length=512,
        description="Fully-qualified class name where the breakpoint applies.",
    )
    lineOfCode: int = Field(
        ge=1,
        le=2_000_000_000,
        description=(
            "Line number in the source file. Matching is tolerant (within ±1 line) to account for source/bytecode "
            "line mapping differences."
        ),
    )
    watchExpressionsBefore: Optional[List[SpelExpression]] = Field(
        default=None,
        max_length=256,
        description="SpEL expressions evaluated before the method proceeds.",
    )
    watchExpressionsAfter: Optional[List[SpelExpression]] = Field(
        default=None,
        max_length=256,
        description=(
            "SpEL expressions evaluated after the method returns successfully. Variable 'return' is available."
        ),
    )
    watchExpressionsOnError: Optional[List[SpelExpression]] = Field(
        default=None,
        max_length=256,
        description="SpEL expressions evaluated when the method throws. Variable 'throw' is available.",
    )
    ifConditionExpression: Optional[str] = Field(
        default=None,
        max_length=2000,
        description=(
            "Optional SpEL boolean expression used to decide whether this breakpoint's tracing flow is active. If "
            "null/blank, the breakpoint always passes. If evaluation fails, it is treated as false."
        ),
    )
    thenPoints: Optional[List[BreakPoint]] = Field(
        default=None,
        max_length=16,
        description=(
            "Recursive nested breakpoints. When this BreakPoint matches and passes ifConditionExpression, thenPoints "
            "become eligible for matching during the lifetime of the current scope, allowing nested (then) tracing "
            "trees."
        ),
    )
    options: TracingOptions = Field(
        description="Rendering options used when serializing watched values for this breakpoint."
    )


TracingPhase = Literal["CALL", "ERROR"]


class TracingRecord(DslBaseModel):
    phase: TracingPhase = Field(
        description=(
            "Tracing record phase. CALL indicates a normal call tracing record; ERROR indicates an error-path record."
        )
    )
    point: str = Field(
        min_length=1,
        max_length=512,
        description="Tracing point identifier (typically the class name).",
    )
    lineOfCode: int = Field(ge=1, le=2_000_000_000)
    ifCondition: bool = Field(
        description=(
            "Whether the breakpoint's ifConditionExpression evaluated to true for this record (i.e., whether the "
            "tracing flow was active)."
        )
    )
    watchesBefore: Optional[JsonStrDict] = Field(
        default=None,
        description="Map from watch expression string to its rendered value (or evaluation error message).",
    )
    watchesAfter: Optional[JsonStrDict] = Field(
        default=None,
        description="Map from watch expression string to its rendered value (or evaluation error message).",
    )
    watchesOnError: Optional[JsonStrDict] = Field(
        default=None,
        description="Map from watch expression string to its rendered value (or evaluation error message).",
    )
    stackTrace: Optional[str] = Field(
        default=None,
        max_length=200000,
        description="Stack trace captured when an exception is thrown (null if no exception).",
    )
    errorMessage: Optional[str] = Field(
        default=None,
        max_length=20000,
        description="Exception message captured when an exception is thrown (null if no exception).",
    )
    timestampMs: int = Field(ge=0, description="Record timestamp in milliseconds since epoch.")
    durationMs: int = Field(ge=0, description="Duration of the intercepted call in milliseconds.")
    thenTracings: Optional[List[TracingRecord]] = Field(
        default=None,
        max_length=10,
        description=(
            "Nested tracing records produced by matching thenPoints within the open scope created by this breakpoint."
        ),
    )


class TracingSession(DslBaseModel):
    tracing_id: str = Field(max_length=16)
    breakpoints: List[BreakPoint] = Field(
        default_factory=list,
        max_length=16,
        description=(
            "Configured tracing breakpoints for the run. Each BreakPoint can contain nested thenPoints (recursive) "
            "to represent conditional sub-traces that should only be captured when the parent BreakPoint was matched "
            "and its ifConditionExpression evaluated to true."
        ),
    )
    tracings: List[TracingRecord] = Field(
        default_factory=list,
        max_length=100000,
        description=(
            "Collected runtime tracing records for the run. Entries can be nested via thenTracings to reflect the "
            "runtime nesting caused by matching a BreakPoint with thenPoints."
        ),
    )
