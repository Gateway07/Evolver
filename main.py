from __future__ import annotations

import argparse
from pathlib import Path

from evolver.runner import run_iterations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parent / "config.yaml",
    )
    parser.add_argument("--iterations", type=int, default=None)

    args = parser.parse_args()

    results = run_iterations(config_path=args.config, iterations=args.iterations)

    failed = [r for r in results if r.status != "validated"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
