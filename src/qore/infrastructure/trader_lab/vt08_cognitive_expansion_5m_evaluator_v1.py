"""Research-only VT08 B01 evaluator for the 5M expansion universe.

The source mechanics are intentionally reused from the frozen VT08 B01 module.
The four new markets are admitted only inside Trader Lab research; this module
does not alter AUTHORIZED_FOREX_MARKETS in the certified Trader.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
    EXPANSION_MARKETS,
    program_fingerprint,
)
from qore.infrastructure.traders.contracts import (
    DemoTradingError,
    DemoTradingSetupSide,
    DemoTradingSetupSpec,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    Vt08B01ProtectedSwing,
    protected_swings_in_candle2,
    resolve_bias,
    source_day_from_m15,
    source_h4_from_m15,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    methodology_fingerprint as vt08_b01_methodology_fingerprint,
)

_NY = ZoneInfo("America/New_York")


class Vt08ExpansionAbstainReason(StrEnum):
    UNSUPPORTED_RESEARCH_MARKET = "unsupported-research-market"
    OUTSIDE_OWNER_ANCHOR = "outside-owner-anchor"
    INCOMPLETE_SOURCE_H4 = "incomplete-source-h4"
    INCOMPLETE_SOURCE_DAY = "incomplete-source-day"
    BIAS_UNRESOLVED = "bias-unresolved"
    C2_REVERSAL_MISMATCH = "c2-reversal-mismatch"
    NO_PROTECTED_SWING = "no-protected-swing"
    MULTIPLE_PROTECTED_SWINGS = "multiple-protected-swings"
    INVALID_RISK_GEOMETRY = "invalid-risk-geometry"


@dataclass(frozen=True, slots=True)
class Vt08ExpansionCandidate:
    symbol: str
    side: DemoTradingSetupSide
    decision_at: datetime
    entry_anchor_hour: int
    reference_h4: Vt08B01Bar
    candle2: Vt08B01Bar
    protected_swing: Vt08B01ProtectedSwing
    setup: DemoTradingSetupSpec
    vt08_methodology_fingerprint: str
    expansion_program_fingerprint: str
    research_only: bool = True

    def __post_init__(self) -> None:
        if self.symbol not in EXPANSION_MARKETS:
            raise ValueError("candidate outside frozen VT08 5M research universe")
        if self.entry_anchor_hour not in ANCHORS_NY:
            raise ValueError("candidate outside 01/05/09 NY")
        if self.side is not self.protected_swing.side or self.side is not self.setup.side:
            raise ValueError("candidate side evidence disagrees")
        if not self.research_only:
            raise ValueError("VT08 5M candidate must remain research-only")
        if self.vt08_methodology_fingerprint != vt08_b01_methodology_fingerprint():
            raise ValueError("VT08 source methodology fingerprint drifted")
        if self.expansion_program_fingerprint != program_fingerprint():
            raise ValueError("VT08 expansion program fingerprint drifted")


@dataclass(frozen=True, slots=True)
class Vt08ExpansionEvaluation:
    candidate: Vt08ExpansionCandidate | None
    abstain_reason: Vt08ExpansionAbstainReason | None

    def __post_init__(self) -> None:
        if (self.candidate is None) == (self.abstain_reason is None):
            raise ValueError("evaluation requires exactly one outcome")


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


def _latest_complete_source_days(
    bars_by_open: dict[datetime, Vt08B01Bar],
    *,
    before_local: datetime,
) -> tuple[Vt08B01Bar, ...]:
    end_date = before_local.astimezone(_NY).date() - timedelta(days=1)
    retained: list[Vt08B01Bar] = []
    for offset in range(10):
        item = source_day_from_m15(
            bars_by_open,
            end_date=end_date - timedelta(days=offset),
        )
        if item is not None:
            retained.append(item)
            if len(retained) == 2:
                break
    return tuple(retained)


def _candle2_reversal_side(
    reference: Vt08B01Bar,
    candle2: Vt08B01Bar,
) -> DemoTradingSetupSide | None:
    swept_high = candle2.high > reference.high
    swept_low = candle2.low < reference.low
    if swept_high == swept_low:
        return None
    if not reference.low < candle2.close < reference.high:
        return None
    return DemoTradingSetupSide.SHORT if swept_high else DemoTradingSetupSide.LONG


def _window_bars(
    bars_by_open: dict[datetime, Vt08B01Bar],
    *,
    opened_at: datetime,
    closed_at: datetime,
) -> tuple[Vt08B01Bar, ...] | None:
    start = _utc(opened_at)
    end = _utc(closed_at)
    retained: list[Vt08B01Bar] = []
    cursor = start
    while cursor < end:
        bar = bars_by_open.get(cursor)
        if bar is None or bar.closed_at != cursor + timedelta(minutes=15):
            return None
        retained.append(bar)
        cursor += timedelta(minutes=15)
    return tuple(retained) if cursor == end else None


def evaluate_expansion_at_entry_indexed(
    *,
    symbol: str,
    bars_by_open: dict[datetime, Vt08B01Bar],
    decision_at: datetime,
) -> Vt08ExpansionEvaluation:
    if symbol not in EXPANSION_MARKETS:
        return Vt08ExpansionEvaluation(
            None,
            Vt08ExpansionAbstainReason.UNSUPPORTED_RESEARCH_MARKET,
        )

    decision_utc = _utc(decision_at)
    decision_local = decision_utc.astimezone(_NY)
    if (
        decision_local.minute != 0
        or decision_local.second != 0
        or decision_local.microsecond != 0
        or decision_local.hour not in ANCHORS_NY
    ):
        return Vt08ExpansionEvaluation(
            None,
            Vt08ExpansionAbstainReason.OUTSIDE_OWNER_ANCHOR,
        )

    reference = source_h4_from_m15(
        bars_by_open,
        opened_at_local=decision_local - timedelta(hours=8),
    )
    candle2 = source_h4_from_m15(
        bars_by_open,
        opened_at_local=decision_local - timedelta(hours=4),
    )
    if reference is None or candle2 is None or candle2.closed_at != decision_utc:
        return Vt08ExpansionEvaluation(
            None,
            Vt08ExpansionAbstainReason.INCOMPLETE_SOURCE_H4,
        )

    source_days = _latest_complete_source_days(
        bars_by_open,
        before_local=decision_local,
    )
    if len(source_days) != 2:
        return Vt08ExpansionEvaluation(
            None,
            Vt08ExpansionAbstainReason.INCOMPLETE_SOURCE_DAY,
        )
    current_day, previous_day = source_days
    side = resolve_bias(previous_day=previous_day, current_day=current_day)
    if side is None:
        return Vt08ExpansionEvaluation(
            None,
            Vt08ExpansionAbstainReason.BIAS_UNRESOLVED,
        )
    if _candle2_reversal_side(reference, candle2) is not side:
        return Vt08ExpansionEvaluation(
            None,
            Vt08ExpansionAbstainReason.C2_REVERSAL_MISMATCH,
        )

    candle2_m15 = _window_bars(
        bars_by_open,
        opened_at=candle2.opened_at,
        closed_at=candle2.closed_at,
    )
    if candle2_m15 is None:
        return Vt08ExpansionEvaluation(
            None,
            Vt08ExpansionAbstainReason.INCOMPLETE_SOURCE_H4,
        )

    important_level = (
        reference.low if side is DemoTradingSetupSide.LONG else reference.high
    )
    swings = protected_swings_in_candle2(
        candle2_m15,
        side=side,
        important_level=important_level,
    )
    if not swings:
        return Vt08ExpansionEvaluation(
            None,
            Vt08ExpansionAbstainReason.NO_PROTECTED_SWING,
        )
    if len(swings) != 1:
        return Vt08ExpansionEvaluation(
            None,
            Vt08ExpansionAbstainReason.MULTIPLE_PROTECTED_SWINGS,
        )
    protected = swings[0]

    entry_bar = bars_by_open.get(decision_utc)
    if entry_bar is None:
        return Vt08ExpansionEvaluation(
            None,
            Vt08ExpansionAbstainReason.INCOMPLETE_SOURCE_H4,
        )
    entry = entry_bar.open
    stop = protected.price
    risk = entry - stop if side is DemoTradingSetupSide.LONG else stop - entry
    if risk <= 0:
        return Vt08ExpansionEvaluation(
            None,
            Vt08ExpansionAbstainReason.INVALID_RISK_GEOMETRY,
        )
    target = (
        entry + Decimal(2) * risk
        if side is DemoTradingSetupSide.LONG
        else entry - Decimal(2) * risk
    )
    if target <= 0:
        return Vt08ExpansionEvaluation(
            None,
            Vt08ExpansionAbstainReason.INVALID_RISK_GEOMETRY,
        )

    try:
        setup = DemoTradingSetupSpec(
            side=side,
            entry_price=entry,
            invalidation_price=stop,
            take_profit_price=target,
            entry_reason=(
                "vt08-cognitive-expansion-5m-v1;"
                "source-faithful-b01;"
                "research-only-new-market-license-test"
            ),
        )
    except DemoTradingError as error:
        raise ValueError("VT08 5M setup geometry invalid") from error

    return Vt08ExpansionEvaluation(
        candidate=Vt08ExpansionCandidate(
            symbol=symbol,
            side=side,
            decision_at=decision_utc,
            entry_anchor_hour=decision_local.hour,
            reference_h4=reference,
            candle2=candle2,
            protected_swing=protected,
            setup=setup,
            vt08_methodology_fingerprint=vt08_b01_methodology_fingerprint(),
            expansion_program_fingerprint=program_fingerprint(),
        ),
        abstain_reason=None,
    )


def expansion_evaluator_fingerprint() -> str:
    material = {
        "schema": "qore.vt08.cognitive_expansion_5m.evaluator.v1",
        "program_fingerprint": program_fingerprint(),
        "vt08_methodology_fingerprint": vt08_b01_methodology_fingerprint(),
        "markets": EXPANSION_MARKETS,
        "anchors_ny": ANCHORS_NY,
        "target": "2R",
        "outer_lifecycle": "next-h4-boundary",
        "daily_cardinality": "exactly-one-candidate-per-market-ny-date",
        "research_only": True,
    }
    encoded = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
