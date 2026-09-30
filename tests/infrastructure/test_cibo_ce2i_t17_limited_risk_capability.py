from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_t17_limited_risk_capability import (
    assess_t17_limited_risk_capability,
)
from qore.infrastructure.cibo_ctrader_demo_account_capability import (
    CTraderDemoAccountCapabilityObservation,
    CTraderDemoAccountType,
    CTraderDemoCatalogSymbol,
    _catalog_sha256,
)
from qore.infrastructure.cibo_ctrader_demo_provider_economics import (
    CTraderExpectedMarginQuote,
    CTraderNativeCommissionTerms,
    CTraderProviderEconomicsProbe,
    CTraderProviderEconomicsSymbolEvidence,
)

T0 = datetime(2026, 9, 30, 23, 0, tzinfo=UTC)


def _account(*, limited: bool | None) -> CTraderDemoAccountCapabilityObservation:
    symbols = (
        CTraderDemoCatalogSymbol(
            symbol_id=1,
            symbol_name="EURUSD",
            enabled=True,
            symbol_category_id=1,
            description="Euro US Dollar",
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
        is_limited_risk=limited,
        limited_risk_margin_calculation_strategy=1 if limited is True else None,
    )


def _symbol(name: str, *, gsl: bool | None) -> CTraderProviderEconomicsSymbolEvidence:
    return CTraderProviderEconomicsSymbolEvidence(
        qore_symbol=name,
        provider_symbol=name,
        symbol_id={"EURUSD": 1, "NAS100": 2}[name],
        observed_at=T0,
        digits=5,
        bid=Decimal("100"),
        ask=Decimal("101"),
        min_volume_cents=1,
        max_volume_cents=100,
        step_volume_cents=1,
        lot_size_cents=100,
        commission=CTraderNativeCommissionTerms(
            precise_rate_raw=1,
            commission_type=1,
            precise_minimum_raw=1,
            minimum_type=1,
            minimum_asset="USD",
        ),
        expected_margin=(
            CTraderExpectedMarginQuote(
                native_volume_cents=1,
                buy_margin_usd=Decimal("1"),
                sell_margin_usd=Decimal("1"),
            ),
        ),
        margin_native_ready=True,
        spread_native_ready=True,
        guaranteed_stop_loss=gsl,
        gsl_distance=10 if gsl is True else None,
        gsl_charge_raw=5 if gsl is True else None,
    )


def _provider(*, gsl_values: tuple[bool | None, bool | None]) -> CTraderProviderEconomicsProbe:
    return CTraderProviderEconomicsProbe(
        account_ref="12345",
        observed_at=T0,
        symbols=(
            _symbol("EURUSD", gsl=gsl_values[0]),
            _symbol("NAS100", gsl=gsl_values[1]),
        ),
    )


def test_limited_risk_plus_full_gsl_coverage_identifies_candidate_only() -> None:
    report = assess_t17_limited_risk_capability(
        account=_account(limited=True),
        provider=_provider(gsl_values=(True, True)),
    )

    assert report.provider_universe_gsl_coverage_complete is True
    assert report.limited_risk_candidate_identified is True
    assert report.gsl_supported_symbols == ("EURUSD", "NAS100")
    assert report.option_structure_proven is False
    assert report.defined_risk_spread_proven is False
    assert report.gsl_execution_economics_proven is False
    assert report.fresh_oos_utility_demonstrated is False
    assert report.t17_policy_ready is False
    assert report.productive_authority is False
    assert "T17_GSL_CANDIDATE_EXECUTION_ECONOMICS_NOT_PROVEN" in report.blockers


def test_unknown_gsl_symbol_keeps_candidate_fail_closed() -> None:
    report = assess_t17_limited_risk_capability(
        account=_account(limited=True),
        provider=_provider(gsl_values=(True, None)),
    )

    assert report.provider_universe_gsl_coverage_complete is False
    assert report.limited_risk_candidate_identified is False
    assert report.gsl_unknown_symbols == ("NAS100",)
    assert "T17_GSL_PROVIDER_UNIVERSE_COVERAGE_INCOMPLETE" in report.blockers


def test_non_limited_risk_account_does_not_create_gsl_candidate() -> None:
    report = assess_t17_limited_risk_capability(
        account=_account(limited=False),
        provider=_provider(gsl_values=(True, True)),
    )

    assert report.limited_risk_candidate_identified is False
    assert "T17_ACCOUNT_NOT_LIMITED_RISK" in report.blockers


def test_account_provider_mismatch_is_rejected() -> None:
    provider = _provider(gsl_values=(True, True))
    other = CTraderProviderEconomicsProbe(
        account_ref="other",
        observed_at=provider.observed_at,
        symbols=provider.symbols,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="account/provider binding mismatch",
    ):
        assess_t17_limited_risk_capability(
            account=_account(limited=True),
            provider=other,
        )
