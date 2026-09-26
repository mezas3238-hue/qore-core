"""Market-specific Stop Cognitive Engine for QORE Capitalizer.

Architecture:

    M1 ENTRY CONTRACT -> STOP INTELLIGENCE -> QORE RISK -> EXECUTION

The engine does not change the ICT/TTrades entry methodology and does not grant capital
authority. It separates three concerns:

1. Structural Brain: where the trade thesis is structurally invalidated.
2. Market Memory Brain: what the same market has historically required to express
   equivalent structure.
3. Adversarial Brain: whether a proposed buffer is justified or merely attempts to rescue
   a weak entry.

The current consumed 5Y holdout can seed market memory, but cannot become a new fresh
holdout. Broad stop-recovery evidence alone is never sufficient to authorize a buffer.
An exact pre-trade state-family profile must be frozen and independently falsified.

After entry, a stop may HOLD or IMPROVE. It may never WIDEN.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    market_is_allowed,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    NINE_MARKET_UNIVERSE,
)

IDENTITY = "QORE_CAPITALIZER_MARKET_STOP_COGNITIVE_ENGINE_V1"
MEMORY_IDENTITY = "QORE_CAPITALIZER_MARKET_STOP_MEMORY_V1"
MEMORY_MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_STOP_MEMORY_MATRIX_V1"
FORENSIC_IDENTITY = "QORE_CAPITALIZER_M1_LOSS_CAUSAL_FORENSICS_V1"


class CapitalizerStopAnchor(StrEnum):
    M1_PROTECTED_SWING = "M1_PROTECTED_SWING"
    M1_VALIDATED_OB_EXTREME = "M1_VALIDATED_OB_EXTREME"
    M1_MSS_ORIGIN_EXTREME = "M1_MSS_ORIGIN_EXTREME"


class CapitalizerStopConfidence(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class CapitalizerBreathingState(StrEnum):
    NORMAL = "NORMAL"
    MARKET_SPECIFIC_CANDIDATE = "MARKET_SPECIFIC_CANDIDATE"
    UNRESOLVED = "UNRESOLVED"


class CapitalizerBufferEvidenceKind(StrEnum):
    STRUCTURAL_EQUIVALENT_EXCURSION = "STRUCTURAL_EQUIVALENT_EXCURSION"
    SPREAD_TICK_MICROSTRUCTURE = "SPREAD_TICK_MICROSTRUCTURE"
    RECOVERY_ONLY = "RECOVERY_ONLY"


class CapitalizerStopDecision(StrEnum):
    STRUCTURAL_STOP = "STRUCTURAL_STOP"
    STRUCTURAL_STOP_WITH_CANDIDATE_BREATHING = (
        "STRUCTURAL_STOP_WITH_CANDIDATE_BREATHING"
    )
    WAIT_STOP_EVIDENCE = "WAIT_STOP_EVIDENCE"
    STOP_GEOMETRY_UNACCEPTABLE = "STOP_GEOMETRY_UNACCEPTABLE"


class CapitalizerPostEntryStopAction(StrEnum):
    HOLD = "HOLD"
    IMPROVE = "IMPROVE"
    REJECT_WIDENING = "REJECT_WIDENING"


@dataclass(frozen=True, slots=True)
class CapitalizerMarketStopMemory:
    identity: str
    symbol: str
    session: CapitalizerSession
    source_forensic_identity: str
    source_trade_count: int
    stop_count: int
    same_session_target_recovery_rate: Decimal
    median_extra_stop_r_recovered: Decimal | None
    p75_extra_stop_r_recovered: Decimal | None
    p90_extra_stop_r_recovered: Decimal | None
    cross_feature_loss_higher: tuple[str, ...]
    evidence_status: str
    exact_state_family_profiles_present: bool = False
    executable_buffer_frozen: bool = False
    holdout_fresh_after_memory_build: bool = False
    runtime_mutation_allowed: bool = False

    def __post_init__(self) -> None:
        if self.identity != MEMORY_IDENTITY:
            raise ValueError("unexpected stop-memory identity")
        if not market_is_allowed(session=self.session, symbol=self.symbol):
            raise ValueError("stop memory market/session drift")
        if self.source_trade_count <= 0 or self.stop_count < 0:
            raise ValueError("stop memory counts must be valid")
        if not Decimal("0") <= self.same_session_target_recovery_rate <= Decimal("1"):
            raise ValueError("stop recovery rate must be in [0, 1]")
        if self.executable_buffer_frozen and not self.exact_state_family_profiles_present:
            raise ValueError("an executable buffer requires exact state-family profiles")
        if self.holdout_fresh_after_memory_build:
            raise ValueError("consumed forensic evidence cannot remain a fresh holdout")
        if self.runtime_mutation_allowed:
            raise ValueError("market stop memory cannot self-train in runtime")


@dataclass(frozen=True, slots=True)
class CapitalizerStopStateFamilyProfile:
    symbol: str
    session: CapitalizerSession
    state_family_id: str
    observations: int
    candidate_buffer_ticks: Decimal
    evidence_kind: CapitalizerBufferEvidenceKind
    replay_frozen: bool
    fresh_holdout_consumed: bool
    runtime_mutation_allowed: bool = False

    def __post_init__(self) -> None:
        if not market_is_allowed(session=self.session, symbol=self.symbol):
            raise ValueError("state-family stop profile market/session drift")
        if not self.state_family_id:
            raise ValueError("state_family_id must be non-empty")
        if self.observations <= 0:
            raise ValueError("state-family profile requires observations")
        if self.candidate_buffer_ticks < 0:
            raise ValueError("candidate buffer cannot be negative")
        if self.runtime_mutation_allowed:
            raise ValueError("state-family stop profile cannot mutate in runtime")


@dataclass(frozen=True, slots=True)
class CapitalizerMarketStopSpecialist:
    symbol: str
    session: CapitalizerSession
    memory: CapitalizerMarketStopMemory
    state_profiles: tuple[CapitalizerStopStateFamilyProfile, ...] = ()

    def __post_init__(self) -> None:
        if self.memory.symbol != self.symbol or self.memory.session is not self.session:
            raise ValueError("specialist memory identity mismatch")
        if not market_is_allowed(session=self.session, symbol=self.symbol):
            raise ValueError("invalid specialist market/session")
        keys = tuple(profile.state_family_id for profile in self.state_profiles)
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate state-family stop profiles")
        for profile in self.state_profiles:
            if profile.symbol != self.symbol or profile.session is not self.session:
                raise ValueError("state-family profile belongs to another market")

    def state_profile(
        self,
        state_family_id: str,
    ) -> CapitalizerStopStateFamilyProfile | None:
        matches = tuple(
            profile
            for profile in self.state_profiles
            if profile.state_family_id == state_family_id
        )
        if len(matches) > 1:
            raise ValueError("duplicate state-family profiles")
        return matches[0] if matches else None


@dataclass(frozen=True, slots=True)
class CapitalizerMarketStopSpecialistRegistry:
    specialists: tuple[CapitalizerMarketStopSpecialist, ...]

    def __post_init__(self) -> None:
        symbols = tuple(item.symbol for item in self.specialists)
        if len(symbols) != 9 or frozenset(symbols) != NINE_MARKET_UNIVERSE:
            raise ValueError("stop specialist registry requires frozen nine-market universe")
        if len(set(symbols)) != 9:
            raise ValueError("stop specialist registry cannot contain duplicates")

    def get(self, symbol: str) -> CapitalizerMarketStopSpecialist:
        normalized = symbol.upper()
        matches = tuple(item for item in self.specialists if item.symbol == normalized)
        if len(matches) != 1:
            raise KeyError(f"unknown stop specialist: {normalized}")
        return matches[0]


@dataclass(frozen=True, slots=True)
class CapitalizerStopStructuralFacts:
    symbol: str
    session: CapitalizerSession
    side: CapitalizerSide
    state_family_id: str
    entry_price: Decimal
    target_price: Decimal
    m1_protected_swing_price: Decimal | None
    m1_mss_origin_price: Decimal
    m1_order_block_low: Decimal
    m1_order_block_high: Decimal
    m1_fvg_low: Decimal
    m1_fvg_high: Decimal
    liquidity_raid_level: Decimal
    tick_size: Decimal
    spread_ticks: Decimal
    volatility_ticks: Decimal
    session_elapsed_minutes: int
    fresh_repeat_state: str
    reclaim_state: str
    displacement_state: str
    expansion_speed_state: str

    def __post_init__(self) -> None:
        if not market_is_allowed(session=self.session, symbol=self.symbol):
            raise ValueError("stop facts market/session drift")
        if not self.state_family_id:
            raise ValueError("stop facts require state_family_id")
        values = (
            self.entry_price,
            self.target_price,
            self.m1_mss_origin_price,
            self.m1_order_block_low,
            self.m1_order_block_high,
            self.m1_fvg_low,
            self.m1_fvg_high,
            self.liquidity_raid_level,
            self.tick_size,
            self.spread_ticks,
            self.volatility_ticks,
        )
        if any(not value.is_finite() for value in values):
            raise ValueError("stop facts must be finite")
        if self.m1_protected_swing_price is not None:
            if not self.m1_protected_swing_price.is_finite():
                raise ValueError("protected swing must be finite")
        if self.tick_size <= 0 or self.spread_ticks < 0 or self.volatility_ticks < 0:
            raise ValueError("tick/spread/volatility geometry must be non-negative")
        if self.m1_order_block_low >= self.m1_order_block_high:
            raise ValueError("order block low must be below high")
        if self.m1_fvg_low >= self.m1_fvg_high:
            raise ValueError("FVG low must be below high")
        if self.session_elapsed_minutes < 0:
            raise ValueError("session elapsed minutes cannot be negative")


@dataclass(frozen=True, slots=True)
class CapitalizerStructuralStopAssessment:
    anchor: CapitalizerStopAnchor | None
    structural_stop_price: Decimal | None
    confidence: CapitalizerStopConfidence
    structurally_valid: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CapitalizerMarketMemoryStopAssessment:
    breathing_state: CapitalizerBreathingState
    exact_state_profile_found: bool
    candidate_buffer_ticks: Decimal
    evidence_kind: CapitalizerBufferEvidenceKind | None
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CapitalizerStopAdversarialAssessment:
    widening_rejected: bool
    findings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CapitalizerStopProposal:
    identity: str
    symbol: str
    session: str
    side: str
    decision: CapitalizerStopDecision
    invalidation_anchor: str | None
    structural_stop_price: Decimal | None
    execution_buffer_ticks: Decimal
    final_stop_price: Decimal | None
    stop_confidence: CapitalizerStopConfidence
    expected_breathing: CapitalizerBreathingState
    reasons: tuple[str, ...]
    adversarial_findings: tuple[str, ...]
    qore_risk_approval_required: bool = True
    grants_capital_authority: bool = False
    entry_methodology_changed: bool = False
    post_entry_widening_allowed: bool = False
    rule_promotion_allowed: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("unexpected stop cognitive engine identity")
        if self.grants_capital_authority:
            raise ValueError("stop cognition cannot grant capital authority")
        if self.entry_methodology_changed:
            raise ValueError("stop cognition cannot mutate entry methodology")
        if self.post_entry_widening_allowed:
            raise ValueError("post-entry stop widening is forbidden")
        if self.rule_promotion_allowed:
            raise ValueError("V1 research engine cannot promote stop rules")
        if self.live_authorized or self.real_capital_authorized:
            raise ValueError("research stop engine cannot authorize live capital")


@dataclass(frozen=True, slots=True)
class CapitalizerPostEntryStopAssessment:
    action: CapitalizerPostEntryStopAction
    current_stop_price: Decimal
    requested_stop_price: Decimal
    reasons: tuple[str, ...]


def assess_structural_stop(
    facts: CapitalizerStopStructuralFacts,
) -> CapitalizerStructuralStopAssessment:
    """Locate invalidation using source-first M1 structure."""

    long_side = facts.side is CapitalizerSide.LONG
    target_valid = (
        facts.target_price > facts.entry_price
        if long_side
        else facts.target_price < facts.entry_price
    )
    if not target_valid:
        return CapitalizerStructuralStopAssessment(
            anchor=None,
            structural_stop_price=None,
            confidence=CapitalizerStopConfidence.LOW,
            structurally_valid=False,
            reasons=("TARGET_NOT_ON_PROFIT_SIDE",),
        )

    protected = facts.m1_protected_swing_price
    if protected is None:
        return CapitalizerStructuralStopAssessment(
            anchor=None,
            structural_stop_price=None,
            confidence=CapitalizerStopConfidence.LOW,
            structurally_valid=False,
            reasons=(
                "M1_PROTECTED_SWING_UNRESOLVED",
                "SOURCE_DEFAULT_INVALIDATION_ANCHOR_MISSING",
            ),
        )

    protected_valid = protected < facts.entry_price if long_side else protected > facts.entry_price
    if not protected_valid:
        return CapitalizerStructuralStopAssessment(
            anchor=CapitalizerStopAnchor.M1_PROTECTED_SWING,
            structural_stop_price=protected,
            confidence=CapitalizerStopConfidence.LOW,
            structurally_valid=False,
            reasons=("PROTECTED_SWING_NOT_ON_INVALIDATION_SIDE",),
        )

    ob_extreme = facts.m1_order_block_low if long_side else facts.m1_order_block_high
    mss_origin = facts.m1_mss_origin_price
    confirmations = 0
    reasons = ["PROTECTED_SWING_SOURCE_DEFAULT_INVALIDATION"]
    if (ob_extreme <= protected) if long_side else (ob_extreme >= protected):
        confirmations += 1
        reasons.append("VALIDATED_OB_EXTREME_CORROBORATES_INVALIDATION")
    else:
        reasons.append("VALIDATED_OB_EXTREME_INSIDE_PROTECTED_SWING")
    if (mss_origin <= protected) if long_side else (mss_origin >= protected):
        confirmations += 1
        reasons.append("MSS_ORIGIN_CORROBORATES_INVALIDATION")
    else:
        reasons.append("MSS_ORIGIN_INSIDE_PROTECTED_SWING")

    confidence = (
        CapitalizerStopConfidence.HIGH
        if confirmations == 2
        else CapitalizerStopConfidence.MEDIUM
    )
    return CapitalizerStructuralStopAssessment(
        anchor=CapitalizerStopAnchor.M1_PROTECTED_SWING,
        structural_stop_price=protected,
        confidence=confidence,
        structurally_valid=True,
        reasons=tuple(reasons),
    )


def assess_market_memory_stop(
    *,
    facts: CapitalizerStopStructuralFacts,
    specialist: CapitalizerMarketStopSpecialist,
) -> CapitalizerMarketMemoryStopAssessment:
    """Read exact market/state memory without learning in runtime."""

    profile = specialist.state_profile(facts.state_family_id)
    if profile is None:
        return CapitalizerMarketMemoryStopAssessment(
            breathing_state=CapitalizerBreathingState.NORMAL,
            exact_state_profile_found=False,
            candidate_buffer_ticks=Decimal("0"),
            evidence_kind=None,
            reasons=(
                "NO_EXACT_STATE_FAMILY_BUFFER_FROZEN",
                "BROAD_MARKET_MEMORY_CANNOT_AUTHORIZE_WIDENING",
            ),
        )

    if not profile.replay_frozen:
        return CapitalizerMarketMemoryStopAssessment(
            breathing_state=CapitalizerBreathingState.UNRESOLVED,
            exact_state_profile_found=True,
            candidate_buffer_ticks=Decimal("0"),
            evidence_kind=profile.evidence_kind,
            reasons=("STATE_FAMILY_PROFILE_NOT_FROZEN_FOR_REPLAY",),
        )

    if profile.candidate_buffer_ticks == 0:
        return CapitalizerMarketMemoryStopAssessment(
            breathing_state=CapitalizerBreathingState.NORMAL,
            exact_state_profile_found=True,
            candidate_buffer_ticks=Decimal("0"),
            evidence_kind=profile.evidence_kind,
            reasons=("EXACT_STATE_FAMILY_REQUIRES_NO_EXTRA_BREATHING",),
        )

    return CapitalizerMarketMemoryStopAssessment(
        breathing_state=CapitalizerBreathingState.MARKET_SPECIFIC_CANDIDATE,
        exact_state_profile_found=True,
        candidate_buffer_ticks=profile.candidate_buffer_ticks,
        evidence_kind=profile.evidence_kind,
        reasons=("EXACT_MARKET_STATE_FAMILY_BUFFER_CANDIDATE",),
    )


def assess_stop_adversarially(
    *,
    structural: CapitalizerStructuralStopAssessment,
    memory: CapitalizerMarketMemoryStopAssessment,
) -> CapitalizerStopAdversarialAssessment:
    """Reject buffer logic that merely rescues historical losers."""

    findings: list[str] = []
    reject = False
    if not structural.structurally_valid:
        findings.append("STRUCTURAL_INVALIDATION_UNRESOLVED")
    if memory.candidate_buffer_ticks > 0 and not memory.exact_state_profile_found:
        reject = True
        findings.append("BUFFER_WITHOUT_EXACT_STATE_FAMILY")
    if memory.evidence_kind is CapitalizerBufferEvidenceKind.RECOVERY_ONLY:
        reject = True
        findings.append("REJECT_STOP_WIDENING_RECOVERY_ONLY_EVIDENCE")
    if (
        memory.breathing_state is CapitalizerBreathingState.MARKET_SPECIFIC_CANDIDATE
        and memory.evidence_kind is None
    ):
        reject = True
        findings.append("BUFFER_EVIDENCE_KIND_UNRESOLVED")
    if not findings:
        findings.append("NO_ADVERSARIAL_STOP_CONTRADICTION")
    return CapitalizerStopAdversarialAssessment(
        widening_rejected=reject,
        findings=tuple(findings),
    )


def evaluate_market_stop(
    *,
    facts: CapitalizerStopStructuralFacts,
    specialist: CapitalizerMarketStopSpecialist,
) -> CapitalizerStopProposal:
    """Create a pre-entry stop proposal while preserving QORE Risk sovereignty."""

    if specialist.symbol != facts.symbol or specialist.session is not facts.session:
        raise ValueError("stop specialist does not match candidate market/session")

    structural = assess_structural_stop(facts)
    memory = assess_market_memory_stop(facts=facts, specialist=specialist)
    adversarial = assess_stop_adversarially(structural=structural, memory=memory)

    if not structural.structurally_valid or structural.structural_stop_price is None:
        return CapitalizerStopProposal(
            identity=IDENTITY,
            symbol=facts.symbol,
            session=facts.session.value,
            side=facts.side.value,
            decision=CapitalizerStopDecision.WAIT_STOP_EVIDENCE,
            invalidation_anchor=None if structural.anchor is None else structural.anchor.value,
            structural_stop_price=structural.structural_stop_price,
            execution_buffer_ticks=Decimal("0"),
            final_stop_price=structural.structural_stop_price,
            stop_confidence=structural.confidence,
            expected_breathing=CapitalizerBreathingState.UNRESOLVED,
            reasons=structural.reasons,
            adversarial_findings=adversarial.findings,
        )

    buffer_ticks = memory.candidate_buffer_ticks
    if adversarial.widening_rejected:
        buffer_ticks = Decimal("0")

    buffer_price = buffer_ticks * facts.tick_size
    if facts.side is CapitalizerSide.LONG:
        final_stop = structural.structural_stop_price - buffer_price
    else:
        final_stop = structural.structural_stop_price + buffer_price

    decision = CapitalizerStopDecision.STRUCTURAL_STOP
    breathing = CapitalizerBreathingState.NORMAL
    if buffer_ticks > 0:
        decision = CapitalizerStopDecision.STRUCTURAL_STOP_WITH_CANDIDATE_BREATHING
        breathing = CapitalizerBreathingState.MARKET_SPECIFIC_CANDIDATE

    reasons = (*structural.reasons, *memory.reasons)
    if adversarial.widening_rejected:
        reasons = (*reasons, "REJECT_STOP_WIDENING_USE_STRUCTURAL_STOP_ONLY")

    return CapitalizerStopProposal(
        identity=IDENTITY,
        symbol=facts.symbol,
        session=facts.session.value,
        side=facts.side.value,
        decision=decision,
        invalidation_anchor=structural.anchor.value if structural.anchor else None,
        structural_stop_price=structural.structural_stop_price,
        execution_buffer_ticks=buffer_ticks,
        final_stop_price=final_stop,
        stop_confidence=structural.confidence,
        expected_breathing=breathing,
        reasons=reasons,
        adversarial_findings=adversarial.findings,
    )


def apply_qore_risk_stop_decision(
    proposal: CapitalizerStopProposal,
    *,
    approved: bool,
    reason: str,
) -> CapitalizerStopProposal:
    """Apply downstream QORE Risk verdict without letting cognition size capital."""

    if approved:
        return proposal
    return CapitalizerStopProposal(
        identity=proposal.identity,
        symbol=proposal.symbol,
        session=proposal.session,
        side=proposal.side,
        decision=CapitalizerStopDecision.STOP_GEOMETRY_UNACCEPTABLE,
        invalidation_anchor=proposal.invalidation_anchor,
        structural_stop_price=proposal.structural_stop_price,
        execution_buffer_ticks=proposal.execution_buffer_ticks,
        final_stop_price=proposal.final_stop_price,
        stop_confidence=proposal.stop_confidence,
        expected_breathing=proposal.expected_breathing,
        reasons=(*proposal.reasons, f"QORE_RISK_REJECTED_STOP_GEOMETRY:{reason}"),
        adversarial_findings=proposal.adversarial_findings,
    )


def assess_post_entry_stop_transition(
    *,
    side: CapitalizerSide,
    current_stop_price: Decimal,
    requested_stop_price: Decimal,
) -> CapitalizerPostEntryStopAssessment:
    """Enforce HOLD/IMPROVE only after entry; widening is impossible."""

    if side is CapitalizerSide.LONG:
        if requested_stop_price < current_stop_price:
            action = CapitalizerPostEntryStopAction.REJECT_WIDENING
            reasons = ("LONG_STOP_CANNOT_MOVE_LOWER_AFTER_ENTRY",)
        elif requested_stop_price > current_stop_price:
            action = CapitalizerPostEntryStopAction.IMPROVE
            reasons = ("LONG_STOP_IMPROVES_MONOTONICALLY",)
        else:
            action = CapitalizerPostEntryStopAction.HOLD
            reasons = ("STOP_UNCHANGED",)
    else:
        if requested_stop_price > current_stop_price:
            action = CapitalizerPostEntryStopAction.REJECT_WIDENING
            reasons = ("SHORT_STOP_CANNOT_MOVE_HIGHER_AFTER_ENTRY",)
        elif requested_stop_price < current_stop_price:
            action = CapitalizerPostEntryStopAction.IMPROVE
            reasons = ("SHORT_STOP_IMPROVES_MONOTONICALLY",)
        else:
            action = CapitalizerPostEntryStopAction.HOLD
            reasons = ("STOP_UNCHANGED",)
    return CapitalizerPostEntryStopAssessment(
        action=action,
        current_stop_price=current_stop_price,
        requested_stop_price=requested_stop_price,
        reasons=reasons,
    )


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def build_market_memory(forensic: dict[str, Any]) -> CapitalizerMarketStopMemory:
    """Convert consumed M1 forensics into broad non-executable market memory."""

    if forensic.get("identity") != FORENSIC_IDENTITY:
        raise ValueError("unexpected M1 forensic identity")
    if forensic.get("evidence_status") != "CONSUMED_FORENSIC_EVIDENCE":
        raise ValueError("stop memory requires consumed forensic evidence")
    symbol = str(forensic["symbol"])
    session = CapitalizerSession(str(forensic["session"]))
    stop = forensic.get("stop_intelligence")
    if not isinstance(stop, dict):
        raise ValueError("forensic report missing stop intelligence")
    medians = forensic.get("winner_loser_feature_medians")
    if not isinstance(medians, dict):
        raise ValueError("forensic report missing feature medians")
    loss_higher = tuple(
        sorted(
            str(feature)
            for feature, data in medians.items()
            if isinstance(data, dict) and data.get("direction") == "LOSS_HIGHER"
        )
    )
    return CapitalizerMarketStopMemory(
        identity=MEMORY_IDENTITY,
        symbol=symbol,
        session=session,
        source_forensic_identity=FORENSIC_IDENTITY,
        source_trade_count=int(forensic["source_trade_count"]),
        stop_count=int(stop["stops"]),
        same_session_target_recovery_rate=Decimal(str(stop["target_recovery_rate"])),
        median_extra_stop_r_recovered=_decimal_or_none(
            stop.get("median_extra_stop_r_needed_for_recovered")
        ),
        p75_extra_stop_r_recovered=_decimal_or_none(
            stop.get("p75_extra_stop_r_needed_for_recovered")
        ),
        p90_extra_stop_r_recovered=_decimal_or_none(
            stop.get("p90_extra_stop_r_needed_for_recovered")
        ),
        cross_feature_loss_higher=loss_higher,
        evidence_status="CONSUMED_FORENSIC_EVIDENCE",
    )


def _one_forensic(root: Path) -> dict[str, Any]:
    paths = sorted(root.rglob("capitalizer-*-m1-loss-causal-forensics-v1.json"))
    if len(paths) != 1:
        raise ValueError(f"expected one market forensic report, got {len(paths)}")
    raw = json.loads(paths[0].read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("forensic report must be JSON object")
    return raw


def write_market_memory(memory: CapitalizerMarketStopMemory, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{memory.symbol.lower()}-market-stop-memory-v1.json"
    payload = asdict(memory)
    payload["session"] = memory.session.value
    payload["same_session_target_recovery_rate"] = str(
        memory.same_session_target_recovery_rate
    )
    for key in (
        "median_extra_stop_r_recovered",
        "p75_extra_stop_r_recovered",
        "p90_extra_stop_r_recovered",
    ):
        value = getattr(memory, key)
        payload[key] = None if value is None else str(value)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_memory_matrix(root: Path) -> dict[str, Any]:
    paths = sorted(root.rglob("capitalizer-*-market-stop-memory-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"nine-market stop memory requires 9 reports, got {len(paths)}")
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    symbols = {str(item["symbol"]) for item in reports}
    if symbols != set(NINE_MARKET_UNIVERSE):
        raise ValueError("nine-market stop memory universe mismatch")
    return {
        "identity": MEMORY_MATRIX_IDENTITY,
        "market_count": 9,
        "symbols": sorted(symbols),
        "total_consumed_trades": sum(int(item["source_trade_count"]) for item in reports),
        "total_stops": sum(int(item["stop_count"]) for item in reports),
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "exact_state_family_profiles_present": False,
        "executable_buffer_frozen": False,
        "runtime_mutation_allowed": False,
        "methodology_changed": False,
        "qore_risk_sovereign": True,
        "post_entry_widening_allowed": False,
        "economic_candidate": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_memory_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-stop-memory-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    memory = sub.add_parser("memory")
    memory.add_argument("forensic_root", type=Path)
    memory.add_argument("output", type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "memory":
        result = build_market_memory(_one_forensic(args.forensic_root))
        write_market_memory(result, args.output)
        print(
            json.dumps(
                {
                    "identity": result.identity,
                    "symbol": result.symbol,
                    "trades": result.source_trade_count,
                    "stops": result.stop_count,
                    "recovery_rate": str(result.same_session_target_recovery_rate),
                    "executable_buffer_frozen": result.executable_buffer_frozen,
                },
                sort_keys=True,
            )
        )
        return

    report = build_memory_matrix(args.input_root)
    write_memory_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
