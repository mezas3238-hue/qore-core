"""Scenario-tree projection for Shared Core.

The scenario tree is not a future-data oracle. It expands the current
competitive-hypothesis distribution through a frozen causal transition model to
represent plausible next states and their relative probability mass.

Branches are probability-weighted hypotheses, not trade instructions. The tree
has no strategy, sizing, risk, stop, target, order or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.core_stack_v2.competitive_hypothesis_engine import (
    CompetitiveHypothesis,
    CompetitiveHypothesisState,
)


@dataclass(frozen=True, slots=True)
class ScenarioTransition:
    source: CompetitiveHypothesis
    target: CompetitiveHypothesis
    probability_bps: int

    def __post_init__(self) -> None:
        if not 0 <= self.probability_bps <= 10_000:
            raise ValueError("transition probability must be within 0..10000")


@dataclass(frozen=True, slots=True)
class ScenarioTreePolicy:
    depth: int = 3
    beam_width: int = 8
    minimum_branch_probability_bps: int = 50

    def __post_init__(self) -> None:
        if self.depth < 1:
            raise ValueError("scenario-tree depth must be positive")
        if self.beam_width < 1:
            raise ValueError("scenario-tree beam width must be positive")
        if not 0 <= self.minimum_branch_probability_bps <= 10_000:
            raise ValueError(
                "minimum branch probability must be within 0..10000"
            )


@dataclass(frozen=True, slots=True)
class ScenarioBranch:
    path: tuple[CompetitiveHypothesis, ...]
    probability_bps: int

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("scenario branch path must be non-empty")
        if not 0 <= self.probability_bps <= 10_000:
            raise ValueError("branch probability must be within 0..10000")


@dataclass(frozen=True, slots=True)
class ScenarioTree:
    root_as_of_iso: str
    branches: tuple[ScenarioBranch, ...]
    depth: int
    retained_probability_bps: int
    pruned_probability_bps: int
    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    stop_authority: bool = False
    target_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.depth < 1:
            raise ValueError("scenario-tree depth must be positive")
        for value in (
            self.retained_probability_bps,
            self.pruned_probability_bps,
        ):
            if not 0 <= value <= 10_000:
                raise ValueError("scenario-tree probability must be within 0..10000")
        if (
            self.outcome_used
            or self.pnl_used
            or self.future_market_used
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.stop_authority
            or self.target_authority
            or self.execution_authority
        ):
            raise ValueError("scenario tree cannot carry trading authority")


def _transition_matrix(
    transitions: tuple[ScenarioTransition, ...],
) -> dict[CompetitiveHypothesis, tuple[tuple[CompetitiveHypothesis, int], ...]]:
    grouped: dict[CompetitiveHypothesis, list[tuple[CompetitiveHypothesis, int]]] = {}
    for item in transitions:
        grouped.setdefault(item.source, []).append(
            (item.target, item.probability_bps)
        )

    matrix: dict[
        CompetitiveHypothesis,
        tuple[tuple[CompetitiveHypothesis, int], ...],
    ] = {}
    for source in CompetitiveHypothesis:
        values = grouped.get(source)
        if not values:
            matrix[source] = ((source, 10_000),)
            continue
        total = sum(probability for _, probability in values)
        if total <= 0:
            raise ValueError("scenario transition row must contain positive mass")
        normalized = [
            (target, probability * 10_000 // total)
            for target, probability in values
        ]
        remainder = 10_000 - sum(probability for _, probability in normalized)
        if remainder:
            target, probability = normalized[0]
            normalized[0] = (target, probability + remainder)
        matrix[source] = tuple(normalized)
    return matrix


def build_scenario_tree(
    *,
    state: CompetitiveHypothesisState,
    transitions: tuple[ScenarioTransition, ...],
    policy: ScenarioTreePolicy | None = None,
) -> ScenarioTree:
    """Expand a bounded scenario tree from current hypothesis probabilities."""

    effective = policy or ScenarioTreePolicy()
    matrix = _transition_matrix(transitions)
    branches = [
        ScenarioBranch(
            path=(posterior.hypothesis,),
            probability_bps=posterior.probability_bps,
        )
        for posterior in state.posteriors
        if posterior.probability_bps >= effective.minimum_branch_probability_bps
    ]

    for _ in range(1, effective.depth):
        expanded: list[ScenarioBranch] = []
        for branch in branches:
            source = branch.path[-1]
            for target, transition_bps in matrix[source]:
                probability = branch.probability_bps * transition_bps // 10_000
                if probability < effective.minimum_branch_probability_bps:
                    continue
                expanded.append(
                    ScenarioBranch(
                        path=(*branch.path, target),
                        probability_bps=probability,
                    )
                )
        branches = sorted(
            expanded,
            key=lambda item: (-item.probability_bps, tuple(x.value for x in item.path)),
        )[: effective.beam_width]
        if not branches:
            break

    retained = min(10_000, sum(item.probability_bps for item in branches))
    return ScenarioTree(
        root_as_of_iso=state.as_of_iso,
        branches=tuple(branches),
        depth=effective.depth,
        retained_probability_bps=retained,
        pruned_probability_bps=max(0, 10_000 - retained),
    )
