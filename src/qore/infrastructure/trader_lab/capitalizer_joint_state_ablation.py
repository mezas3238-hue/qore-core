"""Targeted joint-state ablations for QORE Capitalizer USDJPY development.

The prior full-baseline joint-state report identified a categorical state with both negative
aggregate expectancy and broad temporal weakness:

RECLAIM_ALL_FRESH + OLDER_H1_SOURCE + PRIOR_HIGH_LOW_ONLY + RECLAIM_STRICTLY_BEFORE.

This module tests that exact state and two nearby categorical groupings. It introduces no
numeric threshold and starts from the already-defined consumed-development baseline:
Structural V2 + NO_RECLAIM CISD-cross-H1 exclusion + PROFITABLE_SWING_LOCK.

This remains falsification-only. No rule is selected, no candidate is frozen, no costs are
claimed, and no fresh holdout or promotion is asserted.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_h1_boundary_type_forensics import (
    _boundary_type_state,
    _episode_boundary_types,
)
from qore.infrastructure.trader_lab.capitalizer_h1_episode_multiplicity_forensics import (
    _baseline,
    _journey_boundaries,
)
from qore.infrastructure.trader_lab.capitalizer_h1_source_age_forensics import (
    _source_age_state,
)
from qore.infrastructure.trader_lab.capitalizer_position_lifecycle_forensics import (
    _state_family,
    _year,
)
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Metrics,
    CapitalizerR0Trade,
    summarize_r0,
)
from qore.infrastructure.trader_lab.capitalizer_reclaim_phase_forensics import (
    _episode_reclaim_times,
    _reclaim_phase,
)

IDENTITY = "QORE_CAPITALIZER_JOINT_STATE_ABLATION_V1"


@dataclass(frozen=True, slots=True)
class CapitalizerJointStateAblation:
    name: str
    excluded_trades: int
    metrics: CapitalizerR0Metrics


@dataclass(frozen=True, slots=True)
class CapitalizerJointStateAblationAnnual:
    name: str
    year: int
    metrics: CapitalizerR0Metrics


@dataclass(frozen=True, slots=True)
class CapitalizerJointStateAblationReport:
    identity: str
    symbol: str
    baseline_metrics: CapitalizerR0Metrics
    ablations: tuple[CapitalizerJointStateAblation, ...]
    annual: tuple[CapitalizerJointStateAblationAnnual, ...]
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    development_only: bool = True
    categorical_states_only: bool = True
    numeric_threshold_optimization_used: bool = False
    costs_applied: bool = False
    candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    rule_selected: bool = False
    promotion_allowed: bool = False


def _is_blocked(
    *,
    ablation: str,
    state_family: str,
    source_age_state: str,
    boundary_type_state: str,
    reclaim_phase: str,
) -> bool:
    if state_family != "RECLAIM_ALL_FRESH":
        return False
    if source_age_state != "OLDER_H1_SOURCE":
        return False

    if ablation == "DROP_OLDER_PRIOR_STRICT_RECLAIM":
        return (
            boundary_type_state == "PRIOR_HIGH_LOW_ONLY"
            and reclaim_phase == "RECLAIM_STRICTLY_BEFORE"
        )
    if ablation == "DROP_OLDER_PRIOR_ALL_RECLAIM_PHASES":
        return boundary_type_state == "PRIOR_HIGH_LOW_ONLY"
    if ablation == "DROP_OLDER_NONSWING_STRICT_RECLAIM":
        return (
            boundary_type_state
            in {"PRIOR_HIGH_LOW_ONLY", "MIXED_BOUNDARY_TYPE"}
            and reclaim_phase == "RECLAIM_STRICTLY_BEFORE"
        )
    raise ValueError("unknown joint-state ablation")


def _metrics(trades: tuple[CapitalizerR0Trade, ...]) -> CapitalizerR0Metrics:
    if not trades:
        raise ValueError("joint-state ablation cannot remove all trades")
    return summarize_r0(trades).metrics


def build_joint_state_ablation_report(
    *,
    m5_root: Path,
    journey_root: Path,
    target_root: Path,
) -> CapitalizerJointStateAblationReport:
    baseline, state_index, episode_index = _baseline(
        m5_root=m5_root,
        journey_root=journey_root,
        target_root=target_root,
    )
    if not baseline:
        raise ValueError("joint-state ablation requires baseline trades")

    boundaries = _journey_boundaries(journey_root)
    boundary_types = _episode_boundary_types(journey_root)
    reclaim_times = _episode_reclaim_times(journey_root)

    definitions = (
        "DROP_OLDER_PRIOR_STRICT_RECLAIM",
        "DROP_OLDER_PRIOR_ALL_RECLAIM_PHASES",
        "DROP_OLDER_NONSWING_STRICT_RECLAIM",
    )
    ablations: list[CapitalizerJointStateAblation] = []
    annual: list[CapitalizerJointStateAblationAnnual] = []

    for name in definitions:
        selected: list[CapitalizerR0Trade] = []
        excluded = 0
        for trade in baseline:
            state_family = _state_family(trade, state_index)
            source_age_state = _source_age_state(
                trade,
                episode_index=episode_index,
                boundaries=boundaries,
            )
            boundary_type_state = _boundary_type_state(
                trade,
                episode_index=episode_index,
                boundary_types=boundary_types,
            )
            reclaim_phase = _reclaim_phase(
                trade,
                episode_index=episode_index,
                reclaim_times=reclaim_times,
            )
            if _is_blocked(
                ablation=name,
                state_family=state_family,
                source_age_state=source_age_state,
                boundary_type_state=boundary_type_state,
                reclaim_phase=reclaim_phase,
            ):
                excluded += 1
                continue
            selected.append(trade)

        selected_tuple = tuple(selected)
        ablations.append(
            CapitalizerJointStateAblation(
                name=name,
                excluded_trades=excluded,
                metrics=_metrics(selected_tuple),
            )
        )
        for year in sorted({_year(item) for item in selected_tuple}):
            subset = tuple(item for item in selected_tuple if _year(item) == year)
            if subset:
                annual.append(
                    CapitalizerJointStateAblationAnnual(
                        name=name,
                        year=year,
                        metrics=_metrics(subset),
                    )
                )

    return CapitalizerJointStateAblationReport(
        identity=IDENTITY,
        symbol=baseline[0].symbol,
        baseline_metrics=_metrics(baseline),
        ablations=tuple(ablations),
        annual=tuple(annual),
    )


def write_joint_state_ablation_report(
    report: CapitalizerJointStateAblationReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{report.symbol.lower()}-joint-state-ablation-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer targeted categorical joint-state ablation"
    )
    parser.add_argument("m5_root", type=Path)
    parser.add_argument("journey_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_joint_state_ablation_report(
        m5_root=args.m5_root,
        journey_root=args.journey_root,
        target_root=args.target_root,
    )
    write_joint_state_ablation_report(report, args.output)
    print(
        json.dumps(
            {
                "identity": report.identity,
                "symbol": report.symbol,
                "baseline": asdict(report.baseline_metrics),
                "ablations": [
                    {
                        "name": row.name,
                        "excluded_trades": row.excluded_trades,
                        "metrics": asdict(row.metrics),
                    }
                    for row in report.ablations
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
