"""VT08 Index R25 — R23/R24 failure forensics.

Forensics only. No candidate is created and no operating rule is promoted.

The report answers two bounded questions left by R23/R24:
1) what actually composes the conservative portfolio MTM drawdown episode;
2) why the governed 5Y curve remains negative in the early calendar segments.

All economic windows are consumed. Outcomes may be inspected here because this
module is diagnostic and explicitly has no rule authority.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_density_round4 as r4
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r10_contextual_risk as r10
from qore.infrastructure.trader_lab import vt08_index_r15_concurrent_portfolio_validation as r15
from qore.infrastructure.trader_lab import vt08_index_r17_formation_quality_forensics as r17
from qore.infrastructure.trader_lab import vt08_index_r22_concurrent_stable_formation as r22
from qore.infrastructure.trader_lab import vt08_index_r24_open_position_pressure as r24

SCHEMA = "qore.trader_lab.vt08_index_r25_r23_failure_forensics.v1"
IDENTITY = "VT08_INDEX_R25_R23_FAILURE_FORENSICS_001"
STRESS = Decimal("0.05")
_NY = ZoneInfo("America/New_York")


def _quality_tier(opportunity: r4.ExpandedOpportunity) -> str:
    features = r17._feature_values(opportunity)
    if features["poi"] == "fvg" and features["h4_entry_latency"] == "121-180m":
        return "A_FVG_H4_LATENCY_121_180"
    if features["poi"] == "fvg" and features["cisd_latency"] == "4-7":
        return "B_FVG_CISD_LATENCY_4_7"
    if features["poi"] == "fvg" and features["risk_fraction"] == "0.15-0.30%":
        return "C_FVG_RISK_015_030"
    return "BASE_OTHER"


def _labels(
    item: r15.AssignedTrade,
    context: r10.Context,
) -> dict[str, str]:
    signal = item.opportunity.signal
    return {
        "symbol": item.symbol,
        "side": signal.side.value,
        "anchor": str(signal.h4_opened_at.astimezone(_NY).hour),
        "poi": item.opportunity.source_poi_kind,
        "model_kind": signal.model_kind.value,
        "rearm": "rearm" if item.opportunity.rearm_index > 0 else "initial",
        "quality_tier": _quality_tier(item.opportunity),
        "source_day": (
            "opposed" if context.previous_source_day_body_opposed else "not_opposed"
        ),
        "c2_expansion": "yes" if context.c2_expansion else "no",
    }


def _metrics_for(
    rows: Sequence[tuple[r15.AssignedTrade, r10.Context]],
    *,
    weighted: bool,
) -> dict[str, Any]:
    values = tuple(
        (item.outcome.r_multiple - STRESS) * (item.weight if weighted else Decimal("1"))
        for item, _context in rows
    )
    return fx._metrics(values)


def _breakdown(
    rows: Sequence[tuple[r15.AssignedTrade, r10.Context]],
    *,
    labeler: Callable[[r15.AssignedTrade, r10.Context], str],
) -> dict[str, Any]:
    labels = sorted({labeler(item, context) for item, context in rows})
    result: dict[str, Any] = {}
    for label in labels:
        selected = tuple(
            (item, context)
            for item, context in rows
            if labeler(item, context) == label
        )
        result[label] = {
            "sample": len(selected),
            "raw": _metrics_for(selected, weighted=False),
            "governed": _metrics_for(selected, weighted=True),
        }
    return result


def _period_breakdowns(
    rows: Sequence[tuple[r15.AssignedTrade, r10.Context]],
) -> dict[str, Any]:
    dimensions = (
        "symbol",
        "side",
        "anchor",
        "poi",
        "model_kind",
        "rearm",
        "quality_tier",
        "source_day",
        "c2_expansion",
    )
    result: dict[str, Any] = {}
    for name in dimensions:
        def single_label(
            item: r15.AssignedTrade,
            context: r10.Context,
            *,
            key: str = name,
        ) -> str:
            return _labels(item, context)[key]

        result[name] = _breakdown(rows, labeler=single_label)
    for left, right in (
        ("quality_tier", "side"),
        ("quality_tier", "anchor"),
        ("quality_tier", "symbol"),
        ("source_day", "side"),
    ):
        key = f"{left}__{right}"
        def cross_label(
            item: r15.AssignedTrade,
            context: r10.Context,
            *,
            a: str = left,
            b: str = right,
        ) -> str:
            labels = _labels(item, context)
            return f"{labels[a]}|{labels[b]}"

        result[key] = _breakdown(rows, labeler=cross_label)
    return result


def _mtm_forensics(
    assigned: Sequence[r15.AssignedTrade],
    *,
    bars_by_symbol: dict[str, Sequence[Any]],
    opened_by_symbol: dict[str, tuple[datetime, ...]],
    contexts_by_trade_id: dict[int, r10.Context],
) -> dict[str, Any]:
    events: dict[datetime, list[tuple[str, int, Decimal]]] = {}
    for item in assigned:
        events.setdefault(item.signal_at, []).append(
            ("entry", item.trade_id, -STRESS * item.weight)
        )
        bars = bars_by_symbol[item.symbol]
        opened = opened_by_symbol[item.symbol]
        start = bisect.bisect_left(opened, item.signal_at)
        end = bisect.bisect_left(opened, item.exited_at)
        for bar in bars[start:end]:
            if bar.closed_at.astimezone(UTC) >= item.exited_at:
                break
            mark = (r15._signal_adverse_r(item, bar) - STRESS) * item.weight
            events.setdefault(bar.closed_at.astimezone(UTC), []).append(
                ("mark", item.trade_id, mark)
            )
        events.setdefault(item.exited_at, []).append(
            (
                "exit",
                item.trade_id,
                (item.outcome.r_multiple - STRESS) * item.weight,
            )
        )

    by_id = {item.trade_id: item for item in assigned}
    realized = Decimal()
    open_marks: dict[int, Decimal] = {}
    peak = Decimal()
    peak_at: datetime | None = None
    max_dd = Decimal()
    trough_at: datetime | None = None
    trough_peak_at: datetime | None = None
    trough_realized = Decimal()
    trough_open_marks: dict[int, Decimal] = {}

    order = {"exit": 0, "mark": 1, "entry": 2}
    for timestamp in sorted(events):
        for kind, trade_id, value in sorted(
            events[timestamp],
            key=lambda row: (order[row[0]], row[1]),
        ):
            if kind == "exit":
                open_marks.pop(trade_id, None)
                realized += value
            elif kind == "mark":
                if trade_id in open_marks:
                    open_marks[trade_id] = value
            else:
                open_marks[trade_id] = value
        equity = realized + sum(open_marks.values(), Decimal())
        if equity > peak:
            peak = equity
            peak_at = timestamp
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
            trough_at = timestamp
            trough_peak_at = peak_at
            trough_realized = realized
            trough_open_marks = dict(open_marks)

    active_details: list[dict[str, Any]] = []
    for trade_id, weighted_mark in sorted(
        trough_open_marks.items(),
        key=lambda row: row[1],
    ):
        item = by_id[trade_id]
        context = contexts_by_trade_id[trade_id]
        active_details.append(
            {
                "trade_id": trade_id,
                **_labels(item, context),
                "signal_at": item.signal_at.isoformat(),
                "exit_at": item.exited_at.isoformat(),
                "weight": str(item.weight),
                "weighted_adverse_mark_r": str(weighted_mark),
                "terminal_weighted_r": str(
                    (item.outcome.r_multiple - STRESS) * item.weight
                ),
            }
        )

    return {
        "stress_r_per_trade": str(STRESS),
        "marking": "M15_ADVERSE_EXTREME_CONSERVATIVE",
        "max_drawdown_r": str(max_dd),
        "peak_at": trough_peak_at.isoformat() if trough_peak_at else None,
        "trough_at": trough_at.isoformat() if trough_at else None,
        "realized_r_at_trough": str(trough_realized),
        "open_mark_sum_r_at_trough": str(
            sum(trough_open_marks.values(), Decimal())
        ),
        "open_position_count_at_trough": len(trough_open_marks),
        "active_positions_at_trough": active_details,
    }


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
    (
        stream,
        bars_by_symbol,
        indexed_by_symbol,
        opened_by_symbol,
        provenance,
    ) = r15._build_five_year_stream(roots=roots)

    assigned, diagnostics = r22._assign(
        stream,
        quality=r24.BASE_QUALITY,
        risk=r24.BASE_RISK,
    )
    contexts = tuple(
        r10._context(
            opportunity,
            indexed=indexed_by_symbol[opportunity.signal.symbol],
        )
        for opportunity, _outcome in stream
    )
    if len(assigned) != len(contexts):
        raise ValueError("R25 context/assignment cardinality drift")
    paired = tuple(zip(assigned, contexts, strict=True))
    contexts_by_trade_id = {
        item.trade_id: context for item, context in paired
    }

    early = tuple(
        row for row in paired if row[0].exited_at.year in (2018, 2019)
    )
    later = tuple(
        row for row in paired if row[0].exited_at.year in (2020, 2021, 2022, 2023)
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "base_identity": "VT08_INDEX_R23_CONCURRENT_DD_CLOSURE_001",
        "sample": len(assigned),
        "r23_diagnostics": diagnostics,
        "whole_window": {
            "raw": _metrics_for(paired, weighted=False),
            "governed": _metrics_for(paired, weighted=True),
        },
        "early_2018_2019": {
            "sample": len(early),
            "raw": _metrics_for(early, weighted=False),
            "governed": _metrics_for(early, weighted=True),
            "breakdowns": _period_breakdowns(early),
        },
        "later_2020_2023": {
            "sample": len(later),
            "raw": _metrics_for(later, weighted=False),
            "governed": _metrics_for(later, weighted=True),
            "breakdowns": _period_breakdowns(later),
        },
        "max_mtm_drawdown_episode": _mtm_forensics(
            assigned,
            bars_by_symbol=bars_by_symbol,
            opened_by_symbol=opened_by_symbol,
            contexts_by_trade_id=contexts_by_trade_id,
        ),
        "provenance": provenance,
        "governance": {
            "forensics_only": True,
            "candidate_created": False,
            "parameter_search": False,
            "rule_promotion": False,
            "future_outcomes_used_only_for_post_hoc_diagnosis": True,
            "five_year_window_consumed": True,
            "fresh_holdout_claim": False,
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
                "sample": report["sample"],
                "early": report["early_2018_2019"],
                "mtm": report["max_mtm_drawdown_episode"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
