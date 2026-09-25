"""Causal source-context resolver for VT-08 Index V5 research.

This module deliberately does not use trade outcomes.  It classifies only
fully closed source-day candles available before ``signal_at`` and fails closed
when the source pattern is ambiguous.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar


class SourceClosureContext(StrEnum):
    BULLISH_CONTINUATION = "bullish_continuation"
    BEARISH_CONTINUATION = "bearish_continuation"
    BULLISH_REVERSAL = "bullish_reversal"
    BEARISH_REVERSAL = "bearish_reversal"
    INCONCLUSIVE = "inconclusive"


class SourceContextDecision(StrEnum):
    QUALIFY = "qualify"
    REJECT = "reject"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True, slots=True)
class SourceContextResolution:
    context: SourceClosureContext
    decision: SourceContextDecision
    reference_closed_at: str
    subject_closed_at: str


def classify_closed_source_day(
    reference: Vt08IndexC2R1Bar,
    subject: Vt08IndexC2R1Bar,
) -> SourceClosureContext:
    """Classify a closed source day against the preceding closed source day.

    Definitions are frozen by VT08-INDEX-V5-SOURCE-CONTEXT-PREREGISTRATION-001.
    Two-sided/outside bars and patterns satisfying no unique definition fail
    closed as INCONCLUSIVE.
    """
    swept_high = subject.high > reference.high
    swept_low = subject.low < reference.low
    if swept_high and swept_low:
        return SourceClosureContext.INCONCLUSIVE

    bullish_continuation = subject.close > reference.high
    bearish_continuation = subject.close < reference.low
    bullish_reversal = swept_low and subject.close >= reference.low
    bearish_reversal = swept_high and subject.close <= reference.high

    matches = [
        context
        for matched, context in (
            (bullish_continuation, SourceClosureContext.BULLISH_CONTINUATION),
            (bearish_continuation, SourceClosureContext.BEARISH_CONTINUATION),
            (bullish_reversal, SourceClosureContext.BULLISH_REVERSAL),
            (bearish_reversal, SourceClosureContext.BEARISH_REVERSAL),
        )
        if matched
    ]
    return matches[0] if len(matches) == 1 else SourceClosureContext.INCONCLUSIVE


def resolve_source_context(
    *,
    reference: Vt08IndexC2R1Bar,
    subject: Vt08IndexC2R1Bar,
    side: DemoTradingSetupSide,
) -> SourceContextResolution:
    """Map a causal closure context to trade-side qualification.

    A bullish source closure qualifies LONG and rejects SHORT; a bearish source
    closure qualifies SHORT and rejects LONG.  Ambiguous source structure never
    becomes a trade permission.
    """
    context = classify_closed_source_day(reference, subject)
    if context is SourceClosureContext.INCONCLUSIVE:
        decision = SourceContextDecision.INCONCLUSIVE
    else:
        bullish = context in {
            SourceClosureContext.BULLISH_CONTINUATION,
            SourceClosureContext.BULLISH_REVERSAL,
        }
        aligned = (bullish and side is DemoTradingSetupSide.LONG) or (
            not bullish and side is DemoTradingSetupSide.SHORT
        )
        decision = SourceContextDecision.QUALIFY if aligned else SourceContextDecision.REJECT
    return SourceContextResolution(
        context=context,
        decision=decision,
        reference_closed_at=reference.closed_at.isoformat(),
        subject_closed_at=subject.closed_at.isoformat(),
    )
