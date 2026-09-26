"""CIBO CMA sizing-authority telemetry invariants."""
# ruff: noqa: I001

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.account_wide_risk import CiboRiskRequest, TraderLineage
from qore.infrastructure.ctrader_demo_free_sink import (
    CTraderDemoFreeSinkError,
    assert_cibo_sizing_authority,
)
from qore.infrastructure.ctrader_demo_live_behavior_lab import sizing_path_for


ACTIVE = (
    "VT08_FOREX",
    "R34_XAUUSD",
    "R38_EURUSD",
    "R43_GBPUSD",
    "R38_GBPJPY",
    "R42_AUDJPY",
    "VT31_NAS100",
)


def test_all_active_demo_traders_emit_cibo_cma_sizing_path() -> None:
    assert {
        sizing_path_for(trader)
        for trader in ACTIVE
    } == {"CIBO_CMA_MINIMAL_SEED"}


def test_sink_records_cibo_as_sizing_and_capital_authority() -> None:
    source = Path(
        "src/qore/infrastructure/ctrader_demo_free_sink.py"
    ).read_text(encoding="utf-8")

    assert '"sizing_authority": "CIBO_CMA"' in source
    assert '"capital_management_authority": "CIBO_CMA"' in source



def _request(
    *,
    strategy_requested_risk_usd: Decimal | None,
) -> CiboRiskRequest:
    now = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
    return CiboRiskRequest(
        request_id="authority-test",
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint="signal-1",
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        entry_type="MARKET",
        intended_entry=Decimal("2600"),
        stop_loss=Decimal("2590"),
        take_profit=Decimal("2620"),
        requested_volume=Decimal("0.01"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("25"),
        requested_at=now,
        expires_at=now + timedelta(minutes=1),
        strategy_requested_risk_usd=strategy_requested_risk_usd,
        minimum_volume_uplifted=False,
    )


def test_sink_accepts_only_cibo_owned_volume_authority() -> None:
    assert_cibo_sizing_authority(
        _request(strategy_requested_risk_usd=None)
    )


def test_sink_rejects_legacy_trader_risk_budget_authority() -> None:
    with pytest.raises(
        CTraderDemoFreeSinkError,
        match="legacy Trader sizing authority is forbidden",
    ):
        assert_cibo_sizing_authority(
            _request(strategy_requested_risk_usd=Decimal("5"))
        )
