"""
CLI Interface
=============
Simple command-line wrapper around :class:`~fact_checker.FactCheckerEngine`.

Usage::

    python -m fact_checker.cli "Water boils at 100 degrees Celsius."
    python -m fact_checker.cli --json "The sun is a planet."
"""

from __future__ import annotations

import argparse
import json
import sys

from . import FactCheckerEngine
from .facts_db import Fact


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fact-checker",
        description=(
            "Ethical Fact Checker Engine – facts over semantics.\n\n"
            "Check one or more claims against a structured fact database."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "claims",
        nargs="+",
        metavar="CLAIM",
        help="One or more claims to fact-check (quote multi-word claims).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output results as a JSON array.",
    )
    parser.add_argument(
        "--no-strict-ethics",
        action="store_true",
        default=False,
        help=(
            "Treat ethics failures as warnings rather than blocking verdicts. "
            "NOT recommended for production use."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    engine = FactCheckerEngine(strict_ethics=not args.no_strict_ethics)

    results = [engine.check(claim) for claim in args.claims]

    if args.json:
        print(json.dumps([r.as_dict() for r in results], indent=2))
    else:
        for result in results:
            _print_result(result)

    # Return non-zero exit code if any claim was not verified
    if any(r.verdict in ("FALSE", "REFUSED", "ERROR") for r in results):
        return 1
    return 0


def _print_result(result) -> None:
    verdict_symbols = {
        "TRUE": "✅",
        "LIKELY": "🟡",
        "FALSE": "❌",
        "UNCERTAIN": "❓",
        "REFUSED": "🚫",
        "ERROR": "💥",
    }
    symbol = verdict_symbols.get(result.verdict, "❓")
    print(f"\n{symbol}  [{result.verdict}]  {result.claim}")
    print(f"   {result.explanation}")
    if result.source:
        print(f"   Source: {result.source}")
    if result.warnings:
        for warning in result.warnings:
            print(f"   ⚠️  {warning}")


if __name__ == "__main__":
    sys.exit(main())
