from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_m3_mss_bottleneck_forensics_2y_v1 import (
    IDENTITY,
    LOOKBACK_START,
    MATRIX_IDENTITY,
    WINDOW_END,
    WINDOW_START,
    _summarize,
)


def test_2y_bottleneck_window_and_identity_are_frozen() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_M3_MSS_BOTTLENECK_FORENSICS_2Y_V1"
    assert MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_M3_MSS_BOTTLENECK_FORENSICS_2Y_V1"
    )
    assert WINDOW_START == datetime(2024, 9, 17, tzinfo=UTC)
    assert WINDOW_END == datetime(2026, 9, 17, tzinfo=UTC)
    assert LOOKBACK_START == WINDOW_START - timedelta(days=21)


def test_empty_summary_keeps_research_governance() -> None:
    report = _summarize(
        symbol="EURUSD",
        session=CapitalizerSession.LONDON,
        diagnostics=(),
    )

    assert report["m5_closebacks"] == 0
    assert report["valid_m3_mss"] == 0
    assert report["rejected_m3_mss"] == 0
    assert report["thresholds_changed"] is False
    assert report["session_windows_changed"] is False
    assert report["outcome_aware_selection_used"] is False
    assert report["late_mss_used_for_admission"] is False
    assert report["diagnostic_window_role"] == "CONSUMED_DIAGNOSTIC_RESEARCH"
