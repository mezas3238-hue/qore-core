"""R2-I causal context forensics for VT08 CRT PURE.

This lab does not add a filter. It stratifies the fixed R2-G NEWEST competition
policy by information available no later than the causal entry slot:

- source generation;
- old-reference multiplicity;
- Model #1 confirmation latency;
- projected RR to frozen C1 midpoint;
- source body/range fraction;
- source range relative to parent C1;
- penetration depth relative to source range;
- direction;
- timing triplet;
- selected cross-dimensions.

Every slice is reported for full 2Y, Year 1 and Year 2. The purpose is root-cause
discovery before any additional engineering gate is frozen.

Research only. No strategy/runtime/capital authority.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    END_EXCLUSIVE,
    FOLD_1_END,
    START,
    ReplayBar,
    load_two_year_m5,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    Model1LabTrade,
    ParentCrt,
    _resolve_trade,
    _summary,
    aggregate_complete_m15,
    build_parent_crts,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2c_close_unmitigated_replay import (
    build_close_unmitigated_breach_groups,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2e_source_multiplicity_census import (
    SourceObservation,
    _aligned_sources,
    _c3_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    CompetitionPolicy,
    select_competing_hypothesis,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2h_rr_acceptance_lab import (
    projected_rr,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

IDENTITY = "VT08_CRT_PURE_R2I_CAUSAL_CONTEXT_FORENSICS_001"
SCHEMA = "qore.vt08.crt_pure.r2i_causal_context_forensics.v1"
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST
M15_SECONDS = 15 * 60


@dataclass(frozen=True, slots=True)
class ForensicRecord:
    trade: Model1LabTrade
    generation: int
    reference_count: int
    confirmation_delay_bars: int
    projected_rr: Decimal
    source_body_fraction: Decimal
    source_range_to_c1: Decimal
    penetration_fraction: Decimal


def _safe_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= 0:
        return Decimal("0")
    return numerator / denominator


def _source_body_fraction(source: M15Bar) -> Decimal:
    return _safe_ratio(
        Decimal(abs(source.close_price - source.open_price)),
        Decimal(source.high_price - source.low_price),
    )


def _source_range_to_c1(parent: ParentCrt, source: M15Bar) -> Decimal:
    return _safe_ratio(
        Decimal(source.high_price - source.low_price),
        Decimal(parent.c1.high_price - parent.c1.low_price),
    )


def _penetration_fraction(
    *,
    parent: ParentCrt,
    observation: SourceObservation,
) -> Decimal:
    source = observation.group.source_candle
    source_range = Decimal(source.high_price - source.low_price)
    if source_range <= 0:
        return Decimal("0")
    if parent.direction is CrtPureCandidateDirection.BULLISH:
        depth = max(
            Decimal(reference.price - source.low_price)
            for reference in observation.group.references
        )
    else:
        depth = max(
            Decimal(source.high_price - reference.price)
            for reference in observation.group.references
        )
    return max(Decimal("0"), depth) / source_range


def _delay_bars(source: M15Bar, confirmation: M15Bar) -> int:
    seconds = int((confirmation.closed_at - source.closed_at).total_seconds())
    if seconds <= 0 or seconds % M15_SECONDS:
        raise RuntimeError("Model #1 confirmation delay must be positive whole M15 bars")
    return seconds // M15_SECONDS


def _bucket_generation(value: int) -> str:
    if value == 1:
        return "G1"
    if value == 2:
        return "G2"
    return "G3_PLUS"


def _bucket_references(value: int) -> str:
    return "REF1" if value == 1 else "REF2_PLUS"


def _bucket_delay(value: int) -> str:
    if value == 1:
        return "D1"
    if value == 2:
        return "D2"
    return "D3_PLUS"


def _bucket_rr(value: Decimal) -> str:
    if value < Decimal("0.50"):
        return "RR_LT_0_50"
    if value < Decimal("0.75"):
        return "RR_0_50_TO_0_75"
    if value < Decimal("1.00"):
        return "RR_0_75_TO_1_00"
    if value < Decimal("1.25"):
        return "RR_1_00_TO_1_25"
    if value < Decimal("1.50"):
        return "RR_1_25_TO_1_50"
    if value < Decimal("2.00"):
        return "RR_1_50_TO_2_00"
    return "RR_GE_2_00"


def _bucket_fraction(value: Decimal, prefix: str) -> str:
    if value < Decimal("0.25"):
        return f"{prefix}_LT_0_25"
    if value < Decimal("0.50"):
        return f"{prefix}_0_25_TO_0_50"
    if value < Decimal("0.75"):
        return f"{prefix}_0_50_TO_0_75"
    return f"{prefix}_GE_0_75"


def _bucket_range_ratio(value: Decimal) -> str:
    if value < Decimal("0.10"):
        return "SRC_RANGE_LT_0_10_C1"
    if value < Decimal("0.20"):
        return "SRC_RANGE_0_10_TO_0_20_C1"
    if value < Decimal("0.30"):
        return "SRC_RANGE_0_20_TO_0_30_C1"
    return "SRC_RANGE_GE_0_30_C1"


def _record_summary(records: Iterable[ForensicRecord]) -> dict[str, Any]:
    rows = tuple(records)
    trades = tuple(record.trade for record in rows)
    return _summary(trades)


def _fold_records(
    records: tuple[ForensicRecord, ...],
    start: datetime,
    end: datetime,
) -> tuple[ForensicRecord, ...]:
    return tuple(
        record
        for record in records
        if start <= datetime.fromisoformat(record.trade.entry_opened_at) < end
    )


def _slice(
    records: tuple[ForensicRecord, ...],
) -> dict[str, Any]:
    return {
        "full_2y": _record_summary(records),
        "year_1": _record_summary(_fold_records(records, START, FOLD_1_END)),
        "year_2": _record_summary(_fold_records(records, FOLD_1_END, END_EXCLUSIVE)),
    }


def run_forensics(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[tuple[ForensicRecord, ...], dict[str, Any]]:
    parents = build_parent_crts(market, bars)
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    records: list[ForensicRecord] = []
    diagnostics: dict[str, int] = defaultdict(int)

    for parent in parents:
        diagnostics["parent_count"] += 1
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
        rr = projected_rr(
            parent=parent,
            source=observation.group.source_candle,
            entry=entry,
        )
        if rr is None:
            diagnostics["invalid_projected_geometry"] += 1
            continue
        trade = _resolve_trade(
            parent=parent,
            group=observation.group,
            confirmation=confirmation,
            entry_bar=entry,
            c3_m15=c3_m15,
        )
        if trade is None:
            diagnostics["resolve_trade_rejected"] += 1
            continue

        generation = observations.index(observation) + 1
        records.append(
            ForensicRecord(
                trade=trade,
                generation=generation,
                reference_count=len(observation.group.references),
                confirmation_delay_bars=_delay_bars(
                    observation.group.source_candle,
                    confirmation,
                ),
                projected_rr=rr,
                source_body_fraction=_source_body_fraction(
                    observation.group.source_candle
                ),
                source_range_to_c1=_source_range_to_c1(
                    parent,
                    observation.group.source_candle,
                ),
                penetration_fraction=_penetration_fraction(
                    parent=parent,
                    observation=observation,
                ),
            )
        )
        diagnostics["record_created"] += 1

    frozen = tuple(sorted(records, key=lambda item: item.trade.entry_opened_at))
    groups: dict[str, dict[str, list[ForensicRecord]]] = {
        "generation": defaultdict(list),
        "reference_count": defaultdict(list),
        "confirmation_delay": defaultdict(list),
        "projected_rr": defaultdict(list),
        "source_body_fraction": defaultdict(list),
        "source_range_to_c1": defaultdict(list),
        "penetration_fraction": defaultdict(list),
        "direction": defaultdict(list),
        "timing_triplet": defaultdict(list),
        "triplet_x_direction": defaultdict(list),
        "generation_x_delay": defaultdict(list),
    }

    for record in frozen:
        generation = _bucket_generation(record.generation)
        delay = _bucket_delay(record.confirmation_delay_bars)
        groups["generation"][generation].append(record)
        groups["reference_count"][_bucket_references(record.reference_count)].append(record)
        groups["confirmation_delay"][delay].append(record)
        groups["projected_rr"][_bucket_rr(record.projected_rr)].append(record)
        groups["source_body_fraction"][
            _bucket_fraction(record.source_body_fraction, "BODY")
        ].append(record)
        groups["source_range_to_c1"][
            _bucket_range_ratio(record.source_range_to_c1)
        ].append(record)
        groups["penetration_fraction"][
            _bucket_fraction(record.penetration_fraction, "PEN")
        ].append(record)
        groups["direction"][record.trade.parent_direction].append(record)
        groups["timing_triplet"][f"T{record.trade.timing_triplet}"].append(record)
        groups["triplet_x_direction"][
            f"T{record.trade.timing_triplet}|{record.trade.parent_direction}"
        ].append(record)
        groups["generation_x_delay"][f"{generation}|{delay}"].append(record)

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "base_competition_policy": BASE_POLICY.value,
        "diagnostics": dict(diagnostics),
        "overall": _slice(frozen),
        "dimensions": {
            dimension: {
                label: _slice(tuple(rows))
                for label, rows in sorted(labels.items())
            }
            for dimension, labels in groups.items()
        },
        "all_features_pre_entry_or_entry_time": True,
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
    parser.add_argument("market", choices=[item.value for item in CrtPureMarket])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    market = CrtPureMarket(args.market)
    records, report = run_forensics(market, load_two_year_m5(market))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "records.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            row = asdict(record)
            handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
    print("CRT_R2I_CONTEXT_FORENSICS_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
