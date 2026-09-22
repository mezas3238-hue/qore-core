from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.fundednext_live_guard import (
    DurableFundedNextLiveCapitalStore,
    FundedNextLiveCapitalCheckpoint,
    FundedNextLiveGuardError,
    InactivityState,
    assert_certified_direction,
    causal_daily_candidate_allowed,
    h4_containment_exit_at,
    inactivity_state,
    market_stop_risk_usd,
)

_NOW = datetime(2026, 9, 15, 13, 0, tzinfo=UTC)


def test_certified_direction_contract_is_frozen() -> None:
    assert_certified_direction("AUDJPY", "short")
    assert_certified_direction("GBPUSD", "short")
    assert_certified_direction("GBPJPY", "long")
    assert_certified_direction("GBPJPY", "short")
    assert_certified_direction("NAS100", "long")
    assert_certified_direction("NAS100", "short")
    with pytest.raises(FundedNextLiveGuardError, match="direction-outside"):
        assert_certified_direction("GBPUSD", "long")


def test_live_causal_candidate_accepts_all_authorized_forex_anchors() -> None:
    for hour in (1, 5, 9):
        assert causal_daily_candidate_allowed(
            candidate_anchor_hours=(hour,), current_anchor_hour=hour
        )
    assert causal_daily_candidate_allowed(
        candidate_anchor_hours=(1, 5), current_anchor_hour=5
    )
    assert causal_daily_candidate_allowed(
        candidate_anchor_hours=(1, 5, 9), current_anchor_hour=9
    )
    assert not causal_daily_candidate_allowed(
        candidate_anchor_hours=(1,), current_anchor_hour=5
    )
    assert not causal_daily_candidate_allowed(
        candidate_anchor_hours=(13,), current_anchor_hour=13
    )


def test_market_stop_risk_includes_opening_commission() -> None:
    risk = market_stop_risk_usd(
        executable_entry=Decimal("1.2500"),
        stop_loss=Decimal("1.2550"),
        tick_size=Decimal("0.00001"),
        tick_value=Decimal("1"),
        volume=Decimal("0.01"),
    )
    assert risk == Decimal("5.07")


def test_h4_containment_exit_is_four_hours_after_exact_anchor() -> None:
    signal = datetime(2026, 9, 15, 13, 0, tzinfo=UTC)
    assert h4_containment_exit_at(signal) == datetime(2026, 9, 15, 17, 0, tzinfo=UTC)


def test_inactivity_warns_without_inventing_trade_and_then_blocks() -> None:
    warning = inactivity_state(last_activity_at=_NOW, now=_NOW + timedelta(days=25))
    blocked = inactivity_state(last_activity_at=_NOW, now=_NOW + timedelta(days=30))
    assert warning is InactivityState.WARNING
    assert blocked is InactivityState.BLOCKED


def test_capital_checkpoint_requires_durable_copy_and_never_moves_down(tmp_path: Path) -> None:
    store = DurableFundedNextLiveCapitalStore(
        tmp_path / "capital.json", tmp_path / "capital.backup.json"
    )
    with pytest.raises(FundedNextLiveGuardError, match="checkpoint-missing"):
        store.load_required()
    checkpoint = FundedNextLiveCapitalCheckpoint(
        git_sha="a" * 40,
        account_identity_fingerprint="b" * 64,
        highest_closed_balance=Decimal("2050"),
        active_mll=Decimal("1930"),
        created_at=_NOW,
        updated_at=_NOW,
    )
    store.initialize_once(checkpoint)
    assert store.load_required() == checkpoint
    (tmp_path / "capital.json").unlink()
    assert store.load_required() == checkpoint
    with pytest.raises(FundedNextLiveGuardError, match="cannot move downward"):
        checkpoint.advance(
            highest_closed_balance=Decimal("2040"),
            active_mll=Decimal("1930"),
            updated_at=_NOW + timedelta(minutes=1),
        )
