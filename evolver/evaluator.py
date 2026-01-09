from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from jsonschema import RefResolver
from jsonschema.validators import validator_for
from evolver.models import L1OutputEnvelope

from evolver.config import AppConfig, abs_path, load_config, repo_root_from_config_path


_FORBIDDEN_SQL_TOKENS = {
    "DROP",
    "DELETE",
    "UPDATE",
    "INSERT",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "COPY",
    "CALL",
    "DO",
}

_SQL_KEYWORDS = {
    "AND",
    "OR",
    "IN",
    "IS",
    "NULL",
    "NOT",
    "EXISTS",
    "SELECT",
    "FROM",
    "WHERE",
    "ORDER",
    "BY",
    "LIMIT",
    "JOIN",
    "LEFT",
    "RIGHT",
    "INNER",
    "OUTER",
    "ON",
    "AS",
    "DISTINCT",
    "GROUP",
    "HAVING",
    "CASE",
    "WHEN",
    "THEN",
    "ELSE",
    "END",
    "LIKE",
    "ILIKE",
    "BETWEEN",
}


@dataclass(frozen=True)
class EvaluationResult:
    envelope: L1OutputEnvelope
    validated_json: dict[str, Any]
    iteration_id: str
    iteration_dir: Path | None


class EvaluationError(RuntimeError):
    pass


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _tokenize_sql(sql: str) -> list[str]:
    tokens: list[str] = []
    i = 0
    n = len(sql)

    while i < n:
        ch = sql[i]
        if ch.isspace():
            i += 1
            continue

        if ch == "\"":
            j = i + 1
            while j < n:
                if sql[j] == "\"" and sql[j - 1] != "\\":
                    j += 1
                    break
                j += 1
            tokens.append(sql[i:j])
            i = j
            continue

        if ch == "'":
            j = i + 1
            while j < n:
                if sql[j] == "'":
                    j += 1
                    if j < n and sql[j] == "'":
                        j += 1
                        continue
                    break
                j += 1
            tokens.append(sql[i:j])
            i = j
            continue

        if ch.isalpha() or ch == "_":
            j = i + 1
            while j < n and (sql[j].isalnum() or sql[j] == "_"):
                j += 1
            tokens.append(sql[i:j])
            i = j
            continue

        if ch.isdigit():
            j = i + 1
            while j < n and (sql[j].isdigit() or sql[j] in ".eE+-"):
                j += 1
            tokens.append(sql[i:j])
            i = j
            continue

        tokens.append(ch)
        i += 1

    return tokens


def canonical_sql_where_suffix(where_suffix: str) -> str:
    if ";" in where_suffix:
        raise ValueError("group_sql must not contain ';'")

    if "--" in where_suffix or "/*" in where_suffix or "*/" in where_suffix:
        raise ValueError("group_sql must not contain SQL comments")

    upper = where_suffix.upper()
    for token in _FORBIDDEN_SQL_TOKENS:
        if re.search(rf"\b{re.escape(token)}\b", upper):
            raise ValueError(f"group_sql must not contain DDL/DML keyword: {token}")

    tokens = _tokenize_sql(where_suffix)
    normalized_tokens: list[str] = []

    for tok in tokens:
        if tok.startswith("\"") and tok.endswith("\"") and len(tok) >= 2:
            normalized_tokens.append(tok)
            continue
        if tok.startswith("'") and tok.endswith("'") and len(tok) >= 2:
            normalized_tokens.append(tok)
            continue

        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", tok):
            upper_tok = tok.upper()
            if upper_tok in _SQL_KEYWORDS:
                normalized_tokens.append(upper_tok)
            else:
                normalized_tokens.append(tok.lower())
            continue

        normalized_tokens.append(tok)

    out_parts: list[str] = []
    for part in normalized_tokens:
        if not out_parts:
            out_parts.append(part)
            continue

        prev = out_parts[-1]
        if prev in ("(", ","):
            out_parts.append(part)
        elif part in (")", ","):
            out_parts.append(part)
        else:
            out_parts.append(" " + part)

    return "".join(out_parts).strip()


def _load_schema_store(schema_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    store: dict[str, Any] = {}
    root_schema: dict[str, Any] | None = None

    for schema_path in schema_dir.glob("*.schema.json"):
        schema_obj = json.loads(schema_path.read_text(encoding="utf-8"))
        if not isinstance(schema_obj, dict):
            continue

        schema_id = schema_obj.get("$id")
        if isinstance(schema_id, str) and schema_id:
            store[schema_id] = schema_obj

        store[schema_path.name] = schema_obj

        if schema_path.name == "l1_output.schema.json":
            root_schema = schema_obj

    if root_schema is None:
        raise FileNotFoundError("l1_output.schema.json not found in schema_dir")

    return root_schema, store


def _validate_jsonschema(instance: dict[str, Any], schema_dir: Path) -> None:
    root_schema, store = _load_schema_store(schema_dir)
    Validator = validator_for(root_schema)

    resolver = RefResolver.from_schema(root_schema, store=store)
    validator = Validator(root_schema, resolver=resolver)

    errors = sorted(validator.iter_errors(instance), key=lambda e: e.path)
    if errors:
        first = errors[0]
        raise EvaluationError(f"Schema validation failed at {list(first.path)}: {first.message}")


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_registry_entry(index_path: Path, entry: dict[str, Any]) -> None:
    if index_path.exists():
        existing = json.loads(index_path.read_text(encoding="utf-8"))
        if not isinstance(existing, list):
            existing = []
    else:
        existing = []

    existing.append(entry)
    _ensure_dir(index_path.parent)
    _write_json(index_path, existing)


def _update_state_summary(summary_path: Path, iteration_id: str, status: str) -> None:
    now_utc = datetime.now(timezone.utc).isoformat()

    if summary_path.exists():
        existing = json.loads(summary_path.read_text(encoding="utf-8"))
        if not isinstance(existing, dict):
            existing = {}
    else:
        existing = {}

    total = existing.get("total_iterations")
    if not isinstance(total, int):
        total = 0

    existing["last_iteration_id"] = iteration_id
    existing["last_status"] = status
    existing["last_updated_utc"] = now_utc
    existing["total_iterations"] = total + 1

    _ensure_dir(summary_path.parent)
    _write_json(summary_path, existing)


def _record_iteration_status(
    *,
    repo_root: Path,
    config: AppConfig,
    iteration_id: str,
    timestamp_utc: str | None,
    status: str,
    iteration_dir: Path | None,
    error: str | None = None,
    stage: str | None = None,
) -> None:
    if not config.evaluator.enable_artifacts:
        return

    index_path = abs_path(repo_root, config.evaluator.iterations_index)
    summary_path = abs_path(repo_root, config.evaluator.state_summary)

    artifacts_payload: dict[str, str] = {}
    if iteration_dir is not None:
        artifacts_payload["iteration_dir"] = str(iteration_dir)

        for optional_name in (
            "prompt.messages.json",
            "optillm.response.json",
            "optillm.assistant_text.txt",
            "codex.jsonl",
            "codex.stderr.txt",
            "codex.final_text.txt",
            "l1_output.raw.json",
            "l1_output.validated.json",
            "validation.report.json",
            "evaluation.error.txt",
        ):
            optional_path = iteration_dir / optional_name
            if optional_path.exists():
                artifacts_payload[optional_name] = str(optional_path)

    registry_entry: dict[str, Any] = {
        "iter_id": iteration_id,
        "timestamp_utc": timestamp_utc,
        "status": status,
        "artifacts": artifacts_payload,
    }
    if stage:
        registry_entry["stage"] = stage
    if error:
        registry_entry["error"] = error

    _append_registry_entry(index_path, registry_entry)
    _update_state_summary(summary_path, iteration_id=iteration_id, status=status)


def _iter_groups(container: Any) -> Iterable[dict[str, Any]]:
    if not isinstance(container, dict):
        return

    if isinstance(container.get("group_catalog"), list):
        for g in container["group_catalog"]:
            if isinstance(g, dict):
                yield g

    hypotheses = container.get("hypotheses")
    if isinstance(hypotheses, list):
        for h in hypotheses:
            if not isinstance(h, dict):
                continue
            groups = h.get("groups")
            if isinstance(groups, list):
                for g in groups:
                    if isinstance(g, dict):
                        yield g


def _compute_and_fill_signatures(envelope: dict[str, Any]) -> None:
    experiment = envelope.get("experiment")
    theory = envelope.get("theory")

    if not isinstance(experiment, dict) or not isinstance(theory, dict):
        return

    signatures_hypotheses_by_id: dict[str, str] = {}
    signatures_groups_by_name: dict[str, str] = {}
    signatures_theories_by_id: dict[str, str] = {}

    hypotheses = experiment.get("hypotheses")
    if isinstance(hypotheses, list):
        for h in hypotheses:
            if not isinstance(h, dict):
                continue
            hypothesis_id = h.get("hypothesis_id")
            if isinstance(hypothesis_id, str) and hypothesis_id:
                hypothesis_for_hash = dict(h)
                hypothesis_for_hash.pop("signatures", None)
                hyp_sig = _sha256_hex(canonical_json(hypothesis_for_hash))
                signatures_hypotheses_by_id[hypothesis_id] = hyp_sig
                h.setdefault("signatures", {})
                if isinstance(h["signatures"], dict):
                    h["signatures"].setdefault("hypothesis_signature", hyp_sig)

            for g in _iter_groups({"hypotheses": [h]}):
                name = g.get("name")
                if not isinstance(name, str) or not name:
                    continue

                if g.get("definition") == "where_sql" and isinstance(g.get("group_sql"), str):
                    group_sig = _sha256_hex(canonical_sql_where_suffix(g["group_sql"]))
                    g.setdefault("group_signature", group_sig)
                    signatures_groups_by_name[name] = group_sig

    for g in _iter_groups(experiment):
        name = g.get("name")
        if not isinstance(name, str) or not name:
            continue
        if g.get("definition") == "where_sql" and isinstance(g.get("group_sql"), str):
            group_sig = _sha256_hex(canonical_sql_where_suffix(g["group_sql"]))
            g.setdefault("group_signature", group_sig)
            signatures_groups_by_name[name] = group_sig

    theories = theory.get("theories")
    if isinstance(theories, list):
        for t in theories:
            if not isinstance(t, dict):
                continue
            theory_dsl = t.get("theory_dsl")
            if not isinstance(theory_dsl, dict):
                continue
            theory_id = theory_dsl.get("theory_id")
            if not isinstance(theory_id, str) or not theory_id:
                continue

            theory_for_hash = dict(theory_dsl)
            theory_for_hash.pop("signatures", None)
            theory_sig = _sha256_hex(canonical_json(theory_for_hash))
            signatures_theories_by_id[theory_id] = theory_sig
            theory_dsl.setdefault("signatures", {})
            if isinstance(theory_dsl["signatures"], dict):
                theory_dsl["signatures"].setdefault("theory_signature", theory_sig)

    envelope["signature_report"] = {
        "schema_version": "1.0",
        "canonicalization_version": "v1",
        "signatures": {
            "hypotheses": [
                {"hypothesis_id": hypothesis_id, "hypothesis_signature": signature}
                for hypothesis_id, signature in sorted(signatures_hypotheses_by_id.items())
            ],
            "groups": [
                {"name": name, "group_signature": signature}
                for name, signature in sorted(signatures_groups_by_name.items())
            ],
            "theories": [
                {"theory_id": theory_id, "theory_signature": signature}
                for theory_id, signature in sorted(signatures_theories_by_id.items())
            ],
        },
    }


def evaluate_l1_output(
    l1_json_text: str,
    *,
    config_path: Path | None = None,
    iteration_id: str | None = None,
) -> EvaluationResult:
    if config_path is None:
        config_path = Path(__file__).resolve().parent / "config.yaml"

    config: AppConfig = load_config(config_path)
    repo_root = repo_root_from_config_path(config_path)

    if iteration_id is None:
        iteration_id = ""

    iteration_dir: Path | None = None
    if config.evaluator.enable_artifacts and iteration_id:
        iteration_dir = abs_path(repo_root, config.evaluator.iterations_dir) / iteration_id
        _ensure_dir(iteration_dir)

    try:
        parsed = json.loads(l1_json_text)
    except json.JSONDecodeError as exc:
        error_text = f"Final output is not valid JSON: {exc}"
        if iteration_dir is not None:
            (iteration_dir / "evaluation.error.txt").write_text(error_text, encoding="utf-8")
            (iteration_dir / "validation.report.json").write_text(
                json.dumps(
                    {"status": "failed", "iter_id": iteration_id, "stage": "json_parse", "error": error_text},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        if iteration_id:
            _record_iteration_status(
                repo_root=repo_root,
                config=config,
                iteration_id=iteration_id,
                timestamp_utc=None,
                status="failed",
                iteration_dir=iteration_dir,
                error=error_text,
                stage="json_parse",
            )
        raise EvaluationError(error_text) from exc

    if not isinstance(parsed, dict):
        error_text = "Final output must be a JSON object"
        if iteration_dir is not None:
            (iteration_dir / "evaluation.error.txt").write_text(error_text, encoding="utf-8")
            (iteration_dir / "validation.report.json").write_text(
                json.dumps(
                    {"status": "failed", "iter_id": iteration_id, "stage": "type_check", "error": error_text},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        if iteration_id:
            _record_iteration_status(
                repo_root=repo_root,
                config=config,
                iteration_id=iteration_id,
                timestamp_utc=None,
                status="failed",
                iteration_dir=iteration_dir,
                error=error_text,
                stage="type_check",
            )
        raise EvaluationError(error_text)

    if not iteration_id:
        iteration = parsed.get("iteration")
        if isinstance(iteration, dict) and isinstance(iteration.get("id"), str):
            iteration_id = iteration["id"]

    if not iteration_id:
        raise EvaluationError("iteration_id is required (either argument or iteration.id in JSON)")

    if config.evaluator.enable_artifacts and iteration_dir is None:
        iteration_dir = abs_path(repo_root, config.evaluator.iterations_dir) / iteration_id
        _ensure_dir(iteration_dir)

    if iteration_dir is not None:
        _write_json(iteration_dir / "l1_output.raw.json", parsed)

    timestamp_utc: str | None = None
    iteration_obj = parsed.get("iteration")
    if isinstance(iteration_obj, dict) and isinstance(iteration_obj.get("timestamp_utc"), str):
        timestamp_utc = iteration_obj["timestamp_utc"]

    try:
        _compute_and_fill_signatures(parsed)

        schema_dir = abs_path(repo_root, config.schemas.l1_schema_dir)
        _validate_jsonschema(parsed, schema_dir=schema_dir)

        envelope = L1OutputEnvelope.model_validate(parsed)
    except Exception as exc:  # noqa: BLE001
        error_text = str(exc)
        if iteration_dir is not None:
            (iteration_dir / "evaluation.error.txt").write_text(error_text, encoding="utf-8")
            (iteration_dir / "validation.report.json").write_text(
                json.dumps(
                    {"status": "failed", "iter_id": iteration_id, "stage": "validation", "error": error_text},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

        _record_iteration_status(
            repo_root=repo_root,
            config=config,
            iteration_id=iteration_id,
            timestamp_utc=timestamp_utc,
            status="failed",
            iteration_dir=iteration_dir,
            error=error_text,
            stage="validation",
        )

        raise EvaluationError(error_text) from exc

    if iteration_dir is not None:
        _write_json(iteration_dir / "l1_output.validated.json", parsed)

        validation_report = {
            "status": "validated",
            "iter_id": iteration_id,
            "schema_root": config.schemas.l1_root_schema,
            "schema_dir": str(schema_dir),
        }
        _write_json(iteration_dir / "validation.report.json", validation_report)

        artifacts_payload: dict[str, str] = {
            "iteration_dir": str(iteration_dir),
            "raw": str(iteration_dir / "l1_output.raw.json"),
            "validated": str(iteration_dir / "l1_output.validated.json"),
            "validation_report": str(iteration_dir / "validation.report.json"),
        }

        for optional_name in (
            "prompt.messages.json",
            "optillm.response.json",
            "optillm.assistant_text.txt",
            "codex.jsonl",
            "codex.stderr.txt",
            "codex.final_text.txt",
        ):
            optional_path = iteration_dir / optional_name
            if optional_path.exists():
                artifacts_payload[optional_name] = str(optional_path)

        registry_entry = {
            "iter_id": iteration_id,
            "timestamp_utc": envelope.iteration.timestamp_utc,
            "status": "validated",
            "artifacts": artifacts_payload,
        }

        _append_registry_entry(abs_path(repo_root, config.evaluator.iterations_index), registry_entry)
        _update_state_summary(abs_path(repo_root, config.evaluator.state_summary), iteration_id=iteration_id, status="validated")

    return EvaluationResult(
        envelope=envelope,
        validated_json=parsed,
        iteration_id=iteration_id,
        iteration_dir=iteration_dir,
    )
