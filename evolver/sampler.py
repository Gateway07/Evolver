from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from evolver.config import AppConfig, abs_path


_JSON_BLOCK_RE = re.compile(r"(?s)~~~json\s*(\{.*?\})\s*~~~")


@dataclass(frozen=True)
class IterationContext:
    iteration_id: str
    locale: str
    timestamp_utc: str


class PromptSampler(Protocol):
    def build_messages(self, *, config: AppConfig, repo_root: Path, ctx: IterationContext) -> list[dict[str, str]]:
        ...


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_state_summary(repo_root: Path, config: AppConfig) -> dict[str, Any] | None:
    summary_path = abs_path(repo_root, config.evaluator.state_summary)
    if not summary_path.exists():
        return None
    try:
        parsed = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _extract_seed_json_example(seed_markdown: str) -> str | None:
    match = _JSON_BLOCK_RE.search(seed_markdown)
    if not match:
        return None
    candidate = match.group(1).strip()
    if not candidate:
        return None
    return candidate


def _build_system_prompt(*, config: AppConfig, repo_root: Path) -> str:
    constitution_path = abs_path(repo_root, config.prompt.constitution_path)
    base_prompt_path = abs_path(repo_root, config.prompt.initial_prompt_path)

    constitution = _read_text(constitution_path)
    base_prompt = _read_text(base_prompt_path)

    return f"{constitution}\n\n{base_prompt}".strip()


def _build_user_prompt(*, config: AppConfig, repo_root: Path, ctx: IterationContext) -> str:
    state_summary = _load_state_summary(repo_root=repo_root, config=config)
    state_text = ""
    if config.prompt.include_artifacts and state_summary is not None:
        state_text = json.dumps(state_summary, ensure_ascii=False, indent=2)

    seed_examples: list[str] = []
    for seed_path_text in config.prompt.seed_examples:
        seed_path = abs_path(repo_root, seed_path_text)
        if not seed_path.exists():
            continue
        seed_md = _read_text(seed_path)
        seed_json = _extract_seed_json_example(seed_md)
        if seed_json:
            seed_examples.append(seed_json)

    seed_block = ""
    if seed_examples:
        seed_block = "\n\n".join(
            [
                "SEED_EXAMPLE_JSON (in-context example only; do not copy placeholders verbatim):\n" + s
                for s in seed_examples
            ]
        )

    return (
        "You are running one OpenEvolve L1 iteration.\n\n"
        f"ITERATION_ID: {ctx.iteration_id}\n"
        f"timestamp_utc: {ctx.timestamp_utc}\n"
        f"locale: {ctx.locale}\n\n"
        "Return ONLY a single JSON object as text that validates against agents/prompts/L1/dsl/l1_output.schema.json and sibling schemas.\n"
        "All signature fields must be present but will be overwritten by the wrapper if needed.\n"
        + ("\nState summary (from artifacts/state/summary.json):\n" + state_text + "\n" if state_text else "")
        + ("\n" + seed_block + "\n" if seed_block else "")
    ).strip()


class DefaultPromptSampler:
    def build_messages(self, *, config: AppConfig, repo_root: Path, ctx: IterationContext) -> list[dict[str, str]]:
        system_prompt = _build_system_prompt(config=config, repo_root=repo_root)
        user_prompt = _build_user_prompt(config=config, repo_root=repo_root, ctx=ctx)

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]


def new_iteration_context(*, iteration_id: str, locale: str) -> IterationContext:
    return IterationContext(
        iteration_id=iteration_id,
        locale=locale,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
    )
