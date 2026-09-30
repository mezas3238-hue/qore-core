from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.cibo_ctrader_demo_provider_economics import (
    CTraderExpectedMarginQuote,
    CTraderNativeCommissionTerms,
    CTraderProviderEconomicsProbe,
    CTraderProviderEconomicsSymbolEvidence,
)

_NOW = datetime(2026, 9, 28, 13, 0, tzinfo=UTC)


def _row(
    *,
    commission: CTraderNativeCommissionTerms | None = None,
) -> CTraderProviderEconomicsSymbolEvidence:
    return CTraderProviderEconomicsSymbolEvidence(
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        symbol_id=1,
        observed_at=_NOW,
        digits=5,
        bid=Decimal("1.17000"),
        ask=Decimal("1.17010"),
        min_volume_cents=100000,
        max_volume_cents=100000000,
        step_volume_cents=100000,
        lot_size_cents=10000000,
        commission=commission
        or CTraderNativeCommissionTerms(
            precise_rate_raw=5000000000,
            commission_type=1,
            precise_minimum_raw=100000000,
            minimum_type=1,
            minimum_asset="USD",
        ),
        expected_margin=(
            CTraderExpectedMarginQuote(
                native_volume_cents=100000,
                buy_margin_usd=Decimal("11.70"),
                sell_margin_usd=Decimal("11.70"),
            ),
            CTraderExpectedMarginQuote(
                native_volume_cents=10000000,
                buy_margin_usd=Decimal("1170"),
                sell_margin_usd=Decimal("1170"),
            ),
        ),
        margin_native_ready=True,
        spread_native_ready=True,
    )


def test_provider_terms_ready_requires_margin_spread_and_commission() -> None:
    row = _row()

    assert row.provider_terms_ready is True
    assert row.slippage_empirically_calibrated is False
    assert row.historical_exact_claimed is False
    assert row.source == "CTRADER_OPEN_API_READ_ONLY"
    assert row.provider == "ctrader-demo"
    assert row.effective_period == "POINT_IN_TIME_AT_OBSERVED_AT"
    assert row.provenance == "PROVIDER_NATIVE_SYMBOL_SPOT_AND_EXPECTED_MARGIN"


def test_absent_commission_terms_fail_provider_readiness() -> None:
    row = _row(
        commission=CTraderNativeCommissionTerms(
            precise_rate_raw=None,
            commission_type=None,
            precise_minimum_raw=None,
            minimum_type=None,
            minimum_asset=None,
        )
    )

    assert row.commission_native_ready is False
    assert row.provider_terms_ready is False


def test_probe_never_claims_execution_or_holdout_history() -> None:
    probe = CTraderProviderEconomicsProbe(
        account_ref="redacted-in-production-report",
        observed_at=_NOW,
        symbols=(_row(),),
    )

    assert probe.provider_terms_ready is True
    assert probe.broker_mutation_performed is False
    assert probe.historical_exact_claimed is False
    assert probe.holdout_outcomes_used is False
    assert probe.target_aware is False


def test_provider_symbol_can_carry_gsl_terms_without_promoting_execution() -> None:
    row = CTraderProviderEconomicsSymbolEvidence(
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        symbol_id=1,
        observed_at=_NOW,
        digits=5,
        bid=Decimal("1.17000"),
        ask=Decimal("1.17010"),
        min_volume_cents=100000,
        max_volume_cents=100000000,
        step_volume_cents=100000,
        lot_size_cents=10000000,
        commission=CTraderNativeCommissionTerms(
            precise_rate_raw=5000000000,
            commission_type=1,
            precise_minimum_raw=100000000,
            minimum_type=1,
            minimum_asset="USD",
        ),
        expected_margin=(
            CTraderExpectedMarginQuote(
                native_volume_cents=100000,
                buy_margin_usd=Decimal("11.70"),
                sell_margin_usd=Decimal("11.70"),
            ),
        ),
        margin_native_ready=True,
        spread_native_ready=True,
        guaranteed_stop_loss=True,
        gsl_distance=25,
        gsl_charge_raw=100,
    )

    assert row.guaranteed_stop_loss is True
    assert row.gsl_distance == 25
    assert row.gsl_charge_raw == 100
    assert row.slippage_empirically_calibrated is False
    assert row.historical_exact_claimed is False
