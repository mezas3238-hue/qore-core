"""R2-CD USDJPY cognitive WAIT-resolution walk-forward.

Frozen contract:
- preserve R2-BZ initial EXECUTE / WAIT / ABSTAIN;
- ABSTAIN is terminal;
- WAIT observes one completed M15;
- structural-stop touch -> terminal ABSTAIN;
- consumed original destination -> no chase;
- otherwise delayed candidate enters next M15 open;
- original structural stop preserved;
- fixed 1.5R target recalculated from delayed entry;
- original C3 expiry and STOP_FIRST preserved;
- USDJPY adds no post-entry protection.

Journey Experience Memory learns delayed Expected-R + delayed DOA from the
market's own immediately preceding 4Y evidence. The frozen CRT cognitive reasoner
remains the second-decision sovereign.

Research only.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2bz_usdjpy_cognitive_experience_wf as r2bz,
)
from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2cb_usdjpy_wait_journey_atlas as r2cb,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    Model1LabTrade,
    _summary,
    aggregate_complete_m15,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2az_audusd_protection_family import (
    ProtectionPolicy,
    _simulate,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bc_usdjpy_confirmation_geometry_atlas import (
    END,
    START,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bn_usdjpy_root_cause_expected_r_wf import (
    MIN_CELL_SUPPORT,
    PRIOR_STRENGTH,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2m_survivor_robustness import (
    _stress_summary,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_window_evidence import (
    load_m5_window,
)
from qore.infrastructure.traders.crt_pure_cognitive_contract import (
    CrtPureAttentionState,
    CrtPureHypothesisStage,
    CrtPureKnowledgeState,
    CrtPureReasoningAction,
)
from qore.infrastructure.traders.crt_pure_cognitive_state import (
    CrtPureCausalObservation,
    CrtPureReasoningDecision,
    CrtPureSituationModel,
    reason,
)
from qore.infrastructure.traders.crt_pure_strategy_identity_memory import (
    strategy_identity_ready,
)

IDENTITY = "VT08_CRT_PURE_R2CD_USDJPY_COGNITIVE_WAIT_RESOLUTION_WF_001"
SCHEMA = "qore.vt08.crt_pure.r2cd_usdjpy_cognitive_wait_resolution_wf.v1"
TARGET_R = Decimal("1.5")
MIN_DENSITY_PER_YEAR = 170.0
COST_STRESS_R: tuple[float, ...] = (0.02, 0.05)


@dataclass(frozen=True, slots=True)
class DelayedRecord:
    source: r2bz.CognitiveRecord
    journey_state: str
    delayed_trade: Model1LabTrade | None
    delayed_doa: bool | None
    terminal_reason: str | None


@dataclass(frozen=True, slots=True)
class JourneyCell:
    state: str
    support: int
    expected_r: float
    doa_rate: float


@dataclass(frozen=True, slots=True)
class JourneyModel:
    baseline_mean_r: float
    baseline_doa_rate: float
    cells: tuple[JourneyCell, ...]

    def lookup(self, state: str) -> JourneyCell | None:
        return next((cell for cell in self.cells if cell.state == state), None)


@dataclass(frozen=True, slots=True)
class ExecutedRecord:
    trade: Model1LabTrade
    dead_on_arrival: bool
    origin: str


def _record_key(record: r2bz.CognitiveRecord) -> tuple[str, str, str, str, str]:
    trade = record.trade
    return (
        trade.source_opened_at,
        trade.confirmation_opened_at,
        trade.entry_opened_at,
        trade.parent_direction,
        trade.timing_triplet,
    )


def _bars_from(
    trade: Model1LabTrade,
    *,
    start: datetime,
    by_time: dict[datetime, M15Bar],
) -> tuple[M15Bar, ...]:
    c3_close = datetime.fromisoformat(trade.c3_opened_at) + timedelta(hours=4)
    return tuple(
        by_time[opened_at]
        for opened_at in sorted(by_time)
        if start <= opened_at < c3_close
    )


def _full_stop_doa(
    trade: Model1LabTrade,
    bars: tuple[M15Bar, ...],
) -> bool:
    if trade.exit_reason != "STOP" or abs(float(trade.r_multiple) + 1.0) > 1e-9:
        return False

    bullish = trade.parent_direction == "BULLISH"
    entry = Decimal(trade.entry_price_relative)
    stop = Decimal(trade.stop_price_relative)
    target = Decimal(trade.target_price_relative)
    risk = abs(entry - stop)
    max_close = Decimal("0")

    for bar in bars:
        if bullish:
            stop_hit = Decimal(bar.low_price) <= stop
            target_hit = Decimal(bar.high_price) >= target
        else:
            stop_hit = Decimal(bar.high_price) >= stop
            target_hit = Decimal(bar.low_price) <= target
        if stop_hit or target_hit:
            break
        close = Decimal(bar.close_price)
        close_r = (
            (close - entry) / risk
            if bullish
            else (entry - close) / risk
        )
        max_close = max(max_close, close_r)

    return max_close < Decimal("0.25")


def _delayed_record(
    record: r2bz.CognitiveRecord,
    *,
    by_time: dict[datetime, M15Bar],
) -> DelayedRecord:
    trade = record.trade
    original_entry_time = datetime.fromisoformat(trade.entry_opened_at)
    first_bar = by_time.get(original_entry_time)
    if first_bar is None:
        return DelayedRecord(
            record,
            "MISSING_FIRST_M15",
            None,
            None,
            "MISSING_FIRST_M15",
        )

    bullish = trade.parent_direction == "BULLISH"
    stop = Decimal(trade.stop_price_relative)
    original_target = Decimal(trade.target_price_relative)
    if bullish:
        stop_hit = Decimal(first_bar.low_price) <= stop
        target_hit = Decimal(first_bar.high_price) >= original_target
    else:
        stop_hit = Decimal(first_bar.high_price) >= stop
        target_hit = Decimal(first_bar.low_price) <= original_target

    if stop_hit:
        return DelayedRecord(
            record,
            "INVALIDATED_BEFORE_REASSESS",
            None,
            None,
            "STRUCTURAL_STOP_TOUCHED",
        )
    if target_hit:
        return DelayedRecord(
            record,
            "DESTINATION_CONSUMED_BEFORE_REASSESS",
            None,
            None,
            "ORIGINAL_DESTINATION_CONSUMED",
        )

    close_r = r2cb._close_r(trade, first_bar)
    journey_state = r2cb._bucket(close_r)
    delayed_time = original_entry_time + timedelta(minutes=15)
    c3_close = datetime.fromisoformat(trade.c3_opened_at) + timedelta(hours=4)
    if delayed_time >= c3_close:
        return DelayedRecord(
            record,
            journey_state,
            None,
            None,
            "C3_EXPIRED",
        )
    delayed_bar = by_time.get(delayed_time)
    if delayed_bar is None:
        return DelayedRecord(
            record,
            journey_state,
            None,
            None,
            "MISSING_DELAYED_ENTRY_M15",
        )

    entry = Decimal(delayed_bar.open_price)
    if bullish:
        if stop >= entry:
            return DelayedRecord(
                record,
                journey_state,
                None,
                None,
                "DELAYED_ENTRY_BELOW_STRUCTURAL_STOP",
            )
        risk = entry - stop
        target = entry + TARGET_R * risk
    else:
        if stop <= entry:
            return DelayedRecord(
                record,
                journey_state,
                None,
                None,
                "DELAYED_ENTRY_ABOVE_STRUCTURAL_STOP",
            )
        risk = stop - entry
        target = entry - TARGET_R * risk

    base = Model1LabTrade(
        schema=SCHEMA,
        identity=f"{IDENTITY}:DELAYED_BASE",
        market=trade.market,
        reference_policy=trade.reference_policy,
        reference_count=trade.reference_count,
        reference_ids=trade.reference_ids,
        parent_direction=trade.parent_direction,
        timing_triplet=trade.timing_triplet,
        c3_opened_at=trade.c3_opened_at,
        source_opened_at=trade.source_opened_at,
        confirmation_opened_at=trade.confirmation_opened_at,
        entry_opened_at=delayed_time.isoformat(),
        entry_price_relative=int(entry),
        stop_price_relative=int(stop),
        target_price_relative=str(target),
        exit_price_relative=str(entry),
        exit_reason="UNRESOLVED",
        r_multiple=0.0,
    )
    lifecycle = _bars_from(
        trade,
        start=delayed_time,
        by_time=by_time,
    )
    if not lifecycle:
        return DelayedRecord(
            record,
            journey_state,
            None,
            None,
            "NO_DELAYED_LIFECYCLE",
        )
    managed = _simulate(
        trade=base,
        bars=lifecycle,
        policy=ProtectionPolicy.CONTROL,
    )
    return DelayedRecord(
        source=record,
        journey_state=journey_state,
        delayed_trade=managed,
        delayed_doa=_full_stop_doa(managed, lifecycle),
        terminal_reason=None,
    )


def _fit_journey(
    rows: tuple[DelayedRecord, ...],
) -> tuple[JourneyModel, dict[str, Any]]:
    eligible = tuple(
        row
        for row in rows
        if row.delayed_trade is not None and row.delayed_doa is not None
    )
    if not eligible:
        return JourneyModel(0.0, 0.0, ()), {"reason": "EMPTY_TRAINING"}

    baseline_mean = sum(
        float(row.delayed_trade.r_multiple)
        for row in eligible
        if row.delayed_trade is not None
    ) / len(eligible)
    baseline_doa = sum(bool(row.delayed_doa) for row in eligible) / len(eligible)

    counts: Counter[str] = Counter()
    r_sums: defaultdict[str, float] = defaultdict(float)
    doa_counts: Counter[str] = Counter()
    for row in eligible:
        assert row.delayed_trade is not None
        counts[row.journey_state] += 1
        r_sums[row.journey_state] += float(row.delayed_trade.r_multiple)
        doa_counts[row.journey_state] += int(bool(row.delayed_doa))

    cells: list[JourneyCell] = []
    for state, count in sorted(counts.items()):
        if count < MIN_CELL_SUPPORT:
            continue
        expected_r = (
            r_sums[state] + PRIOR_STRENGTH * baseline_mean
        ) / (count + PRIOR_STRENGTH)
        doa_rate = (
            doa_counts[state] + PRIOR_STRENGTH * baseline_doa
        ) / (count + PRIOR_STRENGTH)
        cells.append(
            JourneyCell(
                state=state,
                support=count,
                expected_r=round(expected_r, 10),
                doa_rate=round(doa_rate, 10),
            )
        )

    return (
        JourneyModel(
            baseline_mean_r=baseline_mean,
            baseline_doa_rate=baseline_doa,
            cells=tuple(cells),
        ),
        {
            "eligible_delayed_trades": len(eligible),
            "baseline_mean_r": round(baseline_mean, 10),
            "baseline_doa_rate": round(baseline_doa, 10),
            "cells": [asdict(cell) for cell in cells],
        },
    )


def _knowledge(
    model: JourneyModel,
    state: str,
) -> tuple[CrtPureKnowledgeState, tuple[str, ...], tuple[str, ...], JourneyCell | None]:
    cell = model.lookup(state)
    if cell is None:
        return (
            CrtPureKnowledgeState.UNKNOWN,
            (),
            ("JOURNEY_EXPERIENCE_UNRESOLVED",),
            None,
        )
    positive_r = cell.expected_r > 0
    lower_doa = cell.doa_rate < model.baseline_doa_rate
    if positive_r and lower_doa:
        return CrtPureKnowledgeState.KNOWN, (), (), cell
    if (not positive_r) and (not lower_doa):
        return (
            CrtPureKnowledgeState.CONFLICTED,
            ("JOURNEY_NEGATIVE_R_AND_HIGH_DOA",),
            (),
            cell,
        )
    return (
        CrtPureKnowledgeState.PARTIAL,
        (),
        ("JOURNEY_MIXED_R_DOA_EVIDENCE",),
        cell,
    )


def _second_decision(
    model: JourneyModel,
    row: DelayedRecord,
) -> CrtPureReasoningDecision:
    if row.delayed_trade is None:
        raise ValueError("second decision requires delayed trade")
    trade = row.delayed_trade
    observed_at = datetime.fromisoformat(trade.entry_opened_at)
    knowledge, contradictions, uncertainties, cell = _knowledge(
        model,
        row.journey_state,
    )
    observations = [
        CrtPureCausalObservation(
            name="WAIT_JOURNEY_STATE",
            observed_at=observed_at,
            value_token=row.journey_state,
        )
    ]
    if cell is not None:
        observations.extend(
            (
                CrtPureCausalObservation(
                    name="JOURNEY_EXPECTED_DELAYED_R",
                    observed_at=observed_at,
                    value_token=f"{cell.expected_r:.8f}",
                ),
                CrtPureCausalObservation(
                    name="JOURNEY_DELAYED_DOA_RATE",
                    observed_at=observed_at,
                    value_token=f"{cell.doa_rate:.8f}",
                ),
            )
        )

    state = CrtPureSituationModel(
        market=r2bz.MARKET,
        observed_at=observed_at,
        hypothesis_id=(
            f"USDJPY:{trade.source_opened_at}:{trade.confirmation_opened_at}"
        ),
        source_event_id=trade.source_opened_at,
        event_generation=1,
        attention_state=CrtPureAttentionState.DECISION,
        hypothesis_stage=CrtPureHypothesisStage.CONFIRMED,
        data_integrity_ok=True,
        strategy_identity_ready=strategy_identity_ready(),
        source_event_present=True,
        confirmation_complete=True,
        destination_context_known=True,
        destination_available=True,
        execution_data_fresh=True,
        knowledge_state=knowledge,
        contradictions=contradictions,
        uncertainties=uncertainties,
        market_context_tokens=(row.journey_state,),
        observations=tuple(observations),
    )
    return reason(state)


def _metrics(rows: tuple[ExecutedRecord, ...]) -> dict[str, Any]:
    trades = tuple(row.trade for row in rows)
    summary = _summary(trades)
    doa = sum(row.dead_on_arrival for row in rows)
    return {
        **summary,
        "dead_on_arrival": doa,
        "dead_on_arrival_rate": (
            0.0 if not rows else round(doa / len(rows), 8)
        ),
        "cost_stress": {
            f"COST_{cost:.2f}R": _stress_summary(trades, cost)
            for cost in COST_STRESS_R
        },
        "origin_counts": dict(Counter(row.origin for row in rows)),
    }


def run_walk_forward() -> tuple[
    tuple[DelayedRecord, ...],
    dict[str, Any],
]:
    records, _ = r2bz._build_records()
    m5 = load_m5_window(
        r2bz.MARKET,
        start=START - timedelta(days=2),
        end_exclusive=END + timedelta(days=1),
    )
    m15 = aggregate_complete_m15(m5)
    by_time = {bar.opened_at: bar for bar in m15}

    delayed = tuple(
        _delayed_record(record, by_time=by_time)
        for record in records
    )
    delayed_by_key = {
        _record_key(row.source): row
        for row in delayed
    }

    baseline_rows: list[ExecutedRecord] = []
    portfolio_rows: list[ExecutedRecord] = []
    folds: list[dict[str, Any]] = []

    for oos_year in range(START.year + r2bz.TRAINING_YEARS, END.year):
        training = r2bz._slice(
            records,
            r2bz._year_start(oos_year - r2bz.TRAINING_YEARS),
            r2bz._year_start(oos_year),
        )
        oos = r2bz._slice(
            records,
            r2bz._year_start(oos_year),
            r2bz._year_start(oos_year + 1),
        )
        initial_model, initial_fit = r2bz._fit(training)
        journey_training = tuple(
            delayed_by_key[_record_key(row)]
            for row in training
        )
        journey_model, journey_fit = _fit_journey(journey_training)

        fold_baseline = tuple(
            ExecutedRecord(row.trade, row.dead_on_arrival, "BASELINE")
            for row in oos
        )
        baseline_rows.extend(fold_baseline)

        fold_portfolio: list[ExecutedRecord] = []
        initial_counts: Counter[str] = Counter()
        second_counts: Counter[str] = Counter()
        terminal_wait: Counter[str] = Counter()

        for row in oos:
            initial = r2bz._decision(initial_model, row)
            initial_counts[initial.action.value] += 1
            if initial.action is CrtPureReasoningAction.EXECUTE:
                fold_portfolio.append(
                    ExecutedRecord(
                        row.trade,
                        row.dead_on_arrival,
                        "INITIAL_EXECUTE",
                    )
                )
                continue
            if initial.action is CrtPureReasoningAction.ABSTAIN:
                continue

            delayed_row = delayed_by_key[_record_key(row)]
            if delayed_row.delayed_trade is None:
                terminal_wait[delayed_row.terminal_reason or "UNKNOWN"] += 1
                continue
            second = _second_decision(journey_model, delayed_row)
            second_counts[second.action.value] += 1
            if second.action is CrtPureReasoningAction.EXECUTE:
                assert delayed_row.delayed_doa is not None
                fold_portfolio.append(
                    ExecutedRecord(
                        delayed_row.delayed_trade,
                        delayed_row.delayed_doa,
                        "WAIT_DELAYED_EXECUTE",
                    )
                )

        frozen_fold = tuple(
            sorted(fold_portfolio, key=lambda item: item.trade.entry_opened_at)
        )
        portfolio_rows.extend(frozen_fold)
        folds.append(
            {
                "oos_start": r2bz._year_start(oos_year).isoformat(),
                "initial_fit": initial_fit,
                "journey_fit": journey_fit,
                "initial_action_counts": dict(initial_counts),
                "second_action_counts": dict(second_counts),
                "terminal_wait_counts": dict(terminal_wait),
                "baseline": _metrics(fold_baseline),
                "portfolio": _metrics(frozen_fold),
            }
        )

    baseline = tuple(
        sorted(baseline_rows, key=lambda item: item.trade.entry_opened_at)
    )
    portfolio = tuple(
        sorted(portfolio_rows, key=lambda item: item.trade.entry_opened_at)
    )
    baseline_metrics = _metrics(baseline)
    portfolio_metrics = _metrics(portfolio)
    years = len(folds)
    density = 0.0 if years == 0 else len(portfolio) / years
    positive_fraction = (
        0.0
        if not folds
        else sum(float(fold["portfolio"]["total_r"]) > 0 for fold in folds)
        / len(folds)
    )

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "market": r2bz.MARKET.value,
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "initial_cognitive_identity": r2bz.IDENTITY,
        "wait_journey_contract": {
            "wait_bars": 1,
            "observation_timeframe": "M15",
            "delayed_entry": "NEXT_M15_OPEN",
            "structural_stop_preserved": True,
            "target": "FIXED_1_5R_RECALCULATED_FROM_DELAYED_ENTRY",
            "expiry": "ORIGINAL_C3_CLOSE",
            "same_bar_precedence": "STOP_FIRST",
            "protection": ProtectionPolicy.CONTROL.value,
        },
        "journey_memory": {
            "training_years": r2bz.TRAINING_YEARS,
            "minimum_cell_support": MIN_CELL_SUPPORT,
            "prior_strength": PRIOR_STRENGTH,
            "state": "FIRST_M15_JOURNEY_BUCKET",
            "labels": ["DELAYED_EXPECTED_R", "DELAYED_DOA_RATE"],
            "future_outcome_visibility": False,
            "audusd_state_transfer": False,
        },
        "combined_oos_baseline": baseline_metrics,
        "combined_oos_cognitive_portfolio": portfolio_metrics,
        "portfolio_trades_per_year": round(density, 8),
        "positive_oos_year_fraction": round(positive_fraction, 8),
        "research_checks": {
            "density_ge_170": density >= MIN_DENSITY_PER_YEAR,
            "pf_improved": (
                float(portfolio_metrics["profit_factor"] or 0.0)
                > float(baseline_metrics["profit_factor"] or 0.0)
            ),
            "total_r_improved": (
                float(portfolio_metrics["total_r"])
                > float(baseline_metrics["total_r"])
            ),
            "dd_improved": (
                float(portfolio_metrics["max_drawdown_r"])
                < float(baseline_metrics["max_drawdown_r"])
            ),
            "doa_improved": (
                float(portfolio_metrics["dead_on_arrival_rate"])
                < float(baseline_metrics["dead_on_arrival_rate"])
            ),
        },
        "folds": folds,
        "automatic_promotion": False,
        "research_only": True,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    return delayed, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    delayed, report = run_walk_forward()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "delayed.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in delayed:
            handle.write(
                json.dumps(asdict(row), sort_keys=True, default=str) + "\n"
            )
    print(
        "CRT_R2CD_USDJPY_COGNITIVE_WAIT_RESOLUTION_JSON="
        + json.dumps(report, sort_keys=True)
    )


if __name__ == "__main__":
    main()
