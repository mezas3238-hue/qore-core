"""R2-L pre-parent regime forensics for USDJPY VT08 CRT PURE.

R2-K showed that the current entry-context feature family changes sign across
2022-2024 and 2024-2026. R2-L moves one causal layer upward and characterizes
market state that is fully known before C3 opens.

Methodology and R2-G competition are unchanged. This lab does not add a filter.

Frozen regime dimensions:
- 24h / 4d realized M15 range ratio;
- 24h directional efficiency;
- 24h directional drift aligned/opposed to the parent CRT;
- C1 range relative to prior 24h H4-like ranges;
- C1 body fraction;
- C2 range relative to C1;
- C2 body fraction;
- C2 manipulation depth relative to C1;
- C2 reclaim depth inside C1;
- selected low-complexity cross dimensions.

Research only. No execution/capital authority.
"""

from __future__ import annotations

import argparse
import json
from bisect import bisect_left
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    Model1LabTrade,
    ParentCrt,
    _resolve_trade,
    _summary,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2e_source_multiplicity_census import (
    _aligned_sources,
    _c3_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    CompetitionPolicy,
    select_competing_hypothesis,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import (
    build_parent_crts_for_window,
    load_m5_window,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

IDENTITY = "VT08_CRT_PURE_R2L_USDJPY_PRE_PARENT_REGIME_FORENSICS_001"
SCHEMA = "qore.vt08.crt_pure.r2l_usdjpy_pre_parent_regime_forensics.v1"

MARKET = CrtPureMarket.USDJPY
START = datetime(2022, 9, 21, 0, 0, tzinfo=UTC)
REGIME_FOLD = datetime(2024, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
FETCH_START = START - timedelta(days=7)

BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST
FAST_BARS = 96
SLOW_BARS = 384
H4_M15_BARS = 16


@dataclass(frozen=True, slots=True)
class RegimeRecord:
    trade: Model1LabTrade
    volatility_ratio_24h_to_4d: Decimal
    trend_efficiency_24h: Decimal
    drift_alignment: str
    c1_range_to_recent_h4: Decimal
    c1_body_fraction: Decimal
    c2_range_to_c1: Decimal
    c2_body_fraction: Decimal
    manipulation_depth_to_c1: Decimal
    reclaim_depth_to_c1: Decimal


def _ratio(numerator: int | Decimal, denominator: int | Decimal) -> Decimal:
    n = Decimal(numerator)
    d = Decimal(denominator)
    if d <= 0:
        return Decimal("0")
    return n / d


def _body_fraction(open_price: int, close_price: int, high_price: int, low_price: int) -> Decimal:
    return _ratio(abs(close_price - open_price), high_price - low_price)


def _mean_range(rows: tuple[M15Bar, ...]) -> Decimal:
    if not rows:
        return Decimal("0")
    return sum(
        (Decimal(row.high_price - row.low_price) for row in rows),
        Decimal("0"),
    ) / Decimal(len(rows))


def _h4_like_ranges(rows: tuple[M15Bar, ...]) -> tuple[int, ...]:
    values: list[int] = []
    for start in range(0, len(rows), H4_M15_BARS):
        block = rows[start : start + H4_M15_BARS]
        if len(block) != H4_M15_BARS:
            continue
        if any(
            right.opened_at - left.opened_at != timedelta(minutes=15)
            for left, right in zip(block[:-1], block[1:], strict=True)
        ):
            continue
        values.append(
            max(item.high_price for item in block)
            - min(item.low_price for item in block)
        )
    return tuple(values)


def _trend_efficiency(rows: tuple[M15Bar, ...]) -> Decimal:
    if len(rows) < 2:
        return Decimal("0")
    net = abs(rows[-1].close_price - rows[0].open_price)
    path = abs(rows[0].close_price - rows[0].open_price) + sum(
        abs(right.close_price - left.close_price)
        for left, right in zip(rows[:-1], rows[1:], strict=True)
    )
    if path <= 0:
        return Decimal("0")
    return _ratio(net, path)


def _drift_alignment(
    *,
    rows: tuple[M15Bar, ...],
    direction: CrtPureCandidateDirection,
) -> str:
    if not rows:
        return "UNKNOWN"
    drift = rows[-1].close_price - rows[0].open_price
    if drift == 0:
        return "FLAT"
    aligned = (
        drift > 0
        if direction is CrtPureCandidateDirection.BULLISH
        else drift < 0
    )
    return "ALIGNED" if aligned else "OPPOSED"


def _manipulation_depth(parent: ParentCrt) -> Decimal:
    c1_range = parent.c1.high_price - parent.c1.low_price
    if parent.direction is CrtPureCandidateDirection.BULLISH:
        depth = parent.c1.low_price - parent.c2.low_price
    else:
        depth = parent.c2.high_price - parent.c1.high_price
    return _ratio(max(depth, 0), c1_range)


def _reclaim_depth(parent: ParentCrt) -> Decimal:
    c1_range = parent.c1.high_price - parent.c1.low_price
    if parent.direction is CrtPureCandidateDirection.BULLISH:
        depth = parent.c2.close_price - parent.c1.low_price
    else:
        depth = parent.c1.high_price - parent.c2.close_price
    return _ratio(max(depth, 0), c1_range)


def _context(
    *,
    parent: ParentCrt,
    m15: tuple[M15Bar, ...],
    m15_times: tuple[datetime, ...],
) -> tuple[Decimal, Decimal, str, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal] | None:
    index = bisect_left(m15_times, parent.c1.opened_at)
    slow = m15[max(0, index - SLOW_BARS) : index]
    fast = m15[max(0, index - FAST_BARS) : index]
    if len(slow) < SLOW_BARS or len(fast) < FAST_BARS:
        return None

    fast_mean = _mean_range(fast)
    slow_mean = _mean_range(slow)
    volatility_ratio = (
        Decimal("0") if slow_mean <= 0 else fast_mean / slow_mean
    )

    h4_ranges = _h4_like_ranges(fast)
    if not h4_ranges:
        return None
    mean_h4 = sum((Decimal(value) for value in h4_ranges), Decimal("0")) / Decimal(
        len(h4_ranges)
    )
    c1_range = parent.c1.high_price - parent.c1.low_price
    c2_range = parent.c2.high_price - parent.c2.low_price

    return (
        volatility_ratio,
        _trend_efficiency(fast),
        _drift_alignment(rows=fast, direction=parent.direction),
        Decimal("0") if mean_h4 <= 0 else Decimal(c1_range) / mean_h4,
        _body_fraction(
            parent.c1.open_price,
            parent.c1.close_price,
            parent.c1.high_price,
            parent.c1.low_price,
        ),
        _ratio(c2_range, c1_range),
        _body_fraction(
            parent.c2.open_price,
            parent.c2.close_price,
            parent.c2.high_price,
            parent.c2.low_price,
        ),
        _manipulation_depth(parent),
        _reclaim_depth(parent),
    )


def _bucket_volatility(value: Decimal) -> str:
    if value < Decimal("0.80"):
        return "VOL_LT_0_80"
    if value < Decimal("1.20"):
        return "VOL_0_80_TO_1_20"
    if value < Decimal("1.60"):
        return "VOL_1_20_TO_1_60"
    return "VOL_GE_1_60"


def _bucket_efficiency(value: Decimal) -> str:
    if value < Decimal("0.20"):
        return "EFF_LT_0_20"
    if value < Decimal("0.40"):
        return "EFF_0_20_TO_0_40"
    if value < Decimal("0.60"):
        return "EFF_0_40_TO_0_60"
    return "EFF_GE_0_60"


def _bucket_c1_ratio(value: Decimal) -> str:
    if value < Decimal("0.75"):
        return "C1R_LT_0_75"
    if value < Decimal("1.25"):
        return "C1R_0_75_TO_1_25"
    if value < Decimal("1.75"):
        return "C1R_1_25_TO_1_75"
    return "C1R_GE_1_75"


def _bucket_c2_ratio(value: Decimal) -> str:
    if value < Decimal("1.00"):
        return "C2R_LT_1_00"
    if value < Decimal("1.50"):
        return "C2R_1_00_TO_1_50"
    if value < Decimal("2.00"):
        return "C2R_1_50_TO_2_00"
    return "C2R_GE_2_00"


def _bucket_fraction(value: Decimal, prefix: str) -> str:
    if value < Decimal("0.25"):
        return f"{prefix}_LT_0_25"
    if value < Decimal("0.50"):
        return f"{prefix}_0_25_TO_0_50"
    if value < Decimal("0.75"):
        return f"{prefix}_0_50_TO_0_75"
    return f"{prefix}_GE_0_75"


def _bucket_depth(value: Decimal, prefix: str) -> str:
    if value < Decimal("0.10"):
        return f"{prefix}_LT_0_10"
    if value < Decimal("0.25"):
        return f"{prefix}_0_10_TO_0_25"
    if value < Decimal("0.50"):
        return f"{prefix}_0_25_TO_0_50"
    return f"{prefix}_GE_0_50"


def _slice(
    records: tuple[RegimeRecord, ...],
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    rows = tuple(
        record.trade
        for record in records
        if start <= datetime.fromisoformat(record.trade.entry_opened_at) < end
    )
    return _summary(rows)


def _three_windows(records: tuple[RegimeRecord, ...]) -> dict[str, Any]:
    return {
        "full_4y": _slice(records, START, END),
        "older_2y": _slice(records, START, REGIME_FOLD),
        "recent_2y": _slice(records, REGIME_FOLD, END),
    }


def run_forensics() -> tuple[tuple[RegimeRecord, ...], dict[str, Any]]:
    bars = load_m5_window(MARKET, start=FETCH_START, end_exclusive=END)
    parents = build_parent_crts_for_window(
        MARKET,
        bars,
        start=START,
        end_exclusive=END,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    m15_times = tuple(bar.opened_at for bar in m15)
    breaches = build_close_unmitigated_breach_groups(m15)

    records: list[RegimeRecord] = []
    diagnostics: dict[str, int] = defaultdict(int)

    for parent in parents:
        diagnostics["parent_count"] += 1
        context = _context(parent=parent, m15=m15, m15_times=m15_times)
        if context is None:
            diagnostics["insufficient_pre_parent_context"] += 1
            continue

        c3_m15 = _c3_m15(parent, m15_by_time)
        observations = _aligned_sources(
            parent=parent,
            c3_m15=c3_m15,
            breaches=breaches,
        )
        selected = select_competing_hypothesis(
            policy=BASE_POLICY,
            parent=parent,
            observations=observations,
            c3_m15=c3_m15,
        )
        if selected is None:
            diagnostics["no_selected_confirmed_hypothesis"] += 1
            continue

        observation, confirmation, entry = selected
        trade = _resolve_trade(
            parent=parent,
            group=observation.group,
            confirmation=confirmation,
            entry_bar=entry,
            c3_m15=c3_m15,
        )
        if trade is None:
            diagnostics["invalid_risk_geometry"] += 1
            continue

        records.append(
            RegimeRecord(
                trade=trade,
                volatility_ratio_24h_to_4d=context[0],
                trend_efficiency_24h=context[1],
                drift_alignment=context[2],
                c1_range_to_recent_h4=context[3],
                c1_body_fraction=context[4],
                c2_range_to_c1=context[5],
                c2_body_fraction=context[6],
                manipulation_depth_to_c1=context[7],
                reclaim_depth_to_c1=context[8],
            )
        )
        diagnostics["record_created"] += 1

    frozen = tuple(sorted(records, key=lambda item: item.trade.entry_opened_at))
    groups: dict[str, dict[str, list[RegimeRecord]]] = {
        "volatility_ratio": defaultdict(list),
        "trend_efficiency": defaultdict(list),
        "drift_alignment": defaultdict(list),
        "c1_range_ratio": defaultdict(list),
        "c1_body_fraction": defaultdict(list),
        "c2_range_to_c1": defaultdict(list),
        "c2_body_fraction": defaultdict(list),
        "manipulation_depth": defaultdict(list),
        "reclaim_depth": defaultdict(list),
        "volatility_x_drift": defaultdict(list),
        "efficiency_x_drift": defaultdict(list),
        "c1range_x_c2range": defaultdict(list),
    }

    for record in frozen:
        vol = _bucket_volatility(record.volatility_ratio_24h_to_4d)
        eff = _bucket_efficiency(record.trend_efficiency_24h)
        c1r = _bucket_c1_ratio(record.c1_range_to_recent_h4)
        c2r = _bucket_c2_ratio(record.c2_range_to_c1)
        groups["volatility_ratio"][vol].append(record)
        groups["trend_efficiency"][eff].append(record)
        groups["drift_alignment"][record.drift_alignment].append(record)
        groups["c1_range_ratio"][c1r].append(record)
        groups["c1_body_fraction"][
            _bucket_fraction(record.c1_body_fraction, "C1BODY")
        ].append(record)
        groups["c2_range_to_c1"][c2r].append(record)
        groups["c2_body_fraction"][
            _bucket_fraction(record.c2_body_fraction, "C2BODY")
        ].append(record)
        groups["manipulation_depth"][
            _bucket_depth(record.manipulation_depth_to_c1, "MANIP")
        ].append(record)
        groups["reclaim_depth"][
            _bucket_fraction(record.reclaim_depth_to_c1, "RECLAIM")
        ].append(record)
        groups["volatility_x_drift"][f"{vol}|{record.drift_alignment}"].append(record)
        groups["efficiency_x_drift"][f"{eff}|{record.drift_alignment}"].append(record)
        groups["c1range_x_c2range"][f"{c1r}|{c2r}"].append(record)

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET.value,
        "start": START.isoformat(),
        "regime_fold": REGIME_FOLD.isoformat(),
        "end": END.isoformat(),
        "base_competition_policy": BASE_POLICY.value,
        "context_known_before_c3": True,
        "bucket_family_frozen_before_results": True,
        "diagnostics": dict(diagnostics),
        "overall": _three_windows(frozen),
        "dimensions": {
            dimension: {
                label: _three_windows(tuple(rows))
                for label, rows in sorted(labels.items())
            }
            for dimension, labels in groups.items()
        },
        "filter_promoted": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return frozen, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    records, report = run_forensics()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "records.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), sort_keys=True, default=str) + "\n")
    print("CRT_R2L_USDJPY_REGIME_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
