"""R2-X six-year multi-regime atlas for AUDUSD VT08 CRT PURE.

R2-S falsified AUD_G1 on 2020-2022. R2-X reuses the exact pre-parent feature
family frozen by R2-Q and applies it to AUDUSD across three non-overlapping 2Y
regimes. No new feature or execution rule is introduced.

Research only. No filter is promoted automatically.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
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
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import (
    build_parent_crts_for_window,
    load_m5_window,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2X_AUDUSD_MULTI_REGIME_ATLAS_001"
SCHEMA = "qore.vt08.crt_pure.r2x_audusd_multi_regime_atlas.v1"
MARKET = CrtPureMarket.AUDUSD
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST

START = datetime(2020, 9, 21, 0, 0, tzinfo=UTC)
BLOCK_2 = datetime(2022, 9, 21, 0, 0, tzinfo=UTC)
BLOCK_3 = datetime(2024, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
FETCH_START = START - timedelta(days=25)


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
        groups["c2_range_to_c1"][
            _bucket_c2_range(record.c2_range_to_c1)
        ].append(record)
        groups["manipulation_depth"][
            _bucket_depth(record.manipulation_depth_to_c1, "MANIP")
        ].append(record)
        groups["reclaim_depth"][
            _bucket_fraction(record.reclaim_depth_to_c1, "RECLAIM")
        ].append(record)
        groups["vol5_20_x_drift5"][
            f"{vol5}|{record.drift_5d}"
        ].append(record)
        groups["eff5_x_drift5"][
            f"{eff5}|{record.drift_5d}"
        ].append(record)
        groups["c1body_x_drift5"][
            f"{body}|{record.drift_5d}"
        ].append(record)

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
        "feature_family_reused_exactly_from_r2q": True,
        "context_known_before_c3": True,
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
            handle.write(
                json.dumps(asdict(record), sort_keys=True, default=str) + "\n"
            )
    print("CRT_R2X_AUDUSD_ATLAS_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
