from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_cibo_2y_density_round4 as r4,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r108_standard_source_retest_execution_replay as r108,
)
from qore.infrastructure.trader_lab import (
    vt08_index_v6_ttrades_source_faithful as v6,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)


def _bar(
    opened: datetime,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> Vt08IndexC2R1Bar:
    return Vt08IndexC2R1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=15),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def _signal(
    *,
    signal_at: datetime,
    entry: str = "102",
    stop: str = "98",
) -> v6.CandidateSignal:
    poi = v6.SourcePoi(
        kind=v6.PoiKind.CISD,
        low=Decimal("99"),
        high=Decimal("99"),
        observed_at=signal_at - timedelta(hours=4),
    )
    return v6.CandidateSignal(
        symbol="NAS100",
        side=DemoTradingSetupSide.LONG,
        model_kind=v6.H4ModelKind.SAME_C2,
        h4_opened_at=signal_at.replace(minute=0, second=0, microsecond=0),
        signal_at=signal_at,
        entry=Decimal(entry),
        stop=Decimal(stop),
        target=Decimal("112"),
        poi=poi,
        cisd_level=Decimal("100"),
        cisd_confirmed_at=signal_at - timedelta(minutes=15),
        protected_swing_extreme=Decimal(stop),
    )


def test_r108_retest_keeps_protected_swing_and_rebuilds_exact_2_5r_target() -> None:
    t0 = datetime(2026, 1, 1, 10, 30, tzinfo=UTC)
    original = _signal(signal_at=t0)
    rerouted = r108._build_retest_signal(
        original,
        retest_level=Decimal("100"),
        retest_window_opened_at=t0 + timedelta(minutes=15),
    )
    assert rerouted.entry == Decimal("100")
    assert rerouted.stop == original.stop == Decimal("98")
    assert rerouted.protected_swing_extreme == original.protected_swing_extreme
    assert rerouted.target == Decimal("105")
    assert rerouted.signal_at == t0 + timedelta(minutes=15)


def test_r108_same_retest_bar_cannot_receive_target_credit() -> None:
    t0 = datetime(2026, 1, 1, 10, 45, tzinfo=UTC)
    fill_bar = _bar(
        t0,
        open_="101",
        high="106",
        low="99.5",
        close="100",
    )
    next_bar = _bar(
        t0 + timedelta(minutes=15),
        open_="100",
        high="101",
        low="97",
        close="98",
    )
    signal = r108._build_retest_signal(
        _signal(signal_at=t0 - timedelta(minutes=15)),
        retest_level=Decimal("100"),
        retest_window_opened_at=t0,
    )
    outcome = r108._manage_retest(
        signal,
        fill_bar=fill_bar,
        bars=(fill_bar, next_bar),
        opened=(fill_bar.opened_at, next_bar.opened_at),
    )
    assert outcome.r_multiple == Decimal("-1")
    assert outcome.exit_reason == "stop"
    assert outcome.exited_at == next_bar.closed_at


def test_r108_retest_geometry_is_not_filtered_by_entry_improvement_sign() -> None:
    t0 = datetime(2026, 1, 1, 10, 30, tzinfo=UTC)
    original = _signal(signal_at=t0, entry="100", stop="98")
    rerouted = r108._build_retest_signal(
        original,
        retest_level=Decimal("101"),
        retest_window_opened_at=t0 + timedelta(minutes=15),
    )
    assert rerouted.entry == Decimal("101")
    assert rerouted.target == Decimal("108.5")


def test_r108_owner_anchor_and_governance_constants_are_frozen() -> None:
    assert tuple(r4.V7_ANCHORS) == (22, 2, 6, 10)
    assert r108.TARGET_R == Decimal("2.5")
    assert r108.EXPECTED_CANONICAL == {"5Y": 2448, "2Y": 1017, "R66": 773}
    assert r108.EXPECTED_STANDARD == {"5Y": 1756, "2Y": 746, "R66": 546}
    assert r108.EXPECTED_RETEST == {"5Y": 1049, "2Y": 452, "R66": 318}


def test_r108_source_r107_is_pinned() -> None:
    assert r108.SOURCE_R107_RUN_ID == 35557537194
    assert r108.SOURCE_R107_ARTIFACT_ID == 10620513767
    assert r108.SOURCE_R107_ARTIFACT_DIGEST == (
        "sha256:ed8e7195ff6641ac23bbd30cac68e6ee3a3ed59f5f6ed60c1a7f06626c6dbe51"
    )
