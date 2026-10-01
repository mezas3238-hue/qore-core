"""Descriptive T16 hedge-candidate readiness audit.

This module measures only pre-decision hedge-candidate evidence: correlation
stability, basis residual, provider execution support and observed hedge cost.
It cannot prove net economic benefit, fresh OOS utility, sizing authority,
Risk authority or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


@dataclass(frozen=True, slots=True)
class T16HedgePairDeclaration:
    declaration_id: str
    provider_key: str
    target_symbol: str
    hedge_symbol: str
    declared_at: datetime
    evidence_sha256: str
    productive_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "declaration_id",
            "provider_key",
            "target_symbol",
            "hedge_symbol",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise CiboCapitalManagementError(
                    f"T16 hedge declaration {name} is required"
                )
        if self.target_symbol == self.hedge_symbol:
            raise CiboCapitalManagementError(
                "T16 hedge declaration requires distinct instruments"
            )
        _aware(self.declared_at, "T16 declaration declared_at")
        _sha(self.evidence_sha256, "declaration evidence_sha256")
        if type(self.productive_authority) is not bool:
            raise CiboCapitalManagementError(
                "T16 declaration productive_authority must be bool"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "T16 hedge declaration cannot carry productive authority"
            )


@dataclass(frozen=True, slots=True)
class T16HedgeReturnObservation:
    provider_key: str
    target_symbol: str
    hedge_symbol: str
    start_market_at: datetime
    end_market_at: datetime
    known_at: datetime
    target_return: Decimal
    hedge_return: Decimal
    hedge_cost_bps: Decimal
    execution_supported: bool
    source_evidence_sha256: str

    def __post_init__(self) -> None:
        if not self.provider_key or not self.target_symbol or not self.hedge_symbol:
            raise CiboCapitalManagementError(
                "T16 hedge observation identities are required"
            )
        if self.target_symbol == self.hedge_symbol:
            raise CiboCapitalManagementError(
                "T16 hedge candidate must use a distinct hedge instrument"
            )
        for name in ("start_market_at", "end_market_at", "known_at"):
            _aware(getattr(self, name), f"T16 {name}")
        if self.end_market_at <= self.start_market_at:
            raise CiboCapitalManagementError(
                "T16 hedge observation market interval must advance"
            )
        if self.known_at < self.end_market_at:
            raise CiboCapitalManagementError(
                "T16 hedge observation cannot be known before interval end"
            )
        for name in ("target_return", "hedge_return", "hedge_cost_bps"):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"T16 {name} must be finite Decimal"
                )
        if self.hedge_cost_bps < 0:
            raise CiboCapitalManagementError(
                "T16 hedge_cost_bps must be non-negative"
            )
        if type(self.execution_supported) is not bool:
            raise CiboCapitalManagementError(
                "T16 execution_supported must be bool"
            )
        _sha(self.source_evidence_sha256, "source_evidence_sha256")


@dataclass(frozen=True, slots=True)
class T16HedgeCandidateAudit:
    declaration_id: str
    provider_key: str | None
    target_symbol: str | None
    hedge_symbol: str | None
    decision_at: datetime
    sample_size: int
    minimum_samples: int
    required_folds: int
    correlation: Decimal | None
    hedge_beta: Decimal | None
    basis_error_rms: Decimal | None
    mean_hedge_cost_bps: Decimal | None
    sample_ready: bool
    fold_coverage_ready: bool
    correlation_stable: bool
    basis_risk_measured: bool
    hedge_cost_bound: bool
    execution_support_complete: bool
    measurement_ready: bool
    fresh_oos_utility_demonstrated: bool
    t16_policy_ready: bool
    productive_authority: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.declaration_id, str) or not self.declaration_id:
            raise CiboCapitalManagementError(
                "T16 hedge audit declaration_id is required"
            )
        _aware(self.decision_at, "T16 audit decision_at")
        if self.sample_size < 0 or self.minimum_samples < 2:
            raise CiboCapitalManagementError(
                "T16 hedge audit sample thresholds invalid"
            )
        if self.required_folds < 2:
            raise CiboCapitalManagementError(
                "T16 hedge audit requires at least two folds"
            )
        for value, name in (
            (self.correlation, "correlation"),
            (self.hedge_beta, "hedge_beta"),
            (self.basis_error_rms, "basis_error_rms"),
            (self.mean_hedge_cost_bps, "mean_hedge_cost_bps"),
        ):
            if value is not None and (
                not isinstance(value, Decimal) or not value.is_finite()
            ):
                raise CiboCapitalManagementError(
                    f"T16 hedge audit {name} must be finite Decimal/null"
                )
        if self.correlation is not None and not (
            Decimal("-1") <= self.correlation <= Decimal("1")
        ):
            raise CiboCapitalManagementError(
                "T16 hedge correlation must stay in [-1, 1]"
            )
        if self.basis_error_rms is not None and self.basis_error_rms < 0:
            raise CiboCapitalManagementError(
                "T16 basis error RMS must be non-negative"
            )
        if self.mean_hedge_cost_bps is not None and self.mean_hedge_cost_bps < 0:
            raise CiboCapitalManagementError(
                "T16 hedge cost must be non-negative"
            )
        for name in (
            "sample_ready",
            "fold_coverage_ready",
            "correlation_stable",
            "basis_risk_measured",
            "hedge_cost_bound",
            "execution_support_complete",
            "measurement_ready",
            "fresh_oos_utility_demonstrated",
            "t16_policy_ready",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"T16 hedge audit {name} must be bool"
                )
        expected_ready = all(
            (
                self.sample_ready,
                self.fold_coverage_ready,
                self.correlation_stable,
                self.basis_risk_measured,
                self.hedge_cost_bound,
                self.execution_support_complete,
            )
        )
        if self.measurement_ready != expected_ready:
            raise CiboCapitalManagementError(
                "T16 hedge measurement readiness drift"
            )
        if (
            self.fresh_oos_utility_demonstrated
            or self.t16_policy_ready
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "T16 descriptive audit cannot promote policy/runtime authority"
            )


def assess_t16_hedge_candidate(
    *,
    declaration: T16HedgePairDeclaration,
    observations: tuple[T16HedgeReturnObservation, ...],
    decision_at: datetime,
    minimum_samples: int = 30,
    required_folds: int = 4,
) -> T16HedgeCandidateAudit:
    """Measure a predeclared hedge pair without claiming economic utility."""

    if not isinstance(declaration, T16HedgePairDeclaration):
        raise CiboCapitalManagementError(
            "T16 hedge audit requires canonical declaration"
        )
    _aware(decision_at, "T16 audit decision_at")
    if declaration.declared_at > decision_at:
        raise CiboCapitalManagementError(
            "T16 hedge declaration cannot postdate decision"
        )
    if minimum_samples < 2:
        raise CiboCapitalManagementError(
            "T16 minimum_samples must be at least two"
        )
    if required_folds < 2:
        raise CiboCapitalManagementError(
            "T16 required_folds must be at least two"
        )
    if not observations:
        return _empty(
            declaration=declaration,
            decision_at=decision_at,
            minimum_samples=minimum_samples,
            required_folds=required_folds,
        )

    ordered = tuple(
        sorted(
            observations,
            key=lambda row: (
                row.end_market_at,
                row.start_market_at,
                row.source_evidence_sha256,
            ),
        )
    )
    providers = {row.provider_key for row in ordered}
    targets = {row.target_symbol for row in ordered}
    hedges = {row.hedge_symbol for row in ordered}
    if len(providers) != 1 or len(targets) != 1 or len(hedges) != 1:
        raise CiboCapitalManagementError(
            "T16 hedge audit requires one provider and one fixed pair"
        )
    identity = (
        next(iter(providers)),
        next(iter(targets)),
        next(iter(hedges)),
    )
    declared_identity = (
        declaration.provider_key,
        declaration.target_symbol,
        declaration.hedge_symbol,
    )
    if identity != declared_identity:
        raise CiboCapitalManagementError(
            "T16 hedge declaration/observation identity drift"
        )
    if declaration.declared_at > ordered[0].start_market_at:
        raise CiboCapitalManagementError(
            "T16 hedge pair must be declared before observed return windows"
        )
    for row in ordered:
        if row.known_at > decision_at:
            raise CiboCapitalManagementError(
                "T16 hedge audit contains future-known evidence"
            )
    for previous, current in zip(ordered, ordered[1:], strict=False):
        if current.start_market_at < previous.end_market_at:
            raise CiboCapitalManagementError(
                "T16 hedge observations must not overlap"
            )

    sample_ready = len(ordered) >= minimum_samples
    folds = _build_folds(ordered, required_folds=required_folds)
    fold_ready = len(folds) == required_folds

    target = tuple(row.target_return for row in ordered)
    hedge = tuple(row.hedge_return for row in ordered)
    correlation = _pearson(target, hedge)
    beta = _beta(target, hedge)
    basis_rms = (
        None
        if beta is None
        else _rms(
            tuple(
                target_value - beta * hedge_value
                for target_value, hedge_value in zip(
                    target,
                    hedge,
                    strict=True,
                )
            )
        )
    )
    correlation_stable = (
        sample_ready
        and fold_ready
        and correlation is not None
        and correlation != 0
        and _fold_signs_stable(folds, correlation)
    )
    execution_supported = all(row.execution_supported for row in ordered)
    mean_cost = sum(
        (row.hedge_cost_bps for row in ordered),
        Decimal(0),
    ) / Decimal(len(ordered))
    basis_measured = beta is not None and basis_rms is not None
    cost_bound = bool(ordered)

    blockers: list[str] = []
    if not sample_ready:
        blockers.append(
            f"T16_MINIMUM_SAMPLE_NOT_MET:{len(ordered)}/{minimum_samples}"
        )
    if not fold_ready:
        blockers.append(
            f"T16_FOLD_COVERAGE_NOT_MET:{len(folds)}/{required_folds}"
        )
    if correlation is None:
        blockers.append("T16_CORRELATION_NOT_IDENTIFIED")
    elif not correlation_stable:
        blockers.append("T16_CORRELATION_NOT_STABLE_ACROSS_FOLDS")
    if not basis_measured:
        blockers.append("T16_BASIS_RISK_NOT_IDENTIFIED")
    if not execution_supported:
        blockers.append("T16_PROVIDER_EXECUTION_SUPPORT_INCOMPLETE")
    blockers.extend(
        (
            "T16_NET_ECONOMIC_BENEFIT_NOT_PROVEN",
            "T16_FRESH_OOS_HEDGE_UTILITY_REQUIRED",
        )
    )

    measurement_ready = all(
        (
            sample_ready,
            fold_ready,
            correlation_stable,
            basis_measured,
            cost_bound,
            execution_supported,
        )
    )
    return T16HedgeCandidateAudit(
        declaration_id=declaration.declaration_id,
        provider_key=next(iter(providers)),
        target_symbol=next(iter(targets)),
        hedge_symbol=next(iter(hedges)),
        decision_at=decision_at,
        sample_size=len(ordered),
        minimum_samples=minimum_samples,
        required_folds=required_folds,
        correlation=correlation,
        hedge_beta=beta,
        basis_error_rms=basis_rms,
        mean_hedge_cost_bps=mean_cost,
        sample_ready=sample_ready,
        fold_coverage_ready=fold_ready,
        correlation_stable=correlation_stable,
        basis_risk_measured=basis_measured,
        hedge_cost_bound=cost_bound,
        execution_support_complete=execution_supported,
        measurement_ready=measurement_ready,
        fresh_oos_utility_demonstrated=False,
        t16_policy_ready=False,
        productive_authority=False,
        blockers=tuple(blockers),
    )


def _empty(
    *,
    declaration: T16HedgePairDeclaration,
    decision_at: datetime,
    minimum_samples: int,
    required_folds: int,
) -> T16HedgeCandidateAudit:
    return T16HedgeCandidateAudit(
        declaration_id=declaration.declaration_id,
        provider_key=declaration.provider_key,
        target_symbol=declaration.target_symbol,
        hedge_symbol=declaration.hedge_symbol,
        decision_at=decision_at,
        sample_size=0,
        minimum_samples=minimum_samples,
        required_folds=required_folds,
        correlation=None,
        hedge_beta=None,
        basis_error_rms=None,
        mean_hedge_cost_bps=None,
        sample_ready=False,
        fold_coverage_ready=False,
        correlation_stable=False,
        basis_risk_measured=False,
        hedge_cost_bound=False,
        execution_support_complete=False,
        measurement_ready=False,
        fresh_oos_utility_demonstrated=False,
        t16_policy_ready=False,
        productive_authority=False,
        blockers=(
            f"T16_MINIMUM_SAMPLE_NOT_MET:0/{minimum_samples}",
            f"T16_FOLD_COVERAGE_NOT_MET:0/{required_folds}",
            "T16_CORRELATION_NOT_IDENTIFIED",
            "T16_BASIS_RISK_NOT_IDENTIFIED",
            "T16_PROVIDER_EXECUTION_SUPPORT_INCOMPLETE",
            "T16_NET_ECONOMIC_BENEFIT_NOT_PROVEN",
            "T16_FRESH_OOS_HEDGE_UTILITY_REQUIRED",
        ),
    )


def _build_folds(
    observations: tuple[T16HedgeReturnObservation, ...],
    *,
    required_folds: int,
) -> tuple[tuple[T16HedgeReturnObservation, ...], ...]:
    if len(observations) < required_folds * 2:
        return ()
    base = len(observations) // required_folds
    extra = len(observations) % required_folds
    folds: list[tuple[T16HedgeReturnObservation, ...]] = []
    cursor = 0
    for index in range(required_folds):
        size = base + (1 if index < extra else 0)
        folds.append(observations[cursor : cursor + size])
        cursor += size
    return tuple(folds)


def _fold_signs_stable(
    folds: tuple[tuple[T16HedgeReturnObservation, ...], ...],
    full_correlation: Decimal,
) -> bool:
    expected_positive = full_correlation > 0
    for fold in folds:
        value = _pearson(
            tuple(row.target_return for row in fold),
            tuple(row.hedge_return for row in fold),
        )
        if value is None or value == 0 or (value > 0) != expected_positive:
            return False
    return True


def _beta(
    target: tuple[Decimal, ...],
    hedge: tuple[Decimal, ...],
) -> Decimal | None:
    if len(target) != len(hedge) or len(target) < 2:
        raise CiboCapitalManagementError(
            "T16 beta series must have equal length >= 2"
        )
    target_mean = sum(target, Decimal(0)) / Decimal(len(target))
    hedge_mean = sum(hedge, Decimal(0)) / Decimal(len(hedge))
    variance = sum(
        ((value - hedge_mean) * (value - hedge_mean) for value in hedge),
        Decimal(0),
    )
    if variance == 0:
        return None
    covariance = sum(
        (
            (target_value - target_mean) * (hedge_value - hedge_mean)
            for target_value, hedge_value in zip(target, hedge, strict=True)
        ),
        Decimal(0),
    )
    return covariance / variance


def _pearson(
    left: tuple[Decimal, ...],
    right: tuple[Decimal, ...],
) -> Decimal | None:
    if len(left) != len(right) or len(left) < 2:
        raise CiboCapitalManagementError(
            "T16 Pearson series must have equal length >= 2"
        )
    left_mean = sum(left, Decimal(0)) / Decimal(len(left))
    right_mean = sum(right, Decimal(0)) / Decimal(len(right))
    numerator = sum(
        (
            (left_value - left_mean) * (right_value - right_mean)
            for left_value, right_value in zip(left, right, strict=True)
        ),
        Decimal(0),
    )
    left_ss = sum(
        ((value - left_mean) * (value - left_mean) for value in left),
        Decimal(0),
    )
    right_ss = sum(
        ((value - right_mean) * (value - right_mean) for value in right),
        Decimal(0),
    )
    if left_ss == 0 or right_ss == 0:
        return None
    value = numerator / (left_ss * right_ss).sqrt()
    return min(Decimal(1), max(Decimal(-1), value))


def _rms(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        raise CiboCapitalManagementError(
            "T16 RMS requires non-empty values"
        )
    return (
        sum((value * value for value in values), Decimal(0))
        / Decimal(len(values))
    ).sqrt()


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(f"{name} must be timezone-aware")


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"T16 {name} must be canonical SHA-256"
        )
