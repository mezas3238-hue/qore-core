"""R2-AC within-regime failure forensics for USDJPY.

The frozen EFF5D 0.10-0.20 regime is positive across four consumed 2Y blocks,
but R2-W proved that 2019-2020 is negative. This lab does not move the EFF5D
bounds. It conditions on the exact frozen regime and asks which already-known
pre-parent dimensions distinguish the losing annual slice from the rest of
2018-2026.

No filter is promoted automatically.
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

IDENTITY = "VT08_CRT_PURE_R2AC_USDJPY_WITHIN_REGIME_FAILURE_001"
SCHEMA = "qore.vt08.crt_pure.r2ac_usdjpy_within_regime_failure.v1"
MARKET = CrtPureMarket.USDJPY
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST

START = datetime(2018, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
FETCH_START = START - timedelta(days=25)
BAD_START = datetime(2019, 9, 21, 0, 0, tzinfo=UTC)
BAD_END = datetime(2020, 9, 21, 0, 0, tzinfo=UTC)
EFF5_LOW = Decimal("0.10")
EFF5_HIGH = Decimal("0.20")

YEAR_BOUNDARIES: tuple[datetime, ...] = tuple(
    datetime(year, 9, 21, 0, 0, tzinfo=UTC)
    for year in range(2018, 2027)
)


@dataclass(frozen=True, slots=True)
class FailureRecord:
    trade: Model1LabTrade
    vol_1d_to_5d: Decimal
    vol_5d_to_20d: Decimal
    efficiency_1d: Decimal
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


def _window(
    records: tuple[FailureRecord, ...],
    start: datetime,
    end: datetime,
) -> tuple[FailureRecord, ...]:
    return tuple(
        record
        for record in records
        if start <= datetime.fromisoformat(record.trade.entry_opened_at) < end
    )


def _summary_records(records: tuple[FailureRecord, ...]) -> dict[str, Any]:
    return _summary(tuple(record.trade for record in records))


def _annual(records: tuple[FailureRecord, ...]) -> dict[str, dict[str, Any]]:
    return {
        f"{left.year}_{right.year}": _summary_records(_window(records, left, right))
        for left, right in zip(
            YEAR_BOUNDARIES[:-1],
            YEAR_BOUNDARIES[1:],
            strict=True,
        )
    }


def _contrast(records: tuple[FailureRecord, ...]) -> dict[str, Any]:
    bad = _window(records, BAD_START, BAD_END)
    other = tuple(
        record
        for record in records
        if not BAD_START <= datetime.fromisoformat(record.trade.entry_opened_at) < BAD_END
    )
    return {
        "full_8y": _summary_records(records),
        "bad_2019_20": _summary_records(bad),
        "other_7y": _summary_records(other),
        "annual": _annual(records),
    }


def run_forensics() -> tuple[tuple[FailureRecord, ...], dict[str, Any]]:
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

    records: list[FailureRecord] = []
    diagnostics: dict[str, int] = defaultdict(int)

    for parent in parents:
        diagnostics["parent_count"] += 1
        context = _context(parent=parent, m15=m15, times=times)
        if context is None:
            diagnostics["insufficient_context"] += 1
            continue
        efficiency_5d = context[3]
        if not EFF5_LOW <= efficiency_5d < EFF5_HIGH:
            diagnostics["outside_frozen_eff5_regime"] += 1
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
            FailureRecord(
                trade=trade,
                vol_1d_to_5d=context[0],
                vol_5d_to_20d=context[1],
                efficiency_1d=context[2],
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
    groups: dict[str, dict[str, list[FailureRecord]]] = {
        "vol_1d_to_5d": defaultdict(list),
        "vol_5d_to_20d": defaultdict(list),
        "efficiency_1d": defaultdict(list),
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

    dimensions = {
        dimension: {
            label: _contrast(tuple(rows))
            for label, rows in sorted(labels.items())
        }
        for dimension, labels in groups.items()
    }

    explanatory_clues: list[dict[str, Any]] = []
    for dimension, labels in dimensions.items():
        for label, result in labels.items():
            bad = result["bad_2019_20"]
            other = result["other_7y"]
            if (
                int(bad["trades"]) >= 2
                and float(bad["total_r"]) < 0
                and int(other["trades"]) >= 12
                and float(other["total_r"]) > 0
            ):
                explanatory_clues.append(
                    {
                        "dimension": dimension,
                        "label": label,
                        "bad_2019_20": bad,
                        "other_7y": other,
                        "full_8y": result["full_8y"],
                    }
                )

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "bad_year_start": BAD_START.isoformat(),
        "bad_year_end_exclusive": BAD_END.isoformat(),
        "frozen_eff5_bounds": [str(EFF5_LOW), str(EFF5_HIGH)],
        "same_feature_family_as_r2q": True,
        "no_filter_promoted": True,
        "diagnostics": dict(diagnostics),
        "overall_regime": _contrast(frozen),
        "dimensions": dimensions,
        "explanatory_clues": explanatory_clues,
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
    print("CRT_R2AC_USDJPY_FAILURE_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
