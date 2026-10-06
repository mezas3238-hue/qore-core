"""Full provider-neutral native MAX cognitive episode for CIBO.

This module exercises the deeper native CIBO cognitive substrate before the
Executive Brain is allowed to recommend capital evaluation:

- world model
- attention/context selection
- MAX reasoning routing
- bounded calibration / abstention
- base/adverse/extreme/regime-change scenarios
- explicit correlation/causality substrate
- metacognitive audit
- integrated replayable cognitive episode

No external AI/model/provider is imported or invoked.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_cognitive_attention import (
    AttentionEvidenceRef,
    AttentionSignal,
    AttentionSignalKind,
    CalibrationNote,
    ContextSelectionResult,
    ReasoningDepthHint,
    ReasoningRequest,
    ReasoningRouteDecision,
    ReasoningRoutingOutcome,
    calibration_requires_abstention,
    route_reasoning,
    select_context,
)
from qore.infrastructure.cibo_cognitive_causality import (
    CausalClaim,
    CausalClaimKind,
    CausalClaimStatus,
    CausalClaimStrength,
    CausalEvidence,
    CausalEvidencePolarity,
    CausalVariable,
    build_causal_claim,
)
from qore.infrastructure.cibo_cognitive_common import fingerprint_material
from qore.infrastructure.cibo_cognitive_integration import (
    CiboIntegratedCognitiveEpisode,
    bind_evidence_fingerprint,
    build_integrated_episode,
)
from qore.infrastructure.cibo_cognitive_metacognition import (
    MetacognitiveAudit,
    MetacognitiveFinding,
    build_metacognitive_audit,
)
from qore.infrastructure.cibo_cognitive_scenarios import (
    Scenario,
    ScenarioAlternative,
    ScenarioAssumption,
    ScenarioFactKind,
    ScenarioFamily,
    build_scenario,
)
from qore.infrastructure.cibo_cognitive_world_model import (
    WorldModelDomain,
    WorldModelReference,
    WorldModelReferenceStatus,
    WorldModelSnapshot,
    WorldModelSourceId,
    WorldModelSourceVersion,
    build_world_model_snapshot,
)
from qore.infrastructure.cibo_sovereign_function_consultation import (
    CiboEconomicConsultationReceipt,
)
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboConfidence,
    CiboConfidenceLevel,
    CiboReasoningMode,
    CiboUncertainty,
    CiboUncertaintyKind,
)


@dataclass(frozen=True, slots=True)
class CiboNativeMaxCognitiveEpisode:
    world_snapshot: WorldModelSnapshot
    selected_context: ContextSelectionResult
    reasoning_routing: ReasoningRoutingOutcome
    calibration: CalibrationNote
    scenarios: tuple[Scenario, ...]
    causal_claim: CausalClaim
    metacognitive_audit: MetacognitiveAudit
    integrated_episode: CiboIntegratedCognitiveEpisode
    uncertainty: CiboUncertainty
    decision_gate_codes: tuple[str, ...] = ()
    external_ai_call_count: int = 0
    external_reasoning_provider_used: bool = False

    def __post_init__(self) -> None:
        self.world_snapshot.revalidate()
        if self.reasoning_routing.decision not in {
            ReasoningRouteDecision.PROCEED,
            ReasoningRouteDecision.ABSTAIN_INSUFFICIENT_EVIDENCE,
        }:
            raise CiboCapitalManagementError(
                "native cognitive episode routing decision invalid"
            )
        for scenario in self.scenarios:
            scenario.revalidate()
        self.causal_claim.revalidate()
        self.metacognitive_audit.revalidate()
        self.integrated_episode.revalidate()
        self.uncertainty.revalidate()
        if (
            not isinstance(self.decision_gate_codes, tuple)
            or any(
                not isinstance(item, str) or not item
                for item in self.decision_gate_codes
            )
            or len(self.decision_gate_codes)
            != len(set(self.decision_gate_codes))
        ):
            raise CiboCapitalManagementError(
                "native cognitive episode decision gate codes invalid"
            )
        if self.external_ai_call_count != 0:
            raise CiboCapitalManagementError(
                "native cognitive episode cannot call external AI"
            )
        if self.external_reasoning_provider_used:
            raise CiboCapitalManagementError(
                "native cognitive episode cannot use external reasoning provider"
            )

    @property
    def abstention_required(self) -> bool:
        return (
            self.reasoning_routing.decision
            is ReasoningRouteDecision.ABSTAIN_INSUFFICIENT_EVIDENCE
            or calibration_requires_abstention(self.calibration)
        )


def _fingerprint_from_semantics(
    consultation: CiboEconomicConsultationReceipt,
):
    material = tuple(
        (
            receipt.function_code,
            str(
                receipt.output_payload.get(
                    "research_semantic_observation"
                )
            ),
        )
        for receipt in consultation.faculty_receipts
    )
    return fingerprint_material(material)


def _semantic_state(
    consultation: CiboEconomicConsultationReceipt,
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for receipt in consultation.faculty_receipts:
        observation = receipt.output_payload.get(
            "research_semantic_observation"
        )
        if not isinstance(observation, dict):
            raise CiboCapitalManagementError(
                "native cognitive faculty semantic observation missing"
            )
        if (
            observation.get("function_code") != receipt.function_code
            or observation.get("research_read_only") is not True
            or observation.get("causal_predecision_only") is not True
            or observation.get("outcome_used") is not False
        ):
            raise CiboCapitalManagementError(
                "native cognitive faculty semantic governance drift"
            )
        semantics = observation.get("semantics")
        if not isinstance(semantics, dict):
            raise CiboCapitalManagementError(
                "native cognitive faculty semantic payload invalid"
            )
        result[receipt.function_code] = semantics
    return result


def _target_semantic_context(
    *,
    consultation: CiboEconomicConsultationReceipt,
    target_signal_fingerprint: str,
) -> dict[str, str]:
    semantics = _semantic_state(consultation)
    cf16 = semantics.get("CF16", {})
    surface = cf16.get("trader_voice_surface")
    if not isinstance(surface, (tuple, list)):
        raise CiboCapitalManagementError(
            "native cognitive CF16 trader voice surface missing"
        )
    matches = [
        item
        for item in surface
        if isinstance(item, dict)
        and item.get("signal_fingerprint") == target_signal_fingerprint
    ]
    if len(matches) != 1:
        raise CiboCapitalManagementError(
            "native cognitive target missing from CF16 semantics"
        )
    raw_context = matches[0].get("decision_context")
    if not isinstance(raw_context, (tuple, list)):
        raise CiboCapitalManagementError(
            "native cognitive target decision context missing"
        )
    context: dict[str, str] = {}
    for item in raw_context:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise CiboCapitalManagementError(
                "native cognitive target context entry invalid"
            )
        key = str(item[0])
        if key in context:
            raise CiboCapitalManagementError(
                "native cognitive target context duplicate key"
            )
        context[key] = str(item[1])
    return context


def _target_economic_semantics(
    *,
    consultation: CiboEconomicConsultationReceipt,
    target_signal_fingerprint: str,
) -> dict[str, object]:
    semantics = _semantic_state(consultation)
    cf07 = semantics.get("CF07", {})
    economic_state = cf07.get("economic_state")
    if not isinstance(economic_state, dict):
        raise CiboCapitalManagementError(
            "native cognitive CF07 economic state missing"
        )
    unit_economics = economic_state.get("unit_economics")
    if not isinstance(unit_economics, (tuple, list)):
        raise CiboCapitalManagementError(
            "native cognitive CF07 unit economics missing"
        )
    matches = [
        item
        for item in unit_economics
        if isinstance(item, dict)
        and item.get("signal_fingerprint") == target_signal_fingerprint
    ]
    if len(matches) != 1:
        raise CiboCapitalManagementError(
            "native cognitive target missing from CF07 semantics"
        )
    return matches[0]


def _native_faculty_blockers(
    consultation: CiboEconomicConsultationReceipt,
) -> tuple[str, ...]:
    return tuple(
        receipt.function_code
        for receipt in consultation.faculty_receipts
        if receipt.output_payload.get("native_engine_status")
        in {"FAIL_CLOSED", "DEPENDENCY_BLOCKED"}
    )


def _world_snapshot(
    *,
    consultation: CiboEconomicConsultationReceipt,
    semantic_fingerprint,
) -> WorldModelSnapshot:
    references = tuple(
        WorldModelReference(
            domain=domain,
            source_id=WorldModelSourceId(
                "cibo-native-" + domain.value
            ),
            source_version=WorldModelSourceVersion("v1"),
            as_of=consultation.decision_at,
            status=WorldModelReferenceStatus.CURRENT,
            evidence_fingerprint=semantic_fingerprint,
            evidence_label="native-causal-predecision-semantics",
        )
        for domain in (
            WorldModelDomain.MARKET,
            WorldModelDomain.TRADER,
            WorldModelDomain.PORTFOLIO,
            WorldModelDomain.OPERATIONAL,
            WorldModelDomain.RESEARCH,
        )
    )
    return build_world_model_snapshot(
        snapshot_id=uuid5(
            NAMESPACE_URL,
            "qore:cibo:native-max:world:"
            + consultation.consultation_id,
        ),
        as_of=consultation.decision_at,
        references=references,
        staleness_threshold=timedelta(0),
    )


def _attention(
    *,
    consultation: CiboEconomicConsultationReceipt,
    regime: CiboCapitalRegimeState,
    semantic_fingerprint,
    target_signal_fingerprint: str,
) -> tuple[
    ContextSelectionResult,
    ReasoningRoutingOutcome,
    CalibrationNote,
    tuple[str, ...],
]:
    evidence = (
        AttentionEvidenceRef(
            reference_id="native-cf01-cf19",
            fingerprint=semantic_fingerprint,
        ),
    )
    signals: list[AttentionSignal] = []
    target_context = _target_semantic_context(
        consultation=consultation,
        target_signal_fingerprint=target_signal_fingerprint,
    )
    target_economics = _target_economic_semantics(
        consultation=consultation,
        target_signal_fingerprint=target_signal_fingerprint,
    )
    faculty_blockers = _native_faculty_blockers(consultation)
    decision_gate_codes: list[str] = []

    def add(kind: AttentionSignalKind, severity: int, summary: str, reason: str) -> None:
        signals.append(
            AttentionSignal(
                signal_id=uuid5(
                    NAMESPACE_URL,
                    (
                        "qore:cibo:native-max:attention:"
                        + consultation.consultation_id
                        + ":"
                        + kind.value
                        + ":"
                        + summary
                    ),
                ),
                kind=kind,
                summary=summary,
                evidence_refs=evidence,
                severity=max(0, min(100, severity)),
                priority_reason=reason,
            )
        )

    add(
        AttentionSignalKind.PENDING_GOAL,
        100,
        "evaluate-current-capital-opportunity",
        "single-account-maximum-capability",
    )
    utilization = max(
        regime.risk_utilization,
        regime.margin_utilization,
        regime.drawdown_utilization,
    )
    utilization_pct = int(utilization * Decimal(100))
    if utilization > 0:
        add(
            AttentionSignalKind.RISK_DETERIORATION,
            utilization_pct,
            "account-capacity-utilization",
            "capital-survival-context",
        )
    if regime.evidence_stale:
        add(
            AttentionSignalKind.STALE_EVIDENCE,
            100,
            "stale-causal-evidence",
            "freshness-required",
        )
    if regime.provider_condition is not ProviderCondition.HEALTHY:
        add(
            AttentionSignalKind.ANOMALY,
            100 if regime.provider_condition is ProviderCondition.UNAVAILABLE else 70,
            "provider-condition-degraded",
            "provider-reality",
        )
    if regime.correlation is not CorrelationState.NORMAL:
        add(
            AttentionSignalKind.CONTRADICTION,
            90 if regime.correlation is CorrelationState.BREAK else 65,
            "portfolio-correlation-nonnormal",
            "portfolio-dependence",
        )
    if regime.volatility is VolatilityState.DISLOCATED:
        add(
            AttentionSignalKind.ANOMALY,
            95,
            "volatility-dislocated",
            "market-regime-anomaly",
        )
    if regime.position_path_adverse:
        add(
            AttentionSignalKind.RISK_DETERIORATION,
            85,
            "position-path-adverse",
            "capital-preservation",
        )

    context_quality_disposition = target_context.get(
        "cibo_context_quality_disposition"
    )
    context_quality_hard_gate = (
        target_context.get(
            "cibo_context_quality_hard_gate_authorized"
        )
        == "true"
    )
    if (
        context_quality_disposition == "ABSTAIN"
        and context_quality_hard_gate
    ):
        add(
            AttentionSignalKind.CONTRADICTION,
            95,
            "context-quality-abstention",
            "causal-predecision-context-quality",
        )
        decision_gate_codes.append("CF16")
    elif context_quality_disposition == "ABSTAIN":
        add(
            AttentionSignalKind.PENDING_GOAL,
            35,
            "research-only-context-quality-warning",
            "non-authoritative-context-research",
        )

    expectation_basis = target_economics.get("expectation_basis")
    cold_start_no_forecast = (
        expectation_basis == "COLD_START_NO_FORECAST"
    )
    walk_forward_forecast = (
        expectation_basis == "WALK_FORWARD_EMPIRICAL_FORECAST"
    )
    walk_forward_provisional = False
    walk_forward_maturity_fraction: Decimal | None = None
    if walk_forward_forecast:
        maturity = target_economics.get("walk_forward_maturity")
        mature = target_economics.get(
            "walk_forward_mature_for_capital_consideration"
        )
        observation_count_raw = target_economics.get(
            "walk_forward_observation_count"
        )
        maturity_fraction_raw = target_economics.get(
            "walk_forward_maturity_fraction"
        )
        dispersion_raw = target_economics.get(
            "walk_forward_block_dispersion_r"
        )
        mad_raw = target_economics.get(
            "walk_forward_median_absolute_deviation_r"
        )
        positive_blocks_raw = target_economics.get(
            "walk_forward_positive_block_count"
        )
        nonpositive_blocks_raw = target_economics.get(
            "walk_forward_nonpositive_block_count"
        )
        evidence_age_raw = target_economics.get(
            "walk_forward_evidence_age_minutes"
        )
        try:
            observation_count = int(str(observation_count_raw))
            positive_blocks = int(str(positive_blocks_raw))
            nonpositive_blocks = int(str(nonpositive_blocks_raw))
            walk_forward_maturity_fraction = Decimal(
                str(maturity_fraction_raw)
            )
            dispersion = Decimal(str(dispersion_raw))
            median_absolute_deviation = Decimal(str(mad_raw))
            evidence_age_minutes = Decimal(str(evidence_age_raw))
        except Exception as error:
            raise CiboCapitalManagementError(
                "native cognitive CF07 walk-forward confidence invalid"
            ) from error
        if (
            maturity not in {"PROVISIONAL", "MATURE"}
            or mature not in {"true", "false"}
            or observation_count < 5
            or positive_blocks < 0
            or nonpositive_blocks < 0
            or positive_blocks + nonpositive_blocks != 5
            or not walk_forward_maturity_fraction.is_finite()
            or walk_forward_maturity_fraction < 0
            or walk_forward_maturity_fraction > 1
            or not dispersion.is_finite()
            or dispersion < 0
            or not median_absolute_deviation.is_finite()
            or median_absolute_deviation < 0
            or not evidence_age_minutes.is_finite()
            or evidence_age_minutes < 0
            or (maturity == "MATURE") != (mature == "true")
        ):
            raise CiboCapitalManagementError(
                "native cognitive CF07 walk-forward confidence malformed"
            )
        walk_forward_provisional = mature != "true"
        if walk_forward_provisional:
            add(
                AttentionSignalKind.PENDING_GOAL,
                max(
                    40,
                    100 - int(
                        walk_forward_maturity_fraction * Decimal(100)
                    ),
                ),
                "walk-forward-forecast-provisional",
                "causal-estimator-maturity",
            )
            decision_gate_codes.append("CF07")

    if cold_start_no_forecast:
        add(
            AttentionSignalKind.PENDING_GOAL,
            100,
            "walk-forward-cold-start-no-forecast",
            "causal-history-warmup",
        )
        decision_gate_codes.append("CF07")

    expected_net_utility_raw = target_economics.get(
        "expected_net_utility_usd"
    )
    expected_net_utility: Decimal | None = None
    if isinstance(expected_net_utility_raw, str) and (
        expected_net_utility_raw
    ):
        try:
            expected_net_utility = Decimal(expected_net_utility_raw)
        except Exception as error:
            raise CiboCapitalManagementError(
                "native cognitive CF07 expected net utility invalid"
            ) from error
        if not expected_net_utility.is_finite():
            raise CiboCapitalManagementError(
                "native cognitive CF07 expected net utility non-finite"
            )
        if (
            not (
                context_quality_disposition == "ABSTAIN"
                and context_quality_hard_gate
            )
            and not cold_start_no_forecast
            and expected_net_utility <= 0
        ):
            add(
                AttentionSignalKind.CONTRADICTION,
                90,
                "nonpositive-causal-expected-net-utility",
                "cf07-economic-intelligence",
            )
            if "CF07" not in decision_gate_codes:
                decision_gate_codes.append("CF07")

    if expectation_basis == "FROZEN_HISTORICAL_PRIOR":
        add(
            AttentionSignalKind.PENDING_GOAL,
            40,
            "prior-only-economic-expectation",
            "contextual-forecast-gap",
        )

    selected = select_context(signals, max_results=10)

    missing: tuple[str, ...] = tuple(
        "native-faculty-" + code.lower() for code in faculty_blockers
    )
    if cold_start_no_forecast:
        missing += ("walk-forward-forecast-history",)
    if walk_forward_provisional:
        missing += ("walk-forward-forecast-maturity",)
    if regime.evidence_stale:
        missing += ("fresh-causal-evidence",)
    if regime.provider_condition is ProviderCondition.UNAVAILABLE:
        missing += ("provider-reality",)

    request = ReasoningRequest(
        request_id=uuid5(
            NAMESPACE_URL,
            "qore:cibo:native-max:routing:" + consultation.consultation_id,
        ),
        depth_hint=ReasoningDepthHint("max"),
        missing_evidence=missing,
        justification="native-max-capital-requires-deep-reasoning",
    )
    routing = route_reasoning(request)

    hard_capacity_exhausted = (
        regime.risk_utilization >= Decimal(1)
        or regime.margin_utilization >= Decimal(1)
        or regime.drawdown_utilization >= Decimal(1)
    )
    severe_joint_risk = (
        regime.position_path_adverse
        and (
            regime.volatility is VolatilityState.DISLOCATED
            or regime.correlation is CorrelationState.BREAK
        )
    )
    context_quality_abstain = (
        context_quality_disposition == "ABSTAIN"
        and context_quality_hard_gate
    )
    semantic_abstain = (
        context_quality_abstain
        or cold_start_no_forecast
        or walk_forward_provisional
        or (
            not context_quality_abstain
            and expected_net_utility is not None
            and expected_net_utility <= 0
        )
    )
    abstain = (
        bool(missing)
        or hard_capacity_exhausted
        or severe_joint_risk
        or semantic_abstain
    )
    if cold_start_no_forecast:
        kind = "more_evidence_requested"
        note = "walk-forward-cold-start-history-required"
    elif walk_forward_provisional:
        kind = "more_evidence_requested"
        note = "walk-forward-provisional-forecast-history-required"
    elif missing:
        kind = "more_evidence_requested"
        note = "fresh-provider-or-causal-evidence-required"
    elif context_quality_abstain:
        kind = "abstain_defer"
        note = "context-quality-abstention"
    elif (
        expected_net_utility is not None
        and expected_net_utility <= 0
    ):
        kind = "abstain_defer"
        note = "nonpositive-causal-expected-net-utility"
    elif hard_capacity_exhausted:
        kind = "abstain_defer"
        note = "account-capacity-exhausted"
    elif severe_joint_risk:
        kind = "abstain_defer"
        note = "joint-market-portfolio-risk-deterioration"
    else:
        kind = "bounded_confidence"
        note = "native-causal-state-bounded-confidence"

    epistemic_confidence_pct = 100
    if (
        walk_forward_forecast
        and walk_forward_maturity_fraction is not None
    ):
        epistemic_confidence_pct = int(
            walk_forward_maturity_fraction * Decimal(100)
        )
    confidence_band = max(
        0,
        min(
            100,
            100 - utilization_pct,
            epistemic_confidence_pct,
        ),
    )
    return (
        selected,
        routing,
        CalibrationNote(
            confidence_band=confidence_band,
            note=note,
            abstention_required=abstain,
            kind=kind,
        ),
        tuple(decision_gate_codes + list(faculty_blockers)),
    )


def _uncertainty(
    *,
    calibration: CalibrationNote,
    evidence_refs: tuple[CiboCognitiveEvidenceRef, ...],
) -> CiboUncertainty:
    if calibration.abstention_required:
        return CiboUncertainty(
            kind=CiboUncertaintyKind.ABSTAIN_DEFER,
        )
    level = (
        CiboConfidenceLevel.HIGH
        if calibration.confidence_band >= 67
        else CiboConfidenceLevel.MEDIUM
        if calibration.confidence_band >= 34
        else CiboConfidenceLevel.LOW
    )
    return CiboUncertainty(
        kind=CiboUncertaintyKind.BOUNDED_CONFIDENCE,
        confidence=CiboConfidence(
            level=level,
            evidence_refs=evidence_refs,
        ),
    )


def _scenarios(
    *,
    consultation: CiboEconomicConsultationReceipt,
    snapshot: WorldModelSnapshot,
    uncertainty: CiboUncertainty,
    abstained: bool,
) -> tuple[Scenario, ...]:
    families = (
        ScenarioFamily.BASE,
        ScenarioFamily.ADVERSE,
        ScenarioFamily.EXTREME,
        ScenarioFamily.REGIME_CHANGE,
    )
    result: list[Scenario] = []
    for family in families:
        observed = family is ScenarioFamily.BASE
        assumptions = (
            ScenarioAssumption(
                code=(
                    "current-causal-state"
                    if observed
                    else family.value.replace("-", "-") + "-hypothesis"
                ),
                fact_kind=(
                    ScenarioFactKind.OBSERVED
                    if observed
                    else ScenarioFactKind.HYPOTHETICAL
                ),
            ),
        )
        alternatives = (
            ()
            if abstained
            else (
                ScenarioAlternative(
                    alternative_id=uuid5(
                        NAMESPACE_URL,
                        f"qore:cibo:native-max:{consultation.consultation_id}:{family.value}:evaluate",
                    ),
                    action_code="evaluate-capital",
                    outcome_code="qore-risk-review",
                ),
                ScenarioAlternative(
                    alternative_id=uuid5(
                        NAMESPACE_URL,
                        f"qore:cibo:native-max:{consultation.consultation_id}:{family.value}:defer",
                    ),
                    action_code="defer",
                    outcome_code="preserve-capital",
                ),
                ScenarioAlternative(
                    alternative_id=uuid5(
                        NAMESPACE_URL,
                        f"qore:cibo:native-max:{consultation.consultation_id}:{family.value}:abstain",
                    ),
                    action_code="abstain",
                    outcome_code="preserve-capital",
                ),
            )
        )
        result.append(
            build_scenario(
                scenario_id=uuid5(
                    NAMESPACE_URL,
                    f"qore:cibo:native-max:scenario:{consultation.consultation_id}:{family.value}",
                ),
                family=family,
                version="v1",
                assumptions=assumptions,
                world_snapshot_id=(
                    snapshot.snapshot_id if observed else None
                ),
                world_fingerprint=(
                    snapshot.fingerprint if observed else None
                ),
                alternatives=alternatives,
                abstained=abstained,
                uncertainty=uncertainty,
                limitations=(
                    "hypothetical-not-fact",
                    "no-outcome-aware-reasoning",
                    "qore-risk-sovereign",
                ),
            )
        )
    return tuple(result)


def _causal_claim(
    *,
    consultation: CiboEconomicConsultationReceipt,
    semantic_ref: CiboCognitiveEvidenceRef,
) -> CausalClaim:
    cause = CausalVariable(
        code="current-causal-state",
        fingerprint=fingerprint_material(("current-causal-state",)),
    )
    effect = CausalVariable(
        code="capital-evaluation-context",
        fingerprint=fingerprint_material(("capital-evaluation-context",)),
    )
    evidence = CausalEvidence(
        ref=semantic_ref,
        polarity=CausalEvidencePolarity.SUPPORTS,
        observed_at=consultation.decision_at,
        fingerprint=fingerprint_material(
            (
                semantic_ref.value,
                CausalEvidencePolarity.SUPPORTS.value,
                consultation.decision_at,
            )
        ),
    )
    return build_causal_claim(
        claim_id=uuid5(
            NAMESPACE_URL,
            "qore:cibo:native-max:causal:" + consultation.consultation_id,
        ),
        kind=CausalClaimKind.CORRELATION,
        cause=cause,
        effect=effect,
        evidence_for=(evidence,),
        strength=CausalClaimStrength.MODERATE,
        status=CausalClaimStatus.ACTIVE,
    )


def build_native_max_cognitive_episode(
    *,
    consultation: CiboEconomicConsultationReceipt,
    opportunities: tuple[TraderOpportunityEnvelope, ...],
    target: TraderOpportunityEnvelope,
    regime_state: CiboCapitalRegimeState,
) -> CiboNativeMaxCognitiveEpisode:
    """Build and replay-validate CIBO's provider-neutral MAX cognitive episode."""

    if not opportunities or target not in opportunities:
        raise CiboCapitalManagementError(
            "native cognitive episode target/opportunity surface drift"
        )
    semantic_fp = _fingerprint_from_semantics(consultation)
    world = _world_snapshot(
        consultation=consultation,
        semantic_fingerprint=semantic_fp,
    )
    (
        selected,
        routing,
        calibration,
        decision_gate_codes,
    ) = _attention(
        consultation=consultation,
        regime=regime_state,
        semantic_fingerprint=semantic_fp,
        target_signal_fingerprint=target.signal_fingerprint,
    )
    evidence_refs = tuple(
        sorted(
            (
                CiboCognitiveEvidenceRef(
                    "cibo:native-world:" + world.fingerprint.value
                ),
                CiboCognitiveEvidenceRef(
                    "cibo:native-cf:" + semantic_fp.value
                ),
                CiboCognitiveEvidenceRef(
                    "cibo:native-target:" + target.signal_fingerprint
                ),
            ),
            key=lambda item: item.value,
        )
    )
    uncertainty = _uncertainty(
        calibration=calibration,
        evidence_refs=evidence_refs,
    )
    scenarios = _scenarios(
        consultation=consultation,
        snapshot=world,
        uncertainty=uncertainty,
        abstained=(
            routing.decision
            is ReasoningRouteDecision.ABSTAIN_INSUFFICIENT_EVIDENCE
            or calibration.abstention_required
        ),
    )
    semantic_ref = CiboCognitiveEvidenceRef(
        "cibo:native-cf:" + semantic_fp.value
    )
    causal = _causal_claim(
        consultation=consultation,
        semantic_ref=semantic_ref,
    )
    audit = build_metacognitive_audit(
        audit_id=uuid5(
            NAMESPACE_URL,
            "qore:cibo:native-max:metacognition:"
            + consultation.consultation_id,
        ),
        reasoning_mode=CiboReasoningMode.MAX,
        evidence_sufficiency=(
            MetacognitiveFinding.INSUFFICIENT_EVIDENCE
            if (
                routing.decision
                is ReasoningRouteDecision.ABSTAIN_INSUFFICIENT_EVIDENCE
                or calibration.abstention_required
            )
            else MetacognitiveFinding.SUFFICIENT
        ),
        reason_codes=(
            (
                "native-max-abstention-required",
            )
            if (
                routing.decision
                is ReasoningRouteDecision.ABSTAIN_INSUFFICIENT_EVIDENCE
                or calibration.abstention_required
            )
            else (
                "cf01-cf19-semantics-consumed",
                "native-perception-complete",
                "no-external-ai",
            )
        ),
    )
    bindings = (
        bind_evidence_fingerprint(semantic_fp),
        bind_evidence_fingerprint(world.fingerprint),
    )
    episode = build_integrated_episode(
        integration_id=uuid5(
            NAMESPACE_URL,
            "qore:cibo:native-max:episode:" + consultation.consultation_id,
        ),
        reasoning_mode=CiboReasoningMode.MAX,
        evidence_bindings=bindings,
        recorded_at=consultation.decision_at,
        world_snapshot=world,
        uncertainty=uncertainty,
        causal_claims=(causal,),
        scenarios=scenarios,
        metacognitive_audit=audit,
    )
    return CiboNativeMaxCognitiveEpisode(
        world_snapshot=world,
        selected_context=selected,
        reasoning_routing=routing,
        calibration=calibration,
        scenarios=scenarios,
        causal_claim=causal,
        metacognitive_audit=audit,
        integrated_episode=episode,
        uncertainty=uncertainty,
        decision_gate_codes=decision_gate_codes,
    )
