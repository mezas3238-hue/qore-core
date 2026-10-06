from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_factor_returns import (
    FROZEN_T08_FACTOR_IDS,
    T08FactorReturn,
    T08FactorReturnObservation,
    T08MarketCollectionBasis,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_risk_mapping import (
    assess_t08_candidate_risk_mapping,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
)

DECISION_AT = datetime(2026, 9, 29, 1, tzinfo=UTC)
BASE = DECISION_AT - timedelta(hours=4)


def _factor_observation(index: int) -> T08FactorReturnObservation:
    start = BASE + timedelta(minutes=5 * index)
    end = start + timedelta(minutes=5)
    base = Decimal(index + 1) / Decimal("10000")
    returns = {
        "AUD": base,
        "EUR": base * Decimal(2),
        "GBP": base * Decimal(3),
        "JPY": -base,
        "USD": Decimal(0),
        "US_TECH_EQUITY_BETA": base * Decimal(4),
        "XAU": -base * Decimal(2),
    }
    return T08FactorReturnObservation(
        provider_key="ctrader-demo",
        start_snapshot_id=f"s{index}",
        end_snapshot_id=f"s{index + 1}",
        start_market_at=start,
        end_market_at=end,
        known_at=end + timedelta(milliseconds=10),
        collection_basis=T08MarketCollectionBasis.FULL_FROZEN_UNIVERSE,
        factor_returns=tuple(
            T08FactorReturn(
                factor_id=factor_id,
                gross_change=Decimal(1) + returns[factor_id],
                fractional_return=returns[factor_id],
            )
            for factor_id in FROZEN_T08_FACTOR_IDS
        ),
        source_evidence_refs=(f"factor:{index}",),
    )


def _opportunity(
    *,
    trader: TraderLineage,
    symbol: str,
    entry: str,
    stop: str,
    target: str,
    stop_loss_per_volume: str,
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
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
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
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("10"),
        volume_step=Decimal("0.01"),
        margin_per_volume=Decimal("1000"),
        commission_per_volume_usd=Decimal(0),
        slippage_reserve_per_volume_usd=Decimal(0),
        observed_at=DECISION_AT - timedelta(seconds=1),
    )


def test_usd_quote_pair_allocates_all_stop_risk_to_stochastic_factor() -> None:
    audit = assess_t08_candidate_risk_mapping(
        opportunity=_opportunity(
            trader=TraderLineage.R43_GBPUSD,
            symbol="GBPUSD",
            entry="1.25",
            stop="1.24",
            target="1.27",
            stop_loss_per_volume="1200",
        ),
        observation=_provider(
            symbol="GBPUSD",
            bid="1.2499",
            ask="1.2501",
            contract_size="100000",
            tick_size="0.0001",
            tick_value="10",
        ),
        factor_returns=tuple(_factor_observation(i) for i in range(32)),
        decision_at=DECISION_AT,
        provider_evidence_ref="provider:gbpusd",
    )

    assert audit.candidate_mapping_identified is True
    assert audit.structural_stop_risk_usd == Decimal("12.00")
    assert audit.gross_allocated_risk_usd == Decimal("12.00")
    assert len(audit.allocations) == 1
    allocation = audit.allocations[0]
    assert allocation.factor_id == "GBP"
    assert allocation.risk_share == Decimal(1)
    assert allocation.signed_risk_usd == Decimal("12.00")
    assert audit.risk_mapping_verified is False
    assert audit.netting_credit_authorized is False


def test_cross_pair_covariance_attribution_is_not_fixed_fifty_fifty() -> None:
    audit = assess_t08_candidate_risk_mapping(
        opportunity=_opportunity(
            trader=TraderLineage.R38_GBPJPY,
            symbol="GBPJPY",
            entry="190",
            stop="189",
            target="192",
            stop_loss_per_volume="700",
        ),
        observation=_provider(
            symbol="GBPJPY",
            bid="189.99",
            ask="190.01",
            contract_size="100000",
            tick_size="0.01",
            tick_value="6",
        ),
        factor_returns=tuple(_factor_observation(i) for i in range(32)),
        decision_at=DECISION_AT,
        provider_evidence_ref="provider:gbpjpy",
    )

    by_factor = {item.factor_id: item for item in audit.allocations}
    assert audit.structural_stop_risk_usd == Decimal("7.00")
    assert audit.gross_allocated_risk_usd == Decimal("7.00")
    assert by_factor["GBP"].risk_share == Decimal("0.75")
    assert by_factor["JPY"].risk_share == Decimal("0.25")
    assert by_factor["GBP"].signed_risk_usd == Decimal("5.2500")
    assert by_factor["JPY"].signed_risk_usd == Decimal("-1.7500")
    assert audit.risk_mapping_verified is False
    assert audit.netting_credit_authorized is False


def test_mapping_stays_unidentified_without_minimum_correlation_sample() -> None:
    audit = assess_t08_candidate_risk_mapping(
        opportunity=_opportunity(
            trader=TraderLineage.R43_GBPUSD,
            symbol="GBPUSD",
            entry="1.25",
            stop="1.24",
            target="1.27",
            stop_loss_per_volume="1200",
        ),
        observation=_provider(
            symbol="GBPUSD",
            bid="1.2499",
            ask="1.2501",
            contract_size="100000",
            tick_size="0.0001",
            tick_value="10",
        ),
        factor_returns=tuple(_factor_observation(i) for i in range(12)),
        decision_at=DECISION_AT,
        provider_evidence_ref="provider:gbpusd",
    )

    assert audit.candidate_mapping_identified is False
    assert audit.allocations == ()
    assert audit.gross_allocated_risk_usd == Decimal(0)
    assert "T08_FACTOR_RISK_MAPPING_NOT_IDENTIFIED" in audit.blockers
    assert audit.netting_credit_authorized is False
