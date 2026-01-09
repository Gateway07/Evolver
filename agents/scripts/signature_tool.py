import argparse
import hashlib
import json
import re
import sys
from typing import Any, Iterable


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


_UNSAFE_SQL_PATTERNS: tuple[tuple[str, str], ...] = (
    ("semicolon", r";"),
    ("line_comment", r"--"),
    ("block_comment_start", r"/\\*"),
    ("block_comment_end", r"\\*/"),
)

_UNSAFE_SQL_KEYWORDS = (
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
)

_SQL_KEYWORDS_TO_UPPER = (
    "AND",
    "OR",
    "IN",
    "NOT",
    "NULL",
    "IS",
    "LIKE",
    "ILIKE",
    "BETWEEN",
    "EXISTS",
    "SELECT",
    "FROM",
    "WHERE",
    "ORDER",
    "BY",
    "LIMIT",
    "OFFSET",
    "JOIN",
    "INNER",
    "LEFT",
    "RIGHT",
    "FULL",
    "ON",
    "AS",
    "CASE",
    "WHEN",
    "THEN",
    "ELSE",
    "END",
)


def _split_by_sql_string_literals(sql: str) -> Iterable[tuple[bool, str]]:
    i = 0
    n = len(sql)
    in_single = False
    in_double = False
    current: list[str] = []

    def flush(is_literal: bool) -> tuple[bool, str] | None:
        if not current:
            return None
        part = "".join(current)
        current.clear()
        return (is_literal, part)

    while i < n:
        ch = sql[i]

        if in_single:
            current.append(ch)
            if ch == "'":
                if i + 1 < n and sql[i + 1] == "'":
                    current.append(sql[i + 1])
                    i += 2
                    continue
                in_single = False
            i += 1
            continue

        if in_double:
            current.append(ch)
            if ch == '"':
                if i + 1 < n and sql[i + 1] == '"':
                    current.append(sql[i + 1])
                    i += 2
                    continue
                in_double = False
            i += 1
            continue

        if ch == "'":
            flushed = flush(is_literal=False)
            if flushed is not None:
                yield flushed
            in_single = True
            current.append(ch)
            i += 1
            continue

        if ch == '"':
            flushed = flush(is_literal=False)
            if flushed is not None:
                yield flushed
            in_double = True
            current.append(ch)
            i += 1
            continue

        current.append(ch)
        i += 1

    flushed = flush(is_literal=in_single or in_double)
    if flushed is not None:
        yield flushed


def canonicalize_where_sql(sql: str, *, uppercase_keywords: bool) -> str:
    for label, pattern in _UNSAFE_SQL_PATTERNS:
        if re.search(pattern, sql):
            raise ValueError(f"Unsafe SQL: contains {label}")

    upper_sql = sql.upper()
    for kw in _UNSAFE_SQL_KEYWORDS:
        if re.search(rf"\\b{re.escape(kw)}\\b", upper_sql):
            raise ValueError(f"Unsafe SQL: contains keyword {kw}")

    collapsed = re.sub(r"\\s+", " ", sql).strip()

    if not uppercase_keywords:
        return collapsed

    keyword_pattern = r"\\b(" + "|".join(re.escape(k) for k in _SQL_KEYWORDS_TO_UPPER) + r")\\b"

    parts: list[str] = []
    for is_literal, segment in _split_by_sql_string_literals(collapsed):
        if is_literal:
            parts.append(segment)
            continue
        parts.append(re.sub(keyword_pattern, lambda m: m.group(1).upper(), segment, flags=re.IGNORECASE))

    return "".join(parts)


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
    sql_parser.add_argument("--uppercase-keywords", action="store_true", default=False)
    sql_parser.add_argument("--print-canonical", action="store_true", default=False)

    args = parser.parse_args(argv)

    raw_text = _read_text_from_file_or_stdin(file_path=args.file_path)

    if args.mode == "json":
        canonical = canonicalize_json_text(raw_text)
    elif args.mode == "sql":
        canonical = canonicalize_where_sql(raw_text, uppercase_keywords=bool(args.uppercase_keywords))
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
