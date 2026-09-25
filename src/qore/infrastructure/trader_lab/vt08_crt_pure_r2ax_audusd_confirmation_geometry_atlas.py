"""R2-AX AUDUSD confirmation-geometry atlas.

R2-AU/R2-AW showed that source quality contains strong retrospective loss
clusters but that adaptive one-state source exclusion does not repair OOS edge.

R2-AX moves exactly one causal step later: the Model #1 confirmation candle
whose body close authorizes the next contiguous M15 entry.

No signal, stop, target, timing, competition or lifecycle rule is changed.
No filter is promoted.

All features are known no later than the next M15 entry open:
- confirmation body fraction;
- direction-normalized close location inside the confirmation candle;
- confirmation range / source range;
- confirmation range / C1 range;
- confirmation close displacement beyond source open / source range;
- confirmation/source range overlap;
- close-through-source-extreme flag;
- next-open gap / confirmation range.

Research only.
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
    M15Bar,
    Model1LabTrade,
    ParentCrt,
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
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

IDENTITY = "VT08_CRT_PURE_R2AX_AUDUSD_CONFIRMATION_GEOMETRY_ATLAS_001"
SCHEMA = "qore.vt08.crt_pure.r2ax_audusd_confirmation_geometry_atlas.v1"
MARKET = CrtPureMarket.AUDUSD
START = datetime(2016, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST
ARM = TargetArm.FIXED_1_5R
MULTIPLE = TARGET_MULTIPLE[ARM]
MIN_BUCKET_TRADES = 60
MIN_SUPPORTED_YEARS = 6


@dataclass(frozen=True, slots=True)
class ConfirmationRecord:
    trade: Model1LabTrade
    buckets: tuple[tuple[str, str], ...]

    def bucket(self, dimension: str) -> str:
        return dict(self.buckets)[dimension]


def _safe_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= 0:
        return Decimal("0")
    return numerator / denominator


def _bucket_quartile(value: Decimal, prefix: str) -> str:
    if value < Decimal("0.25"):
        return f"{prefix}_LT_0_25"
    if value < Decimal("0.50"):
        return f"{prefix}_0_25_TO_0_50"
    if value < Decimal("0.75"):
        return f"{prefix}_0_50_TO_0_75"
    return f"{prefix}_GE_0_75"


def _bucket_ratio(value: Decimal, prefix: str) -> str:
    if value < Decimal("0.50"):
        return f"{prefix}_LT_0_50"
    if value < Decimal("1.00"):
        return f"{prefix}_0_50_TO_1_00"
    if value < Decimal("1.50"):
        return f"{prefix}_1_00_TO_1_50"
    return f"{prefix}_GE_1_50"


def _bucket_gap(value: Decimal) -> str:
    absolute = abs(value)
    if absolute < Decimal("0.05"):
        return "ENTRY_GAP_LT_0_05"
    if absolute < Decimal("0.15"):
        return "ENTRY_GAP_0_05_TO_0_15"
    if absolute < Decimal("0.30"):
        return "ENTRY_GAP_0_15_TO_0_30"
    return "ENTRY_GAP_GE_0_30"


def _directional_close_location(
    *,
    confirmation: M15Bar,
    direction: CrtPureCandidateDirection,
) -> Decimal:
    candle_range = Decimal(confirmation.high_price - confirmation.low_price)
    if candle_range <= 0:
        return Decimal("0")
    if direction is CrtPureCandidateDirection.BULLISH:
        return Decimal(
            confirmation.close_price - confirmation.low_price
        ) / candle_range
    return Decimal(
        confirmation.high_price - confirmation.close_price
    ) / candle_range


def _directional_displacement(
    *,
    source: M15Bar,
    confirmation: M15Bar,
    direction: CrtPureCandidateDirection,
) -> Decimal:
    source_range = Decimal(source.high_price - source.low_price)
    if source_range <= 0:
        return Decimal("0")
    if direction is CrtPureCandidateDirection.BULLISH:
        distance = confirmation.close_price - source.open_price
    else:
        distance = source.open_price - confirmation.close_price
    return Decimal(max(0, distance)) / source_range


def _range_overlap_fraction(source: M15Bar, confirmation: M15Bar) -> Decimal:
    source_range = Decimal(source.high_price - source.low_price)
    if source_range <= 0:
        return Decimal("0")
    overlap = max(
        0,
        min(source.high_price, confirmation.high_price)
        - max(source.low_price, confirmation.low_price),
    )
    return Decimal(overlap) / source_range


def _closed_through_source_extreme(
    *,
    source: M15Bar,
    confirmation: M15Bar,
    direction: CrtPureCandidateDirection,
) -> bool:
    if direction is CrtPureCandidateDirection.BULLISH:
        return confirmation.close_price > source.high_price
    return confirmation.close_price < source.low_price


def _features(
    *,
    parent: ParentCrt,
    source: M15Bar,
    confirmation: M15Bar,
    entry_bar: M15Bar,
) -> tuple[tuple[str, str], ...]:
    confirmation_range = Decimal(
        confirmation.high_price - confirmation.low_price
    )
    source_range = Decimal(source.high_price - source.low_price)
    c1_range = Decimal(parent.c1.high_price - parent.c1.low_price)

    body_fraction = _safe_ratio(
        Decimal(abs(confirmation.close_price - confirmation.open_price)),
        confirmation_range,
    )
    close_location = _directional_close_location(
        confirmation=confirmation,
        direction=parent.direction,
    )
    confirmation_to_source = _safe_ratio(
        confirmation_range,
        source_range,
    )
    confirmation_to_c1 = _safe_ratio(
        confirmation_range,
        c1_range,
    )
    displacement = _directional_displacement(
        source=source,
        confirmation=confirmation,
        direction=parent.direction,
    )
    overlap = _range_overlap_fraction(source, confirmation)
    entry_gap = _safe_ratio(
        Decimal(entry_bar.open_price - confirmation.close_price),
        confirmation_range,
    )
    through = _closed_through_source_extreme(
        source=source,
        confirmation=confirmation,
        direction=parent.direction,
    )

    base = {
        "confirmation_body_fraction": _bucket_quartile(
            body_fraction,
            "CONFBODY",
        ),
        "confirmation_close_location": _bucket_quartile(
            close_location,
            "CONFLOC",
        ),
        "confirmation_range_to_source": _bucket_ratio(
            confirmation_to_source,
            "CONFRANGE_SRC",
        ),
        "confirmation_range_to_c1": _bucket_ratio(
            confirmation_to_c1,
            "CONFRANGE_C1",
        ),
        "confirmation_displacement": _bucket_ratio(
            displacement,
            "CONFDISP",
        ),
        "confirmation_source_overlap": _bucket_quartile(
            overlap,
            "CONFOVERLAP",
        ),
        "confirmation_through_source_extreme": (
            "THROUGH_SOURCE_EXTREME"
            if through
            else "INSIDE_SOURCE_EXTREME"
        ),
        "entry_gap_to_confirmation_range": _bucket_gap(entry_gap),
    }
    base["body_x_location"] = (
        f"{base['confirmation_body_fraction']}|"
        f"{base['confirmation_close_location']}"
    )
    base["displacement_x_overlap"] = (
        f"{base['confirmation_displacement']}|"
        f"{base['confirmation_source_overlap']}"
    )
    base["range_x_through"] = (
        f"{base['confirmation_range_to_source']}|"
        f"{base['confirmation_through_source_extreme']}"
    )
    return tuple(sorted(base.items()))


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
            supported_years = sum(
                int(summary["trades"]) >= 5
                for summary in annual.values()
            )
            negative_years = sum(
                float(summary["total_r"]) < 0
                for summary in annual.values()
                if int(summary["trades"]) > 0
            )
            report[dimension][label] = {
                "full_10y": _summary_records(frozen),
                "annual": annual,
                "supported_years": supported_years,
                "negative_years": negative_years,
            }
    return report


def _stable_toxic(
    dimensions: dict[str, dict[str, Any]],
    total_trades: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dimension, labels in dimensions.items():
        for label, report in labels.items():
            full = report["full_10y"]
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
        "high_density_core": {
            "timing_lattice": "ROLLING_H4",
            "target": ARM.value,
            "competition": BASE_POLICY.value,
            "efficiency_filter": "OFF",
        },
        "all_features_known_by_entry_open": True,
        "diagnostics": dict(diagnostics),
        "overall": {
            "full_10y": _summary_records(frozen),
            "annual": _annual(frozen),
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
    print(
        "CRT_R2AX_CONFIRMATION_ATLAS_JSON="
        + json.dumps(report, sort_keys=True)
    )


if __name__ == "__main__":
    main()
