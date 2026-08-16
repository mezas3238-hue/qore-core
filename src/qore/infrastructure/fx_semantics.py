from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.derivative_contract_semantics import (
    DerivativeStrikeBasis,
    OptionContractTerms,
)
from qore.infrastructure.universal_instrument_identity import EconomicIdentityId
from qore.kernel.errors import InfrastructureError


class FxSemanticsError(InfrastructureError):
    """Base error for provider-neutral static FX contract semantics."""

    __slots__ = ()


class FxValidationError(FxSemanticsError):
    """Violation of an FX static-contract semantic invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise FxValidationError(f"{field_name} must be UUID")


def _validate_identity(value: EconomicIdentityId, *, field_name: str) -> None:
    if not isinstance(value, EconomicIdentityId):
        raise FxValidationError(f"{field_name} must be EconomicIdentityId")


def _validate_date(value: date, *, field_name: str) -> None:
    if type(value) is not date:
        raise FxValidationError(f"{field_name} must be date")


def _validate_decimal(
    value: Decimal,
    *,
    field_name: str,
    positive: bool = False,
) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise FxValidationError(f"{field_name} must be a finite Decimal")
    if positive and value <= 0:
        raise FxValidationError(f"{field_name} must be positive")


def _canonical_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


@dataclass(frozen=True, slots=True)
class FxTermsId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="FX terms id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class FxEvidenceRef:
    """Opaque reference to retained FX evidence; never evidence content."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="FX evidence ref")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class FxSwapLegId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="FX swap leg id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class FxQuoteBasis(StrEnum):
    CURRENCY1_PER_CURRENCY2 = "currency1-per-currency2"
    CURRENCY2_PER_CURRENCY1 = "currency2-per-currency1"


class FxFlowDirection(StrEnum):
    PAY = "pay"
    RECEIVE = "receive"


class FxForwardDeliveryKind(StrEnum):
    DELIVERABLE = "deliverable"
    NON_DELIVERABLE = "non-deliverable"


@dataclass(frozen=True, slots=True)
class FxCurrencyAmount:
    value: Decimal
    currency_identity_id: EconomicIdentityId

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="FX currency amount", positive=True)
        _validate_identity(
            self.currency_identity_id,
            field_name="FX currency amount identity",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            _canonical_decimal(self.value),
            self.currency_identity_id.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class FxCurrencyFlow:
    direction: FxFlowDirection
    amount: FxCurrencyAmount

    def __post_init__(self) -> None:
        if not isinstance(self.direction, FxFlowDirection):
            raise FxValidationError("FX flow direction must be FxFlowDirection")
        if not isinstance(self.amount, FxCurrencyAmount):
            raise FxValidationError("FX flow amount must be FxCurrencyAmount")

    def logical_values(self) -> tuple[object, ...]:
        return (self.direction.value, self.amount.logical_values())


@dataclass(frozen=True, slots=True)
class FxQuotedCurrencyPair:
    pair_identity_id: EconomicIdentityId
    currency1_identity_id: EconomicIdentityId
    currency2_identity_id: EconomicIdentityId
    quote_basis: FxQuoteBasis
    evidence_ref: FxEvidenceRef

    def __post_init__(self) -> None:
        _validate_identity(self.pair_identity_id, field_name="FX pair identity")
        _validate_identity(self.currency1_identity_id, field_name="FX currency1 identity")
        _validate_identity(self.currency2_identity_id, field_name="FX currency2 identity")
        if self.currency1_identity_id == self.currency2_identity_id:
            raise FxValidationError("FX quoted-pair currencies must differ")
        if self.pair_identity_id in (
            self.currency1_identity_id,
            self.currency2_identity_id,
        ):
            raise FxValidationError("FX pair identity must differ from currency identities")
        if not isinstance(self.quote_basis, FxQuoteBasis):
            raise FxValidationError("FX quote basis must be FxQuoteBasis")
        if not isinstance(self.evidence_ref, FxEvidenceRef):
            raise FxValidationError("FX pair evidence_ref must be FxEvidenceRef")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fx-quoted-currency-pair",
            self.pair_identity_id.logical_values(),
            self.currency1_identity_id.logical_values(),
            self.currency2_identity_id.logical_values(),
            self.quote_basis.value,
            self.evidence_ref.logical_values(),
        )


def _same_quoted_pair_relationship(
    left: FxQuotedCurrencyPair,
    right: FxQuotedCurrencyPair,
) -> bool:
    return (
        left.pair_identity_id == right.pair_identity_id
        and left.currency1_identity_id == right.currency1_identity_id
        and left.currency2_identity_id == right.currency2_identity_id
        and left.quote_basis is right.quote_basis
    )


def _fx_quote_identity(quoted_pair: FxQuotedCurrencyPair) -> EconomicIdentityId:
    if quoted_pair.quote_basis is FxQuoteBasis.CURRENCY1_PER_CURRENCY2:
        return quoted_pair.currency1_identity_id
    return quoted_pair.currency2_identity_id


@dataclass(frozen=True, slots=True)
class FxExchangeRate:
    value: Decimal
    pair_identity_id: EconomicIdentityId
    quote_basis: FxQuoteBasis

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="FX exchange rate", positive=True)
        _validate_identity(self.pair_identity_id, field_name="FX rate pair identity")
        if not isinstance(self.quote_basis, FxQuoteBasis):
            raise FxValidationError("FX rate quote basis must be FxQuoteBasis")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fx-exchange-rate",
            _canonical_decimal(self.value),
            self.pair_identity_id.logical_values(),
            self.quote_basis.value,
        )


@dataclass(frozen=True, slots=True)
class FxValueDates:
    currency1_value_date: date
    currency2_value_date: date

    def __post_init__(self) -> None:
        _validate_date(self.currency1_value_date, field_name="FX currency1 value date")
        _validate_date(self.currency2_value_date, field_name="FX currency2 value date")

    def logical_values(self) -> tuple[str, str]:
        return (
            self.currency1_value_date.isoformat(),
            self.currency2_value_date.isoformat(),
        )


def _validated_flows(
    quoted_pair: FxQuotedCurrencyPair,
    flows: tuple[FxCurrencyFlow, ...],
) -> tuple[FxCurrencyFlow, ...]:
    if type(flows) is not tuple:
        raise FxValidationError("FX exchange flows must be an immutable tuple")
    if len(flows) != 2:
        raise FxValidationError("FX exchange must have exactly two currency flows")
    for flow in flows:
        if not isinstance(flow, FxCurrencyFlow):
            raise FxValidationError("FX exchange flows must contain FxCurrencyFlow")

    directions = {flow.direction for flow in flows}
    if directions != {FxFlowDirection.PAY, FxFlowDirection.RECEIVE}:
        raise FxValidationError("FX exchange must contain one PAY and one RECEIVE flow")

    currencies = {flow.amount.currency_identity_id for flow in flows}
    expected = {
        quoted_pair.currency1_identity_id,
        quoted_pair.currency2_identity_id,
    }
    if currencies != expected:
        raise FxValidationError(
            "FX exchange flows must cover exactly the quoted-pair currencies"
        )

    return tuple(sorted(flows, key=lambda flow: flow.direction.value))


def _validate_exchange_rate_binding(
    quoted_pair: FxQuotedCurrencyPair,
    exchange_rate: FxExchangeRate,
    *,
    field_name: str,
) -> None:
    if not isinstance(exchange_rate, FxExchangeRate):
        raise FxValidationError(f"{field_name} must be FxExchangeRate")
    if exchange_rate.pair_identity_id != quoted_pair.pair_identity_id:
        raise FxValidationError(f"{field_name} pair identity must match quoted pair")
    if exchange_rate.quote_basis is not quoted_pair.quote_basis:
        raise FxValidationError(f"{field_name} quote basis must match quoted pair")


def _validate_currency_amount_pair(
    quoted_pair: FxQuotedCurrencyPair,
    put_currency_amount: FxCurrencyAmount,
    call_currency_amount: FxCurrencyAmount,
) -> None:
    if not isinstance(put_currency_amount, FxCurrencyAmount):
        raise FxValidationError("FX option put amount must be FxCurrencyAmount")
    if not isinstance(call_currency_amount, FxCurrencyAmount):
        raise FxValidationError("FX option call amount must be FxCurrencyAmount")
    if put_currency_amount.currency_identity_id == call_currency_amount.currency_identity_id:
        raise FxValidationError("FX option put and call currencies must differ")
    actual = {
        put_currency_amount.currency_identity_id,
        call_currency_amount.currency_identity_id,
    }
    expected = {
        quoted_pair.currency1_identity_id,
        quoted_pair.currency2_identity_id,
    }
    if actual != expected:
        raise FxValidationError(
            "FX option put/call amounts must cover exactly the quoted-pair currencies"
        )


def _validate_option_strike_binding(
    quoted_pair: FxQuotedCurrencyPair,
    option_terms: OptionContractTerms,
) -> None:
    strike = option_terms.strike
    if strike.basis is not DerivativeStrikeBasis.PRICE:
        raise FxValidationError("FX option strike basis must be PRICE")
    if strike.quote_identity_id != _fx_quote_identity(quoted_pair):
        raise FxValidationError(
            "FX option strike quote identity must match the quoted-pair quote currency"
        )
    if (
        strike.price_quote_basis is None
        or strike.price_quote_basis.value != quoted_pair.quote_basis.value
    ):
        raise FxValidationError(
            "FX option strike quote basis must match the quoted-pair quote basis"
        )


@dataclass(frozen=True, slots=True)
class FxFixingTerms:
    fixing_date: date
    fixing_reference_identity_id: EconomicIdentityId
    evidence_ref: FxEvidenceRef

    def __post_init__(self) -> None:
        _validate_date(self.fixing_date, field_name="FX fixing date")
        _validate_identity(
            self.fixing_reference_identity_id,
            field_name="FX fixing reference identity",
        )
        if not isinstance(self.evidence_ref, FxEvidenceRef):
            raise FxValidationError("FX fixing evidence_ref must be FxEvidenceRef")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fx-fixing-terms",
            self.fixing_date.isoformat(),
            self.fixing_reference_identity_id.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class FxNonDeliverableSettlementTerms:
    settlement_currency_identity_id: EconomicIdentityId
    fixing: FxFixingTerms
    evidence_ref: FxEvidenceRef
    settlement_date: date | None = None

    def __post_init__(self) -> None:
        _validate_identity(
            self.settlement_currency_identity_id,
            field_name="NDF settlement currency identity",
        )
        if not isinstance(self.fixing, FxFixingTerms):
            raise FxValidationError("NDF fixing must be FxFixingTerms")
        if not isinstance(self.evidence_ref, FxEvidenceRef):
            raise FxValidationError("NDF evidence_ref must be FxEvidenceRef")
        if self.settlement_date is not None:
            _validate_date(self.settlement_date, field_name="NDF settlement date")
            if self.fixing.fixing_date > self.settlement_date:
                raise FxValidationError(
                    "NDF fixing date must not be after settlement date"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fx-non-deliverable-settlement-terms",
            self.settlement_currency_identity_id.logical_values(),
            self.fixing.logical_values(),
            self.settlement_date.isoformat() if self.settlement_date is not None else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class FxSpotTerms:
    terms_id: FxTermsId
    instrument_identity_id: EconomicIdentityId
    quoted_pair: FxQuotedCurrencyPair
    flows: tuple[FxCurrencyFlow, ...]
    value_dates: FxValueDates
    agreed_exchange_rate: FxExchangeRate
    evidence_ref: FxEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, FxTermsId):
            raise FxValidationError("FX spot terms_id must be FxTermsId")
        _validate_identity(
            self.instrument_identity_id,
            field_name="FX spot instrument identity",
        )
        if not isinstance(self.quoted_pair, FxQuotedCurrencyPair):
            raise FxValidationError("FX spot quoted_pair must be FxQuotedCurrencyPair")
        if self.instrument_identity_id == self.quoted_pair.pair_identity_id:
            raise FxValidationError("FX spot instrument identity must differ from pair identity")
        if not isinstance(self.value_dates, FxValueDates):
            raise FxValidationError("FX spot value_dates must be FxValueDates")
        _validate_exchange_rate_binding(
            self.quoted_pair,
            self.agreed_exchange_rate,
            field_name="FX spot exchange rate",
        )
        if not isinstance(self.evidence_ref, FxEvidenceRef):
            raise FxValidationError("FX spot evidence_ref must be FxEvidenceRef")
        object.__setattr__(self, "flows", _validated_flows(self.quoted_pair, self.flows))

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fx-spot-terms",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.quoted_pair.logical_values(),
            tuple(flow.logical_values() for flow in self.flows),
            self.value_dates.logical_values(),
            self.agreed_exchange_rate.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class FxForwardTerms:
    terms_id: FxTermsId
    instrument_identity_id: EconomicIdentityId
    quoted_pair: FxQuotedCurrencyPair
    flows: tuple[FxCurrencyFlow, ...]
    value_dates: FxValueDates
    agreed_exchange_rate: FxExchangeRate
    delivery_kind: FxForwardDeliveryKind
    evidence_ref: FxEvidenceRef
    non_deliverable_settlement: FxNonDeliverableSettlementTerms | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, FxTermsId):
            raise FxValidationError("FX forward terms_id must be FxTermsId")
        _validate_identity(
            self.instrument_identity_id,
            field_name="FX forward instrument identity",
        )
        if not isinstance(self.quoted_pair, FxQuotedCurrencyPair):
            raise FxValidationError("FX forward quoted_pair must be FxQuotedCurrencyPair")
        if self.instrument_identity_id == self.quoted_pair.pair_identity_id:
            raise FxValidationError(
                "FX forward instrument identity must differ from pair identity"
            )
        if not isinstance(self.value_dates, FxValueDates):
            raise FxValidationError("FX forward value_dates must be FxValueDates")
        _validate_exchange_rate_binding(
            self.quoted_pair,
            self.agreed_exchange_rate,
            field_name="FX forward exchange rate",
        )
        if not isinstance(self.delivery_kind, FxForwardDeliveryKind):
            raise FxValidationError(
                "FX forward delivery_kind must be FxForwardDeliveryKind"
            )
        if not isinstance(self.evidence_ref, FxEvidenceRef):
            raise FxValidationError("FX forward evidence_ref must be FxEvidenceRef")

        if self.delivery_kind is FxForwardDeliveryKind.DELIVERABLE:
            if self.non_deliverable_settlement is not None:
                raise FxValidationError(
                    "deliverable FX forward must not carry NDF settlement terms"
                )
        elif not isinstance(
            self.non_deliverable_settlement,
            FxNonDeliverableSettlementTerms,
        ):
            raise FxValidationError(
                "non-deliverable FX forward requires NDF settlement terms"
            )

        object.__setattr__(self, "flows", _validated_flows(self.quoted_pair, self.flows))

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fx-forward-terms",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.quoted_pair.logical_values(),
            tuple(flow.logical_values() for flow in self.flows),
            self.value_dates.logical_values(),
            self.agreed_exchange_rate.logical_values(),
            self.delivery_kind.value,
            self.non_deliverable_settlement.logical_values()
            if self.non_deliverable_settlement is not None
            else None,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class FxSwapLegTerms:
    leg_id: FxSwapLegId
    quoted_pair: FxQuotedCurrencyPair
    flows: tuple[FxCurrencyFlow, ...]
    value_dates: FxValueDates
    agreed_exchange_rate: FxExchangeRate
    evidence_ref: FxEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.leg_id, FxSwapLegId):
            raise FxValidationError("FX swap leg_id must be FxSwapLegId")
        if not isinstance(self.quoted_pair, FxQuotedCurrencyPair):
            raise FxValidationError("FX swap leg pair must be FxQuotedCurrencyPair")
        if not isinstance(self.value_dates, FxValueDates):
            raise FxValidationError("FX swap leg value_dates must be FxValueDates")
        _validate_exchange_rate_binding(
            self.quoted_pair,
            self.agreed_exchange_rate,
            field_name="FX swap-leg exchange rate",
        )
        if not isinstance(self.evidence_ref, FxEvidenceRef):
            raise FxValidationError("FX swap leg evidence_ref must be FxEvidenceRef")
        object.__setattr__(self, "flows", _validated_flows(self.quoted_pair, self.flows))

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fx-swap-leg-terms",
            self.leg_id.logical_values(),
            self.quoted_pair.logical_values(),
            tuple(flow.logical_values() for flow in self.flows),
            self.value_dates.logical_values(),
            self.agreed_exchange_rate.logical_values(),
            self.evidence_ref.logical_values(),
        )


def _reverse_direction(direction: FxFlowDirection) -> FxFlowDirection:
    if direction is FxFlowDirection.PAY:
        return FxFlowDirection.RECEIVE
    return FxFlowDirection.PAY


@dataclass(frozen=True, slots=True)
class FxSwapTerms:
    terms_id: FxTermsId
    instrument_identity_id: EconomicIdentityId
    quoted_pair: FxQuotedCurrencyPair
    near_leg: FxSwapLegTerms
    far_leg: FxSwapLegTerms
    evidence_ref: FxEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.terms_id, FxTermsId):
            raise FxValidationError("FX swap terms_id must be FxTermsId")
        _validate_identity(
            self.instrument_identity_id,
            field_name="FX swap instrument identity",
        )
        if not isinstance(self.quoted_pair, FxQuotedCurrencyPair):
            raise FxValidationError("FX swap quoted_pair must be FxQuotedCurrencyPair")
        if self.instrument_identity_id == self.quoted_pair.pair_identity_id:
            raise FxValidationError("FX swap instrument identity must differ from pair identity")
        if not isinstance(self.near_leg, FxSwapLegTerms):
            raise FxValidationError("FX swap near_leg must be FxSwapLegTerms")
        if not isinstance(self.far_leg, FxSwapLegTerms):
            raise FxValidationError("FX swap far_leg must be FxSwapLegTerms")
        if not isinstance(self.evidence_ref, FxEvidenceRef):
            raise FxValidationError("FX swap evidence_ref must be FxEvidenceRef")
        if self.near_leg.leg_id == self.far_leg.leg_id:
            raise FxValidationError("FX swap near/far leg ids must differ")
        if not _same_quoted_pair_relationship(self.near_leg.quoted_pair, self.quoted_pair):
            raise FxValidationError("FX swap near-leg pair must match swap pair")
        if not _same_quoted_pair_relationship(self.far_leg.quoted_pair, self.quoted_pair):
            raise FxValidationError("FX swap far-leg pair must match swap pair")

        near_by_currency = {
            flow.amount.currency_identity_id: flow.direction
            for flow in self.near_leg.flows
        }
        far_by_currency = {
            flow.amount.currency_identity_id: flow.direction
            for flow in self.far_leg.flows
        }
        expected = {
            self.quoted_pair.currency1_identity_id,
            self.quoted_pair.currency2_identity_id,
        }
        if set(near_by_currency) != expected or set(far_by_currency) != expected:
            raise FxValidationError("FX swap legs must cover exactly the swap-pair currencies")
        for currency in expected:
            if far_by_currency[currency] is not _reverse_direction(
                near_by_currency[currency]
            ):
                raise FxValidationError(
                    "FX swap far leg must reverse near-leg pay/receive roles"
                )

        if (
            self.far_leg.value_dates.currency1_value_date
            <= self.near_leg.value_dates.currency1_value_date
        ):
            raise FxValidationError(
                "FX swap far currency1 value date must be after near value date"
            )
        if (
            self.far_leg.value_dates.currency2_value_date
            <= self.near_leg.value_dates.currency2_value_date
        ):
            raise FxValidationError(
                "FX swap far currency2 value date must be after near value date"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fx-swap-terms",
            self.terms_id.logical_values(),
            self.instrument_identity_id.logical_values(),
            self.quoted_pair.logical_values(),
            self.near_leg.logical_values(),
            self.far_leg.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class FxOptionPremiumTerms:
    amount: FxCurrencyAmount
    payment_date: date
    evidence_ref: FxEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.amount, FxCurrencyAmount):
            raise FxValidationError("FX option premium amount must be FxCurrencyAmount")
        _validate_date(self.payment_date, field_name="FX option premium payment date")
        if not isinstance(self.evidence_ref, FxEvidenceRef):
            raise FxValidationError("FX option premium evidence_ref must be FxEvidenceRef")

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fx-option-premium-terms",
            self.amount.logical_values(),
            self.payment_date.isoformat(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class FxOptionBinding:
    option_terms: OptionContractTerms
    quoted_pair: FxQuotedCurrencyPair
    put_currency_amount: FxCurrencyAmount
    call_currency_amount: FxCurrencyAmount
    evidence_ref: FxEvidenceRef
    premium: FxOptionPremiumTerms | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.option_terms, OptionContractTerms):
            raise FxValidationError("FX option option_terms must be OptionContractTerms")
        if not isinstance(self.quoted_pair, FxQuotedCurrencyPair):
            raise FxValidationError("FX option quoted_pair must be FxQuotedCurrencyPair")
        if self.option_terms.underlying_identity_id != self.quoted_pair.pair_identity_id:
            raise FxValidationError(
                "FX option underlying identity must equal quoted-pair identity"
            )
        _validate_option_strike_binding(self.quoted_pair, self.option_terms)
        _validate_currency_amount_pair(
            self.quoted_pair,
            self.put_currency_amount,
            self.call_currency_amount,
        )
        if not isinstance(self.evidence_ref, FxEvidenceRef):
            raise FxValidationError("FX option evidence_ref must be FxEvidenceRef")
        if self.premium is not None and not isinstance(
            self.premium,
            FxOptionPremiumTerms,
        ):
            raise FxValidationError(
                "FX option premium must be FxOptionPremiumTerms or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fx-option-binding",
            self.option_terms.logical_values(),
            self.quoted_pair.logical_values(),
            self.put_currency_amount.logical_values(),
            self.call_currency_amount.logical_values(),
            self.premium.logical_values() if self.premium is not None else None,
            self.evidence_ref.logical_values(),
        )
