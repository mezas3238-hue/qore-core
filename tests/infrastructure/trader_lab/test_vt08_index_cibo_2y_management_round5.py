from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as mod
from qore.infrastructure.trader_lab import vt08_index_v6_ttrades_source_faithful as v6
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar


def _bar(
    at: datetime,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> Vt08IndexC2R1Bar:
    return Vt08IndexC2R1Bar(
        opened_at=at,
        closed_at=at + timedelta(minutes=15),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def _signal(at: datetime) -> v6.CandidateSignal:
    poi = v6.SourcePoi(
        v6.PoiKind.CISD,
        Decimal("100"),
        Decimal("100"),
        at - timedelta(minutes=15),
    )
    return v6.CandidateSignal(
        symbol="NAS100",
        side=DemoTradingSetupSide.LONG,
        model_kind=v6.H4ModelKind.SAME_C2,
        h4_opened_at=at - timedelta(hours=1),
        signal_at=at,
        entry=Decimal("100"),
        stop=Decimal("99"),
        target=Decimal("102.5"),
        poi=poi,
        cisd_level=Decimal("100"),
        cisd_confirmed_at=at,
        protected_swing_extreme=Decimal("99"),
    )


def test_fixed_density_contract_is_657() -> None:
    assert mod.FIXED_DENSITY == 657
    assert mod.PF_GOAL == Decimal("1.50")
    assert mod.DD_GOAL == Decimal("6")


def test_policy_grid_preserves_target_and_management_dimensions() -> None:
    policies = mod._policy_grid()
    assert len(policies) == 648
    assert {policy.target_r for policy in policies} == {
        Decimal("2.0"),
        Decimal("2.5"),
        Decimal("3.0"),
    }
    assert {policy.trail_name for policy in policies} == {
        "OFF",
        "BE050",
        "LOCK025_075",
        "STAIR_A",
        "STAIR_B",
        "STAIR_C",
    }


def test_soft_close_can_cut_loss_before_structural_stop() -> None:
    start = datetime(2017, 1, 2, 14, 0, tzinfo=UTC)
    signal = _signal(start)
    bars = (
        _bar(start, "100", "100.1", "99.6", "99.7"),
        _bar(start + timedelta(minutes=15), "99.7", "99.8", "99.4", "99.5"),
    )
    policy = mod.Policy(
        target_r=Decimal("2.5"),
        soft_close_loss_r=Decimal("0.25"),
        soft_close_until_mfe_r=Decimal("0.5"),
        deadline_bars=None,
        deadline_min_mfe_r=None,
        trail_name="OFF",
        trail_steps=(),
    )
    result = mod._manage_trade(
        signal,
        bars=bars,
        opened=tuple(bar.opened_at for bar in bars),
        policy=policy,
    )
    assert result.exit_reason == "soft-close-loss"
    assert result.r_multiple == Decimal("-0.3")


def test_trail_only_activates_after_completed_milestone_bar() -> None:
    start = datetime(2017, 1, 2, 14, 0, tzinfo=UTC)
    signal = _signal(start)
    bars = (
        _bar(start, "100", "100.6", "99.8", "100.4"),
        _bar(start + timedelta(minutes=15), "100.4", "100.5", "99.95", "100.1"),
    )
    policy = mod.Policy(
        target_r=Decimal("2.5"),
        soft_close_loss_r=None,
        soft_close_until_mfe_r=None,
        deadline_bars=None,
        deadline_min_mfe_r=None,
        trail_name="BE050",
        trail_steps=((Decimal("0.5"), Decimal("0")),),
    )
    result = mod._manage_trade(
        signal,
        bars=bars,
        opened=tuple(bar.opened_at for bar in bars),
        policy=policy,
    )
    assert result.exit_reason == "stop"
    assert result.r_multiple == Decimal("0")


def test_no_progress_deadline_is_causal_close_exit() -> None:
    start = datetime(2017, 1, 2, 14, 0, tzinfo=UTC)
    signal = _signal(start)
    bars = (
        _bar(start, "100", "100.1", "99.8", "99.95"),
        _bar(start + timedelta(minutes=15), "99.95", "100.15", "99.8", "100.05"),
        _bar(start + timedelta(minutes=30), "100.05", "100.2", "99.9", "100.1"),
        _bar(start + timedelta(minutes=45), "100.1", "100.2", "99.7", "99.8"),
    )
    policy = mod.Policy(
        target_r=Decimal("2.5"),
        soft_close_loss_r=None,
        soft_close_until_mfe_r=None,
        deadline_bars=4,
        deadline_min_mfe_r=Decimal("0.25"),
        trail_name="OFF",
        trail_steps=(),
    )
    result = mod._manage_trade(
        signal,
        bars=bars,
        opened=tuple(bar.opened_at for bar in bars),
        policy=policy,
    )
    assert result.exit_reason == "no-progress-deadline"
    assert result.r_multiple == Decimal("-0.2")


def test_goal_requires_fixed_density_pf_and_dd() -> None:
    passing = {
        "primary": {
            "sample": 657,
            "profit_factor": "1.60",
            "max_drawdown_r": "5.8",
        },
        "secondary": {
            "sample": 657,
            "profit_factor": "1.35",
            "max_drawdown_r": "7.5",
        },
    }
    assert mod._passes_goal(passing)
    failing_density = {
        **passing,
        "primary": {**passing["primary"], "sample": 656},
    }
    assert not mod._passes_goal(failing_density)
