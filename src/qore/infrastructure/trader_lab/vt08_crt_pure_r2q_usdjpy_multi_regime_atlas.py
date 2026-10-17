"""R2-Q six-year multi-regime atlas for USDJPY VT08 CRT PURE.

R2-N falsified the local C1-body repair on the earlier 2020-2022 window.
R2-Q expands the pre-parent state model across three non-overlapping 2Y regimes:

- 2020-2022;
- 2022-2024;
- 2024-2026.

All features are known before C3 opens. The lab does not add an execution filter.
It searches for state descriptions whose economic sign is coherent across all
three blocks before any new candidate is frozen.

Frozen dimensions include short/medium/long volatility and drift, trend
efficiency, C1 geometry/location, and selected low-complexity crosses.
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
from qore.infrastructure.trader_lab.vt08_crt_pure_r2l_usdjpy_regime_forensics import (
    _body_fraction,
    _drift_alignment,
    _mean_range,
    _ratio,
    _trend_efficiency,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import (
    build_parent_crts_for_window,
    load_m5_window,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

IDENTITY = "VT08_CRT_PURE_R2Q_USDJPY_MULTI_REGIME_ATLAS_001"
SCHEMA = "qore.vt08.crt_pure.r2q_usdjpy_multi_regime_atlas.v1"
MARKET = CrtPureMarket.USDJPY
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST

START = datetime(2020, 9, 21, 0, 0, tzinfo=UTC)
BLOCK_2 = datetime(2022, 9, 21, 0, 0, tzinfo=UTC)
BLOCK_3 = datetime(2024, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
FETCH_START = START - timedelta(days=25)

D1_BARS = 96
D5_BARS = 5 * D1_BARS
D20_BARS = 20 * D1_BARS
H4_BARS = 16


@dataclass(frozen=True, slots=True)
class AtlasRecord:
    trade: Model1LabTrade
    vol_1d_to_5d: Decimal
    vol_5d_to_20d: Decimal
    efficiency_1d: Decimal
    efficiency_5d: Decimal
    drift_1d: str
    drift_5d: str
    drift_20d: str
    c1_body_fraction: Decimal
    c1_body_alignment: str
    c1_range_to_5d_h4: Decimal
    c1_directional_position_5d: Decimal
    c2_range_to_c1: Decimal
    manipulation_depth_to_c1: Decimal
    reclaim_depth_to_c1: Decimal


def _h4_ranges(rows: tuple[M15Bar, ...]) -> tuple[int, ...]:
    result: list[int] = []
    for start in range(0, len(rows), H4_BARS):
        block = rows[start : start + H4_BARS]
        if len(block) != H4_BARS:
            continue
        if any(
            right.opened_at - left.opened_at != timedelta(minutes=15)
            for left, right in zip(block[:-1], block[1:], strict=True)
        ):
            continue
        result.append(
            max(item.high_price for item in block)
            - min(item.low_price for item in block)
        )
    return tuple(result)


def _c1_body_alignment(parent: ParentCrt) -> str:
    body = parent.c1.close_price - parent.c1.open_price
    if body == 0:
        return "DOJI"
    aligned = (
        body > 0
        if parent.direction is CrtPureCandidateDirection.BULLISH
        else body < 0
    )
    return "ALIGNED" if aligned else "OPPOSED"


def _directional_position(
    *,
    parent: ParentCrt,
    prior_5d: tuple[M15Bar, ...],
) -> Decimal:
    high = max(bar.high_price for bar in prior_5d)
    low = min(bar.low_price for bar in prior_5d)
    span = high - low
    if span <= 0:
        return Decimal("0.5")
    midpoint = Decimal(parent.c1.high_price + parent.c1.low_price) / Decimal(2)
    if parent.direction is CrtPureCandidateDirection.BULLISH:
        value = (midpoint - Decimal(low)) / Decimal(span)
    else:
        value = (Decimal(high) - midpoint) / Decimal(span)
    return max(Decimal("0"), min(Decimal("1"), value))


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
    times: tuple[datetime, ...],
) -> tuple[
    Decimal,
    Decimal,
    Decimal,
    Decimal,
    str,
    str,
    str,
    Decimal,
    str,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
] | None:
    index = bisect_left(times, parent.c1.opened_at)
    rows_20d = m15[max(0, index - D20_BARS) : index]
    rows_5d = m15[max(0, index - D5_BARS) : index]
    rows_1d = m15[max(0, index - D1_BARS) : index]
    if (
        len(rows_20d) < D20_BARS
        or len(rows_5d) < D5_BARS
        or len(rows_1d) < D1_BARS
    ):
        return None

    mean_1d = _mean_range(rows_1d)
    mean_5d = _mean_range(rows_5d)
    mean_20d = _mean_range(rows_20d)
    h4 = _h4_ranges(rows_5d)
    if not h4:
        return None
    mean_h4 = sum((Decimal(item) for item in h4), Decimal("0")) / Decimal(len(h4))

    c1_range = parent.c1.high_price - parent.c1.low_price
    c2_range = parent.c2.high_price - parent.c2.low_price
    return (
        Decimal("0") if mean_5d <= 0 else mean_1d / mean_5d,
        Decimal("0") if mean_20d <= 0 else mean_5d / mean_20d,
        _trend_efficiency(rows_1d),
        _trend_efficiency(rows_5d),
        _drift_alignment(rows=rows_1d, direction=parent.direction),
        _drift_alignment(rows=rows_5d, direction=parent.direction),
        _drift_alignment(rows=rows_20d, direction=parent.direction),
        _body_fraction(
            parent.c1.open_price,
            parent.c1.close_price,
            parent.c1.high_price,
            parent.c1.low_price,
        ),
        _c1_body_alignment(parent),
        Decimal("0") if mean_h4 <= 0 else Decimal(c1_range) / mean_h4,
        _directional_position(parent=parent, prior_5d=rows_5d),
        _ratio(c2_range, c1_range),
        _manipulation_depth(parent),
        _reclaim_depth(parent),
    )


def _bucket_ratio(value: Decimal, prefix: str) -> str:
    if value < Decimal("0.80"):
        return f"{prefix}_LT_0_80"
    if value < Decimal("1.20"):
        return f"{prefix}_0_80_TO_1_20"
    return f"{prefix}_GE_1_20"


def _bucket_efficiency(value: Decimal, prefix: str) -> str:
    if value < Decimal("0.10"):
        return f"{prefix}_LT_0_10"
    if value < Decimal("0.20"):
        return f"{prefix}_0_10_TO_0_20"
    if value < Decimal("0.35"):
        return f"{prefix}_0_20_TO_0_35"
    return f"{prefix}_GE_0_35"


def _bucket_fraction(value: Decimal, prefix: str) -> str:
    if value < Decimal("0.25"):
        return f"{prefix}_LT_0_25"
    if value < Decimal("0.50"):
        return f"{prefix}_0_25_TO_0_50"
    if value < Decimal("0.75"):
        return f"{prefix}_0_50_TO_0_75"
    return f"{prefix}_GE_0_75"


def _bucket_c1_range(value: Decimal) -> str:
    if value < Decimal("0.75"):
        return "C1R_LT_0_75"
    if value < Decimal("1.25"):
        return "C1R_0_75_TO_1_25"
    if value < Decimal("1.75"):
        return "C1R_1_25_TO_1_75"
    return "C1R_GE_1_75"


def _bucket_c2_range(value: Decimal) -> str:
    if value < Decimal("1.00"):
        return "C2R_LT_1_00"
    if value < Decimal("1.50"):
        return "C2R_1_00_TO_1_50"
    return "C2R_GE_1_50"


def _bucket_depth(value: Decimal, prefix: str) -> str:
    if value < Decimal("0.10"):
        return f"{prefix}_LT_0_10"
    if value < Decimal("0.25"):
        return f"{prefix}_0_10_TO_0_25"
    if value < Decimal("0.50"):
        return f"{prefix}_0_25_TO_0_50"
    return f"{prefix}_GE_0_50"


def _block(
    rows: tuple[AtlasRecord, ...],
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    trades = tuple(
        row.trade
        for row in rows
        if start <= datetime.fromisoformat(row.trade.entry_opened_at) < end
    )
    return _summary(trades)


def _windows(rows: tuple[AtlasRecord, ...]) -> dict[str, Any]:
    return {
        "full_6y": _block(rows, START, END),
        "block_2020_22": _block(rows, START, BLOCK_2),
        "block_2022_24": _block(rows, BLOCK_2, BLOCK_3),
        "block_2024_26": _block(rows, BLOCK_3, END),
    }


def run_atlas() -> tuple[tuple[AtlasRecord, ...], dict[str, Any]]:
    bars = load_m5_window(MARKET, start=FETCH_START, end_exclusive=END)
    parents = build_parent_crts_for_window(
        MARKET,
        bars,
        start=START,
        end_exclusive=END,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    times = tuple(bar.opened_at for bar in m15)
    breaches = build_close_unmitigated_breach_groups(m15)

    records: list[AtlasRecord] = []
    diagnostics: dict[str, int] = defaultdict(int)

    for parent in parents:
        diagnostics["parent_count"] += 1
        context = _context(parent=parent, m15=m15, times=times)
        if context is None:
            diagnostics["insufficient_context"] += 1
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
            diagnostics["no_selected_hypothesis"] += 1
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
            AtlasRecord(
                trade=trade,
                vol_1d_to_5d=context[0],
                vol_5d_to_20d=context[1],
                efficiency_1d=context[2],
                efficiency_5d=context[3],
                drift_1d=context[4],
                drift_5d=context[5],
                drift_20d=context[6],
                c1_body_fraction=context[7],
                c1_body_alignment=context[8],
                c1_range_to_5d_h4=context[9],
                c1_directional_position_5d=context[10],
                c2_range_to_c1=context[11],
                manipulation_depth_to_c1=context[12],
                reclaim_depth_to_c1=context[13],
            )
        )
        diagnostics["record_created"] += 1

    frozen = tuple(sorted(records, key=lambda row: row.trade.entry_opened_at))
    groups: dict[str, dict[str, list[AtlasRecord]]] = {
        "vol_1d_to_5d": defaultdict(list),
        "vol_5d_to_20d": defaultdict(list),
        "efficiency_1d": defaultdict(list),
        "efficiency_5d": defaultdict(list),
        "drift_1d": defaultdict(list),
        "drift_5d": defaultdict(list),
        "drift_20d": defaultdict(list),
        "c1_body_fraction": defaultdict(list),
        "c1_body_alignment": defaultdict(list),
        "c1_range_to_5d_h4": defaultdict(list),
        "c1_directional_position_5d": defaultdict(list),
        "c2_range_to_c1": defaultdict(list),
        "manipulation_depth": defaultdict(list),
        "reclaim_depth": defaultdict(list),
        "vol5_20_x_drift5": defaultdict(list),
        "eff5_x_drift5": defaultdict(list),
        "c1body_x_drift5": defaultdict(list),
    }

    for record in frozen:
        vol1 = _bucket_ratio(record.vol_1d_to_5d, "VOL1D5D")
        vol5 = _bucket_ratio(record.vol_5d_to_20d, "VOL5D20D")
        eff1 = _bucket_efficiency(record.efficiency_1d, "EFF1D")
        eff5 = _bucket_efficiency(record.efficiency_5d, "EFF5D")
        body = _bucket_fraction(record.c1_body_fraction, "C1BODY")
        groups["vol_1d_to_5d"][vol1].append(record)
        groups["vol_5d_to_20d"][vol5].append(record)
        groups["efficiency_1d"][eff1].append(record)
        groups["efficiency_5d"][eff5].append(record)
        groups["drift_1d"][record.drift_1d].append(record)
        groups["drift_5d"][record.drift_5d].append(record)
        groups["drift_20d"][record.drift_20d].append(record)
        groups["c1_body_fraction"][body].append(record)
        groups["c1_body_alignment"][record.c1_body_alignment].append(record)
        groups["c1_range_to_5d_h4"][
            _bucket_c1_range(record.c1_range_to_5d_h4)
        ].append(record)
        groups["c1_directional_position_5d"][
            _bucket_fraction(record.c1_directional_position_5d, "POS5D")
        ].append(record)
        groups["c2_range_to_c1"][_bucket_c2_range(record.c2_range_to_c1)].append(record)
        groups["manipulation_depth"][
            _bucket_depth(record.manipulation_depth_to_c1, "MANIP")
        ].append(record)
        groups["reclaim_depth"][
            _bucket_fraction(record.reclaim_depth_to_c1, "RECLAIM")
        ].append(record)
        groups["vol5_20_x_drift5"][f"{vol5}|{record.drift_5d}"].append(record)
        groups["eff5_x_drift5"][f"{eff5}|{record.drift_5d}"].append(record)
        groups["c1body_x_drift5"][f"{body}|{record.drift_5d}"].append(record)

    dimensions = {
        dimension: {
            label: _windows(tuple(rows))
            for label, rows in sorted(labels.items())
        }
        for dimension, labels in groups.items()
    }

    coherent: list[dict[str, Any]] = []
    for dimension, labels in dimensions.items():
        for label, window in labels.items():
            blocks = (
                window["block_2020_22"],
                window["block_2022_24"],
                window["block_2024_26"],
            )
            if all(
                int(block["trades"]) >= 8 and float(block["total_r"]) > 0
                for block in blocks
            ):
                coherent.append(
                    {
                        "dimension": dimension,
                        "label": label,
                        "full_6y": window["full_6y"],
                        "block_2020_22": blocks[0],
                        "block_2022_24": blocks[1],
                        "block_2024_26": blocks[2],
                    }
                )

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET.value,
        "start": START.isoformat(),
        "block_2": BLOCK_2.isoformat(),
        "block_3": BLOCK_3.isoformat(),
        "end": END.isoformat(),
        "base_competition_policy": BASE_POLICY.value,
        "context_known_before_c3": True,
        "feature_family_frozen_before_results": True,
        "diagnostics": dict(diagnostics),
        "overall": _windows(frozen),
        "dimensions": dimensions,
        "coherent_positive_buckets": coherent,
        "coherence_rule": "MIN_8_TRADES_AND_POSITIVE_R_IN_EACH_2Y_BLOCK",
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

    records, report = run_atlas()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "records.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), sort_keys=True, default=str) + "\n")
    print("CRT_R2Q_USDJPY_ATLAS_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
