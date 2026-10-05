"""Position Intelligence and Structural Rearm for VT31_NAS100.

The mechanics implement the Turtle Soup architectural lessons without copying
XAUUSD policy parameters.

- initial stop remains VT31 methodological invalidation;
- a stop may only stay or improve, never widen;
- a structural observation becomes actionable only after confirmation;
- conquered DOLs can be represented as protection candidates;
- contextual trailing thresholds are configuration learned from NAS100, not
  hard-coded from Turtle Soup;
- after a protected/trailing exit, re-entry requires a genuinely new VT31
  market event rather than an arbitrary time cooldown.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qore.infrastructure.traders.vt31_nas100_reasoning_engine import (
        Nas100ReasoningDecision,
    )
    from qore.infrastructure.traders.vt31_nas100_situation_model import (
        Nas100SituationModel,
    )


class ManagementContext(StrEnum):
    SUPPORTIVE = "SUPPORTIVE"
    MIXED = "MIXED"
    CAUTIOUS = "CAUTIOUS"
    UNRESOLVED = "UNRESOLVED"


class PositionAction(StrEnum):
    HOLD = "HOLD"
    TRAIL = "TRAIL"
    DOL_LOCK = "DOL_LOCK"
    BANK = "BANK"
    EXTEND = "EXTEND"
    EXIT = "EXIT"
    REARM_REQUIRED = "REARM_REQUIRED"


@dataclass(frozen=True, slots=True)
class ContextualTrailingPolicy:
    """NAS100-learned parameters; None means policy not yet calibrated."""

    supportive_swing_confirmations: int | None
    mixed_swing_confirmations: int | None
    cautious_swing_confirmations: int | None
    dol_lock_enabled: bool

    def __post_init__(self) -> None:
        for value in (
            self.supportive_swing_confirmations,
            self.mixed_swing_confirmations,
            self.cautious_swing_confirmations,
        ):
            if value is not None and value < 1:
                raise ValueError("swing confirmations must be >=1 or None")

    def confirmations_for(self, state: ManagementContext) -> int | None:
        if state is ManagementContext.SUPPORTIVE:
            return self.supportive_swing_confirmations
        if state is ManagementContext.MIXED:
            return self.mixed_swing_confirmations
        if state is ManagementContext.CAUTIOUS:
            return self.cautious_swing_confirmations
        return None


RESEARCH_UNCALIBRATED_POLICY = ContextualTrailingPolicy(
    supportive_swing_confirmations=None,
    mixed_swing_confirmations=None,
    cautious_swing_confirmations=None,
    dol_lock_enabled=False,
)


@dataclass(frozen=True, slots=True)
class StructuralProtectionCandidate:
    level: Decimal
    confirmations: int
    source: str

    def __post_init__(self) -> None:
        if not self.level.is_finite() or self.level <= 0:
            raise ValueError("protection level must be positive finite")
        if self.confirmations < 1:
            raise ValueError("protection candidate requires confirmation")


@dataclass(frozen=True, slots=True)
class PositionManagementDecision:
    action: PositionAction
    next_stop: Decimal | None
    reason: str
    policy_calibrated: bool


@dataclass(frozen=True, slots=True)
class MarketNativePositionDecision:
    """Post-entry decision made only from market structure and cognition."""

    action: PositionAction
    next_stop: Decimal | None
    next_target: Decimal | None
    reason: str
    market_native: bool = True
    volume_agnostic: bool = True
    r_runtime_authority: bool = False


STRUCTURAL_DESTINATION_SOURCES = frozenset(
    {
        "confirmed-liquidity-pool",
        "confirmed-swing-high",
        "confirmed-swing-low",
        "confirmed-pd-array",
        "confirmed-session-liquidity",
    }
)


@dataclass(frozen=True, slots=True)
class StructuralDestinationCandidate:
    level: Decimal
    source: str
    confirmed: bool = True

    def __post_init__(self) -> None:
        if not self.level.is_finite() or self.level <= 0:
            raise ValueError("structural destination level must be positive finite")
        if self.source not in STRUCTURAL_DESTINATION_SOURCES:
            raise ValueError("next target requires approved structural provenance")
        if not self.confirmed:
            raise ValueError("next structural destination must be confirmed")


def decide_market_native_position(
    *,
    side: str,
    current_stop: Decimal,
    primary_structural_target: Decimal,
    next_structural_target: StructuralDestinationCandidate | None,
    cognition: FullCognitivePositionState,
    protective_swing: StructuralProtectionCandidate | None,
    primary_target_reached: bool,
    primary_target_accepted: bool,
    structure_invalidated: bool,
    liquidity_failure_confirmed: bool,
    momentum_deteriorated: bool,
    regime_changed_against_thesis: bool,
) -> MarketNativePositionDecision:
    """Manage VT31 without R, volume, sizing, or fixed-profit caps.

    The caller supplies only causal market facts. R is deliberately absent from
    the function signature so it cannot trigger target, protection, or exit.
    """

    if side not in {"long", "short"}:
        raise ValueError(f"unsupported side: {side}")
    for name, value in (
        ("current_stop", current_stop),
        ("primary_structural_target", primary_structural_target),
    ):
        if not value.is_finite() or value <= 0:
            raise ValueError(f"{name} must be positive finite")
    if next_structural_target is not None:
        level = next_structural_target.level
        beyond_primary = (
            level > primary_structural_target
            if side == "long"
            else level < primary_structural_target
        )
        if not beyond_primary:
            raise ValueError(
                "next structural destination must extend beyond primary target"
            )

    if structure_invalidated:
        return MarketNativePositionDecision(
            action=PositionAction.EXIT,
            next_stop=None,
            next_target=None,
            reason="STRUCTURAL_INVALIDATION_CONFIRMED",
        )

    if (
        cognition.target_intent
        is UniversalTargetIntent.EXIT_ON_CONFIRMED_EXHAUSTION
    ):
        return MarketNativePositionDecision(
            action=PositionAction.EXIT,
            next_stop=None,
            next_target=None,
            reason="COGNITIVE_EXHAUSTION_CONFIRMED",
        )

    if regime_changed_against_thesis:
        return MarketNativePositionDecision(
            action=PositionAction.EXIT,
            next_stop=None,
            next_target=None,
            reason="REGIME_CHANGED_AGAINST_THESIS",
        )

    if liquidity_failure_confirmed:
        return MarketNativePositionDecision(
            action=PositionAction.EXIT,
            next_stop=None,
            next_target=None,
            reason="LIQUIDITY_DELIVERY_FAILURE_CONFIRMED",
        )

    if primary_target_reached:
        extension_allowed = (
            primary_target_accepted
            and next_structural_target is not None
            and cognition.target_intent
            is UniversalTargetIntent.EXTEND_TO_DOL2
        )
        if extension_allowed:
            return MarketNativePositionDecision(
                action=PositionAction.EXTEND,
                next_stop=None,
                next_target=next_structural_target.level,
                reason="STRUCTURAL_TARGET_ACCEPTED_CONTINUATION_SUPPORTED",
            )
        return MarketNativePositionDecision(
            action=PositionAction.EXIT,
            next_stop=None,
            next_target=None,
            reason="PRIMARY_STRUCTURAL_TARGET_DELIVERED",
        )

    if (
        momentum_deteriorated
        and protective_swing is not None
        and improves_stop(
            side=side,
            current_stop=current_stop,
            candidate_stop=protective_swing.level,
            target=primary_structural_target,
        )
    ):
        return MarketNativePositionDecision(
            action=PositionAction.TRAIL,
            next_stop=protective_swing.level,
            next_target=None,
            reason="MOMENTUM_DETERIORATED_CONFIRMED_STRUCTURAL_SWING",
        )

    return MarketNativePositionDecision(
        action=PositionAction.HOLD,
        next_stop=None,
        next_target=None,
        reason="MARKET_STRUCTURE_REMAINS_VALID",
    )


def improves_stop(
    *,
    side: str,
    current_stop: Decimal,
    candidate_stop: Decimal,
    target: Decimal,
) -> bool:
    if side == "long":
        return current_stop < candidate_stop < target
    if side == "short":
        return target < candidate_stop < current_stop
    raise ValueError(f"unsupported side: {side}")


def decide_structural_protection(
    *,
    side: str,
    current_stop: Decimal,
    target: Decimal,
    context: ManagementContext,
    swing: StructuralProtectionCandidate | None,
    conquered_dol: Decimal | None,
    policy: ContextualTrailingPolicy = RESEARCH_UNCALIBRATED_POLICY,
) -> PositionManagementDecision:
    """Choose protection without ever widening or copying XAUUSD thresholds."""
    required = policy.confirmations_for(context)

    # A conquered DOL is supported mechanically, but it is not activated until
    # NAS100 position-management research explicitly enables it.
    if (
        policy.dol_lock_enabled
        and conquered_dol is not None
        and improves_stop(
            side=side,
            current_stop=current_stop,
            candidate_stop=conquered_dol,
            target=target,
        )
    ):
        return PositionManagementDecision(
            action=PositionAction.DOL_LOCK,
            next_stop=conquered_dol,
            reason="CONQUERED_DOL_STRUCTURAL_PROTECTION",
            policy_calibrated=True,
        )

    if required is None:
        return PositionManagementDecision(
            action=PositionAction.HOLD,
            next_stop=None,
            reason="VT31_CONTEXTUAL_TRAILING_NOT_YET_CALIBRATED",
            policy_calibrated=False,
        )

    if swing is None or swing.confirmations < required:
        return PositionManagementDecision(
            action=PositionAction.HOLD,
            next_stop=None,
            reason="ADDITIONAL_STRUCTURAL_CONFIRMATION_REQUIRED",
            policy_calibrated=True,
        )

    if not improves_stop(
        side=side,
        current_stop=current_stop,
        candidate_stop=swing.level,
        target=target,
    ):
        return PositionManagementDecision(
            action=PositionAction.HOLD,
            next_stop=None,
            reason="CANDIDATE_DOES_NOT_IMPROVE_STOP",
            policy_calibrated=True,
        )

    return PositionManagementDecision(
        action=PositionAction.TRAIL,
        next_stop=swing.level,
        reason=f"{context.value}_CONFIRMED_STRUCTURAL_PROTECTION",
        policy_calibrated=True,
    )


def structurally_rearmed(
    *,
    protected_exit_at_epoch: int | None,
    new_raid_at_epoch: int,
    new_confirmation_at_epoch: int,
    new_decision_at_epoch: int,
) -> bool:
    """VT31 rearm: require a new raid + confirmation + decision after exit."""
    if protected_exit_at_epoch is None:
        return True
    return bool(
        new_raid_at_epoch > protected_exit_at_epoch
        and new_confirmation_at_epoch > protected_exit_at_epoch
        and new_decision_at_epoch > protected_exit_at_epoch
    )


class UniversalTargetIntent(StrEnum):
    """Causal target intent independent of trade volume and provider lot size."""

    PRESERVE_DOL1 = "PRESERVE_DOL1"
    EXTEND_TO_DOL2 = "EXTEND_TO_DOL2"
    EXIT_ON_CONFIRMED_EXHAUSTION = "EXIT_ON_CONFIRMED_EXHAUSTION"


class ProtectionUrgency(StrEnum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


@dataclass(frozen=True, slots=True)
class FullCognitivePositionState:
    """Auditable synthesis of the complete causal VT31 cognition after entry.

    The state consumes every cognitive domain already available to VT31 while
    keeping uncalibrated observations visible instead of silently discarding
    them. It never consumes terminal PnL or future-journey labels.
    """

    management_context: ManagementContext
    destination_state: str
    target_intent: UniversalTargetIntent
    protection_urgency: ProtectionUrgency
    support_score: int
    caution_score: int
    signal_codes: tuple[str, ...]
    observed_domains: tuple[str, ...]
    observed_situation_fields: tuple[str, ...]
    actuated_situation_fields: tuple[str, ...]
    observation_only_situation_fields: tuple[str, ...]
    cognitive_coverage_ratio: Decimal
    entry_situation_fingerprint: str
    current_situation_fingerprint: str
    post_entry_reassessment: bool
    memory_fingerprint: str
    entry_tier: str | None
    dol1_acceptance_observed: bool | None
    volume_agnostic: bool = True
    partial_execution_required: bool = False
    terminal_pnl_used: bool = False
    future_journey_label_used: bool = False

    def fingerprint(self) -> str:
        payload = asdict(self)
        encoded = json.dumps(
            {
                key: (
                    format(value, "f")
                    if isinstance(value, Decimal)
                    else value
                )
                for key, value in payload.items()
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def _contains_any(value: str, tokens: tuple[str, ...]) -> bool:
    normalized = value.upper().replace("-", "_").replace(" ", "_")
    return any(token in normalized for token in tokens)


def _direction_alignment(side: str, state: str) -> int:
    normalized = state.lower()
    if normalized not in {"bullish", "bearish"}:
        return 0
    if side == "long":
        return 1 if normalized == "bullish" else -1
    if side == "short":
        return 1 if normalized == "bearish" else -1
    raise ValueError(f"unsupported side: {side}")


def _dol1_reached(state: str) -> bool:
    return _contains_any(
        state,
        ("REACHED", "TOUCHED", "CONQUERED", "ACHIEVED", "DELIVERED"),
    )


def _confirmed_exhaustion(state: str) -> bool:
    if _contains_any(state, ("UNKNOWN", "UNRESOLVED", "NONE", "ABSENT")):
        return False
    return _contains_any(
        state,
        ("EXHAUST", "DEPLET", "FAILED_CONTINUATION", "REVERSAL_CONFIRMED"),
    )


def _destination_state(
    situation: Nas100SituationModel,
    *,
    entry_tier: str | None,
) -> tuple[str, tuple[str, ...]]:
    """Build consumed-evidence SHALLOW/NEUTRAL/DEEP destination state."""

    shallow: list[str] = []
    latency = situation.confirmation_latency_minutes

    if (
        situation.entry_evidence_family == "breaker"
        and latency is not None
        and latency >= 11
    ):
        shallow.append("BREAKER_LATENCY_11M_PLUS")

    if (
        situation.last_structure_event_family == "breaker"
        and situation.entry_evidence_family == "breaker"
    ):
        shallow.append("LAST_BREAKER_ENTRY_BREAKER")

    if (
        situation.premarket_state == "bearish"
        and situation.cash_open_state == "bearish"
    ):
        shallow.append("PREMARKET_BEARISH_CASH_BEARISH")

    if (
        situation.volatility_state == "expanded"
        and situation.current_path_vs_previous is not None
        and situation.current_path_vs_previous > Decimal("1.25")
    ):
        shallow.append("EXPANDED_PATH_HIGH")

    if (
        entry_tier == "SECONDARY"
        and situation.entry_evidence_family == "breaker"
    ):
        shallow.append("SECONDARY_BREAKER")

    if shallow:
        return "SHALLOW", tuple(shallow)
    if situation.volatility_state == "compressed":
        return "DEEP", ("REFERENCE_VOLATILITY_COMPRESSED",)
    return "NEUTRAL", ()


def assess_full_cognitive_position(
    *,
    situation: Nas100SituationModel,
    reasoning: Nas100ReasoningDecision,
    entry_tier: str | None = None,
    dol1_acceptance_observed: bool | None = None,
    entry_situation_fingerprint: str | None = None,
) -> FullCognitivePositionState:
    """Synthesize current cognition from frozen entry reasoning + live situation."""

    current_fingerprint = situation.fingerprint()
    bound_entry_fingerprint = (
        current_fingerprint
        if entry_situation_fingerprint is None
        else entry_situation_fingerprint
    )
    if reasoning.situation_fingerprint != bound_entry_fingerprint:
        raise ValueError("entry reasoning fingerprint mismatch")
    post_entry_reassessment = current_fingerprint != bound_entry_fingerprint

    observed_domains = (
        "STRATEGY_REASONING",
        "MARKET_REGIME",
        "LIQUIDITY_SEQUENCE",
        "ENTRY_QUALITY",
        "RISK_GEOMETRY",
        "JOURNEY_DESTINATION",
        "INTERMARKET",
        "TEMPORAL",
    )
    signals: list[str] = []
    support = 0
    caution = 0

    situation_payload = situation.payload()
    metadata_fields = {
        "schema",
        "memory_class",
        "persistent_memory",
        "causal_as_of_only",
        "terminal_pnl_present",
        "historical_date_outcome_present",
    }
    observed_situation_fields = tuple(
        sorted(
            field
            for field in situation_payload
            if field not in metadata_fields
        )
    )
    actuated_situation_fields = tuple(
        sorted(
            {
                "decision_minute_ny",
                "side",
                "premarket_state",
                "cash_open_state",
                "range_state",
                "volatility_state",
                "current_path_vs_previous",
                "recent_path_efficiency",
                "recent_overlap_rate",
                "reference_reclaimed",
                "reference_reclaim_age_minutes",
                "last_structure_event_family",
                "recent_liquidity_event_count_10m",
                "displacement_state",
                "entry_evidence_family",
                "confirmation_latency_minutes",
                "entry_evidence_freshness",
                "dol1_state",
                "extension_capacity_state",
                "exhaustion_state",
                "cross_index_state",
            }
        )
    )
    observation_only_situation_fields = tuple(
        field
        for field in observed_situation_fields
        if field not in actuated_situation_fields
    )
    coverage_ratio = (
        Decimal("1")
        if observed_situation_fields
        else Decimal("0")
    )
    signals.extend(
        f"OBSERVE_ONLY:{field}={situation_payload[field]}"
        for field in observation_only_situation_fields
    )

    support += min(3, len(reasoning.supporting_evidence))
    signals.extend(
        f"REASONING_SUPPORT:{code}"
        for code in reasoning.supporting_evidence
    )
    signals.extend(
        f"REASONING_CONTEXT:{code}"
        for code in reasoning.context_observations
    )
    signals.extend(
        f"STRATEGY_MEMORY_USED:{name}"
        for name in reasoning.strategy_memory_used
    )
    signals.extend(
        f"CIBO_MEMORY_USED:{name}"
        for name in reasoning.cibo_market_memory_used
    )
    signals.extend(
        f"EXPERIENCE_MEMORY_USED:{name}"
        for name in reasoning.trader_experience_memory_used
    )

    if reasoning.action == "EXECUTE":
        support += 2
        signals.append("REASONING_EXECUTE_SOVEREIGN")
    else:
        caution += 4
        signals.append(f"REASONING_NOT_EXECUTE:{reasoning.action}")

    if reasoning.contradictions:
        caution += min(6, 2 * len(reasoning.contradictions))
        signals.extend(
            f"REASONING_CONTRADICTION:{code}"
            for code in reasoning.contradictions
        )
    else:
        support += 1
        signals.append("REASONING_NO_CONTRADICTIONS")

    if reasoning.uncertainty:
        caution += min(3, len(reasoning.uncertainty))
        signals.extend(
            f"REASONING_UNCERTAINTY:{code}" for code in reasoning.uncertainty
        )

    if situation.volatility_state == "compressed":
        support += 2
        signals.append("REGIME_REFERENCE_COMPRESSED")
    elif situation.volatility_state == "expanded":
        caution += 2
        signals.append("REGIME_REFERENCE_EXPANDED")

    if situation.range_state == "compressed":
        support += 1
        signals.append("RANGE_STATE_COMPRESSED")
    elif situation.range_state == "expanded":
        caution += 1
        signals.append("RANGE_STATE_EXPANDED")

    path = situation.current_path_vs_previous
    if path is not None:
        if path < Decimal("0.75"):
            support += 1
            signals.append("PATH_COMPACT")
        elif path > Decimal("1.25"):
            caution += 2
            signals.append("PATH_OVEREXPANDED")

    efficiency = situation.recent_path_efficiency
    if efficiency is not None:
        if efficiency >= Decimal("0.55"):
            support += 1
            signals.append("PATH_EFFICIENCY_HEALTHY")
        elif efficiency <= Decimal("0.30"):
            caution += 1
            signals.append("PATH_EFFICIENCY_WEAK")

    overlap = situation.recent_overlap_rate
    if overlap is not None:
        if overlap <= Decimal("0.55"):
            support += 1
            signals.append("OVERLAP_LOW")
        elif overlap >= Decimal("0.75"):
            caution += 1
            signals.append("OVERLAP_HIGH")

    if situation.reference_reclaimed:
        support += 1
        signals.append("REFERENCE_RECLAIMED")
    else:
        caution += 1
        signals.append("REFERENCE_NOT_RECLAIMED")

    if situation.last_structure_event_family == "reference-liquidity-sweep":
        support += 1
        signals.append("LATEST_REFERENCE_LIQUIDITY_SWEEP")
    else:
        signals.append(
            f"LATEST_STRUCTURE:{situation.last_structure_event_family}"
        )

    reclaim_age = situation.reference_reclaim_age_minutes
    if reclaim_age is not None:
        if 8 <= reclaim_age < 15:
            caution += 2
            signals.append("SEQUENCE_STALE_8_14")
        elif reclaim_age < 8:
            support += 1
            signals.append("SEQUENCE_FRESH_LT8")

    if (
        situation.recent_liquidity_event_count_10m is not None
        and situation.recent_liquidity_event_count_10m > 0
    ):
        support += 1
        signals.append("RECENT_LIQUIDITY_ACTIVITY")

    if _contains_any(
        situation.displacement_state,
        ("STRUCTURAL_CONFIRMATION", "DISPLACEMENT_CONFIRMED", "CONFIRMED"),
    ):
        support += 1
        signals.append("DISPLACEMENT_CONFIRMED")

    latency = situation.confirmation_latency_minutes
    if latency is not None:
        if latency <= 5:
            support += 1
            signals.append("CONFIRMATION_LATENCY_FAST")
        elif latency >= 11:
            caution += 2
            signals.append("CONFIRMATION_LATENCY_11M_PLUS")

    if _contains_any(
        situation.entry_evidence_freshness,
        ("FRESH", "CURRENT", "NEW"),
    ):
        support += 1
        signals.append("ENTRY_EVIDENCE_FRESH")
    elif _contains_any(
        situation.entry_evidence_freshness,
        ("STALE", "OLD", "EXPIRED"),
    ):
        caution += 1
        signals.append("ENTRY_EVIDENCE_STALE")

    for label, state in (
        ("CASH_OPEN", situation.cash_open_state),
        ("PREMARKET", situation.premarket_state),
    ):
        alignment = _direction_alignment(situation.side, state)
        if alignment > 0:
            support += 1
            signals.append(f"{label}_ALIGNED")
        elif alignment < 0:
            caution += 1
            signals.append(f"{label}_OPPOSED")

    signals.append(f"H1_OBSERVED:{situation.h1_state}")
    signals.append(f"H4_OBSERVED:{situation.h4_state}")
    signals.append(f"PRIOR_DAY_OBSERVED:{situation.prior_day_state}")
    signals.append(
        f"PRIOR_RANGE_LOCATION:{situation.position_in_prior_day_range}"
    )

    destination_state, destination_reasons = _destination_state(
        situation,
        entry_tier=entry_tier,
    )
    signals.extend(f"DESTINATION:{code}" for code in destination_reasons)
    if destination_state == "DEEP":
        support += 2
    elif destination_state == "SHALLOW":
        caution += 2

    exhaustion = _confirmed_exhaustion(situation.exhaustion_state)
    if exhaustion:
        caution += 4
        signals.append("JOURNEY_CONFIRMED_EXHAUSTION")

    extension_state = situation.extension_capacity_state
    if not _contains_any(
        extension_state,
        ("RESEARCH_ONLY", "UNCALIBRATED", "UNKNOWN", "UNRESOLVED"),
    ):
        if _contains_any(extension_state, ("SUPPORT", "DEEP", "EXPANSION")):
            support += 2
            signals.append("EXTENSION_CAPACITY_SUPPORTED")
        elif _contains_any(extension_state, ("DEPLET", "SHALLOW", "EXHAUST")):
            caution += 2
            signals.append("EXTENSION_CAPACITY_DEPLETED")

    cross = situation.cross_index_state
    if _contains_any(cross, ("SAME_SIDE", "ALIGNED", "CONFIRMED_EXPECTED")):
        support += 1
        signals.append("INTERMARKET_ALIGNED")
    elif _contains_any(cross, ("OPPOSITE", "AGAINST_EXPECTED")):
        caution += 2
        signals.append("INTERMARKET_OPPOSITE")
    elif _contains_any(cross, ("DIVERGENT", "MIXED")):
        caution += 1
        signals.append("INTERMARKET_DIVERGENT")
    else:
        signals.append(f"INTERMARKET_OBSERVED:{cross}")

    dol1_reached = _dol1_reached(situation.dol1_state)
    if dol1_reached:
        signals.append("DOL1_REACHED")
        if situation.decision_minute_ny >= 14 * 60:
            caution += 2
            signals.append("LATE_SESSION_EXTENSION_DEPLETED")
        elif situation.decision_minute_ny < 12 * 60:
            support += 1
            signals.append("EARLY_SESSION_EXTENSION_WINDOW")

    if exhaustion or reasoning.action != "EXECUTE":
        context = ManagementContext.CAUTIOUS
    elif support - caution >= 3:
        context = ManagementContext.SUPPORTIVE
    elif caution - support >= 2:
        context = ManagementContext.CAUTIOUS
    else:
        context = ManagementContext.MIXED

    urgency = (
        ProtectionUrgency.HIGH
        if context is ManagementContext.CAUTIOUS
        else (
            ProtectionUrgency.MODERATE
            if context is ManagementContext.MIXED
            else ProtectionUrgency.LOW
        )
    )

    if exhaustion:
        target_intent = UniversalTargetIntent.EXIT_ON_CONFIRMED_EXHAUSTION
    elif (
        dol1_reached
        and destination_state == "DEEP"
        and dol1_acceptance_observed is True
        and context is not ManagementContext.CAUTIOUS
    ):
        target_intent = UniversalTargetIntent.EXTEND_TO_DOL2
    else:
        target_intent = UniversalTargetIntent.PRESERVE_DOL1

    return FullCognitivePositionState(
        management_context=context,
        destination_state=destination_state,
        target_intent=target_intent,
        protection_urgency=urgency,
        support_score=support,
        caution_score=caution,
        signal_codes=tuple(dict.fromkeys(signals)),
        observed_domains=observed_domains,
        observed_situation_fields=observed_situation_fields,
        actuated_situation_fields=actuated_situation_fields,
        observation_only_situation_fields=observation_only_situation_fields,
        cognitive_coverage_ratio=coverage_ratio,
        entry_situation_fingerprint=bound_entry_fingerprint,
        current_situation_fingerprint=current_fingerprint,
        post_entry_reassessment=post_entry_reassessment,
        memory_fingerprint=reasoning.memory_fingerprint,
        entry_tier=entry_tier,
        dol1_acceptance_observed=dol1_acceptance_observed,
    )
