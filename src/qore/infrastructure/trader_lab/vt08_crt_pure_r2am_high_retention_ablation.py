"""R2-AM high-retention context ablation for VT08 CRT PURE FX.

R2-AH shows that the narrow efficiency regimes recover edge by discarding most
of the naturally valid CRT + Model #1 population. R2-AM asks a different
question:

Can one already-known pre-parent context bucket be excluded while retaining at
least 60% of the unfiltered valid-trade population and repairing annual
stability?

This is a single-bucket ablation screen, not a promotion engine. It reuses the
same context taxonomy and the reusable CORE single-bucket ablation helper.

No timing, entry, stop, target, expiry or competition rule changes.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
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
from qore.infrastructure.trader_lab.vt08_crt_pure_r2q_usdjpy_multi_regime_atlas import (
    _bucket_c1_range,
    _bucket_c2_range,
    _bucket_depth,
    _bucket_efficiency,
    _bucket_fraction,
    _bucket_ratio,
    _context,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_single_bucket_ablation import (
    screen_single_bucket_ablations,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import (
    build_parent_crts_for_window,
    load_m5_window,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2AM_HIGH_RETENTION_ABLATION_001"
SCHEMA = "qore.vt08.crt_pure.r2am_high_retention_ablation.v1"
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST
MIN_RETENTION = 0.60


@dataclass(frozen=True, slots=True)
class MarketConfig:
    market: CrtPureMarket
    start: datetime


CONFIGS: dict[CrtPureMarket, MarketConfig] = {
    CrtPureMarket.AUDUSD: MarketConfig(
        market=CrtPureMarket.AUDUSD,
        start=datetime(2016, 9, 21, 0, 0, tzinfo=UTC),
    ),
    CrtPureMarket.USDJPY: MarketConfig(
        market=CrtPureMarket.USDJPY,
        start=datetime(2014, 9, 21, 0, 0, tzinfo=UTC),
    ),
}


@dataclass(frozen=True, slots=True)
class ContextRecord:
    trade: Model1LabTrade
    vol_1d_to_5d: Any
    vol_5d_to_20d: Any
    efficiency_1d: Any
    efficiency_5d: Any
    drift_1d: str
    drift_5d: str
    drift_20d: str
    c1_body_fraction: Any
    c1_body_alignment: str
    c1_range_to_5d_h4: Any
    c1_directional_position_5d: Any
    c2_range_to_c1: Any
    manipulation_depth_to_c1: Any
    reclaim_depth_to_c1: Any


def _annual_boundaries(start: datetime) -> tuple[datetime, ...]:
    return tuple(
        datetime(year, 9, 21, 0, 0, tzinfo=UTC)
        for year in range(start.year, END.year + 1)
    )


def _record_window(
    records: tuple[ContextRecord, ...],
    start: datetime,
    end: datetime,
) -> tuple[ContextRecord, ...]:
    return tuple(
        record
        for record in records
        if start <= datetime.fromisoformat(record.trade.entry_opened_at) < end
    )


def _summary_records(records: tuple[ContextRecord, ...]) -> dict[str, Any]:
    return _summary(tuple(record.trade for record in records))


def _annual(
    records: tuple[ContextRecord, ...],
    start: datetime,
) -> dict[str, dict[str, Any]]:
    boundaries = _annual_boundaries(start)
    return {
        f"{left.year}_{right.year}": _summary_records(
            _record_window(records, left, right)
        )
        for left, right in zip(
            boundaries[:-1],
            boundaries[1:],
            strict=True,
        )
    }


def run_ablation(market: CrtPureMarket) -> tuple[tuple[ContextRecord, ...], dict[str, Any]]:
    config = CONFIGS[market]
    bars = load_m5_window(
        market,
        start=config.start - timedelta(days=25),
        end_exclusive=END,
    )
    parents = build_parent_crts_for_window(
        market,
        bars,
        start=config.start,
        end_exclusive=END,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    times = tuple(bar.opened_at for bar in m15)
    breaches = build_close_unmitigated_breach_groups(m15)

    records: list[ContextRecord] = []
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
            diagnostics["invalid_midpoint_geometry"] += 1
            continue

        records.append(
            ContextRecord(
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
    groups: dict[str, dict[str, list[ContextRecord]]] = {
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
        "direction": defaultdict(list),
        "timing_triplet": defaultdict(list),
    }

    for record in frozen:
        groups["vol_1d_to_5d"][
            _bucket_ratio(record.vol_1d_to_5d, "VOL1D5D")
        ].append(record)
        groups["vol_5d_to_20d"][
            _bucket_ratio(record.vol_5d_to_20d, "VOL5D20D")
        ].append(record)
        groups["efficiency_1d"][
            _bucket_efficiency(record.efficiency_1d, "EFF1D")
        ].append(record)
        groups["efficiency_5d"][
            _bucket_efficiency(record.efficiency_5d, "EFF5D")
        ].append(record)
        groups["drift_1d"][record.drift_1d].append(record)
        groups["drift_5d"][record.drift_5d].append(record)
        groups["drift_20d"][record.drift_20d].append(record)
        groups["c1_body_fraction"][
            _bucket_fraction(record.c1_body_fraction, "C1BODY")
        ].append(record)
        groups["c1_body_alignment"][record.c1_body_alignment].append(record)
        groups["c1_range_to_5d_h4"][
            _bucket_c1_range(record.c1_range_to_5d_h4)
        ].append(record)
        groups["c1_directional_position_5d"][
            _bucket_fraction(record.c1_directional_position_5d, "POS5D")
        ].append(record)
        groups["c2_range_to_c1"][
            _bucket_c2_range(record.c2_range_to_c1)
        ].append(record)
        groups["manipulation_depth"][
            _bucket_depth(record.manipulation_depth_to_c1, "MANIP")
        ].append(record)
        groups["reclaim_depth"][
            _bucket_fraction(record.reclaim_depth_to_c1, "RECLAIM")
        ].append(record)
        groups["direction"][record.trade.parent_direction].append(record)
        groups["timing_triplet"][f"T{record.trade.timing_triplet}"].append(record)

    overall_annual = _annual(frozen, config.start)
    dimensions: dict[str, dict[str, dict[str, Any]]] = {
        dimension: {
            label: {
                "full_window": _summary_records(tuple(rows)),
                "annual": _annual(tuple(rows), config.start),
            }
            for label, rows in sorted(labels.items())
        }
        for dimension, labels in groups.items()
    }

    minimum_residual_trades = math.ceil(len(frozen) * MIN_RETENTION)
    screened = screen_single_bucket_ablations(
        overall_annual=overall_annual,
        dimensions=dimensions,
        minimum_residual_trades=minimum_residual_trades,
    )

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "window_start": config.start.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "base_competition_policy": BASE_POLICY.value,
        "efficiency_regime_filter": "OFF",
        "minimum_residual_retention": MIN_RETENTION,
        "minimum_residual_trades": minimum_residual_trades,
        "diagnostics": dict(diagnostics),
        "overall": {
            "full_window": _summary_records(frozen),
            "annual": overall_annual,
        },
        "dimensions": dimensions,
        "high_retention_single_bucket_ablations": [
            asdict(item) for item in screened
        ],
        "automatic_promotion": False,
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
    parser.add_argument("market", choices=[item.value for item in CONFIGS])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    market = CrtPureMarket(args.market)
    records, report = run_ablation(market)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n"
    )
    with (args.output / "records.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(
                json.dumps(asdict(record), sort_keys=True, default=str) + "\n"
            )
    print("CRT_R2AM_ABLATION_JSON=" + json.dumps(report, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
