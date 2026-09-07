"""Lane-2 adversarial witnesses for VT-01 (NY Precision Core) and VT-08 (CRT 4H AMD).

Deterministic-semantics coverage: positive/negative/abstain cases, closed-candle
(no partial/future leakage) boundaries, session boundaries, and neighboring
false positives. Self-contained: no relative imports; local candle helpers only.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.market_observation import MarketTimeframeCode
from qore.infrastructure.traders.contracts import (
    DemoTradingAbstainReason,
    DemoTradingDecision,
    DemoTradingError,
    DemoTradingEvidenceRef,
    DemoTradingOutput,
    DemoTradingSetupSide,
)
from qore.infrastructure.traders.evaluators import (
    DemoTradingInput,
    Vt01NyPrecisionCore,
    Vt08Crt4hAmd,
)
from qore.infrastructure.traders.primitives import ClosedCandle, timeframe_seconds
from qore.kernel.result import Failure, Result, Success

_BASE = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)  # 07:00 ET (EST)


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
    s = timeframe_seconds(code)
    return tuple(
        _candle(code, start + timedelta(seconds=i * s), o, h, lo, c)
        for i, (o, h, lo, c) in enumerate(bars)
    )


def _m5(
    start: datetime, bars: tuple[tuple[str, str, str, str], ...]
) -> tuple[ClosedCandle, ...]:
    return _seq(MarketTimeframeCode.M5, start, bars)


def _h4(
    start: datetime, bars: tuple[tuple[str, str, str, str], ...]
) -> tuple[ClosedCandle, ...]:
    return _seq(MarketTimeframeCode.H4, start, bars)


def _inp(
    as_of: datetime,
    exec_c: tuple[ClosedCandle, ...],
    ctx: tuple[ClosedCandle, ...] = (),
) -> DemoTradingInput:
    return DemoTradingInput(
        as_of=as_of,
        evidence_refs=(DemoTradingEvidenceRef("qore:demo:ev:1"),),
        execution_candles=exec_c,
        context_candles=ctx,
    )


# 6-candle M5 sweep-then-FVG LONG pattern: swing LOW at index 2 (1.10), bullish
# FVG at (2,3,4) (upper 1.13 / lower 1.12), false downside break at index 5.
_LONG_BARS = (
    ("1.16", "1.18", "1.14", "1.15"),
    ("1.15", "1.16", "1.12", "1.13"),
    ("1.11", "1.12", "1.10", "1.11"),
    ("1.13", "1.14", "1.12", "1.13"),
    ("1.13", "1.15", "1.13", "1.14"),
    ("1.14", "1.14", "1.05", "1.12"),
)

# 6-candle M5 sweep-then-FVG SHORT pattern (mirror): swing HIGH at index 2 (1.20),
# bearish FVG at (2,3,4), false upside break at index 5.
_SHORT_BARS = (
    ("1.10", "1.12", "1.09", "1.11"),
    ("1.11", "1.14", "1.10", "1.13"),
    ("1.16", "1.20", "1.15", "1.19"),
    ("1.19", "1.19", "1.13", "1.14"),
    ("1.14", "1.14", "1.10", "1.11"),
    ("1.11", "1.25", "1.10", "1.16"),
)


def _evaluate_vt01(
    as_of: datetime, candles: tuple[ClosedCandle, ...]
) -> Result[DemoTradingOutput, DemoTradingError]:
    return Vt01NyPrecisionCore().evaluate(_inp(as_of, candles))


def test_vt01_positive_long_setup() -> None:
    candles = _m5(_BASE, _LONG_BARS)
    result = _evaluate_vt01(candles[-1].closed_at, candles)
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.SETUP
    assert out.side is DemoTradingSetupSide.LONG
    assert out.setup is not None
    assert out.setup.side is DemoTradingSetupSide.LONG
    # Entry at the bullish FVG midpoint, invalidation at the swept swing low, 2R.
    assert out.setup.entry_price == Decimal("1.125")
    assert out.setup.invalidation_price == Decimal("1.10")
    assert out.setup.take_profit_price == Decimal("1.175")


def test_vt01_abstain_no_sweep() -> None:
    # Same structure as the positive LONG, but the latest candle stays above the
    # swing low: no wick below 1.10, so no false break of any pivot.
    bars = _LONG_BARS[:-1] + (("1.13", "1.15", "1.11", "1.14"),)
    candles = _m5(_BASE, bars)
    result = _evaluate_vt01(candles[-1].closed_at, candles)
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.ABSTAIN
    assert out.side is None
    assert out.setup is None
    assert out.abstain_reason is DemoTradingAbstainReason.NO_SWEEP


def test_vt01_no_session_vs_positive_boundary() -> None:
    candles = _m5(_BASE, _LONG_BARS)
    # Same candle data: just before 07:00 ET (12:00 UTC) vs inside the session.
    before_session = datetime(2026, 1, 6, 11, 59, 59, tzinfo=UTC)
    result = _evaluate_vt01(before_session, candles)
    assert isinstance(result, Success)
    assert result.value.decision is DemoTradingDecision.ABSTAIN
    assert result.value.abstain_reason is DemoTradingAbstainReason.NO_SESSION

    result = _evaluate_vt01(candles[-1].closed_at, candles)
    assert isinstance(result, Success)
    assert result.value.decision is DemoTradingDecision.SETUP
    assert result.value.side is DemoTradingSetupSide.LONG


def test_vt01_valid_breakout_above_swing_high_is_not_a_setup() -> None:
    # A genuine (non-false) upside breakout: the entire latest candle sits above
    # the swing high (1.20) with its close still above the level. This must NOT
    # be mistaken for a false upside break / SHORT setup.
    bars = _SHORT_BARS[:-1] + (("1.22", "1.30", "1.21", "1.25"),)
    candles = _m5(_BASE, bars)
    result = _evaluate_vt01(candles[-1].closed_at, candles)
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.ABSTAIN
    assert out.setup is None
    assert out.abstain_reason is DemoTradingAbstainReason.NO_SWEEP


def test_vt01_valid_breakout_straddle_must_not_raise() -> None:
    # Genuine upside breakout above the swing high (1.20): close stays above the
    # level, but the candle's low dips below it. This is a valid breakout, not a
    # false break, so evaluate must return ABSTAIN rather than raise or emit a
    # reversed setup.
    bars = _SHORT_BARS[:-1] + (("1.18", "1.30", "1.15", "1.25"),)
    candles = _m5(_BASE, bars)
    result = _evaluate_vt01(candles[-1].closed_at, candles)
    assert isinstance(result, Success)
    assert result.value.decision is DemoTradingDecision.ABSTAIN
    assert result.value.abstain_reason is DemoTradingAbstainReason.NO_SWEEP


def test_vt01_partial_candle_rejected() -> None:
    candles = _m5(_BASE, _LONG_BARS)
    # as_of one second before the final candle closes: the false-break candle is
    # still forming and must not be admitted.
    as_of = candles[-1].closed_at - timedelta(seconds=1)
    result = _evaluate_vt01(as_of, candles)
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.ABSTAIN
    assert out.setup is None
    assert out.abstain_reason is DemoTradingAbstainReason.NO_SWEEP


# ---------------------------------------------------------------------------
# VT-08 CRT 4H AMD.
# ---------------------------------------------------------------------------

# 5 closed H4 candles: range (idx0-3) is high 1.25 / low 1.05; the latest candle
# sweeps the range LOW (low 0.95 < 1.05) and closes ABOVE the range HIGH (1.32),
# resolving into upside distribution (LONG bias).
_H4_LONG_DISTRIBUTION = (
    ("1.10", "1.20", "1.05", "1.15"),
    ("1.15", "1.22", "1.08", "1.18"),
    ("1.18", "1.24", "1.10", "1.20"),
    ("1.20", "1.25", "1.12", "1.22"),
    ("1.10", "1.35", "0.95", "1.32"),
)

# M5 bullish FVG: candle[2].low (1.12) > candle[0].high (1.10).
_M5_BULLISH_FVG = (
    ("1.06", "1.10", "1.05", "1.08"),
    ("1.08", "1.09", "1.06", "1.07"),
    ("1.12", "1.13", "1.12", "1.12"),
)

# M5 with a bearish FVG only (candle[2].high < candle[0].low), no bullish gap.
_M5_BEARISH_FVG = (
    ("1.10", "1.15", "1.08", "1.12"),
    ("1.12", "1.13", "1.05", "1.06"),
    ("1.06", "1.07", "1.00", "1.02"),
)


def _evaluate_vt08(
    as_of: datetime,
    execution: tuple[ClosedCandle, ...],
    context: tuple[ClosedCandle, ...],
) -> Result[DemoTradingOutput, DemoTradingError]:
    return Vt08Crt4hAmd().evaluate(_inp(as_of, execution, ctx=context))


def test_vt08_positive_long_distribution_setup() -> None:
    context = _h4(_BASE, _H4_LONG_DISTRIBUTION)
    execution = _m5(_BASE, _M5_BULLISH_FVG)
    result = _evaluate_vt08(context[-1].closed_at, execution, context)
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.SETUP
    assert out.side is DemoTradingSetupSide.LONG
    assert out.setup is not None
    assert out.setup.side is DemoTradingSetupSide.LONG
    # Entry at the M5 bullish FVG midpoint; invalidation at the manipulated
    # (swept) range low; take-profit at the opposite range high.
    assert out.setup.entry_price == Decimal("1.11")
    assert out.setup.invalidation_price == Decimal("1.05")
    assert out.setup.take_profit_price == Decimal("1.25")


def test_vt08_abstain_accumulation() -> None:
    # Latest H4 candle stays inside the range: no manipulation, no distribution.
    bars = _H4_LONG_DISTRIBUTION[:-1] + (("1.14", "1.20", "1.10", "1.18"),)
    context = _h4(_BASE, bars)
    execution = _m5(_BASE, _M5_BULLISH_FVG)
    result = _evaluate_vt08(context[-1].closed_at, execution, context)
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.ABSTAIN
    assert out.setup is None
    assert out.abstain_reason is DemoTradingAbstainReason.NO_STRUCTURE


def test_vt08_no_structure_insufficient_h4() -> None:
    # Fewer than range_length + 1 (= 5) closed H4 candles: no AMD context.
    context = _h4(_BASE, _H4_LONG_DISTRIBUTION[:4])
    result = _evaluate_vt08(context[-1].closed_at, (), context)
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.ABSTAIN
    assert out.setup is None
    assert out.abstain_reason is DemoTradingAbstainReason.NO_STRUCTURE


def test_vt08_no_fvg_when_bias_direction_has_no_gap() -> None:
    # Upside distribution (LONG bias) exists, but M5 has only a bearish FVG.
    context = _h4(_BASE, _H4_LONG_DISTRIBUTION)
    execution = _m5(_BASE, _M5_BEARISH_FVG)
    result = _evaluate_vt08(context[-1].closed_at, execution, context)
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.ABSTAIN
    assert out.setup is None
    assert out.abstain_reason is DemoTradingAbstainReason.NO_FVG


def test_vt08_closed_h4_future_leakage_excluded() -> None:
    context = _h4(_BASE, _H4_LONG_DISTRIBUTION)
    execution = _m5(_BASE, _M5_BULLISH_FVG)
    # as_of at the close of the 4th H4 candle: the 5th (distribution) candle has
    # opened but not yet closed, so it must be excluded from the AMD context.
    as_of = context[3].closed_at
    result = _evaluate_vt08(as_of, execution, context)
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.ABSTAIN
    assert out.setup is None
    assert out.abstain_reason is DemoTradingAbstainReason.NO_STRUCTURE

    # The same context with the final H4 candle actually closed resolves to a
    # LONG distribution setup, proving the future candle was the sole trigger.
    result = _evaluate_vt08(context[-1].closed_at, execution, context)
    assert isinstance(result, Success)
    assert result.value.decision is DemoTradingDecision.SETUP
    assert result.value.side is DemoTradingSetupSide.LONG


def test_vt01_valid_breakdown_straddle_low_pivot_must_abstain() -> None:
    # Mirror of the valid-upside-breakout case: a genuine downside breakdown of
    # the swing low (1.10) whose high wick straddles above the level. This is a
    # valid breakdown, not a false upside break, so VT-01 must abstain.
    bars = _LONG_BARS[:-1] + (("1.12", "1.14", "1.00", "1.05"),)
    candles = _m5(_BASE, bars)
    result = _evaluate_vt01(candles[-1].closed_at, candles)
    assert isinstance(result, Success)
    assert result.value.decision is DemoTradingDecision.ABSTAIN
    assert result.value.abstain_reason is DemoTradingAbstainReason.NO_SWEEP


def test_vt01_empty_execution_in_session_abstains() -> None:
    # No closed M5 evidence inside the session must abstain, never raise.
    result = _evaluate_vt01(_BASE, ())
    assert isinstance(result, Success)
    assert result.value.decision is DemoTradingDecision.ABSTAIN
    assert result.value.abstain_reason is DemoTradingAbstainReason.NO_SWEEP


def test_vt01_rejects_m15_execution_candles() -> None:
    candles = _seq(MarketTimeframeCode.M15, _BASE, (("1.10", "1.12", "1.09", "1.11"),))
    result = _evaluate_vt01(candles[-1].closed_at, candles)
    assert isinstance(result, Failure)


def test_vt08_empty_execution_with_distribution_abstains() -> None:
    context = _h4(_BASE, _H4_LONG_DISTRIBUTION)
    result = _evaluate_vt08(context[-1].closed_at, (), context)
    assert isinstance(result, Success)
    assert result.value.decision is DemoTradingDecision.ABSTAIN
    assert result.value.abstain_reason is DemoTradingAbstainReason.NO_FVG


def test_vt08_rejects_non_h4_context() -> None:
    context = _m5(_BASE, _M5_BULLISH_FVG)
    execution = _m5(_BASE, _M5_BULLISH_FVG)
    result = _evaluate_vt08(execution[-1].closed_at, execution, context)
    assert isinstance(result, Failure)


def test_vt08_rejects_non_m5_execution() -> None:
    context = _h4(_BASE, _H4_LONG_DISTRIBUTION)
    execution = _seq(
        MarketTimeframeCode.M15, _BASE, _M5_BULLISH_FVG
    )
    result = _evaluate_vt08(context[-1].closed_at, execution, context)
    assert isinstance(result, Failure)
