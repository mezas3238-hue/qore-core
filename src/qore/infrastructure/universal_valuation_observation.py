from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from uuid import UUID

from qore.infrastructure.crypto_perpetual_funding_semantics import (
    CryptoPerpetualPriceRole,
    CryptoPerpetualPricingTerms,
)
from qore.infrastructure.equity_fund_corporate_action_semantics import FundNavBasis
from qore.infrastructure.fixed_income_economics import (
    FinancialTenor,
    FixedIncomeCashFlow,
    FixedIncomePrice,
    FixedIncomeSpread,
    FixedIncomeYield,
    YieldConvention,
)
from qore.infrastructure.market_observation import (
    MarketOhlcField,
    MarketOhlcFieldValidity,
    MarketPrice,
    MarketPriceSide,
    QualifiedOhlcBarObservation,
    QualifiedQuoteTickObservation,
)
from qore.infrastructure.ports import ExternalSourceDescriptor
from qore.infrastructure.rate_term_structure import (
    DiscountFactor,
    ForwardRate,
    ForwardRatePeriod,
    ParRate,
    RateCurveConvention,
    ZeroRate,
)
from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentityId,
    ExternalIdentifierKind,
    ExternalIdentityMappingRevision,
    ListingIdentity,
    ListingIdentityId,
)
from qore.kernel.errors import InfrastructureError


_CODE_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_FAMILY_RE = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z][a-z0-9]*)*$")
_SCHEMA_RE = re.compile(r"^v\d+(?:\.\d+)*$")
_REVISION_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SECRET_MARKERS = ("token=", "secret=", "password=", "bearer ")
_MAX_COMPUTED_INPUTS = 64


class UniversalValuationObservationError(InfrastructureError):
    """Base error for provider-neutral universal valuation observation semantics."""

    __slots__ = ()


class UniversalValuationObservationValidationError(
    UniversalValuationObservationError
):
    """Violation of a universal valuation observation invariant."""

    __slots__ = ()


def _validate_uuid(value: UUID, *, field_name: str) -> None:
    if type(value) is not UUID:
        raise UniversalValuationObservationValidationError(
            f"{field_name} must be UUID"
        )


def _validate_code(value: str, *, field_name: str) -> None:
    if type(value) is not str or len(value) > 96 or _CODE_RE.fullmatch(value) is None:
        raise UniversalValuationObservationValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )
    lowered = value.lower()
    if any(marker in lowered for marker in _SECRET_MARKERS):
        raise UniversalValuationObservationValidationError(
            f"{field_name} must not contain secret-like material"
        )


def _validate_family(value: str, *, field_name: str) -> None:
    if type(value) is not str or _FAMILY_RE.fullmatch(value) is None:
        raise UniversalValuationObservationValidationError(
            f"{field_name} must use canonical dotted family syntax"
        )


def _validate_schema(value: str, *, field_name: str) -> None:
    if type(value) is not str or _SCHEMA_RE.fullmatch(value) is None:
        raise UniversalValuationObservationValidationError(
            f"{field_name} must match v<integer>[.<integer>...]"
        )


def _validate_revision(value: str, *, field_name: str) -> None:
    if type(value) is not str or _REVISION_RE.fullmatch(value) is None:
        raise UniversalValuationObservationValidationError(
            f"{field_name} must use canonical revision syntax"
        )
    lowered = value.lower()
    if any(marker in lowered for marker in _SECRET_MARKERS):
        raise UniversalValuationObservationValidationError(
            f"{field_name} must not contain secret-like material"
        )


def _validate_decimal(
    value: Decimal,
    *,
    field_name: str,
    non_negative: bool = False,
    positive: bool = False,
) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise UniversalValuationObservationValidationError(
            f"{field_name} must be a finite Decimal"
        )
    if positive and value <= 0:
        raise UniversalValuationObservationValidationError(
            f"{field_name} must be positive"
        )
    if non_negative and value < 0:
        raise UniversalValuationObservationValidationError(
            f"{field_name} must be non-negative"
        )


def _canonical_decimal(value: Decimal) -> str:
    normalized = Decimal(0) if value == 0 else value.normalize()
    return format(normalized, "f")


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise UniversalValuationObservationValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise UniversalValuationObservationValidationError(
            f"{field_name} must be timezone-aware"
        )


def _canonical_timestamp(value: datetime, *, field_name: str) -> str:
    _validate_timestamp(value, field_name=field_name)
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _validate_date(value: date, *, field_name: str) -> None:
    if type(value) is not date:
        raise UniversalValuationObservationValidationError(
            f"{field_name} must be date"
        )


@dataclass(frozen=True, slots=True)
class ValuationObservationId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="valuation observation id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ValuationEvidenceRef:
    """Reference to retained UMI-10 evidence; never evidence content or truth."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="valuation evidence ref")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ValuationSourceObservationId:
    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="valuation source observation id")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ValuationSourceEvidenceRef:
    """Reference to external source evidence; never the evidence itself."""

    value: UUID

    def __post_init__(self) -> None:
        _validate_uuid(self.value, field_name="valuation source evidence ref")

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ValuationAsOfInstant:
    value: datetime

    def __post_init__(self) -> None:
        _validate_timestamp(self.value, field_name="valuation as-of instant")

    @property
    def canonical(self) -> str:
        return _canonical_timestamp(self.value, field_name="valuation as-of instant")

    def logical_values(self) -> tuple[str, str]:
        return ("instant", self.canonical)


@dataclass(frozen=True, slots=True)
class ValuationAsOfDate:
    value: date

    def __post_init__(self) -> None:
        _validate_date(self.value, field_name="valuation as-of date")

    def logical_values(self) -> tuple[str, str]:
        return ("date", self.value.isoformat())


@dataclass(frozen=True, slots=True)
class ValuationAsOfInterval:
    opened_at: datetime
    closed_at: datetime

    def __post_init__(self) -> None:
        _validate_timestamp(self.opened_at, field_name="valuation interval opened_at")
        _validate_timestamp(self.closed_at, field_name="valuation interval closed_at")
        if self.closed_at <= self.opened_at:
            raise UniversalValuationObservationValidationError(
                "valuation interval closed_at must be after opened_at"
            )

    def logical_values(self) -> tuple[str, str, str]:
        return (
            "interval",
            _canonical_timestamp(
                self.opened_at,
                field_name="valuation interval opened_at",
            ),
            _canonical_timestamp(
                self.closed_at,
                field_name="valuation interval closed_at",
            ),
        )


type ValuationAsOf = ValuationAsOfInstant | ValuationAsOfDate | ValuationAsOfInterval


class D05OhlcPriceField(StrEnum):
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"


@dataclass(frozen=True, slots=True)
class D05MarketPriceMeasure:
    """One exact D05 price selected from retained source evidence."""

    price: MarketPrice
    side: MarketPriceSide
    ohlc_field: D05OhlcPriceField | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.price, MarketPrice):
            raise UniversalValuationObservationValidationError(
                "D05 market price measure price must be MarketPrice"
            )
        if not isinstance(self.side, MarketPriceSide):
            raise UniversalValuationObservationValidationError(
                "D05 market price measure side must be MarketPriceSide"
            )
        if self.ohlc_field is not None and not isinstance(
            self.ohlc_field,
            D05OhlcPriceField,
        ):
            raise UniversalValuationObservationValidationError(
                "D05 market price measure ohlc_field must be D05OhlcPriceField or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "d05-market-price",
            self.price.logical_values(),
            self.side.value,
            self.ohlc_field.value if self.ohlc_field is not None else None,
        )


@dataclass(frozen=True, slots=True)
class FixedIncomePriceMeasure:
    value: FixedIncomePrice

    def __post_init__(self) -> None:
        if not isinstance(self.value, FixedIncomePrice):
            raise UniversalValuationObservationValidationError(
                "fixed-income price measure must contain FixedIncomePrice"
            )

    def logical_values(self) -> tuple[object, ...]:
        return ("fixed-income-price", self.value.logical_values())


@dataclass(frozen=True, slots=True)
class FixedIncomeYieldMeasure:
    value: FixedIncomeYield
    convention: YieldConvention

    def __post_init__(self) -> None:
        if not isinstance(self.value, FixedIncomeYield):
            raise UniversalValuationObservationValidationError(
                "fixed-income yield measure must contain FixedIncomeYield"
            )
        if not isinstance(self.convention, YieldConvention):
            raise UniversalValuationObservationValidationError(
                "fixed-income yield measure requires YieldConvention"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fixed-income-yield",
            self.value.logical_values(),
            self.convention.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class FixedIncomeSpreadMeasure:
    value: FixedIncomeSpread
    reference_identity_id: EconomicIdentityId

    def __post_init__(self) -> None:
        if not isinstance(self.value, FixedIncomeSpread):
            raise UniversalValuationObservationValidationError(
                "fixed-income spread measure must contain FixedIncomeSpread"
            )
        if not isinstance(self.reference_identity_id, EconomicIdentityId):
            raise UniversalValuationObservationValidationError(
                "fixed-income spread reference must be EconomicIdentityId"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fixed-income-spread",
            self.value.logical_values(),
            self.reference_identity_id.logical_values(),
        )


type StandaloneRateValue = ZeroRate | ParRate | ForwardRate
type StandaloneRateCoordinate = FinancialTenor | ForwardRatePeriod


@dataclass(frozen=True, slots=True)
class StandaloneRateMeasure:
    value: StandaloneRateValue
    convention: RateCurveConvention
    coordinate: StandaloneRateCoordinate

    def __post_init__(self) -> None:
        if not isinstance(self.value, (ZeroRate, ParRate, ForwardRate)):
            raise UniversalValuationObservationValidationError(
                "standalone rate value must be ZeroRate, ParRate, or ForwardRate"
            )
        if not isinstance(self.convention, RateCurveConvention):
            raise UniversalValuationObservationValidationError(
                "standalone rate requires RateCurveConvention"
            )
        if not isinstance(self.coordinate, (FinancialTenor, ForwardRatePeriod)):
            raise UniversalValuationObservationValidationError(
                "standalone rate coordinate must be FinancialTenor or ForwardRatePeriod"
            )
        if isinstance(self.value, ForwardRate):
            if not isinstance(self.coordinate, ForwardRatePeriod):
                raise UniversalValuationObservationValidationError(
                    "forward-rate observation requires ForwardRatePeriod"
                )
        elif not isinstance(self.coordinate, FinancialTenor):
            raise UniversalValuationObservationValidationError(
                "zero/par-rate observation requires FinancialTenor"
            )

    def logical_values(self) -> tuple[object, ...]:
        if isinstance(self.value, ZeroRate):
            kind = "zero-rate"
        elif isinstance(self.value, ParRate):
            kind = "par-rate"
        else:
            kind = "forward-rate"
        coordinate_kind = (
            "tenor" if isinstance(self.coordinate, FinancialTenor) else "forward-period"
        )
        return (
            kind,
            self.value.logical_values(),
            self.convention.logical_values(),
            coordinate_kind,
            self.coordinate.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class DiscountFactorMeasure:
    value: DiscountFactor
    coordinate: StandaloneRateCoordinate

    def __post_init__(self) -> None:
        if not isinstance(self.value, DiscountFactor):
            raise UniversalValuationObservationValidationError(
                "discount-factor measure must contain DiscountFactor"
            )
        if not isinstance(self.coordinate, (FinancialTenor, ForwardRatePeriod)):
            raise UniversalValuationObservationValidationError(
                "discount-factor coordinate must be FinancialTenor or ForwardRatePeriod"
            )

    def logical_values(self) -> tuple[object, ...]:
        coordinate_kind = (
            "tenor" if isinstance(self.coordinate, FinancialTenor) else "forward-period"
        )
        return (
            "discount-factor",
            self.value.logical_values(),
            coordinate_kind,
            self.coordinate.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class FundNavValue:
    """Finite NAV magnitude; UMI-06 FundNavBasis carries its structural basis."""

    value: Decimal

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="fund NAV value")

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class FundNavMeasure:
    value: FundNavValue
    basis: FundNavBasis

    def __post_init__(self) -> None:
        if not isinstance(self.value, FundNavValue):
            raise UniversalValuationObservationValidationError(
                "fund NAV measure value must be FundNavValue"
            )
        if not isinstance(self.basis, FundNavBasis):
            raise UniversalValuationObservationValidationError(
                "fund NAV measure basis must be FundNavBasis"
            )

    def logical_values(self) -> tuple[object, ...]:
        return ("fund-nav", self.value.logical_values(), self.basis.logical_values())


@dataclass(frozen=True, slots=True)
class ImpliedVolatility:
    """Implied-volatility magnitude as a decimal fraction; semantic != price."""

    value: Decimal

    def __post_init__(self) -> None:
        _validate_decimal(
            self.value,
            field_name="implied volatility",
            non_negative=True,
        )

    def logical_values(self) -> tuple[str, ...]:
        return (_canonical_decimal(self.value),)


@dataclass(frozen=True, slots=True)
class ImpliedVolatilityMeasure:
    value: ImpliedVolatility
    reference_identity_id: EconomicIdentityId

    def __post_init__(self) -> None:
        if not isinstance(self.value, ImpliedVolatility):
            raise UniversalValuationObservationValidationError(
                "implied-volatility measure value must be ImpliedVolatility"
            )
        if not isinstance(self.reference_identity_id, EconomicIdentityId):
            raise UniversalValuationObservationValidationError(
                "implied-volatility reference must be EconomicIdentityId"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "implied-volatility",
            self.value.logical_values(),
            self.reference_identity_id.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ValuationQuoteBasisCode:
    """D07 quote-basis code; it performs no conversion or pricing."""

    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="valuation quote basis code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class QuotedValuationValue:
    value: Decimal
    quote_identity_id: EconomicIdentityId
    quote_basis: ValuationQuoteBasisCode

    def __post_init__(self) -> None:
        _validate_decimal(self.value, field_name="quoted valuation value")
        if not isinstance(self.quote_identity_id, EconomicIdentityId):
            raise UniversalValuationObservationValidationError(
                "quoted valuation quote identity must be EconomicIdentityId"
            )
        if not isinstance(self.quote_basis, ValuationQuoteBasisCode):
            raise UniversalValuationObservationValidationError(
                "quoted valuation quote_basis must be ValuationQuoteBasisCode"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            _canonical_decimal(self.value),
            self.quote_identity_id.logical_values(),
            self.quote_basis.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ValuationModelOutputCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="model output code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ModelValueMeasure:
    """Model/theoretical output carrier only; no pricing engine is implemented."""

    value: QuotedValuationValue
    output: ValuationModelOutputCode

    def __post_init__(self) -> None:
        if not isinstance(self.value, QuotedValuationValue):
            raise UniversalValuationObservationValidationError(
                "model value measure must contain QuotedValuationValue"
            )
        if not isinstance(self.output, ValuationModelOutputCode):
            raise UniversalValuationObservationValidationError(
                "model value measure output must be ValuationModelOutputCode"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "model-value",
            self.output.logical_values(),
            self.value.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CryptoPerpetualPriceValue:
    value: Decimal
    quote_identity_id: EconomicIdentityId
    quote_basis: ValuationQuoteBasisCode

    def __post_init__(self) -> None:
        _validate_decimal(
            self.value,
            field_name="crypto perpetual price",
            positive=True,
        )
        if not isinstance(self.quote_identity_id, EconomicIdentityId):
            raise UniversalValuationObservationValidationError(
                "crypto perpetual quote identity must be EconomicIdentityId"
            )
        if not isinstance(self.quote_basis, ValuationQuoteBasisCode):
            raise UniversalValuationObservationValidationError(
                "crypto perpetual quote_basis must be ValuationQuoteBasisCode"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            _canonical_decimal(self.value),
            self.quote_identity_id.logical_values(),
            self.quote_basis.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CryptoPerpetualPriceMeasure:
    value: CryptoPerpetualPriceValue
    role: CryptoPerpetualPriceRole
    pricing_terms: CryptoPerpetualPricingTerms

    def __post_init__(self) -> None:
        if not isinstance(self.value, CryptoPerpetualPriceValue):
            raise UniversalValuationObservationValidationError(
                "crypto perpetual price measure must contain CryptoPerpetualPriceValue"
            )
        if not isinstance(self.role, CryptoPerpetualPriceRole):
            raise UniversalValuationObservationValidationError(
                "crypto perpetual price role must be CryptoPerpetualPriceRole"
            )
        if not isinstance(self.pricing_terms, CryptoPerpetualPricingTerms):
            raise UniversalValuationObservationValidationError(
                "crypto perpetual pricing_terms must be CryptoPerpetualPricingTerms"
            )
        if self.role not in self.pricing_terms.roles:
            raise UniversalValuationObservationValidationError(
                "crypto perpetual price role must be certified by pricing_terms"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "crypto-perpetual-price",
            self.value.logical_values(),
            self.role.value,
            self.pricing_terms.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class FixedIncomeCashFlowValueMeasure:
    """Value of one retained contractual cash flow; never cash/settlement mutation."""

    cash_flow: FixedIncomeCashFlow
    value: QuotedValuationValue

    def __post_init__(self) -> None:
        if not isinstance(self.cash_flow, FixedIncomeCashFlow):
            raise UniversalValuationObservationValidationError(
                "cash-flow value measure requires FixedIncomeCashFlow"
            )
        if not isinstance(self.value, QuotedValuationValue):
            raise UniversalValuationObservationValidationError(
                "cash-flow value measure requires QuotedValuationValue"
            )
        if self.value.quote_identity_id != self.cash_flow.currency_identity_id:
            raise UniversalValuationObservationValidationError(
                "cash-flow value quote identity must equal contractual cash-flow currency"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "fixed-income-cash-flow-value",
            self.cash_flow.logical_values(),
            self.value.logical_values(),
        )


type ValuationMeasure = (
    D05MarketPriceMeasure
    | FixedIncomePriceMeasure
    | FixedIncomeYieldMeasure
    | FixedIncomeSpreadMeasure
    | StandaloneRateMeasure
    | DiscountFactorMeasure
    | FundNavMeasure
    | ImpliedVolatilityMeasure
    | ModelValueMeasure
    | CryptoPerpetualPriceMeasure
    | FixedIncomeCashFlowValueMeasure
)


_VALUATION_MEASURE_TYPES = (
    D05MarketPriceMeasure,
    FixedIncomePriceMeasure,
    FixedIncomeYieldMeasure,
    FixedIncomeSpreadMeasure,
    StandaloneRateMeasure,
    DiscountFactorMeasure,
    FundNavMeasure,
    ImpliedVolatilityMeasure,
    ModelValueMeasure,
    CryptoPerpetualPriceMeasure,
    FixedIncomeCashFlowValueMeasure,
)


def _measure_logical_values(value: ValuationMeasure) -> tuple[object, ...]:
    return value.logical_values()


@dataclass(frozen=True, slots=True)
class ValuationIdentityBinding:
    """Exact supplied UMI-02 mapping evidence; never a currentness resolver."""

    mapping: ExternalIdentityMappingRevision
    economic_identity_id: EconomicIdentityId
    listing: ListingIdentity | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.mapping, ExternalIdentityMappingRevision):
            raise UniversalValuationObservationValidationError(
                "valuation identity binding mapping must be ExternalIdentityMappingRevision"
            )
        if not isinstance(self.economic_identity_id, EconomicIdentityId):
            raise UniversalValuationObservationValidationError(
                "valuation identity binding economic_identity_id must be EconomicIdentityId"
            )
        target = self.mapping.target.value
        if isinstance(target, EconomicIdentityId):
            if target != self.economic_identity_id:
                raise UniversalValuationObservationValidationError(
                    "economic mapping target must equal bound economic identity"
                )
            if self.listing is not None:
                raise UniversalValuationObservationValidationError(
                    "economic mapping target must not carry unrelated listing binding"
                )
        elif isinstance(target, ListingIdentityId):
            if not isinstance(self.listing, ListingIdentity):
                raise UniversalValuationObservationValidationError(
                    "listing mapping target requires exact ListingIdentity binding"
                )
            if self.listing.listing_id != target:
                raise UniversalValuationObservationValidationError(
                    "listing binding id must equal mapping target"
                )
            if self.listing.economic_identity_id != self.economic_identity_id:
                raise UniversalValuationObservationValidationError(
                    "listing binding economic identity must equal final economic identity"
                )
        else:  # pragma: no cover - UMI-02 CanonicalIdentityRef invariant
            raise UniversalValuationObservationValidationError(
                "unsupported canonical identity target"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.mapping.logical_values(),
            self.economic_identity_id.logical_values(),
            self.listing.logical_values() if self.listing is not None else None,
        )


def _validate_legacy_market_binding(
    *,
    symbol: str,
    binding: ValuationIdentityBinding,
) -> None:
    external = binding.mapping.external_identity
    if external.kind is not ExternalIdentifierKind.LEGACY_QORE:
        raise UniversalValuationObservationValidationError(
            "D05 identity binding requires LEGACY_QORE external identifier"
        )
    if external.namespace.value != "market-data.instrument":
        raise UniversalValuationObservationValidationError(
            "D05 identity binding requires market-data.instrument namespace"
        )
    if external.value.value != symbol:
        raise UniversalValuationObservationValidationError(
            "D05 identity binding external value must equal exact Instrument.symbol"
        )


@dataclass(frozen=True, slots=True)
class D05QuoteValuationSource:
    observation: QualifiedQuoteTickObservation
    side: MarketPriceSide
    identity_binding: ValuationIdentityBinding

    def __post_init__(self) -> None:
        if not isinstance(self.observation, QualifiedQuoteTickObservation):
            raise UniversalValuationObservationValidationError(
                "D05 quote source requires QualifiedQuoteTickObservation"
            )
        if self.side not in (MarketPriceSide.BID, MarketPriceSide.ASK):
            raise UniversalValuationObservationValidationError(
                "D05 quote source selector must be BID or ASK"
            )
        if not isinstance(self.identity_binding, ValuationIdentityBinding):
            raise UniversalValuationObservationValidationError(
                "D05 quote source requires ValuationIdentityBinding"
            )
        _validate_legacy_market_binding(
            symbol=self.observation.instrument.symbol,
            binding=self.identity_binding,
        )

    @property
    def economic_identity_id(self) -> EconomicIdentityId:
        return self.identity_binding.economic_identity_id

    @property
    def as_of(self) -> ValuationAsOfInstant:
        return ValuationAsOfInstant(self.observation.observed_at)

    @property
    def measure(self) -> D05MarketPriceMeasure:
        price = (
            self.observation.bid
            if self.side is MarketPriceSide.BID
            else self.observation.ask
        )
        return D05MarketPriceMeasure(price=price, side=self.side)

    def logical_values(self) -> tuple[object, ...]:
        return (
            "d05-quote",
            self.observation.logical_values(),
            self.side.value,
            self.identity_binding.logical_values(),
            self.measure.logical_values(),
        )


def _selected_ohlc_field(
    observation: QualifiedOhlcBarObservation,
    field_name: D05OhlcPriceField,
) -> MarketOhlcField:
    if field_name is D05OhlcPriceField.OPEN:
        return observation.open
    if field_name is D05OhlcPriceField.HIGH:
        return observation.high
    if field_name is D05OhlcPriceField.LOW:
        return observation.low
    return observation.close


@dataclass(frozen=True, slots=True)
class D05OhlcValuationSource:
    observation: QualifiedOhlcBarObservation
    field: D05OhlcPriceField
    identity_binding: ValuationIdentityBinding

    def __post_init__(self) -> None:
        if not isinstance(self.observation, QualifiedOhlcBarObservation):
            raise UniversalValuationObservationValidationError(
                "D05 OHLC source requires QualifiedOhlcBarObservation"
            )
        if not isinstance(self.field, D05OhlcPriceField):
            raise UniversalValuationObservationValidationError(
                "D05 OHLC source field must be D05OhlcPriceField"
            )
        if not isinstance(self.identity_binding, ValuationIdentityBinding):
            raise UniversalValuationObservationValidationError(
                "D05 OHLC source requires ValuationIdentityBinding"
            )
        _validate_legacy_market_binding(
            symbol=self.observation.instrument.symbol,
            binding=self.identity_binding,
        )
        selected = _selected_ohlc_field(self.observation, self.field)
        if (
            selected.validity is not MarketOhlcFieldValidity.VALID
            or selected.price is None
        ):
            raise UniversalValuationObservationValidationError(
                "D05 OHLC valuation source requires a VALID selected field with price"
            )

    @property
    def economic_identity_id(self) -> EconomicIdentityId:
        return self.identity_binding.economic_identity_id

    @property
    def as_of(self) -> ValuationAsOfInterval:
        return ValuationAsOfInterval(
            self.observation.opened_at,
            self.observation.closed_at,
        )

    @property
    def measure(self) -> D05MarketPriceMeasure:
        selected = _selected_ohlc_field(self.observation, self.field)
        if selected.price is None:  # pragma: no cover - guarded by constructor
            raise UniversalValuationObservationValidationError(
                "D05 OHLC selected field lost price"
            )
        return D05MarketPriceMeasure(
            price=selected.price,
            side=self.observation.price_side,
            ohlc_field=self.field,
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "d05-ohlc",
            self.observation.logical_values(),
            self.field.value,
            self.identity_binding.logical_values(),
            self.measure.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class PublishedValuationSource:
    """Externally published typed valuation value observed by QORE."""

    source_observation_id: ValuationSourceObservationId
    source: ExternalSourceDescriptor
    identity_binding: ValuationIdentityBinding
    as_of: ValuationAsOf
    measure: ValuationMeasure
    evidence_ref: ValuationSourceEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.source_observation_id, ValuationSourceObservationId):
            raise UniversalValuationObservationValidationError(
                "published valuation source_observation_id has wrong type"
            )
        if not isinstance(self.source, ExternalSourceDescriptor):
            raise UniversalValuationObservationValidationError(
                "published valuation source must be ExternalSourceDescriptor"
            )
        if not isinstance(self.identity_binding, ValuationIdentityBinding):
            raise UniversalValuationObservationValidationError(
                "published valuation source requires ValuationIdentityBinding"
            )
        if not isinstance(
            self.as_of,
            (ValuationAsOfInstant, ValuationAsOfDate, ValuationAsOfInterval),
        ):
            raise UniversalValuationObservationValidationError(
                "published valuation as_of has unsupported type"
            )
        if not isinstance(self.measure, _VALUATION_MEASURE_TYPES):
            raise UniversalValuationObservationValidationError(
                "published valuation measure must use a certified UMI-10 measure type"
            )
        if isinstance(self.measure, D05MarketPriceMeasure):
            raise UniversalValuationObservationValidationError(
                "published valuation source must not masquerade as exact D05 market evidence"
            )
        if not isinstance(self.evidence_ref, ValuationSourceEvidenceRef):
            raise UniversalValuationObservationValidationError(
                "published valuation evidence_ref must be ValuationSourceEvidenceRef"
            )
        external_source = self.identity_binding.mapping.external_identity.source
        if external_source is not None and external_source != self.source:
            raise UniversalValuationObservationValidationError(
                "provider-scoped identity mapping source must equal valuation source"
            )

    @property
    def economic_identity_id(self) -> EconomicIdentityId:
        return self.identity_binding.economic_identity_id

    def logical_values(self) -> tuple[object, ...]:
        return (
            "published",
            self.source_observation_id.logical_values(),
            self.source.logical_values(),
            self.identity_binding.logical_values(),
            self.as_of.logical_values(),
            _measure_logical_values(self.measure),
            self.evidence_ref.logical_values(),
        )


type ObservedValuationSource = (
    D05QuoteValuationSource | D05OhlcValuationSource | PublishedValuationSource
)


_OBSERVED_SOURCE_TYPES = (
    D05QuoteValuationSource,
    D05OhlcValuationSource,
    PublishedValuationSource,
)


def _source_economic_identity_id(
    source: ObservedValuationSource,
) -> EconomicIdentityId:
    return source.economic_identity_id


def _source_as_of(source: ObservedValuationSource) -> ValuationAsOf:
    return source.as_of


def _source_measure(source: ObservedValuationSource) -> ValuationMeasure:
    return source.measure


@dataclass(frozen=True, slots=True)
class ObservedValuationObservation:
    """Immutable observed D07 record; observation does not imply source truth."""

    observation_id: ValuationObservationId
    source: ObservedValuationSource
    recorded_at: datetime
    evidence_ref: ValuationEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.observation_id, ValuationObservationId):
            raise UniversalValuationObservationValidationError(
                "observed valuation observation_id must be ValuationObservationId"
            )
        if not isinstance(self.source, _OBSERVED_SOURCE_TYPES):
            raise UniversalValuationObservationValidationError(
                "observed valuation source must use a certified source type"
            )
        _validate_timestamp(self.recorded_at, field_name="observed valuation recorded_at")
        if not isinstance(self.evidence_ref, ValuationEvidenceRef):
            raise UniversalValuationObservationValidationError(
                "observed valuation evidence_ref must be ValuationEvidenceRef"
            )

    @property
    def economic_identity_id(self) -> EconomicIdentityId:
        return _source_economic_identity_id(self.source)

    @property
    def as_of(self) -> ValuationAsOf:
        return _source_as_of(self.source)

    @property
    def measure(self) -> ValuationMeasure:
        return _source_measure(self.source)

    def logical_values(self) -> tuple[object, ...]:
        return (
            "observed",
            self.observation_id.logical_values(),
            self.source.logical_values(),
            _canonical_timestamp(
                self.recorded_at,
                field_name="observed valuation recorded_at",
            ),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ValuationMethodologyFamily:
    value: str

    def __post_init__(self) -> None:
        _validate_family(self.value, field_name="valuation methodology family")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ValuationMethodologySchemaVersion:
    value: str

    def __post_init__(self) -> None:
        _validate_schema(self.value, field_name="valuation methodology schema version")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ValuationSoftwareRevision:
    value: str

    def __post_init__(self) -> None:
        _validate_revision(self.value, field_name="valuation software revision")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ValuationMethodologyIdentity:
    """Versioned D07 methodology identity; not an algorithm implementation."""

    family: ValuationMethodologyFamily
    schema_version: ValuationMethodologySchemaVersion
    software_revision: ValuationSoftwareRevision

    def __post_init__(self) -> None:
        if not isinstance(self.family, ValuationMethodologyFamily):
            raise UniversalValuationObservationValidationError(
                "valuation methodology family has wrong type"
            )
        if not isinstance(self.schema_version, ValuationMethodologySchemaVersion):
            raise UniversalValuationObservationValidationError(
                "valuation methodology schema_version has wrong type"
            )
        if not isinstance(self.software_revision, ValuationSoftwareRevision):
            raise UniversalValuationObservationValidationError(
                "valuation methodology software_revision has wrong type"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.family.logical_values(),
            self.schema_version.logical_values(),
            self.software_revision.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ValuationInputRoleCode:
    value: str

    def __post_init__(self) -> None:
        _validate_code(self.value, field_name="valuation input role code")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ValuationComputedInput:
    """One exact leaf input. Nested ValuationObservation inputs are not accepted."""

    role: ValuationInputRoleCode
    source: ObservedValuationSource

    def __post_init__(self) -> None:
        if not isinstance(self.role, ValuationInputRoleCode):
            raise UniversalValuationObservationValidationError(
                "valuation computed input role has wrong type"
            )
        if not isinstance(self.source, _OBSERVED_SOURCE_TYPES):
            raise UniversalValuationObservationValidationError(
                "valuation computed input source must be an observed leaf source"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (self.role.logical_values(), self.source.logical_values())


@dataclass(frozen=True, slots=True)
class ValuationInputFingerprint:
    value: str

    def __post_init__(self) -> None:
        if type(self.value) is not str or _SHA256_RE.fullmatch(self.value) is None:
            raise UniversalValuationObservationValidationError(
                "valuation input fingerprint must be lowercase SHA-256 hex"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def _computed_inputs_material(
    inputs: tuple[ValuationComputedInput, ...],
) -> str:
    logical = tuple(item.logical_values() for item in inputs)
    return json.dumps(logical, separators=(",", ":"), ensure_ascii=True)


def _derive_input_fingerprint(
    inputs: tuple[ValuationComputedInput, ...],
) -> ValuationInputFingerprint:
    material = _computed_inputs_material(inputs).encode("utf-8")
    return ValuationInputFingerprint(sha256(material).hexdigest())


@dataclass(frozen=True, slots=True)
class ComputedValuationProvenance:
    """Retained input lineage carrier; it does not execute the methodology."""

    methodology: ValuationMethodologyIdentity
    inputs: tuple[ValuationComputedInput, ...]
    evidence_ref: ValuationEvidenceRef
    input_fingerprint: ValuationInputFingerprint = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.methodology, ValuationMethodologyIdentity):
            raise UniversalValuationObservationValidationError(
                "computed valuation methodology has wrong type"
            )
        if type(self.inputs) is not tuple or not self.inputs:
            raise UniversalValuationObservationValidationError(
                "computed valuation inputs must be a non-empty tuple"
            )
        if len(self.inputs) > _MAX_COMPUTED_INPUTS:
            raise UniversalValuationObservationValidationError(
                "computed valuation inputs exceed bounded maximum"
            )
        for item in self.inputs:
            if not isinstance(item, ValuationComputedInput):
                raise UniversalValuationObservationValidationError(
                    "computed valuation inputs must contain ValuationComputedInput"
                )
        roles = tuple(item.role.value for item in self.inputs)
        if len(set(roles)) != len(roles):
            raise UniversalValuationObservationValidationError(
                "computed valuation input roles must be unique"
            )
        if not isinstance(self.evidence_ref, ValuationEvidenceRef):
            raise UniversalValuationObservationValidationError(
                "computed valuation evidence_ref must be ValuationEvidenceRef"
            )
        ordered = tuple(
            sorted(
                self.inputs,
                key=lambda item: (
                    item.role.value,
                    json.dumps(
                        item.source.logical_values(),
                        separators=(",", ":"),
                        ensure_ascii=True,
                    ),
                ),
            )
        )
        object.__setattr__(self, "inputs", ordered)
        object.__setattr__(
            self,
            "input_fingerprint",
            _derive_input_fingerprint(ordered),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.methodology.logical_values(),
            tuple(item.logical_values() for item in self.inputs),
            self.input_fingerprint.logical_values(),
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class ComputedValuationObservation:
    """Claimed QORE-computed output carrier; producer/method execution is #350."""

    observation_id: ValuationObservationId
    economic_identity_id: EconomicIdentityId
    as_of: ValuationAsOf
    measure: ValuationMeasure
    provenance: ComputedValuationProvenance
    recorded_at: datetime
    evidence_ref: ValuationEvidenceRef

    def __post_init__(self) -> None:
        if not isinstance(self.observation_id, ValuationObservationId):
            raise UniversalValuationObservationValidationError(
                "computed valuation observation_id must be ValuationObservationId"
            )
        if not isinstance(self.economic_identity_id, EconomicIdentityId):
            raise UniversalValuationObservationValidationError(
                "computed valuation economic_identity_id must be EconomicIdentityId"
            )
        if not isinstance(
            self.as_of,
            (ValuationAsOfInstant, ValuationAsOfDate, ValuationAsOfInterval),
        ):
            raise UniversalValuationObservationValidationError(
                "computed valuation as_of has unsupported type"
            )
        if not isinstance(self.measure, _VALUATION_MEASURE_TYPES):
            raise UniversalValuationObservationValidationError(
                "computed valuation measure must use a certified UMI-10 measure type"
            )
        if isinstance(self.measure, D05MarketPriceMeasure):
            raise UniversalValuationObservationValidationError(
                "computed valuation must not masquerade as exact D05 observed price measure"
            )
        if not isinstance(self.provenance, ComputedValuationProvenance):
            raise UniversalValuationObservationValidationError(
                "computed valuation provenance has wrong type"
            )
        _validate_timestamp(self.recorded_at, field_name="computed valuation recorded_at")
        if not isinstance(self.evidence_ref, ValuationEvidenceRef):
            raise UniversalValuationObservationValidationError(
                "computed valuation evidence_ref must be ValuationEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            "computed",
            self.observation_id.logical_values(),
            self.economic_identity_id.logical_values(),
            self.as_of.logical_values(),
            _measure_logical_values(self.measure),
            self.provenance.logical_values(),
            _canonical_timestamp(
                self.recorded_at,
                field_name="computed valuation recorded_at",
            ),
            self.evidence_ref.logical_values(),
        )


type ValuationObservation = ObservedValuationObservation | ComputedValuationObservation
