from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class OptiLLMConfig(BaseModel):
    base_url: str
    chat_completions_path: str = "/chat/completions"
    model: str
    timeout_seconds: float = 120
    max_retries: int = 2


class CodexCliConfig(BaseModel):
    command: list[str] = Field(default_factory=lambda: ["codex", "exec", "--json"])
    timeout_seconds: float = 600


class SchemasConfig(BaseModel):
    l1_schema_dir: str
    l1_root_schema: str


class EvaluatorConfig(BaseModel):
    enable_artifacts: bool = True
    artifacts_dir: str = "artifacts"
    iterations_dir: str = "artifacts/iterations"
    iterations_index: str = "artifacts/iterations/index.json"
    state_dir: str = "artifacts/state"
    state_summary: str = "artifacts/state/summary.json"


class PromptConfig(BaseModel):
    initial_prompt_path: str
    constitution_path: str
    include_artifacts: bool = True
    seed_examples: list[str] = Field(default_factory=list)


class OpenEvolveConfig(BaseModel):
    max_iterations: int = 10
    locale: str = "en_US"
    seed: int = 1337


class AppConfig(BaseModel):
    optillm: OptiLLMConfig
    codex_cli: CodexCliConfig
    schemas: SchemasConfig
    evaluator: EvaluatorConfig
    prompt: PromptConfig
    open_evolve: OpenEvolveConfig


def load_config(config_path: Path) -> AppConfig:
    with config_path.open("r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f)
    if not isinstance(loaded, dict):
        raise ValueError("config.yaml did not parse to a mapping")
    return AppConfig.model_validate(loaded)


def repo_root_from_config_path(config_path: Path) -> Path:
    return config_path.resolve().parent


def abs_path(repo_root: Path, path_text: str) -> Path:
    candidate = Path(path_text)
    if candidate.is_absolute():
        return candidate
    return (repo_root / candidate).resolve()


def ensure_config_paths_exist(config: AppConfig, repo_root: Path) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    checks["prompt.initial_prompt_path"] = abs_path(repo_root, config.prompt.initial_prompt_path).exists()
    checks["prompt.constitution_path"] = abs_path(repo_root, config.prompt.constitution_path).exists()
    schema_dir = abs_path(repo_root, config.schemas.l1_schema_dir)
    checks["schemas.l1_schema_dir"] = schema_dir.exists()
    checks["schemas.l1_root_schema"] = (schema_dir / config.schemas.l1_root_schema).exists()
    return checks
