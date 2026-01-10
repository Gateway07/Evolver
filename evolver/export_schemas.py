from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Type

from evolver.level0.l1_output import L1OutputEnvelope
from pydantic import BaseModel


def export_model_schema(
        *,
        model: Type[BaseModel],
        output_file: Path,
        overwrite: bool,
) -> Path:
    schema: Dict[str, Any] = model.model_json_schema()

    output_file.parent.mkdir(parents=True, exist_ok=True)

    if output_file.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {output_file}")

    output_file.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_file


def _default_output_dir() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    return repo_root / "agents" / "prompts" / "L1" / "dsl"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export JSON Schemas from evolver.dsl Pydantic models.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_default_output_dir(),
        help="Directory to write schema files to.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing schema files.",
    )

    args = parser.parse_args(argv)

    output_file = args.output_dir / "l1_output.schema.json"
    export_model_schema(model=L1OutputEnvelope, output_file=output_file, overwrite=args.overwrite)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
