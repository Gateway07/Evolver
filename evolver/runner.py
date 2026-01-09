from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from evolver import evaluator as evaluator_module
from evolver.config import AppConfig, abs_path, load_config, repo_root_from_config_path
from evolver.sampler import DefaultPromptSampler, new_iteration_context


@dataclass(frozen=True)
class RunResult:
    iteration_id: str
    status: str
    iteration_dir: Path | None


class OptiLLMError(RuntimeError):
    pass


def _post_chat_completions(*, config: AppConfig, messages: list[dict[str, str]]) -> dict[str, Any]:
    url = config.optillm.base_url.rstrip("/") + config.optillm.chat_completions_path

    payload: dict[str, Any] = {
        "model": config.optillm.model,
        "messages": messages,
    }

    last_error: Exception | None = None
    for attempt in range(max(config.optillm.max_retries, 0) + 1):
        try:
            resp = requests.post(url, json=payload, timeout=config.optillm.timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, dict):
                raise OptiLLMError("OptiLLM response is not a JSON object")
            return data
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= config.optillm.max_retries:
                break
            time.sleep(0.5 * (attempt + 1))

    raise OptiLLMError(str(last_error))


def _extract_assistant_content(chat_response: dict[str, Any]) -> str:
    choices = chat_response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise OptiLLMError("Missing choices in chat response")

    choice0 = choices[0]
    if not isinstance(choice0, dict):
        raise OptiLLMError("choices[0] is not an object")

    message = choice0.get("message")
    if not isinstance(message, dict):
        raise OptiLLMError("choices[0].message is not an object")

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise OptiLLMError("choices[0].message.content is missing or empty")

    return content


def _iteration_id_for_index(index: int) -> str:
    return f"l1_round_{index:04d}"


def run_iterations(*, config_path: Path, iterations: int | None = None) -> list[RunResult]:
    config = load_config(config_path)
    repo_root = repo_root_from_config_path(config_path)

    sampler = DefaultPromptSampler()

    max_iters = config.open_evolve.max_iterations if iterations is None else iterations

    results: list[RunResult] = []

    for i in range(1, max_iters + 1):
        iteration_id = _iteration_id_for_index(i)
        ctx = new_iteration_context(iteration_id=iteration_id, locale=config.open_evolve.locale)

        messages = sampler.build_messages(config=config, repo_root=repo_root, ctx=ctx)

        chat_response = _post_chat_completions(config=config, messages=messages)
        assistant_text = _extract_assistant_content(chat_response)

        iteration_dir: Path | None = None
        if config.evaluator.enable_artifacts:
            iteration_dir = abs_path(repo_root, config.evaluator.iterations_dir) / iteration_id
            iteration_dir.mkdir(parents=True, exist_ok=True)
            (iteration_dir / "prompt.messages.json").write_text(
                json.dumps(messages, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (iteration_dir / "optillm.response.json").write_text(
                json.dumps(chat_response, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (iteration_dir / "optillm.assistant_text.txt").write_text(assistant_text, encoding="utf-8")

        try:
            evaluation = evaluator_module.evaluate_l1_output(
                assistant_text,
                config_path=config_path,
                iteration_id=iteration_id,
            )
            results.append(
                RunResult(iteration_id=iteration_id, status="validated", iteration_dir=evaluation.iteration_dir))
        except Exception as exc:  # noqa: BLE001
            if iteration_dir is not None:
                (iteration_dir / "evaluation.error.txt").write_text(str(exc), encoding="utf-8")
            results.append(RunResult(iteration_id=iteration_id, status="failed", iteration_dir=iteration_dir))

    return results
