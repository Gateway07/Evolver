import argparse
import hashlib
import json
import re
import sys
from typing import Any


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normalize_newlines_in_json(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("\r\n", "\n").replace("\r", "\n")
    if isinstance(value, list):
        return [_normalize_newlines_in_json(v) for v in value]
    if isinstance(value, dict):
        return {k: _normalize_newlines_in_json(v) for k, v in value.items()}
    return value


def canonicalize_json_text(json_text: str) -> str:
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    parsed = _normalize_newlines_in_json(parsed)

    return json.dumps(
        parsed,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )


def canonicalize_where_sql(sql: str) -> str:
    upper_sql = sql.upper()

    collapsed = re.sub(r"\\s+", " ", upper_sql).strip()
    return collapsed


def _read_text_from_file_or_stdin(*, file_path: str | None) -> str:
    if file_path:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return sys.stdin.read()


def _write_output(text: str, *, output_path: str | None) -> None:
    if output_path:
        with open(output_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return
    sys.stdout.write(text)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Compute sha256(canonical_form) for JSON DSL or SQL WHERE-suffix")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    json_parser = subparsers.add_parser("json", help="Canonicalize JSON and compute sha256")
    json_parser.add_argument("--file", dest="file_path", default=None)
    json_parser.add_argument("--out", dest="out_path", default=None)
    json_parser.add_argument("--print-canonical", action="store_true", default=False)

    sql_parser = subparsers.add_parser("sql", help="Canonicalize SQL WHERE-suffix and compute sha256")
    sql_parser.add_argument("--file", dest="file_path", default=None)
    sql_parser.add_argument("--out", dest="out_path", default=None)
    sql_parser.add_argument("--print-canonical", action="store_true", default=False)

    args = parser.parse_args(argv)

    raw_text = _read_text_from_file_or_stdin(file_path=args.file_path)

    if args.mode == "json":
        canonical = canonicalize_json_text(raw_text)
    elif args.mode == "sql":
        canonical = canonicalize_where_sql(raw_text)
    else:
        raise ValueError(f"Unknown mode: {args.mode}")

    digest = _sha256_hex(canonical.encode("utf-8"))

    if getattr(args, "print_canonical", False):
        payload = json.dumps({"sha256": digest, "canonical": canonical}, ensure_ascii=False, indent=2)
        _write_output(payload + "\n", output_path=args.out_path)
        return 0

    _write_output(digest + "\n", output_path=args.out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
