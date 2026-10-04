"""Diagnostic sensors for CIBO Maximum Economic Capability.

Research-only observability. These sensors do not allocate capital, size,
authorize Risk, execute, mutate broker state, or select a productive path.
They quantify where causal economic capability is being lost so Trader Lab can
drive the loop: measure -> diagnose -> repair -> remeasure.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_engine_challenger_lab import (
    CiboAllocationChallengerResult,
)
from qore.infrastructure.cibo_full_economic_digital_twin import (
    CiboIdleCapitalClass,
    CiboObservedEconomicTwin,
    observed_twin_constraints,
)


class CiboDiagnosticGapKind(StrEnum):
    UTILITY_GAP = "UTILITY_GAP"
    VELOCITY_GAP = "VELOCITY_GAP"
    UNNECESSARY_IDLE_RISK = "UNNECESSARY_IDLE_RISK"
    UNNECESSARY_IDLE_MARGIN = "UNNECESSARY_IDLE_MARGIN"
    MISSED_POSITIVE_OPPORTUNITY = "MISSED_POSITIVE_OPPORTUNITY"
    PROVIDER_BLOCK = "PROVIDER_BLOCK"
    CONTEXT_VETO = "CONTEXT_VETO"
    CAPITAL_SOURCE_BLOCK = "CAPITAL_SOURCE_BLOCK"
    FUTURE_WAIT = "FUTURE_WAIT"
    COGNITIVE_UNDERACTUATION = "COGNITIVE_UNDERACTUATION"
    LEVERAGE_HEADROOM_GAP = "LEVERAGE_HEADROOM_GAP"


@dataclass(frozen=True, slots=True)
class CiboDiagnosticGap:
    kind: CiboDiagnosticGapKind
    magnitude: Decimal
    evidence_count: int
    explanation: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.magnitude, Decimal)
            or not self.magnitude.is_finite()
            or self.magnitude < 0
        ):
            raise CiboCapitalManagementError(
                "Diagnostic gap magnitude must be finite non-negative Decimal"
            )
        if (
            not isinstance(self.evidence_count, int)
            or isinstance(self.evidence_count, bool)
            or self.evidence_count < 0
        ):
            raise CiboCapitalManagementError(
                "Diagnostic evidence_count must be non-negative int"
            )
        if not self.explanation:
            raise CiboCapitalManagementError(
                "Diagnostic explanation is required"
            )


@dataclass(frozen=True, slots=True)
class CiboMaximumCapabilityDiagnosticReport:
    twin_id: str
    positive_eligible_opportunities: int
    blocked_provider_opportunities: int
    blocked_context_opportunities: int
    blocked_capital_source_opportunities: int
    future_waiting_opportunities: int
    stop_risk_headroom_utilization: Decimal
    margin_headroom_utilization: Decimal
    cognitive_constraint_count: int
    baseline_expected_utility_usd: Decimal
    native_expected_utility_usd: Decimal
    baseline_velocity_utility: Decimal
    native_velocity_utility: Decimal
    gaps: tuple[CiboDiagnosticGap, ...]
    worst_gap: CiboDiagnosticGap | None
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.twin_id:
            raise CiboCapitalManagementError(
                "Diagnostic report twin identity required"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "Diagnostic report cannot acquire productive authority"
            )
        for name in (
            "stop_risk_headroom_utilization",
            "margin_headroom_utilization",
        ):
            value = getattr(self, name)
            if value < 0 or value > 1:
                raise CiboCapitalManagementError(
                    f"Diagnostic {name} outside [0,1]"
                )
        if self.worst_gap is not None and self.worst_gap not in self.gaps:
            raise CiboCapitalManagementError(
                "Diagnostic worst_gap must belong to gaps"
            )


def _safe_utilization(used: Decimal, capacity: Decimal) -> Decimal:
    if capacity <= 0:
        return Decimal(0)
    return max(Decimal(0), min(Decimal(1), used / capacity))


def build_maximum_capability_diagnostics(
    *,
    twin: CiboObservedEconomicTwin,
    challenger: CiboAllocationChallengerResult,
) -> CiboMaximumCapabilityDiagnosticReport:
    """Measure causal economic gaps on one exact observed Twin snapshot."""

    if challenger.twin_id != twin.twin_id:
        raise CiboCapitalManagementError(
            "Diagnostic challenger/twin identity mismatch"
        )

    constraints = observed_twin_constraints(twin)
    eligible_positive = []
    provider_blocked = []
    context_blocked = []
    source_blocked = []
    future_waiting = []

    for item in twin.opportunities:
        net = (
            item.expected_net_value_usd
            - item.provider_cost_usd
            - item.uncertainty_penalty
        )
        if item.known_at <= twin.captured_at and item.expires_at > twin.captured_at:
            if not item.provider_viable:
                provider_blocked.append(item)
            if not item.context_allowed:
                context_blocked.append(item)
            if not item.capital_source_eligible:
                source_blocked.append(item)
            if item.earliest_action_at > twin.captured_at:
                future_waiting.append(item)
            if (
                item.earliest_action_at <= twin.captured_at
                and item.provider_viable
                and item.context_allowed
                and item.capital_source_eligible
                and net > 0
            ):
                eligible_positive.append(item)

    gaps: list[CiboDiagnosticGap] = []
    utility_gap = max(
        Decimal(0),
        challenger.native.total_expected_net_utility_usd
        - challenger.baseline.total_expected_net_utility_usd,
    )
    if utility_gap > 0:
        gaps.append(
            CiboDiagnosticGap(
                kind=CiboDiagnosticGapKind.UTILITY_GAP,
                magnitude=utility_gap,
                evidence_count=len(eligible_positive),
                explanation=(
                    "native engine exposes causal expected utility unavailable "
                    "to the current baseline path"
                ),
            )
        )

    velocity_gap = max(
        Decimal(0),
        challenger.native.velocity_utility
        - challenger.baseline.velocity_utility,
    )
    if velocity_gap > 0:
        gaps.append(
            CiboDiagnosticGap(
                kind=CiboDiagnosticGapKind.VELOCITY_GAP,
                magnitude=velocity_gap,
                evidence_count=len(eligible_positive),
                explanation=(
                    "native engine converts capital-minutes into causal utility "
                    "more efficiently than baseline"
                ),
            )
        )

    if twin.velocity.idle_classification is CiboIdleCapitalClass.UNNECESSARY_IDLE:
        if twin.velocity.waiting_stop_risk_usd > 0:
            gaps.append(
                CiboDiagnosticGap(
                    kind=CiboDiagnosticGapKind.UNNECESSARY_IDLE_RISK,
                    magnitude=twin.velocity.waiting_stop_risk_usd,
                    evidence_count=len(eligible_positive),
                    explanation=(
                        "released stop-risk capacity is waiting despite an "
                        "economically classified unnecessary-idle state"
                    ),
                )
            )
        if twin.velocity.waiting_margin_usd > 0:
            gaps.append(
                CiboDiagnosticGap(
                    kind=CiboDiagnosticGapKind.UNNECESSARY_IDLE_MARGIN,
                    magnitude=twin.velocity.waiting_margin_usd,
                    evidence_count=len(eligible_positive),
                    explanation=(
                        "released margin is waiting despite an economically "
                        "classified unnecessary-idle state"
                    ),
                )
            )

    selected_ids = {
        line.option_id
        for line in challenger.native_plan.lines
        if line.multiplier > 0
    }
    missed = [item for item in eligible_positive if item.option_id not in selected_ids]
    missed_utility = sum(
        (
            item.expected_net_value_usd
            - item.provider_cost_usd
            - item.uncertainty_penalty
            for item in missed
        ),
        Decimal(0),
    )
    if missed:
        gaps.append(
            CiboDiagnosticGap(
                kind=CiboDiagnosticGapKind.MISSED_POSITIVE_OPPORTUNITY,
                magnitude=max(Decimal(0), missed_utility),
                evidence_count=len(missed),
                explanation=(
                    "positive causal opportunities were eligible but not selected "
                    "by the native account-wide plan; inspect scarcity constraints"
                ),
            )
        )

    for kind, rows, explanation in (
        (
            CiboDiagnosticGapKind.PROVIDER_BLOCK,
            provider_blocked,
            "known opportunities are blocked by provider viability",
        ),
        (
            CiboDiagnosticGapKind.CONTEXT_VETO,
            context_blocked,
            "known opportunities are blocked by causal context",
        ),
        (
            CiboDiagnosticGapKind.CAPITAL_SOURCE_BLOCK,
            source_blocked,
            "known opportunities are blocked by capital-source eligibility",
        ),
        (
            CiboDiagnosticGapKind.FUTURE_WAIT,
            future_waiting,
            "known opportunities are not yet causally actionable",
        ),
    ):
        if rows:
            gaps.append(
                CiboDiagnosticGap(
                    kind=kind,
                    magnitude=Decimal(len(rows)),
                    evidence_count=len(rows),
                    explanation=explanation,
                )
            )

    cognitive_count = len(twin.cognitive_constraints)
    if cognitive_count == 0:
        gaps.append(
            CiboDiagnosticGap(
                kind=CiboDiagnosticGapKind.COGNITIVE_UNDERACTUATION,
                magnitude=Decimal(1),
                evidence_count=0,
                explanation=(
                    "Full Economic Twin carries no explicit cognitive economic "
                    "constraints on this epoch"
                ),
            )
        )

    risk_capacity = twin.capital_twin.total_stop_risk_capacity_usd
    margin_capacity = twin.capital_twin.total_margin_capacity_usd
    used_risk = risk_capacity - twin.capital_twin.stop_risk_headroom_usd
    used_margin = margin_capacity - twin.capital_twin.margin_headroom_usd
    risk_util = _safe_utilization(used_risk, risk_capacity)
    margin_util = _safe_utilization(used_margin, margin_capacity)

    if (
        eligible_positive
        and constraints["stop_risk_headroom_usd"] > 0
        and challenger.native.total_stop_risk_usd
        < constraints["stop_risk_headroom_usd"]
    ):
        unused = (
            constraints["stop_risk_headroom_usd"]
            - challenger.native.total_stop_risk_usd
        )
        gaps.append(
            CiboDiagnosticGap(
                kind=CiboDiagnosticGapKind.LEVERAGE_HEADROOM_GAP,
                magnitude=unused,
                evidence_count=len(eligible_positive),
                explanation=(
                    "causal positive opportunities coexist with unused risk "
                    "headroom; determine whether reserve/optionality or allocator "
                    "inefficiency explains the residual"
                ),
            )
        )

    ordered_gaps = tuple(
        sorted(
            gaps,
            key=lambda item: (
                -item.magnitude,
                item.kind.value,
            ),
        )
    )
    return CiboMaximumCapabilityDiagnosticReport(
        twin_id=twin.twin_id,
        positive_eligible_opportunities=len(eligible_positive),
        blocked_provider_opportunities=len(provider_blocked),
        blocked_context_opportunities=len(context_blocked),
        blocked_capital_source_opportunities=len(source_blocked),
        future_waiting_opportunities=len(future_waiting),
        stop_risk_headroom_utilization=risk_util,
        margin_headroom_utilization=margin_util,
        cognitive_constraint_count=cognitive_count,
        baseline_expected_utility_usd=(
            challenger.baseline.total_expected_net_utility_usd
        ),
        native_expected_utility_usd=(
            challenger.native.total_expected_net_utility_usd
        ),
        baseline_velocity_utility=challenger.baseline.velocity_utility,
        native_velocity_utility=challenger.native.velocity_utility,
        gaps=ordered_gaps,
        worst_gap=ordered_gaps[0] if ordered_gaps else None,
    )
