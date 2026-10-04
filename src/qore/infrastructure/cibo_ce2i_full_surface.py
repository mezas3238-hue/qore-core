"""Complete 20-tool CE2I portfolio coordinator.

This is the single research entry point that binds account mission, causal regime
selection, per-opportunity advanced engines and portfolio-level advanced engines.
It performs no broker mutation and grants no Risk/execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_account_capital_mission import (
    CiboCapitalMissionPolicy,
    available_ce2i_tool_codes_for_mission,
    eligible_ce2i_tool_codes_for_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_advanced_capital_tools import (
    AdvancedCe2iEvidenceBundle,
    AdvancedToolDecision,
    CapitalVelocityEvidence,
    CapitalVelocityPolicy,
    ConvexExposureEvidence,
    FactorExposure,
    HedgedExposureEvidence,
    MarginEfficiencyEvidence,
    MarginExpression,
    PortfolioNettingEvidence,
    RiskEfficiencyCandidate,
    RiskEfficiencyEvidence,
    StructuralLeverageEvidence,
    evaluate_advanced_ce2i_surface,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CiboRegimeToolSelection,
    select_ce2i_tools_for_regime,
)
from qore.infrastructure.cibo_ce2i_runtime_receipt import (
    CiboCe2iRuntimeReceipt,
    build_ce2i_runtime_receipt,
)
from qore.infrastructure.cibo_ce2i_tool_registry import (
    CE2I_TOOL_REGISTRY,
    ToolMaturity,
)
from qore.infrastructure.cibo_next_policy_advanced_scientific_eligibility import (
    AdvancedScientificEligibilityFreeze,
)

_OPPORTUNITY_ADVANCED = ("T02", "T03", "T04", "T17")
_PORTFOLIO_ADVANCED = ("T08", "T10", "T16")


@dataclass(frozen=True, slots=True)
class AdvancedOpportunityEvidence:
    signal_fingerprint: str
    current_volume: Decimal = Decimal(0)
    maximum_additional_volume: Decimal = Decimal(0)
    structural_leverage: StructuralLeverageEvidence | None = None
    margin_efficiency: MarginEfficiencyEvidence | None = None
    risk_efficiency: RiskEfficiencyEvidence | None = None
    convex_exposure: ConvexExposureEvidence | None = None

    def __post_init__(self) -> None:
        if not self.signal_fingerprint:
            raise CiboCapitalManagementError(
                "advanced opportunity signal fingerprint required"
            )
        for name in ("current_volume", "maximum_additional_volume"):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"{name} must be finite non-negative Decimal"
                )


@dataclass(frozen=True, slots=True)
class AdvancedPortfolioEvidence:
    opportunities: tuple[AdvancedOpportunityEvidence, ...] = ()
    portfolio_netting: PortfolioNettingEvidence | None = None
    capital_velocity: CapitalVelocityEvidence | None = None
    hedged_exposure: HedgedExposureEvidence | None = None

    def __post_init__(self) -> None:
        ids = tuple(item.signal_fingerprint for item in self.opportunities)
        if len(ids) != len(set(ids)):
            raise CiboCapitalManagementError(
                "advanced opportunity evidence fingerprints must be unique"
            )


def build_causal_baseline_advanced_evidence(
    *,
    opportunities: tuple[TraderOpportunityEnvelope, ...],
    decision_at: datetime,
    existing: AdvancedPortfolioEvidence | None = None,
) -> AdvancedPortfolioEvidence:
    """Fill absent advanced-tool inputs with explicit causal baseline evidence.

    The baseline never claims OOS utility, provider alternatives, hedges, convex
    instruments, or statistical netting that are not actually present.  Its job is
    to let each native engine answer ABSTAIN/FAIL_CLOSED for a concrete reason
    instead of appearing disconnected through a missing-input placeholder.
    """

    if decision_at.tzinfo is None or decision_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "advanced causal baseline decision_at must be timezone-aware"
        )
    if not opportunities or any(
        not isinstance(item, TraderOpportunityEnvelope) for item in opportunities
    ):
        raise CiboCapitalManagementError(
            "advanced causal baseline requires TraderOpportunityEnvelope inputs"
        )
    existing = existing or AdvancedPortfolioEvidence()
    by_signal = {item.signal_fingerprint: item for item in existing.opportunities}
    if len(by_signal) != len(existing.opportunities):
        raise CiboCapitalManagementError(
            "advanced causal baseline existing evidence duplicates signal"
        )

    rows: list[AdvancedOpportunityEvidence] = []
    factor_rows: list[FactorExposure] = []
    baseline_risks: list[Decimal] = []
    for opportunity in sorted(
        opportunities,
        key=lambda item: (
            item.trader_id.value,
            item.qore_symbol,
            item.signal_fingerprint,
        ),
    ):
        prior = by_signal.get(opportunity.signal_fingerprint)
        minimum_volume = (
            opportunity.minimum_volume
            * Decimal(opportunity.minimum_execution_steps)
        )
        current_volume = (
            prior.current_volume if prior is not None and prior.current_volume > 0
            else minimum_volume
        )
        maximum_additional_volume = (
            prior.maximum_additional_volume
            if prior is not None and prior.maximum_additional_volume > 0
            else max(Decimal(0), opportunity.maximum_volume - current_volume)
        )
        stop_risk = current_volume * opportunity.stop_loss_per_volume
        margin = current_volume * opportunity.margin_per_volume
        baseline_risks.append(stop_risk)
        expression_id = "baseline:" + opportunity.signal_fingerprint
        risk_policy_id = "baseline-risk:" + opportunity.signal_fingerprint

        rows.append(
            AdvancedOpportunityEvidence(
                signal_fingerprint=opportunity.signal_fingerprint,
                current_volume=current_volume,
                maximum_additional_volume=maximum_additional_volume,
                structural_leverage=(
                    None if prior is None else prior.structural_leverage
                ),
                margin_efficiency=(
                    prior.margin_efficiency
                    if prior is not None and prior.margin_efficiency is not None
                    else MarginEfficiencyEvidence(
                        evidence_id="causal-margin:" + opportunity.signal_fingerprint,
                        observed_at=decision_at,
                        baseline_expression_id=expression_id,
                        expressions=(
                            MarginExpression(
                                expression_id=expression_id,
                                normalized_exposure=current_volume,
                                stop_risk_usd=stop_risk,
                                margin_usd=margin,
                                all_in_cost_usd=Decimal(0),
                                executable=True,
                                economics_verified=False,
                            ),
                        ),
                    )
                ),
                risk_efficiency=(
                    prior.risk_efficiency
                    if prior is not None and prior.risk_efficiency is not None
                    else RiskEfficiencyEvidence(
                        evidence_id="causal-risk:" + opportunity.signal_fingerprint,
                        observed_at=decision_at,
                        baseline_candidate_id=risk_policy_id,
                        candidates=(
                            RiskEfficiencyCandidate(
                                candidate_id=risk_policy_id,
                                expected_net_output_usd=Decimal(0),
                                true_stop_risk_usd=stop_risk,
                                p95_drawdown_usd=stop_risk,
                                tail_loss_usd=stop_risk,
                                margin_usd=max(margin, Decimal("0.00000001")),
                                sample_size=1,
                                evidence_oos=False,
                            ),
                        ),
                    )
                ),
                convex_exposure=(
                    prior.convex_exposure
                    if prior is not None and prior.convex_exposure is not None
                    else ConvexExposureEvidence(
                        evidence_id="causal-convex:" + opportunity.signal_fingerprint,
                        observed_at=decision_at,
                        available_limited_downside_capacity_usd=Decimal(0),
                        instruments=(),
                    )
                ),
            )
        )
        factor_rows.append(
            FactorExposure(
                position_id=opportunity.signal_fingerprint,
                factor_id="symbol:" + opportunity.qore_symbol,
                signed_risk_usd=(
                    stop_risk if opportunity.side == "long" else -stop_risk
                ),
            )
        )

    aggregate_risk = max(
        sum(baseline_risks, Decimal(0)),
        Decimal("0.00000001"),
    )
    return AdvancedPortfolioEvidence(
        opportunities=tuple(rows),
        portfolio_netting=(
            existing.portfolio_netting
            if existing.portfolio_netting is not None
            else PortfolioNettingEvidence(
                evidence_id="causal-netting:" + decision_at.isoformat(),
                observed_at=decision_at,
                exposures=tuple(factor_rows),
                correlation_state_id="unverified-causal-symbol-map",
                correlation_stable=False,
                factor_map_verified=False,
            )
        ),
        capital_velocity=(
            existing.capital_velocity
            if existing.capital_velocity is not None
            else CapitalVelocityEvidence(
                evidence_id="causal-velocity:" + decision_at.isoformat(),
                observed_at=decision_at,
                baseline_policy_id="baseline-current-capital-path",
                policies=(
                    CapitalVelocityPolicy(
                        policy_id="baseline-current-capital-path",
                        realized_net_output_usd=Decimal(0),
                        capital_minutes=Decimal(1),
                        p95_drawdown_usd=aggregate_risk,
                        tail_loss_usd=aggregate_risk,
                        sample_size=1,
                        evidence_oos=False,
                    ),
                ),
            )
        ),
        hedged_exposure=(
            existing.hedged_exposure
            if existing.hedged_exposure is not None
            else HedgedExposureEvidence(
                evidence_id="causal-hedge:" + decision_at.isoformat(),
                observed_at=decision_at,
                instruments=(),
            )
        ),
    )


@dataclass(frozen=True, slots=True)
class AdvancedOpportunityAssessment:
    signal_fingerprint: str
    decisions: tuple[AdvancedToolDecision, ...]

    def __post_init__(self) -> None:
        if not self.signal_fingerprint:
            raise CiboCapitalManagementError(
                "advanced opportunity assessment fingerprint required"
            )
        if any(item.tool_code not in _OPPORTUNITY_ADVANCED for item in self.decisions):
            raise CiboCapitalManagementError(
                "opportunity assessment contains portfolio-level tool"
            )


@dataclass(frozen=True, slots=True)
class FullCe2iSurfaceAssessment:
    mission_tools: tuple[str, ...]
    regime: CiboRegimeToolSelection
    opportunity_assessments: tuple[AdvancedOpportunityAssessment, ...]
    portfolio_decisions: tuple[AdvancedToolDecision, ...]
    registry_codes: tuple[str, ...]
    complete_registry: bool
    runtime_receipts: tuple[CiboCe2iRuntimeReceipt, ...] = ()

    def __post_init__(self) -> None:
        if self.registry_codes != tuple(
            f"T{index:02d}" for index in range(1, 21)
        ):
            raise CiboCapitalManagementError(
                "CE2I registry must expose canonical T01..T20 order"
            )
        if not self.complete_registry:
            raise CiboCapitalManagementError(
                "full CE2I coordinator cannot bind incomplete registry"
            )
        if not set(self.regime.enabled_tools).issubset(set(self.mission_tools)):
            raise CiboCapitalManagementError(
                "regime surface cannot exceed account mission"
            )
        if any(
            item.tool_code not in _PORTFOLIO_ADVANCED
            for item in self.portfolio_decisions
        ):
            raise CiboCapitalManagementError(
                "portfolio assessment contains opportunity-level tool"
            )
        if any(
            not isinstance(item, CiboCe2iRuntimeReceipt)
            for item in self.runtime_receipts
        ):
            raise CiboCapitalManagementError(
                "full CE2I runtime receipt type drift"
            )

    @property
    def advanced_decisions(self) -> tuple[AdvancedToolDecision, ...]:
        return tuple(
            decision
            for assessment in self.opportunity_assessments
            for decision in assessment.decisions
        ) + self.portfolio_decisions


def evaluate_full_ce2i_surface(
    *,
    mission: CiboCapitalMissionPolicy,
    regime_state: CiboCapitalRegimeState,
    opportunities: tuple[TraderOpportunityEnvelope, ...],
    advanced_evidence: AdvancedPortfolioEvidence,
    decision_at: datetime | None = None,
    scientific_eligibility: AdvancedScientificEligibilityFreeze | None = None,
) -> FullCe2iSurfaceAssessment:
    """Bind all 20 tool contracts and evaluate enabled advanced engines."""

    if not isinstance(mission, CiboCapitalMissionPolicy):
        raise CiboCapitalManagementError(
            "mission must be CiboCapitalMissionPolicy"
        )
    if not isinstance(regime_state, CiboCapitalRegimeState):
        raise CiboCapitalManagementError(
            "regime_state must be CiboCapitalRegimeState"
        )
    if not isinstance(advanced_evidence, AdvancedPortfolioEvidence):
        raise CiboCapitalManagementError(
            "advanced_evidence must be AdvancedPortfolioEvidence"
        )
    _validate_advanced_evidence_time(
        advanced_evidence=advanced_evidence,
        decision_at=decision_at,
    )
    if regime_state.opportunity_count != len(opportunities):
        raise CiboCapitalManagementError(
            "regime opportunity_count must match opportunity set"
        )
    fingerprints = tuple(item.signal_fingerprint for item in opportunities)
    if len(fingerprints) != len(set(fingerprints)):
        raise CiboCapitalManagementError(
            "full CE2I opportunity fingerprints must be unique"
        )

    registry_codes = tuple(tool.code for tool in CE2I_TOOL_REGISTRY)
    complete_registry = (
        len(registry_codes) == 20
        and registry_codes == tuple(
            f"T{index:02d}" for index in range(1, 21)
        )
        and all(
            tool.maturity
            not in {ToolMaturity.ARCHITECTURE_ONLY, ToolMaturity.REJECTED}
            for tool in CE2I_TOOL_REGISTRY
        )
    )
    if not complete_registry:
        raise CiboCapitalManagementError(
            "CIBO full-surface evaluation requires 20/20 executable contracts"
        )

    mission_tools = available_ce2i_tool_codes_for_mission(mission)
    action_authorized_tools = set(
        eligible_ce2i_tool_codes_for_mission(mission)
    )
    regime = select_ce2i_tools_for_regime(
        mission=mission,
        state=regime_state,
    )
    if not set(action_authorized_tools).issubset(set(mission_tools)):
        raise CiboCapitalManagementError(
            "CE2I action authority cannot exceed universal engine availability"
        )
    if scientific_eligibility is not None:
        if not isinstance(
            scientific_eligibility,
            AdvancedScientificEligibilityFreeze,
        ):
            raise CiboCapitalManagementError(
                "scientific_eligibility must be canonical freeze"
            )
        regime = scientific_eligibility.filter_regime_selection(regime)
    t12_input = {
        "mission_tools": list(mission_tools),
        "liquidity": regime_state.liquidity.value,
        "volatility": regime_state.volatility.value,
        "correlation": regime_state.correlation.value,
        "provider_condition": regime_state.provider_condition.value,
        "risk_utilization": str(regime_state.risk_utilization),
        "margin_utilization": str(regime_state.margin_utilization),
        "drawdown_utilization": str(regime_state.drawdown_utilization),
        "opportunity_count": regime_state.opportunity_count,
        "position_path_adverse": regime_state.position_path_adverse,
        "evidence_stale": regime_state.evidence_stale,
        "scientific_eligibility_applied": scientific_eligibility is not None,
    }
    t12_output = {
        "posture": regime.posture.value,
        "enabled_tools": list(regime.enabled_tools),
        "blocked_tools": list(regime.blocked_tools),
        "reason": regime.reason,
    }
    t12_receipt = build_ce2i_runtime_receipt(
        tool_code="T12",
        engine_name="select_ce2i_tools_for_regime",
        stage="PREDECISION",
        scope_id=(
            decision_at.isoformat()
            if decision_at is not None
            else "UNSEALED_RESEARCH_EPOCH"
        ),
        input_payload=t12_input,
        output_payload=t12_output,
        downstream_consumer="cibo-full-ce2i-surface",
        consumer_action="regime-tool-selection-consumed",
        decision_changed=bool(regime.blocked_tools),
        economic_effect_observable=False,
    )
    evidence_by_signal = {
        item.signal_fingerprint: item
        for item in advanced_evidence.opportunities
    }
    # Engine invocation is universal. Regime/mission restrictions belong to
    # downstream action authority, never to motor availability.
    opportunity_tools = tuple(
        code for code in _OPPORTUNITY_ADVANCED
        if code in mission_tools
    )
    assessments: list[AdvancedOpportunityAssessment] = []
    for opportunity in sorted(
        opportunities,
        key=lambda item: (
            item.trader_id.value,
            item.qore_symbol,
            item.signal_fingerprint,
        ),
    ):
        row = evidence_by_signal.get(opportunity.signal_fingerprint)
        bundle = AdvancedCe2iEvidenceBundle(
            structural_leverage=(
                row.structural_leverage if row is not None else None
            ),
            margin_efficiency=(
                row.margin_efficiency if row is not None else None
            ),
            risk_efficiency=(
                row.risk_efficiency if row is not None else None
            ),
            convex_exposure=(
                row.convex_exposure if row is not None else None
            ),
        )
        decisions = evaluate_advanced_ce2i_surface(
            enabled_tools=opportunity_tools,
            opportunity=opportunity,
            evidence=bundle,
            current_volume=(
                row.current_volume if row is not None else Decimal(0)
            ),
            maximum_additional_volume=(
                row.maximum_additional_volume
                if row is not None
                else Decimal(0)
            ),
        )
        assessments.append(
            AdvancedOpportunityAssessment(
                signal_fingerprint=opportunity.signal_fingerprint,
                decisions=decisions,
            )
        )

    portfolio_tools = tuple(
        code for code in _PORTFOLIO_ADVANCED
        if code in mission_tools
    )
    portfolio_decisions = evaluate_advanced_ce2i_surface(
        enabled_tools=portfolio_tools,
        opportunity=None,
        evidence=AdvancedCe2iEvidenceBundle(
            portfolio_netting=advanced_evidence.portfolio_netting,
            capital_velocity=advanced_evidence.capital_velocity,
            hedged_exposure=advanced_evidence.hedged_exposure,
        ),
    )
    return FullCe2iSurfaceAssessment(
        mission_tools=mission_tools,
        regime=regime,
        opportunity_assessments=tuple(assessments),
        portfolio_decisions=portfolio_decisions,
        registry_codes=registry_codes,
        complete_registry=True,
        runtime_receipts=(t12_receipt,),
    )


def _validate_advanced_evidence_time(
    *,
    advanced_evidence: AdvancedPortfolioEvidence,
    decision_at: datetime | None,
) -> None:
    """Reject advanced evidence that was not knowable at the decision epoch."""

    evidence_rows: list[tuple[str, object]] = []
    for row in advanced_evidence.opportunities:
        opportunity_rows: tuple[tuple[str, object | None], ...] = (
            ("T02", row.structural_leverage),
            ("T03", row.margin_efficiency),
            ("T04", row.risk_efficiency),
            ("T17", row.convex_exposure),
        )
        for label, item in opportunity_rows:
            if item is not None:
                evidence_rows.append((label, item))
    portfolio_rows: tuple[tuple[str, object | None], ...] = (
        ("T08", advanced_evidence.portfolio_netting),
        ("T10", advanced_evidence.capital_velocity),
        ("T16", advanced_evidence.hedged_exposure),
    )
    for label, item in portfolio_rows:
        if item is not None:
            evidence_rows.append((label, item))

    if not evidence_rows:
        return
    if decision_at is None:
        raise CiboCapitalManagementError(
            "advanced CE2I evidence requires explicit decision_at"
        )
    if decision_at.tzinfo is None or decision_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "advanced CE2I decision_at must be timezone-aware"
        )
    for tool_code, evidence in evidence_rows:
        observed_at = getattr(evidence, "observed_at", None)
        if not isinstance(observed_at, datetime):
            raise CiboCapitalManagementError(
                f"{tool_code} advanced evidence missing observed_at"
            )
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                f"{tool_code} advanced evidence observed_at must be timezone-aware"
            )
        if observed_at > decision_at:
            raise CiboCapitalManagementError(
                f"{tool_code} advanced evidence is future-known relative to decision_at"
            )
