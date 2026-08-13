from __future__ import annotations

import inspect
from datetime import UTC, datetime
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.infrastructure.ctrader_native_market_data import CTraderNativeTrendbarPeriod
from qore.infrastructure.ctrader_provider_catalog import (
    CTraderAccountMarginProfile,
    CTraderCanonicalInstrumentMapper,
    CTraderDynamicLeverage,
    CTraderDynamicLeverageTier,
    CTraderLightSymbol,
    CTraderProviderCatalogValidationError,
    CTraderProviderInstrumentCatalogAdapter,
    CTraderSymbolReferenceData,
    CTraderSymbolReferenceDataResult,
    CTraderSymbolsListResult,
    CTraderTotalMarginCalculationType,
    CTraderTradingInterval,
    CTraderTradingMode,
)
import qore.infrastructure.ctrader_provider_catalog as catalog_module
from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_observation import MarketTimeframeCode
from qore.infrastructure.ports import (
    AdapterId,
    ExternalPortError,
    ExternalRequestMetadata,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.provider_instrument_catalog import (
    ProviderCatalogScope,
    ProviderInstrumentEvidenceReference,
    ProviderInstrumentTradingStatus,
)
from qore.kernel.result import Failure, Result, Success


_DESCRIPTOR = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("f2000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("f2000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.ctrader.catalog-test"),
)
_SCOPE = ProviderCatalogScope(
    provider_name="cTrader",
    server_environment="demo-eu",
    account_reference="12345",
)
_METADATA = ExternalRequestMetadata(
    correlation_id=CorrelationId(UUID("f2000000-0000-0000-0000-000000000003")),
)
_SYMBOLS_AT = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
_REFERENCES_AT = datetime(2026, 8, 13, 10, 1, tzinfo=UTC)
_PROFILE_AT = datetime(2026, 8, 13, 10, 2, tzinfo=UTC)
_DYNAMIC_AT = datetime(2026, 8, 13, 10, 3, tzinfo=UTC)


class _Mapper(CTraderCanonicalInstrumentMapper):
    def __init__(self, values: dict[int, Instrument]) -> None:
        self._values = values

    def map_symbol(
        self,
        symbol: CTraderLightSymbol,
    ) -> Result[Instrument, ExternalPortError]:
        instrument = self._values.get(symbol.symbol_id)
        if instrument is None:
            return Failure(
                CTraderProviderCatalogValidationError(
                    "test mapper has no explicit canonical mapping"
                )
            )
        return Success(instrument)


class _CatalogClient:
    def __init__(
        self,
        *,
        symbols: CTraderSymbolsListResult,
        references: CTraderSymbolReferenceDataResult,
        profile: CTraderAccountMarginProfile,
        dynamic: dict[int, CTraderDynamicLeverage],
        scope: ProviderCatalogScope = _SCOPE,
        descriptor: ExternalSourceDescriptor = _DESCRIPTOR,
        verified_native_periods: tuple[CTraderNativeTrendbarPeriod, ...] = tuple(
            CTraderNativeTrendbarPeriod
        ),
    ) -> None:
        self._symbols = symbols
        self._references = references
        self._profile = profile
        self._dynamic = dynamic
        self._scope = scope
        self._descriptor = descriptor
        self._verified_native_periods = verified_native_periods
        self.reference_requests: list[tuple[int, ...]] = []
        self.dynamic_requests: list[int] = []

    @property
    def descriptor(self) -> ExternalSourceDescriptor:
        return self._descriptor

    @property
    def scope(self) -> ProviderCatalogScope:
        return self._scope

    @property
    def verified_native_periods(
        self,
    ) -> tuple[CTraderNativeTrendbarPeriod, ...]:
        return self._verified_native_periods

    def list_symbols(
        self,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[CTraderSymbolsListResult, ExternalPortError]:
        assert metadata is _METADATA
        return Success(self._symbols)

    def read_symbol_reference_data(
        self,
        symbol_ids: tuple[int, ...],
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[CTraderSymbolReferenceDataResult, ExternalPortError]:
        assert metadata is _METADATA
        self.reference_requests.append(symbol_ids)
        return Success(self._references)

    def read_account_margin_profile(
        self,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[CTraderAccountMarginProfile, ExternalPortError]:
        assert metadata is _METADATA
        return Success(self._profile)

    def read_dynamic_leverage(
        self,
        leverage_id: int,
        *,
        metadata: ExternalRequestMetadata,
    ) -> Result[CTraderDynamicLeverage, ExternalPortError]:
        assert metadata is _METADATA
        self.dynamic_requests.append(leverage_id)
        value = self._dynamic.get(leverage_id)
        if value is None:
            return Failure(
                CTraderProviderCatalogValidationError(
                    "test dynamic leverage is unavailable"
                )
            )
        return Success(value)


def _light_symbols() -> tuple[CTraderLightSymbol, CTraderLightSymbol]:
    return (
        CTraderLightSymbol(
            symbol_id=1001,
            symbol_name="EUR/USD",
            enabled=True,
            base_asset_id=1,
            quote_asset_id=2,
            category_id=10,
        ),
        CTraderLightSymbol(
            symbol_id=1002,
            symbol_name="GBP/USD",
            enabled=False,
            base_asset_id=3,
            quote_asset_id=2,
            category_id=10,
        ),
    )


def _reference(
    symbol_id: int,
    *,
    leverage_id: int | None = None,
    trading_mode: CTraderTradingMode = CTraderTradingMode.ENABLED,
    evidence: str | None = None,
) -> CTraderSymbolReferenceData:
    base_asset_id = 1 if symbol_id == 1001 else 3
    return CTraderSymbolReferenceData(
        symbol_id=symbol_id,
        digits=5,
        pip_position=4,
        trading_mode=trading_mode,
        min_volume=100,
        max_volume=1_000_000,
        step_volume=100,
        schedule=(
            CTraderTradingInterval(
                start_second=86_400,
                end_second=172_800,
            ),
        ),
        schedule_timezone="UTC",
        leverage_id=leverage_id,
        measurement_units="units",
        base_asset_id=base_asset_id,
        quote_asset_id=2,
        category_id=10,
        category_name="FX Majors",
        asset_class_id=20,
        asset_class_name="FX",
        evidence_ref=ProviderInstrumentEvidenceReference(
            evidence or f"ctrader-symbol-{symbol_id}-evidence"
        ),
    )


def _profile(*, account_id: int = 12345) -> CTraderAccountMarginProfile:
    return CTraderAccountMarginProfile(
        account_id=account_id,
        leverage_in_cents=5_000,
        total_margin_calculation_type=CTraderTotalMarginCalculationType.NET,
        max_leverage=50_000,
        observed_at=_PROFILE_AT,
    )


def _dynamic(
    *,
    leverage_id: int = 77,
) -> CTraderDynamicLeverage:
    return CTraderDynamicLeverage(
        leverage_id=leverage_id,
        tiers=(
            CTraderDynamicLeverageTier(
                volume_usd_cents=500_000_000,
                leverage_hundredths=10_000,
            ),
            CTraderDynamicLeverageTier(
                volume_usd_cents=100_000_000,
                leverage_hundredths=50_000,
            ),
        ),
        evidence_ref=ProviderInstrumentEvidenceReference(
            f"ctrader-dynamic-{leverage_id}-evidence"
        ),
        observed_at=_DYNAMIC_AT,
    )


def _client(
    *,
    symbols_account_id: int = 12345,
    references: tuple[CTraderSymbolReferenceData, ...] | None = None,
    dynamic: dict[int, CTraderDynamicLeverage] | None = None,
) -> _CatalogClient:
    symbols = CTraderSymbolsListResult(
        account_id=symbols_account_id,
        symbols=_light_symbols(),
        observed_at=_SYMBOLS_AT,
    )
    reference_values = references or (
        _reference(1001, leverage_id=77),
        _reference(1002),
    )
    reference_result = CTraderSymbolReferenceDataResult(
        account_id=12345,
        symbols=reference_values,
        observed_at=_REFERENCES_AT,
    )
    return _CatalogClient(
        symbols=symbols,
        references=reference_result,
        profile=_profile(),
        dynamic={77: _dynamic()} if dynamic is None else dynamic,
    )


def _mapper() -> _Mapper:
    return _Mapper(
        {
            1001: Instrument("EURUSD"),
            1002: Instrument("GBPUSD"),
        }
    )


def _read(client: _CatalogClient, mapper: CTraderCanonicalInstrumentMapper | None = None):
    adapter = CTraderProviderInstrumentCatalogAdapter(
        client=client,
        symbol_mapper=_mapper() if mapper is None else mapper,
    )
    return adapter.read_catalog(metadata=_METADATA)


def test_official_symbol_list_drives_exact_reference_and_dynamic_requests() -> None:
    client = _client()

    result = _read(client)

    assert isinstance(result, Success)
    assert client.reference_requests == [(1001, 1002)]
    assert client.dynamic_requests == [77]
    catalog = result.value
    assert catalog.scope == _SCOPE
    assert catalog.source == _DESCRIPTOR
    assert catalog.observed_at == _DYNAMIC_AT
    assert tuple(entry.provider_symbol_id for entry in catalog.entries) == (
        "1001",
        "1002",
    )


def test_provider_symbol_text_is_retained_separately_from_explicit_mapping() -> None:
    result = _read(_client())

    assert isinstance(result, Success)
    eurusd = result.value.entry_for_instrument(Instrument("EURUSD"))
    assert eurusd.provider_symbol == "EUR/USD"
    assert eurusd.provider_symbol_id == "1001"
    assert eurusd.instrument.symbol == "EURUSD"
    assert eurusd.asset_class == "FX"
    assert ("ctrader_category_name", "FX Majors") in eurusd.provider_native_fields


def test_ctrader_digits_do_not_invent_minimum_tick_increment() -> None:
    result = _read(_client())

    assert isinstance(result, Success)
    eurusd = result.value.entry_for_instrument(Instrument("EURUSD"))
    assert eurusd.price_precision == 5
    assert eurusd.minimum_price_increment is None
    assert ("ctrader_pip_position", "4") in eurusd.provider_native_fields


def test_volume_and_trading_status_preserve_provider_evidence() -> None:
    result = _read(_client())

    assert isinstance(result, Success)
    eurusd = result.value.entry_for_instrument(Instrument("EURUSD"))
    gbpusd = result.value.entry_for_instrument(Instrument("GBPUSD"))
    assert eurusd.volume_terms is not None
    assert eurusd.volume_terms.minimum == 100
    assert eurusd.volume_terms.maximum == 1_000_000
    assert eurusd.volume_terms.step == 100
    assert eurusd.volume_terms.unit == "ctrader_volume_cents"
    assert eurusd.trading_status is ProviderInstrumentTradingStatus.TRADABLE
    assert gbpusd.trading_status is ProviderInstrumentTradingStatus.UNAVAILABLE
    assert gbpusd.is_tradable is False


def test_margin_model_retains_account_and_dynamic_native_semantics() -> None:
    result = _read(_client())

    assert isinstance(result, Success)
    eurusd = result.value.entry_for_instrument(Instrument("EURUSD"))
    terms = eurusd.margin_terms
    assert terms is not None
    assert terms.account_leverage == 50
    assert tuple(tier.upper_bound for tier in terms.tiers) == (
        100_000_000,
        500_000_000,
    )
    assert tuple(tier.leverage for tier in terms.tiers) == (500, 100)
    assert all(tier.bound_unit == "usd_cents" for tier in terms.tiers)
    assert all(tier.per_side is True for tier in terms.tiers)
    assert terms.tiers[0].applies_above is False
    assert terms.tiers[-1].applies_above is True
    assert ("leverage_in_cents", "5000") in terms.native_fields
    assert ("dynamic_leverage_encoding", "hundredths") in terms.native_fields
    assert ("dynamic_leverage_id", "77") in terms.native_fields


def test_verified_native_periods_cover_canonical_identity_without_fake_calendar_seconds() -> None:
    result = _read(_client())

    assert isinstance(result, Success)
    eurusd = result.value.entry_for_instrument(Instrument("EURUSD"))
    assert tuple(item.code for item in eurusd.native_timeframes) == tuple(
        MarketTimeframeCode
    )
    by_code = {item.code: item for item in eurusd.native_timeframes}
    assert by_code[MarketTimeframeCode.D1].fixed_seconds is None
    assert by_code[MarketTimeframeCode.W1].fixed_seconds is None
    assert by_code[MarketTimeframeCode.MN1].fixed_seconds is None


def test_ambiguous_explicit_canonical_mapping_fails_closed() -> None:
    mapper = _Mapper(
        {
            1001: Instrument("EURUSD"),
            1002: Instrument("EURUSD"),
        }
    )

    result = _read(_client(), mapper)

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderProviderCatalogValidationError)


def test_account_scope_and_reference_membership_mismatch_fail_closed() -> None:
    account_mismatch = _read(_client(symbols_account_id=999))
    assert isinstance(account_mismatch, Failure)
    assert isinstance(account_mismatch.error, CTraderProviderCatalogValidationError)

    missing_reference = _read(
        _client(references=(_reference(1001, leverage_id=77),))
    )
    assert isinstance(missing_reference, Failure)
    assert isinstance(missing_reference.error, CTraderProviderCatalogValidationError)


def test_dynamic_leverage_response_id_mismatch_fails_closed() -> None:
    result = _read(
        _client(
            dynamic={77: _dynamic(leverage_id=78)},
        )
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderProviderCatalogValidationError)


def test_ctrader_catalog_adapter_has_no_hardcoded_discovery_or_hidden_credentials() -> None:
    source = inspect.getsource(catalog_module).lower()
    for forbidden in (
        "eurusd",
        "gbpusd",
        "datetime.now(",
        "datetime.utcnow(",
        "uuid4(",
        "requests.",
        "httpx",
        "aiohttp",
        "access_token",
        "password",
        "client_secret",
    ):
        assert forbidden not in source
