"""R2-K historical context forensics for USDJPY.

R2-J proved that USDJPY development clues from 2024-2026 do not generalize to
2022-2024. R2-K applies the same causal feature taxonomy to the older validation
window without adding a filter.

The goal is to identify context dimensions whose sign is consistent across both
windows, or prove that the current feature set is insufficient and a higher-level
regime model is required.

Research only. No execution/capital authority.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
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
from qore.infrastructure.trader_lab.vt08_crt_pure_r2h_rr_acceptance_lab import (
    projected_rr,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2i_context_forensics import (
    ForensicRecord,
    _bucket_delay,
    _bucket_fraction,
    _bucket_generation,
    _bucket_range_ratio,
    _bucket_references,
    _bucket_rr,
    _delay_bars,
    _penetration_fraction,
    _source_body_fraction,
    _source_range_to_c1,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import (
    build_parent_crts_for_window,
    load_m5_window,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2K_USDJPY_HISTORICAL_CONTEXT_001"
SCHEMA = "qore.vt08.crt_pure.r2k_usdjpy_historical_context.v1"
START = datetime(2022, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2024, 9, 21, 0, 0, tzinfo=UTC)
FOLD = datetime(2023, 9, 21, 0, 0, tzinfo=UTC)
MARKET = CrtPureMarket.USDJPY
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST


def _fold(
    records: tuple[ForensicRecord, ...],
    start: datetime,
    end: datetime,
) -> tuple[ForensicRecord, ...]:
    return tuple(
        record
        for record in records
        if start <= datetime.fromisoformat(record.trade.entry_opened_at) < end
    )


def _summary_records(records: tuple[ForensicRecord, ...]) -> dict[str, Any]:
    return _summary(tuple(record.trade for record in records))


def _slice(records: tuple[ForensicRecord, ...]) -> dict[str, Any]:
    return {
        "full_2y": _summary_records(records),
        "year_1": _summary_records(_fold(records, START, FOLD)),
        "year_2": _summary_records(_fold(records, FOLD, END)),
    }


def run_forensics() -> tuple[tuple[ForensicRecord, ...], dict[str, Any]]:
    bars = load_m5_window(MARKET, start=START, end_exclusive=END)
    parents = build_parent_crts_for_window(
        MARKET,
        bars,
        start=START,
        end_exclusive=END,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    records: list[ForensicRecord] = []
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
            continue

        observation, confirmation, entry = selected
        rr = projected_rr(
            parent=parent,
            source=observation.group.source_candle,
            entry=entry,
        )
        if rr is None:
            continue
        trade = _resolve_trade(
            parent=parent,
            group=observation.group,
            confirmation=confirmation,
            entry_bar=entry,
            c3_m15=c3_m15,
        )
        if trade is None:
            continue

        records.append(
            ForensicRecord(
                trade=trade,
                generation=observations.index(observation) + 1,
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
        generation_bucket = _bucket_generation(record.generation)
        delay_bucket = _bucket_delay(record.confirmation_delay_bars)
        groups["generation"][generation_bucket].append(record)
        groups["reference_count"][
            _bucket_references(record.reference_count)
        ].append(record)
        groups["confirmation_delay"][delay_bucket].append(record)
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
        groups["generation_x_delay"][
            f"{generation_bucket}|{delay_bucket}"
        ].append(record)

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "fold": FOLD.isoformat(),
        "base_competition_policy": BASE_POLICY.value,
        "parent_crt_count": len(parents),
        "overall": _slice(frozen),
        "dimensions": {
            dimension: {
                label: _slice(tuple(rows))
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
    print("CRT_R2K_USDJPY_CONTEXT_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
