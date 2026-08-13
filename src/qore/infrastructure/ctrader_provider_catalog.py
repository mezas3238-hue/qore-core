from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from qore.infrastructure.ctrader_native_market_data import (
    CTraderNativeTrendbarPeriod,
    canonical_ctrader_periods,
    market_timeframe_for_ctrader_period,
)
from qore.infrastructure.market_data import Instrument
from qore.infrastructure.ports import (
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
)
from qore.infrastructure.provider_instrument_catalog import (
    ProviderCatalogScope,
    ProviderInstrumentCatalog,
    ProviderInstrumentCatalogEntry,
    ProviderInstrumentCatalogValidationError,
    ProviderInstrumentEvidenceReference,
    ProviderInstrumentTradingStatus,
    ProviderMarginTerms,
    ProviderMarginTier,
    ProviderTradingSession,
    ProviderVolumeTerms,
)
from qore.kernel.result import Failure, Result, Success


class CTraderProviderCatalogError(ExternalPortError):
    """Base error for cTrader account-scoped instrument discovery."""

    __slots__ = ()


class CTraderProviderCatalogValidationError(CTraderProviderCatalogError):
    """cTrader reference data violates a retained catalog invariant."""

    __slots__ = ()


def _positive_int(value: int, *, field_name: str) -> None:
    if type(value) is not int or value <= 0:
        raise CTraderProviderCatalogValidationError(
            f"{field_name} must be a positive int"
        )


def _optional_positive_int(
    value: int | None,
    *,
    field_name: str,
) -> None:
    if value is not None:
        _positive_int(value, field_name=field_name)


def _trimmed(value: str, *, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
    ):
        raise CTraderProviderCatalogValidationError(
            f"{field_name} must be a non-empty trimmed string"
        )


def _timestamp(value: datetime, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise CTraderProviderCatalogValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise CTraderProviderCatalogValidationError(
            f"{field_name} must be timezone-aware"
        )
    return value.astimezone(UTC)


class CTraderTradingMode(StrEnum):
    """ProtoOATradingMode retained without inventing tradability semantics."""

    ENABLED = "enabled"
    DISABLED_WITHOUT_PENDINGS_EXECUTION = "disabled_without_pendings_execution"
    DISABLED_WITH_PENDINGS_EXECUTION = "disabled_with_pendings_execution"
    CLOSE_ONLY_MODE = "close_only_mode"


class CTraderTotalMarginCalculationType(StrEnum):
    """ProtoOATotalMarginCalculationType retained at account scope."""

    MAX = "max"
    SUM = "sum"
    NET = "net"


@dataclass(frozen=True, slots=True)
class CTraderLightSymbol:
    """Account-scoped symbol identity from the official cTrader symbols list."""

    symbol_id: int
    symbol_name: str
    enabled: bool
    base_asset_id: int | None = None
    quote_asset_id: int | None = None
    category_id: int | None = None

    def __post_init__(self) -> None:
        _positive_int(self.symbol_id, field_name="cTrader symbol_id")
        _trimmed(self.symbol_name, field_name="cTrader symbol_name")
        if type(self.enabled) is not bool:
            raise CTraderProviderCatalogValidationError(
                "cTrader symbol enabled must be strict bool"
            )
        _optional_positive_int(
            self.base_asset_id,
            field_name="cTrader base_asset_id",
        )
        _optional_positive_int(
            self.quote_asset_id,
            field_name="cTrader quote_asset_id",
        )
        _optional_positive_int(
            self.category_id,
            field_name="cTrader category_id",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.symbol_id,
            self.symbol_name,
            self.enabled,
            self.base_asset_id,
            self.quote_asset_id,
            self.category_id,
        )


@dataclass(frozen=True, slots=True, order=True)
class CTraderTradingInterval:
    """ProtoOAInterval weekly half-open schedule coordinates."""

    start_second: int
    end_second: int

    def __post_init__(self) -> None:
        if (
            type(self.start_second) is not int
            or self.start_second < 0
            or self.start_second >= 604_800
        ):
            raise CTraderProviderCatalogValidationError(
                "cTrader interval start_second must be in [0, 604800)"
            )
        if (
            type(self.end_second) is not int
            or self.end_second <= 0
            or self.end_second > 604_800
        ):
            raise CTraderProviderCatalogValidationError(
                "cTrader interval end_second must be in (0, 604800]"
            )
        if self.end_second <= self.start_second:
            raise CTraderProviderCatalogValidationError(
                "cTrader interval must be positive and half-open"
            )

    def logical_values(self) -> tuple[int, int]:
        return (self.start_second, self.end_second)


@dataclass(frozen=True, slots=True)
class CTraderSymbolReferenceData:
    """Full symbol/reference-data evidence joined by provider symbol ID."""

    symbol_id: int
    digits: int
    pip_position: int
    trading_mode: CTraderTradingMode
    min_volume: int | None
    max_volume: int | None
    step_volume: int | None
    schedule: tuple[CTraderTradingInterval, ...]
    schedule_timezone: str | None
    leverage_id: int | None
    measurement_units: str | None
    base_asset_id: int | None
    quote_asset_id: int | None
    category_id: int | None
    category_name: str | None
    asset_class_id: int | None
    asset_class_name: str | None
    evidence_ref: ProviderInstrumentEvidenceReference

    def __post_init__(self) -> None:
        _positive_int(
            self.symbol_id,
            field_name="cTrader reference symbol_id",
        )
        if type(self.digits) is not int or self.digits < 0:
            raise CTraderProviderCatalogValidationError(
                "cTrader digits must be a non-negative int"
            )
        if type(self.pip_position) is not int or self.pip_position < 0:
            raise CTraderProviderCatalogValidationError(
                "cTrader pip_position must be a non-negative int"
            )
        if not isinstance(self.trading_mode, CTraderTradingMode):
            raise CTraderProviderCatalogValidationError(
                "cTrader trading_mode must be CTraderTradingMode"
            )
        for field_name, value in (
            ("min_volume", self.min_volume),
            ("max_volume", self.max_volume),
            ("step_volume", self.step_volume),
            ("leverage_id", self.leverage_id),
            ("base_asset_id", self.base_asset_id),
            ("quote_asset_id", self.quote_asset_id),
            ("category_id", self.category_id),
            ("asset_class_id", self.asset_class_id),
        ):
            _optional_positive_int(
                value,
                field_name=f"cTrader {field_name}",
            )
        if (
            self.min_volume is not None
            and self.max_volume is not None
            and self.min_volume > self.max_volume
        ):
            raise CTraderProviderCatalogValidationError(
                "cTrader min_volume must not exceed max_volume"
            )
        if not isinstance(self.schedule, tuple) or any(
            not isinstance(item, CTraderTradingInterval)
            for item in self.schedule
        ):
            raise CTraderProviderCatalogValidationError(
                "cTrader schedule must be immutable CTraderTradingInterval tuple"
            )
        canonical_schedule = tuple(sorted(set(self.schedule)))
        if canonical_schedule != self.schedule:
            object.__setattr__(self, "schedule", canonical_schedule)
        if self.schedule and self.schedule_timezone is None:
            raise CTraderProviderCatalogValidationError(
                "cTrader schedule requires schedule_timezone"
            )
        if self.schedule_timezone is not None:
            _trimmed(
                self.schedule_timezone,
                field_name="cTrader schedule_timezone",
            )
        if self.measurement_units is not None:
            _trimmed(
                self.measurement_units,
                field_name="cTrader measurement_units",
            )
        for field_name, text_value in (
            ("category_name", self.category_name),
            ("asset_class_name", self.asset_class_name),
        ):
            if text_value is not None:
                _trimmed(text_value, field_name=f"cTrader {field_name}")
        if (self.category_name is None) != (self.category_id is None):
            raise CTraderProviderCatalogValidationError(
                "cTrader category id/name evidence must be present together"
            )
        if (self.asset_class_name is None) != (self.asset_class_id is None):
            raise CTraderProviderCatalogValidationError(
                "cTrader asset-class id/name evidence must be present together"
            )
        if self.category_id is not None and self.asset_class_id is None:
            raise CTraderProviderCatalogValidationError(
                "cTrader category evidence requires linked asset class"
            )
        if not isinstance(
            self.evidence_ref,
            ProviderInstrumentEvidenceReference,
        ):
            raise CTraderProviderCatalogValidationError(
                "cTrader reference evidence_ref is invalid"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.symbol_id,
            self.digits,
            self.pip_position,
            self.trading_mode.value,
            self.min_volume,
            self.max_volume,
            self.step_volume,
            tuple(item.logical_values() for item in self.schedule),
            self.schedule_timezone,
            self.leverage_id,
            self.measurement_units,
            self.base_asset_id,
            self.quote_asset_id,
            self.category_id,
            self.category_name,
            self.asset_class_id,
            self.asset_class_name,
            self.evidence_ref.logical_values(),
        )


@dataclass(frozen=True, slots=True)
class CTraderSymbolsListResult:
    account_id: int
    symbols: tuple[CTraderLightSymbol, ...]
    observed_at: datetime

    def __post_init__(self) -> None:
        _positive_int(self.account_id, field_name="cTrader account_id")
        if not isinstance(self.symbols, tuple) or any(
            not isinstance(item, CTraderLightSymbol)
            for item in self.symbols
        ):
            raise CTraderProviderCatalogValidationError(
                "cTrader symbols list must be immutable CTraderLightSymbol tuple"
            )
        ids = tuple(item.symbol_id for item in self.symbols)
        names = tuple(item.symbol_name for item in self.symbols)
        if len(set(ids)) != len(ids):
            raise CTraderProviderCatalogValidationError(
                "cTrader symbols list ids must be unique"
            )
        if len(set(names)) != len(names):
            raise CTraderProviderCatalogValidationError(
                "cTrader symbols list names must be unique"
            )
        canonical = tuple(
            sorted(
                self.symbols,
                key=lambda item: (item.symbol_id, item.symbol_name),
            )
        )
        if canonical != self.symbols:
            object.__setattr__(self, "symbols", canonical)
        _timestamp(
            self.observed_at,
            field_name="cTrader symbols observed_at",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account_id,
            tuple(item.logical_values() for item in self.symbols),
            self.observed_at.astimezone(UTC).isoformat(timespec="microseconds"),
        )


@dataclass(frozen=True, slots=True)
class CTraderSymbolReferenceDataResult:
    account_id: int
    symbols: tuple[CTraderSymbolReferenceData, ...]
    observed_at: datetime

    def __post_init__(self) -> None:
        _positive_int(self.account_id, field_name="cTrader account_id")
        if not isinstance(self.symbols, tuple) or any(
            not isinstance(item, CTraderSymbolReferenceData)
            for item in self.symbols
        ):
            raise CTraderProviderCatalogValidationError(
                "cTrader reference data must be immutable CTraderSymbolReferenceData tuple"
            )
        ids = tuple(item.symbol_id for item in self.symbols)
        if len(set(ids)) != len(ids):
            raise CTraderProviderCatalogValidationError(
                "cTrader reference symbol ids must be unique"
            )
        canonical = tuple(
            sorted(self.symbols, key=lambda item: item.symbol_id)
        )
        if canonical != self.symbols:
            object.__setattr__(self, "symbols", canonical)
        _timestamp(
            self.observed_at,
            field_name="cTrader reference observed_at",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account_id,
            tuple(item.logical_values() for item in self.symbols),
            self.observed_at.astimezone(UTC).isoformat(timespec="microseconds"),
        )


@dataclass(frozen=True, slots=True)
class CTraderAccountMarginProfile:
    """Account-level margin semantics from ProtoOATrader."""

    account_id: int
    leverage_in_cents: int | None
    total_margin_calculation_type: CTraderTotalMarginCalculationType | None
    max_leverage: int | None
    observed_at: datetime

    def __post_init__(self) -> None:
        _positive_int(self.account_id, field_name="cTrader account_id")
        _optional_positive_int(
            self.leverage_in_cents,
            field_name="cTrader leverage_in_cents",
        )
        if (
            self.total_margin_calculation_type is not None
            and not isinstance(
                self.total_margin_calculation_type,
                CTraderTotalMarginCalculationType,
            )
        ):
            raise CTraderProviderCatalogValidationError(
                "cTrader total margin calculation type is invalid"
            )
        _optional_positive_int(
            self.max_leverage,
            field_name="cTrader max_leverage",
        )
        _timestamp(
            self.observed_at,
            field_name="cTrader account margin observed_at",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.account_id,
            self.leverage_in_cents,
            (
                self.total_margin_calculation_type.value
                if self.total_margin_calculation_type is not None
                else None
            ),
            self.max_leverage,
            self.observed_at.astimezone(UTC).isoformat(timespec="microseconds"),
        )


@dataclass(frozen=True, slots=True)
class CTraderDynamicLeverageTier:
    """ProtoOADynamicLeverageTier native values before exact ratio normalization."""

    volume_usd_cents: int
    leverage_hundredths: int

    def __post_init__(self) -> None:
        _positive_int(
            self.volume_usd_cents,
            field_name="cTrader dynamic leverage volume_usd_cents",
        )
        _positive_int(
            self.leverage_hundredths,
            field_name="cTrader dynamic leverage_hundredths",
        )

    def logical_values(self) -> tuple[int, int]:
        return (self.volume_usd_cents, self.leverage_hundredths)


@dataclass(frozen=True, slots=True)
class CTraderDynamicLeverage:
    """One dynamic-leverage entity retained by explicit leverage ID."""

    leverage_id: int
    tiers: tuple[CTraderDynamicLeverageTier, ...]
    evidence_ref: ProviderInstrumentEvidenceReference
    observed_at: datetime

    def __post_init__(self) -> None:
        _positive_int(
            self.leverage_id,
            field_name="cTrader dynamic leverage_id",
        )
        if not isinstance(self.tiers, tuple) or any(
            not isinstance(item, CTraderDynamicLeverageTier)
            for item in self.tiers
        ):
            raise CTraderProviderCatalogValidationError(
                "cTrader dynamic leverage tiers must be immutable tier tuple"
            )
        if not self.tiers:
            raise CTraderProviderCatalogValidationError(
                "cTrader dynamic leverage must retain at least one tier"
            )
        volumes = tuple(item.volume_usd_cents for item in self.tiers)
        if len(set(volumes)) != len(volumes):
            raise CTraderProviderCatalogValidationError(
                "cTrader dynamic leverage tier volumes must be unique"
            )
        canonical = tuple(
            sorted(
                self.tiers,
                key=lambda item: item.volume_usd_cents,
            )
        )
        if canonical != self.tiers:
            object.__setattr__(self, "tiers", canonical)
        if not isinstance(
            self.evidence_ref,
            ProviderInstrumentEvidenceReference,
        ):
            raise CTraderProviderCatalogValidationError(
                "cTrader dynamic leverage evidence_ref is invalid"
            )
        _timestamp(
            self.observed_at,
            field_name="cTrader dynamic leverage observed_at",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.leverage_id,
            tuple(item.logical_values() for item in self.tiers),
            self.evidence_ref.logical_values(),
            self.observed_at.astimezone(UTC).isoformat(timespec="microseconds"),
        )


class CTraderCanonicalInstrumentMapper(Protocol):
    """Explicit provider-symbol to canonical QORE instrument mapping boundary."""

    def map_symbol(
        self,
        symbol: CTraderLightSymbol,
    ) -> Result[Instrument, ExternalPortError]: ...


@dataclass(frozen=True, slots=True)
class CTraderExactSymbolMapper:
    """Use provider symbol text only if it is already a valid QORE identity."""

    def map_symbol(
        self,
        symbol: CTraderLightSymbol,
    ) -> Result[Instrument, ExternalPortError]:
        if not isinstance(symbol, CTraderLightSymbol):
            return Failure(
                CTraderProviderCatalogValidationError(
                    "cTrader mapping requires CTraderLightSymbol"
                )
            )
        try:
            return Success(Instrument(symbol.symbol_name))
        except ExternalPortError:
            return Failure(
                CTraderProviderCatalogValidationError(
                    "cTrader symbol needs explicit canonical mapping"
                )
            )


class CTraderProviderCatalogClientBoundary(Protocol):
    """Injected Open API reference-data client; auth and transport remain outside."""

    @property
    def descriptor(self) -> ExternalSourceDescriptor: ...

    @property
    def scope(self) -> ProviderCatalogScope: ...

    @property
    def verified_native_periods(
        self,
    ) -> tuple[CTraderNativeTrendbarPeriod, ...]: ...

    def list_symbols(
        self,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[CTraderSymbolsListResult, ExternalPortError]: ...

    def read_symbol_reference_data(
        self,
        symbol_ids: tuple[int, ...],
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[CTraderSymbolReferenceDataResult, ExternalPortError]: ...

    def read_account_margin_profile(
        self,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[CTraderAccountMarginProfile, ExternalPortError]: ...

    def read_dynamic_leverage(
        self,
        leverage_id: int,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[CTraderDynamicLeverage, ExternalPortError]: ...


def _scope_account_id(
    scope: ProviderCatalogScope,
) -> Result[int, ExternalPortError]:
    if scope.provider_name.lower() != "ctrader":
        return Failure(
            CTraderProviderCatalogValidationError(
                "cTrader scope provider_name must identify cTrader"
            )
        )
    try:
        account_id = int(scope.account_reference)
    except ValueError:
        return Failure(
            CTraderProviderCatalogValidationError(
                "cTrader account_reference must be provider account id"
            )
        )
    if account_id <= 0 or str(account_id) != scope.account_reference:
        return Failure(
            CTraderProviderCatalogValidationError(
                "cTrader account_reference must be canonical positive integer text"
            )
        )
    return Success(account_id)


def _trading_status(
    light: CTraderLightSymbol,
    reference: CTraderSymbolReferenceData,
) -> ProviderInstrumentTradingStatus:
    if not light.enabled:
        return ProviderInstrumentTradingStatus.UNAVAILABLE
    if reference.trading_mode is CTraderTradingMode.ENABLED:
        return ProviderInstrumentTradingStatus.TRADABLE
    if reference.trading_mode is CTraderTradingMode.CLOSE_ONLY_MODE:
        return ProviderInstrumentTradingStatus.CLOSE_ONLY
    return ProviderInstrumentTradingStatus.UNAVAILABLE


def _volume_terms(
    reference: CTraderSymbolReferenceData,
) -> ProviderVolumeTerms | None:
    if (
        reference.min_volume is None
        or reference.max_volume is None
        or reference.step_volume is None
    ):
        return None
    try:
        return ProviderVolumeTerms(
            minimum=Decimal(reference.min_volume),
            maximum=Decimal(reference.max_volume),
            step=Decimal(reference.step_volume),
            unit="ctrader_volume_cents",
        )
    except ProviderInstrumentCatalogValidationError as error:
        raise CTraderProviderCatalogValidationError(
            "cTrader volume terms cannot be normalized safely"
        ) from error


def _sessions(
    reference: CTraderSymbolReferenceData,
) -> tuple[ProviderTradingSession, ...]:
    if not reference.schedule:
        return ()
    timezone_name = reference.schedule_timezone
    if timezone_name is None:  # pragma: no cover - guarded by reference invariant
        raise CTraderProviderCatalogValidationError(
            "cTrader schedule lost timezone evidence"
        )
    try:
        return tuple(
            ProviderTradingSession(
                start_second=item.start_second,
                end_second=item.end_second,
                timezone_name=timezone_name,
            )
            for item in reference.schedule
        )
    except ProviderInstrumentCatalogValidationError as error:
        raise CTraderProviderCatalogValidationError(
            "cTrader schedule cannot be normalized safely"
        ) from error


def _margin_terms(
    profile: CTraderAccountMarginProfile,
    reference: CTraderSymbolReferenceData,
    dynamic_by_id: dict[int, CTraderDynamicLeverage],
) -> ProviderMarginTerms | None:
    dynamic: CTraderDynamicLeverage | None = None
    if reference.leverage_id is not None:
        dynamic = dynamic_by_id.get(reference.leverage_id)
        if dynamic is None:
            raise CTraderProviderCatalogValidationError(
                "cTrader leverage_id requires dynamic leverage evidence"
            )
    if (
        profile.leverage_in_cents is None
        and profile.total_margin_calculation_type is None
        and profile.max_leverage is None
        and dynamic is None
    ):
        return None
    account_leverage = (
        Decimal(profile.leverage_in_cents) / Decimal(100)
        if profile.leverage_in_cents is not None
        else None
    )
    tiers: tuple[ProviderMarginTier, ...] = ()
    native_reference: str | None = None
    if dynamic is not None:
        last_index = len(dynamic.tiers) - 1
        tiers = tuple(
            ProviderMarginTier(
                upper_bound=Decimal(item.volume_usd_cents),
                leverage=Decimal(item.leverage_hundredths) / Decimal(100),
                bound_unit="usd_cents",
                per_side=True,
                applies_above=index == last_index,
            )
            for index, item in enumerate(dynamic.tiers)
        )
        native_reference = dynamic.evidence_ref.value
    native_fields: list[tuple[str, str]] = []
    if profile.leverage_in_cents is not None:
        native_fields.append(
            ("leverage_in_cents", str(profile.leverage_in_cents))
        )
    if profile.total_margin_calculation_type is not None:
        native_fields.append(
            (
                "total_margin_calculation_type",
                profile.total_margin_calculation_type.value,
            )
        )
    if profile.max_leverage is not None:
        native_fields.append(("max_leverage", str(profile.max_leverage)))
    if reference.leverage_id is not None:
        native_fields.append(
            ("dynamic_leverage_id", str(reference.leverage_id))
        )
    if dynamic is not None:
        native_fields.append(
            ("dynamic_leverage_encoding", "hundredths")
        )
    try:
        return ProviderMarginTerms(
            model_name="ctrader_open_api",
            account_leverage=account_leverage,
            tiers=tiers,
            native_reference=native_reference,
            native_fields=tuple(native_fields),
        )
    except ProviderInstrumentCatalogValidationError as error:
        raise CTraderProviderCatalogValidationError(
            "cTrader margin terms cannot be retained safely"
        ) from error


def _provider_native_fields(
    light: CTraderLightSymbol,
    reference: CTraderSymbolReferenceData,
) -> tuple[tuple[str, str], ...]:
    fields: list[tuple[str, str]] = [
        ("ctrader_enabled", str(light.enabled)),
        ("ctrader_pip_position", str(reference.pip_position)),
        ("ctrader_symbol_id", str(light.symbol_id)),
        ("ctrader_trading_mode", reference.trading_mode.value),
    ]
    for key, value in (
        ("ctrader_base_asset_id", reference.base_asset_id),
        ("ctrader_quote_asset_id", reference.quote_asset_id),
        ("ctrader_category_id", reference.category_id),
        ("ctrader_asset_class_id", reference.asset_class_id),
        ("ctrader_min_volume", reference.min_volume),
        ("ctrader_max_volume", reference.max_volume),
        ("ctrader_step_volume", reference.step_volume),
        ("ctrader_leverage_id", reference.leverage_id),
    ):
        if value is not None:
            fields.append((key, str(value)))
    if reference.category_name is not None:
        fields.append(("ctrader_category_name", reference.category_name))
    if reference.asset_class_name is not None:
        fields.append(
            ("ctrader_asset_class_name", reference.asset_class_name)
        )
    if reference.measurement_units is not None:
        fields.append(
            ("ctrader_measurement_units", reference.measurement_units)
        )
    if reference.schedule_timezone is not None:
        fields.append(
            ("ctrader_schedule_timezone", reference.schedule_timezone)
        )
    return tuple(sorted(fields))


@dataclass(frozen=True, slots=True)
class CTraderProviderInstrumentCatalogAdapter:
    """Normalize official cTrader account reference-data into provider-neutral QORE."""

    client: CTraderProviderCatalogClientBoundary
    symbol_mapper: CTraderCanonicalInstrumentMapper

    def __post_init__(self) -> None:
        descriptor = getattr(self.client, "descriptor", None)
        if not isinstance(descriptor, ExternalSourceDescriptor):
            raise CTraderProviderCatalogValidationError(
                "cTrader catalog client descriptor must be ExternalSourceDescriptor"
            )
        if not descriptor.port_name.value.startswith("market-data.ctrader"):
            raise CTraderProviderCatalogValidationError(
                "cTrader catalog source must use market-data.ctrader namespace"
            )
        scope = getattr(self.client, "scope", None)
        if not isinstance(scope, ProviderCatalogScope):
            raise CTraderProviderCatalogValidationError(
                "cTrader catalog client scope must be ProviderCatalogScope"
            )
        account_result = _scope_account_id(scope)
        if isinstance(account_result, Failure):
            raise CTraderProviderCatalogValidationError(
                "cTrader catalog scope must identify one provider account"
            ) from account_result.error
        periods = getattr(self.client, "verified_native_periods", None)
        if not isinstance(periods, tuple):
            raise CTraderProviderCatalogValidationError(
                "cTrader verified native periods must be immutable tuple"
            )
        canonical = canonical_ctrader_periods(periods)
        if canonical != periods:
            raise CTraderProviderCatalogValidationError(
                "cTrader verified native periods must use canonical provider order"
            )
        if not callable(getattr(self.symbol_mapper, "map_symbol", None)):
            raise CTraderProviderCatalogValidationError(
                "cTrader symbol_mapper must expose map_symbol"
            )
        for method_name in (
            "list_symbols",
            "read_symbol_reference_data",
            "read_account_margin_profile",
            "read_dynamic_leverage",
        ):
            if not callable(getattr(self.client, method_name, None)):
                raise CTraderProviderCatalogValidationError(
                    f"cTrader catalog client must expose {method_name}"
                )

    @property
    def descriptor(self) -> ExternalSourceDescriptor:
        return self.client.descriptor

    def read_catalog(
        self,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[ProviderInstrumentCatalog, ExternalPortError]:
        scope = self.client.scope
        account_result = _scope_account_id(scope)
        if isinstance(account_result, Failure):
            return Failure(account_result.error)
        account_id = account_result.value

        try:
            symbols_raw = self.client.list_symbols(metadata=metadata)
        except ExternalPortError as error:
            return Failure(error)
        if isinstance(symbols_raw, Failure):
            return Failure(symbols_raw.error)
        if not isinstance(symbols_raw, Success) or not isinstance(
            symbols_raw.value,
            CTraderSymbolsListResult,
        ):
            return Failure(
                CTraderProviderCatalogValidationError(
                    "cTrader list_symbols must return CTraderSymbolsListResult"
                )
            )
        symbols = symbols_raw.value
        if symbols.account_id != account_id:
            return Failure(
                CTraderProviderCatalogValidationError(
                    "cTrader symbols account id must match catalog scope"
                )
            )
        symbol_ids = tuple(item.symbol_id for item in symbols.symbols)

        try:
            references_raw = self.client.read_symbol_reference_data(
                symbol_ids,
                metadata=metadata,
            )
            profile_raw = self.client.read_account_margin_profile(
                metadata=metadata,
            )
        except ExternalPortError as error:
            return Failure(error)
        if isinstance(references_raw, Failure):
            return Failure(references_raw.error)
        if not isinstance(references_raw, Success) or not isinstance(
            references_raw.value,
            CTraderSymbolReferenceDataResult,
        ):
            return Failure(
                CTraderProviderCatalogValidationError(
                    "cTrader reference-data response is invalid"
                )
            )
        if isinstance(profile_raw, Failure):
            return Failure(profile_raw.error)
        if not isinstance(profile_raw, Success) or not isinstance(
            profile_raw.value,
            CTraderAccountMarginProfile,
        ):
            return Failure(
                CTraderProviderCatalogValidationError(
                    "cTrader account-margin response is invalid"
                )
            )
        references = references_raw.value
        profile = profile_raw.value
        if references.account_id != account_id or profile.account_id != account_id:
            return Failure(
                CTraderProviderCatalogValidationError(
                    "cTrader reference/account evidence must match catalog scope"
                )
            )
        expected_ids = set(symbol_ids)
        reference_ids = {item.symbol_id for item in references.symbols}
        if reference_ids != expected_ids:
            return Failure(
                CTraderProviderCatalogValidationError(
                    "cTrader reference data must exactly cover listed symbol ids"
                )
            )
        reference_by_id = {
            item.symbol_id: item for item in references.symbols
        }
        for light in symbols.symbols:
            reference = reference_by_id[light.symbol_id]
            for field_name, list_value, reference_value in (
                ("base_asset_id", light.base_asset_id, reference.base_asset_id),
                ("quote_asset_id", light.quote_asset_id, reference.quote_asset_id),
                ("category_id", light.category_id, reference.category_id),
            ):
                if (
                    list_value is not None
                    and reference_value is not None
                    and list_value != reference_value
                ):
                    return Failure(
                        CTraderProviderCatalogValidationError(
                            f"cTrader {field_name} must agree across reference evidence"
                        )
                    )

        dynamic_by_id: dict[int, CTraderDynamicLeverage] = {}
        dynamic_observed: list[datetime] = []
        leverage_ids = tuple(
            sorted(
                {
                    item.leverage_id
                    for item in references.symbols
                    if item.leverage_id is not None
                }
            )
        )
        for leverage_id in leverage_ids:
            try:
                dynamic_raw = self.client.read_dynamic_leverage(
                    leverage_id,
                    metadata=metadata,
                )
            except ExternalPortError as error:
                return Failure(error)
            if isinstance(dynamic_raw, Failure):
                return Failure(dynamic_raw.error)
            if not isinstance(dynamic_raw, Success) or not isinstance(
                dynamic_raw.value,
                CTraderDynamicLeverage,
            ):
                return Failure(
                    CTraderProviderCatalogValidationError(
                        "cTrader dynamic-leverage response is invalid"
                    )
                )
            dynamic = dynamic_raw.value
            if dynamic.leverage_id != leverage_id:
                return Failure(
                    CTraderProviderCatalogValidationError(
                        "cTrader dynamic leverage id must match requested id"
                    )
                )
            dynamic_by_id[leverage_id] = dynamic
            dynamic_observed.append(dynamic.observed_at)

        native_timeframes = tuple(
            market_timeframe_for_ctrader_period(period)
            for period in self.client.verified_native_periods
        )
        entries: list[ProviderInstrumentCatalogEntry] = []
        for light in symbols.symbols:
            reference = reference_by_id[light.symbol_id]
            mapping = self.symbol_mapper.map_symbol(light)
            if isinstance(mapping, Failure):
                return Failure(mapping.error)
            if not isinstance(mapping, Success) or not isinstance(
                mapping.value,
                Instrument,
            ):
                return Failure(
                    CTraderProviderCatalogValidationError(
                        "cTrader symbol mapper must return Result[Instrument]"
                    )
                )
            try:
                entries.append(
                    ProviderInstrumentCatalogEntry(
                        instrument=mapping.value,
                        provider_symbol=light.symbol_name,
                        provider_symbol_id=str(light.symbol_id),
                        asset_class=reference.asset_class_name,
                        price_precision=reference.digits,
                        minimum_price_increment=None,
                        volume_terms=_volume_terms(reference),
                        trading_status=_trading_status(light, reference),
                        trading_sessions=_sessions(reference),
                        native_timeframes=native_timeframes,
                        margin_terms=_margin_terms(
                            profile,
                            reference,
                            dynamic_by_id,
                        ),
                        effective_at=references.observed_at,
                        evidence_ref=reference.evidence_ref,
                        provider_native_fields=_provider_native_fields(
                            light,
                            reference,
                        ),
                    )
                )
            except (
                ProviderInstrumentCatalogValidationError,
                CTraderProviderCatalogValidationError,
            ):
                return Failure(
                    CTraderProviderCatalogValidationError(
                        "cTrader catalog entry normalization failed closed"
                    )
                )
        observed_candidates = [
            symbols.observed_at,
            references.observed_at,
            profile.observed_at,
            *dynamic_observed,
        ]
        observed_at = max(
            item.astimezone(UTC)
            for item in observed_candidates
        )
        try:
            catalog = ProviderInstrumentCatalog(
                scope=scope,
                source=self.descriptor,
                observed_at=observed_at,
                entries=tuple(entries),
            )
        except ProviderInstrumentCatalogValidationError:
            return Failure(
                CTraderProviderCatalogValidationError(
                    "cTrader catalog failed canonical provider-neutral validation"
                )
            )
        return Success(catalog)
