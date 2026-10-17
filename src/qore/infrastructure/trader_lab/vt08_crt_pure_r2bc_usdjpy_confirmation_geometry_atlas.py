"""R2-BC USDJPY independent confirmation-geometry atlas.

The feature family is generic causal engineering reused from R2-AX, but no
AUDUSD state, threshold winner, exclusion or economic conclusion is transferred.

USDJPY learns USDJPY on its own consumed 2014-2026 high-density population.

No filter is promoted. Research only.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
    _summary,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2af_audusd_target_family import (
    TARGET_MULTIPLE,
    TargetArm,
    _resolve_fixed_target,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2aq_high_density_historical_validation import (
    ValidationWindow,
    _rolling_parents,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2ax_audusd_confirmation_geometry_atlas import (
    _features,
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
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import load_m5_window
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2BC_USDJPY_CONFIRMATION_GEOMETRY_ATLAS_001"
SCHEMA = "qore.vt08.crt_pure.r2bc_usdjpy_confirmation_geometry_atlas.v1"
MARKET = CrtPureMarket.USDJPY
START = datetime(2014, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
YEARS = 12
ARM = TargetArm.FIXED_1_5R
MULTIPLE = TARGET_MULTIPLE[ARM]
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST
MIN_BUCKET_TRADES = 72
MIN_SUPPORTED_YEARS = 7


@dataclass(frozen=True, slots=True)
class ConfirmationRecord:
    trade: Model1LabTrade
    buckets: tuple[tuple[str, str], ...]


def _year_start(year: int) -> datetime:
    return datetime(year, 9, 21, 0, 0, tzinfo=UTC)


def _slice(
    records: tuple[ConfirmationRecord, ...],
    start: datetime,
    end: datetime,
) -> tuple[ConfirmationRecord, ...]:
    return tuple(
        record
        for record in records
        if start <= datetime.fromisoformat(record.trade.entry_opened_at) < end
    )


def _summary_records(
    records: tuple[ConfirmationRecord, ...],
) -> dict[str, Any]:
    return _summary(tuple(record.trade for record in records))


def _annual(
    records: tuple[ConfirmationRecord, ...],
) -> dict[str, dict[str, Any]]:
    return {
        f"{year}_{year + 1}": _summary_records(
            _slice(records, _year_start(year), _year_start(year + 1))
        )
        for year in range(START.year, END.year)
    }


def _dimension_report(
    records: tuple[ConfirmationRecord, ...],
) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, list[ConfirmationRecord]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for record in records:
        for dimension, label in record.buckets:
            groups[dimension][label].append(record)

    report: dict[str, dict[str, Any]] = {}
    for dimension, labels in sorted(groups.items()):
        report[dimension] = {}
        for label, rows in sorted(labels.items()):
            frozen = tuple(rows)
            annual = _annual(frozen)
            report[dimension][label] = {
                "full_12y": _summary_records(frozen),
                "annual": annual,
                "supported_years": sum(
                    int(item["trades"]) >= 5 for item in annual.values()
                ),
                "negative_years": sum(
                    float(item["total_r"]) < 0
                    for item in annual.values()
                    if int(item["trades"]) > 0
                ),
            }
    return report


def _stable_toxic(
    dimensions: dict[str, dict[str, Any]],
    total_trades: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dimension, labels in dimensions.items():
        for label, report in labels.items():
            full = report["full_12y"]
            trades = int(full["trades"])
            total_r = float(full["total_r"])
            if trades < MIN_BUCKET_TRADES or total_r >= 0:
                continue
            if int(report["supported_years"]) < MIN_SUPPORTED_YEARS:
                continue
            retention = 1.0 - trades / total_trades
            if retention < 0.70:
                continue
            rows.append(
                {
                    "dimension": dimension,
                    "label": label,
                    "trades": trades,
                    "total_r": round(total_r, 8),
                    "profit_factor": full["profit_factor"],
                    "negative_years": report["negative_years"],
                    "supported_years": report["supported_years"],
                    "retention_if_excluded": round(retention, 8),
                }
            )
    rows.sort(
        key=lambda item: (
            item["total_r"],
            -item["negative_years"],
            item["dimension"],
            item["label"],
        )
    )
    return rows


def run_atlas() -> tuple[tuple[ConfirmationRecord, ...], dict[str, Any]]:
    window = ValidationWindow(market=MARKET, start=START, end=END)
    bars = load_m5_window(
        MARKET,
        start=START - timedelta(days=2),
        end_exclusive=END + timedelta(days=2),
    )
    parents = _rolling_parents(
        market=MARKET,
        bars=bars,
        window=window,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    records: list[ConfirmationRecord] = []
    diagnostics: dict[str, int] = defaultdict(int)
    diagnostics["parent_count"] = len(parents)

    for parent in parents:
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

        observation, confirmation, entry_bar = selected
        trade = _resolve_fixed_target(
            arm=ARM,
            multiple=MULTIPLE,
            parent=parent,
            group=observation.group,
            confirmation=confirmation,
            entry_bar=entry_bar,
            c3_m15=c3_m15,
        )
        if trade is None:
            diagnostics["invalid_structural_geometry"] += 1
            continue

        records.append(
            ConfirmationRecord(
                trade=trade,
                buckets=_features(
                    parent=parent,
                    source=observation.group.source_candle,
                    confirmation=confirmation,
                    entry_bar=entry_bar,
                ),
            )
        )
        diagnostics["record_created"] += 1

    frozen = tuple(
        sorted(records, key=lambda record: record.trade.entry_opened_at)
    )
    dimensions = _dimension_report(frozen)

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "years": YEARS,
        "feature_family_reused_from": "R2_AX_GENERIC_CONFIRMATION_GEOMETRY",
        "audusd_state_transfer_forbidden": True,
        "high_density_core": {
            "timing_lattice": "ROLLING_H4",
            "target": ARM.value,
            "competition": BASE_POLICY.value,
            "efficiency_filter": "OFF",
        },
        "diagnostics": dict(diagnostics),
        "overall": {
            "full_12y": _summary_records(frozen),
            "annual": _annual(frozen),
            "trades_per_year": round(len(frozen) / YEARS, 8),
        },
        "dimensions": dimensions,
        "stable_toxic_candidates": _stable_toxic(
            dimensions,
            len(frozen),
        ),
        "filter_promoted": False,
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
    print("CRT_R2BC_USDJPY_CONFIRMATION_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
