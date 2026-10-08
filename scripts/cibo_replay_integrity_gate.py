#!/usr/bin/env python3
"""Independent CIBO replay integrity audit.

Does not change allocations, admission, PnL, or replay outcomes.
Research DD frontier != sovereign-safe != provider-feasible != certified.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


DEFAULT_FLOOR = Decimal("582440.0252953678696769360345")
DEFAULT_DD_MAX = Decimal("0.25")


def _decimal(source: dict[str, Any], key: str) -> Decimal:
    try:
        value = Decimal(str(source[key]))
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise ValueError(f"missing/invalid Decimal field: {key}") from exc
    if not value.is_finite():
        raise ValueError(f"non-finite Decimal field: {key}")
    return value


def assess_replay(
    replay: dict[str, Any],
    *,
    capital_floor: Decimal = DEFAULT_FLOOR,
    dd_limit: Decimal = DEFAULT_DD_MAX,
    expected_entries: int = 3368,
) -> dict[str, Any]:
    if capital_floor <= 0 or dd_limit <= 0 or dd_limit >= 1:
        raise ValueError("invalid gate thresholds")
    total = _decimal(replay, "ending_total_capital_usd")
    bank = _decimal(replay, "ending_sovereign_bank_usd")
    cushion = _decimal(replay, "ending_portfolio_cushion_usd")
    min_bank = _decimal(replay, "minimum_sovereign_bank_usd")
    floor_breach = _decimal(replay, "sovereign_floor_breach_usd")
    attack_breach = _decimal(replay, "attack_sovereign_breach_usd")
    dd = _decimal(replay, "max_drawdown_fraction")

    econ = replay.get("economic_group_report") or {}
    funnel = (replay.get("engineering_sensor_report") or {}).get("execution_funnel") or {}
    counts = (
        replay.get("decision_count") == expected_entries
        and replay.get("trade_count") == expected_entries
        and funnel.get("final_trade_count") == expected_entries
        and econ.get("all_entries_preserved") is True
        and funnel.get("sizing_medium_rejected_count") == 0
        and funnel.get("sizing_medium_deferred_count") == 0
    )
    checks = {
        "terminal_capital_floor": total >= capital_floor,
        "max_dd_target": 0 <= dd <= dd_limit,
        "all_entries_preserved": counts,
        "total_capital_reconciled": abs(total - bank - cushion) <= Decimal("1e-8"),
        "attack_sovereign_breach_zero": attack_breach == 0,
        "sovereign_protection_floor_breach_zero": floor_breach == 0,
        "no_negative_sovereign_bank": min_bank >= 0,
        "final_sovereign_bank_nonnegative": bank >= 0,
    }
    sovereign_safe = all(
        checks[key] for key in (
            "total_capital_reconciled",
            "attack_sovereign_breach_zero",
            "sovereign_protection_floor_breach_zero",
            "no_negative_sovereign_bank",
            "final_sovereign_bank_nonnegative",
        )
    )
    result = {
        "schema": "qore.cibo.replay_integrity_gate.v1",
        "research_only": True,
        "certified": False,
        "provider_margin_feasibility_proven": False,
        "fresh_sealed_oos_proven": False,
        "checks": checks,
        "sovereign_integrity_pass": sovereign_safe,
        "replay_prerequisites_pass": all(checks.values()),
        "metrics": {
            "total_capital_usd": str(total),
            "sovereign_bank_usd": str(bank),
            "portfolio_cushion_usd": str(cushion),
            "minimum_sovereign_bank_usd": str(min_bank),
            "sovereign_floor_breach_usd": str(floor_breach),
            "attack_sovereign_breach_usd": str(attack_breach),
            "max_dd_pct": str(dd * 100),
            "capital_floor_usd": str(capital_floor),
            "dd_limit_pct": str(dd_limit * 100),
        },
        "reason": (
            "Only the ATTACK sovereign breach is zero; full sovereign "
            "protection and minimum balance require independent checks. "
            "A positive combined cushion cannot silently erase a negative "
            "Sovereign subledger. Provider margin, costs, fresh OOS and "
            "scientific certification are separate mandatory gates."
        ),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("replay", type=Path, nargs="+")
    parser.add_argument("--floor", type=Decimal, default=DEFAULT_FLOOR)
    parser.add_argument("--dd-limit", type=Decimal, default=DEFAULT_DD_MAX)
    parser.add_argument("--research-report-only", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    results = []
    for file in args.replay:
        try:
            payload = json.loads(file.read_text())
            if not isinstance(payload, dict):
                raise ValueError("replay root must be mapping")
            report = assess_replay(payload, capital_floor=args.floor, dd_limit=args.dd_limit)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            report = {
                "schema": "qore.cibo.replay_integrity_gate.v1",
                "replay_prerequisites_pass": False,
                "sovereign_integrity_pass": False,
                "certified": False,
                "error": str(exc),
            }
        report["source"] = str(file)
        results.append(report)
        print("CIBO_INTEGRITY_GATE=" + json.dumps(report, sort_keys=True))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, sort_keys=True, indent=2))
    if args.research_report_only:
        return 0
    return 0 if all(r["replay_prerequisites_pass"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
