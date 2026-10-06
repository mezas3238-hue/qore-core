from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_digital_twin import (
    Genc10EconomicBucket,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalCapacityDimension,
    CapitalSource,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_single_account_ceiling_state import (
    CiboCeilingOpenExposure,
    CiboCeilingOpportunityEvidence,
)
from qore.infrastructure.cibo_single_account_historical_capital_ledger import (
    CiboHistoricalCapitalSlice,
    CiboHistoricalOpenDeployment,
    CiboHistoricalProfitGeneration,
    CiboHistoricalResearchCapitalState,
)
from qore.infrastructure.cibo_single_account_historical_ceiling_state import (
    build_historical_ceiling_epoch_state,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="historical-research",
        account_ref="ceiling-usd60",
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _opportunity(signal: str = "alpha") -> CiboCeilingOpportunityEvidence:
    envelope = TraderOpportunityEnvelope(
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint=signal,
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("103"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("20"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("10"),
    )
    return CiboCeilingOpportunityEvidence(
        opportunity=envelope,
        expected_net_value_usd=Decimal("1.5"),
        expected_capital_minutes=Decimal("30"),
        provider_cost_per_volume_usd=Decimal("0.1"),
        expectation_evidence_sha256="sha256:" + "a" * 64,
    )


def test_historical_projection_exposes_continuous_compound_capital() -> None:
    state = CiboHistoricalResearchCapitalState(
        original_base_consumed_usd=Decimal("2"),
        profit_generations=(
            CiboHistoricalProfitGeneration(
                generation=1,
                proven_usd=Decimal("20"),
            ),
        ),
        peak_realized_capital_usd=Decimal("78"),
    )

    epoch = build_historical_ceiling_epoch_state(
        account_identity=_identity(),
        historical_capital=state,
        captured_at=NOW,
        expires_at=NOW + timedelta(minutes=1),
        opportunities=(_opportunity(),),
    )

    assert epoch.capital.assigned_capital_usd == Decimal("78")
    assert epoch.capital.base_capital_at_risk_usd == Decimal("58")
    assert epoch.capital.realized_net_profit_usd == Decimal("20")
    assert epoch.capital.proven_self_financing_capacity_usd == Decimal("20")
    assert epoch.capital_twin.total_realized_capital_usd == Decimal("78")
    assert epoch.capital_twin.original_base_usd == Decimal("58")
    assert epoch.capital_twin.compound_economic_value_usd == Decimal("20")
    assert epoch.capital_twin.bucket(
        Genc10EconomicBucket.REALIZED_PROFIT
    ) == Decimal("20")
    capacities = {
        item.dimension: item for item in epoch.capital_twin.source_capacities
    }
    assert capacities[
        CapitalCapacityDimension.BASE_RISK_CAPITAL
    ].consumed == Decimal("2")
    assert capacities[
        CapitalCapacityDimension.ECONOMIC_PROFIT_CAPITAL
    ].available == Decimal("20")
    assert epoch.twin.opportunities[0].option_id == "alpha"
    assert epoch.capital_twin.known_options[0].option_id == "alpha"
    assert (
        epoch.twin.opportunities[0].requested_capital_usd
        == Decimal("0.101")
    )
    assert (
        epoch.capital_twin.known_options[0].requested_capital_usd
        == Decimal("0.101")
    )
    assert epoch.twin.future_outcome_used is False
    assert epoch.capital_twin.future_leakage_used is False


def test_historical_projection_tracks_open_authorized_capacity() -> None:
    deployment = CiboHistoricalOpenDeployment(
        authorization_id="risk-alpha",
        signal_fingerprint="open-alpha",
        trader_id=TraderLineage.R34_XAUUSD,
        authorized_at=NOW - timedelta(minutes=2),
        authorized_volume=Decimal("1"),
        authorized_stop_risk_usd=Decimal("10"),
        authorized_margin_usd=Decimal("20"),
        provider_cost_usd=Decimal("2"),
        slices=(
            CiboHistoricalCapitalSlice(
                source=CapitalSource.ORIGINAL_BASE_CAPITAL,
                generation=0,
                stop_risk_reserved_usd=Decimal("10"),
            ),
            CiboHistoricalCapitalSlice(
                source=CapitalSource.ORIGINAL_BASE_CAPITAL,
                generation=0,
                provider_cost_reserved_usd=Decimal("2"),
            ),
        ),
    )
    state = CiboHistoricalResearchCapitalState(
        original_base_reserved_usd=Decimal("12"),
        open_deployments=(deployment,),
    )
    exposure = CiboCeilingOpenExposure(
        signal_fingerprint="open-alpha",
        trader_id=TraderLineage.R34_XAUUSD,
        qore_symbol="XAUUSD",
        side="long",
        entry_at=NOW - timedelta(minutes=1),
        volume=Decimal("1"),
        stop_risk_usd=Decimal("10"),
        margin_usd=Decimal("20"),
        provider_cost_usd=Decimal("2"),
        entry_price=Decimal("100"),
        structural_stop=Decimal("90"),
        technical_target=Decimal("120"),
        entry_expected_net_value_usd=Decimal("3"),
        entry_expected_capital_minutes=Decimal("45"),
        expectation_evidence_sha256="sha256:" + "b" * 64,
    )

    epoch = build_historical_ceiling_epoch_state(
        account_identity=_identity(),
        historical_capital=state,
        captured_at=NOW,
        expires_at=NOW + timedelta(minutes=1),
        opportunities=(_opportunity("new-beta"),),
        open_exposures=(exposure,),
        total_stop_risk_capacity_usd=Decimal(
            "60.123456789012345678901234567890123456789"
        ),
        total_margin_capacity_usd=Decimal(
            "100.987654321098765432109876543210987654321"
        ),
    )

    assert epoch.capital_twin.used_stop_risk_usd == Decimal("10")
    assert epoch.capital_twin.stop_risk_headroom_usd == Decimal(
        "50.123456789012345678901234567890123456789"
    )
    assert epoch.capital_twin.used_margin_usd == Decimal("20")
    assert epoch.capital_twin.margin_headroom_usd == Decimal(
        "80.987654321098765432109876543210987654321"
    )
    assert epoch.capital.hard_risk_headroom_usd == Decimal(
        "50.123456789012345678901234567890123456789"
    )
    assert epoch.capital.margin_headroom_usd == Decimal(
        "80.987654321098765432109876543210987654321"
    )
    assert epoch.capital.cost_reserve_usd == Decimal("2")
    assert epoch.twin.portfolio.active_position_ids == ("open-alpha",)



def test_historical_projection_preserves_long_decimal_source_capacity() -> None:
    first = Decimal("1.1111111111111111111111111111111111111111")
    second = Decimal("2.2222222222222222222222222222222222222222")
    total = Decimal("3.3333333333333333333333333333333333333333")
    state = CiboHistoricalResearchCapitalState(
        profit_generations=(
            CiboHistoricalProfitGeneration(
                generation=1,
                proven_usd=first,
            ),
            CiboHistoricalProfitGeneration(
                generation=2,
                proven_usd=second,
            ),
        ),
        peak_realized_capital_usd=Decimal(
            "63.3333333333333333333333333333333333333333"
        ),
    )

    epoch = build_historical_ceiling_epoch_state(
        account_identity=_identity(),
        historical_capital=state,
        captured_at=NOW,
        expires_at=NOW + timedelta(minutes=1),
        opportunities=(_opportunity(),),
    )
    capacities = {
        item.dimension: item for item in epoch.capital_twin.source_capacities
    }
    profit = capacities[CapitalCapacityDimension.ECONOMIC_PROFIT_CAPITAL]

    assert profit.proven == total
    assert profit.available == total
    assert profit.reserved == Decimal("0")
    assert profit.deployed == Decimal("0")
    assert profit.consumed == Decimal("0")
