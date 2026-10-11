"""TTrades M30→M3 authority gate: authored stop rule != verified setup.

Written July 30 2025 bullish M30→M3 example: stop BELOW BOTH M30 EQ
and breaker low. The full causal EQ-reference-swing and breaker-identity
selectors are NOT documented enough to certify any trading setup here.
A four-close M3 breaker-sequence *proxy* is deliberately never an
author-verified breaker or an executable stop.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.trader_lab.vt08_5m_a_m30m3_h1_liquidity_swing_asof_verifier_v1 import (
    ClosedExternalPivot,
    ExternalPivotKind,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

STOP_SOURCE = (
    "https://ttrades.com/timeframe-alignment-how-to-align-higher-and-"
    "lower-time-frames-for-precision-entries/"
)
BREAKER_SOURCE = "https://ttrades.com/trading-breaker-blocks-for-continuations/"
POI_PRIORITY_SOURCE = (
    "https://ttrades.com/the-only-points-of-interest-that-actually-matter-for-trading/"
)
POI_OB_SOURCE = "https://ttrades.com/using-equilibrium-in-continuations/"
EQ_SOURCE = "https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/"
PS_STOP_SOURCE = (
    "https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/"
)

# This ORDER is A-author written for continuations, but the exact
# spatial selector and relevance predicate remain D.  OB also appears
# as a supporting POI in a separate author article; don't omit it.
POI_AUTHOR_CONTINUATION_HIERARCHY = ("FVG", "SWING_HIGH_LOW", "CISD_RETEST")
POI_AUTHOR_ADDITIONAL_CONTEXT = ("ORDER_BLOCK", "PROTECTED_HIGH_LOW")


class AuthorCheckStatus(StrEnum):
    WRONG_FAMILY = "WRONG_FAMILY_FOR_SPECIFIC_BULLISH_EXAMPLE"
    WAIT_M30_CLOSE = "WAIT_M30_CLOSE"
    INVALID_SOURCE_CLOCK = "INVALID_SOURCE_CLOCK"
    REFERENCE_SWING_UNADJUDICATED = "REFERENCE_SWING_EQ_D"
    BREAKER_LOW_UNADJUDICATED = "BREAKER_LOW_D"
    BOTH_EQ_AND_BREAKER_UNADJUDICATED = "EQ_SWING_AND_BREAKER_D"


@dataclass(frozen=True, slots=True)
class CausalBreakerShape:
    """Four M3 CLOSED bars, QORE geometry only, never verified breaker low."""

    low_1: Decimal
    high_2: Decimal
    lower_low_3: Decimal
    higher_high_4: Decimal
    source_first_opened_at: datetime
    observed_at: datetime
    origin_id: str
    author_breaker_identity_verified: bool = False
    usable_as_trade_stop_level: bool = False


def observed_bullish_breaker_shapes(
    bars: tuple[Vt08B01Bar, ...],
    *,
    decision_at: datetime,
) -> tuple[CausalBreakerShape, ...]:
    """Low→high→lower low→higher high, 4 consecutive closed M3 bars.

    Four single-bar extrema represent only a restricted, operational QORE
    interpretation of the author's multi-swing bullish breaker structure.
    This detector does NOT select the true breaker low from the source.
    """
    if decision_at.utcoffset() is None:
        raise ValueError("decision_at must be aware")
    until = decision_at.astimezone(UTC)
    found: list[CausalBreakerShape] = []
    for i in range(len(bars) - 3):
        seq = bars[i:i + 4]
        start = seq[0].opened_at.astimezone(UTC)
        for bar in seq:
            if bar.opened_at.astimezone(UTC) != start:
                raise ValueError("breaker proxy source bars must be contiguous")
            if bar.closed_at.astimezone(UTC) != start + timedelta(minutes=3):
                raise ValueError("breaker proxy source must be exact closed M3")
            if bar.closed_at.astimezone(UTC) > until:
                raise ValueError("breaker cannot use a future M3 bar")
            start = bar.closed_at.astimezone(UTC)
        low_1, high_2, lower_low_3, higher_high_4 = (
            seq[0].low, seq[1].high, seq[2].low, seq[3].high
        )
        if lower_low_3 >= low_1 or higher_high_4 <= high_2:
            continue
        signature = (
            f"QORE-BREAKER-GEOMETRY|{seq[0].opened_at.isoformat()}|"
            f"{start.isoformat()}|{low_1}|{high_2}|{lower_low_3}|"
            f"{higher_high_4}"
        )
        found.append(
            CausalBreakerShape(
                low_1=low_1, high_2=high_2,
                lower_low_3=lower_low_3, higher_high_4=higher_high_4,
                source_first_opened_at=seq[0].opened_at,
                observed_at=seq[3].closed_at,
                origin_id="qore-breaker-proxy:" + hashlib.sha256(
                    signature.encode()
                ).hexdigest(),
            )
        )
    return tuple(found)


@dataclass(frozen=True, slots=True)
class M30BullishExampleAuthority:
    """Read-only schema, proof of AUTHOR RULE not proof of valid order."""

    status: AuthorCheckStatus
    decision_at: datetime
    candidate_eq_full_c2: Decimal | None
    candidate_eq_close_to_low_c2: Decimal | None
    pre_c2_external_pivot_known: bool
    research_breaker_proxy_count: int
    documented_stop_condition: str = "LONG_STOP_STRICTLY_BELOW_EQ_AND_BREAKER_LOW"
    stop_condition_written_A: bool = True
    source_eq_reference_swing_valid: bool = False
    source_breaker_low_adjudicated: bool = False
    source_poi_significant: bool = False
    source_entry_complete: bool = False
    cognitive_ready: bool = False
    authorized_orders: int = 0

    def as_json(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "decision_at": self.decision_at.astimezone(UTC).isoformat(),
            "candidate_eq_full_c2": (
                str(self.candidate_eq_full_c2)
                if self.candidate_eq_full_c2 is not None else None
            ),
            "candidate_eq_close_to_low_c2": (
                str(self.candidate_eq_close_to_low_c2)
                if self.candidate_eq_close_to_low_c2 is not None else None
            ),
            "pre_c2_external_pivot_known": self.pre_c2_external_pivot_known,
            "research_breaker_proxy_count": self.research_breaker_proxy_count,
            "doc_stop_rule": self.documented_stop_condition,
            "stop_rule_author_source": STOP_SOURCE,
            "breaker_structure_author_source": BREAKER_SOURCE,
            "poi_hierarchy_written_A": POI_AUTHOR_CONTINUATION_HIERARCHY,
            "ob_support_documented_A": POI_AUTHOR_ADDITIONAL_CONTEXT,
            "poi_source": POI_PRIORITY_SOURCE,
            "ob_source": POI_OB_SOURCE,
            "eq_source": EQ_SOURCE,
            "ps_stop_source": PS_STOP_SOURCE,
            "stop_rule_written_A": self.stop_condition_written_A,
            "reference_swing_eq_valid": self.source_eq_reference_swing_valid,
            "breaker_low_adjudicated": self.source_breaker_low_adjudicated,
            "source_poi_significant": self.source_poi_significant,
            "source_entry_complete": self.source_entry_complete,
            "cognitive_ready": self.cognitive_ready,
            "authorized_orders": self.authorized_orders,
        }


def stop_below_eq_and_breaker(
    *,
    stop: Decimal,
    eq: Decimal,
    breaker_low: Decimal,
) -> bool:
    """Literal numerical relation only; DOES NOT authenticate either level."""
    if min(stop, eq, breaker_low) <= 0:
        raise ValueError("quote prices must be positive")
    return stop < eq and stop < breaker_low


def inspect_bullish_m30_example(
    *,
    c2: Vt08B01Bar,
    decision_at: datetime,
    side: DemoTradingSetupSide,
    candidate_reference_pivots: tuple[ClosedExternalPivot, ...],
    preceding_m3: tuple[Vt08B01Bar, ...],
) -> M30BullishExampleAuthority:
    """Fail-closed EQ+breaker author check, no externally injected approval bool.

    The reference external pivot is independently VERIFIED TO EXIST before
    C2 opens but its author-valid relationship to C2 EQ still remains D.
    A breaker *geometry* is not an author-adjudicated breaker LOW.
    """
    if decision_at.utcoffset() is None:
        raise ValueError("decision clock must be aware")
    now = decision_at.astimezone(UTC)
    if c2.closed_at.astimezone(UTC) != (
        c2.opened_at.astimezone(UTC) + timedelta(minutes=30)
    ):
        raise ValueError("this author example requires complete M30 C2")
    if side is not DemoTradingSetupSide.LONG:
        return M30BullishExampleAuthority(
            status=AuthorCheckStatus.WRONG_FAMILY, decision_at=decision_at,
            candidate_eq_full_c2=None, candidate_eq_close_to_low_c2=None,
            pre_c2_external_pivot_known=False, research_breaker_proxy_count=0,
        )
    if c2.closed_at.astimezone(UTC) > now:
        return M30BullishExampleAuthority(
            status=AuthorCheckStatus.WAIT_M30_CLOSE, decision_at=decision_at,
            candidate_eq_full_c2=None, candidate_eq_close_to_low_c2=None,
            pre_c2_external_pivot_known=False, research_breaker_proxy_count=0,
        )
    if preceding_m3 and (
        preceding_m3[0].opened_at.astimezone(UTC)
        < c2.opened_at.astimezone(UTC)
    ):
        raise ValueError("breaker window must start within the M30 C2")
    if any(
        p.confirmed_at.astimezone(UTC) > c2.opened_at.astimezone(UTC)
        for p in candidate_reference_pivots
    ):
        raise ValueError("external pivot not known before C2 opens")
    past_relevant = any(
        p.kind is ExternalPivotKind.LOW
        and p.confirmed_at.astimezone(UTC) <= c2.opened_at.astimezone(UTC)
        for p in candidate_reference_pivots
    )
    shapes = observed_bullish_breaker_shapes(
        preceding_m3, decision_at=decision_at,
    )
    eq_full = (c2.high + c2.low) / 2
    eq_wick = (c2.close + c2.low) / 2
    # We expressly DO NOT select between them without an author-valid
    # swing identified pre-C2. Neither is a valid actionable EQ.
    return M30BullishExampleAuthority(
        status=AuthorCheckStatus.BOTH_EQ_AND_BREAKER_UNADJUDICATED,
        decision_at=decision_at,
        candidate_eq_full_c2=eq_full,
        candidate_eq_close_to_low_c2=eq_wick,
        pre_c2_external_pivot_known=past_relevant,
        research_breaker_proxy_count=len(shapes),
    )
