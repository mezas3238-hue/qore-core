from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from qore.infrastructure.trader_lab import (
    vt08_index_r112_same_m15_ambiguity_census as r112,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)


def _bar(
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> Vt08IndexC2R1Bar:
    opened = datetime(2026, 1, 1, tzinfo=UTC)
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
    side: DemoTradingSetupSide,
    entry: str,
    stop: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        side=side,
        entry=Decimal(entry),
        stop=Decimal(stop),
    )


def test_r112_detects_long_same_m15_stop_and_target_ambiguity() -> None:
    signal = _signal(
        side=DemoTradingSetupSide.LONG,
        entry="100",
        stop="98",
    )
    # 2.5R target = 105; both 98 and 105 are inside the M15 range.
    bar = _bar(open_="100", high="106", low="97", close="101")
    assert r112._is_same_m15_ambiguous(
        signal=signal,
        exit_bar=bar,
    )


def test_r112_detects_short_same_m15_stop_and_target_ambiguity() -> None:
    signal = _signal(
        side=DemoTradingSetupSide.SHORT,
        entry="100",
        stop="102",
    )
    # 2.5R target = 95.
    bar = _bar(open_="100", high="103", low="94", close="99")
    assert r112._is_same_m15_ambiguous(
        signal=signal,
        exit_bar=bar,
    )


def test_r112_gap_exit_is_not_classified_as_intrabar_ambiguity() -> None:
    signal = _signal(
        side=DemoTradingSetupSide.LONG,
        entry="100",
        stop="98",
    )
    bar = _bar(open_="97", high="106", low="96", close="101")
    assert not r112._is_same_m15_ambiguous(
        signal=signal,
        exit_bar=bar,
    )


def test_r112_single_touch_is_not_ambiguous() -> None:
    signal = _signal(
        side=DemoTradingSetupSide.LONG,
        entry="100",
        stop="98",
    )
    bar = _bar(open_="100", high="104", low="97", close="101")
    assert not r112._is_same_m15_ambiguous(
        signal=signal,
        exit_bar=bar,
    )


def test_r112_source_and_surface_are_pinned() -> None:
    assert r112.TARGET_R == Decimal("2.5")
    assert r112.EXPECTED_STANDARD == {
        "5Y": 1756,
        "2Y": 746,
        "R66": 546,
    }
    assert r112.SOURCE_R111_RUN_ID == 35661275019
    assert r112.SOURCE_R111_ARTIFACT_ID == 10666554085
    assert r112.SOURCE_R111_ARTIFACT_DIGEST == (
        "sha256:f80a38fa197f005ec50f16d7f05ac640e19d86d9aad30c501c5ca45959850ed4"
    )
