from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import Field

from .base import DslBaseModel


DbManifestPolicy = Literal["NONE", "VIEWS_ONLY", "VIEWS_PLUS_MATERIALIZED_VIEWS"]

DbObjectKind = Literal["VIEW", "MATERIALIZED_VIEW"]

DbApplyStatus = Literal["REUSED_EXISTING", "CREATED_NEW", "FAILED"]


class DbManifestObject(DslBaseModel):
    name: str = Field(max_length=128)
    kind: DbObjectKind
    depends_on: List[str] = Field(default_factory=list, max_length=64)
    notes: Optional[str] = Field(default=None, max_length=2000)


class DbManifestPolicyChecks(DslBaseModel):
    no_osmand_writes: Optional[bool] = None
    no_run_tables_for_prediction: Optional[bool] = None
    no_nondeterminism: Optional[bool] = None
    immutable_no_replace: Optional[bool] = None


class DbManifestApplyStatus(DslBaseModel):
    status: DbApplyStatus
    error: Optional[str] = Field(default=None, max_length=4000)
    execution_ms: Optional[int] = Field(default=None, ge=0)


class DbManifestApplyReport(DslBaseModel):
    policy: DbManifestPolicy
    theory_schema_name: str = Field(max_length=128)
    manifest_sql: str = Field(max_length=500000)
    objects: List[DbManifestObject] = Field(default_factory=list, max_length=512)
    apply_status: DbManifestApplyStatus
    policy_checks: Optional[DbManifestPolicyChecks] = None
