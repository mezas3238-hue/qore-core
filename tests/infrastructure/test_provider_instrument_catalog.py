from __future__ import annotations

import inspect
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

import qore.infrastructure.provider_instrument_catalog as catalog_module
from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_observation import MarketTimeframe, MarketTimeframeCode
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
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

_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("f1000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("f1000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.provider-catalog-test"),
)
_SCOPE = ProviderCatalogScope(
    provider_name="provider-test",
    server_environment="demo",
    account_reference="account-1",
)
_OBSERVED_AT = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)


def _entry(
    *,
    provider_symbol: str = "EUR/USD",
    provider_symbol_id: str = "1",
    canonical_symbol: str = "EURUSD",
    status: ProviderInstrumentTradingStatus = ProviderInstrumentTradingStatus.TRADABLE,
    evidence: str = "catalog-evidence-1",
    timeframes: tuple[MarketTimeframe, ...] = (),
    margin_terms: ProviderMarginTerms | None = None,
    native_fields: tuple[tuple[str, str], ...] = (),
    effective_at: datetime = _OBSERVED_AT,
) -> ProviderInstrumentCatalogEntry:
    return ProviderInstrumentCatalogEntry(
        instrument=Instrument(canonical_symbol),
        provider_symbol=provider_symbol,
        provider_symbol_id=provider_symbol_id,
        asset_class="FX",
        price_precision=5,
        minimum_price_increment=Decimal("0.00001"),
        volume_terms=ProviderVolumeTerms(
            minimum=Decimal("100"),
            maximum=Decimal("100000"),
            step=Decimal("100"),
            unit="provider_units",
        ),
        trading_status=status,
        trading_sessions=(
            ProviderTradingSession(
                start_second=3600,
                end_second=7200,
                timezone_name="UTC",
            ),
        ),
        native_timeframes=timeframes,
        margin_terms=margin_terms,
        effective_at=effective_at,
        evidence_ref=ProviderInstrumentEvidenceReference(evidence),
        provider_native_fields=native_fields,
    )


def test_catalog_keeps_provider_identity_separate_from_canonical_instrument() -> None:
    entry = _entry(
        provider_symbol="EUR/USD",
        provider_symbol_id="42",
        canonical_symbol="EURUSD",
    )

    assert entry.provider_symbol == "EUR/USD"
    assert entry.provider_symbol_id == "42"
    assert entry.instrument == Instrument("EURUSD")
    assert entry.provider_symbol != entry.instrument.symbol


def test_catalog_canonicalizes_entry_and_timeframe_permutations() -> None:
    first = _entry(
        provider_symbol="EUR/USD",
        provider_symbol_id="1",
        canonical_symbol="EURUSD",
        evidence="catalog-evidence-1",
        timeframes=(
            MarketTimeframe(MarketTimeframeCode.MN1),
            MarketTimeframe(MarketTimeframeCode.M1),
            MarketTimeframe(MarketTimeframeCode.H4),
        ),
    )
    second = _entry(
        provider_symbol="GBP/USD",
        provider_symbol_id="2",
        canonical_symbol="GBPUSD",
        evidence="catalog-evidence-2",
    )

    left = ProviderInstrumentCatalog(
        scope=_SCOPE,
        source=_SOURCE,
        observed_at=_OBSERVED_AT,
        entries=(second, first),
    )
    right = ProviderInstrumentCatalog(
        scope=_SCOPE,
        source=_SOURCE,
        observed_at=_OBSERVED_AT,
        entries=(first, second),
    )

    assert left.logical_values() == right.logical_values()
    assert left.entries == (first, second)
    assert tuple(item.code for item in first.native_timeframes) == (
        MarketTimeframeCode.M1,
        MarketTimeframeCode.H4,
        MarketTimeframeCode.MN1,
    )


def test_duplicate_provider_id_fails_closed() -> None:
    first = _entry()
    second = _entry(
        provider_symbol="GBP/USD",
        provider_symbol_id="1",
        canonical_symbol="GBPUSD",
        evidence="catalog-evidence-2",
    )

    with pytest.raises(ProviderInstrumentCatalogValidationError):
        ProviderInstrumentCatalog(
            scope=_SCOPE,
            source=_SOURCE,
            observed_at=_OBSERVED_AT,
            entries=(first, second),
        )


def test_ambiguous_canonical_mapping_fails_closed() -> None:
    first = _entry()
    second = _entry(
        provider_symbol="EURUSD",
        provider_symbol_id="2",
        canonical_symbol="EURUSD",
        evidence="catalog-evidence-2",
    )

    with pytest.raises(ProviderInstrumentCatalogValidationError):
        ProviderInstrumentCatalog(
            scope=_SCOPE,
            source=_SOURCE,
            observed_at=_OBSERVED_AT,
            entries=(first, second),
        )


def test_nontradable_status_never_permits_new_positions() -> None:
    unavailable = _entry(
        status=ProviderInstrumentTradingStatus.UNAVAILABLE,
    )
    close_only = _entry(
        status=ProviderInstrumentTradingStatus.CLOSE_ONLY,
    )
    unknown = _entry(
        status=ProviderInstrumentTradingStatus.UNKNOWN,
    )

    assert unavailable.is_tradable is False
    assert close_only.is_tradable is False
    assert unknown.is_tradable is False
    assert _entry().is_tradable is True


def test_precision_and_tick_increment_are_retained_without_float_conversion() -> None:
    entry = _entry()

    assert entry.price_precision == 5
    assert entry.minimum_price_increment == Decimal("0.00001")
    assert entry.logical_values()[5] == "0.00001"

    with pytest.raises(ProviderInstrumentCatalogValidationError):
        ProviderInstrumentCatalogEntry(
            instrument=Instrument("EURUSD"),
            provider_symbol="EUR/USD",
            provider_symbol_id="1",
            asset_class=None,
            price_precision=5,
            minimum_price_increment=Decimal("0.000001"),
            volume_terms=None,
            trading_status=ProviderInstrumentTradingStatus.TRADABLE,
            trading_sessions=(),
            native_timeframes=(),
            margin_terms=None,
            effective_at=_OBSERVED_AT,
            evidence_ref=ProviderInstrumentEvidenceReference("evidence-tick"),
        )


def test_margin_rate_model_does_not_require_scalar_leverage() -> None:
    terms = ProviderMarginTerms(
        model_name="provider_margin_rate",
        instrument_margin_rate=Decimal("0.05"),
        initial_margin_rate=Decimal("0.06"),
        maintenance_margin_rate=Decimal("0.04"),
    )

    assert terms.account_leverage is None
    assert terms.instrument_margin_rate == Decimal("0.05")
    assert terms.logical_values()[1] is None


def test_margin_tiers_retain_native_bound_units_and_order() -> None:
    terms = ProviderMarginTerms(
        model_name="dynamic",
        tiers=(
            ProviderMarginTier(
                upper_bound=Decimal("100000000"),
                leverage=Decimal("500"),
                bound_unit="usd_cents",
                per_side=True,
            ),
            ProviderMarginTier(
                upper_bound=Decimal("500000000"),
                leverage=Decimal("200"),
                bound_unit="usd_cents",
                per_side=True,
                applies_above=True,
            ),
        ),
        native_fields=(("margin_model", "tiered"),),
    )

    assert tuple(item.upper_bound for item in terms.tiers) == (
        Decimal("100000000"),
        Decimal("500000000"),
    )
    assert terms.tiers[-1].applies_above is True

    with pytest.raises(ProviderInstrumentCatalogValidationError):
        ProviderMarginTerms(
            model_name="dynamic",
            tiers=tuple(reversed(terms.tiers)),
        )


def test_provider_native_fields_are_canonical_and_secret_like_keys_fail_closed() -> None:
    entry = _entry(
        native_fields=(
            ("z_field", "z"),
            ("a_field", "a"),
        ),
    )

    assert entry.provider_native_fields == (
        ("a_field", "a"),
        ("z_field", "z"),
    )

    with pytest.raises(ProviderInstrumentCatalogValidationError):
        _entry(
            native_fields=(("access_token", "redacted"),),
        )
    with pytest.raises(ProviderInstrumentCatalogValidationError):
        ProviderInstrumentEvidenceReference("provider-token-secret")


def test_catalog_source_scope_and_effective_time_fail_closed() -> None:
    bad_source = ExternalSourceDescriptor(
        adapter_id=AdapterId(UUID("f1000000-0000-0000-0000-000000000011")),
        source_id=SourceId(UUID("f1000000-0000-0000-0000-000000000012")),
        port_name=PortName("execution.provider-catalog-test"),
    )
    with pytest.raises(ProviderInstrumentCatalogValidationError):
        ProviderInstrumentCatalog(
            scope=_SCOPE,
            source=bad_source,
            observed_at=_OBSERVED_AT,
            entries=(),
        )

    future = _entry(
        evidence="future-evidence",
        effective_at=datetime(2026, 8, 13, 11, 0, tzinfo=UTC),
    )
    with pytest.raises(ProviderInstrumentCatalogValidationError):
        ProviderInstrumentCatalog(
            scope=_SCOPE,
            source=_SOURCE,
            observed_at=_OBSERVED_AT,
            entries=(future,),
        )


def test_catalog_contract_has_no_hidden_clock_uuid_network_or_provider_sdk() -> None:
    source = inspect.getsource(catalog_module).lower()
    for forbidden in (
        "datetime.now(",
        "datetime.utcnow(",
        "uuid4(",
        "random.",
        "requests.",
        "httpx",
        "aiohttp",
        "socket",
        "ctrader",
        "oanda",
    ):
        assert forbidden not in source
