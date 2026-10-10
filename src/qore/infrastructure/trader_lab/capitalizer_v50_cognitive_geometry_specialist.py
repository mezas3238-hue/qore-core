"""V50 cognitive geometry specialist for the H1 -> M15 -> M1 Scalper.

This specialist is called only after a source-complete V49 opportunity exists. It does not
invent setups. It attempts to repair the economic mismatch diagnosed in V49 by reasoning over
decision-time geometry:

- M15 protected swing = thesis invalidation;
- causal M1 pivot = execution invalidation candidate;
- recent M1 range = local breathing/noise reference;
- H1 target ladder = causal destinations already known at entry.

The specialist never widens a stop after entry and never selects a destination using future
outcomes. Candidate policies are DEVELOPMENT HYPOTHESES and are not promoted automatically.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_opportunity import (
    V50CognitiveOpportunitySnapshot,
)
from qore.infrastructure.trader_lab.capitalizer_v50_target_stop_intelligence import (
    V50H1TargetCandidate,
)

IDENTITY = "QORE_CAPITALIZER_V50_COGNITIVE_GEOMETRY_SPECIALIST"

MIN_EXECUTION_STOP_NOISE = Decimal("4")
MAX_EXECUTION_STOP_NOISE = Decimal("8")
MIN_FULL_TARGET_R = Decimal("1")
PREFERRED_RUNNER_R = Decimal("1.5")


class V50GeometryDecision(StrEnum):
    READY = "READY"
    WAIT_EXECUTION_STOP = "WAIT_EXECUTION_STOP"
    WAIT_STOP_BREATHING = "WAIT_STOP_BREATHING"
    WAIT_DESTINATION = "WAIT_DESTINATION"
    WAIT_ECONOMIC_ASYMMETRY = "WAIT_ECONOMIC_ASYMMETRY"


class V50StopMode(StrEnum):
    EXECUTION_M1 = "EXECUTION_M1"
    THESIS_M15 = "THESIS_M15"


@dataclass(frozen=True, slots=True)
class V50GeometryProposal:
    identity: str
    decision: V50GeometryDecision
    side: CapitalizerSide
    entry_price: Decimal
    stop_mode: V50StopMode | None
    stop_price: Decimal | None
    stop_risk_price: Decimal | None
    stop_to_noise_ratio: Decimal | None
    t1: V50H1TargetCandidate | None
    t1_reward_r: Decimal | None
    runner: V50H1TargetCandidate | None
    runner_reward_r: Decimal | None
    reasons: tuple[str, ...]
    full_exit_at_t1_required: bool = False
    post_entry_stop_widening_allowed: bool = False
    outcome_used: bool = False
    grants_entry_authority: bool = False
    grants_capital_authority: bool = False
    rule_promotion_allowed: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("unexpected V50 geometry specialist identity")
        ready = self.decision is V50GeometryDecision.READY
        payload = (
            self.stop_mode is not None
            and self.stop_price is not None
            and self.stop_risk_price is not None
            and self.stop_to_noise_ratio is not None
            and self.t1 is not None
            and self.t1_reward_r is not None
        )
        if ready != payload:
            raise ValueError("V50 geometry READY/payload mismatch")
        if self.post_entry_stop_widening_allowed:
            raise ValueError("V50 geometry cannot authorize post-entry widening")
        if self.outcome_used:
            raise ValueError("V50 geometry cannot use future outcome")
        if self.grants_entry_authority or self.grants_capital_authority:
            raise ValueError("V50 geometry is advisory only")
        if self.rule_promotion_allowed:
            raise ValueError("V50 geometry hypotheses cannot self-promote")
        if self.full_exit_at_t1_required:
            raise ValueError("V50 target ladder must not collapse back to mandatory T1 full exit")


def _side(snapshot: V50CognitiveOpportunitySnapshot) -> CapitalizerSide:
    return (
        CapitalizerSide.LONG
        if snapshot.source_opportunity.h1_state_direction == "BULLISH"
        else CapitalizerSide.SHORT
    )


def _reward_r(
    *,
    entry: Decimal,
    target: Decimal,
    stop_risk: Decimal,
) -> Decimal:
    if stop_risk <= 0:
        raise ValueError("V50 geometry requires positive stop risk")
    return abs(target - entry) / stop_risk


def _targets_for_stop(
    snapshot: V50CognitiveOpportunitySnapshot,
    *,
    stop_risk: Decimal,
) -> tuple[tuple[V50H1TargetCandidate, Decimal], ...]:
    return tuple(
        (candidate, _reward_r(
            entry=snapshot.target_ladder.entry_price,
            target=candidate.price,
            stop_risk=stop_risk,
        ))
        for candidate in snapshot.target_ladder.candidates
    )


def propose_v50_geometry(
    snapshot: V50CognitiveOpportunitySnapshot,
) -> V50GeometryProposal:
    """Propose causal execution geometry without authorizing the trade."""

    side = _side(snapshot)
    entry = Decimal(snapshot.source_opportunity.decision_reference_price)
    dual = snapshot.dual_invalidation

    if (
        not dual.execution_anchor_available
        or dual.execution_stop_price is None
        or dual.execution_risk_price is None
    ):
        return V50GeometryProposal(
            identity=IDENTITY,
            decision=V50GeometryDecision.WAIT_EXECUTION_STOP,
            side=side,
            entry_price=entry,
            stop_mode=None,
            stop_price=None,
            stop_risk_price=None,
            stop_to_noise_ratio=None,
            t1=None,
            t1_reward_r=None,
            runner=None,
            runner_reward_r=None,
            reasons=("M1_EXECUTION_INVALIDATION_UNAVAILABLE",),
        )

    # The snapshot distances are already expressed in ticks. Convert the execution risk to
    # the same local-noise scale using its ratio to thesis risk.
    if (
        dual.execution_vs_thesis_ratio is None
        or snapshot.thesis_stop_distance_ticks <= 0
        or snapshot.recent_m1_range_ticks <= 0
    ):
        raise ValueError("V50 geometry requires complete stop/noise state")
    execution_ticks = (
        snapshot.thesis_stop_distance_ticks
        * dual.execution_vs_thesis_ratio
    )
    execution_noise = execution_ticks / snapshot.recent_m1_range_ticks

    if execution_noise < MIN_EXECUTION_STOP_NOISE:
        return V50GeometryProposal(
            identity=IDENTITY,
            decision=V50GeometryDecision.WAIT_STOP_BREATHING,
            side=side,
            entry_price=entry,
            stop_mode=None,
            stop_price=None,
            stop_risk_price=None,
            stop_to_noise_ratio=execution_noise,
            t1=None,
            t1_reward_r=None,
            runner=None,
            runner_reward_r=None,
            reasons=("M1_EXECUTION_STOP_INSIDE_LOCAL_NOISE",),
        )

    if execution_noise > MAX_EXECUTION_STOP_NOISE:
        # A wide M1 execution stop is not automatically replaced with M15. Ask for a new
        # execution structure rather than paying thesis-scale risk mechanically.
        return V50GeometryProposal(
            identity=IDENTITY,
            decision=V50GeometryDecision.WAIT_STOP_BREATHING,
            side=side,
            entry_price=entry,
            stop_mode=None,
            stop_price=None,
            stop_risk_price=None,
            stop_to_noise_ratio=execution_noise,
            t1=None,
            t1_reward_r=None,
            runner=None,
            runner_reward_r=None,
            reasons=("M1_EXECUTION_STOP_TOO_WIDE_FOR_SCALP",),
        )

    if not snapshot.target_ladder.candidates:
        return V50GeometryProposal(
            identity=IDENTITY,
            decision=V50GeometryDecision.WAIT_DESTINATION,
            side=side,
            entry_price=entry,
            stop_mode=None,
            stop_price=None,
            stop_risk_price=None,
            stop_to_noise_ratio=execution_noise,
            t1=None,
            t1_reward_r=None,
            runner=None,
            runner_reward_r=None,
            reasons=("NO_CAUSAL_H1_DESTINATION_LADDER",),
        )

    target_rows = _targets_for_stop(
        snapshot,
        stop_risk=dual.execution_risk_price,
    )
    eligible = tuple(
        row for row in target_rows if row[1] >= MIN_FULL_TARGET_R
    )
    if not eligible:
        return V50GeometryProposal(
            identity=IDENTITY,
            decision=V50GeometryDecision.WAIT_ECONOMIC_ASYMMETRY,
            side=side,
            entry_price=entry,
            stop_mode=None,
            stop_price=None,
            stop_risk_price=None,
            stop_to_noise_ratio=execution_noise,
            t1=None,
            t1_reward_r=None,
            runner=None,
            runner_reward_r=None,
            reasons=("NO_H1_DESTINATION_AT_OR_ABOVE_1R_WITH_EXECUTION_STOP",),
        )

    t1, t1_r = eligible[0]
    runner_row = next(
        (row for row in eligible[1:] if row[1] >= PREFERRED_RUNNER_R),
        None,
    )
    runner = None if runner_row is None else runner_row[0]
    runner_r = None if runner_row is None else runner_row[1]
    return V50GeometryProposal(
        identity=IDENTITY,
        decision=V50GeometryDecision.READY,
        side=side,
        entry_price=entry,
        stop_mode=V50StopMode.EXECUTION_M1,
        stop_price=dual.execution_stop_price,
        stop_risk_price=dual.execution_risk_price,
        stop_to_noise_ratio=execution_noise,
        t1=t1,
        t1_reward_r=t1_r,
        runner=runner,
        runner_reward_r=runner_r,
        reasons=(
            "M1_EXECUTION_INVALIDATION_OUTSIDE_LOCAL_NOISE",
            "H1_DESTINATION_AT_LEAST_1R",
            (
                "RUNNER_DESTINATION_AVAILABLE"
                if runner is not None
                else "NO_RUNNER_AT_PREFERRED_R"
            ),
        ),
    )
