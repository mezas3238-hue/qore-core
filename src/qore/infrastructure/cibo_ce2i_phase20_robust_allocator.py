"""Phase 20H-A robust constrained allocator candidate.

This candidate composes already-certified CE2I contracts without fitting a
performance policy to Phase-19J validation:

mission/regime gate
-> optionality/reserve envelope
-> deployable risk/margin headroom
-> T09/T18 causal opportunity competition
-> independent QORE Risk remains downstream

The candidate never receives realized trade outcomes, future labels or broker
mutation authority. It is a research contract candidate only; it is not policy,
holdout, DEMO, LIVE or real-capital certified.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_account_capital_mission import (
    CiboCapitalMissionPolicy,
    eligible_ce2i_tool_codes_for_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_opportunity_competition import (
    CapitalOpportunityCandidate,
    OpportunityAllocationBudget,
    OpportunityAllocationDecision,
    allocate_competing_opportunities,
)
from qore.infrastructure.cibo_ce2i_optionality import (
    KnownCapitalOption,
    plan_capital_optionality,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboRegimePosture,
    CiboRegimeToolSelection,
)


class Phase20AllocatorDisposition(StrEnum):
    ALLOCATE = "ALLOCATE"
    PRESERVE_CAPACITY = "PRESERVE_CAPACITY"
    NO_ELIGIBLE_ALLOCATION = "NO_ELIGIBLE_ALLOCATION"


@dataclass(frozen=True, slots=True)
class Phase20RobustAllocatorDecision:
    candidate_id: str
    disposition: Phase20AllocatorDisposition
    regime_posture: CiboRegimePosture
    applied_tools: tuple[str, ...]
    reserve_stop_risk_usd: Decimal
    reserve_margin_usd: Decimal
    deployable_stop_risk_usd: Decimal
    deployable_margin_usd: Decimal
    reserved_for_opportunity_ids: tuple[str, ...]
    allocation: OpportunityAllocationDecision | None
    reason: str
    outcome_aware: bool = False
    validation_tuned: bool = False
    phase19j_burned_validation_reused: bool = False
    policy_certified: bool = False
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False
    demo_execution_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    merge_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.reason:
            raise CiboCapitalManagementError(
                "Phase20H allocator identity/reason is required"
            )
        if type(self.disposition) is not Phase20AllocatorDisposition:
            raise CiboCapitalManagementError(
                "Phase20H disposition must use canonical enum"
            )
        if type(self.regime_posture) is not CiboRegimePosture:
            raise CiboCapitalManagementError(
                "Phase20H regime posture must use canonical enum"
            )
        for name in (
            "reserve_stop_risk_usd",
            "reserve_margin_usd",
            "deployable_stop_risk_usd",
            "deployable_margin_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20H {name} must be finite non-negative Decimal"
                )
        if (
            self.outcome_aware
            or self.validation_tuned
            or self.phase19j_burned_validation_reused
            or self.policy_certified
            or self.allocation_authority
            or self.risk_authority
            or self.execution_authority
            or self.demo_execution_authorized
            or self.live_authorized
            or self.real_capital_authorized
            or self.merge_authorized
        ):
            raise CiboCapitalManagementError(
                "Phase20H allocator governance drift"
            )
        if (
            self.disposition is Phase20AllocatorDisposition.ALLOCATE
            and (
                self.allocation is None
                or not self.allocation.selected_signal_fingerprints
            )
        ):
            raise CiboCapitalManagementError(
                "Phase20H ALLOCATE requires selected opportunities"
            )
        if self.allocation is not None:
            if (
                self.allocation.used_stop_risk_usd
                > self.deployable_stop_risk_usd
                or self.allocation.used_margin_usd
                > self.deployable_margin_usd
            ):
                raise CiboCapitalManagementError(
                    "Phase20H allocation exceeds deployable capacity"
                )


def _validate_headroom(value: Decimal, *, name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value < 0
    ):
        raise CiboCapitalManagementError(
            f"Phase20H {name} must be finite non-negative Decimal"
        )


def _empty_decision() -> OpportunityAllocationDecision:
    return OpportunityAllocationDecision(
        rows=(),
        selected_signal_fingerprints=(),
        used_stop_risk_usd=Decimal(0),
        used_margin_usd=Decimal(0),
        concentration_used_by_group=(),
    )


def propose_phase20h_robust_allocation(
    *,
    mission: CiboCapitalMissionPolicy,
    regime: CiboRegimeToolSelection,
    hard_risk_headroom_usd: Decimal,
    margin_headroom_usd: Decimal,
    concentration_limit_by_group: tuple[tuple[str, Decimal], ...],
    candidates: tuple[CapitalOpportunityCandidate, ...],
    known_options: tuple[KnownCapitalOption, ...] = (),
) -> Phase20RobustAllocatorDecision:
    """Compose causal CE2I constraints without using post-trade outcomes."""

    if not isinstance(mission, CiboCapitalMissionPolicy):
        raise CiboCapitalManagementError(
            "Phase20H mission must be CiboCapitalMissionPolicy"
        )
    if not isinstance(regime, CiboRegimeToolSelection):
        raise CiboCapitalManagementError(
            "Phase20H regime must be CiboRegimeToolSelection"
        )
    _validate_headroom(
        hard_risk_headroom_usd,
        name="hard_risk_headroom_usd",
    )
    _validate_headroom(
        margin_headroom_usd,
        name="margin_headroom_usd",
    )

    mission_tools = set(eligible_ce2i_tool_codes_for_mission(mission))
    enabled = set(regime.enabled_tools)
    if not enabled.issubset(mission_tools):
        raise CiboCapitalManagementError(
            "Phase20H regime surface exceeds account mission"
        )

    # HALT is an architectural hard stop. Do not invoke a blocked research tool
    # merely to manufacture a reserve decision: preserve the whole envelope.
    if regime.posture is CiboRegimePosture.HALT_NEW_CAPITAL:
        return Phase20RobustAllocatorDecision(
            candidate_id="PHASE20H_ROBUST_CONSTRAINED_ALLOCATOR_V1",
            disposition=Phase20AllocatorDisposition.PRESERVE_CAPACITY,
            regime_posture=regime.posture,
            applied_tools=(),
            reserve_stop_risk_usd=hard_risk_headroom_usd,
            reserve_margin_usd=margin_headroom_usd,
            deployable_stop_risk_usd=Decimal(0),
            deployable_margin_usd=Decimal(0),
            reserved_for_opportunity_ids=tuple(
                item.opportunity_id for item in known_options
            ),
            allocation=None,
            reason="HALT_NEW_CAPITAL preserves the complete capital envelope",
        )

    applied: list[str] = []
    if "T15" in enabled:
        optionality = plan_capital_optionality(
            mission=mission,
            regime=regime,
            hard_risk_headroom_usd=hard_risk_headroom_usd,
            margin_headroom_usd=margin_headroom_usd,
            known_options=known_options,
        )
        reserve_risk = optionality.reserve_stop_risk_usd
        reserve_margin = optionality.reserve_margin_usd
        deployable_risk = optionality.deployable_stop_risk_usd
        deployable_margin = optionality.deployable_margin_usd
        reserved_ids = optionality.reserved_for_opportunity_ids
        applied.append("T15")
        if (
            regime.posture is CiboRegimePosture.RECOVERY
            and "T13" in enabled
        ):
            applied.append("T13")
    elif (
        mission.preserve_optionality_priority
        or regime.posture
        in {CiboRegimePosture.DEFENSIVE, CiboRegimePosture.RECOVERY}
    ):
        # Required preservation tooling is unavailable under this mission;
        # fail conservative rather than silently spending its capacity.
        return Phase20RobustAllocatorDecision(
            candidate_id="PHASE20H_ROBUST_CONSTRAINED_ALLOCATOR_V1",
            disposition=Phase20AllocatorDisposition.PRESERVE_CAPACITY,
            regime_posture=regime.posture,
            applied_tools=(),
            reserve_stop_risk_usd=hard_risk_headroom_usd,
            reserve_margin_usd=margin_headroom_usd,
            deployable_stop_risk_usd=Decimal(0),
            deployable_margin_usd=Decimal(0),
            reserved_for_opportunity_ids=tuple(
                item.opportunity_id for item in known_options
            ),
            allocation=None,
            reason=(
                "required optionality protection is not executable under "
                "the current mission/regime"
            ),
        )
    else:
        reserve_risk = Decimal(0)
        reserve_margin = Decimal(0)
        deployable_risk = hard_risk_headroom_usd
        deployable_margin = margin_headroom_usd
        reserved_ids = ()

    competition_enabled = (
        mission.allow_cross_trader_competition
        and {"T09", "T18"}.issubset(enabled)
    )
    single_candidate_direct = (
        len(candidates) == 1
        and regime.posture
        in {CiboRegimePosture.STABLE, CiboRegimePosture.WATCH}
    )
    if (
        deployable_risk <= 0
        or deployable_margin <= 0
        or not candidates
        or (
            len(candidates) > 1
            and not competition_enabled
        )
        or (
            len(candidates) == 1
            and not competition_enabled
            and not single_candidate_direct
        )
    ):
        disposition = (
            Phase20AllocatorDisposition.PRESERVE_CAPACITY
            if deployable_risk <= 0 or deployable_margin <= 0
            else Phase20AllocatorDisposition.NO_ELIGIBLE_ALLOCATION
        )
        return Phase20RobustAllocatorDecision(
            candidate_id="PHASE20H_ROBUST_CONSTRAINED_ALLOCATOR_V1",
            disposition=disposition,
            regime_posture=regime.posture,
            applied_tools=tuple(applied),
            reserve_stop_risk_usd=reserve_risk,
            reserve_margin_usd=reserve_margin,
            deployable_stop_risk_usd=deployable_risk,
            deployable_margin_usd=deployable_margin,
            reserved_for_opportunity_ids=reserved_ids,
            allocation=None,
            reason=(
                "allocation is blocked by capital, candidate availability, "
                "or required multi-candidate competition tooling"
            ),
        )

    budget = OpportunityAllocationBudget(
        stop_risk_headroom_usd=deployable_risk,
        margin_headroom_usd=deployable_margin,
        concentration_limit_by_group=concentration_limit_by_group,
    )
    allocation = allocate_competing_opportunities(candidates, budget)
    if len(candidates) > 1:
        applied.extend(("T09", "T18"))
    disposition = (
        Phase20AllocatorDisposition.ALLOCATE
        if allocation.selected_signal_fingerprints
        else Phase20AllocatorDisposition.NO_ELIGIBLE_ALLOCATION
    )
    return Phase20RobustAllocatorDecision(
        candidate_id="PHASE20H_ROBUST_CONSTRAINED_ALLOCATOR_V1",
        disposition=disposition,
        regime_posture=regime.posture,
        applied_tools=tuple(applied),
        reserve_stop_risk_usd=reserve_risk,
        reserve_margin_usd=reserve_margin,
        deployable_stop_risk_usd=deployable_risk,
        deployable_margin_usd=deployable_margin,
        reserved_for_opportunity_ids=reserved_ids,
        allocation=allocation,
        reason=(
            "single causal candidate allocated without unnecessary competition "
            "tooling"
            if len(candidates) == 1
            else (
                "causal candidates allocated only inside mission/regime, "
                "optionality, shared headroom and concentration constraints"
            )
        ),
    )
