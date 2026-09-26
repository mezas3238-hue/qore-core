from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab.capitalizer_v3_density_n1_n2_1y_v1 import (
    IDENTITY,
    MATRIX_IDENTITY,
    STOP_IDENTITY,
    TARGET_IDENTITY,
    _execution_deadline_for_mss,
)


def test_density_n1_n2_keeps_v3_economic_contract() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_DENSITY_N1_N2_1Y_V1"
    assert (
        MATRIX_IDENTITY
        == "QORE_CAPITALIZER_NINE_MARKET_V3_DENSITY_N1_N2_1Y_V1"
    )
    assert STOP_IDENTITY == "M3_BROKEN_SWING_PLUS_5_PIP_BUFFER"
    assert TARGET_IDENTITY == "FIXED_2R_OR_NEXT_H1_OPEN"


def test_n1_mss_keeps_original_v3_h1_deadline() -> None:
    h1_deadline = datetime(2026, 9, 22, 10, tzinfo=UTC)
    mss_deadline = h1_deadline + timedelta(hours=1)

    actual = _execution_deadline_for_mss(
        mss_confirmed_at=h1_deadline - timedelta(minutes=3),
        h1_deadline=h1_deadline,
        mss_deadline=mss_deadline,
    )

    assert actual == h1_deadline


def test_n2_mss_uses_only_the_extended_h1_deadline() -> None:
    h1_deadline = datetime(2026, 9, 22, 10, tzinfo=UTC)
    mss_deadline = h1_deadline + timedelta(hours=1)

    actual = _execution_deadline_for_mss(
        mss_confirmed_at=h1_deadline + timedelta(minutes=3),
        h1_deadline=h1_deadline,
        mss_deadline=mss_deadline,
    )

    assert actual == mss_deadline
