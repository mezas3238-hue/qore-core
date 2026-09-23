"""R2-BA AUDUSD lifecycle extension family.

Frozen after R2-AZ and before lifecycle outcomes.

Source population:
- exact R2-AY OOS-retained entries;
- BE_CLOSE_075 protection from R2-AZ;
- fixed 1.5R target;
- structural source stop;
- no entry removal.

Single changed dimension:
- CONTROL_C3_CLOSE: lifecycle ends at C3 close.
- NEXT_H4: if the trade is still active at C3 close, allow exactly one additional
  contiguous H4 block before forced exit.

Protection remains close-confirmed and becomes effective only on the next M15.
Stop never widens. Same-bar ambiguity remains STOP_FIRST.

A missing/incomplete extension block fails closed to the C3-close control rather
than synthesizing market data.

Research only.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
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
    run_walk_forward,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2ax_audusd_confirmation_geometry_atlas import (
    END,
    START,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2az_audusd_protection_family import (
    ProtectionPolicy,
    _simulate,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import (
    load_m5_window,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2BA_AUDUSD_LIFECYCLE_EXTENSION_001"
SCHEMA = "qore.vt08.crt_pure.r2ba_audusd_lifecycle_extension.v1"
EXTENSION = timedelta(hours=4)
M15 = timedelta(minutes=15)
EXPECTED_EXTENSION_BARS = 16


class LifecyclePolicy(StrEnum):
    CONTROL_C3_CLOSE = "CONTROL_C3_CLOSE"
    NEXT_H4 = "NEXT_H4"


def _interval(
    *,
    trade: Model1LabTrade,
    m15_by_time: dict[datetime, M15Bar],
    end_exclusive: datetime,
) -> tuple[M15Bar, ...]:
    entry_time = datetime.fromisoformat(trade.entry_opened_at)
    return tuple(
        m15_by_time[opened_at]
        for opened_at in sorted(m15_by_time)
        if entry_time <= opened_at < end_exclusive
    )


def _extension_complete(
    *,
    c3_close: datetime,
    m15_by_time: dict[datetime, M15Bar],
) -> bool:
    return all(
        c3_close + index * M15 in m15_by_time
        for index in range(EXPECTED_EXTENSION_BARS)
    )


def _retag(
    trade: Model1LabTrade,
    policy: LifecyclePolicy,
) -> Model1LabTrade:
    return Model1LabTrade(
        schema=SCHEMA,
        identity=f"{IDENTITY}:{policy.value}",
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
        exit_price_relative=trade.exit_price_relative,
        exit_reason=trade.exit_reason,
        r_multiple=trade.r_multiple,
    )


def _annual(
    trades: tuple[Model1LabTrade, ...],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for year in range(START.year + 3, END.year):
        left = datetime(year, 9, 21, 0, 0, tzinfo=UTC)
        right = datetime(year + 1, 9, 21, 0, 0, tzinfo=UTC)
        rows = tuple(
            trade
            for trade in trades
            if left <= datetime.fromisoformat(trade.entry_opened_at) < right
        )
        result[f"{year}_{year + 1}"] = _summary(rows)
    return result


def run_family() -> tuple[
    dict[LifecyclePolicy, tuple[Model1LabTrade, ...]],
    dict[str, Any],
]:
    _, retained_records, ay_report = run_walk_forward()
    source = tuple(record.trade for record in retained_records)

    m5 = load_m5_window(
        CrtPureMarket.AUDUSD,
        start=START - timedelta(days=2),
        end_exclusive=END + timedelta(days=1),
    )
    m15 = aggregate_complete_m15(m5)
    m15_by_time = {bar.opened_at: bar for bar in m15}

    control_rows: list[Model1LabTrade] = []
    extended_rows: list[Model1LabTrade] = []
    incomplete_extension_fallbacks = 0

    for trade in source:
        c3_open = datetime.fromisoformat(trade.c3_opened_at)
        c3_close = c3_open + timedelta(hours=4)
        control_bars = _interval(
            trade=trade,
            m15_by_time=m15_by_time,
            end_exclusive=c3_close,
        )
        control = _simulate(
            trade=trade,
            bars=control_bars,
            policy=ProtectionPolicy.BE_CLOSE_075,
        )
        control_rows.append(
            _retag(control, LifecyclePolicy.CONTROL_C3_CLOSE)
        )

        if control.exit_reason != "C3_CLOSE":
            extended_rows.append(
                _retag(control, LifecyclePolicy.NEXT_H4)
            )
            continue

        if not _extension_complete(
            c3_close=c3_close,
            m15_by_time=m15_by_time,
        ):
            incomplete_extension_fallbacks += 1
            extended_rows.append(
                _retag(control, LifecyclePolicy.NEXT_H4)
            )
            continue

        extended_bars = _interval(
            trade=trade,
            m15_by_time=m15_by_time,
            end_exclusive=c3_close + EXTENSION,
        )
        extended = _simulate(
            trade=trade,
            bars=extended_bars,
            policy=ProtectionPolicy.BE_CLOSE_075,
        )
        extended_rows.append(
            _retag(extended, LifecyclePolicy.NEXT_H4)
        )

    family = {
        LifecyclePolicy.CONTROL_C3_CLOSE: tuple(control_rows),
        LifecyclePolicy.NEXT_H4: tuple(extended_rows),
    }

    policies: dict[str, Any] = {}
    for policy, trades in family.items():
        annual = _annual(trades)
        policies[policy.value] = {
            "full_oos": _summary(trades),
            "annual": annual,
            "trades_per_year": round(len(trades) / max(1, len(annual)), 8),
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

    control = policies[LifecyclePolicy.CONTROL_C3_CLOSE.value]["full_oos"]
    candidate = policies[LifecyclePolicy.NEXT_H4.value]
    candidate_full = candidate["full_oos"]
    advancement = {
        "density_pass": candidate["trades_per_year"] >= 170,
        "pf_pass": (
            candidate_full["profit_factor"] is not None
            and float(candidate_full["profit_factor"]) >= 1.05
        ),
        "total_r_pass": float(candidate_full["total_r"]) > 0,
        "temporal_breadth_pass": (
            candidate["positive_oos_year_fraction"] >= 0.60
        ),
        "drawdown_pass": (
            float(candidate_full["max_drawdown_r"])
            <= float(control["max_drawdown_r"])
        ),
    }
    advancement["all_pass"] = all(advancement.values())

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_population": "R2_AY_OOS_RETAINED",
        "protection_policy": ProtectionPolicy.BE_CLOSE_075.value,
        "target": "FIXED_1_5R",
        "single_changed_dimension": "EXPIRY",
        "policies_frozen_before_results": [
            policy.value for policy in LifecyclePolicy
        ],
        "extension": "EXACTLY_ONE_ADDITIONAL_H4",
        "extension_missing_data_policy": "FAIL_CLOSED_TO_C3_CLOSE",
        "incomplete_extension_fallbacks": incomplete_extension_fallbacks,
        "source_population_report": {
            "trades": len(source),
            "ay_oos_retention": ay_report["oos_retention"],
            "ay_oos_trades_per_year": ay_report["oos_trades_per_year"],
        },
        "policies": policies,
        "advancement_gate": advancement,
        "automatic_promotion": False,
        "overlap_portfolio_effect_not_yet_adjudicated": True,
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
        for policy in LifecyclePolicy:
            for trade in family[policy]:
                row = asdict(trade)
                row["lifecycle_policy"] = policy.value
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    print("CRT_R2BA_LIFECYCLE_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
