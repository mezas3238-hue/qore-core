from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CapitalSource,
    CapitalStage,
    CiboCapitalActionPlan,
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_cma_risk_request import build_cma_risk_request


def _opportunity() -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint="signal-1",
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        entry_type="MARKET",
        intended_entry=Decimal("2600"),
        stop_loss=Decimal("2590"),
        take_profit=Decimal("2620"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("25"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
    )


def _plan(action: CapitalAction = CapitalAction.OPEN_MINIMAL_SEED) -> CiboCapitalActionPlan:
    return CiboCapitalActionPlan(
        trader_id=TraderLineage.R34_XAUUSD,
        qore_symbol="XAUUSD",
        stage=(
            CapitalStage.MINIMAL_SEED
            if action is CapitalAction.OPEN_MINIMAL_SEED
            else CapitalStage.CAPITALIZE
        ),
        action=action,
        volume=Decimal("0.01"),
        stop_risk_usd=Decimal("0.10"),
        margin_usd=Decimal("0.25"),
        capital_source=(
            CapitalSource.ORIGINAL_BASE_CAPITAL
            if action is CapitalAction.OPEN_MINIMAL_SEED
            else CapitalSource.REALIZED_PROFIT
        ),
        capital_source_amount_usd=Decimal("0.10"),
        reason="test",
    )


def test_risk_request_volume_comes_from_cibo_plan() -> None:
    now = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
    request = build_cma_risk_request(
        request_id="cma-1",
        opportunity=_opportunity(),
        plan=_plan(),
        requested_at=now,
        expires_at=now + timedelta(minutes=1),
    )

    assert request.requested_volume == Decimal("0.01")
    assert request.requested_stop_risk == Decimal("0.10")
    assert request.requested_margin == Decimal("0.25")
    assert request.strategy_requested_risk_usd is None


def test_hold_plan_cannot_reach_risk_engine() -> None:
    now = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
    hold = CiboCapitalActionPlan(
        trader_id=TraderLineage.R34_XAUUSD,
        qore_symbol="XAUUSD",
        stage=CapitalStage.OBSERVE,
        action=CapitalAction.HOLD,
        volume=Decimal("0"),
        stop_risk_usd=Decimal("0"),
        margin_usd=Decimal("0"),
        capital_source=None,
        capital_source_amount_usd=Decimal("0"),
        reason="hold",
    )

    with pytest.raises(CiboCapitalManagementError, match="deployment"):
        build_cma_risk_request(
            request_id="cma-hold",
            opportunity=_opportunity(),
            plan=hold,
            requested_at=now,
            expires_at=now + timedelta(minutes=1),
        )


def test_plan_economics_must_match_opportunity() -> None:
    now = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
    bad = CiboCapitalActionPlan(
        trader_id=TraderLineage.R34_XAUUSD,
        qore_symbol="XAUUSD",
        stage=CapitalStage.MINIMAL_SEED,
        action=CapitalAction.OPEN_MINIMAL_SEED,
        volume=Decimal("0.01"),
        stop_risk_usd=Decimal("9"),
        margin_usd=Decimal("0.25"),
        capital_source=CapitalSource.ORIGINAL_BASE_CAPITAL,
        capital_source_amount_usd=Decimal("9"),
        reason="bad",
    )

    with pytest.raises(CiboCapitalManagementError, match="stop risk"):
        build_cma_risk_request(
            request_id="cma-bad",
            opportunity=_opportunity(),
            plan=bad,
            requested_at=now,
            expires_at=now + timedelta(minutes=1),
        )
