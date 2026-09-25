"""Bayesian causal-state filter for Shared Core.

The filter converts point-in-time causal state emissions into a persistent
posterior over competing market hypotheses. It is outcome-blind at runtime and
authority-free.

A transition prior may be learned offline from CLOSED historical episodes, but
runtime filtering consumes only:
- the frozen transition matrix,
- current point-in-time emission likelihoods,
- bounded causal history,
- current data integrity and uncertainty.

No PnL, future bars, sizing, risk, order, stop, target or execution authority is
accepted by this module.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from math import log


@dataclass(frozen=True, slots=True)
class CausalStateEmission:
    as_of: datetime
    probabilities_bps: tuple[tuple[str, int], ...]
    uncertainty_bps: int
    data_integrity_bps: int = 10_000

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if not self.probabilities_bps:
            raise ValueError("at least one causal-state probability is required")
        names = [name for name, _ in self.probabilities_bps]
        if len(names) != len(set(names)):
            raise ValueError("causal-state probability names must be unique")
        for name, value in self.probabilities_bps:
            if not name:
                raise ValueError("causal-state name must be non-empty")
            if not 0 <= int(value) <= 10_000:
                raise ValueError("causal-state probability must be within 0..10000")
        if not 0 <= self.uncertainty_bps <= 10_000:
            raise ValueError("uncertainty_bps must be within 0..10000")
        if not 0 <= self.data_integrity_bps <= 10_000:
            raise ValueError("data_integrity_bps must be within 0..10000")
        if sum(value for _, value in self.probabilities_bps) <= 0:
            raise ValueError("causal-state probability mass must be positive")


@dataclass(frozen=True, slots=True)
class FilteredCausalStateBelief:
    as_of: datetime
    evidence_count: int
    posterior_bps: tuple[tuple[str, int], ...]
    dominant_state: str
    dominance_margin_bps: int
    entropy_bps: int
    confidence_bps: int
    reasons: tuple[str, ...]
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
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if self.evidence_count < 1:
            raise ValueError("evidence_count must be positive")
        if not self.dominant_state:
            raise ValueError("dominant_state must be non-empty")
        for name, value in self.posterior_bps:
            if not name:
                raise ValueError("posterior state name must be non-empty")
            if not 0 <= int(value) <= 10_000:
                raise ValueError("posterior probability must be within 0..10000")
        for value in (
            self.dominance_margin_bps,
            self.entropy_bps,
            self.confidence_bps,
        ):
            if not 0 <= int(value) <= 10_000:
                raise ValueError("belief metric must be within 0..10000")
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
            raise ValueError("causal-state belief cannot carry trading authority")

    def probability_bps(self, state: str) -> int:
        for name, value in self.posterior_bps:
            if name == state:
                return int(value)
        return 0


def _normalize(values: list[float]) -> list[int]:
    total = sum(max(0.0, value) for value in values)
    if total <= 0:
        size = len(values)
        base = 10_000 // size
        result = [base] * size
        result[0] += 10_000 - sum(result)
        return result
    raw = [max(0.0, value) * 10_000.0 / total for value in values]
    result = [int(value) for value in raw]
    remainder = 10_000 - sum(result)
    if remainder:
        order = sorted(
            range(len(raw)),
            key=lambda index: raw[index] - result[index],
            reverse=True,
        )
        for index in order[:remainder]:
            result[index] += 1
    return result


def _entropy_bps(values: list[int]) -> int:
    positive = [value / 10_000.0 for value in values if value > 0]
    if len(positive) <= 1:
        return 0
    entropy = -sum(value * log(value) for value in positive)
    maximum = log(len(values))
    return max(0, min(10_000, int(round(entropy / maximum * 10_000))))


def _validated_matrix(
    states: tuple[str, ...],
    transition_bps: Mapping[str, Mapping[str, int]],
) -> list[list[float]]:
    matrix: list[list[float]] = []
    for source in states:
        row = transition_bps.get(source)
        if row is None:
            raise ValueError(f"missing transition row for {source}")
        values: list[float] = []
        for target in states:
            value = int(row.get(target, 0))
            if not 0 <= value <= 10_000:
                raise ValueError("transition probability must be within 0..10000")
            values.append(float(value))
        if sum(values) <= 0:
            raise ValueError("transition row must contain positive mass")
        total = sum(values)
        matrix.append([value / total for value in values])
    return matrix


def filter_causal_state_sequence(
    emissions: tuple[CausalStateEmission, ...],
    *,
    transition_bps: Mapping[str, Mapping[str, int]],
    initial_prior_bps: Mapping[str, int] | None = None,
) -> tuple[FilteredCausalStateBelief, ...]:
    """Bayes-filter a causal emission sequence with a frozen transition prior."""

    if not emissions:
        raise ValueError("at least one causal-state emission is required")
    for left, right in zip(emissions, emissions[1:], strict=False):
        if right.as_of <= left.as_of:
            raise ValueError("causal-state emissions must be strictly increasing")

    states = tuple(name for name, _ in emissions[0].probabilities_bps)
    if any(
        tuple(name for name, _ in frame.probabilities_bps) != states
        for frame in emissions
    ):
        raise ValueError("all emission frames must share canonical state order")
    matrix = _validated_matrix(states, transition_bps)

    if initial_prior_bps is None:
        prior = [1.0 / len(states)] * len(states)
    else:
        values = [max(0, int(initial_prior_bps.get(state, 0))) for state in states]
        total = sum(values)
        if total <= 0:
            raise ValueError("initial prior must contain positive mass")
        prior = [value / total for value in values]

    results: list[FilteredCausalStateBelief] = []
    posterior = prior

    for frame in emissions:
        predicted = [
            sum(posterior[source] * matrix[source][target] for source in range(len(states)))
            for target in range(len(states))
        ]
        emission_raw = [value for _, value in frame.probabilities_bps]
        emission = _normalize([float(value) for value in emission_raw])
        certainty = min(
            int(frame.data_integrity_bps),
            10_000 - int(frame.uncertainty_bps),
        )
        uniform = 10_000 / len(states)
        tempered = [
            certainty * value / 10_000.0
            + (10_000 - certainty) * uniform / 10_000.0
            for value in emission
        ]
        unnormalized = [
            predicted[index] * tempered[index]
            for index in range(len(states))
        ]
        posterior_bps = _normalize(unnormalized)
        posterior = [value / 10_000.0 for value in posterior_bps]

        ranked = sorted(
            range(len(states)),
            key=lambda index: posterior_bps[index],
            reverse=True,
        )
        dominant = ranked[0]
        runner_up = ranked[1] if len(ranked) > 1 else ranked[0]
        margin = posterior_bps[dominant] - posterior_bps[runner_up]
        entropy = _entropy_bps(posterior_bps)
        confidence = min(
            10_000 - entropy,
            margin,
            certainty,
        )
        reasons = (
            "BAYESIAN_TRANSITION_PRIOR_APPLIED",
            "CURRENT_CAUSAL_EMISSION_APPLIED",
            (
                "CAUSAL_STATE_POSTERIOR_CONCENTRATED"
                if entropy <= 5_000
                else "CAUSAL_STATE_POSTERIOR_DIFFUSE"
            ),
        )
        results.append(
            FilteredCausalStateBelief(
                as_of=frame.as_of,
                evidence_count=len(results) + 1,
                posterior_bps=tuple(zip(states, posterior_bps, strict=True)),
                dominant_state=states[dominant],
                dominance_margin_bps=margin,
                entropy_bps=entropy,
                confidence_bps=confidence,
                reasons=reasons,
            )
        )

    return tuple(results)
