"""Probabilistic latent-market-state inference for Shared Core.

Observed market facts are not themselves the market state. This module
maintains posterior beliefs over hidden market factors using causal,
point-in-time evidence only.

The engine is intentionally generic and authority-free. It does not know trader
identity, setup identity, account state, PnL, sizing, Risk, orders, stops,
targets or execution.

Evidence is aggregated in log-odds space. Repeated observations from the same
independence group receive diminishing weight, which prevents one correlated
data family from masquerading as many independent confirmations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import exp, log


class LatentMarketFactor(StrEnum):
    BUY_PRESSURE = "BUY_PRESSURE"
    SELL_PRESSURE = "SELL_PRESSURE"
    ABSORPTION = "ABSORPTION"
    POST_SWEEP_CONTINUATION = "POST_SWEEP_CONTINUATION"
    STRUCTURAL_FRAGILITY = "STRUCTURAL_FRAGILITY"
    REGIME_TRANSITION = "REGIME_TRANSITION"
    MOMENTUM_PERSISTENCE = "MOMENTUM_PERSISTENCE"
    LIQUIDITY_VACUUM = "LIQUIDITY_VACUUM"
    INFORMATIVE_MOVE = "INFORMATIVE_MOVE"
    MULTISCALE_COHERENCE = "MULTISCALE_COHERENCE"


@dataclass(frozen=True, slots=True)
class LatentEvidenceAtom:
    factor: LatentMarketFactor
    source_family: str
    independence_group: str
    as_of: datetime
    support_bps: int
    contradiction_bps: int
    integrity_bps: int = 10_000

    def __post_init__(self) -> None:
        if not self.source_family or not self.independence_group:
            raise ValueError("evidence source and independence group must be non-empty")
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        for name in ("support_bps", "contradiction_bps", "integrity_bps"):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if self.support_bps == 0 and self.contradiction_bps == 0:
            raise ValueError("evidence atom must contain information")


@dataclass(frozen=True, slots=True)
class LatentFactorPosterior:
    factor: LatentMarketFactor
    probability_bps: int
    confidence_bps: int
    epistemic_uncertainty_bps: int
    independent_group_count: int
    evidence_count: int

    def __post_init__(self) -> None:
        for name in (
            "probability_bps",
            "confidence_bps",
            "epistemic_uncertainty_bps",
        ):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")
        if self.independent_group_count < 0 or self.evidence_count < 0:
            raise ValueError("evidence counts cannot be negative")


@dataclass(frozen=True, slots=True)
class LatentMarketState:
    as_of: datetime
    posteriors: tuple[LatentFactorPosterior, ...]
    overall_epistemic_uncertainty_bps: int
    regime_familiarity_bps: int
    evidence_cutoff_at: datetime
    outcome_used: bool = False
    pnl_used: bool = False
    future_market_used: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    stop_authority: bool = False
    target_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if self.evidence_cutoff_at.tzinfo is None or self.evidence_cutoff_at.utcoffset() is None:
            raise ValueError("evidence_cutoff_at must be timezone-aware")
        if self.evidence_cutoff_at > self.as_of:
            raise ValueError("future evidence is forbidden")
        if not 0 <= self.overall_epistemic_uncertainty_bps <= 10_000:
            raise ValueError("overall epistemic uncertainty must be within 0..10000")
        if not 0 <= self.regime_familiarity_bps <= 10_000:
            raise ValueError("regime familiarity must be within 0..10000")
        if len({item.factor for item in self.posteriors}) != len(self.posteriors):
            raise ValueError("latent factors must be unique")
        if (
            self.outcome_used
            or self.pnl_used
            or self.future_market_used
            or self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.stop_authority
            or self.target_authority
            or self.execution_authority
        ):
            raise ValueError("latent market state cannot carry trading authority")

    def probability_bps(self, factor: LatentMarketFactor) -> int:
        for item in self.posteriors:
            if item.factor is factor:
                return item.probability_bps
        return 5_000


@dataclass(frozen=True, slots=True)
class LatentMarketStatePolicy:
    prior_probability_bps: int = 5_000
    evidence_half_life_seconds: int = 900
    maximum_atom_age_seconds: int = 3_600
    correlation_discount_bps: int = 6_500
    minimum_integrity_bps: int = 2_500

    def __post_init__(self) -> None:
        if not 1 <= self.prior_probability_bps <= 9_999:
            raise ValueError("prior probability must be within 1..9999")
        if self.evidence_half_life_seconds <= 0:
            raise ValueError("evidence half life must be positive")
        if self.maximum_atom_age_seconds <= 0:
            raise ValueError("maximum atom age must be positive")
        for name in ("correlation_discount_bps", "minimum_integrity_bps"):
            value = int(getattr(self, name))
            if not 0 <= value <= 10_000:
                raise ValueError(f"{name} must be within 0..10000")


def _logit(probability: float) -> float:
    bounded = min(0.9999, max(0.0001, probability))
    return log(bounded / (1.0 - bounded))


def _logistic(value: float) -> float:
    if value >= 0:
        term = exp(-value)
        return 1.0 / (1.0 + term)
    term = exp(value)
    return term / (1.0 + term)


def _atom_log_likelihood(atom: LatentEvidenceAtom) -> float:
    epsilon = 250.0
    support = float(atom.support_bps) + epsilon
    contradiction = float(atom.contradiction_bps) + epsilon
    return log(support / contradiction)


def infer_latent_market_state(
    *,
    as_of: datetime,
    evidence: tuple[LatentEvidenceAtom, ...],
    regime_familiarity_bps: int,
    policy: LatentMarketStatePolicy | None = None,
) -> LatentMarketState:
    """Infer hidden market factors from bounded causal evidence."""

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    if not 0 <= regime_familiarity_bps <= 10_000:
        raise ValueError("regime_familiarity_bps must be within 0..10000")
    effective = policy or LatentMarketStatePolicy()

    eligible = []
    for atom in evidence:
        if atom.as_of > as_of:
            raise ValueError("future latent evidence is forbidden")
        age_seconds = int((as_of - atom.as_of).total_seconds())
        if age_seconds > effective.maximum_atom_age_seconds:
            continue
        if atom.integrity_bps < effective.minimum_integrity_bps:
            continue
        eligible.append((atom, age_seconds))

    prior = effective.prior_probability_bps / 10_000.0
    prior_logit = _logit(prior)
    posteriors: list[LatentFactorPosterior] = []

    for factor in LatentMarketFactor:
        atoms = [
            (atom, age_seconds)
            for atom, age_seconds in eligible
            if atom.factor is factor
        ]
        if not atoms:
            posteriors.append(
                LatentFactorPosterior(
                    factor=factor,
                    probability_bps=effective.prior_probability_bps,
                    confidence_bps=0,
                    epistemic_uncertainty_bps=10_000,
                    independent_group_count=0,
                    evidence_count=0,
                )
            )
            continue

        group_seen: dict[str, int] = {}
        log_odds = prior_logit
        weighted_information = 0.0
        for atom, age_seconds in sorted(
            atoms,
            key=lambda item: (item[0].as_of, item[0].source_family),
        ):
            repeats = group_seen.get(atom.independence_group, 0)
            group_seen[atom.independence_group] = repeats + 1
            correlation_weight = (
                effective.correlation_discount_bps / 10_000.0
            ) ** repeats
            decay_weight = 0.5 ** (
                age_seconds / effective.evidence_half_life_seconds
            )
            integrity_weight = atom.integrity_bps / 10_000.0
            weight = correlation_weight * decay_weight * integrity_weight
            information = _atom_log_likelihood(atom)
            log_odds += information * weight
            weighted_information += abs(information) * weight

        probability = _logistic(log_odds)
        groups = len(group_seen)
        diversity = min(1.0, groups / 4.0)
        evidence_strength = min(1.0, weighted_information / 4.0)
        confidence = int(round(10_000 * diversity * evidence_strength))
        epistemic = 10_000 - confidence
        posteriors.append(
            LatentFactorPosterior(
                factor=factor,
                probability_bps=int(round(probability * 10_000)),
                confidence_bps=confidence,
                epistemic_uncertainty_bps=epistemic,
                independent_group_count=groups,
                evidence_count=len(atoms),
            )
        )

    overall_uncertainty = (
        sum(item.epistemic_uncertainty_bps for item in posteriors)
        // len(posteriors)
    )
    cutoff = max((atom.as_of for atom, _ in eligible), default=as_of)
    return LatentMarketState(
        as_of=as_of,
        posteriors=tuple(posteriors),
        overall_epistemic_uncertainty_bps=overall_uncertainty,
        regime_familiarity_bps=regime_familiarity_bps,
        evidence_cutoff_at=cutoff,
    )
