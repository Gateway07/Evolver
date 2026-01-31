from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Iterable, Tuple

import yaml

SLUG = "codex-cli"

_ITERATION_ID_PATTERN = re.compile(
    r"(?im)^(?:ITERATION_ID|__ITERATION_ID__)\s*[:=]\s*(?P<id>[A-Za-z0-9_\-\.]{1,128})\s*$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_config() -> dict[str, Any]:
    config_path = _repo_root() / "config.yaml"
    with config_path.open("r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f)
    if not isinstance(loaded, dict):
        raise ValueError("config.yaml did not parse to a mapping")
    return loaded


def _resolve_working_dir(config: dict[str, Any]) -> Path:
    repo_root = _repo_root()

    working_dir_value = config.get("codex_cli", {}).get("working_dir")
    if working_dir_value is None:
        return repo_root

    if not isinstance(working_dir_value, str) or not working_dir_value.strip():
        raise ValueError("codex_cli.working_dir must be a non-empty string")

    working_dir_path = (repo_root / working_dir_value).resolve()
    repo_root_resolved = repo_root.resolve()

    try:
        working_dir_path.relative_to(repo_root_resolved)
    except ValueError as exc:
        raise ValueError(
            f"codex_cli.working_dir must be under repo root: {repo_root_resolved}"
        ) from exc

    if not working_dir_path.exists() or not working_dir_path.is_dir():
        raise ValueError(f"codex_cli.working_dir does not exist or is not a directory: {working_dir_path}")

    return working_dir_path


def _extract_iteration_id(system_prompt: str, initial_query: str) -> str | None:
    for text in (initial_query, system_prompt):
        match = _ITERATION_ID_PATTERN.search(text)
        if match:
            return match.group("id")
    return None


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


_PROMPT_PLACEHOLDER_PATTERN = re.compile(r"\{(?P<key>[A-Za-z0-9_]+)\}")


def _extract_prompt_placeholders(prompt_text: str) -> set[str]:
    return {match.group("key") for match in _PROMPT_PLACEHOLDER_PATTERN.finditer(prompt_text)}


def _resolve_prompt_params(
        *,
        required_keys: set[str],
        config: dict[str, Any],
        runtime_params: dict[str, Any] | None,
) -> dict[str, Any]:
    resolved: dict[str, Any] = {}

    prompt_defaults = config.get("codex_cli", {}).get("prompt_params")
    if prompt_defaults is None:
        prompt_defaults = {}
    if not isinstance(prompt_defaults, dict):
        raise ValueError("codex_cli.prompt_params must be a mapping")

    for key, value in prompt_defaults.items():
        resolved[str(key)] = value

    for key in required_keys:
        env_key = f"EVOLVER_PROMPT_PARAM_{key}"
        env_value = os.environ.get(env_key)
        if env_value is not None:
            resolved[key] = env_value

    if runtime_params:
        for key, value in runtime_params.items():
            resolved[str(key)] = value

    if "tracingId" in required_keys:
        tracing_id_value = resolved.get("tracingId")
        if tracing_id_value is None or (isinstance(tracing_id_value, str) and not tracing_id_value.strip()):
            resolved["tracingId"] = str(uuid.uuid4())

    missing_required = []
    for key in sorted(required_keys):
        if key not in resolved:
            missing_required.append(key)
            continue
        value = resolved[key]
        if value is None:
            missing_required.append(key)
            continue
        if isinstance(value, str) and not value.strip():
            missing_required.append(key)
            continue

    if missing_required:
        missing_str = ", ".join(missing_required)
        raise ValueError(
            "Missing required prompt parameters: "
            f"{missing_str}. Provide codex_cli.prompt_params in config.yaml, "
            "set environment variables EVOLVER_PROMPT_PARAM_<KEY>, or pass run(..., params={...})."
        )

    return resolved


def _append_prompt_params_suffix(*, prompt_text: str, required_keys: set[str], resolved_params: dict[str, Any]) -> str:
    if not required_keys:
        return prompt_text

    lines = [
        "",
        "---",
        "PROMPT_PARAMETERS (auto-generated; use these to substitute {PLACEHOLDER} tokens above):",
    ]

    for key in sorted(required_keys):
        value = resolved_params.get(key)
        if isinstance(value, (dict, list)):
            rendered_value = json.dumps(value, ensure_ascii=False)
        else:
            rendered_value = str(value)
        lines.append(f"{key}={rendered_value}")

    return prompt_text.rstrip() + "\n" + "\n".join(lines) + "\n"


def run(iteration_id: str, prompt_text: str, params: dict[str, Any] | None = None) -> Tuple[str, int]:
    config = _load_config()

    cmd = ["codex", "exec", "--json"]
    codex_executable = shutil.which(cmd[0])
    if codex_executable is None:
        raise FileNotFoundError("'codex' executable not found on PATH")

    codex_executable_path = Path(codex_executable)
    if codex_executable_path.suffix.lower() in {".cmd", ".bat"}:
        cmd = ["cmd.exe", "/c", str(codex_executable_path), *cmd[1:]]
    else:
        cmd[0] = str(codex_executable_path)

    timeout_seconds = config.get("codex_cli", {}).get("timeout_seconds")
    if not isinstance(timeout_seconds, (int, float)):
        timeout_seconds = 600

    working_dir = _resolve_working_dir(config)

    required_placeholders = _extract_prompt_placeholders(prompt_text)
    resolved_params = _resolve_prompt_params(
        required_keys=required_placeholders,
        config=config,
        runtime_params=params,
    )
    final_prompt_text = _append_prompt_params_suffix(
        prompt_text=prompt_text,
        required_keys=required_placeholders,
        resolved_params=resolved_params,
    )

    started = time.time()
    try:
        proc = subprocess.run(
            [*cmd, final_prompt_text],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
            env=os.environ.copy(),
            cwd=str(working_dir),
        )
    except subprocess.TimeoutExpired as exc:
        stderr_text = f"codex exec timed out after {timeout_seconds}s\n{exc}".strip()
        return stderr_text, 0

    elapsed_s = time.time() - started

    stdout_text = proc.stdout or ""
    stderr_text = proc.stderr or ""

    final_text = _extract_final_json_text(stdout_text)

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
