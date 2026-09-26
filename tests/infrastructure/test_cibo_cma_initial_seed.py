from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_cma_initial_seed import build_initial_seed_request


def _opportunity(
    *,
    minimum_volume: str = "0.01",
    minimum_execution_steps: int = 1,
) -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint="signal-1",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("1.1000"),
        stop_loss=Decimal("1.0950"),
        take_profit=Decimal("1.1100"),
        stop_loss_per_volume=Decimal("100"),
        margin_per_volume=Decimal("200"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal(minimum_volume),
        maximum_volume=Decimal("100"),
        minimum_execution_steps=minimum_execution_steps,
    )


def test_initial_seed_uses_broker_minimum_not_legacy_risk_budget() -> None:
    now = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
    seed = build_initial_seed_request(
        request_id="cma-seed-1",
        opportunity=_opportunity(),
        assigned_capital_usd=Decimal("142857.14"),
        observed_free_margin_usd=Decimal("900000"),
        requested_at=now,
        expires_at=now + timedelta(seconds=30),
    )

    assert seed.plan.volume == Decimal("0.01")
    assert seed.plan.stop_risk_usd == Decimal("1.00")
    assert seed.request.requested_volume == Decimal("0.01")
    assert seed.request.strategy_requested_risk_usd is None


def test_vt31_style_four_leg_seed_uses_four_broker_minimums() -> None:
    now = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
    seed = build_initial_seed_request(
        request_id="cma-vt31",
        opportunity=_opportunity(
            minimum_volume="0.10",
            minimum_execution_steps=4,
        ),
        assigned_capital_usd=Decimal("142857.14"),
        observed_free_margin_usd=Decimal("900000"),
        requested_at=now,
        expires_at=now + timedelta(seconds=30),
    )

    assert seed.plan.volume == Decimal("0.40")


def test_seed_fails_closed_when_observed_free_margin_cannot_support_minimum() -> None:
    now = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)

    with pytest.raises(CiboCapitalManagementError, match="minimal seed unavailable"):
        build_initial_seed_request(
            request_id="cma-no-margin",
            opportunity=_opportunity(),
            assigned_capital_usd=Decimal("1000"),
            observed_free_margin_usd=Decimal("0.50"),
            requested_at=now,
            expires_at=now + timedelta(seconds=30),
        )


def test_seed_fails_closed_when_minimum_stop_risk_exceeds_assigned_capital() -> None:
    now = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
    opportunity = TraderOpportunityEnvelope(
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint="xau-1",
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("2600"),
        stop_loss=Decimal("2500"),
        take_profit=Decimal("2700"),
        stop_loss_per_volume=Decimal("200000"),
        margin_per_volume=Decimal("10"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
    )

    with pytest.raises(CiboCapitalManagementError, match="minimal seed unavailable"):
        build_initial_seed_request(
            request_id="cma-too-risky",
            opportunity=opportunity,
            assigned_capital_usd=Decimal("1000"),
            observed_free_margin_usd=Decimal("1000"),
            requested_at=now,
            expires_at=now + timedelta(seconds=30),
        )
