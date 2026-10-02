"""Generic A/B evidence contracts for CURRENT trader vs CORE STACK V2 shadow."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DecisionObservation:
    trader_id: str
    observation_id: str
    baseline_action: str
    v2_action: str
    baseline_fingerprint: str
    v2_fingerprint: str
    core_context_valid: bool
    end_to_end_latency_us: int

    def __post_init__(self) -> None:
        if self.end_to_end_latency_us < 0:
            raise ValueError("latency cannot be negative")


@dataclass(frozen=True, slots=True)
class DecisionABSummary:
    observations: int
    decision_deltas: int
    invalid_core_contexts: int
    wait_deltas: int
    abstain_deltas: int
    latency_p50_us: int
    latency_p95_us: int
    latency_p99_us: int


def _percentile(values: tuple[int, ...], percentile: int) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = ((len(ordered) - 1) * percentile + 99) // 100
    return ordered[min(index, len(ordered) - 1)]


def summarize_decision_ab(
    observations: tuple[DecisionObservation, ...],
) -> DecisionABSummary:
    latencies = tuple(item.end_to_end_latency_us for item in observations)
    return DecisionABSummary(
        observations=len(observations),
        decision_deltas=sum(
            item.baseline_action != item.v2_action for item in observations
        ),
        invalid_core_contexts=sum(
            not item.core_context_valid for item in observations
        ),
        wait_deltas=sum(
            (item.baseline_action == "WAIT") != (item.v2_action == "WAIT")
            for item in observations
        ),
        abstain_deltas=sum(
            (item.baseline_action == "ABSTAIN") != (item.v2_action == "ABSTAIN")
            for item in observations
        ),
        latency_p50_us=_percentile(latencies, 50),
        latency_p95_us=_percentile(latencies, 95),
        latency_p99_us=_percentile(latencies, 99),
    )
