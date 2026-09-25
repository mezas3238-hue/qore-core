"""Sequence-aware causal hypothesis belief for Shared Core.

This module is a resident, authority-free belief accumulator. It does not
learn from trade outcomes and it does not own strategy, risk, sizing, stop,
target, order or execution authority.

Upstream research or runtime components may supply point-in-time hypothesis
likelihoods. Shared keeps a bounded causal history and accumulates evidence
for four mutually exclusive near-term hypotheses: TERMINAL, RECOVERY, TARGET,
and NO_EVENT.

The accumulator deliberately separates current evidence from belief state.
A single adverse snapshot cannot overwrite a mature favorable belief, and a
single favorable snapshot cannot erase persistent terminal evidence. Newer,
higher-integrity and lower-uncertainty frames receive more weight, while old
evidence decays deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class CausalBeliefDisposition(StrEnum):
    TERMINAL_DOMINANT = "TERMINAL_DOMINANT"
    FAVORABLE_DOMINANT = "FAVORABLE_DOMINANT"
    CONTESTED = "CONTESTED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class CausalHypothesisEvidence:
    as_of: datetime
    terminal_bps: int
    recovery_bps: int
    target_bps: int
    no_event_bps: int
    uncertainty_bps: int
    data_integrity_bps: int = 10_000

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        for name in (
            "terminal_bps",
            "recovery_bps",
            "target_bps",
            "no_event_bps",
            "uncertainty_bps",
            "data_integrity_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        total = (
            self.terminal_bps
            + self.recovery_bps
            + self.target_bps
            + self.no_event_bps
        )
        if total <= 0:
            raise ValueError("hypothesis evidence must contain positive mass")


@dataclass(frozen=True, slots=True)
class CausalHypothesisBelief:
    as_of: datetime
    evidence_count: int
    terminal_bps: int
    recovery_bps: int
    target_bps: int
    no_event_bps: int
    favorable_bps: int
    confidence_bps: int
    disposition: CausalBeliefDisposition
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
        for name in (
            "terminal_bps",
            "recovery_bps",
            "target_bps",
            "no_event_bps",
            "favorable_bps",
            "confidence_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
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
            raise ValueError("causal belief cannot consume outcomes or carry authority")


def _normalize(values: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    total = sum(values)
    if total <= 0:
        return 2_500, 2_500, 2_500, 2_500
    scaled = [max(0, value) * 10_000 // total for value in values]
    remainder = 10_000 - sum(scaled)
    scaled[0] += remainder
    return tuple(scaled)  # type: ignore[return-value]


def accumulate_causal_hypotheses(
    frames: tuple[CausalHypothesisEvidence, ...],
    *,
    maximum_frames: int = 8,
    decay_bps: int = 7_500,
    minimum_frames: int = 2,
    dominance_margin_bps: int = 1_200,
) -> CausalHypothesisBelief:
    """Accumulate bounded causal evidence into a persistent belief state."""

    if not frames:
        raise ValueError("at least one evidence frame is required")
    if maximum_frames < 2:
        raise ValueError("maximum_frames must be at least 2")
    if minimum_frames < 1 or minimum_frames > maximum_frames:
        raise ValueError("minimum_frames must be within 1..maximum_frames")
    if not 0 <= decay_bps <= 10_000:
        raise ValueError("decay_bps must be within 0..10000")
    if not 0 <= dominance_margin_bps <= 10_000:
        raise ValueError("dominance_margin_bps must be within 0..10000")

    window = frames[-maximum_frames:]
    for left, right in zip(window, window[1:], strict=False):
        if right.as_of <= left.as_of:
            raise ValueError("evidence frames must be strictly increasing and causal")

    terminal = recovery = target = no_event = 0
    certainty_weight_total = 0
    recency = 10_000

    for frame in reversed(window):
        certainty = min(
            int(frame.data_integrity_bps),
            10_000 - int(frame.uncertainty_bps),
        )
        weight = recency * certainty // 10_000
        certainty_weight_total += weight
        terminal += frame.terminal_bps * weight
        recovery += frame.recovery_bps * weight
        target += frame.target_bps * weight
        no_event += frame.no_event_bps * weight
        recency = recency * decay_bps // 10_000

    normalized = _normalize((terminal, recovery, target, no_event))
    terminal_bps, recovery_bps, target_bps, no_event_bps = normalized
    favorable_bps = min(10_000, recovery_bps + target_bps)
    separation = abs(terminal_bps - favorable_bps)
    average_certainty = certainty_weight_total // len(window)
    confidence = min(10_000, separation, average_certainty)

    reasons: list[str] = []
    if len(window) < minimum_frames:
        disposition = CausalBeliefDisposition.INSUFFICIENT
        reasons.append("CAUSAL_HISTORY_INSUFFICIENT")
    elif terminal_bps - favorable_bps >= dominance_margin_bps:
        disposition = CausalBeliefDisposition.TERMINAL_DOMINANT
        reasons.extend(
            (
                "TERMINAL_HYPOTHESIS_DOMINANT",
                "SEQUENCE_EVIDENCE_PERSISTENT",
            )
        )
    elif favorable_bps - terminal_bps >= dominance_margin_bps:
        disposition = CausalBeliefDisposition.FAVORABLE_DOMINANT
        reasons.extend(
            (
                "RECOVERY_OR_TARGET_HYPOTHESIS_DOMINANT",
                "SEQUENCE_EVIDENCE_PERSISTENT",
            )
        )
    else:
        disposition = CausalBeliefDisposition.CONTESTED
        reasons.append("COMPETING_HYPOTHESES_NOT_SEPARATED")

    if no_event_bps >= max(terminal_bps, favorable_bps):
        reasons.append("NO_NEAR_TERM_EVENT_DOMINANT")
    if average_certainty < 5_000:
        reasons.append("SEQUENCE_CERTAINTY_LOW")

    return CausalHypothesisBelief(
        as_of=window[-1].as_of,
        evidence_count=len(window),
        terminal_bps=terminal_bps,
        recovery_bps=recovery_bps,
        target_bps=target_bps,
        no_event_bps=no_event_bps,
        favorable_bps=favorable_bps,
        confidence_bps=confidence,
        disposition=disposition,
        reasons=tuple(dict.fromkeys(reasons)),
    )
