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
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, localcontext
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
    CapitalCapacityDimension,
    CapitalSource,
    CiboCapitalActionPlan,
    CiboCapitalManagementError,
    CiboCapitalState,
    TraderOpportunityEnvelope,
    minimum_seed_volume,
)
from qore.infrastructure.cibo_capital_science_runtime_bridge import (
    CapitalScienceDirective,
    CapitalScienceKnownOpportunity,
    CapitalSciencePredecisionInput,
    evaluate_capital_science_predecision,
)
from qore.infrastructure.cibo_ce2i_regime_selector import CiboCapitalRegimeState
from qore.infrastructure.cibo_cma_risk_request import build_cma_risk_request
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
from qore.infrastructure.cibo_profit_preservation_shadow import (
    Genc7Action,
    Genc7PreservationProposalEvidence,
    Genc7SourceBucket,
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
    capital_science: CapitalScienceDirective
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
        if not isinstance(self.capital_science, CapitalScienceDirective):
            raise CiboCapitalManagementError(
                "sovereign decision requires canonical Capital Science directive"
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

    # Cognition never selects a broker volume, but it must grade the maximum
    # capital-intensity surface from its own causal epistemic state.  The old
    # binary 0-or-existing-cap seam let any positive recommendation inherit 4x.
    # Bounded confidence is intentionally not treated as certainty: LOW/MEDIUM/
    # HIGH can expose at most 1x/2x/3x respectively.  A future 4x path therefore
    # requires a distinct, explicit capital-confidence contract rather than
    # silently inheriting the historical maximum.
    existing_cap_raw = constraints.get("capital_intensity_cap", "4")
    try:
        existing_cap = int(existing_cap_raw)
    except (TypeError, ValueError) as error:
        raise CiboCapitalManagementError(
            "cognitive capital_intensity_cap must be integer 0..4"
        ) from error
    if existing_cap not in {0, 1, 2, 3, 4}:
        raise CiboCapitalManagementError(
            "cognitive capital_intensity_cap outside 0..4"
        )

    if synthesis.directive is not CiboExecutiveDirectiveKind.RECOMMEND:
        cognitive_cap = 0
    elif synthesis.uncertainty.confidence is None:
        cognitive_cap = 1
    else:
        confidence_cap = {
            "low": 1,
            "medium": 2,
            "high": 3,
        }
        level = synthesis.uncertainty.confidence.level.value
        if level not in confidence_cap:
            raise CiboCapitalManagementError(
                "cognitive confidence level has no capital-intensity mapping"
            )
        cognitive_cap = confidence_cap[level]

    constraints["capital_intensity_cap"] = str(
        min(existing_cap, cognitive_cap)
    )

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
    faculty_consultation: CiboEconomicConsultationReceipt | None = None,
    survival_capital_usd: Decimal,
    protected_capital_usd: Decimal,
    request_id: str,
    requested_at: datetime,
    expires_at: datetime,
    portfolio_fixed_multiplier: int | None = None,
    lifecycle_requests: tuple[CiboLifecycleWireRequest, ...] = (),
    peak_realized_capital_usd: Decimal | None = None,
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

    _validate_capital_twin_alignment(capital=capital, twin=twin)

    if faculty_consultation is None:
        consultation = consult_cibo_economic_faculties(
            decision_at=twin.captured_at,
            opportunities=(opportunity,),
            regime_state=regime_state,
            evidence_ref=evidence_ref,
        )
    else:
        if not isinstance(
            faculty_consultation,
            CiboEconomicConsultationReceipt,
        ):
            raise CiboCapitalManagementError(
                "sovereign runtime faculty_consultation must be canonical"
            )
        if faculty_consultation.decision_at != twin.captured_at:
            raise CiboCapitalManagementError(
                "sovereign runtime consultation/twin clock drift"
            )
        if (
            opportunity.signal_fingerprint
            not in faculty_consultation.opportunity_fingerprints
        ):
            raise CiboCapitalManagementError(
                "sovereign runtime target absent from shared consultation"
            )
        if faculty_consultation.opportunity_fingerprints.count(
            opportunity.signal_fingerprint
        ) != 1:
            raise CiboCapitalManagementError(
                "sovereign runtime target must appear exactly once"
            )
        consultation = faculty_consultation

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
        fixed_multiplier=portfolio_fixed_multiplier,
        lifecycle_requests=lifecycle_requests,
        competition_option_ids=(option_id,),
    )
    minimum_volume = minimum_seed_volume(opportunity)
    with localcontext() as context:
        context.prec = 100
        provider_cost_per_volume_usd = (
            twin_opportunity.provider_cost_usd / minimum_volume
        )
    sizing = plan_account_sizing(
        opportunity=opportunity,
        capital=capital,
        mission_policy=mission_policy,
        survival_capital_usd=survival_capital_usd,
        protected_capital_usd=protected_capital_usd,
        provider_cost_per_volume_usd=provider_cost_per_volume_usd,
        original_base_available_usd=_available_source_capacity(
            twin,
            CapitalCapacityDimension.BASE_RISK_CAPITAL,
        ),
        realized_profit_available_usd=_available_source_capacity(
            twin,
            CapitalCapacityDimension.ECONOMIC_PROFIT_CAPITAL,
        ),
    )
    capital_science = evaluate_capital_science_predecision(
        _build_capital_science_state(
            decision_id=decision_id,
            option_id=option_id,
            opportunity=opportunity,
            twin=cognitive_twin,
            sizing=sizing,
            capital=capital,
            regime_state=regime_state,
            peak_realized_capital_usd=peak_realized_capital_usd,
        )
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
            capital_science=capital_science,
            economic_run=economic,
            sizing=sizing,
            final_plan=final_plan,
            disposition=CiboSovereignCapitalDisposition.COGNITIVE_BLOCK,
            risk_request=None,
        )

    genc12_receipts = tuple(
        item
        for item in capital_science.receipts
        if item.function_code == "GEN-C12"
    )
    if len(genc12_receipts) != 1:
        raise CiboCapitalManagementError(
            "Capital Science must expose exactly one GEN-C12 receipt"
        )
    genc12_pauses_new_capital = (
        genc12_receipts[0].consumer_action == "PAUSE_NEW_CAPITAL"
    )
    if (
        sizing.plan.action
        in {
            CapitalAction.OPEN_MINIMAL_SEED,
            CapitalAction.OPEN_CAPABILITY_MAX,
            CapitalAction.EXPAND,
        }
        and genc12_pauses_new_capital
    ):
        final_plan = _hold_plan(
            opportunity=opportunity,
            sizing=sizing,
            reason=(
                "Capital Science GEN-C12 paused all new capital deployment"
            ),
        )
        return CiboSovereignCapitalDecision(
            decision_id=decision_id,
            option_id=option_id,
            synthesis=synthesis,
            faculty_consultation=consultation,
            capital_science=capital_science,
            economic_run=economic,
            sizing=sizing,
            final_plan=final_plan,
            disposition=CiboSovereignCapitalDisposition.CAPITAL_BLOCK,
            risk_request=None,
        )

    if (
        _plan_uses_realized_profit(sizing.plan)
        and not capital_science.allow_incremental_compound
    ):
        final_plan = _hold_plan(
            opportunity=opportunity,
            sizing=sizing,
            reason=(
                "Capital Science GEN-C surface did not admit incremental compound"
            ),
        )
        return CiboSovereignCapitalDecision(
            decision_id=decision_id,
            option_id=option_id,
            synthesis=synthesis,
            faculty_consultation=consultation,
            capital_science=capital_science,
            economic_run=economic,
            sizing=sizing,
            final_plan=final_plan,
            disposition=CiboSovereignCapitalDisposition.CAPITAL_BLOCK,
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
            capital_science=capital_science,
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
            capital_science=capital_science,
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
        capital_science=capital_science,
        economic_run=economic,
        sizing=sizing,
        final_plan=final_plan,
        disposition=CiboSovereignCapitalDisposition.RISK_REVIEW_READY,
        risk_request=risk_request,
    )


def _build_capital_science_state(
    *,
    decision_id: str,
    option_id: str,
    opportunity: TraderOpportunityEnvelope,
    twin: CiboObservedEconomicTwin,
    sizing: CiboAccountSizingDecision,
    capital: CiboCapitalState,
    regime_state: CiboCapitalRegimeState,
    peak_realized_capital_usd: Decimal | None = None,
) -> CapitalSciencePredecisionInput:
    """Project sovereign predecision truth into the native Capital Science surface."""

    known = tuple(
        CapitalScienceKnownOpportunity(
            option_id=item.option_id,
            trader_id=item.trader_id,
            qore_symbol=item.qore_symbol,
            known_at=item.known_at,
            earliest_action_at=item.earliest_action_at,
            expires_at=item.expires_at,
            requested_capital_usd=item.requested_capital_usd,
            stop_risk_usd=item.stop_risk_usd,
            margin_usd=item.margin_usd,
            evidence_sha256=item.evidence_sha256,
            expected_net_value_usd=item.expected_net_value_usd,
            expected_capital_minutes=item.expected_capital_minutes,
        )
        for item in twin.opportunities
    )
    target = next(
        (item for item in twin.opportunities if item.option_id == option_id),
        None,
    )
    if target is None:
        raise CiboCapitalManagementError(
            "Capital Science target option is absent from Full Economic Twin"
        )
    if (
        target.trader_id != opportunity.trader_id.value
        or target.qore_symbol != opportunity.qore_symbol
    ):
        raise CiboCapitalManagementError(
            "Capital Science target option identity drift"
        )

    current_provider_cost_usd = Decimal(0)
    current_expected_net_value_usd = target.expected_net_value_usd
    if sizing.plan.volume > 0:
        base_volume = minimum_seed_volume(opportunity)
        if target.stop_risk_usd <= 0 or base_volume <= 0:
            raise CiboCapitalManagementError(
                "Capital Science target base geometry must be positive"
            )
        with localcontext() as context:
            context.prec = 100
            expected_risk = (
                sizing.plan.volume * opportunity.stop_loss_per_volume
            )
            expected_margin = (
                sizing.plan.volume * opportunity.margin_per_volume
            )
            volume_scale = sizing.plan.volume / base_volume
            risk_scale = sizing.plan.stop_risk_usd / target.stop_risk_usd
            current_provider_cost_usd = (
                target.provider_cost_usd * volume_scale
            )
            current_expected_net_value_usd = (
                target.expected_net_value_usd * risk_scale
            )
        if (
            sizing.plan.stop_risk_usd != expected_risk
            or sizing.plan.margin_usd != expected_margin
        ):
            raise CiboCapitalManagementError(
                "Capital Science sizing plan geometry drift"
            )
        matches = tuple(item for item in known if item.option_id == option_id)
        if len(matches) != 1:
            raise CiboCapitalManagementError(
                "Capital Science current option must exist exactly once"
            )
        with localcontext() as context:
            context.prec = 100
            current_requested_capital_usd = (
                sizing.plan.stop_risk_usd + current_provider_cost_usd
            )
        known = tuple(
            replace(
                item,
                requested_capital_usd=current_requested_capital_usd,
                stop_risk_usd=sizing.plan.stop_risk_usd,
                margin_usd=sizing.plan.margin_usd,
                expected_net_value_usd=current_expected_net_value_usd,
                expected_capital_minutes=target.expected_capital_minutes,
            )
            if item.option_id == option_id
            else item
            for item in known
        )
    elif (
        sizing.plan.stop_risk_usd != 0
        or sizing.plan.margin_usd != 0
    ):
        raise CiboCapitalManagementError(
            "Capital Science zero-volume sizing geometry drift"
        )

    source = (
        sizing.plan.capital_source.value
        if sizing.plan.capital_source is not None
        else "NONE"
    )
    with localcontext() as context:
        context.prec = 100
        deployable_profit_usd = max(
            Decimal(0),
            twin.capital_twin.compound_economic_value_usd
            - twin.capital_twin.protected_floor_usd,
        )
    realized_capital_usd = twin.capital_twin.total_realized_capital_usd
    resolved_peak_realized_capital_usd = (
        realized_capital_usd
        if peak_realized_capital_usd is None
        else peak_realized_capital_usd
    )
    if (
        not isinstance(resolved_peak_realized_capital_usd, Decimal)
        or not resolved_peak_realized_capital_usd.is_finite()
        or resolved_peak_realized_capital_usd < realized_capital_usd
    ):
        raise CiboCapitalManagementError(
            "Capital Science peak realized capital must be finite and "
            "not below current realized capital"
        )
    genc7_proposal = None
    if sizing.plan.volume > 0 and _plan_uses_realized_profit(sizing.plan):
        with localcontext() as context:
            context.prec = 100
            compound_request_capital = (
                sizing.plan.stop_risk_usd + current_provider_cost_usd
            )
        if compound_request_capital > 0:
            horizon = max(
                1,
                int(
                    target.expected_capital_minutes.to_integral_value(
                        rounding=ROUND_CEILING
                    )
                ),
            )
            genc7_proposal = Genc7PreservationProposalEvidence(
                proposal_id=(
                    "genc7:upstream-sizing:"
                    + decision_id
                    + ":"
                    + opportunity.signal_fingerprint
                ),
                decision_at=twin.captured_at,
                account_identity=twin.capital_twin.account_identity,
                action=Genc7Action.COMPOUND,
                source_bucket=(
                    Genc7SourceBucket.COMPOUNDABLE_OR_RELEASED_CAPACITY
                ),
                amount_usd=compound_request_capital,
                evidence_sha256=target.evidence_sha256,
                rationale_code=(
                    "CAUSAL_REALIZED_PROFIT_SIZING_PROPOSAL"
                ),
                evaluation_horizon_minutes=horizon,
                calibrated=True,
                capital_eligible=target.capital_source_eligible,
            )

    return CapitalSciencePredecisionInput(
        decision_epoch_id=decision_id,
        signal_fingerprint=opportunity.signal_fingerprint,
        trader_id=opportunity.trader_id.value,
        decision_at=twin.captured_at,
        realized_capital_usd=realized_capital_usd,
        peak_realized_capital_usd=resolved_peak_realized_capital_usd,
        realized_profit_pool_usd=twin.capital_twin.compound_economic_value_usd,
        protected_capacity_usd=twin.capital_twin.protected_floor_usd,
        deployed_profit_usd=min(
            capital.reserved_expansion_risk_usd,
            deployable_profit_usd,
        ),
        open_stop_risk_usd=twin.capital_twin.used_stop_risk_usd,
        open_margin_usd=twin.capital_twin.used_margin_usd,
        requested_stop_risk_usd=sizing.plan.stop_risk_usd,
        requested_margin_usd=sizing.plan.margin_usd,
        provider_cost_usd=current_provider_cost_usd,
        expected_net_value_usd=current_expected_net_value_usd,
        expected_capital_minutes=target.expected_capital_minutes,
        hard_risk_headroom_usd=twin.capital_twin.stop_risk_headroom_usd,
        margin_headroom_usd=twin.capital_twin.margin_headroom_usd,
        competing_candidates=max(0, len(twin.opportunities) - 1),
        capital_source=source,
        qore_symbol=opportunity.qore_symbol,
        account_identity=twin.capital_twin.account_identity,
        regime_state=regime_state,
        known_simultaneous_opportunities=known,
        genc7_proposal=genc7_proposal,
    )


def _plan_uses_realized_profit(plan: CiboCapitalActionPlan) -> bool:
    """Return whether any requested stop-risk is sourced from realized profit."""

    if plan.capital_source is CapitalSource.REALIZED_PROFIT:
        return plan.stop_risk_usd > 0
    return any(
        item.source is CapitalSource.REALIZED_PROFIT and item.amount_usd > 0
        for item in plan.capital_source_lots
    )


def _available_source_capacity(
    twin: CiboObservedEconomicTwin,
    dimension: CapitalCapacityDimension,
) -> Decimal | None:
    """Read current source availability when the capital twin exposes it."""

    matches = tuple(
        item.available
        for item in twin.capital_twin.source_capacities
        if item.dimension is dimension
    )
    if not matches:
        return None
    if len(matches) != 1:
        raise CiboCapitalManagementError(
            "sovereign capital twin has duplicate source-capacity dimension"
        )
    return matches[0]


def _validate_capital_twin_alignment(
    *,
    capital: CiboCapitalState,
    twin: CiboObservedEconomicTwin,
) -> None:
    """Require Sizing/Compound inputs to be grounded in the same capital truth."""

    capital_twin = twin.capital_twin
    if capital.hard_risk_headroom_usd != capital_twin.stop_risk_headroom_usd:
        raise CiboCapitalManagementError(
            "CIBO sizing risk headroom must equal Full Economic Twin truth"
        )
    if capital.margin_headroom_usd != capital_twin.margin_headroom_usd:
        raise CiboCapitalManagementError(
            "CIBO sizing margin headroom must equal Full Economic Twin truth"
        )
    if (
        capital.realized_net_profit_usd
        > capital_twin.compound_economic_value_usd
    ):
        raise CiboCapitalManagementError(
            "CIBO realized-profit sizing state exceeds compound economic truth"
        )
    if (
        capital.proven_self_financing_capacity_usd
        > capital_twin.compound_economic_value_usd
    ):
        raise CiboCapitalManagementError(
            "CIBO self-financing capacity exceeds compound economic truth"
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

    with localcontext() as context:
        context.prec = 100
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

    with localcontext() as context:
        context.prec = 100
        risk = volume * opportunity.stop_loss_per_volume
        margin = volume * opportunity.margin_per_volume

    source_lots = plan.capital_source_lots
    capital_source = plan.capital_source
    if source_lots and risk != plan.stop_risk_usd:
        remaining = risk
        resized_lots = []
        with localcontext() as context:
            context.prec = 100
            for lot in source_lots:
                if remaining <= 0:
                    break
                amount = min(lot.amount_usd, remaining)
                if amount > 0:
                    resized_lots.append(
                        type(lot)(
                            source=lot.source,
                            amount_usd=amount,
                            source_id=lot.source_id,
                        )
                    )
                    remaining -= amount
        if remaining != 0:
            raise CiboCapitalManagementError(
                "sovereign resize exceeds declared capital-source provenance"
            )
        source_lots = tuple(resized_lots)
        capital_source = (
            source_lots[0].source
            if len(source_lots) == 1
            else None
        )

    return CiboCapitalActionPlan(
        trader_id=plan.trader_id,
        qore_symbol=plan.qore_symbol,
        stage=plan.stage,
        action=plan.action,
        volume=volume,
        stop_risk_usd=risk,
        margin_usd=margin,
        capital_source=capital_source,
        capital_source_amount_usd=risk,
        reason=(
            plan.reason
            + "; capped by Executive Brain + GEN-C11 + account-wide "
            "Portfolio/Adaptive Leverage"
        ),
        capital_source_lots=source_lots,
    )
