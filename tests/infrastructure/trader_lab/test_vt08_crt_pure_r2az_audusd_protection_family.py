from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    Model1LabTrade,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2az_audusd_protection_family import (
    IDENTITY,
    POLICY_PARAMETERS,
    ProtectionPolicy,
    _simulate,
)


def _trade() -> Model1LabTrade:
    start = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    return Model1LabTrade(
        schema="test",
        identity="test",
        market="AUDUSD",
        reference_policy="TEST",
        reference_count=1,
        reference_ids=("ref",),
        parent_direction="BULLISH",
        timing_triplet="ROLLING_H4:1",
        c3_opened_at=start.isoformat(),
        source_opened_at=start.isoformat(),
        confirmation_opened_at=start.isoformat(),
        entry_opened_at=start.isoformat(),
        entry_price_relative=100,
        stop_price_relative=90,
        target_price_relative="115",
        exit_price_relative="100",
        exit_reason="C3_CLOSE",
        r_multiple=0.0,
    )


def _bar(
    offset: int,
    *,
    high: int,
    low: int,
    close: int,
) -> M15Bar:
    opened = datetime(2026, 1, 1, 0, 0, tzinfo=UTC) + timedelta(
        minutes=15 * offset
    )
    return M15Bar(
        opened_at=opened,
        open_price=100,
        high_price=high,
        low_price=low,
        close_price=close,
    )


def test_r2az_identity_and_family_are_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2AZ_AUDUSD_CAUSAL_PROTECTION_FAMILY_001"
    assert POLICY_PARAMETERS[ProtectionPolicy.BE_CLOSE_050][0] is not None
    assert POLICY_PARAMETERS[ProtectionPolicy.LOCK050_CLOSE_100][1] is not None


def test_be_close_050_acts_only_on_next_bar() -> None:
    trade = _trade()
    bars = (
        _bar(0, high=106, low=99, close=106),
        _bar(1, high=107, low=99, close=101),
    )
    managed = _simulate(
        trade=trade,
        bars=bars,
        policy=ProtectionPolicy.BE_CLOSE_050,
    )
    assert managed.r_multiple == 0.0
    assert managed.exit_reason == "STOP"


def test_protection_does_not_retroactively_save_trigger_bar() -> None:
    trade = _trade()
    bars = (_bar(0, high=106, low=89, close=106),)
    managed = _simulate(
        trade=trade,
        bars=bars,
        policy=ProtectionPolicy.BE_CLOSE_050,
    )
    assert managed.r_multiple == -1.0


def test_control_preserves_fixed_target() -> None:
    trade = _trade()
    bars = (_bar(0, high=116, low=99, close=114),)
    managed = _simulate(
        trade=trade,
        bars=bars,
        policy=ProtectionPolicy.CONTROL,
    )
    assert managed.r_multiple == 1.5
