from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_atlas_m5_reader import CapitalizerM5Bar
from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_protected_swing_corrected_replay_v1 import (
    IDENTITY,
    MATRIX_IDENTITY,
    CapitalizerProtectedSwingCorrectionMarketReport,
    CapitalizerStopCorrectionTransition,
    _protected_swing_surrogate,
    build_matrix_from_reports,
)
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Metrics,
)


def _bar(
    minute: int,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
) -> CapitalizerM5Bar:
    opened = datetime(2026, 1, 5, 10, minute, tzinfo=UTC)
    return CapitalizerM5Bar(
        symbol="EURUSD",
        opened_at=opened,
        closed_at=opened.replace(minute=minute + 5),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=None,
        digits=5,
    )


def _metrics(*, pf: str, dd: str, streak: int) -> CapitalizerR0Metrics:
    return CapitalizerR0Metrics(
        trades=10,
        wins=6,
        losses=4,
        flats=0,
        total_gross_r="5",
        mean_gross_r="0.5",
        gross_profit_r="9",
        gross_loss_r="4",
        profit_factor=pf,
        max_drawdown_r=dd,
        max_losing_streak=streak,
        median_planned_reward_r="2",
        median_bars_held="3",
        stop_exits=4,
        target_exits=5,
        session_exits=1,
        ambiguous_stop_first_exits=0,
    )


def _report(
    symbol: str,
    session: CapitalizerSession,
) -> CapitalizerProtectedSwingCorrectionMarketReport:
    return CapitalizerProtectedSwingCorrectionMarketReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session.value,
        total_replay_trades=20,
        protected_swing_surrogate_matched_trades=10,
        protected_swing_surrogate_coverage="0.5",
        baseline_all_metrics=_metrics(pf="1.4", dd="20", streak=8),
        baseline_matched_metrics=_metrics(pf="1.3", dd="15", streak=7),
        corrected_matched_metrics=_metrics(pf="1.6", dd="10", streak=5),
        median_corrected_stop_width_vs_baseline="1.4",
        median_causal_series_bars="2",
        transitions=(
            CapitalizerStopCorrectionTransition(
                baseline_exit="STOP",
                corrected_exit="TARGET",
                trades=2,
            ),
        ),
    )


def test_bullish_surrogate_requires_close_through_opposing_series() -> None:
    bars = (
        _bar(0, open_="100", high="100.2", low="99.4", close="99.6"),
        _bar(5, open_="99.6", high="99.8", low="99.0", close="99.2"),
        _bar(10, open_="99.2", high="100.6", low="98.8", close="100.3"),
    )
    result = _protected_swing_surrogate(
        bars,
        confirmation_index=2,
        side=CapitalizerSide.LONG,
    )

    assert result == (Decimal("98.8"), 2)


def test_surrogate_rejects_missing_cisd_close() -> None:
    bars = (
        _bar(0, open_="100", high="100.2", low="99.4", close="99.6"),
        _bar(5, open_="99.6", high="99.8", low="99.0", close="99.2"),
        _bar(10, open_="99.2", high="99.9", low="98.8", close="99.8"),
    )
    result = _protected_swing_surrogate(
        bars,
        confirmation_index=2,
        side=CapitalizerSide.LONG,
    )

    assert result is None


def test_matrix_keeps_m1_and_promotion_fail_closed() -> None:
    reports = tuple(
        _report(symbol, session)
        for session in CapitalizerSession
        for symbol in allowed_markets(session)
    )
    matrix = build_matrix_from_reports(reports)

    assert matrix.identity == MATRIX_IDENTITY
    assert matrix.complete_nine_market_universe is True
    assert len(matrix.markets) == 9
    assert matrix.all_markets_pf_improved is True
    assert matrix.all_markets_dd_reduced is True
    assert matrix.all_markets_losing_streak_reduced is True
    assert matrix.m1_evidence_required is True
    assert matrix.m1_evidence_present is False
    assert matrix.source_faithful_replay_complete is False
    assert matrix.geometry_proxy_only is True
    assert matrix.rule_promotion_allowed is False
    assert matrix.economic_candidate is False
    assert matrix.trader_certified is False


def test_market_report_does_not_claim_source_faithful_m1_replay() -> None:
    report = _report("EURUSD", CapitalizerSession.LONDON)

    assert report.baseline_stop_probe == "SOURCE_M5_DIRECTIONAL_EXTREME"
    assert report.corrected_stop_probe == "M5_CAUSAL_CISD_PROTECTED_SWING_SURROGATE"
    assert report.source_default_stop_semantics == "PROTECTED_SWING_WICK_INVALIDATION"
    assert report.entry_changed is False
    assert report.target_changed is False
    assert report.arbitrary_numeric_buffer_added is False
    assert report.m1_evidence_present is False
    assert report.source_faithful_replay_complete is False
    assert report.rule_promotion_allowed is False
    assert report.trader_certified is False
