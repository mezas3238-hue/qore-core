"""Architect B5 relational science for empirical Shared world relations.

Cognition-only, pre-outcome and fail-closed.  B5 may observe relationship
lifecycle, temporal precedence and structural divergence, but it cannot infer
causation or acquire any execution/risk/capital authority.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from statistics import fmean

from qore.infrastructure.core_stack_v2.global_market_relational_graph import (
    RelationDirection,
    RelationEpistemicGrade,
)
from qore.infrastructure.core_stack_v2.global_temporal_comparability import (
    ComparabilityConfidence,
    RelationalComparabilityState,
)


class B5RelationalScienceError(ValueError):
    """B5 relation-science invariant failed closed."""


class RelationshipLifecycleState(StrEnum):
    BIRTH = "BIRTH"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    DEAD = "DEAD"


@dataclass(frozen=True, slots=True)
class RelationalSample:
    observed_at: datetime
    source_value_bps: int
    target_value_bps: int
    comparability_state: RelationalComparabilityState
    comparability_confidence: ComparabilityConfidence
    source_freshness_ms: int
    target_freshness_ms: int
    provenance_refs: tuple[str, ...]
    outcome_used: bool = False
    future_market_used: bool = False

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise B5RelationalScienceError("observed_at must be timezone-aware")
        if self.source_freshness_ms < 0 or self.target_freshness_ms < 0:
            raise B5RelationalScienceError("freshness cannot be negative")
        if (
            not self.provenance_refs
            or self.provenance_refs != tuple(sorted(set(self.provenance_refs)))
        ):
            raise B5RelationalScienceError(
                "sample provenance must be non-empty and canonical"
            )
        if self.outcome_used or self.future_market_used:
            raise B5RelationalScienceError(
                "relational science cannot consume outcomes or future market data"
            )


@dataclass(frozen=True, slots=True)
class RelationshipLifecycleTransition:
    observed_at: datetime
    state: RelationshipLifecycleState
    strength_bps: int | None
    sample_count: int
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise B5RelationalScienceError("lifecycle timestamp must be aware")
        if self.strength_bps is not None and not 0 <= self.strength_bps <= 10_000:
            raise B5RelationalScienceError("strength_bps must be within 0..10000")
        if self.sample_count < 0:
            raise B5RelationalScienceError("sample_count cannot be negative")
        if (
            not self.reason_codes
            or self.reason_codes != tuple(sorted(set(self.reason_codes)))
        ):
            raise B5RelationalScienceError(
                "reason codes must be non-empty and canonical"
            )


@dataclass(frozen=True, slots=True)
class RelationshipLifecycleReceipt:
    relation_id: str
    window_size: int
    transitions: tuple[RelationshipLifecycleTransition, ...]
    current_state: RelationshipLifecycleState
    outcome_used: bool = False
    future_market_used: bool = False
    productive_authority: bool = False

    def fingerprint(self) -> str:
        return _sha256(
            {
                "relation_id": self.relation_id,
                "window_size": self.window_size,
                "transitions": [
                    {
                        **asdict(item),
                        "observed_at": item.observed_at.astimezone(UTC).isoformat(),
                        "state": item.state.value,
                    }
                    for item in self.transitions
                ],
                "current_state": self.current_state.value,
                "outcome_used": self.outcome_used,
                "future_market_used": self.future_market_used,
                "productive_authority": self.productive_authority,
            }
        )


@dataclass(frozen=True, slots=True)
class LeadLagObservation:
    relation_id: str
    evaluated_at: datetime
    direction: RelationDirection
    lag_steps: int
    lag_ms: int
    pearson_r_bps: int
    sample_count: int
    epistemic_grade: RelationEpistemicGrade
    temporal_precedence_observed: bool
    causation_claimed: bool = False
    outcome_used: bool = False
    future_market_used: bool = False

    def __post_init__(self) -> None:
        if self.evaluated_at.tzinfo is None or self.evaluated_at.utcoffset() is None:
            raise B5RelationalScienceError("lead-lag timestamp must be aware")
        if self.lag_steps < 0 or self.lag_ms < 0:
            raise B5RelationalScienceError("lead-lag cannot be negative")
        if not -10_000 <= self.pearson_r_bps <= 10_000:
            raise B5RelationalScienceError("pearson_r_bps outside range")
        if self.sample_count < 2:
            raise B5RelationalScienceError("lead-lag requires at least two pairs")
        if self.epistemic_grade not in {
            RelationEpistemicGrade.OBSERVED,
            RelationEpistemicGrade.ASSOCIATION,
            RelationEpistemicGrade.TEMPORAL_DEPENDENCY,
        }:
            raise B5RelationalScienceError(
                "lead-lag observability cannot self-promote to causal evidence"
            )
        if self.causation_claimed or self.outcome_used or self.future_market_used:
            raise B5RelationalScienceError("forbidden lead-lag claim")


@dataclass(frozen=True, slots=True)
class StructuralDivergenceObservation:
    relation_id: str
    evaluated_at: datetime
    window_size: int
    source_delta_bps: int
    target_delta_bps: int
    divergence_bps: int
    divergent: bool
    comparable_sample_count: int
    causation_claimed: bool = False
    outcome_used: bool = False
    future_market_used: bool = False

    def __post_init__(self) -> None:
        if self.evaluated_at.tzinfo is None or self.evaluated_at.utcoffset() is None:
            raise B5RelationalScienceError("divergence timestamp must be aware")
        if self.window_size < 2:
            raise B5RelationalScienceError("divergence window must be >= 2")
        if not 0 <= self.divergence_bps <= 10_000:
            raise B5RelationalScienceError("divergence_bps outside range")
        if self.comparable_sample_count != self.window_size:
            raise B5RelationalScienceError(
                "structural divergence requires a fully comparable window"
            )
        if self.causation_claimed or self.outcome_used or self.future_market_used:
            raise B5RelationalScienceError("forbidden divergence evidence")


def _sha256(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _validate_order(samples: tuple[RelationalSample, ...]) -> None:
    timestamps = tuple(item.observed_at for item in samples)
    if timestamps != tuple(sorted(timestamps)) or len(timestamps) != len(set(timestamps)):
        raise B5RelationalScienceError(
            "relational samples must have unique chronological timestamps"
        )


def _validate_step_geometry(
    samples: tuple[RelationalSample, ...],
    step_ms: int,
) -> None:
    if step_ms <= 0:
        raise B5RelationalScienceError("step_ms must be positive")
    expected = step_ms / 1000
    for left, right in zip(samples, samples[1:], strict=False):
        observed = (right.observed_at - left.observed_at).total_seconds()
        if observed != expected:
            raise B5RelationalScienceError(
                "lead-lag requires exact uniform predeclared cadence"
            )


def _fully_comparable(
    sample: RelationalSample,
    *,
    max_freshness_ms: int | None = None,
) -> bool:
    if (
        sample.comparability_state is not RelationalComparabilityState.COMPARABLE
        or sample.comparability_confidence is not ComparabilityConfidence.HIGH
    ):
        return False
    return max_freshness_ms is None or max(
        sample.source_freshness_ms,
        sample.target_freshness_ms,
    ) <= max_freshness_ms


def _pearson_bps(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    if len(left) != len(right) or len(left) < 2:
        raise B5RelationalScienceError("pearson requires equal paired samples")
    left_mean = fmean(left)
    right_mean = fmean(right)
    left_centered = tuple(value - left_mean for value in left)
    right_centered = tuple(value - right_mean for value in right)
    numerator = sum(a * b for a, b in zip(left_centered, right_centered, strict=True))
    left_sq = sum(value * value for value in left_centered)
    right_sq = sum(value * value for value in right_centered)
    denominator = math.sqrt(left_sq * right_sq)
    if denominator == 0:
        return 0
    return int(round(max(-1.0, min(1.0, numerator / denominator)) * 10_000))


def _changes(values: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(right - left for left, right in zip(values, values[1:], strict=False))


def populate_relationship_lifecycle(
    *,
    relation_id: str,
    samples: tuple[RelationalSample, ...],
    window_size: int = 5,
    active_threshold_bps: int = 6_000,
    degraded_threshold_bps: int = 3_000,
    dead_after_stale_windows: int = 2,
    max_freshness_ms: int = 300_000,
) -> RelationshipLifecycleReceipt:
    """Populate BIRTH/ACTIVE/DEGRADED/STALE/DEAD without hindsight rewrite."""

    if not relation_id.strip():
        raise B5RelationalScienceError("relation_id required")
    if window_size < 3:
        raise B5RelationalScienceError("window_size must be >= 3")
    if not 0 <= degraded_threshold_bps < active_threshold_bps <= 10_000:
        raise B5RelationalScienceError("invalid lifecycle thresholds")
    if dead_after_stale_windows < 1 or max_freshness_ms < 0:
        raise B5RelationalScienceError("invalid lifecycle freshness/death policy")
    if len(samples) < window_size:
        raise B5RelationalScienceError("insufficient lifecycle population")
    _validate_order(samples)

    transitions: list[RelationshipLifecycleTransition] = []
    stale_windows = 0
    ever_born = False
    last_state: RelationshipLifecycleState | None = None

    for end in range(window_size, len(samples) + 1):
        window = samples[end - window_size : end]
        at = window[-1].observed_at
        if not all(
            _fully_comparable(item, max_freshness_ms=max_freshness_ms)
            for item in window
        ):
            stale_windows += 1
            state = (
                RelationshipLifecycleState.DEAD
                if ever_born and stale_windows >= dead_after_stale_windows
                else RelationshipLifecycleState.STALE
            )
            strength = None
            reasons = ("COMPARABILITY_OR_FRESHNESS_LOST",)
        else:
            source_changes = _changes(tuple(item.source_value_bps for item in window))
            target_changes = _changes(tuple(item.target_value_bps for item in window))
            strength = abs(_pearson_bps(source_changes, target_changes))
            if strength >= active_threshold_bps:
                stale_windows = 0
                if not ever_born:
                    ever_born = True
                    state = RelationshipLifecycleState.BIRTH
                    reasons = ("RELATION_FIRST_OBSERVED",)
                else:
                    state = RelationshipLifecycleState.ACTIVE
                    reasons = ("RELATION_ACTIVE",)
            elif strength >= degraded_threshold_bps:
                stale_windows = 0
                if not ever_born:
                    ever_born = True
                    state = RelationshipLifecycleState.BIRTH
                    reasons = ("RELATION_FIRST_OBSERVED_DEGRADED_STRENGTH",)
                else:
                    state = RelationshipLifecycleState.DEGRADED
                    reasons = ("RELATION_STRENGTH_DEGRADED",)
            else:
                stale_windows += 1
                state = (
                    RelationshipLifecycleState.DEAD
                    if ever_born and stale_windows >= dead_after_stale_windows
                    else RelationshipLifecycleState.STALE
                )
                reasons = ("RELATION_STRENGTH_BELOW_FLOOR",)

        if state is not last_state:
            transitions.append(
                RelationshipLifecycleTransition(
                    observed_at=at,
                    state=state,
                    strength_bps=strength,
                    sample_count=window_size,
                    reason_codes=tuple(sorted(reasons)),
                )
            )
            last_state = state

    assert last_state is not None
    return RelationshipLifecycleReceipt(
        relation_id=relation_id,
        window_size=window_size,
        transitions=tuple(transitions),
        current_state=last_state,
    )


def observe_lead_lag(
    *,
    relation_id: str,
    samples: tuple[RelationalSample, ...],
    max_lag_steps: int = 4,
    step_ms: int = 60_000,
    minimum_abs_r_bps: int = 3_000,
) -> LeadLagObservation:
    """Observe precedence on changes; never convert it into a causal claim."""

    if not relation_id.strip():
        raise B5RelationalScienceError("relation_id required")
    if len(samples) < max(7, max_lag_steps + 4):
        raise B5RelationalScienceError("insufficient lead-lag population")
    if max_lag_steps < 1:
        raise B5RelationalScienceError("invalid lead-lag search geometry")
    if not 0 <= minimum_abs_r_bps <= 10_000:
        raise B5RelationalScienceError("invalid lead-lag threshold")
    _validate_order(samples)
    _validate_step_geometry(samples, step_ms)
    if not all(_fully_comparable(item) for item in samples):
        raise B5RelationalScienceError(
            "lead-lag requires fully comparable HIGH-confidence samples"
        )

    source = _changes(tuple(item.source_value_bps for item in samples))
    target = _changes(tuple(item.target_value_bps for item in samples))
    candidates: list[tuple[int, int, RelationDirection, int]] = []

    zero_corr = _pearson_bps(source, target)
    candidates.append((abs(zero_corr), 0, RelationDirection.UNRESOLVED, zero_corr))
    for lag in range(1, max_lag_steps + 1):
        if len(source) - lag < 2:
            break
        source_leads = _pearson_bps(source[:-lag], target[lag:])
        target_leads = _pearson_bps(target[:-lag], source[lag:])
        candidates.extend(
            (
                (
                    abs(source_leads),
                    lag,
                    RelationDirection.SOURCE_TO_TARGET,
                    source_leads,
                ),
                (
                    abs(target_leads),
                    lag,
                    RelationDirection.TARGET_TO_SOURCE,
                    target_leads,
                ),
            )
        )

    best = max(candidates, key=lambda item: (item[0], -item[1]))
    _, lag_steps, direction, correlation = best
    precedence = lag_steps > 0 and abs(correlation) >= minimum_abs_r_bps
    if not precedence:
        direction = RelationDirection.UNRESOLVED
        lag_steps = 0
        lag_ms = 0
        grade = RelationEpistemicGrade.ASSOCIATION
        sample_count = len(source)
    else:
        lag_ms = lag_steps * step_ms
        grade = RelationEpistemicGrade.TEMPORAL_DEPENDENCY
        sample_count = len(source) - lag_steps

    return LeadLagObservation(
        relation_id=relation_id,
        evaluated_at=samples[-1].observed_at,
        direction=direction,
        lag_steps=lag_steps,
        lag_ms=lag_ms,
        pearson_r_bps=correlation,
        sample_count=sample_count,
        epistemic_grade=grade,
        temporal_precedence_observed=precedence,
    )


def observe_structural_divergence(
    *,
    relation_id: str,
    samples: tuple[RelationalSample, ...],
    window_size: int = 5,
    minimum_leg_move_bps: int = 100,
) -> StructuralDivergenceObservation:
    """Measure opposing structural movement on a fully comparable causal window."""

    if not relation_id.strip():
        raise B5RelationalScienceError("relation_id required")
    if window_size < 2 or len(samples) < window_size:
        raise B5RelationalScienceError("insufficient divergence population")
    if minimum_leg_move_bps < 0:
        raise B5RelationalScienceError("minimum_leg_move_bps cannot be negative")
    _validate_order(samples)
    window = samples[-window_size:]
    if not all(_fully_comparable(item) for item in window):
        raise B5RelationalScienceError(
            "structural divergence requires fully comparable HIGH-confidence samples"
        )

    source_delta = window[-1].source_value_bps - window[0].source_value_bps
    target_delta = window[-1].target_value_bps - window[0].target_value_bps
    opposing = source_delta * target_delta < 0
    material = (
        abs(source_delta) >= minimum_leg_move_bps
        and abs(target_delta) >= minimum_leg_move_bps
    )
    divergent = opposing and material
    divergence = min(abs(source_delta), abs(target_delta)) if divergent else 0

    return StructuralDivergenceObservation(
        relation_id=relation_id,
        evaluated_at=window[-1].observed_at,
        window_size=window_size,
        source_delta_bps=source_delta,
        target_delta_bps=target_delta,
        divergence_bps=min(10_000, divergence),
        divergent=divergent,
        comparable_sample_count=window_size,
    )
