from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import Field, model_validator

from .base import DslBaseModel, JsonDict


GroupDefinitionKind = Literal[
    "where_sql",
    "stratified_random_sample",
    "fixed_holdout_control",
    "fixed_feature_bin",
]


class GroupSafetyAssertions(DslBaseModel):
    """Safety assertions for group SQL snippets."""

    no_semicolons: Optional[bool] = None
    no_comments: Optional[bool] = None
    no_ddl_dml: Optional[bool] = None
    deterministic_only: Optional[bool] = None


class GroupDefinition(DslBaseModel):
    """Group definition (WHERE-suffix or protocol-defined)."""

    name: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_\-]*$",
        description="Group name.",
    )
    definition: GroupDefinitionKind
    group_sql: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=20000,
        description="SQL WHERE suffix (required when definition='where_sql').",
    )
    params: Optional[JsonDict] = Field(default=None, description="Protocol-specific parameters.")
    group_signature: Optional[str] = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    implies: Optional[List[str]] = Field(
        default=None,
        max_length=64,
        description="Signatures (sha256 hex) of other groups implied by this group.",
    )
    safety_assertions: Optional[GroupSafetyAssertions] = None
    notes: Optional[str] = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def _require_group_sql_for_where_sql(self) -> "GroupDefinition":
        if self.definition == "where_sql" and not self.group_sql:
            raise ValueError("group_sql is required when definition is 'where_sql'")
        return self
