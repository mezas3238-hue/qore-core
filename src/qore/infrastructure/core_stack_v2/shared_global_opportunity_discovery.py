"""Real source-only opportunity discovery engine for proactive Shared STI.

The engine consumes chronological market observations that exist at decision
time. It does not consume future bars, trade outcomes, PnL, sizing, Risk or
execution state. Thresholds are supplied by a frozen policy so historical
research can fit them from source-only development evidence and replay them
unchanged on later partitions.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedDirectionalHypothesis,
    SharedOpportunityMaturity,
    SharedTraderIntelligenceValidationError,
)


def _validate_bps(name: str, value: int) -> None:
    if type(value) is not int or not 0 <= value <= 10_000:
        raise SharedTraderIntelligenceValidationError(
            f"{name} must be int within 0..10000"
        )


def _mean(values: Sequence[int]) -> int:
    if not values:
        raise SharedTraderIntelligenceValidationError(
            "opportunity score requires evidence"
        )
    return sum(values) // len(values)


@dataclass(frozen=True, slots=True)
@dataclass(frozen=True, slots=True)
class SharedOpportunitySourceObservation:
    """Source-only world evidence for one instrument at one causal timestamp."""

    observation_id: str
    asset: str
    as_of: datetime
    evidence_cutoff_at: datetime
    direction_sign: int
    data_integrity_bps: int
    compression_bps: int
    liquidity_accumulation_bps: int
    failed_auction_bps: int
    displacement_bps: int
    acceptance_bps: int
    absorption_bps: int
    leader_confirmation_bps: int
    leader_divergence_bps: int
    momentum_persistence_bps: int
    momentum_decay_bps: int
    structural_fragility_bps: int
    liquidity_vacuum_bps: int
    regime_transition_bps: int
    anomaly_bps: int
    provenance_refs: tuple[str, ...]
    future_market_used: bool = False
    future_outcome_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.observation_id.strip() or not self.asset.strip():
            raise SharedTraderIntelligenceValidationError(
                "opportunity observation identity must be explicit"
            )
        for value in (self.as_of, self.evidence_cutoff_at):
            if value.tzinfo is None or value.utcoffset() is None:
                raise SharedTraderIntelligenceValidationError(
                    "opportunity observation timestamps must be timezone-aware"
                )
        if self.evidence_cutoff_at > self.as_of:
            raise SharedTraderIntelligenceValidationError(
                "opportunity observation cannot use future evidence"
            )
        if self.direction_sign not in {-1, 0, 1}:
            raise SharedTraderIntelligenceValidationError(
                "direction_sign must be -1, 0 or 1"
            )
        for name in (
            "data_integrity_bps",
            "compression_bps",
            "liquidity_accumulation_bps",
            "failed_auction_bps",
            "displacement_bps",
            "acceptance_bps",
            "absorption_bps",
            "leader_confirmation_bps",
            "leader_divergence_bps",
            "momentum_persistence_bps",
            "momentum_decay_bps",
            "structural_fragility_bps",
            "liquidity_vacuum_bps",
            "regime_transition_bps",
            "anomaly_bps",
        ):
            _validate_bps(name, getattr(self, name))
        if (
            not self.provenance_refs
            or self.provenance_refs != tuple(sorted(set(self.provenance_refs)))
        ):
            raise SharedTraderIntelligenceValidationError(
                "opportunity provenance must be non-empty and canonical"
            )
        if (
            self.future_market_used
            or self.future_outcome_used
            or self.productive_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "opportunity source observation is causal research evidence only"
            )


@dataclass(frozen=True, slots=True)
@dataclass(frozen=True, slots=True)
class SharedOpportunityEnginePolicy:
    policy_id: str
    version: str
    frozen_at: datetime
    early_threshold_bps: int
    developing_threshold_bps: int
    mature_threshold_bps: int
    minimum_integrity_bps: int
    mature_persistence_bps: int
    sequence_window: int
    source_only_calibration: bool
    calibration_evidence_refs: tuple[str, ...]
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.policy_id.strip() or not self.version.strip():
            raise SharedTraderIntelligenceValidationError(
                "opportunity policy identity must be explicit"
            )
        if self.frozen_at.tzinfo is None or self.frozen_at.utcoffset() is None:
            raise SharedTraderIntelligenceValidationError(
                "opportunity policy frozen_at must be timezone-aware"
            )
        for name in (
            "early_threshold_bps",
            "developing_threshold_bps",
            "mature_threshold_bps",
            "minimum_integrity_bps",
            "mature_persistence_bps",
        ):
            _validate_bps(name, getattr(self, name))
        if not (
            self.early_threshold_bps
            < self.developing_threshold_bps
            < self.mature_threshold_bps
        ):
            raise SharedTraderIntelligenceValidationError(
                "opportunity thresholds must be strictly ordered"
            )
        if self.sequence_window < 3:
            raise SharedTraderIntelligenceValidationError(
                "opportunity sequence_window must be at least 3"
            )
        if not self.source_only_calibration:
            raise SharedTraderIntelligenceValidationError(
                "opportunity policy calibration must be source-only"
            )
        if (
            not self.calibration_evidence_refs
            or self.calibration_evidence_refs
            != tuple(sorted(set(self.calibration_evidence_refs)))
        ):
            raise SharedTraderIntelligenceValidationError(
                "opportunity policy evidence must be non-empty and canonical"
            )
        if self.productive_authority:
            raise SharedTraderIntelligenceValidationError(
                "opportunity research policy cannot authorize production"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["frozen_at"] = self.frozen_at.astimezone(UTC).isoformat()
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
@dataclass(frozen=True, slots=True)
class SharedOpportunityEngineAssessment:
    asset: str
    as_of: datetime
    evidence_cutoff_at: datetime
    maturity: SharedOpportunityMaturity
    directional_hypothesis: SharedDirectionalHypothesis
    opportunity_score_bps: int
    trend_support_bps: int
    reversal_support_bps: int
    expansion_support_bps: int
    novelty_bps: int
    persistence_bps: int
    contradiction_bps: int
    uncertainty_bps: int
    reason_codes: tuple[str, ...]
    policy_fingerprint: str
    creates_trader_setup: bool = False
    execution_authority: bool = False
    sizing_authority: bool = False
    capital_authority: bool = False
    risk_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "opportunity_score_bps",
            "trend_support_bps",
            "reversal_support_bps",
            "expansion_support_bps",
            "novelty_bps",
            "persistence_bps",
            "contradiction_bps",
            "uncertainty_bps",
        ):
            _validate_bps(name, getattr(self, name))
        if len(self.policy_fingerprint) != 64:
            raise SharedTraderIntelligenceValidationError(
                "opportunity policy_fingerprint must be sha256 hex"
            )
        if not self.reason_codes:
            raise SharedTraderIntelligenceValidationError(
                "opportunity assessment requires reason codes"
            )
        if (
            self.creates_trader_setup
            or self.execution_authority
            or self.sizing_authority
            or self.capital_authority
            or self.risk_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "opportunity assessment is attention only"
            )


def _components(
    observation: SharedOpportunitySourceObservation,
) -> tuple[int, int, int, int, int]:
    trend = _mean(
        (
            observation.displacement_bps,
            observation.acceptance_bps,
            observation.leader_confirmation_bps,
            observation.momentum_persistence_bps,
        )
    )
    reversal = _mean(
        (
            observation.failed_auction_bps,
            observation.absorption_bps,
            observation.leader_divergence_bps,
            observation.momentum_decay_bps,
            observation.regime_transition_bps,
        )
    )
    expansion = _mean(
        (
            observation.compression_bps,
            observation.liquidity_accumulation_bps,
            observation.displacement_bps,
            observation.liquidity_vacuum_bps,
        )
    )
    contradiction = _mean(
        (
            observation.structural_fragility_bps,
            observation.anomaly_bps,
            observation.leader_divergence_bps,
        )
    )
    raw_support = max(trend, reversal, expansion)
    score = max(
        0,
        min(
            10_000,
            (raw_support * 7 + observation.data_integrity_bps * 3) // 10
            - contradiction // 4,
        ),
    )
    return score, trend, reversal, expansion, contradiction


def opportunity_source_score_bps(
    observation: SharedOpportunitySourceObservation,
) -> int:
    """Source-only score used both for policy freeze and causal replay."""

    return _components(observation)[0]


def assess_global_opportunity(
    observations: Sequence[SharedOpportunitySourceObservation],
    *,
    policy: SharedOpportunityEnginePolicy,
) -> SharedOpportunityEngineAssessment:
    """Derive attention-worthy opportunity state from causal observations."""

    if not observations:
        raise SharedTraderIntelligenceValidationError(
            "opportunity engine requires observations"
        )
    ordered = tuple(observations)
    for left, right in zip(ordered, ordered[1:], strict=False):
        if right.as_of <= left.as_of:
            raise SharedTraderIntelligenceValidationError(
                "opportunity observations must be strictly chronological"
            )
        if left.asset != right.asset:
            raise SharedTraderIntelligenceValidationError(
                "opportunity sequence must use one asset"
            )

    latest = ordered[-1]
    if latest.evidence_cutoff_at > latest.as_of:
        raise SharedTraderIntelligenceValidationError(
            "opportunity engine cannot consume future evidence"
        )

    score, trend, reversal, expansion, contradiction = _components(latest)
    recent = ordered[-policy.sequence_window :]
    recent_scores = tuple(opportunity_source_score_bps(item) for item in recent)
    prior_scores = recent_scores[:-1]
    prior_reference = (
        sum(prior_scores) // len(prior_scores)
        if prior_scores
        else recent_scores[-1]
    )
    novelty = min(10_000, abs(score - prior_reference))
    persistence = (
        sum(value >= policy.early_threshold_bps for value in recent_scores)
        * 10_000
        // len(recent_scores)
    )
    uncertainty = min(
        10_000,
        _mean(
            (
                10_000 - latest.data_integrity_bps,
                latest.anomaly_bps,
                latest.structural_fragility_bps,
                latest.regime_transition_bps,
            )
        ),
    )

    reasons: list[str] = []
    if latest.data_integrity_bps < policy.minimum_integrity_bps:
        maturity = SharedOpportunityMaturity.INSUFFICIENT
        hypothesis = SharedDirectionalHypothesis.INSUFFICIENT
        reasons.append("DATA_INTEGRITY_INSUFFICIENT")
    else:
        prior_peak = max(prior_scores, default=0)
        if (
            prior_peak >= policy.developing_threshold_bps
            and score < policy.developing_threshold_bps
            and score >= policy.early_threshold_bps
        ):
            maturity = SharedOpportunityMaturity.DETERIORATING
            reasons.append("OPPORTUNITY_SUPPORT_DECAYING")
        elif (
            score >= policy.mature_threshold_bps
            and persistence >= policy.mature_persistence_bps
        ):
            maturity = SharedOpportunityMaturity.MATURE
            reasons.append("MATURE_SOURCE_ONLY_OPPORTUNITY")
        elif score >= policy.developing_threshold_bps:
            maturity = SharedOpportunityMaturity.DEVELOPING
            reasons.append("DEVELOPING_SOURCE_ONLY_OPPORTUNITY")
        elif score >= policy.early_threshold_bps:
            maturity = SharedOpportunityMaturity.EARLY
            reasons.append("EARLY_SOURCE_ONLY_OPPORTUNITY")
        else:
            maturity = SharedOpportunityMaturity.NO_OPPORTUNITY
            reasons.append("NO_MATERIAL_SOURCE_ONLY_OPPORTUNITY")

        dominant = max(
            (
                ("TREND", trend),
                ("REVERSAL", reversal),
                ("EXPANSION", expansion),
            ),
            key=lambda item: (item[1], item[0]),
        )[0]
        if maturity is SharedOpportunityMaturity.NO_OPPORTUNITY:
            hypothesis = SharedDirectionalHypothesis.INSUFFICIENT
        elif dominant == "REVERSAL":
            hypothesis = SharedDirectionalHypothesis.REVERSAL_HYPOTHESIS
            reasons.append("REVERSAL_STRUCTURE_DOMINANT")
        elif dominant == "EXPANSION":
            hypothesis = SharedDirectionalHypothesis.REGIME_TRANSITION_HYPOTHESIS
            reasons.append("EXPANSION_STRUCTURE_DOMINANT")
        elif latest.direction_sign > 0:
            hypothesis = SharedDirectionalHypothesis.BULLISH_HYPOTHESIS
            reasons.append("BULLISH_TREND_STRUCTURE_DOMINANT")
        elif latest.direction_sign < 0:
            hypothesis = SharedDirectionalHypothesis.BEARISH_HYPOTHESIS
            reasons.append("BEARISH_TREND_STRUCTURE_DOMINANT")
        else:
            hypothesis = SharedDirectionalHypothesis.CONTINUATION_HYPOTHESIS
            reasons.append("TREND_SUPPORT_DIRECTION_UNRESOLVED")

    if novelty >= 1_500:
        reasons.append("SOURCE_STATE_NOVELTY_HIGH")
    if contradiction >= 6_000:
        reasons.append("CONTRADICTORY_EVIDENCE_HIGH")
    if uncertainty >= 6_000:
        reasons.append("UNCERTAINTY_HIGH")

    return SharedOpportunityEngineAssessment(
        asset=latest.asset,
        as_of=latest.as_of,
        evidence_cutoff_at=latest.evidence_cutoff_at,
        maturity=maturity,
        directional_hypothesis=hypothesis,
        opportunity_score_bps=score,
        trend_support_bps=trend,
        reversal_support_bps=reversal,
        expansion_support_bps=expansion,
        novelty_bps=novelty,
        persistence_bps=persistence,
        contradiction_bps=contradiction,
        uncertainty_bps=uncertainty,
        reason_codes=tuple(sorted(set(reasons))),
        policy_fingerprint=policy.fingerprint(),
    )
