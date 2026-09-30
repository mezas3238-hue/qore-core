from datetime import UTC, datetime

from qore.infrastructure.cibo_ctrader_demo_account_capability import (
    CTraderDemoAccountCapabilityObservation,
    CTraderDemoAccountType,
    CTraderDemoCatalogSymbol,
    _catalog_sha256,
)
from scripts.cibo_ctrader_demo_account_capability_probe import build_report

T0 = datetime(2026, 9, 30, 20, 0, tzinfo=UTC)


def _observation() -> CTraderDemoAccountCapabilityObservation:
    symbols = (
        CTraderDemoCatalogSymbol(
            symbol_id=1,
            symbol_name="EURUSD",
            enabled=True,
            symbol_category_id=10,
            description="Euro US Dollar",
        ),
        CTraderDemoCatalogSymbol(
            symbol_id=2,
            symbol_name="USTEC",
            enabled=True,
            symbol_category_id=20,
            description="US Tech index",
        ),
    )
    return CTraderDemoAccountCapabilityObservation(
        account_ref="12345",
        observed_at=T0,
        account_type=CTraderDemoAccountType.HEDGED,
        account_type_field_present=True,
        same_symbol_opposite_positions_supported=True,
        symbols=symbols,
        catalog_sha256=_catalog_sha256(symbols),
    )


def test_report_is_sanitized_and_does_not_promote_t16_t17() -> None:
    report = build_report(_observation())

    assert report["provider_key"] == "ctrader-demo"
    assert report["environment"] == "demo"
    assert report["account_type"] == "HEDGED"
    assert report["same_symbol_opposite_positions_supported"] is True
    assert report["symbol_count"] == 2
    assert report["enabled_symbol_count"] == 2
    assert report["broker_mutation_performed"] is False
    assert report["t16_hedge_instrument_certified"] is False
    assert report["t17_option_structure_certified"] is False
    assert report["productive_authority"] is False
    assert report["status"] == "ACCOUNT_MODE_OBSERVED_T16_T17_NOT_CERTIFIED"
    assert report["account_fingerprint_sha256"] != "12345"
    assert "account_ref" not in report


def test_report_preserves_provider_catalog_identity() -> None:
    observation = _observation()
    report = build_report(observation)

    assert report["catalog_sha256"] == observation.catalog_sha256
    symbols = report["symbols"]
    assert isinstance(symbols, list)
    assert [row["symbol_name"] for row in symbols] == ["EURUSD", "USTEC"]
