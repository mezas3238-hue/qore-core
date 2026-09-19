"""VT08 Index R12 — context-specific journey management.

R12 keeps the R8 priority-POI + structural-rearm opportunity generator. It
assigns one simple management policy to strong pre-entry contexts and another
bounded policy to weak contexts, then recomputes the one-active-position-per-
symbol stream using the actual managed exit time.

Strong context = previous completed source-day body opposed to side OR a
structural rearm event. No outcome information is used to classify a trade.
The 5Y window is consumed development evidence.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_density_round4 as r4
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as r5
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r6_five_year_validation as v5y
from qore.infrastructure.trader_lab import vt08_index_r8_priority_poi_rearm_reset as r8
from qore.infrastructure.trader_lab import vt08_index_r10_contextual_risk as r10
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r12_contextual_management.v1"
IDENTITY = "VT08_INDEX_R12_CONTEXTUAL_MANAGEMENT_001"
MIN_TRADES = 1500
MAX_TRADES = 1600
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")


@dataclass(frozen=True, slots=True)
class ManagementPair:
    strong_policy: r5.Policy
    weak_policy: r5.Policy

    @property
    def pair_id(self) -> str:
        return (
            f"R12-S-{self.strong_policy.policy_id}-"
            f"W-{self.weak_policy.policy_id}"
        )

    def payload(self) -> dict[str, Any]:
        return {
            "pair_id": self.pair_id,
            "strong_policy": self.strong_policy.payload(),
            "weak_policy": self.weak_policy.payload(),
        }


def _policy(
    *,
    target: str,
    deadline_bars: int | None = None,
    deadline_mfe: str | None = None,
    soft_loss: str | None = None,
    soft_until: str | None = None,
    trail_name: str = "OFF",
    trail_steps: tuple[tuple[str, str], ...] = (),
) -> r5.Policy:
    return r5.Policy(
        target_r=Decimal(target),
        soft_close_loss_r=Decimal(soft_loss) if soft_loss else None,
        soft_close_until_mfe_r=Decimal(soft_until) if soft_until else None,
        deadline_bars=deadline_bars,
        deadline_min_mfe_r=Decimal(deadline_mfe) if deadline_mfe else None,
        trail_name=trail_name,
        trail_steps=tuple(
            (Decimal(trigger), Decimal(lock))
            for trigger, lock in trail_steps
        ),
    )


def _pairs() -> tuple[ManagementPair, ...]:
    strong = (
        _policy(target="2.5"),
        _policy(target="3.0"),
    )
    weak = (
        _policy(target="2.5"),
        _policy(target="2.0"),
        _policy(target="1.5"),
        _policy(target="2.5", deadline_bars=4, deadline_mfe="0.25"),
        _policy(target="2.5", deadline_bars=4, deadline_mfe="0.5"),
        _policy(target="2.5", deadline_bars=8, deadline_mfe="0.25"),
        _policy(
            target="2.5",
            soft_loss="0.5",
            soft_until="1.0",
        ),
        _policy(
            target="2.5",
            trail_name="BE050",
            trail_steps=(("0.5", "0"),),
        ),
        _policy(
            target="2.5",
            trail_name="LOCK025_075",
            trail_steps=(("0.75", "0.25"),),
        ),
    )
    return tuple(
        ManagementPair(strong_policy=s, weak_policy=w)
        for s in strong
        for w in weak
    )


def _is_strong(context: r10.Context) -> bool:
    return context.previous_source_day_body_opposed or context.rearm


def _sequential_symbol(
    opportunities: Sequence[r4.ExpandedOpportunity],
    *,
    bars: Sequence[Vt08IndexC2R1Bar],
    indexed: dict[datetime, Vt08IndexC2R1Bar],
    pair: ManagementPair,
) -> tuple[
    tuple[r4.ExpandedOpportunity, r5.ManagedTrade, r10.Context],
    ...,
]:
    opened = tuple(bar.opened_at.astimezone(UTC) for bar in bars)
    candidates: list[
        tuple[r4.ExpandedOpportunity, r5.ManagedTrade, r10.Context]
    ] = []
    for opportunity in opportunities:
        context = r10._context(opportunity, indexed=indexed)
        policy = pair.strong_policy if _is_strong(context) else pair.weak_policy
        outcome = r5._manage_trade(
            opportunity.signal,
            bars=bars,
            opened=opened,
            policy=policy,
        )
        candidates.append((opportunity, outcome, context))

    selected: list[
        tuple[r4.ExpandedOpportunity, r5.ManagedTrade, r10.Context]
    ] = []
    last_exit: datetime | None = None
    for opportunity, outcome, context in candidates:
        if last_exit is not None and opportunity.signal.signal_at < last_exit:
            continue
        selected.append((opportunity, outcome, context))
        last_exit = outcome.exited_at
    return tuple(selected)


def _year_metrics(
    stream: Sequence[
        tuple[r4.ExpandedOpportunity, r5.ManagedTrade, r10.Context]
    ],
    values: Sequence[Decimal],
) -> dict[str, Any]:
    years = sorted(
        {
            opportunity.signal.signal_at.astimezone(v5y._NY).year
            for opportunity, _outcome, _context in stream
        }
    )
    result: dict[str, Any] = {}
    for year in years:
        subset = tuple(
            value
            for (opportunity, _outcome, _context), value in zip(
                stream,
                values,
                strict=True,
            )
            if opportunity.signal.signal_at.astimezone(v5y._NY).year == year
        )
        result[str(year)] = fx._metrics(subset)
    return result


def _candidate(
    *,
    pair: ManagementPair,
    opportunities_by_symbol: dict[
        str,
        tuple[r4.ExpandedOpportunity, ...],
    ],
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
    indexed_by_symbol: dict[str, dict[datetime, Vt08IndexC2R1Bar]],
) -> dict[str, Any]:
    stream: list[
        tuple[r4.ExpandedOpportunity, r5.ManagedTrade, r10.Context]
    ] = []
    for symbol in ("NAS100", "SP500", "US30"):
        stream.extend(
            _sequential_symbol(
                opportunities_by_symbol[symbol],
                bars=bars_by_symbol[symbol],
                indexed=indexed_by_symbol[symbol],
                pair=pair,
            )
        )
    stream.sort(
        key=lambda item: (item[0].signal.signal_at, item[0].signal.symbol)
    )
    primary_values = tuple(
        outcome.r_multiple - PRIMARY_STRESS
        for _opportunity, outcome, _context in stream
    )
    secondary_values = tuple(
        outcome.r_multiple - SECONDARY_STRESS
        for _opportunity, outcome, _context in stream
    )
    primary = fx._metrics(primary_values)
    secondary = fx._metrics(secondary_values)
    years = _year_metrics(stream, primary_values)
    positive_years = sum(
        Decimal(str(row["total_r"])) > 0 for row in years.values()
    )
    sample = len(stream)
    return {
        "pair": pair.payload(),
        "sample": sample,
        "density_pass": MIN_TRADES <= sample <= MAX_TRADES,
        "strong_trade_count": sum(
            _is_strong(context)
            for _opportunity, _outcome, context in stream
        ),
        "weak_trade_count": sum(
            not _is_strong(context)
            for _opportunity, _outcome, context in stream
        ),
        "rearm_trade_count": sum(
            context.rearm
            for _opportunity, _outcome, context in stream
        ),
        "primary": primary,
        "secondary": secondary,
        "positive_years": positive_years,
        "primary_by_year": years,
        "goal_pass": (
            MIN_TRADES <= sample <= MAX_TRADES
            and Decimal(str(primary["profit_factor"] or "0")) >= Decimal("1.25")
            and Decimal(str(primary["max_drawdown_r"])) <= Decimal("35")
            and Decimal(str(secondary["profit_factor"] or "0")) >= Decimal("1.15")
            and positive_years >= 4
        ),
    }


def _rank(row: dict[str, Any]) -> tuple[int, int, Decimal, Decimal, Decimal]:
    primary = row["primary"]
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
    indexed_by_symbol: dict[
        str,
        dict[datetime, Vt08IndexC2R1Bar],
    ] = {}
    opportunities_by_symbol: dict[
        str,
        tuple[r4.ExpandedOpportunity, ...],
    ] = {}
    provenance: dict[str, Any] = {}
    for symbol in ("NAS100", "SP500", "US30"):
        bars, source = v5y._load_cibo_m15_5y(roots[symbol], symbol=symbol)
        bars_by_symbol[symbol] = bars
        indexed_by_symbol[symbol] = {
            bar.opened_at.astimezone(UTC): bar for bar in bars
        }
        opportunities_by_symbol[symbol] = r8._opportunities(
            symbol=symbol,
            bars=bars,
        )
        provenance[symbol] = source

    rows = [
        _candidate(
            pair=pair,
            opportunities_by_symbol=opportunities_by_symbol,
            bars_by_symbol=bars_by_symbol,
            indexed_by_symbol=indexed_by_symbol,
        )
        for pair in _pairs()
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
        "execution_architecture": r8.IDENTITY,
        "pair_count": len(rows),
        "goal_candidate_count": len(goals),
        "best": rows[0],
        "top_10": rows[:10],
        "goal_candidates": goals[:10],
        "provenance": provenance,
        "governance": {
            "development_only": True,
            "pre_entry_context_only": True,
            "bounded_management_pairs": True,
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
