#!/usr/bin/env python3
"""Run headless batch simulations and print distribution summary (stdout + optional JSON file)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._teams import build_team

from app.engine.batch_analysis import run_batch


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch simulate matches for calibration evidence.")
    parser.add_argument("-n", "--count", type=int, default=100, help="Number of matches (default 100)")
    parser.add_argument("--seed-start", type=int, default=0, help="First RNG seed")
    parser.add_argument("--home-overall", type=int, default=62)
    parser.add_argument("--away-overall", type=int, default=62)
    parser.add_argument("-o", "--output", type=Path, help="Write JSON summary to this path")
    args = parser.parse_args()

    home = build_team("batch_home", "Batch Home", overall=args.home_overall)
    away = build_team("batch_away", "Batch Away", overall=args.away_overall)
    report = run_batch(home, away, count=args.count, seed_start=args.seed_start)
    summary = report.to_dict()
    summary["note"] = (
        "Shots are phase-chain attempts, not full tracking stats — "
        "typical elite matches report more attempts; see README limitations."
    )

    print(json.dumps(summary, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()