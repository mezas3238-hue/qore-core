"""Decision-time CORE breaker regime-risk overlay for VT31 NAS100 ALLOC_G.

Consumed development evidence only.

The base trader, entry grammar, stops, targets, lifecycle, rearm admission, and
ALLOC_G remain unchanged. This lab applies one bounded capital multiplier only
to CORE breaker trades, using decision-time state already available to the
reasoning engine.

The overlay is deliberately bounded:
- protection never below 0.75x of ALLOC_G risk,
- emphasis never above 1.10x of ALLOC_G risk.

No date, fold identity, terminal PnL, target trade count, or future bar is used
at runtime. Trade count is unchanged.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_causal_hybrid_rearm_v1 as engine
import vt31_nas100_r5_causal_allocation_frontier_v1 as allocation
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.r5.core_breaker_regime_risk_frontier.v1"
MARKET = "NAS100"
BASE_PROFILE = "ALLOC_G_CORE_FAMILY_050"

OVERLAYS = {
    "BASELINE": {
        "protect": Decimal("1.00"),
        "emphasize": Decimal("1.00"),
        "fragile_threshold": Decimal("-99"),
        "robust_threshold": Decimal("99"),
    },
    "REGIME_A": {
        "protect": Decimal("0.80"),
        "emphasize": Decimal("1.05"),
        "fragile_threshold": Decimal("-1"),
        "robust_threshold": Decimal("2"),
    },
    "REGIME_B": {
        "protect": Decimal("0.75"),
        "emphasize": Decimal("1.10"),
        "fragile_threshold": Decimal("-1"),
        "robust_threshold": Decimal("2"),
    },
    "REGIME_C": {
        "protect": Decimal("0.80"),
        "emphasize": Decimal("1.10"),
        "fragile_threshold": Decimal("-2"),
        "robust_threshold": Decimal("2"),
    },
}


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _breaker_state(row: dict[str, object]) -> tuple[int, int, int]:
    if row.get("tier") != "CORE" or row.get("entry_family") != "breaker":
        return 0, 0, 0

    latency = _int_or_none(row.get("confirmation_latency_minutes"))
    reclaim_age = _int_or_none(row.get("reference_reclaim_age_minutes"))

    robust = 0
    fragile = 0

    if row.get("h1_state") == "mixed":
        robust += 1
    if row.get("reference_volatility_state") == "compressed":
        robust += 1
    if latency is not None and 6 <= latency <= 10:
        robust += 1
    if reclaim_age is not None and reclaim_age <= 4:
        robust += 1
    current_path = row.get("current_path_vs_previous")
    if current_path is not None and Decimal(str(current_path)) < Decimal("0.75"):
        robust += 1

    if row.get("cash_open_state") == "bullish":
        fragile += 1
    if latency is not None and 3 <= latency <= 5:
        fragile += 1
    if row.get("side") == "short":
        fragile += 1
    if row.get("premarket_state") == "bearish":
        fragile += 1

    return robust - fragile, robust, fragile


def _apply_overlay(
    rows: list[dict[str, object]],
    *,
    overlay_name: str,
) -> list[dict[str, object]]:
    cfg = OVERLAYS[overlay_name]
    adjusted: list[dict[str, object]] = []

    for row in rows:
        updated = dict(row)
        score, robust_votes, fragile_votes = _breaker_state(updated)
        multiplier = Decimal("1.00")
        reason = "NON_CORE_BREAKER_UNCHANGED"

        if updated.get("tier") == "CORE" and updated.get("entry_family") == "breaker":
            if score <= int(cfg["fragile_threshold"]):
                multiplier = cfg["protect"]
                reason = "CORE_BREAKER_REGIME_FRAGILE_PROTECTION"
            elif score >= int(cfg["robust_threshold"]):
                multiplier = cfg["emphasize"]
                reason = "CORE_BREAKER_ROBUST_STATE_EMPHASIS"
            else:
                reason = "CORE_BREAKER_NEUTRAL_STATE"

        updated["regime_state_score"] = score
        updated["regime_robust_votes"] = robust_votes
        updated["regime_fragile_votes"] = fragile_votes
        updated["regime_risk_multiplier"] = format(multiplier, "f")
        updated["regime_risk_reason"] = reason
        updated["requested_risk_r"] = format(
            Decimal(cast(str, updated["requested_risk_r"])) * multiplier,
            "f",
        )
        updated["capital_weighted_net_r"] = format(
            Decimal(cast(str, updated["capital_weighted_net_r"])) * multiplier,
            "f",
        )
        adjusted.append(updated)
    return adjusted


def _metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    ordered = sorted(rows, key=lambda row: cast(str, row["signal_at"]))
    return engine._capital_metrics(ordered)


def _annual_blocks(
    rows: list[dict[str, object]],
    *,
    start: date,
    years: int,
) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    for idx in range(years):
        block_start = date(start.year + idx, start.month, start.day)
        block_end = date(start.year + idx + 1, start.month, start.day)
        selected = [
            row
            for row in rows
            if block_start
            <= date.fromisoformat(cast(str, row["local_date"]))
            < block_end
        ]
        metrics = _metrics(selected)
        blocks.append(
            {
                "year_block": idx + 1,
                "start": block_start.isoformat(),
                "end_exclusive": block_end.isoformat(),
                "trade_count": len(selected),
                "metrics": metrics,
                "positive": (
                    bool(selected)
                    and Decimal(cast(str, metrics["total_r"])) > 0
                ),
            }
        )
    return blocks


def replay(path: Path, *, partition: str) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if not series or series[0].instrument.symbol != MARKET:
        raise ValueError("CORE breaker regime-risk frontier requires NAS100")

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
    alloc_g = allocation._apply_profile(
        nominal,
        profile=allocation.PROFILES[BASE_PROFILE],
    )

    variants: dict[str, object] = {}
    for overlay_name in OVERLAYS:
        rows = _apply_overlay(alloc_g, overlay_name=overlay_name)
        metrics = _metrics(rows)
        mc = engine._monte_carlo(
            rows,
            variant=f"CORE_BREAKER_REGIME:{overlay_name}:{partition}",
        )
        reason_counts: dict[str, int] = defaultdict(int)
        for row in rows:
            reason_counts[str(row["regime_risk_reason"])] += 1

        annual = []
        if partition == "consumed_holdout":
            annual = _annual_blocks(
                rows,
                start=date(2022, 7, 18),
                years=2,
            )

        objectives = {
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
                Decimal(cast(str, mc["positive_terminal_probability"]))
                >= Decimal("0.90")
            ),
            "mc_p95_dd_le_15": (
                Decimal(cast(str, mc["p95_max_drawdown_r"]))
                <= Decimal("15")
            ),
        }
        if annual:
            objectives["both_consumed_years_positive"] = all(
                bool(block["positive"]) for block in annual
            )

        variants[overlay_name] = {
            "trade_count": len(rows),
            "metrics": metrics,
            "monte_carlo": mc,
            "annual_blocks": annual,
            "reason_counts": dict(sorted(reason_counts.items())),
            "overlay": {
                key: format(value, "f")
                for key, value in OVERLAYS[overlay_name].items()
            },
            "objectives": objectives,
            "passes_all_objectives": all(objectives.values()),
        }

    return {
        "schema": SCHEMA,
        "partition": partition,
        "market": MARKET,
        "base_profile": BASE_PROFILE,
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
            "bounded_overlay_only": True,
            "minimum_overlay_multiplier": "0.75",
            "maximum_overlay_multiplier": "1.10",
            "trade_count_changed": False,
            "entry_changed": False,
            "stop_changed": False,
            "target_changed": False,
            "lifecycle_changed": False,
            "rearm_admission_changed": False,
            "uses_terminal_pnl_at_runtime": False,
            "uses_fold_identity_at_runtime": False,
            "uses_calendar_time_at_runtime": False,
            "opens_new_holdout": False,
            "policy_promoted": False,
            "candidate_certified": False,
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
                "variants": payload["variants"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
