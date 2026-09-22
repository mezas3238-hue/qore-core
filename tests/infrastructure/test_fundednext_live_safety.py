from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.account_wide_risk import RiskAuthorization, RiskDecision, TraderLineage
from qore.infrastructure.execution_boundary import ExecutionSubmission
from qore.infrastructure.fundednext_live_safety import (
    FundedNextLiveSafetyState,
    JsonFileLiveOperationalSafetyBoundary,
    initialize_live_safety_state,
    store_live_safety_state,
)
from qore.infrastructure.fundednext_mt5 import Mt5ExecutionBlockedError
from qore.infrastructure.fundednext_operational import build_account_bound_submission
from qore.infrastructure.pretrade_safety import ExecutionSafetySwitchSnapshot, ExecutionSwitchState

_NOW = datetime(2026, 9, 15, 13, 0, tzinfo=UTC)


def _submission() -> ExecutionSubmission:
    auth = RiskAuthorization(
        authorization_id="risk-1",
        account_binding_id="b" * 64,
        trader_id=TraderLineage.VT08_FOREX,
        request_id="request-1",
        signal_fingerprint="signal-1",
        qore_symbol="GBPUSD",
        provider_symbol="GBPUSD",
        side="short",
        entry_type="market",
        intended_entry=Decimal("1.25"),
        stop_loss=Decimal("1.26"),
        take_profit=Decimal("1.23"),
        requested_volume=Decimal("0.01"),
        authorized_volume=Decimal("0.01"),
        monetary_stop_loss=Decimal("1"),
        aggregate_pre_order_worst_case=Decimal("0"),
        aggregate_post_order_worst_case=Decimal("1"),
        provider_headroom=Decimal("120"),
        internal_qore_headroom=Decimal("20"),
        margin_reserved=Decimal("1"),
        decision=RiskDecision.ALLOW,
        reason="test",
        issued_at=_NOW,
        expires_at=_NOW + timedelta(minutes=2),
        authorization_fingerprint="c" * 64,
    )
    return build_account_bound_submission(
        auth,
        switch=ExecutionSafetySwitchSnapshot(
            state=ExecutionSwitchState.ENABLED,
            observed_at=_NOW,
            reason="test",
        ),
        authorized_at=_NOW,
        submitted_at=_NOW,
    )


def test_missing_safety_file_fails_closed(tmp_path: Path) -> None:
    boundary = JsonFileLiveOperationalSafetyBoundary(tmp_path / "safety.json")
    with pytest.raises(Exception, match="live-safety-state-missing"):
        boundary.assert_new_order_allowed(_submission())


def test_market_kill_switch_blocks_new_order(tmp_path: Path) -> None:
    path = tmp_path / "safety.json"
    initialize_live_safety_state(path)
    store_live_safety_state(
        path,
        FundedNextLiveSafetyState(
            account_enabled=True,
            gateway_enabled=True,
            disabled_traders=(),
            disabled_markets=("GBPUSD",),
        ),
    )
    boundary = JsonFileLiveOperationalSafetyBoundary(path)
    with pytest.raises(Mt5ExecutionBlockedError, match="market-kill-switch"):
        boundary.assert_new_order_allowed(_submission())


def test_default_safety_allows_certified_path(tmp_path: Path) -> None:
    path = tmp_path / "safety.json"
    initialize_live_safety_state(path)
    JsonFileLiveOperationalSafetyBoundary(path).assert_new_order_allowed(_submission())
