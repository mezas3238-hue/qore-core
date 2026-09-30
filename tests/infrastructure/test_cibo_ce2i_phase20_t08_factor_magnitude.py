from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_factor_magnitude import (
    T08FactorVolumeBasis,
    T08UsdConversionBasis,
    assess_minimum_seed_factor_magnitude,
)
from qore.infrastructure.cibo_provider_economic_normalization import ProviderEconomicObservation

DECISION_AT = datetime(2026, 9, 28, 18, 0, tzinfo=UTC)


def _opportunity(
    *,
    trader: TraderLineage,
    symbol: str,
    entry: str,
    stop: str,
    target: str,
    stop_loss_per_volume: str,
    side: str = "long",
    minimum_volume: str = "0.01",
    volume_step: str = "0.01",
) -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=trader,
        signal_fingerprint=f"signal:{symbol.lower()}:{side}",
        qore_symbol=symbol,
        provider_symbol=symbol,
        side=side,
        entry_type="market",
        intended_entry=Decimal(entry),
        stop_loss=Decimal(stop),
        take_profit=Decimal(target),
        stop_loss_per_volume=Decimal(stop_loss_per_volume),
        margin_per_volume=Decimal("1000"),
        volume_step=Decimal(volume_step),
        minimum_volume=Decimal(minimum_volume),
        maximum_volume=Decimal("10"),
    )


def _provider(
    *,
    symbol: str,
    bid: str,
    ask: str,
    contract_size: str,
    tick_size: str,
    tick_value: str,
    minimum_volume: str = "0.01",
    volume_step: str = "0.01",
) -> ProviderEconomicObservation:
    return ProviderEconomicObservation(
        provider_key="ctrader-demo",
        qore_symbol=symbol,
        provider_symbol=symbol,
        bid=Decimal(bid),
        ask=Decimal(ask),
        contract_size=Decimal(contract_size),
        tick_size=Decimal(tick_size),
        tick_value=Decimal(tick_value),
        minimum_volume=Decimal(minimum_volume),
        maximum_volume=Decimal("10"),
        volume_step=Decimal(volume_step),
        margin_per_volume=Decimal("1000"),
        commission_per_volume_usd=Decimal("0"),
        slippage_reserve_per_volume_usd=Decimal("0"),
        observed_at=DECISION_AT - timedelta(seconds=1),
    )


def test_quote_usd_pair_uses_provider_tick_economics_not_stop_risk_split() -> None:
    opportunity = _opportunity(
        trader=TraderLineage.R43_GBPUSD,
        symbol="GBPUSD",
        entry="1.25",
        stop="1.24",
        target="1.27",
        stop_loss_per_volume="1200",
    )
    provider = _provider(
        symbol="GBPUSD",
        bid="1.2499",
        ask="1.2501",
        contract_size="100000",
        tick_size="0.0001",
        tick_value="10",
    )

    audit = assess_minimum_seed_factor_magnitude(
        opportunity=opportunity,
        observation=provider,
        decision_at=DECISION_AT,
        provider_evidence_ref="provider:gbpusd",
    )

    exposures = {item.factor_id: item for item in audit.exposures}
    assert audit.volume_basis is T08FactorVolumeBasis.MINIMUM_EXECUTABLE_CANDIDATE
    assert audit.volume == Decimal("0.01")
    assert exposures["GBP"].signed_native_amount == Decimal("1000.00")
    assert exposures["GBP"].usd_per_native_unit == Decimal("1.25")
    assert exposures["GBP"].signed_notional_usd == Decimal("1250.0000")
    assert exposures["USD"].signed_native_amount == Decimal("-1250.0000")
    assert exposures["USD"].usd_per_native_unit == Decimal("1")
    assert exposures["USD"].signed_notional_usd == Decimal("-1250.0000")
    assert all(
        item.conversion_basis
        is T08UsdConversionBasis.PROVIDER_TICK_ECONOMICS
        for item in audit.exposures
    )
    assert audit.native_magnitude_identified is True
    assert audit.usd_magnitude_complete is True
    assert audit.risk_equivalent_identified is False
    assert audit.correlation_state_identified is False
    assert audit.netting_credit_authorized is False


def test_cross_pair_resolves_usd_notional_from_provider_tick_economics() -> None:
    opportunity = _opportunity(
        trader=TraderLineage.R38_GBPJPY,
        symbol="GBPJPY",
        entry="190",
        stop="189",
        target="192",
        stop_loss_per_volume="700",
    )
    provider = _provider(
        symbol="GBPJPY",
        bid="189.99",
        ask="190.01",
        contract_size="100000",
        tick_size="0.01",
        tick_value="6",
    )

    audit = assess_minimum_seed_factor_magnitude(
        opportunity=opportunity,
        observation=provider,
        decision_at=DECISION_AT,
        provider_evidence_ref="provider:gbpjpy",
    )

    exposures = {item.factor_id: item for item in audit.exposures}
    assert exposures["GBP"].signed_native_amount == Decimal("1000.00")
    assert exposures["GBP"].usd_per_native_unit == Decimal("1.140")
    assert exposures["GBP"].signed_notional_usd == Decimal("1140.00000")
    assert exposures["JPY"].signed_native_amount == Decimal("-190000.00")
    assert exposures["JPY"].usd_per_native_unit == Decimal("0.006")
    assert exposures["JPY"].signed_notional_usd == Decimal("-1140.00000")
    assert audit.native_magnitude_identified is True
    assert audit.usd_magnitude_complete is True
    assert not any(
        blocker.startswith("USD_CONVERSION_REQUIRED:")
        for blocker in audit.blockers
    )
    assert audit.risk_equivalent_identified is False
    assert audit.correlation_state_identified is False
    assert audit.netting_credit_authorized is False


def test_short_pair_reverses_native_and_usd_factor_signs() -> None:
    opportunity = _opportunity(
        trader=TraderLineage.R38_GBPJPY,
        symbol="GBPJPY",
        entry="190",
        stop="191",
        target="188",
        stop_loss_per_volume="700",
        side="short",
    )
    provider = _provider(
        symbol="GBPJPY",
        bid="189.99",
        ask="190.01",
        contract_size="100000",
        tick_size="0.01",
        tick_value="6",
    )

    audit = assess_minimum_seed_factor_magnitude(
        opportunity=opportunity,
        observation=provider,
        decision_at=DECISION_AT,
        provider_evidence_ref="provider:gbpjpy",
    )

    exposures = {item.factor_id: item for item in audit.exposures}
    assert exposures["GBP"].signed_native_amount == Decimal("-1000.00")
    assert exposures["GBP"].signed_notional_usd == Decimal("-1140.00000")
    assert exposures["JPY"].signed_native_amount == Decimal("190000.00")
    assert exposures["JPY"].signed_notional_usd == Decimal("1140.00000")
    assert audit.netting_credit_authorized is False


def test_xauusd_uses_same_provider_tick_conversion_contract() -> None:
    opportunity = _opportunity(
        trader=TraderLineage.R34_XAUUSD,
        symbol="XAUUSD",
        entry="3800",
        stop="3790",
        target="3820",
        stop_loss_per_volume="1000",
    )
    provider = _provider(
        symbol="XAUUSD",
        bid="3799.9",
        ask="3800.1",
        contract_size="100",
        tick_size="0.01",
        tick_value="1",
    )

    audit = assess_minimum_seed_factor_magnitude(
        opportunity=opportunity,
        observation=provider,
        decision_at=DECISION_AT,
        provider_evidence_ref="provider:xauusd",
    )

    exposures = {item.factor_id: item for item in audit.exposures}
    assert exposures["XAU"].signed_native_amount == Decimal("1.00")
    assert exposures["XAU"].signed_notional_usd == Decimal("3800.00")
    assert exposures["USD"].signed_native_amount == Decimal("-3800.00")
    assert exposures["USD"].signed_notional_usd == Decimal("-3800.00")
    assert audit.usd_magnitude_complete is True
    assert audit.netting_credit_authorized is False


def test_nas100_resolves_usd_delta_notional_from_provider_tick_economics() -> None:
    opportunity = _opportunity(
        trader=TraderLineage.VT31_NAS100,
        symbol="NAS100",
        entry="20000",
        stop="19900",
        target="20200",
        stop_loss_per_volume="100",
        minimum_volume="1",
        volume_step="1",
    )
    provider = _provider(
        symbol="NAS100",
        bid="19999",
        ask="20001",
        contract_size="1",
        tick_size="1",
        tick_value="1",
        minimum_volume="1",
        volume_step="1",
    )

    audit = assess_minimum_seed_factor_magnitude(
        opportunity=opportunity,
        observation=provider,
        decision_at=DECISION_AT,
        provider_evidence_ref="provider:nas100",
    )

    assert len(audit.exposures) == 1
    exposure = audit.exposures[0]
    assert exposure.factor_id == "US_TECH_EQUITY_BETA"
    assert exposure.signed_native_amount == Decimal("1")
    assert exposure.usd_per_native_unit == Decimal("20000")
    assert exposure.signed_notional_usd == Decimal("20000")
    assert (
        exposure.conversion_basis
        is T08UsdConversionBasis.PROVIDER_TICK_ECONOMICS
    )
    assert audit.native_magnitude_identified is True
    assert audit.usd_magnitude_complete is True
    assert audit.risk_equivalent_identified is False
    assert audit.correlation_state_identified is False
    assert audit.netting_credit_authorized is False
