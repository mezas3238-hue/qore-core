from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab.capitalizer_v3_master_funnel_forensics_1y_v1 import (
    ARCHITECTURE,
    EXPECTED_D1_MAX3_TRADES,
    EXPECTED_V3_MAX3_TRADES,
    IDENTITY,
    MATRIX_IDENTITY,
    _distribution,
    _portfolio_max3,
)


def test_master_forensics_contract_is_diagnostic_only_identity() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_MASTER_FUNNEL_FORENSICS_1Y_V1"
    assert MATRIX_IDENTITY.startswith(
        "QORE_CAPITALIZER_NINE_MARKET_V3_MASTER"
    )
    assert ARCHITECTURE == "V3_FROZEN_DIAGNOSTIC_ONLY_POST_MSS_TO_FVG_FILL"
    assert EXPECTED_V3_MAX3_TRADES == 226
    assert EXPECTED_D1_MAX3_TRADES == 398


def test_distribution_uses_declared_non_overlapping_bins() -> None:
    rows = (
        {"latency": 0},
        {"latency": 5},
        {"latency": 6},
        {"latency": 15},
        {"latency": 16},
        {"latency": 31},
        {"latency": None},
    )
    actual = _distribution(
        rows,
        "latency",
        bins=(
            ("0_5", 5),
            ("6_15", 15),
            ("16_30", 30),
            ("31_plus", None),
        ),
    )
    assert actual == {
        "0_5": 2,
        "6_15": 2,
        "16_30": 1,
        "31_plus": 1,
    }


def test_portfolio_max3_is_global_per_session_and_day() -> None:
    base = datetime(2026, 9, 22, 13, tzinfo=UTC)
    rows = tuple(
        {
            "symbol": symbol,
            "session": "NEW_YORK",
            "operating_date": "2026-09-22",
            "fill_at": (base + timedelta(minutes=index)).isoformat(),
        }
        for index, symbol in enumerate(
            ("NAS100", "USDCAD", "XAUUSD", "NAS100")
        )
    )

    selected = _portfolio_max3(rows, entry_field="fill_at")

    assert len(selected) == 3
    assert [row["symbol"] for row in selected] == [
        "NAS100",
        "USDCAD",
        "XAUUSD",
    ]
