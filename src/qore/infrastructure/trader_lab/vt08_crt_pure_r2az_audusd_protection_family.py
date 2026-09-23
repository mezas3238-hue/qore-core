"""R2-AZ AUDUSD causal close-confirmed protection family.

R2-AY is the first high-density causal population to pass density, Total-R,
temporal-breadth and drawdown advancement gates while missing only PF >= 1.05.

R2-AZ preserves every R2-AY OOS-retained entry and changes only post-entry stop
protection. No entry is removed.

Protection is deliberately close-confirmed:
- a protection trigger is evaluated only after a complete M15 closes;
- the new stop becomes effective on the next M15 bar;
- stop can improve or hold, never widen;
- target remains fixed 1.5R;
- same-bar STOP_FIRST remains conservative.

Frozen family:
- CONTROL
- BE after a completed M15 closes >= +0.50R
- BE after close >= +0.75R
- BE after close >= +1.00R
- lock +0.25R after close >= +1.00R
- lock +0.50R after close >= +1.00R

Research only.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    Model1LabTrade,
    _summary,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2ay_audusd_confirmation_suitability_wf import (
    END,
    START,
    run_walk_forward,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import load_m5_window

IDENTITY = "VT08_CRT_PURE_R2AZ_AUDUSD_CAUSAL_PROTECTION_FAMILY_001"
SCHEMA = "qore.vt08.crt_pure.r2az_audusd_causal_protection_family.v1"
TARGET_R = Decimal("1.5")


class ProtectionPolicy(StrEnum):
    CONTROL = "CONTROL"
    BE_CLOSE_050 = "BE_CLOSE_050"
    BE_CLOSE_075 = "BE_CLOSE_075"
    BE_CLOSE_100 = "BE_CLOSE_100"
    LOCK025_CLOSE_100 = "LOCK025_CLOSE_100"
    LOCK050_CLOSE_100 = "LOCK050_CLOSE_100"


POLICY_PARAMETERS: dict[
    ProtectionPolicy,
    tuple[Decimal | None, Decimal | None],
] = {
    ProtectionPolicy.CONTROL: (None, None),
    ProtectionPolicy.BE_CLOSE_050: (Decimal("0.50"), Decimal("0")),
    ProtectionPolicy.BE_CLOSE_075: (Decimal("0.75"), Decimal("0")),
    ProtectionPolicy.BE_CLOSE_100: (Decimal("1.00"), Decimal("0")),
    ProtectionPolicy.LOCK025_CLOSE_100: (
        Decimal("1.00"),
        Decimal("0.25"),
    ),
    ProtectionPolicy.LOCK050_CLOSE_100: (
        Decimal("1.00"),
        Decimal("0.50"),
    ),
}


def _bar_window(
    trade: Model1LabTrade,
    m15_by_time: dict[Any, M15Bar],
) -> tuple[M15Bar, ...]:
    from datetime import datetime

    entry_time = datetime.fromisoformat(trade.entry_opened_at)
    c3_open = datetime.fromisoformat(trade.c3_opened_at)
    c3_close = c3_open + timedelta(hours=4)
    return tuple(
        m15_by_time[opened_at]
        for opened_at in sorted(m15_by_time)
        if entry_time <= opened_at < c3_close
    )


def _r_at_price(
    *,
    bullish: bool,
    entry: Decimal,
    risk: Decimal,
    price: Decimal,
) -> Decimal:
    if bullish:
        return (price - entry) / risk
    return (entry - price) / risk


def _improved_stop(
    *,
    bullish: bool,
    entry: Decimal,
    risk: Decimal,
    current_stop: Decimal,
    lock_r: Decimal,
) -> Decimal:
    candidate = (
        entry + lock_r * risk
        if bullish
        else entry - lock_r * risk
    )
    if bullish:
        return max(current_stop, candidate)
    return min(current_stop, candidate)


def _simulate(
    *,
    trade: Model1LabTrade,
    bars: tuple[M15Bar, ...],
    policy: ProtectionPolicy,
) -> Model1LabTrade:
    if not bars:
        raise RuntimeError("managed trade requires contiguous M15 lifecycle bars")

    bullish = trade.parent_direction == "BULLISH"
    entry = Decimal(trade.entry_price_relative)
    original_stop = Decimal(trade.stop_price_relative)
    target = Decimal(trade.target_price_relative)
    risk = abs(entry - original_stop)
    if risk <= 0:
        raise RuntimeError("managed trade risk must be positive")

    trigger_r, lock_r = POLICY_PARAMETERS[policy]
    current_stop = original_stop
    protection_armed = False
    exit_reason = "C3_CLOSE"
    exit_price = Decimal(bars[-1].close_price)
    exit_r: Decimal | None = None

    for bar in bars:
        if bullish:
            stop_hit = Decimal(bar.low_price) <= current_stop
            target_hit = Decimal(bar.high_price) >= target
        else:
            stop_hit = Decimal(bar.high_price) >= current_stop
            target_hit = Decimal(bar.low_price) <= target

        if stop_hit:
            exit_reason = "STOP"
            exit_price = current_stop
            exit_r = _r_at_price(
                bullish=bullish,
                entry=entry,
                risk=risk,
                price=current_stop,
            )
            break

        if target_hit:
            exit_reason = "TARGET_FIXED_1_5R"
            exit_price = target
            exit_r = TARGET_R
            break

        if trigger_r is not None and lock_r is not None:
            close_r = _r_at_price(
                bullish=bullish,
                entry=entry,
                risk=risk,
                price=Decimal(bar.close_price),
            )
            if close_r >= trigger_r:
                next_stop = _improved_stop(
                    bullish=bullish,
                    entry=entry,
                    risk=risk,
                    current_stop=current_stop,
                    lock_r=lock_r,
                )
                if next_stop != current_stop:
                    current_stop = next_stop
                    protection_armed = True

    if exit_r is None:
        exit_r = _r_at_price(
            bullish=bullish,
            entry=entry,
            risk=risk,
            price=exit_price,
        )

    suffix = policy.value
    if protection_armed:
        suffix += ":PROTECTED"

    return Model1LabTrade(
        schema=SCHEMA,
        identity=f"{IDENTITY}:{suffix}",
        market=trade.market,
        reference_policy=trade.reference_policy,
        reference_count=trade.reference_count,
        reference_ids=trade.reference_ids,
        parent_direction=trade.parent_direction,
        timing_triplet=trade.timing_triplet,
        c3_opened_at=trade.c3_opened_at,
        source_opened_at=trade.source_opened_at,
        confirmation_opened_at=trade.confirmation_opened_at,
        entry_opened_at=trade.entry_opened_at,
        entry_price_relative=trade.entry_price_relative,
        stop_price_relative=trade.stop_price_relative,
        target_price_relative=trade.target_price_relative,
        exit_price_relative=str(exit_price),
        exit_reason=exit_reason,
        r_multiple=round(float(exit_r), 8),
    )


def _annual(
    trades: tuple[Model1LabTrade, ...],
) -> dict[str, dict[str, Any]]:
    from datetime import UTC, datetime

    rows: dict[str, dict[str, Any]] = {}
    for year in range(START.year + 3, END.year):
        left = datetime(year, 9, 21, 0, 0, tzinfo=UTC)
        right = datetime(year + 1, 9, 21, 0, 0, tzinfo=UTC)
        fold = tuple(
            trade
            for trade in trades
            if left <= datetime.fromisoformat(trade.entry_opened_at) < right
        )
        rows[f"{year}_{year + 1}"] = _summary(fold)
    return rows


def run_family() -> tuple[
    dict[ProtectionPolicy, tuple[Model1LabTrade, ...]],
    dict[str, Any],
]:
    _, retained_records, ay_report = run_walk_forward()
    source_trades = tuple(record.trade for record in retained_records)

    m5 = load_m5_window(
        market=__import__(
            "qore.infrastructure.traders.crt_pure_identity",
            fromlist=["CrtPureMarket"],
        ).CrtPureMarket.AUDUSD,
        start=START - timedelta(days=2),
        end_exclusive=END + timedelta(days=2),
    )
    m15 = aggregate_complete_m15(m5)
    m15_by_time = {bar.opened_at: bar for bar in m15}

    family: dict[ProtectionPolicy, tuple[Model1LabTrade, ...]] = {}
    reports: dict[str, Any] = {}
    control_mismatch = 0

    for policy in ProtectionPolicy:
        managed = tuple(
            _simulate(
                trade=trade,
                bars=_bar_window(trade, m15_by_time),
                policy=policy,
            )
            for trade in source_trades
        )
        family[policy] = managed
        annual = _annual(managed)
        summary = _summary(managed)
        reports[policy.value] = {
            "full_oos": summary,
            "annual": annual,
            "trades_per_year": round(
                len(managed) / max(1, len(annual)),
                8,
            ),
            "positive_oos_year_fraction": (
                0.0
                if not annual
                else round(
                    sum(
                        float(item["total_r"]) > 0
                        for item in annual.values()
                    )
                    / len(annual),
                    8,
                )
            ),
        }

        if policy is ProtectionPolicy.CONTROL:
            control_mismatch = sum(
                abs(left.r_multiple - right.r_multiple) > 1e-7
                for left, right in zip(
                    source_trades,
                    managed,
                    strict=True,
                )
            )

    control = reports[ProtectionPolicy.CONTROL.value]["full_oos"]
    candidates: list[str] = []
    for policy in ProtectionPolicy:
        if policy is ProtectionPolicy.CONTROL:
            continue
        report = reports[policy.value]
        full = report["full_oos"]
        if (
            report["trades_per_year"] >= 170
            and full["profit_factor"] is not None
            and float(full["profit_factor"]) >= 1.05
            and float(full["total_r"]) > 0
            and report["positive_oos_year_fraction"] >= 0.60
            and float(full["max_drawdown_r"])
            <= float(control["max_drawdown_r"])
        ):
            candidates.append(policy.value)

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_population": "R2_AY_OOS_RETAINED",
        "source_population_report": {
            "trades": len(source_trades),
            "ay_oos_retention": ay_report["oos_retention"],
            "ay_oos_trades_per_year": ay_report["oos_trades_per_year"],
        },
        "policies_frozen_before_results": [
            policy.value for policy in ProtectionPolicy
        ],
        "protection_trigger_basis": "COMPLETED_M15_CLOSE",
        "protection_effective_from": "NEXT_M15_BAR",
        "same_bar_ambiguity": "STOP_FIRST",
        "target": "FIXED_1_5R_UNCHANGED",
        "stop_never_widens": True,
        "control_replay_mismatch_count": control_mismatch,
        "policies": reports,
        "advancement_candidates": candidates,
        "automatic_promotion": False,
        "final_untouched_certification_claim": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return family, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    family, report = run_family()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for policy in ProtectionPolicy:
            for trade in family[policy]:
                row = asdict(trade)
                row["protection_policy"] = policy.value
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    print("CRT_R2AZ_PROTECTION_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
