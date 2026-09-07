"""L3 adversarial tests: VT-09 Turtle Soup (M15) and VT-17 QT Scalper (M5).

Self-contained deterministic-witness tests for the false-break reversal
methodologies and the epoch-aligned 90-minute cycle semantics. No relative
imports; all helpers are local.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.market_observation import MarketTimeframeCode
from qore.infrastructure.traders.contracts import (
    DemoTradingAbstainReason,
    DemoTradingDecision,
    DemoTradingEvidenceRef,
    DemoTradingSetupSide,
)
from qore.infrastructure.traders.evaluators import (
    DemoTradingInput,
    Vt09TurtleSoup,
    Vt17QtScalper,
)
from qore.infrastructure.traders.primitives import ClosedCandle, timeframe_seconds
from qore.infrastructure.traders.windows import (
    NY_AM_SESSION,
    cycle_is_closed,
    is_in_window,
    ninety_minute_cycle,
)
from qore.kernel.result import Failure, Success

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
# 12:00 UTC == 07:00 ET (EST, Jan 6 2026).
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


def _inp(as_of: datetime, exec_c: tuple[ClosedCandle, ...]) -> DemoTradingInput:
    return DemoTradingInput(
        as_of=as_of,
        evidence_refs=(DemoTradingEvidenceRef("qore:demo:ev:1"),),
        execution_candles=exec_c,
    )


# ---------------------------------------------------------------------------
# VT-09 (M15) witnesses.
# ---------------------------------------------------------------------------

# Swing LOW at index 2 (low 1.00); latest candle false-breaks it downward
# (low 0.98 < 1.00, close 1.06 > 1.00) -> LONG turtle-soup.
_VT09_LONG_BARS: tuple[tuple[str, str, str, str], ...] = (
    ("1.10", "1.12", "1.05", "1.08"),
    ("1.08", "1.11", "1.06", "1.09"),
    ("1.09", "1.13", "1.00", "1.12"),
    ("1.12", "1.14", "1.08", "1.10"),
    ("1.10", "1.15", "1.07", "1.13"),
    ("1.13", "1.14", "0.98", "1.06"),
)

# Swing HIGH at index 2 (high 1.20, no LOW pivot); latest candle false-breaks it
# upward (high 1.25 > 1.20, close 1.16 < 1.20) -> SHORT turtle-soup.
_VT09_SHORT_BARS: tuple[tuple[str, str, str, str], ...] = (
    ("1.00", "1.05", "0.98", "1.04"),
    ("1.04", "1.08", "1.02", "1.06"),
    ("1.06", "1.20", "1.05", "1.18"),
    ("1.18", "1.19", "1.12", "1.14"),
    ("1.14", "1.16", "1.10", "1.12"),
    ("1.12", "1.25", "1.10", "1.16"),
)

# Same prior structure, but the latest candle makes a VALID upside breakout
# (close 1.28 beyond the swing high 1.20) -> must NOT produce a reversal.
_VT09_VALID_BREAKOUT_BARS: tuple[tuple[str, str, str, str], ...] = (
    ("1.00", "1.05", "0.98", "1.04"),
    ("1.04", "1.08", "1.02", "1.06"),
    ("1.06", "1.20", "1.05", "1.18"),
    ("1.18", "1.19", "1.12", "1.14"),
    ("1.14", "1.16", "1.10", "1.12"),
    ("1.21", "1.30", "1.20", "1.28"),
)

# Only 5 candles: below the 2*swing_strength+2 == 6 minimum.
_VT09_FIVE_BARS: tuple[tuple[str, str, str, str], ...] = (
    ("1.00", "1.05", "0.98", "1.04"),
    ("1.04", "1.08", "1.02", "1.06"),
    ("1.06", "1.20", "1.05", "1.18"),
    ("1.18", "1.19", "1.12", "1.14"),
    ("1.14", "1.16", "1.10", "1.12"),
)


def test_vt09_long_false_downside_break_of_swing_low() -> None:
    candles = _m15(_BASE, _VT09_LONG_BARS)
    result = Vt09TurtleSoup().evaluate(_inp(candles[-1].closed_at, candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.SETUP
    assert out.side is DemoTradingSetupSide.LONG
    assert out.setup is not None
    assert out.setup.side is DemoTradingSetupSide.LONG
    assert out.setup.entry_price == Decimal("1.06")
    assert out.setup.invalidation_price == Decimal("1.00")
    assert out.setup.take_profit_price == Decimal("1.18")
    assert out.setup.entry_reason == "turtle-soup-false-break-low"
    assert out.abstain_reason is None


def test_vt09_short_false_upside_break_of_swing_high() -> None:
    candles = _m15(_BASE, _VT09_SHORT_BARS)
    result = Vt09TurtleSoup().evaluate(_inp(candles[-1].closed_at, candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.SETUP
    assert out.side is DemoTradingSetupSide.SHORT
    assert out.setup is not None
    assert out.setup.side is DemoTradingSetupSide.SHORT
    assert out.setup.entry_price == Decimal("1.16")
    assert out.setup.invalidation_price == Decimal("1.20")
    assert out.setup.take_profit_price == Decimal("1.08")
    assert out.setup.entry_reason == "turtle-soup-false-break-high"
    assert out.abstain_reason is None


def test_vt09_valid_breakout_does_not_reverse() -> None:
    candles = _m15(_BASE, _VT09_VALID_BREAKOUT_BARS)
    result = Vt09TurtleSoup().evaluate(_inp(candles[-1].closed_at, candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.ABSTAIN
    assert out.abstain_reason is DemoTradingAbstainReason.NO_FALSE_BREAK
    assert out.side is None
    assert out.setup is None


def test_vt09_insufficient_evidence_abstain() -> None:
    candles = _m15(_BASE, _VT09_FIVE_BARS)
    result = Vt09TurtleSoup().evaluate(_inp(candles[-1].closed_at, candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.ABSTAIN
    assert out.abstain_reason is DemoTradingAbstainReason.INSUFFICIENT_EVIDENCE


def test_vt09_replay_deterministic() -> None:
    candles = _m15(_BASE, _VT09_LONG_BARS)
    as_of = candles[-1].closed_at
    first = Vt09TurtleSoup().evaluate(_inp(as_of, candles))
    second = Vt09TurtleSoup().evaluate(_inp(as_of, candles))
    assert isinstance(first, Success) and isinstance(second, Success)
    assert first.value.output_fingerprint == second.value.output_fingerprint
    assert first.value.logical_values() == second.value.logical_values()


def test_vt09_reports_m15_path() -> None:
    evaluator = Vt09TurtleSoup()
    assert evaluator.timeframe == "M15"
    assert evaluator.trader_code == "vt-09"
    candles = _m15(_BASE, _VT09_LONG_BARS)
    result = evaluator.evaluate(_inp(candles[-1].closed_at, candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.timeframe == "M15"
    assert out.methodology_id.value == "turtle-soup"


# ---------------------------------------------------------------------------
# VT-17 (M5) witnesses.
# ---------------------------------------------------------------------------

# Cycle high 1.20 / low 0.99 over the first two candles; the third false-breaks
# the high upward (high 1.25 > 1.20, close 1.16 < 1.20) -> SHORT.
_VT17_SHORT_BARS: tuple[tuple[str, str, str, str], ...] = (
    ("1.00", "1.10", "0.99", "1.05"),
    ("1.05", "1.20", "1.04", "1.18"),
    ("1.18", "1.25", "1.14", "1.16"),
)

# Cycle high 1.12 / low 0.99 over the first two candles; the third false-breaks
# the low downward (low 0.97 < 0.99, close 1.04 > 0.99) -> LONG.
_VT17_LONG_BARS: tuple[tuple[str, str, str, str], ...] = (
    ("1.00", "1.10", "0.99", "1.08"),
    ("1.08", "1.12", "1.05", "1.10"),
    ("1.10", "1.11", "0.97", "1.04"),
)

# Only two closed cycle candles: below the 3-candle minimum -> NO_CYCLE.
_VT17_TWO_BARS: tuple[tuple[str, str, str, str], ...] = (
    ("1.00", "1.10", "0.99", "1.05"),
    ("1.05", "1.20", "1.04", "1.18"),
)


def test_vt17_short_false_upside_break_of_cycle_high() -> None:
    as_of = datetime(2026, 1, 6, 12, 30, tzinfo=UTC)
    cycle = ninety_minute_cycle(as_of)
    candles = _m5(cycle.opened_at, _VT17_SHORT_BARS)
    result = Vt17QtScalper().evaluate(_inp(as_of, candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.SETUP
    assert out.side is DemoTradingSetupSide.SHORT
    assert out.setup is not None
    assert out.setup.entry_price == Decimal("1.16")
    assert out.setup.invalidation_price == Decimal("1.20")
    assert out.setup.take_profit_price == Decimal("1.08")
    assert out.setup.entry_reason == f"qt-scalper-cycle-{cycle.index}-high-sweep"
    assert out.abstain_reason is None


def test_vt17_long_false_downside_break_of_cycle_low() -> None:
    as_of = datetime(2026, 1, 6, 12, 30, tzinfo=UTC)
    cycle = ninety_minute_cycle(as_of)
    candles = _m5(cycle.opened_at, _VT17_LONG_BARS)
    result = Vt17QtScalper().evaluate(_inp(as_of, candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.SETUP
    assert out.side is DemoTradingSetupSide.LONG
    assert out.setup is not None
    assert out.setup.entry_price == Decimal("1.04")
    assert out.setup.invalidation_price == Decimal("0.99")
    assert out.setup.take_profit_price == Decimal("1.14")
    assert out.setup.entry_reason == f"qt-scalper-cycle-{cycle.index}-low-sweep"
    assert out.abstain_reason is None


def test_vt17_no_session_abstain() -> None:
    # 18:00 UTC == 13:00 ET, outside NY_AM_SESSION (07:00-11:00 ET).
    as_of = datetime(2026, 1, 6, 18, 0, tzinfo=UTC)
    candles = _m5(datetime(2026, 1, 6, 17, 0, tzinfo=UTC), _VT17_SHORT_BARS)
    result = Vt17QtScalper().evaluate(_inp(as_of, candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.ABSTAIN
    assert out.abstain_reason is DemoTradingAbstainReason.NO_SESSION


def test_vt17_no_cycle_abstain() -> None:
    as_of = datetime(2026, 1, 6, 12, 30, tzinfo=UTC)
    cycle = ninety_minute_cycle(as_of)
    candles = _m5(cycle.opened_at, _VT17_TWO_BARS)
    result = Vt17QtScalper().evaluate(_inp(as_of, candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.ABSTAIN
    assert out.abstain_reason is DemoTradingAbstainReason.NO_CYCLE


def test_vt17_cycle_epoch_aligned_boundaries() -> None:
    instant = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)
    cycle = ninety_minute_cycle(instant)
    assert cycle.opened_at == datetime(2026, 1, 6, 12, 0, tzinfo=UTC)
    assert cycle.closed_at == datetime(2026, 1, 6, 13, 30, tzinfo=UTC)
    assert (cycle.closed_at - cycle.opened_at).total_seconds() == 5400
    opened_seconds = int((cycle.opened_at - _EPOCH).total_seconds())
    closed_seconds = int((cycle.closed_at - _EPOCH).total_seconds())
    assert opened_seconds % 5400 == 0
    assert closed_seconds % 5400 == 0
    assert cycle.index == opened_seconds // 5400
    # Every instant in [opened_at, closed_at) resolves to the same cycle.
    assert ninety_minute_cycle(datetime(2026, 1, 6, 13, 29, 59, tzinfo=UTC)) == cycle


def test_vt17_cycle_half_open_boundary_assignment() -> None:
    cycle = ninety_minute_cycle(datetime(2026, 1, 6, 12, 0, tzinfo=UTC))
    # closed_at belongs to the NEXT cycle, not this one (half-open interval).
    nxt = ninety_minute_cycle(cycle.closed_at)
    assert nxt.opened_at == cycle.closed_at
    assert nxt.index == cycle.index + 1
    assert cycle_is_closed(cycle, as_of=cycle.closed_at) is True


def test_vt17_cycle_is_closed_boundary() -> None:
    cycle = ninety_minute_cycle(datetime(2026, 1, 6, 12, 30, tzinfo=UTC))
    assert cycle_is_closed(cycle, as_of=cycle.closed_at) is True
    assert cycle_is_closed(cycle, as_of=cycle.closed_at - timedelta(seconds=1)) is False


def test_vt17_replay_deterministic() -> None:
    as_of = datetime(2026, 1, 6, 12, 30, tzinfo=UTC)
    cycle = ninety_minute_cycle(as_of)
    candles = _m5(cycle.opened_at, _VT17_SHORT_BARS)
    first = Vt17QtScalper().evaluate(_inp(as_of, candles))
    second = Vt17QtScalper().evaluate(_inp(as_of, candles))
    assert isinstance(first, Success) and isinstance(second, Success)
    assert first.value.output_fingerprint == second.value.output_fingerprint
    assert first.value.logical_values() == second.value.logical_values()


def test_vt17_gap_bearing_execution_abstains_not_raises() -> None:
    # A non-contiguous M5 execution sequence is malformed closed-candle evidence;
    # VT-17 must abstain (NO_CYCLE) like the rest of the cohort instead of
    # leaking an uncaught primitive validation error.
    as_of = datetime(2026, 1, 6, 12, 30, tzinfo=UTC)
    cycle = ninety_minute_cycle(as_of)
    first = _candle(
        MarketTimeframeCode.M5, cycle.opened_at, "1.00", "1.10", "0.99", "1.05"
    )
    gapped = _candle(
        MarketTimeframeCode.M5,
        cycle.opened_at + timedelta(minutes=10),
        "1.05",
        "1.20",
        "1.04",
        "1.18",
    )
    result = Vt17QtScalper().evaluate(_inp(as_of, (first, gapped)))
    assert isinstance(result, Success)
    assert result.value.decision is DemoTradingDecision.ABSTAIN
    assert result.value.abstain_reason is DemoTradingAbstainReason.NO_CYCLE


def test_ny_am_session_half_open_boundaries() -> None:
    # 07:00 ET (inclusive) and 11:00 ET (exclusive) boundary semantics.
    open_et = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)
    close_et = datetime(2026, 1, 6, 16, 0, tzinfo=UTC)
    assert is_in_window(open_et, NY_AM_SESSION) is True
    assert is_in_window(close_et, NY_AM_SESSION) is False
    assert is_in_window(close_et - timedelta(seconds=1), NY_AM_SESSION) is True


def test_vt09_valid_upside_breakout_with_low_wick_abstains() -> None:
    # The bug witness: a valid upside breakout above the swing high (1.20) whose
    # low (1.10) dips below the level. This is a valid breakout, not a false
    # downside break, so VT-09 must abstain rather than emit a LONG reversal.
    bars = _VT09_VALID_BREAKOUT_BARS[:-1] + (("1.18", "1.30", "1.10", "1.28"),)
    candles = _m15(_BASE, bars)
    result = Vt09TurtleSoup().evaluate(_inp(candles[-1].closed_at, candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.ABSTAIN
    assert out.abstain_reason is DemoTradingAbstainReason.NO_FALSE_BREAK
    assert out.side is None
    assert out.setup is None


def test_vt09_valid_downside_breakdown_with_high_wick_abstains() -> None:
    # Symmetric bug witness: a valid downside breakdown of the swing low (1.00)
    # whose high (1.12) pokes above the level. Must abstain, not reverse.
    bars = _VT09_LONG_BARS[:-1] + (("1.02", "1.12", "0.90", "0.95"),)
    candles = _m15(_BASE, bars)
    result = Vt09TurtleSoup().evaluate(_inp(candles[-1].closed_at, candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.ABSTAIN
    assert out.abstain_reason is DemoTradingAbstainReason.NO_FALSE_BREAK


def test_vt09_rejects_m5_execution_candles() -> None:
    candles = _m5(_BASE, _VT09_LONG_BARS)
    result = Vt09TurtleSoup().evaluate(_inp(candles[-1].closed_at, candles))
    assert isinstance(result, Failure)


def test_vt17_valid_upside_break_of_cycle_high_with_low_wick_abstains() -> None:
    # A valid breakout of the cycle high (1.20) whose low (1.05) straddles below
    # it must abstain (NO_SWEEP), never emit a spurious "low-sweep" LONG.
    as_of = datetime(2026, 1, 6, 12, 30, tzinfo=UTC)
    cycle = ninety_minute_cycle(as_of)
    bars = _VT17_SHORT_BARS[:-1] + (("1.18", "1.30", "1.05", "1.28"),)
    candles = _m5(cycle.opened_at, bars)
    result = Vt17QtScalper().evaluate(_inp(as_of, candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.ABSTAIN
    assert out.abstain_reason is DemoTradingAbstainReason.NO_SWEEP
    assert out.side is None
    assert out.setup is None


def test_vt17_valid_downside_break_of_cycle_low_with_high_wick_abstains() -> None:
    # A valid breakdown of the cycle low (0.99) whose high (1.05) pokes above it
    # must abstain, never emit a spurious "high-sweep" SHORT.
    as_of = datetime(2026, 1, 6, 12, 30, tzinfo=UTC)
    cycle = ninety_minute_cycle(as_of)
    bars = _VT17_LONG_BARS[:-1] + (("1.00", "1.05", "0.90", "0.95"),)
    candles = _m5(cycle.opened_at, bars)
    result = Vt17QtScalper().evaluate(_inp(as_of, candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.ABSTAIN
    assert out.abstain_reason is DemoTradingAbstainReason.NO_SWEEP


def test_vt17_rejects_m15_execution_candles() -> None:
    as_of = datetime(2026, 1, 6, 12, 30, tzinfo=UTC)
    cycle = ninety_minute_cycle(as_of)
    candles = _m15(cycle.opened_at, _VT17_SHORT_BARS)
    result = Vt17QtScalper().evaluate(_inp(as_of, candles))
    assert isinstance(result, Failure)
