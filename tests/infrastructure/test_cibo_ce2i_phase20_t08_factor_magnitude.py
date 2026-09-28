from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_factor_magnitude import (
    FactorUsdConversion,
    T08FactorVolumeBasis,
    assess_minimum_seed_factor_magnitude,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
)


DECISION_AT = datetime(2026, 9, 28, 18, 0, tzinfo=UTC)


def _opportunity(
    *,
    trader: TraderLineage,
    symbol: str,
    entry: str,
    stop: str,
    target: str,
    stop_loss_per_volume: str,
    minimum_volume: str = "0.01",
    volume_step: str = "0.01",
) -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=trader,
        signal_fingerprint=f"signal:{symbol.lower()}",
        qore_symbol=symbol,
        provider_symbol=symbol,
        side="long",
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


def test_quote_usd_pair_resolves_notional_without_splitting_stop_risk() -> None:
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
    assert exposures["GBP"].signed_notional_usd == Decimal("1250.0000")
    assert exposures["USD"].signed_native_amount == Decimal("-1250.0000")
    assert exposures["USD"].signed_notional_usd == Decimal("-1250.0000")
    assert audit.native_magnitude_identified is True
    assert audit.usd_magnitude_complete is True
    assert audit.risk_equivalent_identified is False
    assert audit.correlation_state_identified is False
    assert audit.netting_credit_authorized is False
    assert "FACTOR_NOTIONAL_TO_SIGNED_RISK_USD_MAPPING_NOT_IDENTIFIED" in (
        audit.blockers
    )


def test_cross_pair_keeps_native_magnitude_and_blocks_missing_usd_conversion() -> None:
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
    assert exposures["JPY"].signed_native_amount == Decimal("-190000.00")
    assert exposures["GBP"].signed_notional_usd is None
    assert exposures["JPY"].signed_notional_usd is None
    assert audit.native_magnitude_identified is True
    assert audit.usd_magnitude_complete is False
    assert "USD_CONVERSION_REQUIRED:GBP" in audit.blockers
    assert "USD_CONVERSION_REQUIRED:JPY" in audit.blockers
    assert audit.netting_credit_authorized is False


def test_cross_pair_accepts_only_causal_explicit_usd_conversions() -> None:
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
    conversions = (
        FactorUsdConversion(
            factor_id="GBP",
            usd_per_native_unit=Decimal("1.25"),
            observed_at=DECISION_AT - timedelta(seconds=2),
            evidence_ref="fx:gbpusd:predecision",
        ),
        FactorUsdConversion(
            factor_id="JPY",
            usd_per_native_unit=Decimal("0.0065"),
            observed_at=DECISION_AT - timedelta(seconds=2),
            evidence_ref="fx:jpyusd:predecision",
        ),
    )

    audit = assess_minimum_seed_factor_magnitude(
        opportunity=opportunity,
        observation=provider,
        decision_at=DECISION_AT,
        provider_evidence_ref="provider:gbpjpy",
        conversions=conversions,
    )

    exposures = {item.factor_id: item for item in audit.exposures}
    assert exposures["GBP"].signed_notional_usd == Decimal("1250.0000")
    assert exposures["JPY"].signed_notional_usd == Decimal("-1235.000000")
    assert audit.usd_magnitude_complete is True
    assert not any(
        blocker.startswith("USD_CONVERSION_REQUIRED:")
        for blocker in audit.blockers
    )
    assert audit.risk_equivalent_identified is False
    assert audit.correlation_state_identified is False
    assert audit.netting_credit_authorized is False


def test_nas100_stays_blocked_without_explicit_contract_denomination() -> None:
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

    assert audit.exposures == ()
    assert audit.native_magnitude_identified is False
    assert audit.usd_magnitude_complete is False
    assert "PROVIDER_CONTRACT_DENOMINATION_REQUIRED:NAS100" in audit.blockers
    assert audit.netting_credit_authorized is False


def test_future_conversion_evidence_is_rejected_before_any_magnitude_claim() -> None:
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

    with pytest.raises(
        CiboCapitalManagementError,
        match="conversion evidence cannot postdate decision",
    ):
        assess_minimum_seed_factor_magnitude(
            opportunity=opportunity,
            observation=provider,
            decision_at=DECISION_AT,
            provider_evidence_ref="provider:gbpjpy",
            conversions=(
                FactorUsdConversion(
                    factor_id="GBP",
                    usd_per_native_unit=Decimal("1.25"),
                    observed_at=DECISION_AT + timedelta(milliseconds=1),
                    evidence_ref="fx:future",
                ),
            ),
        )
