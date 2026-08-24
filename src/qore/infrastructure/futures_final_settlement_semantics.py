from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeContractMonth,
    DerivativeContractMultiplier,
    DerivativeEvidenceRef,
    DerivativeTermsId,
    DerivativeTickValue,
    FuturesContractTerms,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.kernel.errors import InfrastructureError

_CODE_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_SECRET_MARKERS = ("token=", "secret=", "password=", "bearer ")


class FuturesFinalSettlementSemanticsError(InfrastructureError):
    """Base error for bounded futures final-settlement rule semantics."""

    __slots__ = ()


class FuturesFinalSettlementValidationError(FuturesFinalSettlementSemanticsError):
    """Violation of a futures final-settlement rule invariant."""

    __slots__ = ()


def _canonical_decimal(value: Decimal) -> str:
    parts = value.as_tuple()
    if all(digit == 0 for digit in parts.digits):
        return "0"

    digits = list(parts.digits)
    exponent = int(parts.exponent)
    while digits[-1] == 0:
        digits.pop()
        exponent += 1

    normalized = Decimal((parts.sign, tuple(digits), exponent))
    compact = str(normalized).lower()
    sign_length = 1 if parts.sign else 0

    if exponent >= 0:
        fixed_length = sign_length + len(digits) + exponent
    elif -exponent < len(digits):
        fixed_length = sign_length + len(digits) + 1
    else:
        fixed_length = sign_length + 2 - exponent

    if fixed_length <= len(compact) + 1:
        return format(normalized, "f")
    return compact


def _exact_uuid(value: UUID, field_name: str) -> None:
    if type(value) is not UUID:
        raise FuturesFinalSettlementValidationError(f"{field_name} must be exact UUID")


def _exact_decimal(value: Decimal, field_name: str, *, positive: bool = False) -> None:
    if type(value) is not Decimal or not value.is_finite():
        raise FuturesFinalSettlementValidationError(
            f"{field_name} must be a finite exact Decimal"
        )
    if positive and value <= 0:
        raise FuturesFinalSettlementValidationError(f"{field_name} must be positive")


def _exact_date(value: date, field_name: str) -> None:
    if type(value) is not date:
        raise FuturesFinalSettlementValidationError(f"{field_name} must be exact date")


def _exact_timestamp(value: datetime, field_name: str) -> None:
    if type(value) is not datetime:
        raise FuturesFinalSettlementValidationError(
            f"{field_name} must be exact datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise FuturesFinalSettlementValidationError(
            f"{field_name} must be timezone-aware"
        )


def _canonical_timestamp(value: datetime, field_name: str) -> str:
    _exact_timestamp(value, field_name)
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _code(value: str, field_name: str) -> None:
    if type(value) is not str or len(value) > 96 or _CODE_RE.fullmatch(value) is None:
        raise FuturesFinalSettlementValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )
    lowered = value.lower()
    if any(marker in lowered for marker in _SECRET_MARKERS):
        raise FuturesFinalSettlementValidationError(
            f"{field_name} must not contain secret-like material"
        )


def _revalidate_identity(value: EconomicIdentityId, field_name: str) -> None:
    if type(value) is not EconomicIdentityId:
        raise FuturesFinalSettlementValidationError(
            f"{field_name} must be exact EconomicIdentityId"
        )
    _exact_uuid(value.value, f"{field_name} value")
    value.__post_init__()


def _revalidate_futures_terms(value: FuturesContractTerms) -> None:
    """Revalidate UMI-05 futures leaves without owning generic futures semantics."""

    value.__post_init__()

    if type(value.terms_id) is not DerivativeTermsId:
        raise FuturesFinalSettlementValidationError(
            "futures terms_id must be exact DerivativeTermsId"
        )
    _exact_uuid(value.terms_id.value, "futures terms_id value")
    value.terms_id.__post_init__()

    _revalidate_identity(value.instrument_identity_id, "futures instrument identity")
    _revalidate_identity(value.reference_identity_id, "futures reference identity")
    _revalidate_identity(value.settlement_identity_id, "futures settlement identity")

    if type(value.contract_month) is not DerivativeContractMonth:
        raise FuturesFinalSettlementValidationError(
            "futures contract_month must be exact DerivativeContractMonth"
        )
    value.contract_month.__post_init__()

    if type(value.multiplier) is not DerivativeContractMultiplier:
        raise FuturesFinalSettlementValidationError(
            "futures multiplier must be exact DerivativeContractMultiplier"
        )
    _exact_decimal(value.multiplier.value, "futures multiplier value", positive=True)
    value.multiplier.__post_init__()
    _revalidate_identity(
        value.multiplier.unit_identity_id,
        "futures multiplier unit identity",
    )

    if type(value.evidence_ref) is not DerivativeEvidenceRef:
        raise FuturesFinalSettlementValidationError(
            "futures evidence_ref must be exact DerivativeEvidenceRef"
        )
    _exact_uuid(value.evidence_ref.value, "futures evidence_ref value")
    value.evidence_ref.__post_init__()

    if value.tick_value is not None:
        if type(value.tick_value) is not DerivativeTickValue:
            raise FuturesFinalSettlementValidationError(
                "futures tick_value must be exact DerivativeTickValue or None"
            )
        _exact_decimal(value.tick_value.value, "futures tick_value value", positive=True)
        value.tick_value.__post_init__()
        _revalidate_identity(
            value.tick_value.value_identity_id,
            "futures tick value identity",
        )


def _futures_terms_logical_values(value: FuturesContractTerms) -> tuple[object, ...]:
    """Preserve UMI-05 field layout without ambient Decimal-context dependence."""

    _revalidate_futures_terms(value)
    multiplier_values: tuple[object, ...] = (
        _canonical_decimal(value.multiplier.value),
        value.multiplier.unit_identity_id.logical_values(),
    )
    tick_values: tuple[object, ...] | None = None
    if value.tick_value is not None:
        tick_values = (
            _canonical_decimal(value.tick_value.value),
            value.tick_value.value_identity_id.logical_values(),
        )

    return (
        "futures",
        value.terms_id.logical_values(),
        value.instrument_identity_id.logical_values(),
        value.reference_identity_id.logical_values(),
        value.settlement_identity_id.logical_values(),
        value.contract_month.logical_values(),
        value.expiry_date.isoformat(),
        multiplier_values,
        value.settlement_style.value,
        value.evidence_ref.logical_values(),
        tick_values,
        value.first_notice_date.isoformat()
        if value.first_notice_date is not None
        else None,
        value.last_trade_date.isoformat() if value.last_trade_date is not None else None,
    )


@dataclass(frozen=True, slots=True)
class FuturesFinalSettlementRuleId:
    value: UUID

    def __post_init__(self) -> None:
        _exact_uuid(self.value, "futures final-settlement rule id")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class FuturesFinalSettlementEvidenceRef:
    """Opaque retained evidence reference; never evidence content."""

    value: UUID

    def __post_init__(self) -> None:
        _exact_uuid(self.value, "futures final-settlement evidence ref")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class FuturesFinalSettlementAlgorithmCode:
    """Contractual algorithm identifier; it implements no calculation engine."""

    value: str

    def __post_init__(self) -> None:
        _code(self.value, "futures final-settlement algorithm code")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class FuturesFinalSettlementInputRoleCode:
    """Contractual role of one settlement-rule input."""

    value: str

    def __post_init__(self) -> None:
        _code(self.value, "futures final-settlement input role code")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class FuturesFinalSettlementRoundingModeCode:
    """Contractual rounding-mode identifier; no rounding is executed here."""

    value: str

    def __post_init__(self) -> None:
        _code(self.value, "futures final-settlement rounding mode code")

    def logical_values(self) -> tuple[str, ...]:
        self.__post_init__()
        return (self.value,)


@dataclass(frozen=True, slots=True)
class FuturesFinalSettlementObservationWindow:
    """Explicit observation interval; no scheduler or data retrieval authority."""

    opened_at: datetime
    closed_at: datetime
    sampling_interval_seconds: int | None = None

    def __post_init__(self) -> None:
        _exact_timestamp(self.opened_at, "final-settlement observation opened_at")
        _exact_timestamp(self.closed_at, "final-settlement observation closed_at")
        if self.closed_at < self.opened_at:
            raise FuturesFinalSettlementValidationError(
                "final-settlement observation closed_at must not precede opened_at"
            )
        if self.sampling_interval_seconds is not None:
            if (
                type(self.sampling_interval_seconds) is not int
                or self.sampling_interval_seconds <= 0
            ):
                raise FuturesFinalSettlementValidationError(
                    "sampling_interval_seconds must be a positive exact int or None"
                )
            if self.closed_at == self.opened_at:
                raise FuturesFinalSettlementValidationError(
                    "point observation must not carry sampling_interval_seconds"
                )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            _canonical_timestamp(self.opened_at, "final-settlement observation opened_at"),
            _canonical_timestamp(self.closed_at, "final-settlement observation closed_at"),
            self.sampling_interval_seconds,
        )


@dataclass(frozen=True, slots=True)
class FuturesFinalSettlementInput:
    """One static reference/input declaration for the settlement rule."""

    reference_identity_id: EconomicIdentityId
    role: FuturesFinalSettlementInputRoleCode
    observation_window: FuturesFinalSettlementObservationWindow | None = None
    fixed_weight: Decimal | None = None

    def __post_init__(self) -> None:
        _revalidate_identity(
            self.reference_identity_id,
            "final-settlement input reference identity",
        )
        if type(self.role) is not FuturesFinalSettlementInputRoleCode:
            raise FuturesFinalSettlementValidationError(
                "final-settlement input role must be exact FuturesFinalSettlementInputRoleCode"
            )
        self.role.__post_init__()
        if self.observation_window is not None:
            if type(self.observation_window) is not FuturesFinalSettlementObservationWindow:
                raise FuturesFinalSettlementValidationError(
                    "observation_window must be exact FuturesFinalSettlementObservationWindow or None"
                )
            self.observation_window.__post_init__()
        if self.fixed_weight is not None:
            _exact_decimal(
                self.fixed_weight,
                "final-settlement input fixed_weight",
                positive=True,
            )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            self.reference_identity_id.logical_values(),
            self.role.logical_values(),
            self.observation_window.logical_values()
            if self.observation_window is not None
            else None,
            _canonical_decimal(self.fixed_weight)
            if self.fixed_weight is not None
            else None,
        )


def _input_sort_key(
    value: FuturesFinalSettlementInput,
) -> tuple[str, str, int, str, str, str, int, str]:
    value.__post_init__()
    window = value.observation_window
    if window is None:
        window_present = 0
        opened_at = ""
        closed_at = ""
        sampling_interval = ""
    else:
        window_present = 1
        opened_at = _canonical_timestamp(
            window.opened_at,
            "final-settlement observation opened_at",
        )
        closed_at = _canonical_timestamp(
            window.closed_at,
            "final-settlement observation closed_at",
        )
        sampling_interval = (
            str(window.sampling_interval_seconds)
            if window.sampling_interval_seconds is not None
            else ""
        )
    weight_present = 1 if value.fixed_weight is not None else 0
    weight = (
        _canonical_decimal(value.fixed_weight)
        if value.fixed_weight is not None
        else ""
    )
    return (
        str(value.reference_identity_id.value),
        value.role.value,
        window_present,
        opened_at,
        closed_at,
        sampling_interval,
        weight_present,
        weight,
    )


@dataclass(frozen=True, slots=True)
class FuturesFinalSettlementRoundingRule:
    """Static rounding convention only; no numeric result is produced."""

    mode: FuturesFinalSettlementRoundingModeCode
    increment: Decimal

    def __post_init__(self) -> None:
        if type(self.mode) is not FuturesFinalSettlementRoundingModeCode:
            raise FuturesFinalSettlementValidationError(
                "rounding mode must be exact FuturesFinalSettlementRoundingModeCode"
            )
        self.mode.__post_init__()
        _exact_decimal(
            self.increment,
            "final-settlement rounding increment",
            positive=True,
        )

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (self.mode.logical_values(), _canonical_decimal(self.increment))


@dataclass(frozen=True, slots=True)
class FuturesFinalSettlementRule:
    """Static product-specific final-settlement determination rule."""

    rule_id: FuturesFinalSettlementRuleId
    futures_terms: FuturesContractTerms
    algorithm: FuturesFinalSettlementAlgorithmCode
    final_settlement_date: date
    inputs: tuple[FuturesFinalSettlementInput, ...]
    evidence_ref: FuturesFinalSettlementEvidenceRef
    rounding: FuturesFinalSettlementRoundingRule | None = None

    def __post_init__(self) -> None:
        if type(self.rule_id) is not FuturesFinalSettlementRuleId:
            raise FuturesFinalSettlementValidationError(
                "rule_id must be exact FuturesFinalSettlementRuleId"
            )
        self.rule_id.__post_init__()

        if type(self.futures_terms) is not FuturesContractTerms:
            raise FuturesFinalSettlementValidationError(
                "futures_terms must be exact FuturesContractTerms"
            )
        _revalidate_futures_terms(self.futures_terms)

        if type(self.algorithm) is not FuturesFinalSettlementAlgorithmCode:
            raise FuturesFinalSettlementValidationError(
                "algorithm must be exact FuturesFinalSettlementAlgorithmCode"
            )
        self.algorithm.__post_init__()

        _exact_date(self.final_settlement_date, "final_settlement_date")

        if type(self.inputs) is not tuple or not self.inputs:
            raise FuturesFinalSettlementValidationError(
                "final-settlement inputs must be a non-empty immutable tuple"
            )
        for input_value in self.inputs:
            if type(input_value) is not FuturesFinalSettlementInput:
                raise FuturesFinalSettlementValidationError(
                    "final-settlement inputs must contain exact FuturesFinalSettlementInput"
                )
            input_value.__post_init__()

        ordered = tuple(sorted(self.inputs, key=_input_sort_key))
        logical_inputs = tuple(value.logical_values() for value in ordered)
        if len(set(logical_inputs)) != len(logical_inputs):
            raise FuturesFinalSettlementValidationError(
                "final-settlement inputs must not contain duplicate logical declarations"
            )
        object.__setattr__(self, "inputs", ordered)

        if self.rounding is not None:
            if type(self.rounding) is not FuturesFinalSettlementRoundingRule:
                raise FuturesFinalSettlementValidationError(
                    "rounding must be exact FuturesFinalSettlementRoundingRule or None"
                )
            self.rounding.__post_init__()

        if type(self.evidence_ref) is not FuturesFinalSettlementEvidenceRef:
            raise FuturesFinalSettlementValidationError(
                "evidence_ref must be exact FuturesFinalSettlementEvidenceRef"
            )
        self.evidence_ref.__post_init__()

    def logical_values(self) -> tuple[object, ...]:
        self.__post_init__()
        return (
            "futures-final-settlement-rule",
            self.rule_id.logical_values(),
            _futures_terms_logical_values(self.futures_terms),
            self.algorithm.logical_values(),
            self.final_settlement_date.isoformat(),
            tuple(value.logical_values() for value in self.inputs),
            self.rounding.logical_values() if self.rounding is not None else None,
            self.evidence_ref.logical_values(),
        )
