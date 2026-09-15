from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_index_v5_source_context import (
    SourceClosureContext,
    SourceContextDecision,
    classify_closed_source_day,
    resolve_source_context,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar


def _bar(
    open_: str,
    high: str,
    low: str,
    close: str,
    *,
    day: int = 1,
) -> Vt08IndexC2R1Bar:
    opened = datetime(2026, 1, day, tzinfo=UTC)
    return Vt08IndexC2R1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(days=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_classifies_four_preregistered_source_closures() -> None:
    ref = _bar("100", "110", "90", "102")
    bullish_continuation = classify_closed_source_day(
        ref, _bar("102", "115", "98", "112", day=2)
    )
    bearish_continuation = classify_closed_source_day(
        ref, _bar("102", "105", "85", "88", day=2)
    )
    bullish_reversal = classify_closed_source_day(
        ref, _bar("102", "108", "85", "96", day=2)
    )
    bearish_reversal = classify_closed_source_day(
        ref, _bar("102", "115", "95", "105", day=2)
    )
    assert bullish_continuation is SourceClosureContext.BULLISH_CONTINUATION
    assert bearish_continuation is SourceClosureContext.BEARISH_CONTINUATION
    assert bullish_reversal is SourceClosureContext.BULLISH_REVERSAL
    assert bearish_reversal is SourceClosureContext.BEARISH_REVERSAL


def test_two_sided_source_day_fails_closed() -> None:
    ref = _bar("100", "110", "90", "102")
    subject = _bar("102", "115", "85", "105", day=2)
    assert classify_closed_source_day(ref, subject) is SourceClosureContext.INCONCLUSIVE
    result = resolve_source_context(
        reference=ref,
        subject=subject,
        side=DemoTradingSetupSide.LONG,
    )
    assert result.decision is SourceContextDecision.INCONCLUSIVE


def test_context_direction_qualifies_only_matching_side() -> None:
    ref = _bar("100", "110", "90", "102")
    bullish = _bar("102", "115", "98", "112", day=2)
    long_result = resolve_source_context(
        reference=ref,
        subject=bullish,
        side=DemoTradingSetupSide.LONG,
    )
    short_result = resolve_source_context(
        reference=ref,
        subject=bullish,
        side=DemoTradingSetupSide.SHORT,
    )
    assert long_result.decision is SourceContextDecision.QUALIFY
    assert short_result.decision is SourceContextDecision.REJECT
    assert long_result.reference_closed_at == ref.closed_at.isoformat()
    assert long_result.subject_closed_at == bullish.closed_at.isoformat()
