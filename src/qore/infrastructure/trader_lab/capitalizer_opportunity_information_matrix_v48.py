"""Opportunity Survival & Information Matrix for Capitalizer V48.

The matrix is diagnostic only. It quantifies how much two decision-time gates overlap
inside one frozen route population. It does not decide which gate should be removed and
does not read terminal outcomes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import log2

IDENTITY = "QORE_CAPITALIZER_V48_OPPORTUNITY_SURVIVAL_INFORMATION_MATRIX"


@dataclass(frozen=True, slots=True)
class V48GateObservation:
    observation_id: str
    route: str
    gates: Mapping[str, bool]

    def __post_init__(self) -> None:
        if not self.observation_id:
            raise ValueError("observation_id is required")
        if not self.route:
            raise ValueError("route is required")
        if not self.gates:
            raise ValueError("at least one decision-time gate is required")
        if any(not key or key != key.upper() for key in self.gates):
            raise ValueError("gate names must be non-empty uppercase")


@dataclass(frozen=True, slots=True)
class V48GatePairMetrics:
    route: str
    gate_a: str
    gate_b: str
    population: int
    a_true: int
    b_true: int
    both_true: int
    p_a: float
    p_b: float
    p_a_and_b: float
    p_b_given_a: float
    p_a_given_b: float
    jaccard: float
    mutual_information_bits: float

    def __post_init__(self) -> None:
        if self.population <= 0:
            raise ValueError("pair metrics require positive population")
        if self.gate_a == self.gate_b:
            raise ValueError("pair metrics require distinct gates")


def _safe_ratio(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def _binary_mutual_information(
    n11: int,
    n10: int,
    n01: int,
    n00: int,
) -> float:
    total = n11 + n10 + n01 + n00
    if total == 0:
        return 0.0

    p_a = {
        1: (n11 + n10) / total,
        0: (n01 + n00) / total,
    }
    p_b = {
        1: (n11 + n01) / total,
        0: (n10 + n00) / total,
    }
    joint = {
        (1, 1): n11 / total,
        (1, 0): n10 / total,
        (0, 1): n01 / total,
        (0, 0): n00 / total,
    }

    information = 0.0
    for (a_value, b_value), p_joint in joint.items():
        if p_joint == 0.0:
            continue
        denominator = p_a[a_value] * p_b[b_value]
        information += p_joint * log2(p_joint / denominator)
    return information


def pair_metrics(
    observations: Sequence[V48GateObservation],
    *,
    route: str,
    gate_a: str,
    gate_b: str,
) -> V48GatePairMetrics:
    """Measure overlap for two gates inside exactly one route.

    Cross-route pooling is deliberately forbidden because route alternatives are not
    interchangeable observations of one universal strategy pipeline.
    """

    if not route:
        raise ValueError("route is required")
    if gate_a == gate_b:
        raise ValueError("gate_a and gate_b must differ")

    rows = [row for row in observations if row.route == route]
    if not rows:
        raise ValueError(f"no observations for route {route}")

    missing = [
        row.observation_id
        for row in rows
        if gate_a not in row.gates or gate_b not in row.gates
    ]
    if missing:
        raise ValueError(f"missing gate values for observations: {missing[:5]}")

    n11 = sum(row.gates[gate_a] and row.gates[gate_b] for row in rows)
    n10 = sum(row.gates[gate_a] and not row.gates[gate_b] for row in rows)
    n01 = sum(not row.gates[gate_a] and row.gates[gate_b] for row in rows)
    n00 = len(rows) - n11 - n10 - n01

    a_true = n11 + n10
    b_true = n11 + n01
    union = a_true + b_true - n11

    return V48GatePairMetrics(
        route=route,
        gate_a=gate_a,
        gate_b=gate_b,
        population=len(rows),
        a_true=a_true,
        b_true=b_true,
        both_true=n11,
        p_a=_safe_ratio(a_true, len(rows)),
        p_b=_safe_ratio(b_true, len(rows)),
        p_a_and_b=_safe_ratio(n11, len(rows)),
        p_b_given_a=_safe_ratio(n11, a_true),
        p_a_given_b=_safe_ratio(n11, b_true),
        jaccard=_safe_ratio(n11, union),
        mutual_information_bits=_binary_mutual_information(n11, n10, n01, n00),
    )


@dataclass(frozen=True, slots=True)
class V48OpportunityInformationMatrix:
    identity: str
    route: str
    gate_names: tuple[str, ...]
    pairs: tuple[V48GatePairMetrics, ...]
    outcome_fields_used: bool = False
    fresh_holdout_used: bool = False
    automatic_gate_removal_allowed: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 information matrix identity is frozen")
        if len(self.gate_names) < 2:
            raise ValueError("matrix requires at least two gates")
        if self.outcome_fields_used or self.fresh_holdout_used:
            raise ValueError("information matrix must be pre-economic")
        if self.automatic_gate_removal_allowed:
            raise ValueError("matrix is diagnostic and cannot remove gates automatically")


def build_information_matrix(
    observations: Sequence[V48GateObservation],
    *,
    route: str,
    gate_names: Sequence[str],
) -> V48OpportunityInformationMatrix:
    unique = tuple(dict.fromkeys(gate_names))
    if len(unique) < 2:
        raise ValueError("at least two unique gates are required")

    pairs: list[V48GatePairMetrics] = []
    for index, gate_a in enumerate(unique):
        for gate_b in unique[index + 1 :]:
            pairs.append(
                pair_metrics(
                    observations,
                    route=route,
                    gate_a=gate_a,
                    gate_b=gate_b,
                )
            )

    return V48OpportunityInformationMatrix(
        identity=IDENTITY,
        route=route,
        gate_names=unique,
        pairs=tuple(pairs),
    )
