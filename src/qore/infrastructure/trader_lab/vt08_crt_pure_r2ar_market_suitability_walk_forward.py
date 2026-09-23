"""R2-AR causal market-suitability walk-forward for VT08 CRT PURE FX.

Frozen before outcomes.

High-density core:
- ROLLING_H4;
- FIXED_1_5R;
- no EFF gate;
- one selected Model #1 hypothesis max per parent;
- structural source stop;
- C3 expiry;
- STOP_FIRST.

Suitability algorithm:
- use only context known before C3;
- each OOS year trains on the immediately preceding 3 years;
- candidate UNSUITABLE state is exactly one frozen context bucket;
- that bucket must be negative in every one of the 3 training years;
- removing it must retain >=70% of training trades;
- among eligible states, exclude the state with the most negative aggregate
  training Total-R;
- if none qualify, exclude nothing;
- the selected state is frozen before evaluating the next OOS year.

This is an engineering characterization. The target family and context taxonomy
were developed using already-consumed evidence, so this is not final untouched
certification evidence. A later older holdout is required.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
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
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import load_m5_window
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2AR_MARKET_SUITABILITY_WALK_FORWARD_001"
SCHEMA = "qore.vt08.crt_pure.r2ar_market_suitability_walk_forward.v1"
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST
ARM = TargetArm.FIXED_1_5R
MULTIPLE = TARGET_MULTIPLE[ARM]
TRAINING_YEARS = 3
MIN_RETENTION = Decimal("0.70")


@dataclass(frozen=True, slots=True)
class MarketPeriod:
    market: CrtPureMarket
    start: datetime
    end: datetime


PERIODS: dict[CrtPureMarket, MarketPeriod] = {
    CrtPureMarket.AUDUSD: MarketPeriod(
        market=CrtPureMarket.AUDUSD,
        start=datetime(2016, 9, 21, 0, 0, tzinfo=UTC),
        end=datetime(2026, 9, 21, 0, 0, tzinfo=UTC),
    ),
    CrtPureMarket.USDJPY: MarketPeriod(
        market=CrtPureMarket.USDJPY,
        start=datetime(2014, 9, 21, 0, 0, tzinfo=UTC),
        end=datetime(2026, 9, 21, 0, 0, tzinfo=UTC),
    ),
}


@dataclass(frozen=True, slots=True)
class SuitabilityRecord:
    trade: Model1LabTrade
    buckets: tuple[tuple[str, str], ...]

    def bucket(self, dimension: str) -> str:
        return dict(self.buckets)[dimension]


@dataclass(frozen=True, slots=True)
class ExclusionRule:
    dimension: str
    label: str

    @property
    def code(self) -> str:
        return f"{self.dimension}={self.label}"


def _year_start(year: int) -> datetime:
    return datetime(year, 9, 21, 0, 0, tzinfo=UTC)


def _slice(
    records: tuple[SuitabilityRecord, ...],
    start: datetime,
    end: datetime,
) -> tuple[SuitabilityRecord, ...]:
    return tuple(
        record
        for record in records
        if start <= datetime.fromisoformat(record.trade.entry_opened_at) < end
    )


def _trades(records: tuple[SuitabilityRecord, ...]) -> tuple[Model1LabTrade, ...]:
    return tuple(record.trade for record in records)


def _total_r(records: tuple[SuitabilityRecord, ...]) -> float:
    return sum(record.trade.r_multiple for record in records)


def _buckets(
    *,
    trade: Model1LabTrade,
    context: tuple[Any, ...],
) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (
                ("vol_1d_to_5d", _bucket_ratio(context[0], "VOL1D5D")),
                ("vol_5d_to_20d", _bucket_ratio(context[1], "VOL5D20D")),
                ("efficiency_1d", _bucket_efficiency(context[2], "EFF1D")),
                ("efficiency_5d", _bucket_efficiency(context[3], "EFF5D")),
                ("drift_1d", str(context[4])),
                ("drift_5d", str(context[5])),
                ("drift_20d", str(context[6])),
                ("c1_body_fraction", _bucket_fraction(context[7], "C1BODY")),
                ("c1_body_alignment", str(context[8])),
                ("c1_range_to_5d_h4", _bucket_c1_range(context[9])),
                (
                    "c1_directional_position_5d",
                    _bucket_fraction(context[10], "POS5D"),
                ),
                ("c2_range_to_c1", _bucket_c2_range(context[11])),
                (
                    "manipulation_depth",
                    _bucket_depth(context[12], "MANIP"),
                ),
                (
                    "reclaim_depth",
                    _bucket_fraction(context[13], "RECLAIM"),
                ),
                ("direction", trade.parent_direction),
                ("timing_triplet", trade.timing_triplet),
            )
        )
    )


def _candidate_rules(
    records: tuple[SuitabilityRecord, ...],
) -> tuple[ExclusionRule, ...]:
    values: set[tuple[str, str]] = set()
    for record in records:
        values.update(record.buckets)
    return tuple(
        ExclusionRule(dimension=dimension, label=label)
        for dimension, label in sorted(values)
    )


def _matches(record: SuitabilityRecord, rule: ExclusionRule) -> bool:
    return record.bucket(rule.dimension) == rule.label


def _select_rule(
    *,
    training: tuple[SuitabilityRecord, ...],
    training_start_year: int,
) -> tuple[ExclusionRule | None, dict[str, Any]]:
    if not training:
        return None, {"eligible_rules": 0, "reason": "EMPTY_TRAINING"}

    candidates: list[tuple[float, ExclusionRule, dict[str, Any]]] = []
    for rule in _candidate_rules(training):
        removed = tuple(record for record in training if _matches(record, rule))
        residual = tuple(record for record in training if not _matches(record, rule))
        retention = Decimal(len(residual)) / Decimal(len(training))
        if retention < MIN_RETENTION or not removed:
            continue

        yearly_removed: dict[str, float] = {}
        negative_every_year = True
        for offset in range(TRAINING_YEARS):
            left = _year_start(training_start_year + offset)
            right = _year_start(training_start_year + offset + 1)
            rows = _slice(removed, left, right)
            value = _total_r(rows)
            yearly_removed[f"{left.year}_{right.year}"] = round(value, 8)
            if not rows or value >= 0:
                negative_every_year = False
                break
        if not negative_every_year:
            continue

        removed_total = _total_r(removed)
        if removed_total >= 0:
            continue

        candidates.append(
            (
                removed_total,
                rule,
                {
                    "removed_trades": len(removed),
                    "removed_total_r": round(removed_total, 8),
                    "residual_trades": len(residual),
                    "retention": round(float(retention), 8),
                    "yearly_removed_total_r": yearly_removed,
                },
            )
        )

    if not candidates:
        return None, {"eligible_rules": 0, "reason": "NO_STABLE_TOXIC_STATE"}

    # Most negative aggregate state wins. Tie-break by stable rule code.
    candidates.sort(key=lambda item: (item[0], item[1].code))
    _, rule, evidence = candidates[0]
    return rule, {
        "eligible_rules": len(candidates),
        "selected_rule": rule.code,
        **evidence,
    }


def _build_records(market: CrtPureMarket) -> tuple[SuitabilityRecord, ...]:
    period = PERIODS[market]
    validation = ValidationWindow(
        market=market,
        start=period.start,
        end=period.end,
    )
    bars = load_m5_window(
        market,
        start=period.start - timedelta(days=25),
        end_exclusive=period.end + timedelta(days=2),
    )
    parents = _rolling_parents(
        market=market,
        bars=bars,
        window=validation,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    times = tuple(bar.opened_at for bar in m15)
    breaches = build_close_unmitigated_breach_groups(m15)

    records: list[SuitabilityRecord] = []
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
            continue
        context = _context(parent=parent, m15=m15, times=times)
        if context is None:
            continue
        records.append(
            SuitabilityRecord(
                trade=trade,
                buckets=_buckets(trade=trade, context=context),
            )
        )
    return tuple(
        sorted(records, key=lambda item: item.trade.entry_opened_at)
    )


def run_walk_forward(
    market: CrtPureMarket,
) -> tuple[
    tuple[SuitabilityRecord, ...],
    tuple[SuitabilityRecord, ...],
    dict[str, Any],
]:
    period = PERIODS[market]
    records = _build_records(market)
    baseline_oos: list[SuitabilityRecord] = []
    suitability_oos: list[SuitabilityRecord] = []
    folds: list[dict[str, Any]] = []

    first_oos_year = period.start.year + TRAINING_YEARS
    for oos_year in range(first_oos_year, period.end.year):
        training_start_year = oos_year - TRAINING_YEARS
        training_start = _year_start(training_start_year)
        training_end = _year_start(oos_year)
        oos_start = _year_start(oos_year)
        oos_end = _year_start(oos_year + 1)

        training = _slice(records, training_start, training_end)
        oos = _slice(records, oos_start, oos_end)
        rule, selection = _select_rule(
            training=training,
            training_start_year=training_start_year,
        )
        retained = (
            oos
            if rule is None
            else tuple(record for record in oos if not _matches(record, rule))
        )

        baseline_oos.extend(oos)
        suitability_oos.extend(retained)
        folds.append(
            {
                "training_start": training_start.isoformat(),
                "training_end_exclusive": training_end.isoformat(),
                "oos_start": oos_start.isoformat(),
                "oos_end_exclusive": oos_end.isoformat(),
                "training_trades": len(training),
                "oos_baseline_trades": len(oos),
                "oos_retained_trades": len(retained),
                "selected_unsuitable_state": None if rule is None else rule.code,
                "selection_evidence": selection,
                "oos_baseline": _summary(_trades(oos)),
                "oos_suitability": _summary(_trades(retained)),
            }
        )

    baseline = tuple(
        sorted(baseline_oos, key=lambda item: item.trade.entry_opened_at)
    )
    suitability = tuple(
        sorted(suitability_oos, key=lambda item: item.trade.entry_opened_at)
    )
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": market.value,
        "period_start": period.start.isoformat(),
        "period_end_exclusive": period.end.isoformat(),
        "training_years": TRAINING_YEARS,
        "minimum_training_retention": str(MIN_RETENTION),
        "high_density_core": {
            "timing_lattice": "ROLLING_H4",
            "target": ARM.value,
            "competition": BASE_POLICY.value,
            "efficiency_filter": "OFF",
        },
        "selection_rule": (
            "ONE_BUCKET_NEGATIVE_IN_ALL_3_TRAINING_YEARS;"
            "RETAIN_GE_70_PERCENT;"
            "MOST_NEGATIVE_AGGREGATE_STATE"
        ),
        "folds": folds,
        "combined_oos_baseline": _summary(_trades(baseline)),
        "combined_oos_suitability": _summary(_trades(suitability)),
        "oos_retention": (
            None
            if not baseline
            else round(len(suitability) / len(baseline), 8)
        ),
        "walk_forward_no_future_leakage": True,
        "final_untouched_certification_claim": False,
        "automatic_promotion": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return records, suitability, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("market", choices=[item.value for item in PERIODS])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    market = CrtPureMarket(args.market)
    records, suitability, report = run_walk_forward(market)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "records.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(
                json.dumps(asdict(record), sort_keys=True, default=str) + "\n"
            )
    with (args.output / "oos_suitability.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for record in suitability:
            handle.write(
                json.dumps(asdict(record), sort_keys=True, default=str) + "\n"
            )
    print("CRT_R2AR_SUITABILITY_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
