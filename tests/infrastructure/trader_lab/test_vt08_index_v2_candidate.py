from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_index_qore_ambiguity_lab_v1 import Signal
from qore.infrastructure.trader_lab.vt08_index_v2_candidate import (
    CANDIDATE_ID,
    DEVELOPMENT_SELECTION_ID,
    SELECTED_VARIANT,
    _gap_exit,
    _in_partition,
    _intrabar_exit,
    _model_hardened,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
    Vt08IndexC2R1ProtectedSwing,
)


def _bar(
    opened_at: datetime,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> Vt08IndexC2R1Bar:
    return Vt08IndexC2R1Bar(
        opened_at=opened_at,
        closed_at=opened_at + timedelta(minutes=15),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def _swing(side: DemoTradingSetupSide, price: str) -> Vt08IndexC2R1ProtectedSwing:
    return Vt08IndexC2R1ProtectedSwing(
        side,
        Decimal(price),
        Decimal("100"),
        datetime(2026, 1, 2, 9, 30, tzinfo=UTC),
        datetime(2026, 1, 2, 9, 0, tzinfo=UTC),
    )


def _signal(side: DemoTradingSetupSide, decision: datetime, price: str) -> Signal:
    return Signal(
        symbol="NAS100",
        decision_at=decision,
        anchor=decision.hour,
        side=side,
        protected_swing=_swing(side, price),
        closure_kind="c2",
    )


def _window(
    decision: datetime,
    *,
    first: Vt08IndexC2R1Bar,
    second: Vt08IndexC2R1Bar | None = None,
) -> dict[datetime, Vt08IndexC2R1Bar]:
    rows: dict[datetime, Vt08IndexC2R1Bar] = {decision: first}
    for index in range(1, 16):
        opened = decision + timedelta(minutes=15 * index)
        rows[opened] = (
            second
            if index == 1 and second is not None
            else _bar(opened, open_="100", high="100.2", low="99.8", close="100")
        )
    return rows


def test_candidate_identity_is_exactly_the_development_selection() -> None:
    assert CANDIDATE_ID == "VT08_INDEX_V2_QORE_CANDIDATE_001"
    assert DEVELOPMENT_SELECTION_ID == "V-32e621c9282c"
    assert SELECTED_VARIANT.variant_id == DEVELOPMENT_SELECTION_ID
    assert SELECTED_VARIANT.payload() == {
        "variant_id": "V-32e621c9282c",
        "closure": "c2-or-c3-body-close",
        "swing": "farthest-structural",
        "stop": "protected-swing-extreme",
        "target": "1.5r",
        "lifecycle": "next-h4-boundary",
        "daily": "unique-only",
    }


def test_long_gap_through_stop_exits_at_observed_open() -> None:
    opened = datetime(2026, 1, 2, 10, tzinfo=UTC)
    first = _bar(opened, open_="100", high="100.2", low="99.8", close="100")
    second_opened = opened + timedelta(minutes=15)
    second = _bar(
        second_opened,
        open_="98",
        high="98.5",
        low="97.5",
        close="98.2",
    )
    modeled = _model_hardened(
        _signal(DemoTradingSetupSide.LONG, opened, "99"),
        bars_by_open=_window(opened, first=first, second=second),
    )
    assert modeled is not None
    assert modeled.exit_reason == "stop-gap"
    assert modeled.exit_price == Decimal("98")
    assert modeled.r_multiple == Decimal("-2")


def test_short_gap_through_stop_exits_at_observed_open() -> None:
    opened = datetime(2026, 1, 2, 10, tzinfo=UTC)
    first = _bar(opened, open_="100", high="100.2", low="99.8", close="100")
    second_opened = opened + timedelta(minutes=15)
    second = _bar(
        second_opened,
        open_="102",
        high="102.5",
        low="101.5",
        close="101.8",
    )
    modeled = _model_hardened(
        _signal(DemoTradingSetupSide.SHORT, opened, "101"),
        bars_by_open=_window(opened, first=first, second=second),
    )
    assert modeled is not None
    assert modeled.exit_reason == "stop-gap"
    assert modeled.exit_price == Decimal("102")
    assert modeled.r_multiple == Decimal("-2")


def test_target_gap_is_conservatively_capped_at_target() -> None:
    opened = datetime(2026, 1, 2, 10, tzinfo=UTC)
    bar = _bar(opened, open_="103", high="104", low="102", close="103")
    assert _gap_exit(
        side=DemoTradingSetupSide.LONG,
        bar=bar,
        stop=Decimal("99"),
        target=Decimal("101.5"),
    ) == (Decimal("101.5"), "target-gap")


def test_same_bar_ordering_remains_stop_first() -> None:
    opened = datetime(2026, 1, 2, 10, tzinfo=UTC)
    bar = _bar(opened, open_="100", high="102", low="98", close="100")
    assert _intrabar_exit(
        bar=bar,
        stop=Decimal("99"),
        target=Decimal("101.5"),
    ) == (Decimal("99"), "stop")


def test_partition_is_new_york_date_bound_and_end_exclusive() -> None:
    inside = datetime(2024, 8, 12, 14, tzinfo=UTC)
    boundary = datetime(2024, 8, 13, 14, tzinfo=UTC)
    assert _in_partition(
        inside,
        start_date=date(2023, 9, 14),
        end_date_exclusive=date(2024, 8, 13),
    )
    assert not _in_partition(
        boundary,
        start_date=date(2023, 9, 14),
        end_date_exclusive=date(2024, 8, 13),
    )
