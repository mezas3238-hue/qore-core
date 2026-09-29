"""Canonical historical assembly adapter for Capitalizer V46-R2.

R2 binds already-causal source observations into the exact canonical
DualSourceEntryAcceptance -> SourceTraderEngine path.  It does not discover
trades, calculate economics, execute, size, or grant capital authority.

Frozen in PR #623 comment 5883247470.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_native_source_fact_remediation_v46 as remediation,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    market_is_allowed,
)
from qore.infrastructure.trader_lab.capitalizer_decision_sovereignty import (
    CapitalizerCognitiveGateDecision,
)
from qore.infrastructure.trader_lab.capitalizer_dual_source_entry_acceptance_v1 import (
    CapitalizerDualSourceEntryAcceptance,
    CapitalizerDualSourceEntryFacts,
    CapitalizerM1EntryStructureFacts,
    assess_dual_source_entry,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerSide,
)
from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    CapitalizerCISDObservation,
    CapitalizerFailureToManipulateObservation,
)
from qore.infrastructure.trader_lab.capitalizer_source_daily_bias_v2 import (
    CapitalizerDailyBiasObservation,
    CapitalizerDailyBiasResolution,
)
from qore.infrastructure.trader_lab.capitalizer_source_fractal_alignment_v2 import (
    CapitalizerFractalAlignmentObservation,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingObservation,
    CapitalizerSourceClosureObservation,
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_source_session_context_v2 import (
    CapitalizerSourceSessionAssessment,
    assess_source_session_context,
)
from qore.infrastructure.trader_lab.capitalizer_source_trader_engine_v2 import (
    CapitalizerSourceTraderEngineAssessment,
    CapitalizerSourceTraderEngineFacts,
    assess_source_trader_engine,
)

IDENTITY = "QORE_CAPITALIZER_CANONICAL_HISTORICAL_REPLAY_ADAPTER_V46_R2"
PREDECLARATION_COMMENT_ID = 5883247470

REQUIRED_EVIDENCE_KEYS = frozenset(
    {
        "HTF_POI",
        "HTF_CLOSURE",
        "HTF_BIAS",
        "STRUCTURAL_TARGET",
        "PROTECTED_SWING",
        "ICT_LIQUIDITY_REFERENCE",
        "ICT_LIQUIDITY_RAID",
        "ICT_MSS",
        "ICT_DISPLACEMENT",
        "ICT_FVG",
        "ICT_PD_ARRAY_RETRACE",
        "ICT_NO_CHASE",
        "TTRADES_LTF_CISD",
        "TTRADES_CONTINUATION",
        "TTRADES_WICK",
        "M1_MSS",
        "M1_FVG",
        "M1_ORDER_BLOCK",
    }
)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("canonical historical adapter requires aware timestamps")
    return value.astimezone(UTC)


def _direction(side: CapitalizerSide) -> CapitalizerSourceDirection:
    return (
        CapitalizerSourceDirection.BULLISH
        if side is CapitalizerSide.LONG
        else CapitalizerSourceDirection.BEARISH
    )


@dataclass(frozen=True, slots=True)
class CapitalizerHistoricalEvidenceStamp:
    key: str
    observed_at: datetime

    def __post_init__(self) -> None:
        if self.key not in REQUIRED_EVIDENCE_KEYS:
            raise ValueError(f"unknown canonical evidence key: {self.key}")
        _aware(self.observed_at)


@dataclass(frozen=True, slots=True)
class CapitalizerCanonicalICTFacts:
    liquidity_reference_defined: bool
    liquidity_raid_observed: bool
    market_structure_shift_confirmed: bool
    displacement_significant: bool
    fvg_present_in_displacement: bool
    entry_retrace_into_valid_pd_array: bool


@dataclass(frozen=True, slots=True)
class CapitalizerCanonicalHistoricalBundle:
    symbol: str
    side: CapitalizerSide
    session: CapitalizerSession
    decision_at: datetime
    cognitive_gate_decision: CapitalizerCognitiveGateDecision
    entry_price: Decimal

    daily_bias: CapitalizerDailyBiasObservation
    htf_closure: CapitalizerSourceClosureObservation
    structural_target: remediation.CapitalizerStructuralTargetResolution
    protected_swing: CapitalizerProtectedSwingObservation

    ict: CapitalizerCanonicalICTFacts
    no_chase: remediation.CapitalizerNoChaseObservation

    ltf_cisd: CapitalizerCISDObservation
    fractal_alignment: CapitalizerFractalAlignmentObservation | None
    failure_to_manipulate: CapitalizerFailureToManipulateObservation | None
    wick_formation: remediation.CapitalizerWickFormationObservation

    m1_mss: remediation.CapitalizerM1MSSObservation
    m1_fvg_confirmed: bool
    m1_order_block: remediation.CapitalizerM1OrderBlockObservation

    evidence_timestamps: tuple[CapitalizerHistoricalEvidenceStamp, ...]
    asian_open_reference_at: datetime | None = None
    contradictions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("canonical adapter symbol must be uppercase")
        if not market_is_allowed(session=self.session, symbol=self.symbol):
            raise ValueError("canonical adapter symbol outside frozen session universe")
        if not self.entry_price.is_finite():
            raise ValueError("canonical adapter entry price must be finite")
        decision = _aware(self.decision_at)
        if self.asian_open_reference_at is not None:
            _aware(self.asian_open_reference_at)

        keys = [stamp.key for stamp in self.evidence_timestamps]
        if len(keys) != len(set(keys)):
            raise ValueError("canonical evidence timestamps contain duplicate keys")
        if set(keys) != set(REQUIRED_EVIDENCE_KEYS):
            missing = sorted(REQUIRED_EVIDENCE_KEYS - set(keys))
            extra = sorted(set(keys) - REQUIRED_EVIDENCE_KEYS)
            raise ValueError(
                "canonical evidence timestamp coverage mismatch: "
                f"missing={missing} extra={extra}"
            )
        future = tuple(
            stamp.key
            for stamp in self.evidence_timestamps
            if _aware(stamp.observed_at) > decision
        )
        if future:
            raise ValueError(
                "canonical adapter future evidence prohibited: "
                + ",".join(sorted(future))
            )


@dataclass(frozen=True, slots=True)
class CapitalizerCanonicalHistoricalAdapterResult:
    identity: str
    symbol: str
    decision_at: str
    source_session: CapitalizerSourceSessionAssessment
    route_resolution: remediation.CapitalizerSourceRouteResolution
    dual_source_entry_acceptance: CapitalizerDualSourceEntryAcceptance
    source_engine_assessment: CapitalizerSourceTraderEngineAssessment | None
    passes_to_qore_risk: bool
    trade_plan_built: bool
    reasons: tuple[str, ...]
    all_evidence_timestamp_le_decision: bool = True
    outcome_aware: bool = False
    fixed_r_target_used: bool = False
    executes_trade: bool = False
    sizes_position: bool = False
    grants_capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("canonical historical adapter identity drift")
        if not self.reasons:
            raise ValueError("canonical historical adapter requires reasons")
        if not self.all_evidence_timestamp_le_decision:
            raise ValueError("canonical historical adapter cannot use future evidence")
        if (
            self.outcome_aware
            or self.fixed_r_target_used
            or self.executes_trade
            or self.sizes_position
            or self.grants_capital_authority
        ):
            raise ValueError("canonical historical adapter governance violated")

        if self.passes_to_qore_risk:
            if self.source_engine_assessment is None:
                raise ValueError("Risk pass requires source engine assessment")
            if not self.dual_source_entry_acceptance.passes_to_qore_risk:
                raise ValueError("Risk pass requires dual-source gate")
            if not self.source_engine_assessment.passes_to_qore_risk:
                raise ValueError("Risk pass requires source engine pass")
            if self.source_engine_assessment.trade_plan is None:
                raise ValueError("Risk pass requires structural trade plan")
        if self.trade_plan_built != (
            self.source_engine_assessment is not None
            and self.source_engine_assessment.trade_plan is not None
        ):
            raise ValueError("trade_plan_built mismatch")


def _directional_fractal(
    bundle: CapitalizerCanonicalHistoricalBundle,
) -> CapitalizerFractalAlignmentObservation | None:
    observation = bundle.fractal_alignment
    if observation is None:
        return None
    if observation.direction is not _direction(bundle.side):
        return None
    return observation


def _directional_ftm(
    bundle: CapitalizerCanonicalHistoricalBundle,
) -> CapitalizerFailureToManipulateObservation | None:
    observation = bundle.failure_to_manipulate
    if observation is None:
        return None
    if observation.continuation_direction is not _direction(bundle.side):
        return None
    return observation


def assess_canonical_historical_bundle(
    bundle: CapitalizerCanonicalHistoricalBundle,
) -> CapitalizerCanonicalHistoricalAdapterResult:
    """Assemble one causal historical candidate through both official gates."""

    intended = _direction(bundle.side)
    source_session = assess_source_session_context(
        session=bundle.session,
        observed_at=bundle.decision_at,
        asian_open_reference_at=bundle.asian_open_reference_at,
    )

    fractal = _directional_fractal(bundle)
    ftm = _directional_ftm(bundle)
    route_resolution = remediation.resolve_source_entry_route(
        fractal_alignment=fractal,
        failure_to_manipulate=ftm,
    )

    bias_aligned = (
        bundle.daily_bias.resolution is CapitalizerDailyBiasResolution.CONFIRMED
        and bundle.daily_bias.direction is intended
    )
    target_observation = bundle.structural_target.observation
    target_intact = (
        bundle.structural_target.resolved
        and target_observation is not None
        and target_observation.valid
        and target_observation.direction is intended
    )
    stop_geometry_valid = (
        bundle.protected_swing.confirmed
        and bundle.protected_swing.direction is intended
        and (
            bundle.protected_swing.swing_price < bundle.entry_price
            if bundle.side is CapitalizerSide.LONG
            else bundle.protected_swing.swing_price > bundle.entry_price
        )
    )
    htf_closure_ok = (
        bundle.htf_closure.source_rule_satisfied
        and bundle.htf_closure.point_of_interest_present
        and bundle.htf_closure.direction is intended
    )
    ltf_cisd_ok = (
        bundle.ltf_cisd.setup_confirmed
        and bundle.ltf_cisd.direction is intended
    )
    protected_ok = (
        bundle.protected_swing.confirmed
        and bundle.protected_swing.direction is intended
    )
    continuation_ok = (
        (fractal is not None and fractal.confirmed)
        or (ftm is not None and ftm.confirmed)
    )
    wick_ok = (
        bundle.wick_formation.confirmed
        and bundle.wick_formation.direction is intended
    )

    m1 = CapitalizerM1EntryStructureFacts(
        market_structure_shift_confirmed=bundle.m1_mss.confirmed,
        fair_value_gap_confirmed=bundle.m1_fvg_confirmed,
        order_block_confirmed=bundle.m1_order_block.confirmed,
    )
    dual_facts = CapitalizerDualSourceEntryFacts(
        cognitive_gate_decision=bundle.cognitive_gate_decision,
        source_session_resolved=source_session.resolved,
        source_session_eligible=source_session.eligible,
        higher_timeframe_bias_confirmed_aligned=bias_aligned,
        structural_target_intact=target_intact,
        structural_stop_geometry_valid=stop_geometry_valid,
        ict_liquidity_reference_defined=bundle.ict.liquidity_reference_defined,
        ict_liquidity_raid_observed=bundle.ict.liquidity_raid_observed,
        ict_market_structure_shift_confirmed=(
            bundle.ict.market_structure_shift_confirmed
        ),
        ict_displacement_significant=bundle.ict.displacement_significant,
        ict_fvg_present_in_displacement=bundle.ict.fvg_present_in_displacement,
        ict_entry_retrace_into_valid_pd_array=(
            bundle.ict.entry_retrace_into_valid_pd_array
        ),
        ict_entry_not_chasing=bundle.no_chase.confirmed,
        ttrades_htf_closure_at_poi_confirmed=htf_closure_ok,
        ttrades_ltf_cisd_confirmed=ltf_cisd_ok,
        ttrades_protected_swing_confirmed=protected_ok,
        ttrades_continuation_confirmed=continuation_ok,
        ttrades_wick_formation_confirmed=wick_ok,
        m1_entry_structure=m1,
        contradictions=bundle.contradictions,
    )
    dual_assessment = assess_dual_source_entry(dual_facts)

    engine: CapitalizerSourceTraderEngineAssessment | None = None
    reasons: list[str] = []

    if not route_resolution.resolved:
        reasons.extend(route_resolution.reasons)
    if not bundle.structural_target.resolved:
        reasons.extend(bundle.structural_target.reasons)

    if (
        route_resolution.route is not None
        and target_observation is not None
        and bundle.structural_target.target_kind is not None
    ):
        engine_facts = CapitalizerSourceTraderEngineFacts(
            symbol=bundle.symbol,
            side=bundle.side,
            route=route_resolution.route,
            cognitive_gate_decision=bundle.cognitive_gate_decision,
            source_session=source_session,
            daily_bias=bundle.daily_bias,
            entry_price=bundle.entry_price,
            protected_swing=bundle.protected_swing,
            structural_target=target_observation,
            target_kind=bundle.structural_target.target_kind,
            fractal_alignment=(
                fractal
                if route_resolution.route.value
                == "FRACTAL_SCALP_CONTINUATION"
                else None
            ),
            failure_to_manipulate=(
                ftm
                if route_resolution.route.value
                == "FAILURE_TO_MANIPULATE_CONTINUATION"
                else None
            ),
            dual_source_entry_acceptance=dual_assessment,
            contradictions=bundle.contradictions,
        )
        engine = assess_source_trader_engine(engine_facts)
        reasons.extend(engine.reasons)
    else:
        reasons.extend(
            f"DUAL_SOURCE:{reason}"
            for reason in dual_assessment.reasons
        )

    passes = engine is not None and engine.passes_to_qore_risk
    if not reasons:
        reasons.append("CANONICAL_HISTORICAL_ADAPTER_ASSESSED")

    result = CapitalizerCanonicalHistoricalAdapterResult(
        identity=IDENTITY,
        symbol=bundle.symbol,
        decision_at=_aware(bundle.decision_at).isoformat(),
        source_session=source_session,
        route_resolution=route_resolution,
        dual_source_entry_acceptance=dual_assessment,
        source_engine_assessment=engine,
        passes_to_qore_risk=passes,
        trade_plan_built=engine is not None and engine.trade_plan is not None,
        reasons=tuple(dict.fromkeys(reasons)),
    )

    if result.passes_to_qore_risk:
        if engine is None or engine.trade_plan is None:
            raise AssertionError("validated engine/trade plan unexpectedly missing")
        plan = engine.trade_plan
        if plan.initial_stop_price != bundle.protected_swing.swing_price:
            raise ValueError("canonical adapter stop drift")
        if plan.target_price != target_observation.target_price:
            raise ValueError("canonical adapter target drift")
        if plan.fixed_r_target_invented:
            raise ValueError("canonical adapter invented fixed-R target")

    return result
