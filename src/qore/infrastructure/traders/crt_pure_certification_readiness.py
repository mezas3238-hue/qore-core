"""Fail-closed certification readiness for VT08 CRT PURE.

Software quality, source discovery and research replay are necessary but never sufficient
to certify a trader.  This gate keeps methodology, market evidence and economic validation
as independent authorities and requires all of them before CERTIFIED can be reached.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.traders.crt_pure_strategy_identity_memory import (
    strategy_identity_ready,
)


class CrtPureCertificationStage(StrEnum):
    SOURCE_OPEN = "SOURCE_OPEN"
    MARKET_EVIDENCE_OPEN = "MARKET_EVIDENCE_OPEN"
    REPLAY_RESEARCH = "REPLAY_RESEARCH"
    CANDIDATE_FREEZE_READY = "CANDIDATE_FREEZE_READY"
    INDEPENDENT_VALIDATION = "INDEPENDENT_VALIDATION"
    CERTIFIED = "CERTIFIED"


@dataclass(frozen=True, slots=True)
class CrtPureCertificationEvidence:
    """Exact evidence gates; no individual flag grants trading authority."""

    source_identity_closed: bool
    audusd_history_verified: bool
    usdjpy_history_verified: bool
    btcusd_history_verified: bool
    deterministic_replay_green: bool = False
    per_market_forensics_closed: bool = False
    exact_candidate_frozen: bool = False
    walk_forward_green: bool = False
    monte_carlo_green: bool = False
    stress_green: bool = False
    slippage_green: bool = False
    robustness_green: bool = False
    fresh_holdout_green: bool = False
    combined_three_market_validation_green: bool = False
    full_qore_green: bool = False

    @property
    def all_market_history_verified(self) -> bool:
        return (
            self.audusd_history_verified
            and self.usdjpy_history_verified
            and self.btcusd_history_verified
        )

    @property
    def all_independent_validation_green(self) -> bool:
        return (
            self.walk_forward_green
            and self.monte_carlo_green
            and self.stress_green
            and self.slippage_green
            and self.robustness_green
            and self.fresh_holdout_green
            and self.combined_three_market_validation_green
            and self.full_qore_green
        )


@dataclass(frozen=True, slots=True)
class CrtPureCertificationReadiness:
    stage: CrtPureCertificationStage
    blockers: tuple[str, ...]
    certified: bool = False
    demo_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    production_authorized: bool = False

    def __post_init__(self) -> None:
        if self.certified is not (self.stage is CrtPureCertificationStage.CERTIFIED):
            raise ValueError("certified flag must match certification stage")
        if (
            self.demo_authorized
            or self.live_authorized
            or self.real_capital_authorized
            or self.production_authorized
        ):
            raise ValueError("certification readiness cannot grant deployment authority")


def evaluate_certification_readiness(
    evidence: CrtPureCertificationEvidence,
) -> CrtPureCertificationReadiness:
    """Return the furthest evidence-supported stage without skipping any authority."""

    blockers: list[str] = []

    if not evidence.source_identity_closed or not strategy_identity_ready():
        blockers.append("CRT_PRIMARY_SOURCE_AND_STRATEGY_IDENTITY_NOT_CLOSED")
        return CrtPureCertificationReadiness(
            stage=CrtPureCertificationStage.SOURCE_OPEN,
            blockers=tuple(blockers),
        )

    if not evidence.all_market_history_verified:
        if not evidence.audusd_history_verified:
            blockers.append("AUDUSD_HISTORY_NOT_VERIFIED")
        if not evidence.usdjpy_history_verified:
            blockers.append("USDJPY_HISTORY_NOT_VERIFIED")
        if not evidence.btcusd_history_verified:
            blockers.append("BTCUSD_HISTORY_NOT_VERIFIED")
        return CrtPureCertificationReadiness(
            stage=CrtPureCertificationStage.MARKET_EVIDENCE_OPEN,
            blockers=tuple(blockers),
        )

    if not evidence.deterministic_replay_green or not evidence.per_market_forensics_closed:
        if not evidence.deterministic_replay_green:
            blockers.append("DETERMINISTIC_REPLAY_NOT_GREEN")
        if not evidence.per_market_forensics_closed:
            blockers.append("PER_MARKET_FORENSICS_NOT_CLOSED")
        return CrtPureCertificationReadiness(
            stage=CrtPureCertificationStage.REPLAY_RESEARCH,
            blockers=tuple(blockers),
        )

    if not evidence.exact_candidate_frozen:
        return CrtPureCertificationReadiness(
            stage=CrtPureCertificationStage.CANDIDATE_FREEZE_READY,
            blockers=("EXACT_CANDIDATE_NOT_FROZEN",),
        )

    if not evidence.all_independent_validation_green:
        for name, passed in (
            ("WALK_FORWARD_NOT_GREEN", evidence.walk_forward_green),
            ("MONTE_CARLO_NOT_GREEN", evidence.monte_carlo_green),
            ("STRESS_NOT_GREEN", evidence.stress_green),
            ("SLIPPAGE_NOT_GREEN", evidence.slippage_green),
            ("ROBUSTNESS_NOT_GREEN", evidence.robustness_green),
            ("FRESH_HOLDOUT_NOT_GREEN", evidence.fresh_holdout_green),
            (
                "THREE_MARKET_VALIDATION_NOT_GREEN",
                evidence.combined_three_market_validation_green,
            ),
            ("FULL_QORE_NOT_GREEN", evidence.full_qore_green),
        ):
            if not passed:
                blockers.append(name)
        return CrtPureCertificationReadiness(
            stage=CrtPureCertificationStage.INDEPENDENT_VALIDATION,
            blockers=tuple(blockers),
        )

    return CrtPureCertificationReadiness(
        stage=CrtPureCertificationStage.CERTIFIED,
        blockers=(),
        certified=True,
    )
