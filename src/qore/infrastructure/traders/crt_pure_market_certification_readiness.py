"""Fail-closed per-market research certification for VT08 CRT PURE.

The existing CRT readiness gate intentionally governs the combined three-market
trader. This module adds the missing independent per-market seam required by the
research contract:

    certify markets independently -> only certified markets may later enter
    combined-portfolio validation.

Per-market research certification is evidence status only. It never grants DEMO,
LIVE, production or real-capital authority and never substitutes for external
Risk/CIBO/independent-validation evidence required by Trader Lab promotion.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


class CrtPureMarketCertificationStage(StrEnum):
    HISTORY_OPEN = "HISTORY_OPEN"
    CANDIDATE_OPEN = "CANDIDATE_OPEN"
    INDEPENDENT_VALIDATION = "INDEPENDENT_VALIDATION"
    ROBUSTNESS_VALIDATION = "ROBUSTNESS_VALIDATION"
    RESEARCH_CERTIFIED = "RESEARCH_CERTIFIED"


@dataclass(frozen=True, slots=True)
class CrtPureMarketCertificationEvidence:
    market: CrtPureMarket
    market_history_verified: bool
    exact_candidate_frozen: bool = False
    fresh_holdout_green: bool = False
    chronological_replay_green: bool = False
    annual_stability_green: bool = False
    rolling_stability_green: bool = False
    walk_forward_green: bool = False
    stress_green: bool = False
    slippage_green: bool = False
    monte_carlo_green: bool = False
    robustness_green: bool = False

    @property
    def independent_validation_green(self) -> bool:
        return (
            self.fresh_holdout_green
            and self.chronological_replay_green
            and self.annual_stability_green
            and self.rolling_stability_green
            and self.walk_forward_green
        )

    @property
    def robustness_validation_green(self) -> bool:
        return (
            self.stress_green
            and self.slippage_green
            and self.monte_carlo_green
            and self.robustness_green
        )


@dataclass(frozen=True, slots=True)
class CrtPureMarketCertificationReadiness:
    market: CrtPureMarket
    stage: CrtPureMarketCertificationStage
    blockers: tuple[str, ...]
    research_certified: bool = False
    external_review_required: bool = True
    demo_authorized: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    production_authorized: bool = False

    def __post_init__(self) -> None:
        expected = self.stage is CrtPureMarketCertificationStage.RESEARCH_CERTIFIED
        if self.research_certified is not expected:
            raise ValueError(
                "research_certified flag must match RESEARCH_CERTIFIED stage"
            )
        if (
            self.demo_authorized
            or self.live_authorized
            or self.real_capital_authorized
            or self.production_authorized
        ):
            raise ValueError(
                "per-market research certification cannot grant deployment authority"
            )


def evaluate_market_certification_readiness(
    evidence: CrtPureMarketCertificationEvidence,
) -> CrtPureMarketCertificationReadiness:
    if not isinstance(evidence.market, CrtPureMarket):
        raise TypeError("market certification requires CrtPureMarket")

    if not evidence.market_history_verified:
        return CrtPureMarketCertificationReadiness(
            market=evidence.market,
            stage=CrtPureMarketCertificationStage.HISTORY_OPEN,
            blockers=("MARKET_HISTORY_NOT_VERIFIED",),
        )

    if not evidence.exact_candidate_frozen:
        return CrtPureMarketCertificationReadiness(
            market=evidence.market,
            stage=CrtPureMarketCertificationStage.CANDIDATE_OPEN,
            blockers=("EXACT_CANDIDATE_NOT_FROZEN",),
        )

    if not evidence.independent_validation_green:
        blockers: list[str] = []
        for name, passed in (
            ("FRESH_HOLDOUT_NOT_GREEN", evidence.fresh_holdout_green),
            ("CHRONOLOGICAL_REPLAY_NOT_GREEN", evidence.chronological_replay_green),
            ("ANNUAL_STABILITY_NOT_GREEN", evidence.annual_stability_green),
            ("ROLLING_STABILITY_NOT_GREEN", evidence.rolling_stability_green),
            ("WALK_FORWARD_NOT_GREEN", evidence.walk_forward_green),
        ):
            if not passed:
                blockers.append(name)
        return CrtPureMarketCertificationReadiness(
            market=evidence.market,
            stage=CrtPureMarketCertificationStage.INDEPENDENT_VALIDATION,
            blockers=tuple(blockers),
        )

    if not evidence.robustness_validation_green:
        blockers = []
        for name, passed in (
            ("STRESS_NOT_GREEN", evidence.stress_green),
            ("SLIPPAGE_NOT_GREEN", evidence.slippage_green),
            ("MONTE_CARLO_NOT_GREEN", evidence.monte_carlo_green),
            ("ROBUSTNESS_NOT_GREEN", evidence.robustness_green),
        ):
            if not passed:
                blockers.append(name)
        return CrtPureMarketCertificationReadiness(
            market=evidence.market,
            stage=CrtPureMarketCertificationStage.ROBUSTNESS_VALIDATION,
            blockers=tuple(blockers),
        )

    return CrtPureMarketCertificationReadiness(
        market=evidence.market,
        stage=CrtPureMarketCertificationStage.RESEARCH_CERTIFIED,
        blockers=(),
        research_certified=True,
        external_review_required=True,
    )
