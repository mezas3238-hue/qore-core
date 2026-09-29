"""Causal correlation-readiness audit for CE2I T08.

The audit consumes only full-universe T08 factor-return observations that were
known before the decision timestamp. It estimates descriptive Pearson
correlations on the full window and on four contiguous folds. No estimate in
this module authorizes portfolio netting: stop-risk factor mapping and fresh OOS
netting utility remain separate mandatory gates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_factor_returns import (
    FROZEN_T08_FACTOR_IDS,
    T08FactorReturnObservation,
    T08MarketCollectionBasis,
)

T08_STOCHASTIC_FACTOR_IDS = tuple(
    factor_id
    for factor_id in FROZEN_T08_FACTOR_IDS
    if factor_id != "USD"
)


@dataclass(frozen=True, slots=True)
class T08CorrelationEstimate:
    left_factor: str
    right_factor: str
    sample_size: int
    correlation: Decimal | None

    def __post_init__(self) -> None:
        if (
            self.left_factor not in T08_STOCHASTIC_FACTOR_IDS
            or self.right_factor not in T08_STOCHASTIC_FACTOR_IDS
            or self.left_factor >= self.right_factor
        ):
            raise CiboCapitalManagementError(
                "T08 correlation pair must use ordered stochastic factors"
            )
        if self.sample_size < 2:
            raise CiboCapitalManagementError(
                "T08 correlation estimate requires at least two samples"
            )
        if self.correlation is not None and (
            not self.correlation.is_finite()
            or self.correlation < Decimal(-1)
            or self.correlation > Decimal(1)
        ):
            raise CiboCapitalManagementError(
                "T08 correlation estimate must stay in [-1, 1]"
            )


@dataclass(frozen=True, slots=True)
class T08CorrelationFold:
    fold_index: int
    start_market_at: datetime
    end_market_at: datetime
    sample_size: int
    estimates: tuple[T08CorrelationEstimate, ...]
    zero_variance_factors: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.fold_index < 0 or self.sample_size < 2:
            raise CiboCapitalManagementError(
                "T08 correlation fold identity/sample invalid"
            )
        _aware(self.start_market_at, "T08 correlation fold start")
        _aware(self.end_market_at, "T08 correlation fold end")
        if self.end_market_at <= self.start_market_at:
            raise CiboCapitalManagementError(
                "T08 correlation fold must advance in market time"
            )


@dataclass(frozen=True, slots=True)
class T08CorrelationAudit:
    provider_key: str | None
    decision_at: datetime
    sample_size: int
    minimum_samples: int
    required_folds: int
    estimates: tuple[T08CorrelationEstimate, ...]
    folds: tuple[T08CorrelationFold, ...]
    zero_variance_factors: tuple[str, ...]
    sample_ready: bool
    correlation_matrix_identified: bool
    directional_stability_observed: bool
    risk_mapping_verified: bool
    netting_utility_oos: bool
    netting_credit_authorized: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        _aware(self.decision_at, "T08 correlation audit decision_at")
        if self.sample_size < 0 or self.minimum_samples < 2:
            raise CiboCapitalManagementError(
                "T08 correlation audit sample thresholds invalid"
            )
        if self.required_folds < 2:
            raise CiboCapitalManagementError(
                "T08 correlation audit requires at least two folds"
            )
        if self.netting_credit_authorized:
            raise CiboCapitalManagementError(
                "T08 correlation audit cannot authorize netting credit"
            )
        if self.risk_mapping_verified or self.netting_utility_oos:
            raise CiboCapitalManagementError(
                "T08 correlation audit cannot certify independent gates"
            )


def assess_t08_correlation_readiness(
    *,
    observations: tuple[T08FactorReturnObservation, ...],
    decision_at: datetime,
    minimum_samples: int = 30,
    required_folds: int = 4,
) -> T08CorrelationAudit:
    """Assess only pre-decision, non-overlapping, full-universe observations."""

    _aware(decision_at, "T08 correlation decision_at")
    if minimum_samples < 2:
        raise CiboCapitalManagementError(
            "T08 minimum correlation sample must be at least two"
        )
    if required_folds < 2:
        raise CiboCapitalManagementError(
            "T08 correlation required_folds must be at least two"
        )
    if not observations:
        return _empty_audit(
            decision_at=decision_at,
            minimum_samples=minimum_samples,
            required_folds=required_folds,
        )

    ordered = tuple(
        sorted(
            observations,
            key=lambda item: (
                item.end_market_at,
                item.start_market_at,
                item.end_snapshot_id,
            ),
        )
    )
    provider_keys = {item.provider_key for item in ordered}
    if len(provider_keys) != 1:
        raise CiboCapitalManagementError(
            "T08 correlation window must use one provider"
        )
    for item in ordered:
        if (
            item.collection_basis
            is not T08MarketCollectionBasis.FULL_FROZEN_UNIVERSE
        ):
            raise CiboCapitalManagementError(
                "T08 correlation rejects candidate-conditioned evidence"
            )
        if item.known_at > decision_at:
            raise CiboCapitalManagementError(
                "T08 correlation window contains future-known evidence"
            )
    for previous, current in zip(ordered, ordered[1:], strict=False):
        if current.start_market_at < previous.end_market_at:
            raise CiboCapitalManagementError(
                "T08 correlation observations must not overlap"
            )

    estimates, zero_variance = _estimate_window(ordered)
    folds = _build_folds(
        ordered,
        required_folds=required_folds,
    )
    sample_ready = len(ordered) >= minimum_samples
    fold_ready = len(folds) == required_folds
    fold_zero_variance = {
        factor_id
        for fold in folds
        for factor_id in fold.zero_variance_factors
    }
    all_zero_variance = tuple(
        sorted(set(zero_variance) | fold_zero_variance)
    )
    matrix_identified = (
        sample_ready
        and fold_ready
        and not all_zero_variance
        and bool(estimates)
    )
    directional_stability = (
        matrix_identified
        and _direction_signs_stable(estimates, folds)
    )

    blockers: list[str] = []
    if not sample_ready:
        blockers.append(
            f"T08_CORRELATION_MINIMUM_SAMPLE_NOT_MET:"
            f"{len(ordered)}/{minimum_samples}"
        )
    if not fold_ready:
        blockers.append(
            f"T08_CORRELATION_FOLD_COVERAGE_NOT_MET:"
            f"{len(folds)}/{required_folds}"
        )
    if all_zero_variance:
        blockers.append(
            "T08_ZERO_VARIANCE_FACTORS:" + ",".join(all_zero_variance)
        )
    if matrix_identified and not directional_stability:
        blockers.append("T08_CORRELATION_DIRECTION_NOT_STABLE_ACROSS_FOLDS")
    if not matrix_identified:
        blockers.append("CAUSAL_CORRELATION_STATE_NOT_IDENTIFIED")
    blockers.extend(
        (
            "SIGNED_FACTOR_RISK_MAP_NOT_CERTIFIED",
            "FRESH_OOS_NETTING_UTILITY_ANALYSIS_REQUIRED",
        )
    )
    return T08CorrelationAudit(
        provider_key=next(iter(provider_keys)),
        decision_at=decision_at,
        sample_size=len(ordered),
        minimum_samples=minimum_samples,
        required_folds=required_folds,
        estimates=estimates,
        folds=folds,
        zero_variance_factors=all_zero_variance,
        sample_ready=sample_ready,
        correlation_matrix_identified=matrix_identified,
        directional_stability_observed=directional_stability,
        risk_mapping_verified=False,
        netting_utility_oos=False,
        netting_credit_authorized=False,
        blockers=tuple(blockers),
    )


def _empty_audit(
    *,
    decision_at: datetime,
    minimum_samples: int,
    required_folds: int,
) -> T08CorrelationAudit:
    return T08CorrelationAudit(
        provider_key=None,
        decision_at=decision_at,
        sample_size=0,
        minimum_samples=minimum_samples,
        required_folds=required_folds,
        estimates=(),
        folds=(),
        zero_variance_factors=(),
        sample_ready=False,
        correlation_matrix_identified=False,
        directional_stability_observed=False,
        risk_mapping_verified=False,
        netting_utility_oos=False,
        netting_credit_authorized=False,
        blockers=(
            f"T08_CORRELATION_MINIMUM_SAMPLE_NOT_MET:0/{minimum_samples}",
            f"T08_CORRELATION_FOLD_COVERAGE_NOT_MET:0/{required_folds}",
            "CAUSAL_CORRELATION_STATE_NOT_IDENTIFIED",
            "SIGNED_FACTOR_RISK_MAP_NOT_CERTIFIED",
            "FRESH_OOS_NETTING_UTILITY_ANALYSIS_REQUIRED",
        ),
    )


def _estimate_window(
    observations: tuple[T08FactorReturnObservation, ...],
) -> tuple[tuple[T08CorrelationEstimate, ...], tuple[str, ...]]:
    if len(observations) < 2:
        return (), T08_STOCHASTIC_FACTOR_IDS

    series = {
        factor_id: tuple(
            item.return_for(factor_id)
            for item in observations
        )
        for factor_id in T08_STOCHASTIC_FACTOR_IDS
    }
    zero_variance = tuple(
        factor_id
        for factor_id, values in series.items()
        if _sum_squared_deviations(values) == 0
    )
    estimates: list[T08CorrelationEstimate] = []
    for left_index, left in enumerate(T08_STOCHASTIC_FACTOR_IDS):
        for right in T08_STOCHASTIC_FACTOR_IDS[left_index + 1 :]:
            estimates.append(
                T08CorrelationEstimate(
                    left_factor=left,
                    right_factor=right,
                    sample_size=len(observations),
                    correlation=_pearson(series[left], series[right]),
                )
            )
    return tuple(estimates), zero_variance


def _build_folds(
    observations: tuple[T08FactorReturnObservation, ...],
    *,
    required_folds: int,
) -> tuple[T08CorrelationFold, ...]:
    if len(observations) < required_folds * 2:
        return ()
    base = len(observations) // required_folds
    extra = len(observations) % required_folds
    folds: list[T08CorrelationFold] = []
    cursor = 0
    for fold_index in range(required_folds):
        size = base + (1 if fold_index < extra else 0)
        subset = observations[cursor : cursor + size]
        cursor += size
        estimates, zero_variance = _estimate_window(subset)
        folds.append(
            T08CorrelationFold(
                fold_index=fold_index,
                start_market_at=subset[0].start_market_at,
                end_market_at=subset[-1].end_market_at,
                sample_size=len(subset),
                estimates=estimates,
                zero_variance_factors=zero_variance,
            )
        )
    return tuple(folds)


def _direction_signs_stable(
    estimates: tuple[T08CorrelationEstimate, ...],
    folds: tuple[T08CorrelationFold, ...],
) -> bool:
    full = {
        (item.left_factor, item.right_factor): item.correlation
        for item in estimates
    }
    for pair, full_value in full.items():
        if full_value is None or full_value == 0:
            return False
        expected_positive = full_value > 0
        for fold in folds:
            by_pair = {
                (item.left_factor, item.right_factor): item.correlation
                for item in fold.estimates
            }
            value = by_pair.get(pair)
            if value is None or value == 0 or (value > 0) != expected_positive:
                return False
    return True


def _pearson(
    left: tuple[Decimal, ...],
    right: tuple[Decimal, ...],
) -> Decimal | None:
    if len(left) != len(right) or len(left) < 2:
        raise CiboCapitalManagementError(
            "T08 Pearson series must have equal length >= 2"
        )
    left_mean = sum(left, Decimal(0)) / Decimal(len(left))
    right_mean = sum(right, Decimal(0)) / Decimal(len(right))
    numerator = sum(
        (
            (left_value - left_mean)
            * (right_value - right_mean)
            for left_value, right_value in zip(left, right, strict=True)
        ),
        Decimal(0),
    )
    left_ss = _sum_squared_deviations(left)
    right_ss = _sum_squared_deviations(right)
    if left_ss == 0 or right_ss == 0:
        return None
    denominator = (left_ss * right_ss).sqrt()
    value = numerator / denominator
    return min(Decimal(1), max(Decimal(-1), value))


def _sum_squared_deviations(values: tuple[Decimal, ...]) -> Decimal:
    mean = sum(values, Decimal(0)) / Decimal(len(values))
    return sum(
        ((value - mean) * (value - mean) for value in values),
        Decimal(0),
    )


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(f"{name} must be timezone-aware")
