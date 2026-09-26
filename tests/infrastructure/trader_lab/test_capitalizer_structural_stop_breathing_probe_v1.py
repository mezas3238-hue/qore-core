from __future__ import annotations

from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_structural_stop_breathing_probe_v1 import (
    IDENTITY,
    MATRIX_IDENTITY,
    CapitalizerNineMarketStopBreathingMatrix,
    CapitalizerStopBreathingMarketReport,
    CapitalizerStopBreathingMetrics,
    build_matrix_from_reports,
)


def _metrics(mode: str, *, pf: str, dd: str, width: str) -> CapitalizerStopBreathingMetrics:
    return CapitalizerStopBreathingMetrics(
        mode=mode,
        trades=100,
        wins=55,
        losses=45,
        flats=0,
        total_gross_r="20",
        profit_factor=pf,
        max_drawdown_r=dd,
        max_losing_streak=5,
        stop_exits=45,
        target_exits=45,
        session_exits=10,
        same_m5_ambiguities=0,
        median_stop_width_vs_baseline=width,
        unchanged_due_to_history_gap=0,
    )


def _report(symbol: str, session: CapitalizerSession) -> CapitalizerStopBreathingMarketReport:
    return CapitalizerStopBreathingMarketReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session.value,
        modes=(
            _metrics("SOURCE_M5_EXTREME", pf="1.4", dd="20", width="1"),
            _metrics("TWO_CLOSED_M5_EXTREME", pf="1.5", dd="15", width="1.3"),
            _metrics("THREE_CLOSED_M5_EXTREME", pf="1.6", dd="10", width="1.5"),
        ),
    )


def test_nine_market_matrix_stays_diagnostic() -> None:
    reports = tuple(
        _report(symbol, session)
        for session in CapitalizerSession
        for symbol in allowed_markets(session)
    )
    matrix = build_matrix_from_reports(reports)

    assert isinstance(matrix, CapitalizerNineMarketStopBreathingMatrix)
    assert matrix.identity == MATRIX_IDENTITY
    assert matrix.complete_nine_market_universe is True
    assert matrix.modes_improving_pf_all_markets == (
        "TWO_CLOSED_M5_EXTREME",
        "THREE_CLOSED_M5_EXTREME",
    )
    assert matrix.modes_reducing_dd_all_markets == (
        "TWO_CLOSED_M5_EXTREME",
        "THREE_CLOSED_M5_EXTREME",
    )
    assert matrix.markets_reaching_owner_dd_ceiling == ()
    assert matrix.source_strategy_status == "WAIT_M1_EVIDENCE"
    assert matrix.rule_promotion_allowed is False
    assert matrix.stop_widening_authorized is False
    assert matrix.economic_candidate is False
    assert matrix.trader_certified is False


def test_market_report_does_not_replace_source_stop() -> None:
    report = _report("USDJPY", CapitalizerSession.ASIA)

    assert report.geometry_proxy_only is True
    assert report.diagnostic_only is True
    assert report.arbitrary_price_padding_used is False
    assert report.protected_swing_replaced is False
    assert report.m1_evidence_present is False
    assert report.rule_promotion_allowed is False
    assert report.stop_widening_authorized is False
    assert report.trader_certified is False
