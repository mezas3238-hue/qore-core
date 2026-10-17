"""Source-closed Model #1 research contract for VT08 CRT PURE.

This module freezes only the Model #1 semantics that survived primary-source
adjudication.  It is research-only and grants no deployment authority.

Source-closed core:
- H4 CRT -> M15 Model #1.
- Bearish Model #1: an up-close M15 candle stabs an old high; a later M15
  body closes below that source candle.
- Bullish Model #1: a down-close M15 candle stabs an old low; a later M15
  body closes above that source candle.
- Wick-only confirmation does not count.

Still caller-owned / engineering:
- which eligible old high/low is the active reference when several exist;
- exact market fill transport after the confirming close;
- destination selection and position management.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

MODEL1_PARENT_TIMEFRAME_SECONDS = 4 * 60 * 60
MODEL1_EXECUTION_TIMEFRAME_SECONDS = 15 * 60
MODEL1_FILL_POLICY = "NEXT_M15_OPEN_AFTER_CONFIRMING_CLOSE"


class CrtPureModel1Direction(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"


class CrtPureModel1ReferenceKind(StrEnum):
    OLD_HIGH = "OLD_HIGH"
    OLD_LOW = "OLD_LOW"


class CrtPureModel1State(StrEnum):
    NO_CANDIDATE = "NO_CANDIDATE"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    ENTRY_READY = "ENTRY_READY"


@dataclass(frozen=True, slots=True)
class CrtPureModel1Bar:
    opened_at: datetime
    open_price: int
    high_price: int
    low_price: int
    close_price: int

    def __post_init__(self) -> None:
        if self.opened_at.tzinfo is None or self.opened_at.utcoffset() is None:
            raise ValueError("Model #1 bar timestamp must be timezone-aware")
        if self.low_price > min(self.open_price, self.close_price):
            raise ValueError("Model #1 low must not exceed candle body")
        if self.high_price < max(self.open_price, self.close_price):
            raise ValueError("Model #1 high must not be below candle body")
        if self.low_price > self.high_price:
            raise ValueError("Model #1 bar low must not exceed high")

    @property
    def is_up_close(self) -> bool:
        return self.close_price > self.open_price

    @property
    def is_down_close(self) -> bool:
        return self.close_price < self.open_price


@dataclass(frozen=True, slots=True)
class CrtPureModel1Reference:
    kind: CrtPureModel1ReferenceKind
    price: int
    evidence_id: str

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise ValueError("Model #1 old-level reference requires evidence_id")


@dataclass(frozen=True, slots=True)
class CrtPureModel1Candidate:
    direction: CrtPureModel1Direction
    reference: CrtPureModel1Reference
    source_candle: CrtPureModel1Bar
    confirmation_body_level: int
    structural_stop: int
    thick_body_required: bool = False
    source_rule_closed: bool = True
    executable_authority: bool = False

    def __post_init__(self) -> None:
        if self.executable_authority:
            raise ValueError("Model #1 candidate cannot grant execution authority")
        expected = (
            CrtPureModel1ReferenceKind.OLD_LOW
            if self.direction is CrtPureModel1Direction.BULLISH
            else CrtPureModel1ReferenceKind.OLD_HIGH
        )
        if self.reference.kind is not expected:
            raise ValueError("Model #1 direction/reference kind mismatch")


@dataclass(frozen=True, slots=True)
class CrtPureModel1Confirmation:
    candidate: CrtPureModel1Candidate
    confirming_candle: CrtPureModel1Bar
    state: CrtPureModel1State
    decision_at: datetime

    def __post_init__(self) -> None:
        if self.confirming_candle.opened_at <= self.candidate.source_candle.opened_at:
            raise ValueError("Model #1 confirmation must occur after source candle")
        expected_decision = self.confirming_candle.opened_at + timedelta(
            seconds=MODEL1_EXECUTION_TIMEFRAME_SECONDS
        )
        if self.decision_at != expected_decision:
            raise ValueError("Model #1 decision_at must equal confirming M15 close")


@dataclass(frozen=True, slots=True)
class CrtPureModel1Entry:
    confirmation: CrtPureModel1Confirmation
    fill_candle: CrtPureModel1Bar
    entry_price: int
    stop_price: int
    fill_policy: str = MODEL1_FILL_POLICY
    research_only: bool = True
    demo_authorized: bool = False
    live_authorized: bool = False
    production_authorized: bool = False

    def __post_init__(self) -> None:
        if self.confirmation.state is not CrtPureModel1State.CONFIRMED:
            raise ValueError("Model #1 entry requires confirmed source event")
        if self.fill_candle.opened_at != self.confirmation.decision_at:
            raise ValueError("Model #1 fill must use next M15 open after confirming close")
        if self.entry_price != self.fill_candle.open_price:
            raise ValueError("Model #1 engineering fill must equal next M15 open")
        if self.demo_authorized or self.live_authorized or self.production_authorized:
            raise ValueError("Model #1 research contract grants no deployment authority")


def detect_model1_candidate(
    *,
    reference: CrtPureModel1Reference,
    candle: CrtPureModel1Bar,
) -> CrtPureModel1Candidate | None:
    """Detect the source candle against an already-adjudicated old level."""

    if (
        reference.kind is CrtPureModel1ReferenceKind.OLD_HIGH
        and candle.high_price > reference.price
        and candle.is_up_close
    ):
        return CrtPureModel1Candidate(
            direction=CrtPureModel1Direction.BEARISH,
            reference=reference,
            source_candle=candle,
            confirmation_body_level=candle.open_price,
            structural_stop=candle.high_price,
        )

    if (
        reference.kind is CrtPureModel1ReferenceKind.OLD_LOW
        and candle.low_price < reference.price
        and candle.is_down_close
    ):
        return CrtPureModel1Candidate(
            direction=CrtPureModel1Direction.BULLISH,
            reference=reference,
            source_candle=candle,
            confirmation_body_level=candle.open_price,
            structural_stop=candle.low_price,
        )

    return None


def assess_model1_confirmation(
    *,
    candidate: CrtPureModel1Candidate,
    candle: CrtPureModel1Bar,
) -> CrtPureModel1Confirmation:
    """Confirm only on a later M15 body close beyond the Model #1 body boundary."""

    if candle.opened_at <= candidate.source_candle.opened_at:
        raise ValueError("confirmation candle must occur after Model #1 source candle")

    confirmed = (
        candle.close_price > candidate.confirmation_body_level
        if candidate.direction is CrtPureModel1Direction.BULLISH
        else candle.close_price < candidate.confirmation_body_level
    )
    return CrtPureModel1Confirmation(
        candidate=candidate,
        confirming_candle=candle,
        state=(
            CrtPureModel1State.CONFIRMED
            if confirmed
            else CrtPureModel1State.AWAITING_CONFIRMATION
        ),
        decision_at=candle.opened_at
        + timedelta(seconds=MODEL1_EXECUTION_TIMEFRAME_SECONDS),
    )


def build_model1_entry(
    *,
    confirmation: CrtPureModel1Confirmation,
    next_candle: CrtPureModel1Bar,
) -> CrtPureModel1Entry:
    """Bind a causal replay fill without pretending the fill convention is Romeo's rule."""

    return CrtPureModel1Entry(
        confirmation=confirmation,
        fill_candle=next_candle,
        entry_price=next_candle.open_price,
        stop_price=confirmation.candidate.structural_stop,
    )
