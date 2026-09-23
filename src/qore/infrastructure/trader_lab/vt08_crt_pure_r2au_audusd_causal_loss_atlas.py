"""R2-AU AUDUSD high-density causal loss atlas.

Purpose
-------
R2-AQ established that the broad AUDUSD high-density core
ROLLING_H4 + FIXED_1_5R + structural stop produces ~247 trades/year over 10Y,
with aggregate PF ~1.01 but strong regime variation.

R2-AR showed that excluding one parent-context bucket via walk-forward did not
improve OOS economics. R2-AT showed that routing among 1R/1.5R/2R destinations
also did not repair edge.

R2-AU therefore moves one causal layer deeper and characterizes *joint*
pre-entry state:
- parent CRT market context;
- selected Model #1 source/confirmation context.

No rule is promoted and no trade is removed. This is an attribution atlas only.

Research only. No runtime/capital authority.
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
    SourceObservation,
    _aligned_sources,
    _c3_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    CompetitionPolicy,
    select_competing_hypothesis,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2i_context_forensics import (
    _bucket_delay,
    _bucket_fraction as _bucket_source_fraction,
    _bucket_generation,
    _bucket_range_ratio,
    _bucket_references,
    _delay_bars,
    _penetration_fraction,
    _source_body_fraction,
    _source_range_to_c1,
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
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import load_m5_window
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2AU_AUDUSD_CAUSAL_LOSS_ATLAS_001"
SCHEMA = "qore.vt08.crt_pure.r2au_audusd_causal_loss_atlas.v1"
MARKET = CrtPureMarket.AUDUSD
START = datetime(2016, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST
ARM = TargetArm.FIXED_1_5R
MULTIPLE = TARGET_MULTIPLE[ARM]
MIN_BUCKET_TRADES = 60
MIN_ANNUAL_SUPPORT = 5


@dataclass(frozen=True, slots=True)
class AtlasRecord:
    trade: Model1LabTrade
    buckets: tuple[tuple[str, str], ...]

    def bucket(self, dimension: str) -> str:
        return dict(self.buckets)[dimension]


def _year_start(year: int) -> datetime:
    return datetime(year, 9, 21, 0, 0, tzinfo=UTC)


def _slice(
    records: tuple[AtlasRecord, ...],
    start: datetime,
    end: datetime,
) -> tuple[AtlasRecord, ...]:
    return tuple(
        record
        for record in records
        if start <= datetime.fromisoformat(record.trade.entry_opened_at) < end
    )


def _summary_records(records: tuple[AtlasRecord, ...]) -> dict[str, Any]:
    return _summary(tuple(record.trade for record in records))


def _annual(records: tuple[AtlasRecord, ...]) -> dict[str, dict[str, Any]]:
    return {
        f"{year}_{year + 1}": _summary_records(
            _slice(records, _year_start(year), _year_start(year + 1))
        )
        for year in range(START.year, END.year)
    }


def _source_buckets(
    *,
    parent: ParentCrt,
    observation: SourceObservation,
    confirmation: M15Bar,
    generation: int,
) -> dict[str, str]:
    source = observation.group.source_candle
    return {
        "source_generation": _bucket_generation(generation),
        "source_reference_count": _bucket_references(
            len(observation.group.references)
        ),
        "confirmation_delay": _bucket_delay(_delay_bars(source, confirmation)),
        "source_body_fraction": _bucket_source_fraction(
            _source_body_fraction(source),
            "SRCBODY",
        ),
        "source_range_to_c1": _bucket_range_ratio(
            _source_range_to_c1(parent, source)
        ),
        "source_penetration": _bucket_source_fraction(
            _penetration_fraction(
                parent=parent,
                observation=observation,
            ),
            "SRCPEN",
        ),
    }


def _parent_buckets(
    *,
    trade: Model1LabTrade,
    context: tuple[Any, ...],
) -> dict[str, str]:
    return {
        "vol_1d_to_5d": _bucket_ratio(context[0], "VOL1D5D"),
        "vol_5d_to_20d": _bucket_ratio(context[1], "VOL5D20D"),
        "efficiency_1d": _bucket_efficiency(context[2], "EFF1D"),
        "efficiency_5d": _bucket_efficiency(context[3], "EFF5D"),
        "drift_1d": str(context[4]),
        "drift_5d": str(context[5]),
        "drift_20d": str(context[6]),
        "c1_body_fraction": _bucket_fraction(context[7], "C1BODY"),
        "c1_body_alignment": str(context[8]),
        "c1_range_to_5d_h4": _bucket_c1_range(context[9]),
        "c1_directional_position_5d": _bucket_fraction(
            context[10],
            "POS5D",
        ),
        "c2_range_to_c1": _bucket_c2_range(context[11]),
        "manipulation_depth": _bucket_depth(context[12], "MANIP"),
        "reclaim_depth": _bucket_fraction(context[13], "RECLAIM"),
        "direction": trade.parent_direction,
        "timing_triplet": trade.timing_triplet,
    }


INTERACTIONS: tuple[tuple[str, str], ...] = (
    ("timing_triplet", "direction"),
    ("timing_triplet", "source_generation"),
    ("source_generation", "confirmation_delay"),
    ("source_body_fraction", "source_range_to_c1"),
    ("source_penetration", "direction"),
    ("efficiency_1d", "source_generation"),
    ("efficiency_5d", "source_generation"),
    ("c1_body_fraction", "source_body_fraction"),
    ("manipulation_depth", "source_penetration"),
    ("c2_range_to_c1", "source_range_to_c1"),
    ("drift_5d", "direction"),
    ("reclaim_depth", "source_penetration"),
)


def _record_buckets(
    *,
    parent: ParentCrt,
    trade: Model1LabTrade,
    observation: SourceObservation,
    confirmation: M15Bar,
    generation: int,
    context: tuple[Any, ...],
) -> tuple[tuple[str, str], ...]:
    base = {
        **_parent_buckets(trade=trade, context=context),
        **_source_buckets(
            parent=parent,
            observation=observation,
            confirmation=confirmation,
            generation=generation,
        ),
    }
    for left, right in INTERACTIONS:
        base[f"{left}_x_{right}"] = f"{base[left]}|{base[right]}"
    return tuple(sorted(base.items()))


def _dimension_report(
    records: tuple[AtlasRecord, ...],
) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, list[AtlasRecord]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for record in records:
        for dimension, label in record.buckets:
            groups[dimension][label].append(record)

    result: dict[str, dict[str, Any]] = {}
    for dimension, labels in sorted(groups.items()):
        result[dimension] = {}
        for label, rows in sorted(labels.items()):
            frozen = tuple(rows)
            annual = _annual(frozen)
            negative_years = sum(
                float(summary["total_r"]) < 0
                for summary in annual.values()
                if int(summary["trades"]) > 0
            )
            supported_years = sum(
                int(summary["trades"]) >= MIN_ANNUAL_SUPPORT
                for summary in annual.values()
            )
            result[dimension][label] = {
                "full_10y": _summary_records(frozen),
                "annual": annual,
                "negative_years": negative_years,
                "supported_years": supported_years,
            }
    return result


def _stable_toxic_candidates(
    dimensions: dict[str, dict[str, Any]],
    total_trades: int,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for dimension, labels in dimensions.items():
        for label, report in labels.items():
            full = report["full_10y"]
            trades = int(full["trades"])
            total_r = float(full["total_r"])
            if trades < MIN_BUCKET_TRADES or total_r >= 0:
                continue
            if int(report["supported_years"]) < 6:
                continue
            retention = 1.0 - (trades / total_trades)
            if retention < 0.70:
                continue
            candidates.append(
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
    candidates.sort(
        key=lambda item: (
            item["total_r"],
            -item["negative_years"],
            item["dimension"],
            item["label"],
        )
    )
    return candidates


def run_atlas() -> tuple[tuple[AtlasRecord, ...], dict[str, Any]]:
    window = ValidationWindow(
        market=MARKET,
        start=START,
        end=END,
    )
    bars = load_m5_window(
        MARKET,
        start=START - timedelta(days=25),
        end_exclusive=END + timedelta(days=2),
    )
    parents = _rolling_parents(
        market=MARKET,
        bars=bars,
        window=window,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    times = tuple(bar.opened_at for bar in m15)
    breaches = build_close_unmitigated_breach_groups(m15)

    records: list[AtlasRecord] = []
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

        observation, confirmation, entry = selected
        generation = observations.index(observation) + 1
        trade = _resolve_fixed_target(
            arm=ARM,
            multiple=MULTIPLE,
            parent=parent,
            group=observation.group,
            confirmation=confirmation,
            entry_bar=entry,
            c3_m15=c3_m15,
        )
        if trade is None:
            diagnostics["invalid_structural_geometry"] += 1
            continue

        context = _context(parent=parent, m15=m15, times=times)
        if context is None:
            diagnostics["insufficient_parent_context"] += 1
            continue

        records.append(
            AtlasRecord(
                trade=trade,
                buckets=_record_buckets(
                    parent=parent,
                    trade=trade,
                    observation=observation,
                    confirmation=confirmation,
                    generation=generation,
                    context=context,
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
        "interaction_family": [
            f"{left}_x_{right}" for left, right in INTERACTIONS
        ],
        "interaction_family_frozen_before_results": True,
        "all_features_pre_entry_or_entry_time": True,
        "diagnostics": dict(diagnostics),
        "overall": {
            "full_10y": _summary_records(frozen),
            "annual": _annual(frozen),
        },
        "dimensions": dimensions,
        "stable_toxic_candidates": _stable_toxic_candidates(
            dimensions,
            len(frozen),
        ),
        "candidate_selection_performed": False,
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
    print("CRT_R2AU_AUDUSD_LOSS_ATLAS_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
