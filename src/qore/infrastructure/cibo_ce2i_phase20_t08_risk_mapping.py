"""Candidate structural-stop risk attribution for CE2I T08.

The mapping uses only pre-decision full-universe factor returns and the causal
minimum-seed monetary factor exposure. Covariance determines relative risk
attribution; the structural stop-risk total is conserved exactly. No fixed
50/50 split is permitted.

This is a research candidate, not certified netting evidence. It never marks the
risk mapping as verified and never authorizes netting credit. Fresh OOS mapping
validation and netting-utility ablation remain mandatory.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_correlation import (
    T08_STOCHASTIC_FACTOR_IDS,
    assess_t08_correlation_readiness,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_factor_magnitude import (
    MonetaryFactorExposure,
    assess_minimum_seed_factor_magnitude,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_factor_returns import (
    T08FactorReturnObservation,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
    normalize_provider_economics,
)


@dataclass(frozen=True, slots=True)
class T08FactorRiskAllocation:
    factor_id: str
    signed_notional_usd: Decimal
    absolute_variance_contribution: Decimal
    risk_share: Decimal
    signed_risk_usd: Decimal

    def __post_init__(self) -> None:
        if self.factor_id not in T08_STOCHASTIC_FACTOR_IDS:
            raise CiboCapitalManagementError(
                "T08 risk allocation factor must be stochastic"
            )
        for name in (
            "signed_notional_usd",
            "absolute_variance_contribution",
            "risk_share",
            "signed_risk_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"T08 risk allocation {name} must be finite Decimal"
                )
        if self.signed_notional_usd == 0:
            raise CiboCapitalManagementError(
                "T08 risk allocation notional cannot be zero"
            )
        if self.absolute_variance_contribution <= 0:
            raise CiboCapitalManagementError(
                "T08 variance contribution must be positive"
            )
        if self.risk_share <= 0 or self.risk_share > 1:
            raise CiboCapitalManagementError(
                "T08 risk share must be in (0, 1]"
            )
        if self.signed_risk_usd == 0:
            raise CiboCapitalManagementError(
                "T08 signed factor risk cannot be zero"
            )
        if (self.signed_risk_usd > 0) != (self.signed_notional_usd > 0):
            raise CiboCapitalManagementError(
                "T08 factor risk direction must match factor notional"
            )


@dataclass(frozen=True, slots=True)
class T08FactorRiskMappingAudit:
    mapping_candidate_id: str | None
    signal_fingerprint: str
    qore_symbol: str
    decision_at: datetime
    structural_stop_risk_usd: Decimal
    correlation_sample_size: int
    allocations: tuple[T08FactorRiskAllocation, ...]
    gross_allocated_risk_usd: Decimal
    candidate_mapping_identified: bool
    risk_mapping_verified: bool
    netting_credit_authorized: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.qore_symbol:
            raise CiboCapitalManagementError(
                "T08 risk mapping signal/symbol required"
            )
        _aware(self.decision_at, "T08 risk mapping decision_at")
        _non_negative(
            self.structural_stop_risk_usd,
            "structural_stop_risk_usd",
        )
        _non_negative(
            self.gross_allocated_risk_usd,
            "gross_allocated_risk_usd",
        )
        if self.correlation_sample_size < 0:
            raise CiboCapitalManagementError(
                "T08 correlation sample size cannot be negative"
            )
        for name in (
            "candidate_mapping_identified",
            "risk_mapping_verified",
            "netting_credit_authorized",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"T08 risk mapping {name} must be bool"
                )
        if self.risk_mapping_verified or self.netting_credit_authorized:
            raise CiboCapitalManagementError(
                "T08 candidate mapping cannot certify or authorize netting"
            )
        if self.candidate_mapping_identified:
            if self.mapping_candidate_id is None or not self.allocations:
                raise CiboCapitalManagementError(
                    "T08 identified mapping requires candidate identity/allocations"
                )
            if (
                self.gross_allocated_risk_usd
                != self.structural_stop_risk_usd
            ):
                raise CiboCapitalManagementError(
                    "T08 factor allocation must conserve structural stop risk"
                )
        elif self.allocations or self.gross_allocated_risk_usd != 0:
            raise CiboCapitalManagementError(
                "T08 unidentified mapping cannot carry factor risk"
            )


def assess_t08_candidate_risk_mapping(
    *,
    opportunity: TraderOpportunityEnvelope,
    observation: ProviderEconomicObservation,
    factor_returns: tuple[T08FactorReturnObservation, ...],
    decision_at: datetime,
    provider_evidence_ref: str,
    minimum_correlation_samples: int = 30,
    required_correlation_folds: int = 4,
) -> T08FactorRiskMappingAudit:
    """Attribute minimum structural stop risk without changing its total."""

    _aware(decision_at, "T08 risk mapping decision_at")
    magnitude = assess_minimum_seed_factor_magnitude(
        opportunity=opportunity,
        observation=observation,
        decision_at=decision_at,
        provider_evidence_ref=provider_evidence_ref,
    )
    normalized = normalize_provider_economics(
        opportunity=opportunity,
        observation=observation,
    )
    correlation = assess_t08_correlation_readiness(
        observations=factor_returns,
        decision_at=decision_at,
        minimum_samples=minimum_correlation_samples,
        required_folds=required_correlation_folds,
    )
    stop_risk = normalized.minimum_stop_risk_usd

    stochastic_exposures = tuple(
        item
        for item in magnitude.exposures
        if item.factor_id != "USD"
    )
    if (
        not correlation.correlation_matrix_identified
        or not correlation.directional_stability_observed
        or not stochastic_exposures
    ):
        blockers = list(correlation.blockers)
        blockers.append("T08_FACTOR_RISK_MAPPING_NOT_IDENTIFIED")
        return T08FactorRiskMappingAudit(
            mapping_candidate_id=None,
            signal_fingerprint=opportunity.signal_fingerprint,
            qore_symbol=opportunity.qore_symbol,
            decision_at=decision_at,
            structural_stop_risk_usd=stop_risk,
            correlation_sample_size=correlation.sample_size,
            allocations=(),
            gross_allocated_risk_usd=Decimal(0),
            candidate_mapping_identified=False,
            risk_mapping_verified=False,
            netting_credit_authorized=False,
            blockers=tuple(dict.fromkeys(blockers)),
        )

    notionals = _signed_notional_map(stochastic_exposures)
    active_factors = tuple(sorted(notionals))
    centered = _centered_factor_series(
        factor_returns=factor_returns,
        factor_ids=active_factors,
    )
    absolute_contributions: dict[str, Decimal] = {}
    for factor_id in active_factors:
        sigma_times_exposure = sum(
            (
                _cross_deviation_sum(
                    centered[factor_id],
                    centered[other],
                )
                * notionals[other]
                for other in active_factors
            ),
            Decimal(0),
        )
        contribution = notionals[factor_id] * sigma_times_exposure
        absolute_contributions[factor_id] = abs(contribution)

    total_contribution = sum(
        absolute_contributions.values(),
        Decimal(0),
    )
    if total_contribution <= 0:
        return T08FactorRiskMappingAudit(
            mapping_candidate_id=None,
            signal_fingerprint=opportunity.signal_fingerprint,
            qore_symbol=opportunity.qore_symbol,
            decision_at=decision_at,
            structural_stop_risk_usd=stop_risk,
            correlation_sample_size=correlation.sample_size,
            allocations=(),
            gross_allocated_risk_usd=Decimal(0),
            candidate_mapping_identified=False,
            risk_mapping_verified=False,
            netting_credit_authorized=False,
            blockers=(
                "T08_FACTOR_VARIANCE_CONTRIBUTION_DEGENERATE",
                "T08_FACTOR_RISK_MAPPING_NOT_IDENTIFIED",
                "FRESH_OOS_NETTING_UTILITY_ANALYSIS_REQUIRED",
            ),
        )

    allocations: list[T08FactorRiskAllocation] = []
    allocated_abs = Decimal(0)
    for index, factor_id in enumerate(active_factors):
        if index == len(active_factors) - 1:
            factor_risk_abs = stop_risk - allocated_abs
        else:
            factor_risk_abs = (
                stop_risk
                * absolute_contributions[factor_id]
                / total_contribution
            )
            allocated_abs += factor_risk_abs
        sign = Decimal(1) if notionals[factor_id] > 0 else Decimal(-1)
        allocations.append(
            T08FactorRiskAllocation(
                factor_id=factor_id,
                signed_notional_usd=notionals[factor_id],
                absolute_variance_contribution=(
                    absolute_contributions[factor_id]
                ),
                risk_share=factor_risk_abs / stop_risk,
                signed_risk_usd=sign * factor_risk_abs,
            )
        )

    gross = sum(
        (abs(item.signed_risk_usd) for item in allocations),
        Decimal(0),
    )
    candidate_id = "sha256:" + _sha256(
        {
            "signal_fingerprint": opportunity.signal_fingerprint,
            "qore_symbol": opportunity.qore_symbol,
            "decision_at": decision_at.isoformat(),
            "provider_evidence_ref": provider_evidence_ref,
            "stop_risk_usd": str(stop_risk),
            "correlation_sample_size": correlation.sample_size,
            "allocations": [
                {
                    "factor_id": item.factor_id,
                    "signed_notional_usd": str(item.signed_notional_usd),
                    "risk_share": str(item.risk_share),
                    "signed_risk_usd": str(item.signed_risk_usd),
                }
                for item in allocations
            ],
        }
    )
    return T08FactorRiskMappingAudit(
        mapping_candidate_id=candidate_id,
        signal_fingerprint=opportunity.signal_fingerprint,
        qore_symbol=opportunity.qore_symbol,
        decision_at=decision_at,
        structural_stop_risk_usd=stop_risk,
        correlation_sample_size=correlation.sample_size,
        allocations=tuple(allocations),
        gross_allocated_risk_usd=gross,
        candidate_mapping_identified=True,
        risk_mapping_verified=False,
        netting_credit_authorized=False,
        blockers=(
            "T08_FACTOR_RISK_MAPPING_REQUIRES_FRESH_OOS_VALIDATION",
            "FRESH_OOS_NETTING_UTILITY_ANALYSIS_REQUIRED",
        ),
    )


def _signed_notional_map(
    exposures: tuple[MonetaryFactorExposure, ...],
) -> dict[str, Decimal]:
    values: dict[str, Decimal] = {}
    for item in exposures:
        if item.factor_id not in T08_STOCHASTIC_FACTOR_IDS:
            raise CiboCapitalManagementError(
                "T08 risk mapping exposure factor outside stochastic universe"
            )
        if item.signed_notional_usd is None:
            raise CiboCapitalManagementError(
                "T08 risk mapping requires complete USD factor notionals"
            )
        if item.factor_id in values:
            raise CiboCapitalManagementError(
                "T08 risk mapping duplicate factor exposure"
            )
        values[item.factor_id] = item.signed_notional_usd
    return values


def _centered_factor_series(
    *,
    factor_returns: tuple[T08FactorReturnObservation, ...],
    factor_ids: tuple[str, ...],
) -> dict[str, tuple[Decimal, ...]]:
    result: dict[str, tuple[Decimal, ...]] = {}
    for factor_id in factor_ids:
        raw = tuple(item.return_for(factor_id) for item in factor_returns)
        mean = sum(raw, Decimal(0)) / Decimal(len(raw))
        result[factor_id] = tuple(value - mean for value in raw)
    return result


def _cross_deviation_sum(
    left: tuple[Decimal, ...],
    right: tuple[Decimal, ...],
) -> Decimal:
    if len(left) != len(right) or not left:
        raise CiboCapitalManagementError(
            "T08 covariance series must be non-empty and aligned"
        )
    return sum(
        (
            left_value * right_value
            for left_value, right_value in zip(left, right, strict=True)
        ),
        Decimal(0),
    )


def _sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(f"{name} must be timezone-aware")


def _non_negative(value: Decimal, name: str) -> None:
    if (
        not isinstance(value, Decimal)
        or not value.is_finite()
        or value < 0
    ):
        raise CiboCapitalManagementError(
            f"T08 risk mapping {name} must be finite non-negative Decimal"
        )
