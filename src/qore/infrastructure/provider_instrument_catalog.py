from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_observation import MarketTimeframe, MarketTimeframeCode
from qore.infrastructure.ports import (
    ExternalPort,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
)
from qore.kernel.result import Result


class ProviderInstrumentCatalogError(ExternalPortError):
    """Base error for provider-qualified instrument catalog boundaries."""

    __slots__ = ()


class ProviderInstrumentCatalogValidationError(ProviderInstrumentCatalogError):
    """Provider catalog data violates a canonical retained invariant."""

    __slots__ = ()


_SECRET_MARKERS = (
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "password",
    "secret",
    "token",
)
_TIMEFRAME_ORDER = tuple(MarketTimeframeCode)


def _require_trimmed(value: str, *, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
    ):
        raise ProviderInstrumentCatalogValidationError(
            f"{field_name} must be a non-empty trimmed string"
        )
    return value


def _require_timestamp(value: datetime, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ProviderInstrumentCatalogValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ProviderInstrumentCatalogValidationError(
            f"{field_name} must be timezone-aware"
        )
    return value.astimezone(UTC)


def _require_positive_decimal(
    value: Decimal,
    *,
    field_name: str,
) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise ProviderInstrumentCatalogValidationError(
            f"{field_name} must be a positive finite Decimal"
        )
    return value


def _canonical_decimal(value: Decimal) -> str:
    normalized = Decimal(0) if value == 0 else value.normalize()
    return format(normalized, "f")


def _contains_secret_marker(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in _SECRET_MARKERS)


def _canonical_timeframes(
    values: tuple[MarketTimeframe, ...],
) -> tuple[MarketTimeframe, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, MarketTimeframe) for item in values
    ):
        raise ProviderInstrumentCatalogValidationError(
            "native_timeframes must be an immutable MarketTimeframe tuple"
        )
    codes = tuple(item.code for item in values)
    if len(set(codes)) != len(codes):
        raise ProviderInstrumentCatalogValidationError(
            "native_timeframes must not contain duplicates"
        )
    return tuple(
        sorted(
            values,
            key=lambda item: _TIMEFRAME_ORDER.index(item.code),
        )
    )


@dataclass(frozen=True, slots=True)
class ProviderInstrumentEvidenceReference:
    """Secret-free reference to retained provider catalog evidence."""

    value: str

    def __post_init__(self) -> None:
        _require_trimmed(self.value, field_name="provider evidence reference")
        if _contains_secret_marker(self.value):
            raise ProviderInstrumentCatalogValidationError(
                "provider evidence reference must not contain secret-like material"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ProviderCatalogScope:
    """Exact provider/server/account scope of one instrument catalog."""

    provider_name: str
    server_environment: str
    account_reference: str

    def __post_init__(self) -> None:
        _require_trimmed(self.provider_name, field_name="provider_name")
        _require_trimmed(
            self.server_environment,
            field_name="server_environment",
        )
        _require_trimmed(
            self.account_reference,
            field_name="account_reference",
        )

    def logical_values(self) -> tuple[str, ...]:
        return (
            self.provider_name,
            self.server_environment,
            self.account_reference,
        )


class ProviderInstrumentTradingStatus(StrEnum):
    """Normalized ability to open exposure, without inventing market-hours policy."""

    TRADABLE = "tradable"
    CLOSE_ONLY = "close_only"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"

    @property
    def permits_new_positions(self) -> bool:
        return self is ProviderInstrumentTradingStatus.TRADABLE


@dataclass(frozen=True, slots=True)
class ProviderVolumeTerms:
    """Provider-native min/max/step volume terms with explicit retained unit."""

    minimum: Decimal
    maximum: Decimal
    step: Decimal
    unit: str

    def __post_init__(self) -> None:
        _require_positive_decimal(self.minimum, field_name="minimum volume")
        _require_positive_decimal(self.maximum, field_name="maximum volume")
        _require_positive_decimal(self.step, field_name="volume step")
        _require_trimmed(self.unit, field_name="volume unit")
        if self.minimum > self.maximum:
            raise ProviderInstrumentCatalogValidationError(
                "minimum volume must not exceed maximum volume"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (
            _canonical_decimal(self.minimum),
            _canonical_decimal(self.maximum),
            _canonical_decimal(self.step),
            self.unit,
        )


@dataclass(frozen=True, slots=True, order=True)
class ProviderTradingSession:
    """One provider-qualified weekly trading interval, retained without policy meaning."""

    start_second: int
    end_second: int
    timezone_name: str

    def __post_init__(self) -> None:
        if (
            type(self.start_second) is not int
            or self.start_second < 0
            or self.start_second >= 604_800
        ):
            raise ProviderInstrumentCatalogValidationError(
                "session start_second must be in [0, 604800)"
            )
        if (
            type(self.end_second) is not int
            or self.end_second <= 0
            or self.end_second > 604_800
        ):
            raise ProviderInstrumentCatalogValidationError(
                "session end_second must be in (0, 604800]"
            )
        if self.end_second <= self.start_second:
            raise ProviderInstrumentCatalogValidationError(
                "session must be a positive half-open weekly interval"
            )
        _require_trimmed(self.timezone_name, field_name="session timezone_name")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.start_second,
            self.end_second,
            self.timezone_name,
        )


@dataclass(frozen=True, slots=True)
class ProviderMarginTier:
    """One retained provider leverage/margin tier in native bound semantics."""

    upper_bound: Decimal
    leverage: Decimal
    bound_unit: str
    per_side: bool
    applies_above: bool = False

    def __post_init__(self) -> None:
        _require_positive_decimal(
            self.upper_bound,
            field_name="margin tier upper_bound",
        )
        _require_positive_decimal(
            self.leverage,
            field_name="margin tier leverage",
        )
        _require_trimmed(self.bound_unit, field_name="margin tier bound_unit")
        if type(self.per_side) is not bool:
            raise ProviderInstrumentCatalogValidationError(
                "margin tier per_side must be strict bool"
            )
        if type(self.applies_above) is not bool:
            raise ProviderInstrumentCatalogValidationError(
                "margin tier applies_above must be strict bool"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            _canonical_decimal(self.upper_bound),
            _canonical_decimal(self.leverage),
            self.bound_unit,
            self.per_side,
            self.applies_above,
        )


@dataclass(frozen=True, slots=True)
class ProviderMarginTerms:
    """Provider-native margin model without collapsing all semantics to leverage."""

    model_name: str
    account_leverage: Decimal | None = None
    instrument_margin_rate: Decimal | None = None
    initial_margin_rate: Decimal | None = None
    maintenance_margin_rate: Decimal | None = None
    buy_margin_multiplier: Decimal | None = None
    sell_margin_multiplier: Decimal | None = None
    tiers: tuple[ProviderMarginTier, ...] = ()
    native_reference: str | None = None
    native_fields: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _require_trimmed(self.model_name, field_name="margin model_name")
        for field_name, value in (
            ("account_leverage", self.account_leverage),
            ("instrument_margin_rate", self.instrument_margin_rate),
            ("initial_margin_rate", self.initial_margin_rate),
            ("maintenance_margin_rate", self.maintenance_margin_rate),
            ("buy_margin_multiplier", self.buy_margin_multiplier),
            ("sell_margin_multiplier", self.sell_margin_multiplier),
        ):
            if value is not None:
                _require_positive_decimal(value, field_name=field_name)
        if self.native_reference is not None:
            _require_trimmed(
                self.native_reference,
                field_name="margin native_reference",
            )
            if _contains_secret_marker(self.native_reference):
                raise ProviderInstrumentCatalogValidationError(
                    "margin native_reference must not contain secret-like material"
                )
        if not isinstance(self.tiers, tuple) or any(
            not isinstance(item, ProviderMarginTier) for item in self.tiers
        ):
            raise ProviderInstrumentCatalogValidationError(
                "margin tiers must be an immutable ProviderMarginTier tuple"
            )
        if self.tiers:
            if tuple(
                sorted(self.tiers, key=lambda item: item.upper_bound)
            ) != self.tiers:
                raise ProviderInstrumentCatalogValidationError(
                    "margin tiers must use canonical ascending upper-bound order"
                )
            bounds = tuple(item.upper_bound for item in self.tiers)
            if len(set(bounds)) != len(bounds):
                raise ProviderInstrumentCatalogValidationError(
                    "margin tier upper bounds must be unique"
                )
        if not isinstance(self.native_fields, tuple) or any(
            not isinstance(item, tuple)
            or len(item) != 2
            or not isinstance(item[0], str)
            or not isinstance(item[1], str)
            for item in self.native_fields
        ):
            raise ProviderInstrumentCatalogValidationError(
                "margin native_fields must be immutable string pairs"
            )
        canonical_fields: list[tuple[str, str]] = []
        seen_keys: set[str] = set()
        for key, value in self.native_fields:
            _require_trimmed(key, field_name="margin native field key")
            _require_trimmed(value, field_name="margin native field value")
            if _contains_secret_marker(key):
                raise ProviderInstrumentCatalogValidationError(
                    "margin native field key must not be secret-like"
                )
            if key in seen_keys:
                raise ProviderInstrumentCatalogValidationError(
                    "margin native field keys must be unique"
                )
            seen_keys.add(key)
            canonical_fields.append((key, value))
        canonical_tuple = tuple(sorted(canonical_fields))
        if canonical_tuple != self.native_fields:
            object.__setattr__(self, "native_fields", canonical_tuple)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.model_name,
            (
                _canonical_decimal(self.account_leverage)
                if self.account_leverage is not None
                else None
            ),
            (
                _canonical_decimal(self.instrument_margin_rate)
                if self.instrument_margin_rate is not None
                else None
            ),
            (
                _canonical_decimal(self.initial_margin_rate)
                if self.initial_margin_rate is not None
                else None
            ),
            (
                _canonical_decimal(self.maintenance_margin_rate)
                if self.maintenance_margin_rate is not None
                else None
            ),
            (
                _canonical_decimal(self.buy_margin_multiplier)
                if self.buy_margin_multiplier is not None
                else None
            ),
            (
                _canonical_decimal(self.sell_margin_multiplier)
                if self.sell_margin_multiplier is not None
                else None
            ),
            tuple(item.logical_values() for item in self.tiers),
            self.native_reference,
            self.native_fields,
        )


@dataclass(frozen=True, slots=True)
class ProviderInstrumentCatalogEntry:
    """One provider-qualified instrument and its effective retained terms."""

    instrument: Instrument
    provider_symbol: str
    provider_symbol_id: str | None
    asset_class: str | None
    price_precision: int | None
    minimum_price_increment: Decimal | None
    volume_terms: ProviderVolumeTerms | None
    trading_status: ProviderInstrumentTradingStatus
    trading_sessions: tuple[ProviderTradingSession, ...]
    native_timeframes: tuple[MarketTimeframe, ...]
    margin_terms: ProviderMarginTerms | None
    effective_at: datetime
    evidence_ref: ProviderInstrumentEvidenceReference
    provider_native_fields: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, Instrument):
            raise ProviderInstrumentCatalogValidationError(
                "catalog instrument must be Instrument"
            )
        _require_trimmed(self.provider_symbol, field_name="provider_symbol")
        if self.provider_symbol_id is not None:
            _require_trimmed(
                self.provider_symbol_id,
                field_name="provider_symbol_id",
            )
        if self.asset_class is not None:
            _require_trimmed(self.asset_class, field_name="asset_class")
        if self.price_precision is not None and (
            type(self.price_precision) is not int or self.price_precision < 0
        ):
            raise ProviderInstrumentCatalogValidationError(
                "price_precision must be a non-negative int or None"
            )
        if self.minimum_price_increment is not None:
            _require_positive_decimal(
                self.minimum_price_increment,
                field_name="minimum_price_increment",
            )
            if self.price_precision is None:
                raise ProviderInstrumentCatalogValidationError(
                    "minimum_price_increment requires explicit price_precision"
                )
            quantum = Decimal(1).scaleb(-self.price_precision)
            units = self.minimum_price_increment / quantum
            if units != units.to_integral_value():
                raise ProviderInstrumentCatalogValidationError(
                    "minimum_price_increment must align to price_precision"
                )
        if self.volume_terms is not None and not isinstance(
            self.volume_terms,
            ProviderVolumeTerms,
        ):
            raise ProviderInstrumentCatalogValidationError(
                "volume_terms must be ProviderVolumeTerms or None"
            )
        if not isinstance(
            self.trading_status,
            ProviderInstrumentTradingStatus,
        ):
            raise ProviderInstrumentCatalogValidationError(
                "trading_status must be ProviderInstrumentTradingStatus"
            )
        if not isinstance(self.trading_sessions, tuple) or any(
            not isinstance(item, ProviderTradingSession)
            for item in self.trading_sessions
        ):
            raise ProviderInstrumentCatalogValidationError(
                "trading_sessions must be immutable ProviderTradingSession tuple"
            )
        canonical_sessions = tuple(sorted(set(self.trading_sessions)))
        if canonical_sessions != self.trading_sessions:
            object.__setattr__(self, "trading_sessions", canonical_sessions)
        canonical_timeframes = _canonical_timeframes(self.native_timeframes)
        if canonical_timeframes != self.native_timeframes:
            object.__setattr__(self, "native_timeframes", canonical_timeframes)
        if self.margin_terms is not None and not isinstance(
            self.margin_terms,
            ProviderMarginTerms,
        ):
            raise ProviderInstrumentCatalogValidationError(
                "margin_terms must be ProviderMarginTerms or None"
            )
        _require_timestamp(self.effective_at, field_name="effective_at")
        if not isinstance(
            self.evidence_ref,
            ProviderInstrumentEvidenceReference,
        ):
            raise ProviderInstrumentCatalogValidationError(
                "evidence_ref must be ProviderInstrumentEvidenceReference"
            )
        if not isinstance(self.provider_native_fields, tuple) or any(
            not isinstance(item, tuple)
            or len(item) != 2
            or not isinstance(item[0], str)
            or not isinstance(item[1], str)
            for item in self.provider_native_fields
        ):
            raise ProviderInstrumentCatalogValidationError(
                "provider_native_fields must be immutable string pairs"
            )
        canonical_native_fields: list[tuple[str, str]] = []
        native_keys: set[str] = set()
        for key, value in self.provider_native_fields:
            _require_trimmed(key, field_name="provider native field key")
            _require_trimmed(value, field_name="provider native field value")
            if _contains_secret_marker(key):
                raise ProviderInstrumentCatalogValidationError(
                    "provider native field key must not be secret-like"
                )
            if key in native_keys:
                raise ProviderInstrumentCatalogValidationError(
                    "provider native field keys must be unique"
                )
            native_keys.add(key)
            canonical_native_fields.append((key, value))
        canonical_native_tuple = tuple(sorted(canonical_native_fields))
        if canonical_native_tuple != self.provider_native_fields:
            object.__setattr__(
                self,
                "provider_native_fields",
                canonical_native_tuple,
            )

    @property
    def is_tradable(self) -> bool:
        return self.trading_status.permits_new_positions

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.instrument.symbol,
            self.provider_symbol,
            self.provider_symbol_id,
            self.asset_class,
            self.price_precision,
            (
                _canonical_decimal(self.minimum_price_increment)
                if self.minimum_price_increment is not None
                else None
            ),
            (
                self.volume_terms.logical_values()
                if self.volume_terms is not None
                else None
            ),
            self.trading_status.value,
            tuple(item.logical_values() for item in self.trading_sessions),
            tuple(item.logical_values() for item in self.native_timeframes),
            (
                self.margin_terms.logical_values()
                if self.margin_terms is not None
                else None
            ),
            self.effective_at.astimezone(UTC).isoformat(timespec="microseconds"),
            self.evidence_ref.logical_values(),
            self.provider_native_fields,
        )


@dataclass(frozen=True, slots=True)
class ProviderInstrumentCatalog:
    """Deterministic account/server-scoped provider instrument catalog."""

    scope: ProviderCatalogScope
    source: ExternalSourceDescriptor
    observed_at: datetime
    entries: tuple[ProviderInstrumentCatalogEntry, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ProviderCatalogScope):
            raise ProviderInstrumentCatalogValidationError(
                "catalog scope must be ProviderCatalogScope"
            )
        if not isinstance(self.source, ExternalSourceDescriptor):
            raise ProviderInstrumentCatalogValidationError(
                "catalog source must be ExternalSourceDescriptor"
            )
        port_name = self.source.port_name.value
        if port_name != "market-data" and not port_name.startswith("market-data."):
            raise ProviderInstrumentCatalogValidationError(
                "catalog source must use market-data namespace"
            )
        observed_utc = _require_timestamp(
            self.observed_at,
            field_name="catalog observed_at",
        )
        if not isinstance(self.entries, tuple) or any(
            not isinstance(item, ProviderInstrumentCatalogEntry)
            for item in self.entries
        ):
            raise ProviderInstrumentCatalogValidationError(
                "catalog entries must be immutable ProviderInstrumentCatalogEntry tuple"
            )
        provider_ids = tuple(
            item.provider_symbol_id
            for item in self.entries
            if item.provider_symbol_id is not None
        )
        if len(set(provider_ids)) != len(provider_ids):
            raise ProviderInstrumentCatalogValidationError(
                "provider symbol ids must be unique inside one catalog scope"
            )
        provider_symbols = tuple(item.provider_symbol for item in self.entries)
        if len(set(provider_symbols)) != len(provider_symbols):
            raise ProviderInstrumentCatalogValidationError(
                "provider symbols must be unique inside one catalog scope"
            )
        canonical_instruments = tuple(item.instrument for item in self.entries)
        if len(set(canonical_instruments)) != len(canonical_instruments):
            raise ProviderInstrumentCatalogValidationError(
                "provider catalog mapping to canonical instruments must be unambiguous"
            )
        if any(
            item.effective_at.astimezone(UTC) > observed_utc
            for item in self.entries
        ):
            raise ProviderInstrumentCatalogValidationError(
                "catalog entry effective_at must not postdate catalog observed_at"
            )
        canonical_entries = tuple(
            sorted(
                self.entries,
                key=lambda item: (
                    item.provider_symbol_id or "",
                    item.provider_symbol,
                    item.instrument.symbol,
                ),
            )
        )
        if canonical_entries != self.entries:
            object.__setattr__(self, "entries", canonical_entries)

    def entry_for_instrument(
        self,
        instrument: Instrument,
    ) -> ProviderInstrumentCatalogEntry:
        if not isinstance(instrument, Instrument):
            raise ProviderInstrumentCatalogValidationError(
                "catalog lookup instrument must be Instrument"
            )
        matches = tuple(
            item for item in self.entries if item.instrument == instrument
        )
        if len(matches) != 1:
            raise ProviderInstrumentCatalogValidationError(
                "catalog must contain exactly one matching canonical instrument"
            )
        return matches[0]

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.scope.logical_values(),
            self.source.logical_values(),
            self.observed_at.astimezone(UTC).isoformat(timespec="microseconds"),
            tuple(item.logical_values() for item in self.entries),
        )


class ProviderInstrumentCatalogPort(ExternalPort, Protocol):
    """External boundary for one account/server-scoped provider catalog."""

    def read_catalog(
        self,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ProviderInstrumentCatalog, ExternalPortError]:
        """Read one retained provider-qualified catalog through an injected boundary."""
        ...
