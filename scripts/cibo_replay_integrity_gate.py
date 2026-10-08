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



def assess_research_pareto(
    candidate: dict[str, Any],
    comparator: dict[str, Any],
    *,
    capital_floor: Decimal = DEFAULT_FLOOR,
    minimum_real_dd_improvement: Decimal = Decimal("0.00000001"),
) -> dict[str, Any]:
    """Research-only comparison with meaningful DD delta and full Sovereign safety.

    The previous ridge reporters can mislabel the *same* control as STRICT PARETO
    when DD differs by ~1e-32 after Decimal serialization/recalculation.
    Never promote a control/self-match due to sub-microscopic numerical drift.
    """
    if minimum_real_dd_improvement <= 0:
        raise ValueError("DD improvement threshold must be positive")
    cand_check = assess_replay(candidate, capital_floor=capital_floor)
    cand_loss = candidate["economic_group_report"]["portfolio_loss_report"]
    ref_loss = comparator["economic_group_report"]["portfolio_loss_report"]
    if not isinstance(cand_loss, dict) or not isinstance(ref_loss, dict):
        raise ValueError("missing gross-loss ledgers")
    cdd = _decimal(candidate, "max_drawdown_fraction")
    rdd = _decimal(comparator, "max_drawdown_fraction")
    ccap = _decimal(candidate, "ending_total_capital_usd")
    ctgl = _decimal(cand_loss, "total_gross_loss_usd")
    rtgl = _decimal(ref_loss, "total_gross_loss_usd")
    cagl = _decimal(cand_loss, "attack_gross_loss_usd")
    ragl = _decimal(ref_loss, "attack_gross_loss_usd")
    delta = rdd - cdd
    passes = {
        "meaningful_dd_improvement": delta >= minimum_real_dd_improvement,
        "capital_above_frozen_floor": ccap >= capital_floor,
        "gross_loss_nonworsening": ctgl <= rtgl,
        "attack_gross_loss_nonworsening": cagl <= ragl,
        "full_sovereign_integrity": cand_check["sovereign_integrity_pass"],
        "all_trader_entries_preserved": cand_check["checks"]["all_entries_preserved"],
    }
    return {
        "schema": "qore.cibo.research_sovereign_safe_pareto.v1",
        "research_only": True,
        "certified": False,
        "dd_improvement_fraction": str(delta),
        "dd_materiality_threshold_fraction": str(minimum_real_dd_improvement),
        "checks": passes,
        "strict_sovereign_safe_research_pareto": all(passes.values()),
    }



def assess_economic_noninferiority(
    candidate: dict[str, Any],
    comparator: dict[str, Any],
    *,
    capital_floor: Decimal = DEFAULT_FLOOR,
    max_dd_worsening_fraction: Decimal = Decimal("1e-8"),
    minimum_capital_gain: Decimal = Decimal("0.01"),
    minimum_gross_loss_reduction: Decimal = Decimal("0.01"),
) -> dict[str, Any]:
    """Research-only economic improvement while full Sovereign and DD survive.

    This does NOT assert a DD breakthrough and does NOT certify historical data.
    It separates a material capital+gross-loss improvement from pseudo-Pareto
    flags caused by ~1e-28 Decimal DD drift.
    """
    if (
        max_dd_worsening_fraction < 0
        or minimum_capital_gain <= 0
        or minimum_gross_loss_reduction <= 0
    ):
        raise ValueError("invalid noninferiority thresholds")
    c = assess_replay(candidate, capital_floor=capital_floor)
    r = assess_replay(comparator, capital_floor=capital_floor)
    c_loss = candidate["economic_group_report"]["portfolio_loss_report"]
    r_loss = comparator["economic_group_report"]["portfolio_loss_report"]
    candidate_cap = _decimal(candidate, "ending_total_capital_usd")
    comparator_cap = _decimal(comparator, "ending_total_capital_usd")
    candidate_dd = _decimal(candidate, "max_drawdown_fraction")
    comparator_dd = _decimal(comparator, "max_drawdown_fraction")
    gross_reduction = _decimal(r_loss, "total_gross_loss_usd") - _decimal(
        c_loss, "total_gross_loss_usd"
    )
    attack_reduction = _decimal(r_loss, "attack_gross_loss_usd") - _decimal(
        c_loss, "attack_gross_loss_usd"
    )
    checks = {
        "reference_sovereign_safe": r["sovereign_integrity_pass"],
        "candidate_sovereign_safe": c["sovereign_integrity_pass"],
        "all_trader_entries_preserved": (
            r["checks"]["all_entries_preserved"]
            and c["checks"]["all_entries_preserved"]
        ),
        "capital_floor": candidate_cap >= capital_floor,
        "minimum_real_capital_gain": (
            candidate_cap - comparator_cap >= minimum_capital_gain
        ),
        "gross_loss_materially_reduced": (
            gross_reduction >= minimum_gross_loss_reduction
        ),
        "attack_loss_nonworsening": attack_reduction >= 0,
        "dd_not_materially_worse": (
            candidate_dd <= comparator_dd + max_dd_worsening_fraction
        ),
    }
    return {
        "schema": "qore.cibo.research_economic_noninferiority.v1",
        "research_only": True,
        "certified": False,
        "dd_target_pass": c["checks"]["max_dd_target"],
        "broker_margin_verified": False,
        "fresh_oos_verified": False,
        "checks": checks,
        "economic_noninferiority_pass": all(checks.values()),
        "capital_gain_usd": str(candidate_cap - comparator_cap),
        "gross_loss_reduction_usd": str(gross_reduction),
        "attack_gross_loss_reduction_usd": str(attack_reduction),
        "dd_change_fraction": str(candidate_dd - comparator_dd),
        "max_dd_worsening_fraction": str(max_dd_worsening_fraction),
    }


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
