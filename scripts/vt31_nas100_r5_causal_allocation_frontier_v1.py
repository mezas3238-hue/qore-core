"""Causal capital-allocation frontier for VT31_NAS100_R5.

Consumed development evidence only.

Trade authorization, entry, stop, target, lifecycle, ACTIVITY_L rearm admission,
and one-trade-per-source semantics are unchanged. This lab only changes the
capital allocated at decision time using contexts independently observed as
stable across R5/R6/R8 and the consumed 2022-2024 interval.

The rules never use terminal PnL, fold identity, date labels, or target trade
count. Nominal monthly budgets remain admission budgets; context multipliers
act only on authorized risk after admission, so no extra trade is manufactured.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.r5.causal_allocation_frontier.v1"
MARKET = "NAS100"
GLOBAL_SCALAR = Decimal("0.60")

PROFILES = {
    "ALLOC_A": {
        "core_breaker": Decimal("1.20"),
        "weak_secondary": Decimal("0.50"),
        "other_secondary": Decimal("0.75"),
        "secondary_fvg_h1_mixed": Decimal("1.00"),
        "scout": Decimal("0.50"),
        "rearm": Decimal("0.50"),
    },
    "ALLOC_B": {
        "core_breaker": Decimal("1.25"),
        "weak_secondary": Decimal("0.50"),
        "other_secondary": Decimal("0.65"),
        "secondary_fvg_h1_mixed": Decimal("1.00"),
        "scout": Decimal("0.50"),
        "rearm": Decimal("0.50"),
    },
    "ALLOC_C": {
        "core_breaker": Decimal("1.30"),
        "weak_secondary": Decimal("0.50"),
        "other_secondary": Decimal("0.60"),
        "secondary_fvg_h1_mixed": Decimal("1.00"),
        "scout": Decimal("0.50"),
        "rearm": Decimal("0.50"),
    },
    "ALLOC_D": {
        "core_breaker": Decimal("1.25"),
        "weak_secondary": Decimal("0.60"),
        "other_secondary": Decimal("0.75"),
        "secondary_fvg_h1_mixed": Decimal("1.00"),
        "scout": Decimal("0.60"),
        "rearm": Decimal("0.60"),
    },
}


def _multiplier(
    row: dict[str, object],
    profile: dict[str, Decimal],
) -> tuple[Decimal, str]:
    tier = str(row.get("tier"))
    family = str(row.get("entry_family"))
    side = str(row.get("side"))

    if tier == "CORE":
        if family == "breaker":
            return profile["core_breaker"], "CORE_BREAKER_STABLE_POSITIVE"
        return Decimal("1.00"), "CORE_UNCHANGED"

    if tier == "SCOUT":
        return profile["scout"], "SCOUT_CAPITAL_PROTECTION"

    if tier == "REARM":
        return profile["rearm"], "REARM_REGIME_UNSTABLE_PROTECTION"

    if tier != "SECONDARY":
        return Decimal("1.00"), "UNKNOWN_TIER_UNCHANGED"

    fvg_h1_mixed = (
        family == "fair-value-gap"
        and row.get("h1_state") == "mixed"
    )
    if fvg_h1_mixed:
        return (
            profile["secondary_fvg_h1_mixed"],
            "SECONDARY_FVG_H1_MIXED_STABLE_POSITIVE",
        )

    weak = (
        family == "breaker"
        or (family == "order-block" and side == "long")
        or row.get("cash_open_state") == "bullish"
    )
    if weak:
        return (
            profile["weak_secondary"],
            "SECONDARY_STABLE_NEGATIVE_CONTEXT_PROTECTION",
        )

    return profile["other_secondary"], "SECONDARY_UNRESOLVED_PROTECTION"


def _apply_profile(
    rows: list[dict[str, object]],
    *,
    profile: dict[str, Decimal],
) -> list[dict[str, object]]:
    adjusted: list[dict[str, object]] = []
    for row in rows:
        multiplier, reason = _multiplier(row, profile)
        updated = dict(row)
        updated["requested_risk_r"] = format(
            Decimal(cast(str, row["requested_risk_r"])) * multiplier,
            "f",
        )
        updated["capital_weighted_net_r"] = format(
            Decimal(cast(str, row["capital_weighted_net_r"])) * multiplier,
            "f",
        )
        updated["context_risk_multiplier"] = format(multiplier, "f")
        updated["context_risk_reason"] = reason
        adjusted.append(updated)
    return engine._scale_capital_rows(
        adjusted,
        scalar=GLOBAL_SCALAR,
    )


def replay(path: Path, *, partition: str) -> dict[str, object]:
    (
        series,
        account,
        evidence,
        checked,
        evidence_sha,
        provider,
    ) = load_market_evidence(path)
    if not series or series[0].instrument.symbol != MARKET:
        raise ValueError("causal allocation frontier requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(bar.opened_at)].append(bar)
    by_day = {
        local_day: tuple(sorted(items, key=lambda item: item.opened_at))
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)

    first_rows, first_diag = corrective._first_rows(
        by_day,
        context_by_day,
        evidence=evidence,
        alt_partial_r=None,
        secondary_route_policy="ORIGINAL",
    )
    rearm_rows, rearm_diag = corrective._rearm_rows(
        by_day,
        context_by_day,
        first_rows,
        evidence=evidence,
        rearm_partial_r=None,
    )
    nominal = sorted(
        [*first_rows, *rearm_rows],
        key=lambda row: cast(str, row["signal_at"]),
    )

    variants: dict[str, object] = {}
    for name, profile in PROFILES.items():
        rows = _apply_profile(nominal, profile=profile)
        metrics = engine._capital_metrics(rows)
        mc = engine._monte_carlo(
            rows,
            variant=f"CAUSAL_ALLOCATION:{name}:{partition}",
        )
        reason_counts: dict[str, int] = defaultdict(int)
        for row in rows:
            reason_counts[str(row["context_risk_reason"])] += 1
        variants[name] = {
            "trade_count": len(rows),
            "base_trade_count": len(first_rows),
            "rearm_trade_count": len(rearm_rows),
            "metrics": metrics,
            "monte_carlo": mc,
            "reason_counts": dict(sorted(reason_counts.items())),
            "profile": {
                key: format(value, "f")
                for key, value in profile.items()
            },
            "objectives": {
                "density_300_350": 300 <= len(rows) <= 350,
                "pf_ge_1_50": (
                    metrics["profit_factor"] is not None
                    and Decimal(cast(str, metrics["profit_factor"]))
                    >= Decimal("1.50")
                ),
                "dd_le_6": (
                    Decimal(cast(str, metrics["max_drawdown_r"]))
                    <= Decimal("6")
                ),
                "mc_positive_ge_0_90": (
                    Decimal(
                        cast(str, mc["positive_terminal_probability"])
                    )
                    >= Decimal("0.90")
                ),
                "mc_p95_dd_le_15": (
                    Decimal(cast(str, mc["p95_max_drawdown_r"]))
                    <= Decimal("15")
                ),
            },
        }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "nominal_trade_count": len(nominal),
        "variants": variants,
        "diagnostics": {
            "first": first_diag,
            "rearm": rearm_diag,
        },
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "checked_at": checked.isoformat(),
            "evidence_software_sha": evidence_sha,
            "provider_symbol_name": provider,
        },
        "governance": {
            "consumed_evidence_only": True,
            "trade_authorization_changed": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "lifecycle_changed": False,
            "rearm_admission_changed": False,
            "trade_count_changed_by_allocation": False,
            "allocation_uses_pre_entry_context_only": True,
            "uses_terminal_pnl_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "uses_target_trade_count_at_runtime": False,
            "minimum_context_multiplier": "0.50",
            "maximum_context_multiplier": "1.30",
            "global_risk_scalar": "0.60",
            "policy_promoted": False,
            "opens_new_holdout": False,
            "live_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = replay(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "nominal_trade_count": payload["nominal_trade_count"],
                "variants": payload["variants"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
