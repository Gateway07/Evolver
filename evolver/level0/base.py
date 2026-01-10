from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from pydantic.config import ConfigDict


class DslBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @classmethod
    def json_schema(cls) -> Dict[str, Any]:
        return cls.model_json_schema()


class DslAllowExtraModel(DslBaseModel):
    model_config = ConfigDict(extra="allow")


JsonDict = Dict[str, Any]
JsonStrDict = Dict[str, str]

UtcDateTime = datetime
