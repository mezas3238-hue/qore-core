from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_single_account_ceiling_state import (
    CiboCeilingOpenExposure,
    CiboCeilingOpportunityEvidence,
    build_ceiling_epoch_state,
    initialize_ceiling_account_state,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment


NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader-research",
        account_ref="cibo-ceiling",
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _opportunity(
    *,
    signal: str = "ceiling-signal",
    trader: TraderLineage = TraderLineage.R34_XAUUSD,
    symbol: str = "XAUUSD",
) -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=trader,
        signal_fingerprint=signal,
        qore_symbol=symbol,
        provider_symbol=symbol,
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


def _evidence(opportunity: TraderOpportunityEnvelope):
    return CiboCeilingOpportunityEvidence(
        opportunity=opportunity,
        expected_net_value_usd=Decimal("0.02"),
        expected_capital_minutes=Decimal("30"),
        provider_cost_per_volume_usd=Decimal("0.10"),
        expectation_evidence_sha256="sha256:" + "a" * 64,
    )


def test_initial_ceiling_epoch_is_exact_single_usd60_account() -> None:
    account = initialize_ceiling_account_state(
        account_identity=_identity(),
    )
    epoch = build_ceiling_epoch_state(
        account=account,
        captured_at=NOW,
        expires_at=NOW + timedelta(minutes=1),
        opportunities=(_evidence(_opportunity()),),
    )

    assert epoch.account.realized_capital_usd == Decimal("60")
    assert epoch.twin.capital_twin.total_realized_capital_usd == Decimal("60")
    assert epoch.twin.capital_twin.original_base_usd == Decimal("60")
    assert epoch.twin.capital_twin.compound_economic_value_usd == Decimal("0")
    assert epoch.twin.capital_twin.stop_risk_headroom_usd == Decimal("60")
    assert epoch.twin.capital_twin.margin_headroom_usd == Decimal("60")
    assert epoch.capital.assigned_capital_usd == Decimal("60")
    assert epoch.capital.realized_net_profit_usd == Decimal("0")
    assert epoch.capital.proven_self_financing_capacity_usd == Decimal("0")
    assert epoch.twin.future_outcome_used is False


def test_simultaneous_same_symbol_opportunities_do_not_duplicate_provider_state() -> None:
    account = initialize_ceiling_account_state(
        account_identity=_identity(),
    )
    first = _opportunity(signal="a")
    second = _opportunity(
        signal="b",
        trader=TraderLineage.R38_EURUSD,
    )
    epoch = build_ceiling_epoch_state(
        account=account,
        captured_at=NOW,
        expires_at=NOW + timedelta(minutes=1),
        opportunities=(_evidence(first), _evidence(second)),
    )

    assert len(epoch.twin.opportunities) == 2
    assert epoch.twin.provider_state == (
        ("XAUUSD", "COUNTERFACTUAL_PROVIDER_ECONOMICS"),
    )


def test_open_exposure_is_counted_once_in_t19_and_reduces_headroom() -> None:
    account = initialize_ceiling_account_state(
        account_identity=_identity(),
    )
    exposure = CiboCeilingOpenExposure(
        signal_fingerprint="open-1",
        trader_id=TraderLineage.R34_XAUUSD,
        qore_symbol="XAUUSD",
        side="long",
        entry_at=NOW - timedelta(minutes=10),
        volume=Decimal("1"),
        stop_risk_usd=Decimal("10"),
        margin_usd=Decimal("20"),
        provider_cost_usd=Decimal("0.10"),
        entry_price=Decimal("100"),
        structural_stop=Decimal("99"),
        technical_target=Decimal("103"),
        entry_expected_net_value_usd=Decimal("0.20"),
        entry_expected_capital_minutes=Decimal("30"),
        expectation_evidence_sha256="sha256:" + "b" * 64,
    )
    account = replace(account, open_exposures=(exposure,))

    epoch = build_ceiling_epoch_state(
        account=account,
        captured_at=NOW,
        expires_at=NOW + timedelta(minutes=1),
        opportunities=(_evidence(_opportunity(signal="new-1")),),
    )

    assert epoch.twin.capital_twin.used_stop_risk_usd == Decimal("10")
    assert epoch.twin.capital_twin.used_margin_usd == Decimal("20")
    assert epoch.twin.capital_twin.stop_risk_headroom_usd == Decimal("50")
    assert epoch.twin.capital_twin.margin_headroom_usd == Decimal("40")
    assert epoch.twin.portfolio.reserved_stop_risk_usd == Decimal("0")
    assert epoch.twin.portfolio.reserved_margin_usd == Decimal("0")
    assert epoch.twin.positions[0].current_stop_risk_usd == Decimal("10")
    assert epoch.capital.hard_risk_headroom_usd == Decimal("50")
    assert epoch.capital.margin_headroom_usd == Decimal("40")
