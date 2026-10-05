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


class SingleUnitTargetIntent(StrEnum):
    """Causal target intent that remains executable when total volume is 0.01."""

    PRESERVE_DOL1 = "PRESERVE_DOL1"
    EXTEND_FULL_UNIT_TO_DOL2 = "EXTEND_FULL_UNIT_TO_DOL2"
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
    target_intent: SingleUnitTargetIntent
    protection_urgency: ProtectionUrgency
    support_score: int
    caution_score: int
    signal_codes: tuple[str, ...]
    observed_domains: tuple[str, ...]
    situation_fingerprint: str
    memory_fingerprint: str
    entry_tier: str | None
    dol1_acceptance_observed: bool | None
    minimum_volume_compatible: Decimal = Decimal("0.01")
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
    situation: "Nas100SituationModel",
    reasoning: Nas100ReasoningDecision,
    entry_tier: str | None = None,
    dol1_acceptance_observed: bool | None = None,
) -> FullCognitivePositionState:
    """Synthesize all causal VT31 cognitive domains into one position state."""

    if reasoning.situation_fingerprint != situation.fingerprint():
        raise ValueError("reasoning/situation fingerprint mismatch")

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
        target_intent = SingleUnitTargetIntent.EXIT_ON_CONFIRMED_EXHAUSTION
    elif (
        dol1_reached
        and destination_state == "DEEP"
        and dol1_acceptance_observed is True
        and context is not ManagementContext.CAUTIOUS
    ):
        target_intent = SingleUnitTargetIntent.EXTEND_FULL_UNIT_TO_DOL2
    else:
        target_intent = SingleUnitTargetIntent.PRESERVE_DOL1

    return FullCognitivePositionState(
        management_context=context,
        destination_state=destination_state,
        target_intent=target_intent,
        protection_urgency=urgency,
        support_score=support,
        caution_score=caution,
        signal_codes=tuple(dict.fromkeys(signals)),
        observed_domains=observed_domains,
        situation_fingerprint=situation.fingerprint(),
        memory_fingerprint=reasoning.memory_fingerprint,
        entry_tier=entry_tier,
        dol1_acceptance_observed=dol1_acceptance_observed,
    )
