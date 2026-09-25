"""R2-BY AUDUSD cognitive experience sovereignty walk-forward.

Purpose
-------
Use the already-implemented CRT PURE cognitive stack explicitly rather than
adding another static post-hoc filter.

The market-specific Experience Memory is learned from prior 4Y only on the
frozen REF_DELAY_DIRECTION state.  Each supported cell estimates:

- expected R with empirical-Bayes shrinkage;
- dead-on-arrival probability with the same shrinkage.

At the next 1Y OOS decision point the experience is translated into the frozen
cognitive ontology:

- KNOWN: expected R > 0 and DOA rate < training baseline -> cognition may EXECUTE;
- CONFLICTED: expected R <= 0 and DOA rate >= baseline -> cognition ABSTAINS;
- PARTIAL: mixed evidence -> cognition WAITS;
- UNKNOWN: insufficient cell support -> cognition WAITS.

The final action is produced by crt_pure_cognitive_state.reason(), not by this
lab.  No future outcome is visible to the Situation Model.  Strategy Identity
remains immutable and source-gated.

No target, stop, entry, confirmation, competition or lifecycle rule changes.
Research only.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2bj_audusd_root_cause_expected_r_family as r2bj,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bh_audusd_entry_viability_wf import (
    END,
    START,
    TRAINING_YEARS,
    ViabilityRecord,
    _build_records,
    _slice,
    _year_start,
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
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_strategy_identity_memory import (
    strategy_identity_ready,
)

IDENTITY = "VT08_CRT_PURE_R2BY_AUDUSD_COGNITIVE_EXPERIENCE_WF_001"
SCHEMA = "qore.vt08.crt_pure.r2by_audusd_cognitive_experience_wf.v1"
MARKET = CrtPureMarket.AUDUSD
MIN_CELL_SUPPORT = r2bj.MIN_CELL_SUPPORT
PRIOR_STRENGTH = r2bj.PRIOR_STRENGTH
MIN_DENSITY_PER_YEAR = 170.0


@dataclass(frozen=True, slots=True)
class ExperienceCell:
    key: str
    support: int
    expected_r: float
    doa_rate: float


@dataclass(frozen=True, slots=True)
class ExperienceModel:
    baseline_mean_r: float
    baseline_doa_rate: float
    cells: tuple[ExperienceCell, ...]

    def lookup(self, key: str) -> ExperienceCell | None:
        return next((cell for cell in self.cells if cell.key == key), None)


def _cell_key(record: ViabilityRecord) -> str:
    features = dict(record.features)
    ref = "REF1" if features["source_reference_count"] == "REF1" else "REF2_PLUS"
    delay_raw = features["confirmation_delay"]
    delay = delay_raw if delay_raw in {"D1", "D2"} else "D3_PLUS"
    return f"{ref}|{delay}|{features['direction']}"


def _fit(training: tuple[ViabilityRecord, ...]) -> tuple[ExperienceModel, dict[str, Any]]:
    if not training:
        return (
            ExperienceModel(
                baseline_mean_r=0.0,
                baseline_doa_rate=0.0,
                cells=(),
            ),
            {"reason": "EMPTY_TRAINING"},
        )

    baseline_mean = sum(float(row.trade.r_multiple) for row in training) / len(training)
    baseline_doa = sum(row.dead_on_arrival for row in training) / len(training)

    counts: Counter[str] = Counter()
    r_sums: defaultdict[str, float] = defaultdict(float)
    doa_counts: Counter[str] = Counter()
    for row in training:
        key = _cell_key(row)
        counts[key] += 1
        r_sums[key] += float(row.trade.r_multiple)
        doa_counts[key] += int(row.dead_on_arrival)

    cells: list[ExperienceCell] = []
    for key, count in sorted(counts.items()):
        if count < MIN_CELL_SUPPORT:
            continue
        expected_r = (
            r_sums[key] + PRIOR_STRENGTH * baseline_mean
        ) / (count + PRIOR_STRENGTH)
        doa_rate = (
            doa_counts[key] + PRIOR_STRENGTH * baseline_doa
        ) / (count + PRIOR_STRENGTH)
        cells.append(
            ExperienceCell(
                key=key,
                support=count,
                expected_r=round(expected_r, 10),
                doa_rate=round(doa_rate, 10),
            )
        )

    model = ExperienceModel(
        baseline_mean_r=baseline_mean,
        baseline_doa_rate=baseline_doa,
        cells=tuple(cells),
    )
    return model, {
        "baseline_mean_r": round(baseline_mean, 10),
        "baseline_doa_rate": round(baseline_doa, 10),
        "eligible_cells": len(cells),
        "cells": [asdict(cell) for cell in cells],
    }


def _knowledge(
    model: ExperienceModel,
    record: ViabilityRecord,
) -> tuple[CrtPureKnowledgeState, tuple[str, ...], tuple[str, ...], ExperienceCell | None]:
    cell = model.lookup(_cell_key(record))
    if cell is None:
        return (
            CrtPureKnowledgeState.UNKNOWN,
            (),
            ("EXPERIENCE_CELL_UNRESOLVED",),
            None,
        )

    positive_r = cell.expected_r > 0.0
    lower_doa = cell.doa_rate < model.baseline_doa_rate

    if positive_r and lower_doa:
        return CrtPureKnowledgeState.KNOWN, (), (), cell

    if (not positive_r) and (not lower_doa):
        return (
            CrtPureKnowledgeState.CONFLICTED,
            ("EXPERIENCE_NEGATIVE_R_AND_HIGH_DOA",),
            (),
            cell,
        )

    return (
        CrtPureKnowledgeState.PARTIAL,
        (),
        ("EXPERIENCE_MIXED_R_DOA_EVIDENCE",),
        cell,
    )


def _decision(
    *,
    model: ExperienceModel,
    record: ViabilityRecord,
) -> CrtPureReasoningDecision:
    trade = record.trade
    observed_at = datetime.fromisoformat(trade.entry_opened_at)
    knowledge, contradictions, uncertainties, cell = _knowledge(model, record)
    key = _cell_key(record)
    observations = [
        CrtPureCausalObservation(
            name="EXPERIENCE_CELL",
            observed_at=observed_at,
            value_token=key,
        ),
        CrtPureCausalObservation(
            name="EXPERIENCE_BASELINE_DOA",
            observed_at=observed_at,
            value_token=f"{model.baseline_doa_rate:.8f}",
        ),
    ]
    if cell is not None:
        observations.extend(
            (
                CrtPureCausalObservation(
                    name="EXPERIENCE_EXPECTED_R",
                    observed_at=observed_at,
                    value_token=f"{cell.expected_r:.8f}",
                ),
                CrtPureCausalObservation(
                    name="EXPERIENCE_DOA_RATE",
                    observed_at=observed_at,
                    value_token=f"{cell.doa_rate:.8f}",
                ),
            )
        )

    state = CrtPureSituationModel(
        market=MARKET,
        observed_at=observed_at,
        hypothesis_id=(
            f"AUDUSD:{trade.source_opened_at}:{trade.confirmation_opened_at}"
        ),
        source_event_id=trade.source_opened_at,
        event_generation=max(1, int(trade.source_generation)),
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
        market_context_tokens=(key,),
        observations=tuple(observations),
    )
    return reason(state)


def _metrics(records: tuple[ViabilityRecord, ...]) -> dict[str, Any]:
    return r2bj._metrics(records)


def run_walk_forward() -> tuple[
    tuple[ViabilityRecord, ...],
    dict[str, Any],
]:
    records, source_diagnostics = _build_records()
    baseline_oos: list[ViabilityRecord] = []
    action_rows: dict[CrtPureReasoningAction, list[ViabilityRecord]] = {
        action: [] for action in CrtPureReasoningAction
    }
    folds: list[dict[str, Any]] = []

    for oos_year in range(START.year + TRAINING_YEARS, END.year):
        training = _slice(
            records,
            _year_start(oos_year - TRAINING_YEARS),
            _year_start(oos_year),
        )
        oos = _slice(
            records,
            _year_start(oos_year),
            _year_start(oos_year + 1),
        )
        model, fit = _fit(training)
        per_action: dict[CrtPureReasoningAction, list[ViabilityRecord]] = {
            action: [] for action in CrtPureReasoningAction
        }
        reason_counts: Counter[str] = Counter()

        for row in oos:
            decision = _decision(model=model, record=row)
            per_action[decision.action].append(row)
            action_rows[decision.action].append(row)
            reason_counts.update(decision.auditable_why)

        baseline_oos.extend(oos)
        folds.append(
            {
                "training_start": _year_start(
                    oos_year - TRAINING_YEARS
                ).isoformat(),
                "oos_start": _year_start(oos_year).isoformat(),
                "fit": fit,
                "oos_baseline": _metrics(oos),
                "actions": {
                    action.value: {
                        "count": len(per_action[action]),
                        "metrics": _metrics(tuple(per_action[action])),
                    }
                    for action in CrtPureReasoningAction
                },
                "auditable_why_counts": dict(reason_counts),
            }
        )

    baseline = tuple(
        sorted(baseline_oos, key=lambda row: row.trade.entry_opened_at)
    )
    frozen_actions = {
        action: tuple(
            sorted(
                action_rows[action],
                key=lambda row: row.trade.entry_opened_at,
            )
        )
        for action in CrtPureReasoningAction
    }
    execute = frozen_actions[CrtPureReasoningAction.EXECUTE]
    baseline_metrics = _metrics(baseline)
    execute_metrics = _metrics(execute)
    years = len(folds)
    execute_per_year = 0.0 if years == 0 else len(execute) / years
    positive_fraction = (
        0.0
        if not folds
        else sum(
            float(fold["actions"]["EXECUTE"]["metrics"]["total_r"]) > 0
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
        "experience_memory": {
            "state": "REF_DELAY_DIRECTION",
            "minimum_cell_support": MIN_CELL_SUPPORT,
            "prior_strength": PRIOR_STRENGTH,
            "labels": ["EXPECTED_R", "DEAD_ON_ARRIVAL_RATE"],
            "future_outcome_visibility": False,
            "market_specific": True,
            "may_rewrite_strategy_identity": False,
        },
        "cognitive_engine": (
            "qore.infrastructure.traders.crt_pure_cognitive_state.reason"
        ),
        "strategy_identity_ready": strategy_identity_ready(),
        "source_diagnostics": source_diagnostics,
        "combined_oos_baseline": baseline_metrics,
        "combined_oos_actions": {
            action.value: {
                "count": len(frozen_actions[action]),
                "metrics": _metrics(frozen_actions[action]),
            }
            for action in CrtPureReasoningAction
        },
        "execute_trades_per_year": round(execute_per_year, 8),
        "execute_positive_oos_year_fraction": round(
            positive_fraction,
            8,
        ),
        "research_checks": {
            "execute_density_ge_170": execute_per_year >= MIN_DENSITY_PER_YEAR,
            "execute_pf_improved": (
                float(execute_metrics["profit_factor"] or 0.0)
                > float(baseline_metrics["profit_factor"] or 0.0)
            ),
            "execute_total_r_improved": (
                float(execute_metrics["total_r"])
                > float(baseline_metrics["total_r"])
            ),
            "execute_doa_rate_improved": (
                float(execute_metrics["dead_on_arrival_rate"])
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
    return records, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    records, report = run_walk_forward()
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
        "CRT_R2BY_AUDUSD_COGNITIVE_EXPERIENCE_JSON="
        + json.dumps(report, sort_keys=True)
    )


if __name__ == "__main__":
    main()
