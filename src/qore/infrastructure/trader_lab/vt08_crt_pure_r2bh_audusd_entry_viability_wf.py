"""R2-BH AUDUSD causal entry-viability walk-forward.

Root cause from R2-BF/R2-BG:
- full -1R stops dominate gross loss;
- 84.67% of full stops never establish >= +0.25R on a completed M15 close;
- therefore the primary defect is pre-entry setup viability, not lifecycle.

R2-BH fits a deterministic categorical risk model using ONLY prior years and
ONLY information known by the next M15 entry open.

It does not change:
- CRT parent construction;
- Model #1 confirmation;
- structural stop;
- fixed 1.5R target;
- BE_CLOSE_075;
- C3-close expiry.

The model may abstain from the highest-risk 10/15/20/25% of setups in training.
The selected removal fraction is frozen before each next 1Y OOS fold.
Minimum retained density is therefore structurally >=75% before market gaps.

Research only.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
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
from qore.infrastructure.trader_lab.vt08_crt_pure_r2ax_audusd_confirmation_geometry_atlas import (
    _features as _confirmation_features,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2az_audusd_protection_family import (
    ProtectionPolicy,
    _simulate,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bg_audusd_prestop_path_forensics import (
    _bars as _path_bars,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bg_audusd_prestop_path_forensics import (
    _trace,
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
    _bucket_generation,
    _bucket_range_ratio,
    _bucket_references,
    _delay_bars,
    _penetration_fraction,
    _source_body_fraction,
    _source_range_to_c1,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2i_context_forensics import (
    _bucket_fraction as _bucket_source_fraction,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import load_m5_window
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

IDENTITY = "VT08_CRT_PURE_R2BH_AUDUSD_ENTRY_VIABILITY_WF_001"
SCHEMA = "qore.vt08.crt_pure.r2bh_audusd_entry_viability_wf.v1"
MARKET = CrtPureMarket.AUDUSD
START = datetime(2011, 9, 21, 0, 0, tzinfo=UTC)
END = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
TRAINING_YEARS = 4
ARM = TargetArm.FIXED_1_5R
MULTIPLE = TARGET_MULTIPLE[ARM]
BASE_POLICY = CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST
PROTECTION = ProtectionPolicy.BE_CLOSE_075
REMOVAL_FRACTIONS: tuple[float, ...] = (0.10, 0.15, 0.20, 0.25)
MIN_STATE_SUPPORT = 30
LAPLACE_STRENGTH = 5.0
MIN_DENSITY_PER_YEAR = 170.0


@dataclass(frozen=True, slots=True)
class ViabilityRecord:
    trade: Model1LabTrade
    features: tuple[tuple[str, str], ...]
    dead_on_arrival: bool

    def feature(self, name: str) -> str:
        return dict(self.features)[name]


@dataclass(frozen=True, slots=True)
class RiskModel:
    baseline_bad_rate: float
    state_log_odds_lift: tuple[tuple[str, str, float], ...]
    removal_fraction: float
    score_threshold: float

    def score(self, record: ViabilityRecord) -> float:
        lookup = {
            (dimension, label): value
            for dimension, label, value in self.state_log_odds_lift
        }
        values = [
            lookup[(dimension, label)]
            for dimension, label in record.features
            if (dimension, label) in lookup
        ]
        if not values:
            return 0.0
        return sum(values) / math.sqrt(len(values))


def _source_features(
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


def _entry_features(
    *,
    parent: ParentCrt,
    observation: SourceObservation,
    confirmation: M15Bar,
    entry_bar: M15Bar,
    generation: int,
) -> tuple[tuple[str, str], ...]:
    base = {
        "timing_triplet": parent.timing_triplet,
        "direction": parent.direction.value,
        **_source_features(
            parent=parent,
            observation=observation,
            confirmation=confirmation,
            generation=generation,
        ),
        **dict(
            _confirmation_features(
                parent=parent,
                source=observation.group.source_candle,
                confirmation=confirmation,
                entry_bar=entry_bar,
            )
        ),
    }
    return tuple(sorted(base.items()))


def _year_start(year: int) -> datetime:
    return datetime(year, 9, 21, 0, 0, tzinfo=UTC)


def _slice(
    records: tuple[ViabilityRecord, ...],
    start: datetime,
    end: datetime,
) -> tuple[ViabilityRecord, ...]:
    return tuple(
        record
        for record in records
        if start <= datetime.fromisoformat(record.trade.entry_opened_at) < end
    )


def _trades(
    records: tuple[ViabilityRecord, ...],
) -> tuple[Model1LabTrade, ...]:
    return tuple(record.trade for record in records)


def _is_dead_on_arrival(
    *,
    trade: Model1LabTrade,
    path_max_close_r: float,
) -> bool:
    return (
        trade.exit_reason == "STOP"
        and abs(float(trade.r_multiple) + 1.0) <= 1e-9
        and path_max_close_r < 0.25
    )


def _build_records() -> tuple[tuple[ViabilityRecord, ...], dict[str, int]]:
    window = ValidationWindow(market=MARKET, start=START, end=END)
    bars = load_m5_window(
        MARKET,
        start=START - timedelta(days=2),
        end_exclusive=END + timedelta(days=1),
    )
    parents = _rolling_parents(
        market=MARKET,
        bars=bars,
        window=window,
    )
    m15 = aggregate_complete_m15(bars)
    m15_by_time = {bar.opened_at: bar for bar in m15}
    breaches = build_close_unmitigated_breach_groups(m15)

    diagnostics: Counter[str] = Counter()
    diagnostics["parent_count"] = len(parents)
    records: list[ViabilityRecord] = []

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
        generation = observations.index(observation) + 1
        base_trade = _resolve_fixed_target(
            arm=ARM,
            multiple=MULTIPLE,
            parent=parent,
            group=observation.group,
            confirmation=confirmation,
            entry_bar=entry_bar,
            c3_m15=c3_m15,
        )
        if base_trade is None:
            diagnostics["invalid_structural_geometry"] += 1
            continue

        lifecycle = _path_bars(
            trade=base_trade,
            m15_by_time=m15_by_time,
        )
        managed = _simulate(
            trade=base_trade,
            bars=lifecycle,
            policy=PROTECTION,
        )
        path = _trace(
            trade=managed,
            bars=lifecycle,
        )
        records.append(
            ViabilityRecord(
                trade=managed,
                features=_entry_features(
                    parent=parent,
                    observation=observation,
                    confirmation=confirmation,
                    entry_bar=entry_bar,
                    generation=generation,
                ),
                dead_on_arrival=_is_dead_on_arrival(
                    trade=managed,
                    path_max_close_r=path.max_completed_close_r_before_exit,
                ),
            )
        )
        diagnostics["record_created"] += 1
        if records[-1].dead_on_arrival:
            diagnostics["dead_on_arrival"] += 1

    return (
        tuple(
            sorted(records, key=lambda record: record.trade.entry_opened_at)
        ),
        dict(diagnostics),
    )


def _safe_log_odds(rate: float) -> float:
    clipped = min(max(rate, 1e-6), 1 - 1e-6)
    return math.log(clipped / (1.0 - clipped))


def _state_statistics(
    training: tuple[ViabilityRecord, ...],
) -> tuple[float, tuple[tuple[str, str, float], ...]]:
    bad = sum(record.dead_on_arrival for record in training)
    baseline = (bad + LAPLACE_STRENGTH) / (
        len(training) + 2 * LAPLACE_STRENGTH
    )
    baseline_log_odds = _safe_log_odds(baseline)

    totals: Counter[tuple[str, str]] = Counter()
    bads: Counter[tuple[str, str]] = Counter()
    for record in training:
        for key in record.features:
            totals[key] += 1
            if record.dead_on_arrival:
                bads[key] += 1

    lifts: list[tuple[str, str, float]] = []
    for (dimension, label), total in sorted(totals.items()):
        if total < MIN_STATE_SUPPORT:
            continue
        state_rate = (
            bads[(dimension, label)] + LAPLACE_STRENGTH
        ) / (total + 2 * LAPLACE_STRENGTH)
        lift = _safe_log_odds(state_rate) - baseline_log_odds
        lifts.append(
            (
                dimension,
                label,
                round(max(-2.0, min(2.0, lift)), 8),
            )
        )
    return baseline, tuple(lifts)


def _temporary_model(
    *,
    baseline: float,
    lifts: tuple[tuple[str, str, float], ...],
) -> RiskModel:
    return RiskModel(
        baseline_bad_rate=baseline,
        state_log_odds_lift=lifts,
        removal_fraction=0.0,
        score_threshold=float("inf"),
    )


def _metrics(records: tuple[ViabilityRecord, ...]) -> dict[str, Any]:
    trades = _trades(records)
    summary = _summary(trades)
    dead = sum(record.dead_on_arrival for record in records)
    return {
        **summary,
        "dead_on_arrival": dead,
        "dead_on_arrival_rate": (
            0.0 if not records else round(dead / len(records), 8)
        ),
    }


def _select_model(
    training: tuple[ViabilityRecord, ...],
) -> tuple[RiskModel, dict[str, Any]]:
    baseline, lifts = _state_statistics(training)
    provisional = _temporary_model(baseline=baseline, lifts=lifts)
    scored = sorted(
        ((provisional.score(record), record) for record in training),
        key=lambda item: item[0],
        reverse=True,
    )
    baseline_metrics = _metrics(training)

    choices: list[tuple[float, RiskModel, dict[str, Any]]] = []
    for fraction in REMOVAL_FRACTIONS:
        remove_count = max(1, int(round(len(scored) * fraction)))
        threshold = scored[remove_count - 1][0]
        retained = tuple(
            record
            for score, record in scored
            if score < threshold
        )
        removed = tuple(
            record
            for score, record in scored
            if score >= threshold
        )
        if len(retained) < 0.75 * len(training):
            continue
        retained_metrics = _metrics(retained)
        removed_bad_rate = (
            0.0
            if not removed
            else sum(record.dead_on_arrival for record in removed)
            / len(removed)
        )
        improvement = (
            float(retained_metrics["profit_factor"] or 0.0)
            - float(baseline_metrics["profit_factor"] or 0.0)
        )
        choices.append(
            (
                improvement,
                RiskModel(
                    baseline_bad_rate=baseline,
                    state_log_odds_lift=lifts,
                    removal_fraction=fraction,
                    score_threshold=threshold,
                ),
                {
                    "fraction": fraction,
                    "threshold": threshold,
                    "retained_trades": len(retained),
                    "removed_trades": len(removed),
                    "removed_dead_on_arrival_rate": round(
                        removed_bad_rate,
                        8,
                    ),
                    "training_baseline": baseline_metrics,
                    "training_retained": retained_metrics,
                },
            )
        )

    if not choices:
        model = RiskModel(
            baseline_bad_rate=baseline,
            state_log_odds_lift=lifts,
            removal_fraction=0.0,
            score_threshold=float("inf"),
        )
        return model, {
            "reason": "NO_VALID_REMOVAL_CHOICE",
            "training_baseline": baseline_metrics,
        }

    choices.sort(
        key=lambda item: (
            -item[0],
            item[1].removal_fraction,
        )
    )
    _, model, evidence = choices[0]
    return model, evidence


def _apply_model(
    records: tuple[ViabilityRecord, ...],
    model: RiskModel,
) -> tuple[ViabilityRecord, ...]:
    if model.removal_fraction <= 0:
        return records
    return tuple(
        record
        for record in records
        if model.score(record) < model.score_threshold
    )


def run_walk_forward() -> tuple[
    tuple[ViabilityRecord, ...],
    tuple[ViabilityRecord, ...],
    dict[str, Any],
]:
    records, diagnostics = _build_records()
    baseline_oos: list[ViabilityRecord] = []
    retained_oos: list[ViabilityRecord] = []
    folds: list[dict[str, Any]] = []

    for oos_year in range(START.year + TRAINING_YEARS, END.year):
        train_start = oos_year - TRAINING_YEARS
        training = _slice(
            records,
            _year_start(train_start),
            _year_start(oos_year),
        )
        oos = _slice(
            records,
            _year_start(oos_year),
            _year_start(oos_year + 1),
        )
        model, selection = _select_model(training)
        retained = _apply_model(oos, model)

        baseline_oos.extend(oos)
        retained_oos.extend(retained)
        folds.append(
            {
                "training_start": _year_start(train_start).isoformat(),
                "training_end_exclusive": _year_start(oos_year).isoformat(),
                "oos_start": _year_start(oos_year).isoformat(),
                "oos_end_exclusive": _year_start(oos_year + 1).isoformat(),
                "selected_removal_fraction": model.removal_fraction,
                "score_threshold": model.score_threshold,
                "training_selection": selection,
                "oos_baseline": _metrics(oos),
                "oos_retained": _metrics(retained),
            }
        )

    baseline = tuple(
        sorted(baseline_oos, key=lambda record: record.trade.entry_opened_at)
    )
    retained = tuple(
        sorted(retained_oos, key=lambda record: record.trade.entry_opened_at)
    )
    years = len(folds)
    baseline_metrics = _metrics(baseline)
    retained_metrics = _metrics(retained)
    trades_per_year = 0.0 if years == 0 else len(retained) / years
    positive_year_fraction = (
        0.0
        if not folds
        else sum(
            float(fold["oos_retained"]["total_r"]) > 0
            for fold in folds
        )
        / len(folds)
    )

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": MARKET.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "training_years": TRAINING_YEARS,
        "feature_family": [
            "timing_triplet",
            "direction",
            "source_generation",
            "source_reference_count",
            "confirmation_delay",
            "source_body_fraction",
            "source_range_to_c1",
            "source_penetration",
            "confirmation_body_fraction",
            "confirmation_close_location",
            "confirmation_range_to_source",
            "confirmation_range_to_c1",
            "confirmation_displacement",
            "confirmation_source_overlap",
            "confirmation_through_source_extreme",
            "entry_gap_to_confirmation_range",
            "body_x_location",
            "displacement_x_overlap",
            "range_x_through",
        ],
        "label": "FULL_STOP_WITH_MAX_COMPLETED_CLOSE_LT_0_25R",
        "model": "REGULARIZED_CATEGORICAL_LOG_ODDS_RISK_SCORE",
        "minimum_state_support": MIN_STATE_SUPPORT,
        "laplace_strength": LAPLACE_STRENGTH,
        "removal_fraction_choices": list(REMOVAL_FRACTIONS),
        "minimum_structural_retention": 0.75,
        "no_future_leakage": True,
        "diagnostics": diagnostics,
        "folds": folds,
        "combined_oos_baseline": baseline_metrics,
        "combined_oos_retained": retained_metrics,
        "oos_retention": (
            None if not baseline else round(len(retained) / len(baseline), 8)
        ),
        "oos_trades_per_year": round(trades_per_year, 8),
        "positive_oos_year_fraction": round(positive_year_fraction, 8),
        "research_checks": {
            "density_ge_170": trades_per_year >= MIN_DENSITY_PER_YEAR,
            "pf_improved": (
                float(retained_metrics["profit_factor"] or 0.0)
                > float(baseline_metrics["profit_factor"] or 0.0)
            ),
            "total_r_improved": (
                float(retained_metrics["total_r"])
                > float(baseline_metrics["total_r"])
            ),
            "dead_on_arrival_rate_reduced": (
                retained_metrics["dead_on_arrival_rate"]
                < baseline_metrics["dead_on_arrival_rate"]
            ),
        },
        "automatic_promotion": False,
        "candidate_certified": False,
        "research_only": True,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return records, retained, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    records, retained, report = run_walk_forward()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "records.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(
                json.dumps(asdict(record), sort_keys=True, default=str) + "\n"
            )
    with (args.output / "oos_retained.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for record in retained:
            handle.write(
                json.dumps(asdict(record), sort_keys=True, default=str) + "\n"
            )
    print("CRT_R2BH_ENTRY_VIABILITY_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
