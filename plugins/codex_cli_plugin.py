from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Tuple

import yaml


SLUG = "codex-cli"


_ITERATION_ID_PATTERN = re.compile(r"(?im)^(?:ITERATION_ID|__ITERATION_ID__)\s*[:=]\s*(?P<id>[A-Za-z0-9_\-\.]{1,128})\s*$")


@dataclass(frozen=True)
class _ArtifactsPaths:
    iteration_dir: Path
    codex_jsonl_path: Path
    codex_stderr_path: Path
    extracted_final_text_path: Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_config() -> dict[str, Any]:
    config_path = _repo_root() / "config.yaml"
    with config_path.open("r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f)
    if not isinstance(loaded, dict):
        raise ValueError("config.yaml did not parse to a mapping")
    return loaded


def _extract_iteration_id(system_prompt: str, initial_query: str) -> str | None:
    for text in (initial_query, system_prompt):
        match = _ITERATION_ID_PATTERN.search(text)
        if match:
            return match.group("id")
    return None


def _artifacts_paths(config: dict[str, Any], iteration_id: str | None) -> _ArtifactsPaths | None:
    evaluator_cfg = config.get("evaluator")
    if not isinstance(evaluator_cfg, dict):
        return None

    enable_artifacts = bool(evaluator_cfg.get("enable_artifacts", False))
    if not enable_artifacts:
        return None

    iterations_dir = evaluator_cfg.get("iterations_dir")
    if not isinstance(iterations_dir, str) or not iterations_dir:
        return None

    if not iteration_id:
        return None

    iteration_dir = (_repo_root() / iterations_dir / iteration_id).resolve()
    iteration_dir.mkdir(parents=True, exist_ok=True)

    return _ArtifactsPaths(
        iteration_dir=iteration_dir,
        codex_jsonl_path=iteration_dir / "codex.jsonl",
        codex_stderr_path=iteration_dir / "codex.stderr.txt",
        extracted_final_text_path=iteration_dir / "codex.final_text.txt",
    )


def _iter_candidate_texts(event: Any) -> Iterable[str]:
    if not isinstance(event, dict):
        return

    message = event.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            yield content

    content = event.get("content")
    if isinstance(content, str):
        yield content

    text = event.get("text")
    if isinstance(text, str):
        yield text

    output = event.get("output")
    if isinstance(output, str):
        yield output


def _extract_final_json_text(stdout_text: str) -> str:
    json_events: list[dict[str, Any]] = []

    for raw_line in stdout_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            json_events.append(parsed)

    for event in reversed(json_events):
        for candidate in _iter_candidate_texts(event):
            candidate_stripped = candidate.strip()
            if not candidate_stripped:
                continue
            try:
                parsed_candidate = json.loads(candidate_stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed_candidate, dict):
                return candidate_stripped

    return stdout_text.strip()


def run(system_prompt: str, initial_query: str, client=None, model=None) -> Tuple[str, int]:
    config = _load_config()

    iteration_id = _extract_iteration_id(system_prompt=system_prompt, initial_query=initial_query)
    artifacts = _artifacts_paths(config=config, iteration_id=iteration_id)

    cmd = config.get("codex_cli", {}).get("command")
    if not isinstance(cmd, list) or not all(isinstance(x, str) for x in cmd):
        cmd = ["codex", "exec", "--json"]

    timeout_seconds = config.get("codex_cli", {}).get("timeout_seconds")
    if not isinstance(timeout_seconds, (int, float)):
        timeout_seconds = 600

    prompt_text = f"{system_prompt}\n\n{initial_query}".strip()

    started = time.time()

    try:
        proc = subprocess.run(
            [*cmd, prompt_text],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired as exc:
        stderr_text = f"codex exec timed out after {timeout_seconds}s\n{exc}".strip()
        if artifacts:
            artifacts.codex_stderr_path.write_text(stderr_text, encoding="utf-8")
        return stderr_text, 0

    elapsed_s = time.time() - started

    stdout_text = proc.stdout or ""
    stderr_text = proc.stderr or ""

    if artifacts:
        artifacts.codex_jsonl_path.write_text(stdout_text, encoding="utf-8")
        artifacts.codex_stderr_path.write_text(stderr_text, encoding="utf-8")

    final_text = _extract_final_json_text(stdout_text)

    if artifacts:
        artifacts.extracted_final_text_path.write_text(final_text, encoding="utf-8")

    if proc.returncode != 0:
        error_payload = {
            "error": "codex_cli_failed",
            "returncode": proc.returncode,
            "elapsed_s": elapsed_s,
            "stderr_excerpt": stderr_text[-4000:],
            "stdout_excerpt": stdout_text[-4000:],
        }
        return json.dumps(error_payload, ensure_ascii=False), 0

    return final_text, 0
