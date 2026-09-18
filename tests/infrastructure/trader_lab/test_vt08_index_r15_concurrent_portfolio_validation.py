from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_density_round4 as r4
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as r5
from qore.infrastructure.trader_lab import vt08_index_r10_contextual_risk as r10
from qore.infrastructure.trader_lab import vt08_index_r15_concurrent_portfolio_validation as mod
from qore.infrastructure.trader_lab import vt08_index_v6_ttrades_source_faithful as v6
from qore.infrastructure.traders.contracts import DemoTradingSetupSide


def _signal(
    symbol: str,
    at: datetime,
    *,
    side: DemoTradingSetupSide = DemoTradingSetupSide.LONG,
) -> v6.CandidateSignal:
    poi = v6.SourcePoi(
        v6.PoiKind.CISD,
        Decimal("100"),
        Decimal("100"),
        at - timedelta(minutes=15),
    )
    stop = Decimal("99") if side is DemoTradingSetupSide.LONG else Decimal("101")
    target = Decimal("102.5") if side is DemoTradingSetupSide.LONG else Decimal("97.5")
    return v6.CandidateSignal(
        symbol=symbol,
        side=side,
        model_kind=v6.H4ModelKind.SAME_C2,
        h4_opened_at=at - timedelta(hours=1),
        signal_at=at,
        entry=Decimal("100"),
        stop=stop,
        target=target,
        poi=poi,
        cisd_level=Decimal("100"),
        cisd_confirmed_at=at,
        protected_swing_extreme=stop,
    )


def _opportunity(symbol: str, at: datetime) -> r4.ExpandedOpportunity:
    signal = _signal(symbol, at)
    return r4.ExpandedOpportunity(
        signal=signal,
        source_poi_kind=v6.PoiKind.CISD.value,
        poi_touch_at=at - timedelta(minutes=15),
        rearm_index=0,
    )


def _outcome(
    opportunity: r4.ExpandedOpportunity,
    *,
    exit_at: datetime,
    r_multiple: str,
) -> r5.ManagedTrade:
    return r5.ManagedTrade(
        symbol=opportunity.signal.symbol,
        signal_at=opportunity.signal.signal_at,
        exited_at=exit_at,
        r_multiple=Decimal(r_multiple),
        exit_reason="fixture",
    )


def _strong_context() -> r10.Context:
    return r10.Context(
        previous_source_day_body_opposed=True,
        rearm=False,
        c2_expansion=False,
        short=False,
    )


def test_concurrent_assignment_preserves_all_three_markets() -> None:
    t0 = datetime(2020, 1, 2, 14, 0, tzinfo=UTC)
    nas = _opportunity("NAS100", t0)
    sp = _opportunity("SP500", t0)
    us = _opportunity("US30", t0 + timedelta(minutes=15))
    stream = (
        (nas, _outcome(nas, exit_at=t0 + timedelta(hours=1), r_multiple="-1")),
        (sp, _outcome(sp, exit_at=t0 + timedelta(minutes=45), r_multiple="2.5")),
        (us, _outcome(us, exit_at=t0 + timedelta(minutes=30), r_multiple="2.5")),
    )
    assigned, diagnostics = mod._assign_concurrent_weights(
        stream,
        contexts=(_strong_context(), _strong_context(), _strong_context()),
    )
    assert len(assigned) == 3
    assert diagnostics["assigned_trade_count"] == 3
    assert diagnostics["suppressed_trade_count"] == 0
    assert diagnostics["same_timestamp_signal_batches"] == 1
    assert diagnostics["same_timestamp_signal_trades"] == 2
    assert diagnostics["max_concurrent_open_positions"] == 3


def test_open_trade_future_result_cannot_degrade_later_signal() -> None:
    t0 = datetime(2020, 1, 2, 14, 0, tzinfo=UTC)
    nas = _opportunity("NAS100", t0)
    sp = _opportunity("SP500", t0 + timedelta(minutes=15))
    stream = (
        (
            nas,
            _outcome(
                nas,
                exit_at=t0 + timedelta(hours=2),
                r_multiple="-1",
            ),
        ),
        (
            sp,
            _outcome(
                sp,
                exit_at=t0 + timedelta(minutes=45),
                r_multiple="2.5",
            ),
        ),
    )
    assigned, diagnostics = mod._assign_concurrent_weights(
        stream,
        contexts=(_strong_context(), _strong_context()),
    )
    # NAS100 is still open when SP500 signals. Its eventual loss cannot be used.
    assert assigned[0].weight == Decimal("1")
    assert assigned[1].weight == Decimal("1")
    assert diagnostics["suppressed_trade_count"] == 0
    assert diagnostics["max_concurrent_open_positions"] == 2


def test_contract_caps_portfolio_drawdown_at_six_r() -> None:
    assert mod.MAX_PORTFOLIO_DD_R == Decimal("6")
    assert mod.MIN_EFFECTIVE_WEIGHT == Decimal("0.005")
