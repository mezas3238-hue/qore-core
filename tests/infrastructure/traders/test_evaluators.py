"""Deterministic methodology evaluator tests: positive, negative, abstain, replay."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.market_observation import MarketTimeframeCode
from qore.infrastructure.traders.contracts import (
    DemoTradingDecision,
    DemoTradingEvidenceRef,
    DemoTradingSetupSide,
)
from qore.infrastructure.traders.evaluators import (
    DemoTradingInput,
    Vt01NyPrecisionCore,
    Vt08Crt4hAmd,
    Vt09TurtleSoup,
    Vt17QtScalper,
    Vt31SilverBullet,
    cohort_evaluators,
)
from qore.infrastructure.traders.primitives import ClosedCandle, timeframe_seconds
from qore.kernel.result import Success

_BASE = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)


def _candle(
    code: MarketTimeframeCode,
    opened_at: datetime,
    o: str,
    h: str,
    lo: str,
    c: str,
) -> ClosedCandle:
    return ClosedCandle(
        timeframe=code,
        opened_at=opened_at,
        closed_at=opened_at + timedelta(seconds=timeframe_seconds(code)),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(lo),
        close=Decimal(c),
    )


def _seq(
    code: MarketTimeframeCode,
    start: datetime,
    bars: tuple[tuple[str, str, str, str], ...],
) -> tuple[ClosedCandle, ...]:
    seconds = timeframe_seconds(code)
    return tuple(
        _candle(code, start + timedelta(seconds=i * seconds), o, h, lo, c)
        for i, (o, h, lo, c) in enumerate(bars)
    )


def _m5(
    start: datetime, bars: tuple[tuple[str, str, str, str], ...]
) -> tuple[ClosedCandle, ...]:
    return _seq(MarketTimeframeCode.M5, start, bars)


def _m15(
    start: datetime, bars: tuple[tuple[str, str, str, str], ...]
) -> tuple[ClosedCandle, ...]:
    return _seq(MarketTimeframeCode.M15, start, bars)


def _h4(
    start: datetime, bars: tuple[tuple[str, str, str, str], ...]
) -> tuple[ClosedCandle, ...]:
    return _seq(MarketTimeframeCode.H4, start, bars)


def _refs(*values: str) -> tuple[DemoTradingEvidenceRef, ...]:
    return tuple(DemoTradingEvidenceRef(value) for value in values)


# A 6-candle M5 sweep-then-FVG short pattern: swing high at index 2, bearish FVG
# at (2,3,4), false upside break at index 5.
_SWEEP_FVG_SHORT = (
    ("1.10", "1.12", "1.09", "1.11"),
    ("1.11", "1.14", "1.10", "1.13"),
    ("1.16", "1.20", "1.15", "1.19"),
    ("1.19", "1.19", "1.13", "1.14"),
    ("1.14", "1.14", "1.10", "1.11"),
    ("1.11", "1.25", "1.10", "1.16"),
)


def _input(
    *,
    as_of: datetime,
    execution_candles: tuple[ClosedCandle, ...],
    context_candles: tuple[ClosedCandle, ...] = (),
    refs: tuple[str, ...] = ("qore:demo:ev:1",),
) -> DemoTradingInput:
    return DemoTradingInput(
        as_of=as_of,
        evidence_refs=_refs(*refs),
        execution_candles=execution_candles,
        context_candles=context_candles,
    )


def test_cohort_has_exactly_five_evaluators() -> None:
    evaluators = cohort_evaluators()
    assert len(evaluators) == 5
    assert {type(item).__name__ for item in evaluators} == {
        "Vt01NyPrecisionCore",
        "Vt08Crt4hAmd",
        "Vt09TurtleSoup",
        "Vt17QtScalper",
        "Vt31SilverBullet",
    }


def test_vt01_positive_short_setup() -> None:
    candles = _m5(_BASE, _SWEEP_FVG_SHORT)
    as_of = candles[-1].closed_at
    result = Vt01NyPrecisionCore().evaluate(_input(as_of=as_of, execution_candles=candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.SETUP
    assert out.side is DemoTradingSetupSide.SHORT
    assert out.setup is not None


def test_vt01_no_session_abstain() -> None:
    candles = _m5(_BASE, _SWEEP_FVG_SHORT)
    # 04:00 ET (09:00 UTC) is outside the NY AM session.
    as_of = datetime(2026, 1, 6, 9, 0, tzinfo=UTC)
    result = Vt01NyPrecisionCore().evaluate(_input(as_of=as_of, execution_candles=candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.ABSTAIN
    assert out.abstain_reason is not None
    assert out.abstain_reason.value == "no-session"


def test_vt01_partial_candle_rejected() -> None:
    candles = _m5(_BASE, _SWEEP_FVG_SHORT)
    # as_of before the final candle closes: the false-break candle is not admissible.
    as_of = candles[-1].closed_at - timedelta(seconds=1)
    result = Vt01NyPrecisionCore().evaluate(_input(as_of=as_of, execution_candles=candles))
    assert isinstance(result, Success)
    assert result.value.decision is DemoTradingDecision.ABSTAIN


def test_vt08_positive_amd_distribution_setup() -> None:
    h4_bars = (
        ("1.00", "1.20", "0.90", "1.10"),
        ("1.10", "1.25", "1.00", "1.20"),
        ("1.20", "1.30", "1.10", "1.25"),
        ("1.25", "1.28", "1.15", "1.20"),
        ("1.20", "1.40", "0.85", "0.88"),
    )
    context = _h4(_BASE, h4_bars)
    m5_bars = (
        ("1.10", "1.15", "1.08", "1.12"),
        ("1.12", "1.13", "1.05", "1.06"),
        ("1.06", "1.07", "1.00", "1.02"),
    )
    execution = _m5(_BASE, m5_bars)
    as_of = context[-1].closed_at
    result = Vt08Crt4hAmd().evaluate(
        _input(as_of=as_of, execution_candles=execution, context_candles=context)
    )
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.SETUP
    assert out.side is DemoTradingSetupSide.SHORT


def test_vt08_no_structure_abstain() -> None:
    context = _h4(
        _BASE,
        (
            ("1.00", "1.20", "0.90", "1.10"),
            ("1.10", "1.25", "1.00", "1.20"),
            ("1.20", "1.30", "1.10", "1.25"),
            ("1.25", "1.28", "1.15", "1.20"),
            ("1.20", "1.29", "1.15", "1.25"),
        ),
    )
    m5_bars = (
        ("1.10", "1.15", "1.08", "1.12"),
        ("1.12", "1.13", "1.05", "1.06"),
        ("1.06", "1.07", "1.00", "1.02"),
    )
    execution = _m5(_BASE, m5_bars)
    result = Vt08Crt4hAmd().evaluate(
        _input(
            as_of=context[-1].closed_at,
            execution_candles=execution,
            context_candles=context,
        )
    )
    assert isinstance(result, Success)
    assert result.value.decision is DemoTradingDecision.ABSTAIN


def test_vt09_turtle_soup_positive() -> None:
    bars = (
        ("1.00", "1.05", "0.99", "1.04"),
        ("1.04", "1.10", "1.03", "1.09"),
        ("1.09", "1.20", "1.08", "1.18"),
        ("1.18", "1.19", "1.12", "1.14"),
        ("1.14", "1.15", "1.10", "1.12"),
        ("1.12", "1.25", "1.11", "1.16"),
    )
    candles = _m15(_BASE, bars)
    as_of = candles[-1].closed_at
    result = Vt09TurtleSoup().evaluate(_input(as_of=as_of, execution_candles=candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.SETUP
    assert out.side is DemoTradingSetupSide.SHORT


def test_vt09_no_false_break_abstain() -> None:
    bars = (
        ("1.00", "1.05", "0.99", "1.04"),
        ("1.04", "1.10", "1.03", "1.09"),
        ("1.09", "1.20", "1.08", "1.18"),
        ("1.18", "1.19", "1.12", "1.14"),
        ("1.14", "1.15", "1.10", "1.12"),
        ("1.12", "1.16", "1.11", "1.15"),
    )
    candles = _m15(_BASE, bars)
    as_of = candles[-1].closed_at
    result = Vt09TurtleSoup().evaluate(_input(as_of=as_of, execution_candles=candles))
    assert isinstance(result, Success)
    assert result.value.decision is DemoTradingDecision.ABSTAIN


def test_vt17_qt_scalper_cycle_sweep() -> None:
    # as_of = 12:30 UTC (07:30 ET). Cycle 8 spans 12:00-13:30 UTC.
    as_of = datetime(2026, 1, 6, 12, 30, tzinfo=UTC)
    cycle_open = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)
    bars = (
        ("1.00", "1.10", "0.99", "1.05"),
        ("1.05", "1.20", "1.04", "1.18"),
        ("1.18", "1.25", "1.14", "1.16"),
    )
    candles = _m5(cycle_open, bars)
    result = Vt17QtScalper().evaluate(_input(as_of=as_of, execution_candles=candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.SETUP
    assert out.side is DemoTradingSetupSide.SHORT


def test_vt17_no_session_abstain() -> None:
    as_of = datetime(2026, 1, 6, 18, 0, tzinfo=UTC)  # 13:00 ET, outside NY AM
    candles = _m5(datetime(2026, 1, 6, 17, 0, tzinfo=UTC), (
        ("1.00", "1.10", "0.99", "1.05"),
        ("1.05", "1.20", "1.04", "1.18"),
    ))
    result = Vt17QtScalper().evaluate(_input(as_of=as_of, execution_candles=candles))
    assert isinstance(result, Success)
    assert result.value.decision is DemoTradingDecision.ABSTAIN


def test_vt31_silver_bullet_positive() -> None:
    # 10:00 ET = 15:00 UTC.
    start = datetime(2026, 1, 6, 15, 0, tzinfo=UTC)
    candles = _m5(start, _SWEEP_FVG_SHORT)
    as_of = candles[-1].closed_at
    result = Vt31SilverBullet().evaluate(_input(as_of=as_of, execution_candles=candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.SETUP
    assert out.side is DemoTradingSetupSide.SHORT


def test_vt31_window_closed_abstain() -> None:
    start = datetime(2026, 1, 6, 11, 30, tzinfo=UTC)  # 06:30 ET, no window
    candles = _m5(start, _SWEEP_FVG_SHORT)
    as_of = candles[-1].closed_at
    result = Vt31SilverBullet().evaluate(_input(as_of=as_of, execution_candles=candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.ABSTAIN
    assert out.abstain_reason is not None
    assert out.abstain_reason.value == "window-closed"


def test_replay_produces_identical_output() -> None:
    candles = _m5(_BASE, _SWEEP_FVG_SHORT)
    as_of = candles[-1].closed_at
    first = Vt01NyPrecisionCore().evaluate(_input(as_of=as_of, execution_candles=candles))
    second = Vt01NyPrecisionCore().evaluate(_input(as_of=as_of, execution_candles=candles))
    assert isinstance(first, Success) and isinstance(second, Success)
    assert first.value.output_fingerprint == second.value.output_fingerprint
    assert first.value.logical_values() == second.value.logical_values()


def test_config_change_alters_output_identity() -> None:
    candles = _m5(_BASE, _SWEEP_FVG_SHORT)
    as_of = candles[-1].closed_at
    default = Vt01NyPrecisionCore().evaluate(_input(as_of=as_of, execution_candles=candles))
    changed = Vt01NyPrecisionCore(sweep_strength=3).evaluate(
        _input(as_of=as_of, execution_candles=candles)
    )
    assert isinstance(default, Success) and isinstance(changed, Success)
    assert default.value.config_fingerprint != changed.value.config_fingerprint
    assert default.value.output_fingerprint != changed.value.output_fingerprint


def test_config_fingerprint_is_stable_for_same_config() -> None:
    assert Vt01NyPrecisionCore().config_fingerprint() == Vt01NyPrecisionCore().config_fingerprint()
    assert Vt01NyPrecisionCore().config_fingerprint() != Vt01NyPrecisionCore(
        sweep_strength=3
    ).config_fingerprint()
