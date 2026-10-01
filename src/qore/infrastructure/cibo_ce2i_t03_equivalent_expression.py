"""Fail-closed T03 equivalent-expression economics.

T03 may compare margin only after two expressions prove the same normalized
economic exposure. This module never discovers instruments by name and never
assumes that lower margin means lower risk. Candidate expressions must arrive
with provider-bound economics and a pre-decision normalized exposure vector.

The audit is descriptive research evidence only. Fresh OOS economic utility,
sizing authority, Risk authority and execution authority remain separate gates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


@dataclass(frozen=True, slots=True)
class T03NormalizedExposureComponent:
    factor_id: str
    signed_exposure_usd: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.factor_id, str) or not self.factor_id.strip():
            raise CiboCapitalManagementError(
                "T03 normalized exposure factor_id is required"
            )
        if (
            not isinstance(self.signed_exposure_usd, Decimal)
            or not self.signed_exposure_usd.is_finite()
            or self.signed_exposure_usd == 0
        ):
            raise CiboCapitalManagementError(
                "T03 normalized exposure must be finite non-zero Decimal"
            )


@dataclass(frozen=True, slots=True)
class T03ExpressionEconomics:
    provider_key: str
    account_fingerprint_sha256: str
    qore_symbol: str
    provider_symbol: str
    observed_at: datetime
    known_at: datetime
    normalized_exposure: tuple[T03NormalizedExposureComponent, ...]
    margin_occupancy_usd: Decimal
    stop_risk_usd: Decimal
    stressed_loss_usd: Decimal
    execution_cost_usd: Decimal
    provider_verified: bool
    execution_supported: bool
    evidence_sha256: str

    def __post_init__(self) -> None:
        for name in ("provider_key", "qore_symbol", "provider_symbol"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise CiboCapitalManagementError(
                    f"T03 expression {name} is required"
                )
        _hex_sha(self.account_fingerprint_sha256, "account_fingerprint_sha256")
        _canonical_sha(self.evidence_sha256, "evidence_sha256")
        _aware(self.observed_at, "observed_at")
        _aware(self.known_at, "known_at")
        if self.known_at < self.observed_at:
            raise CiboCapitalManagementError(
                "T03 expression cannot be known before provider observation"
            )
        if not self.normalized_exposure:
            raise CiboCapitalManagementError(
                "T03 expression requires normalized exposure"
            )
        if any(
            not isinstance(item, T03NormalizedExposureComponent)
            for item in self.normalized_exposure
        ):
            raise CiboCapitalManagementError(
                "T03 normalized exposure component invalid"
            )
        factor_ids = tuple(item.factor_id for item in self.normalized_exposure)
        if factor_ids != tuple(sorted(factor_ids)) or len(factor_ids) != len(
            set(factor_ids)
        ):
            raise CiboCapitalManagementError(
                "T03 normalized exposure factors must be sorted unique"
            )
        for name in (
            "margin_occupancy_usd",
            "stop_risk_usd",
            "stressed_loss_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"T03 expression {name} must be finite positive Decimal"
                )
        if (
            not isinstance(self.execution_cost_usd, Decimal)
            or not self.execution_cost_usd.is_finite()
            or self.execution_cost_usd < 0
        ):
            raise CiboCapitalManagementError(
                "T03 expression execution_cost_usd must be non-negative"
            )
        for name in ("provider_verified", "execution_supported"):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"T03 expression {name} must be bool"
                )


@dataclass(frozen=True, slots=True)
class T03EquivalentExpressionAudit:
    decision_at: datetime
    target_provider_symbol: str
    candidate_provider_symbol: str
    normalized_exposure_equivalent: bool
    provider_scope_match: bool
    provider_evidence_complete: bool
    execution_support_complete: bool
    lower_margin: bool
    no_stop_risk_increase: bool
    no_stressed_loss_increase: bool
    margin_saved_usd: Decimal
    margin_reduction_fraction: Decimal
    stop_risk_delta_usd: Decimal
    stressed_loss_delta_usd: Decimal
    execution_cost_delta_usd: Decimal
    mechanically_eligible: bool
    fresh_oos_utility_demonstrated: bool
    t03_policy_ready: bool
    productive_authority: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        _aware(self.decision_at, "audit decision_at")
        for name in (
            "normalized_exposure_equivalent",
            "provider_scope_match",
            "provider_evidence_complete",
            "execution_support_complete",
            "lower_margin",
            "no_stop_risk_increase",
            "no_stressed_loss_increase",
            "mechanically_eligible",
            "fresh_oos_utility_demonstrated",
            "t03_policy_ready",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"T03 equivalent-expression {name} must be bool"
                )
        for name in (
            "margin_saved_usd",
            "margin_reduction_fraction",
            "stop_risk_delta_usd",
            "stressed_loss_delta_usd",
            "execution_cost_delta_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"T03 equivalent-expression {name} must be finite Decimal"
                )
        expected = all(
            (
                self.normalized_exposure_equivalent,
                self.provider_scope_match,
                self.provider_evidence_complete,
                self.execution_support_complete,
                self.lower_margin,
                self.no_stop_risk_increase,
                self.no_stressed_loss_increase,
            )
        )
        if self.mechanically_eligible != expected:
            raise CiboCapitalManagementError(
                "T03 equivalent-expression eligibility drift"
            )
        if (
            self.fresh_oos_utility_demonstrated
            or self.t03_policy_ready
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "T03 mechanical audit cannot promote policy/runtime authority"
            )


def assess_t03_equivalent_expression(
    *,
    target: T03ExpressionEconomics,
    candidate: T03ExpressionEconomics,
    decision_at: datetime,
) -> T03EquivalentExpressionAudit:
    """Compare one predeclared provider-verified candidate to its target."""

    if not isinstance(target, T03ExpressionEconomics) or not isinstance(
        candidate,
        T03ExpressionEconomics,
    ):
        raise CiboCapitalManagementError(
            "T03 equivalent-expression audit requires canonical economics"
        )
    _aware(decision_at, "audit decision_at")
    if target.known_at > decision_at or candidate.known_at > decision_at:
        raise CiboCapitalManagementError(
            "T03 equivalent-expression audit contains future-known evidence"
        )
    if (
        target.provider_symbol == candidate.provider_symbol
        and target.qore_symbol == candidate.qore_symbol
    ):
        raise CiboCapitalManagementError(
            "T03 equivalent-expression candidate must be a distinct expression"
        )

    equivalent = target.normalized_exposure == candidate.normalized_exposure
    provider_scope = (
        target.provider_key == candidate.provider_key
        and target.account_fingerprint_sha256
        == candidate.account_fingerprint_sha256
    )
    provider_evidence = target.provider_verified and candidate.provider_verified
    execution_support = (
        target.execution_supported and candidate.execution_supported
    )
    margin_saved = (
        target.margin_occupancy_usd - candidate.margin_occupancy_usd
    )
    lower_margin = margin_saved > 0
    margin_fraction = margin_saved / target.margin_occupancy_usd
    stop_delta = candidate.stop_risk_usd - target.stop_risk_usd
    stressed_delta = candidate.stressed_loss_usd - target.stressed_loss_usd
    execution_delta = (
        candidate.execution_cost_usd - target.execution_cost_usd
    )
    no_stop_increase = stop_delta <= 0
    no_stressed_increase = stressed_delta <= 0

    blockers: list[str] = []
    if not equivalent:
        blockers.append("T03_NORMALIZED_EXPOSURE_NOT_EQUIVALENT")
    if not provider_scope:
        blockers.append("T03_PROVIDER_ACCOUNT_SCOPE_MISMATCH")
    if not provider_evidence:
        blockers.append("T03_PROVIDER_EVIDENCE_NOT_VERIFIED")
    if not execution_support:
        blockers.append("T03_EXECUTION_SUPPORT_INCOMPLETE")
    if not lower_margin:
        blockers.append("T03_MARGIN_ADVANTAGE_NOT_PRESENT")
    if not no_stop_increase:
        blockers.append("T03_STOP_RISK_INCREASES")
    if not no_stressed_increase:
        blockers.append("T03_STRESSED_LOSS_INCREASES")
    blockers.extend(
        (
            "T03_FRESH_OOS_EQUIVALENT_EXPRESSION_UTILITY_REQUIRED",
            "T03_HISTORICAL_2017_MARGIN_TERMS_NOT_PROVEN",
        )
    )

    mechanical = all(
        (
            equivalent,
            provider_scope,
            provider_evidence,
            execution_support,
            lower_margin,
            no_stop_increase,
            no_stressed_increase,
        )
    )
    return T03EquivalentExpressionAudit(
        decision_at=decision_at,
        target_provider_symbol=target.provider_symbol,
        candidate_provider_symbol=candidate.provider_symbol,
        normalized_exposure_equivalent=equivalent,
        provider_scope_match=provider_scope,
        provider_evidence_complete=provider_evidence,
        execution_support_complete=execution_support,
        lower_margin=lower_margin,
        no_stop_risk_increase=no_stop_increase,
        no_stressed_loss_increase=no_stressed_increase,
        margin_saved_usd=margin_saved,
        margin_reduction_fraction=margin_fraction,
        stop_risk_delta_usd=stop_delta,
        stressed_loss_delta_usd=stressed_delta,
        execution_cost_delta_usd=execution_delta,
        mechanically_eligible=mechanical,
        fresh_oos_utility_demonstrated=False,
        t03_policy_ready=False,
        productive_authority=False,
        blockers=tuple(blockers),
    )


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(f"T03 {name} must be timezone-aware")


def _canonical_sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"T03 {name} must be canonical SHA-256"
        )


def _hex_sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise CiboCapitalManagementError(
            f"T03 {name} must be lowercase SHA-256 hex"
        )
