"""VT08 Index R9 — journey management screen on R8 opportunity architecture.

The R8 opportunity architecture (priority source POI + structural rearm) is kept
fixed. R9 changes only causal post-entry management and re-computes sequential
admission under the actual exit time of each policy.

The failed 5Y period remains consumed development evidence.
"""

from __future__ import annotations

import argparse
import itertools
import json
from collections.abc import Sequence
from datetime import UTC
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as r5
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r6_five_year_validation as v5y
from qore.infrastructure.trader_lab import vt08_index_r8_priority_poi_rearm_reset as r8
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r9_journey_management_screen.v1"
IDENTITY = "VT08_INDEX_R9_JOURNEY_MANAGEMENT_SCREEN_001"
MIN_TRADES = 1500
MAX_TRADES = 1600
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
RAW_PF_GOAL = Decimal("1.20")
RAW_DD_GOAL = Decimal("30")
SECONDARY_PF_GOAL = Decimal("1.10")


def _policies() -> tuple[r5.Policy, ...]:
    trails: dict[str, tuple[tuple[Decimal, Decimal], ...]] = {
        "OFF": (),
        "BE050": ((Decimal("0.5"), Decimal("0")),),
        "LOCK025_075": ((Decimal("0.75"), Decimal("0.25")),),
    }
    deadlines: tuple[tuple[int | None, Decimal | None], ...] = (
        (None, None),
        (4, Decimal("0.25")),
        (4, Decimal("0.5")),
        (8, Decimal("0.25")),
        (8, Decimal("0.5")),
    )
    return tuple(
        r5.Policy(
            target_r=target,
            soft_close_loss_r=None,
            soft_close_until_mfe_r=None,
            deadline_bars=deadline_bars,
            deadline_min_mfe_r=deadline_mfe,
            trail_name=trail_name,
            trail_steps=trail_steps,
        )
        for target, (deadline_bars, deadline_mfe), (trail_name, trail_steps)
        in itertools.product(
            (Decimal("2.5"), Decimal("3.0")),
            deadlines,
            trails.items(),
        )
    )


def _sequential_policy(
    opportunities: Sequence[Any],
    *,
    bars: Sequence[Vt08IndexC2R1Bar],
    policy: r5.Policy,
) -> tuple[tuple[Any, r5.ManagedTrade], ...]:
    opened = tuple(bar.opened_at.astimezone(UTC) for bar in bars)
    candidates = tuple(
        (
            opportunity,
            r5._manage_trade(
                opportunity.signal,
                bars=bars,
                opened=opened,
                policy=policy,
            ),
        )
        for opportunity in opportunities
    )
    selected: list[tuple[Any, r5.ManagedTrade]] = []
    last_exit = None
    for opportunity, outcome in candidates:
        if last_exit is not None and opportunity.signal.signal_at < last_exit:
            continue
        selected.append((opportunity, outcome))
        last_exit = outcome.exited_at
    return tuple(selected)


def _year_metrics(
    selected: Sequence[tuple[Any, r5.ManagedTrade]],
    values: Sequence[Decimal],
) -> dict[str, Any]:
    years = sorted(
        {
            opportunity.signal.signal_at.astimezone(v5y._NY).year
            for opportunity, _outcome in selected
        }
    )
    result: dict[str, Any] = {}
    for year in years:
        subset = tuple(
            value
            for (opportunity, _outcome), value in zip(
                selected,
                values,
                strict=True,
            )
            if opportunity.signal.signal_at.astimezone(v5y._NY).year == year
        )
        result[str(year)] = fx._metrics(subset)
    return result


def _candidate(
    *,
    policy: r5.Policy,
    opportunities_by_symbol: dict[str, tuple[Any, ...]],
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> dict[str, Any]:
    selected: list[tuple[Any, r5.ManagedTrade]] = []
    for symbol in ("NAS100", "SP500", "US30"):
        selected.extend(
            _sequential_policy(
                opportunities_by_symbol[symbol],
                bars=bars_by_symbol[symbol],
                policy=policy,
            )
        )
    selected.sort(
        key=lambda item: (item[0].signal.signal_at, item[0].signal.symbol)
    )
    raw_primary_values = tuple(
        outcome.r_multiple - PRIMARY_STRESS for _opportunity, outcome in selected
    )
    raw_secondary_values = tuple(
        outcome.r_multiple - SECONDARY_STRESS for _opportunity, outcome in selected
    )
    primary = fx._metrics(raw_primary_values)
    secondary = fx._metrics(raw_secondary_values)
    year_rows = _year_metrics(selected, raw_primary_values)
    positive_years = sum(
        Decimal(str(row["total_r"])) > 0 for row in year_rows.values()
    )
    sample = len(selected)
    raw_pf = Decimal(str(primary["profit_factor"] or "0"))
    raw_dd = Decimal(str(primary["max_drawdown_r"]))
    secondary_pf = Decimal(str(secondary["profit_factor"] or "0"))
    return {
        "policy": policy.payload(),
        "sample": sample,
        "density_pass": MIN_TRADES <= sample <= MAX_TRADES,
        "raw_primary": primary,
        "raw_secondary": secondary,
        "positive_years": positive_years,
        "primary_by_year": year_rows,
        "trade_count_by_market": {
            symbol: sum(
                opportunity.signal.symbol == symbol
                for opportunity, _outcome in selected
            )
            for symbol in ("NAS100", "SP500", "US30")
        },
        "rearm_trade_count": sum(
            int(opportunity.rearm_index) > 0
            for opportunity, _outcome in selected
        ),
        "goal_pass": (
            MIN_TRADES <= sample <= MAX_TRADES
            and raw_pf >= RAW_PF_GOAL
            and raw_dd <= RAW_DD_GOAL
            and secondary_pf >= SECONDARY_PF_GOAL
            and positive_years >= 4
        ),
    }


def _rank(row: dict[str, Any]) -> tuple[int, int, Decimal, Decimal, Decimal]:
    primary = row["raw_primary"]
    return (
        int(bool(row["goal_pass"])),
        int(bool(row["density_pass"])),
        Decimal(str(primary["profit_factor"] or "0")),
        -Decimal(str(primary["max_drawdown_r"])),
        Decimal(str(primary["total_r"])),
    )


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]] = {}
    opportunities_by_symbol: dict[str, tuple[Any, ...]] = {}
    provenance: dict[str, Any] = {}
    for symbol in ("NAS100", "SP500", "US30"):
        bars, source = v5y._load_cibo_m15_5y(roots[symbol], symbol=symbol)
        bars_by_symbol[symbol] = bars
        opportunities_by_symbol[symbol] = r8._opportunities(
            symbol=symbol,
            bars=bars,
        )
        provenance[symbol] = source

    rows = [
        _candidate(
            policy=policy,
            opportunities_by_symbol=opportunities_by_symbol,
            bars_by_symbol=bars_by_symbol,
        )
        for policy in _policies()
    ]
    rows.sort(key=_rank, reverse=True)
    goals = [row for row in rows if bool(row["goal_pass"])]
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "window": {
            "start_date": v5y.START_DATE.isoformat(),
            "end_date_exclusive": v5y.END_DATE_EXCLUSIVE.isoformat(),
            "status": "CONSUMED_DEVELOPMENT",
            "fresh_certification_holdout": False,
        },
        "opportunity_architecture": r8.IDENTITY,
        "policy_count": len(rows),
        "goal_candidate_count": len(goals),
        "best": rows[0],
        "top_10": rows[:10],
        "goal_candidates": goals[:10],
        "provenance": provenance,
        "governance": {
            "development_only": True,
            "opportunity_architecture_changed": False,
            "bounded_management_screen": True,
            "stop_widening_allowed": False,
            "five_year_window_consumed": True,
            "fresh_holdout_claim": False,
            "candidate_promoted": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "goal_candidate_count": report["goal_candidate_count"],
                "best": report["best"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
