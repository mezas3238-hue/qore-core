"""Canonical CIBO sovereign capital-decision runtime.

This module is the non-broker sovereign orchestration seam for CIBO:

Executive Brain
-> Full Economic Twin
-> GEN-C11 multi-period capital intelligence
-> account-wide Portfolio / Adaptive Leverage
-> position/opportunity competition
-> account Sizing / Compound funding state
-> CIBO CMA plan
-> QORE Risk request

CIBO owns the requested capital plan. QORE Risk remains the independent hard
survivability authority. No order submission, broker mutation, LIVE authority,
production authority, or real-capital authority exists in this module.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import ROUND_FLOOR, Decimal
from enum import StrEnum

from qore.infrastructure.account_wide_risk import CiboRiskRequest
from qore.infrastructure.cibo_account_capital_mission import (
    CiboCapitalMissionPolicy,
)
from qore.infrastructure.cibo_account_sizing_authority import (
    CiboAccountSizingDecision,
    plan_account_sizing,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CiboCapitalActionPlan,
    CiboCapitalManagementError,
    CiboCapitalState,
    TraderOpportunityEnvelope,
    minimum_seed_volume,
)
from qore.infrastructure.cibo_cma_risk_request import build_cma_risk_request
from qore.infrastructure.cibo_ce2i_regime_selector import CiboCapitalRegimeState
from qore.infrastructure.cibo_economic_engine_wiring import (
    CiboEconomicEngineRun,
    CiboLifecycleWireRequest,
    run_cibo_economic_engine_chain,
)
from qore.infrastructure.cibo_executive_brain import (
    CiboExecutiveDirectiveKind,
    CiboExecutiveSynthesis,
)
from qore.infrastructure.cibo_full_economic_digital_twin import (
    CiboObservedEconomicTwin,
)
from qore.infrastructure.cibo_multi_period_capital_mpc import (
    Genc11KnownOptionSchedule,
    Genc11WorldPath,
)
from qore.infrastructure.cibo_sovereign_function_consultation import (
    CiboEconomicConsultationReceipt,
    consult_cibo_economic_faculties,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef


class CiboSovereignCapitalDisposition(StrEnum):
    COGNITIVE_BLOCK = "COGNITIVE_BLOCK"
    CAPITAL_BLOCK = "CAPITAL_BLOCK"
    RISK_REVIEW_READY = "RISK_REVIEW_READY"


@dataclass(frozen=True, slots=True)
class CiboSovereignCapitalDecision:
    decision_id: str
    option_id: str
    synthesis: CiboExecutiveSynthesis
    faculty_consultation: CiboEconomicConsultationReceipt
    economic_run: CiboEconomicEngineRun
    sizing: CiboAccountSizingDecision
    final_plan: CiboCapitalActionPlan
    disposition: CiboSovereignCapitalDisposition
    risk_request: CiboRiskRequest | None
    cognitive_consumed: bool = True
    portfolio_consumed: bool = True
    adaptive_leverage_consumed: bool = True
    compound_state_consumed: bool = True
    qore_risk_sovereign: bool = True
    broker_mutation: bool = False
    execution_authority: bool = False
    live_authority: bool = False
    production_authority: bool = False
    real_capital_authority: bool = False

    def __post_init__(self) -> None:
        if not self.decision_id or not self.option_id:
            raise CiboCapitalManagementError(
                "sovereign capital decision identity is required"
            )
        if not isinstance(self.synthesis, CiboExecutiveSynthesis):
            raise CiboCapitalManagementError(
                "sovereign decision requires canonical CIBO synthesis"
            )
        self.synthesis.revalidate()
        if not isinstance(
            self.faculty_consultation,
            CiboEconomicConsultationReceipt,
        ):
            raise CiboCapitalManagementError(
                "sovereign decision requires CF01-CF19 consultation receipt"
            )
        if not isinstance(self.economic_run, CiboEconomicEngineRun):
            raise CiboCapitalManagementError(
                "sovereign decision requires canonical economic run"
            )
        if not isinstance(self.sizing, CiboAccountSizingDecision):
            raise CiboCapitalManagementError(
                "sovereign decision requires canonical sizing decision"
            )
        if not isinstance(self.final_plan, CiboCapitalActionPlan):
            raise CiboCapitalManagementError(
                "sovereign decision requires canonical CMA plan"
            )
        if type(self.disposition) is not CiboSovereignCapitalDisposition:
            raise CiboCapitalManagementError(
                "sovereign capital disposition is invalid"
            )
        ready = self.disposition is CiboSovereignCapitalDisposition.RISK_REVIEW_READY
        if ready != (self.risk_request is not None):
            raise CiboCapitalManagementError(
                "Risk-review disposition/request presence drift"
            )
        for name in (
            "cognitive_consumed",
            "portfolio_consumed",
            "adaptive_leverage_consumed",
            "compound_state_consumed",
            "qore_risk_sovereign",
            "broker_mutation",
            "execution_authority",
            "live_authority",
            "production_authority",
            "real_capital_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"sovereign decision {name} must be bool"
                )
        if (
            not self.cognitive_consumed
            or not self.portfolio_consumed
            or not self.adaptive_leverage_consumed
            or not self.compound_state_consumed
            or not self.qore_risk_sovereign
            or self.broker_mutation
            or self.execution_authority
            or self.live_authority
            or self.production_authority
            or self.real_capital_authority
        ):
            raise CiboCapitalManagementError(
                "sovereign capital authority boundary violated"
            )


def bind_cibo_cognition_to_twin(
    twin: CiboObservedEconomicTwin,
    synthesis: CiboExecutiveSynthesis,
) -> CiboObservedEconomicTwin:
    """Bind executive cognition to the economic twin without giving it sizing authority."""

    if not isinstance(twin, CiboObservedEconomicTwin):
        raise CiboCapitalManagementError(
            "cognitive binding requires canonical Full Economic Twin"
        )
    if not isinstance(synthesis, CiboExecutiveSynthesis):
        raise CiboCapitalManagementError(
            "cognitive binding requires canonical executive synthesis"
        )
    synthesis.revalidate()
    if synthesis.synthesized_at < twin.captured_at:
        raise CiboCapitalManagementError(
            "executive synthesis cannot predate the economic twin it governs"
        )

    constraints = dict(twin.cognitive_constraints)
    constraints["executive_directive"] = synthesis.directive.value
    constraints["executive_reasoning_mode"] = synthesis.reasoning_mode.value
    constraints["executive_uncertainty"] = synthesis.uncertainty.kind.value

    # Cognition does not pick volume. It can only close the capital-intensity
    # gate. A positive RECOMMEND leaves the existing economic cap untouched.
    if synthesis.directive is not CiboExecutiveDirectiveKind.RECOMMEND:
        constraints["capital_intensity_cap"] = "0"

    return replace(
        twin,
        cognitive_constraints=tuple(
            sorted((str(key), str(value)) for key, value in constraints.items())
        ),
    )


def run_cibo_sovereign_capital_runtime(
    *,
    decision_id: str,
    option_id: str,
    opportunity: TraderOpportunityEnvelope,
    synthesis: CiboExecutiveSynthesis,
    twin: CiboObservedEconomicTwin,
    world_paths: tuple[Genc11WorldPath, ...],
    option_schedules: tuple[Genc11KnownOptionSchedule, ...],
    mission_policy: CiboCapitalMissionPolicy,
    capital: CiboCapitalState,
    regime_state: CiboCapitalRegimeState,
    evidence_ref: CiboEvidenceRef,
    survival_capital_usd: Decimal,
    protected_capital_usd: Decimal,
    request_id: str,
    requested_at: datetime,
    expires_at: datetime,
    lifecycle_requests: tuple[CiboLifecycleWireRequest, ...] = (),
) -> CiboSovereignCapitalDecision:
    """Run the sovereign CIBO path through the QORE Risk handoff boundary."""

    if not decision_id or not option_id or not request_id:
        raise CiboCapitalManagementError(
            "sovereign runtime decision/option/request identity is required"
        )
    if not isinstance(opportunity, TraderOpportunityEnvelope):
        raise CiboCapitalManagementError(
            "sovereign runtime requires canonical Trader opportunity"
        )
    if not isinstance(twin, CiboObservedEconomicTwin):
        raise CiboCapitalManagementError(
            "sovereign runtime requires canonical Full Economic Twin"
        )
    if requested_at.tzinfo is None or requested_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "sovereign runtime requested_at must be timezone-aware"
        )
    if expires_at.tzinfo is None or expires_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "sovereign runtime expires_at must be timezone-aware"
        )
    if expires_at <= requested_at:
        raise CiboCapitalManagementError(
            "sovereign runtime expiry must follow request"
        )
    synthesis.revalidate()
    if not (twin.captured_at <= synthesis.synthesized_at <= requested_at):
        raise CiboCapitalManagementError(
            "sovereign causal order must be twin <= cognition <= Risk request"
        )

    consultation = consult_cibo_economic_faculties(
        decision_at=twin.captured_at,
        opportunities=(opportunity,),
        regime_state=regime_state,
        evidence_ref=evidence_ref,
    )

    twin_opportunity = next(
        (item for item in twin.opportunities if item.option_id == option_id),
        None,
    )
    if twin_opportunity is None:
        raise CiboCapitalManagementError(
            "sovereign option is absent from Full Economic Twin"
        )
    if (
        twin_opportunity.trader_id != opportunity.trader_id.value
        or twin_opportunity.qore_symbol != opportunity.qore_symbol
    ):
        raise CiboCapitalManagementError(
            "sovereign option identity does not match Trader opportunity"
        )

    cognitive_twin = bind_cibo_cognition_to_twin(twin, synthesis)
    economic = run_cibo_economic_engine_chain(
        twin=cognitive_twin,
        world_paths=world_paths,
        option_schedules=option_schedules,
        lifecycle_requests=lifecycle_requests,
        competition_option_ids=(option_id,),
    )
    sizing = plan_account_sizing(
        opportunity=opportunity,
        capital=capital,
        mission_policy=mission_policy,
        survival_capital_usd=survival_capital_usd,
        protected_capital_usd=protected_capital_usd,
    )

    portfolio_line = next(
        (
            item
            for item in economic.portfolio_plan.lines
            if item.option_id == option_id
        ),
        None,
    )
    if portfolio_line is None:
        raise CiboCapitalManagementError(
            "sovereign portfolio plan omitted the governed option"
        )

    competition = next(
        (
            item
            for item in economic.competition_plans
            if item.opportunity_id == option_id
        ),
        None,
    )
    if competition is None:
        raise CiboCapitalManagementError(
            "sovereign position/opportunity competition was not evaluated"
        )

    if synthesis.directive is not CiboExecutiveDirectiveKind.RECOMMEND:
        final_plan = _hold_plan(
            opportunity=opportunity,
            sizing=sizing,
            reason=(
                "executive cognition did not recommend capital deployment; "
                "memory/context remain advisory evidence only"
            ),
        )
        return CiboSovereignCapitalDecision(
            decision_id=decision_id,
            option_id=option_id,
            synthesis=synthesis,
            faculty_consultation=consultation,
            economic_run=economic,
            sizing=sizing,
            final_plan=final_plan,
            disposition=CiboSovereignCapitalDisposition.COGNITIVE_BLOCK,
            risk_request=None,
        )

    if portfolio_line.multiplier == 0 or not competition.admit_opportunity:
        final_plan = _hold_plan(
            opportunity=opportunity,
            sizing=sizing,
            reason=(
                "account-wide Portfolio/Adaptive Leverage or position "
                "competition rejected incremental capital"
            ),
        )
        return CiboSovereignCapitalDecision(
            decision_id=decision_id,
            option_id=option_id,
            synthesis=synthesis,
            faculty_consultation=consultation,
            economic_run=economic,
            sizing=sizing,
            final_plan=final_plan,
            disposition=CiboSovereignCapitalDisposition.CAPITAL_BLOCK,
            risk_request=None,
        )

    first_robust = economic.genc11_plan.robust_step_envelopes[0]
    final_plan = _cap_sizing_plan(
        opportunity=opportunity,
        sizing=sizing,
        portfolio_risk_cap_usd=portfolio_line.stop_risk_usd,
        portfolio_margin_cap_usd=portfolio_line.margin_usd,
        robust_risk_cap_usd=first_robust.common_stop_risk_headroom_usd,
        robust_margin_cap_usd=first_robust.common_margin_headroom_usd,
    )
    if final_plan.action is CapitalAction.HOLD:
        return CiboSovereignCapitalDecision(
            decision_id=decision_id,
            option_id=option_id,
            synthesis=synthesis,
            faculty_consultation=consultation,
            economic_run=economic,
            sizing=sizing,
            final_plan=final_plan,
            disposition=CiboSovereignCapitalDisposition.CAPITAL_BLOCK,
            risk_request=None,
        )

    risk_request = build_cma_risk_request(
        request_id=request_id,
        opportunity=opportunity,
        plan=final_plan,
        requested_at=requested_at,
        expires_at=expires_at,
    )
    return CiboSovereignCapitalDecision(
        decision_id=decision_id,
        option_id=option_id,
        synthesis=synthesis,
        faculty_consultation=consultation,
        economic_run=economic,
        sizing=sizing,
        final_plan=final_plan,
        disposition=CiboSovereignCapitalDisposition.RISK_REVIEW_READY,
        risk_request=risk_request,
    )


def _hold_plan(
    *,
    opportunity: TraderOpportunityEnvelope,
    sizing: CiboAccountSizingDecision,
    reason: str,
) -> CiboCapitalActionPlan:
    return CiboCapitalActionPlan(
        trader_id=opportunity.trader_id,
        qore_symbol=opportunity.qore_symbol,
        stage=sizing.plan.stage,
        action=CapitalAction.HOLD,
        volume=Decimal(0),
        stop_risk_usd=Decimal(0),
        margin_usd=Decimal(0),
        capital_source=None,
        capital_source_amount_usd=Decimal(0),
        reason=reason,
    )


def _cap_sizing_plan(
    *,
    opportunity: TraderOpportunityEnvelope,
    sizing: CiboAccountSizingDecision,
    portfolio_risk_cap_usd: Decimal,
    portfolio_margin_cap_usd: Decimal,
    robust_risk_cap_usd: Decimal,
    robust_margin_cap_usd: Decimal,
) -> CiboCapitalActionPlan:
    plan = sizing.plan
    if plan.action not in {
        CapitalAction.OPEN_MINIMAL_SEED,
        CapitalAction.OPEN_CAPABILITY_MAX,
        CapitalAction.EXPAND,
    }:
        return plan

    for name, value in (
        ("portfolio_risk_cap_usd", portfolio_risk_cap_usd),
        ("portfolio_margin_cap_usd", portfolio_margin_cap_usd),
        ("robust_risk_cap_usd", robust_risk_cap_usd),
        ("robust_margin_cap_usd", robust_margin_cap_usd),
    ):
        if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
            raise CiboCapitalManagementError(
                f"sovereign {name} must be finite non-negative Decimal"
            )

    raw = min(
        plan.volume,
        portfolio_risk_cap_usd / opportunity.stop_loss_per_volume,
        portfolio_margin_cap_usd / opportunity.margin_per_volume,
        robust_risk_cap_usd / opportunity.stop_loss_per_volume,
        robust_margin_cap_usd / opportunity.margin_per_volume,
    )
    steps = (raw / opportunity.volume_step).to_integral_value(
        rounding=ROUND_FLOOR
    )
    volume = steps * opportunity.volume_step
    minimum = minimum_seed_volume(opportunity)
    if volume < minimum:
        return _hold_plan(
            opportunity=opportunity,
            sizing=sizing,
            reason=(
                "combined cognition/portfolio/adaptive-leverage/GEN-C11 "
                "capacity cannot express the minimum executable seed"
            ),
        )

    if plan.capital_source_lots and volume != plan.volume:
        raise CiboCapitalManagementError(
            "sovereign resizing cannot mutate pre-reserved capital-source lots"
        )

    risk = volume * opportunity.stop_loss_per_volume
    margin = volume * opportunity.margin_per_volume
    return CiboCapitalActionPlan(
        trader_id=plan.trader_id,
        qore_symbol=plan.qore_symbol,
        stage=plan.stage,
        action=plan.action,
        volume=volume,
        stop_risk_usd=risk,
        margin_usd=margin,
        capital_source=plan.capital_source,
        capital_source_amount_usd=risk,
        reason=(
            plan.reason
            + "; capped by Executive Brain + GEN-C11 + account-wide "
            "Portfolio/Adaptive Leverage"
        ),
        capital_source_lots=plan.capital_source_lots,
    )
