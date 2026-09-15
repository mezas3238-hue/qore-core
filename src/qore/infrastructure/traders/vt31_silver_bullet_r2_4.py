"""VT-31 R2.4 source-demonstrated AM Silver Bullet subset.

R2.4 preserves the R2.2 source-structure model but revokes generic executable
prices for Breaker, Order Block and FVG zones.  The only executable historical
subset implemented here is the primary-video example around 02:37-02:56:

* NAS100 / NQ AM Silver Bullet only;
* 09:00-10:00 New-York reference range;
* 10:00-11:00 setup window;
* high raid -> SHORT;
* post-raid structural confirmation;
* bearish M1 FVG whose consequent encroachment exactly coincides with the
  New-York midnight-open price;
* historical entry at that exact confluence price;
* historical stop at the demonstrated raid swing high;
* target at the opposite 09:00-10:00 range low;
* 3R touch arms break-even;
* unfilled entry expires at 11:00; filled positions may survive 11:00.

No generic Breaker/OB/FVG execution price, broker order type, live stop offset,
re-entry rule, or both-sides-swept priority is invented here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from zoneinfo import ZoneInfo

from qore.infrastructure.market_data import Instrument, OhlcSnapshot
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    AUTHORIZED_MARKET,
    SOURCE_FILE,
    SOURCE_SHA256,
    SOURCE_VIDEO,
    Vt31R22SourceEvaluation,
    Vt31R22SourceSetup,
    evaluate_vt31_r2_2_source,
)
from qore.kernel.errors import InfrastructureError

_NY = ZoneInfo("America/New_York")
_BUNDLE_ID = "SB_AM_FVG_MIDNIGHT_CE_SHORT_R2_4_V1"
_METHODOLOGY_ID = "ttrades-am-silver-bullet-nq-r2.4-source-demonstrated-subset"


class Vt31R24Error(InfrastructureError):
    __slots__ = ()


class Vt31R24ValidationError(Vt31R24Error):
    __slots__ = ()


class Vt31R24AbstainReason(StrEnum):
    SOURCE_MODEL_ABSTAINED = "source-model-abstained"
    LONG_NOT_SOURCE_DEMONSTRATED = "long-not-source-demonstrated-r2.4"
    MIDNIGHT_OPEN_MISSING = "midnight-open-missing"
    NO_EXACT_FVG_MIDNIGHT_CONFLUENCE = "no-exact-fvg-midnight-confluence"
    MULTIPLE_EXACT_FVG_MIDNIGHT_CONFLUENCES = "multiple-exact-fvg-midnight-confluences"
    INVALID_EXECUTION_GEOMETRY = "invalid-execution-geometry"


@dataclass(frozen=True, slots=True)
class Vt31R24FvgConfluence:
    first_opened_at: datetime
    third_closed_at: datetime
    lower: Decimal
    upper: Decimal
    consequent_encroachment: Decimal
    midnight_open: Decimal

    def __post_init__(self) -> None:
        for value in (self.lower, self.upper, self.consequent_encroachment, self.midnight_open):
            if not value.is_finite() or value <= 0:
                raise Vt31R24ValidationError("confluence prices must be positive finite")
        if self.lower >= self.upper:
            raise Vt31R24ValidationError("FVG must have lower < upper")
        if self.consequent_encroachment != (self.lower + self.upper) / Decimal(2):
            raise Vt31R24ValidationError("consequent encroachment must be exact FVG midpoint")
        if self.consequent_encroachment != self.midnight_open:
            raise Vt31R24ValidationError("R2.4 subset requires exact CE/midnight-open equality")
        _aware(self.first_opened_at, "first_opened_at")
        _aware(self.third_closed_at, "third_closed_at")
        if self.third_closed_at <= self.first_opened_at:
            raise Vt31R24ValidationError("FVG timestamps must be causal")


@dataclass(frozen=True, slots=True)
class Vt31R24ExactSetup:
    bundle_id: str
    side: DemoTradingSetupSide
    entry_price: Decimal
    stop_price: Decimal
    target_price: Decimal
    three_r_price: Decimal
    decision_at: datetime
    pending_expires_at: datetime
    confluence: Vt31R24FvgConfluence
    source_setup: Vt31R22SourceSetup
    source_bundle_fingerprint: str
    broker_order_type_resolved: bool = False
    live_stop_offset_resolved: bool = False

    def __post_init__(self) -> None:
        if self.bundle_id != _BUNDLE_ID:
            raise Vt31R24ValidationError("unexpected R2.4 bundle id")
        if self.side is not DemoTradingSetupSide.SHORT:
            raise Vt31R24ValidationError("R2.4 exact subset is source-demonstrated SHORT only")
        for value in (self.entry_price, self.stop_price, self.target_price, self.three_r_price):
            if not value.is_finite() or value <= 0:
                raise Vt31R24ValidationError("setup prices must be positive finite")
        if not self.target_price < self.entry_price < self.stop_price:
            raise Vt31R24ValidationError("SHORT setup geometry must be target < entry < stop")
        expected_three_r = self.entry_price - (self.stop_price - self.entry_price) * Decimal(3)
        if self.three_r_price != expected_three_r:
            raise Vt31R24ValidationError("three_r_price must be exact 3R projection")
        if self.entry_price != self.confluence.consequent_encroachment:
            raise Vt31R24ValidationError("entry must equal exact FVG CE/midnight confluence")
        if self.stop_price != self.source_setup.structure.swing_extreme:
            raise Vt31R24ValidationError("historical stop must equal demonstrated swing extreme")
        if self.target_price != self.source_setup.reference.low:
            raise Vt31R24ValidationError("SHORT target must equal opposite reference low")
        _aware(self.decision_at, "decision_at")
        _aware(self.pending_expires_at, "pending_expires_at")
        if self.decision_at != self.confluence.third_closed_at:
            raise Vt31R24ValidationError("decision time must be when the qualifying FVG is known")
        if self.decision_at >= self.pending_expires_at:
            raise Vt31R24ValidationError("decision must precede strict 11:00 expiry")
        _sha256(self.source_bundle_fingerprint, "source_bundle_fingerprint")
        if self.broker_order_type_resolved or self.live_stop_offset_resolved:
            raise Vt31R24ValidationError("R2.4 historical subset grants no live broker exactness")

    @property
    def initial_risk(self) -> Decimal:
        return self.stop_price - self.entry_price


@dataclass(frozen=True, slots=True)
class Vt31R24Evaluation:
    source_evaluation: Vt31R22SourceEvaluation
    setup: Vt31R24ExactSetup | None
    abstain_reason: Vt31R24AbstainReason | None

    def __post_init__(self) -> None:
        if (self.setup is None) == (self.abstain_reason is None):
            raise Vt31R24ValidationError("R2.4 evaluation requires setup xor abstain reason")


def _aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise Vt31R24ValidationError(f"{field} must be timezone-aware")


def _sha256(value: str, field: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise Vt31R24ValidationError(f"{field} must be lowercase sha256")


def _digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def source_bundle_fingerprint() -> str:
    return _digest(
        {
            "schema": "qore.trader.vt31.r2.4.source-demonstrated-bundle.v1",
            "bundle_id": _BUNDLE_ID,
            "methodology_id": _METHODOLOGY_ID,
            "source_file": SOURCE_FILE,
            "source_sha256": SOURCE_SHA256,
            "source_video": SOURCE_VIDEO,
            "primary_video_window": "02:37-02:56",
            "market": AUTHORIZED_MARKET,
            "direction": "high-raid-to-short-only",
            "entry": "bearish-fvg-ce-exactly-equals-new-york-midnight-open",
            "historical_stop": "raid-swing-high-primary-audio-plus-visual",
            "target": "opposite-09:00-10:00-reference-low",
            "management": "3R-touch-intrabar-arms-stop-to-entry",
            "pending_expiry": "11:00-America/New_York",
            "filled_position_may_survive_11": True,
            "broker_order_type": "unresolved",
            "live_stop_offset": "unresolved",
            "generic_breaker_entry": "unresolved",
            "generic_order_block_entry": "unresolved",
            "generic_fvg_entry": "unresolved",
            "both_sides_swept": "abstain-operational-containment",
            "reentry": "unresolved-human-owner-max-one-fill-per-day",
        }
    )


def _same_ny_date(value: datetime, as_of: datetime) -> bool:
    return value.astimezone(_NY).date() == as_of.astimezone(_NY).date()


def _wall(value: datetime) -> tuple[int, int, int]:
    local = value.astimezone(_NY)
    return local.hour, local.minute, local.second


def _d(value: float) -> Decimal:
    return Decimal(str(value))


def _midnight_open(
    as_of: datetime,
    bars: tuple[OhlcSnapshot, ...],
) -> Decimal | None:
    matches = tuple(
        bar
        for bar in bars
        if _same_ny_date(bar.opened_at, as_of) and _wall(bar.opened_at) == (0, 0, 0)
    )
    if len(matches) != 1:
        return None
    return _d(matches[0].open)


def _qualifying_confluences(
    *,
    as_of: datetime,
    bars: tuple[OhlcSnapshot, ...],
    source_setup: Vt31R22SourceSetup,
    midnight_open: Decimal,
) -> tuple[Vt31R24FvgConfluence, ...]:
    session = tuple(
        bar
        for bar in bars
        if _same_ny_date(bar.opened_at, as_of)
        and (10, 0, 0) <= _wall(bar.opened_at) < (11, 0, 0)
        and bar.closed_at <= as_of
    )
    result: list[Vt31R24FvgConfluence] = []
    for third_index in range(2, len(session)):
        first = session[third_index - 2]
        second = session[third_index - 1]
        third = session[third_index]
        if first.closed_at != second.opened_at or second.closed_at != third.opened_at:
            continue
        if third.closed_at < source_setup.structure.confirmation_at:
            continue
        first_low = _d(first.low)
        third_high = _d(third.high)
        if third_high >= first_low:
            continue
        ce = (third_high + first_low) / Decimal(2)
        if ce != midnight_open:
            continue
        result.append(
            Vt31R24FvgConfluence(
                first_opened_at=first.opened_at.astimezone(UTC),
                third_closed_at=third.closed_at.astimezone(UTC),
                lower=third_high,
                upper=first_low,
                consequent_encroachment=ce,
                midnight_open=midnight_open,
            )
        )
    return tuple(result)


def evaluate_vt31_r2_4_exact(
    *,
    instrument: Instrument,
    as_of: datetime,
    m1_candles: tuple[OhlcSnapshot, ...],
    evidence_fingerprint: str,
) -> Vt31R24Evaluation:
    """Evaluate only the R2.4 source-demonstrated historical subset."""

    source_evaluation = evaluate_vt31_r2_2_source(
        instrument=instrument,
        as_of=as_of,
        m1_candles=m1_candles,
        evidence_fingerprint=evidence_fingerprint,
    )
    source_setup = source_evaluation.setup
    if source_setup is None:
        return Vt31R24Evaluation(
            source_evaluation,
            None,
            Vt31R24AbstainReason.SOURCE_MODEL_ABSTAINED,
        )
    if source_setup.side is not DemoTradingSetupSide.SHORT:
        return Vt31R24Evaluation(
            source_evaluation,
            None,
            Vt31R24AbstainReason.LONG_NOT_SOURCE_DEMONSTRATED,
        )
    midnight_open = _midnight_open(as_of, m1_candles)
    if midnight_open is None:
        return Vt31R24Evaluation(
            source_evaluation,
            None,
            Vt31R24AbstainReason.MIDNIGHT_OPEN_MISSING,
        )
    confluences = _qualifying_confluences(
        as_of=as_of,
        bars=m1_candles,
        source_setup=source_setup,
        midnight_open=midnight_open,
    )
    if not confluences:
        return Vt31R24Evaluation(
            source_evaluation,
            None,
            Vt31R24AbstainReason.NO_EXACT_FVG_MIDNIGHT_CONFLUENCE,
        )
    if len(confluences) != 1:
        return Vt31R24Evaluation(
            source_evaluation,
            None,
            Vt31R24AbstainReason.MULTIPLE_EXACT_FVG_MIDNIGHT_CONFLUENCES,
        )
    confluence = confluences[0]
    entry = confluence.consequent_encroachment
    stop = source_setup.structure.swing_extreme
    target = source_setup.reference.low
    if not target < entry < stop:
        return Vt31R24Evaluation(
            source_evaluation,
            None,
            Vt31R24AbstainReason.INVALID_EXECUTION_GEOMETRY,
        )
    setup = Vt31R24ExactSetup(
        bundle_id=_BUNDLE_ID,
        side=DemoTradingSetupSide.SHORT,
        entry_price=entry,
        stop_price=stop,
        target_price=target,
        three_r_price=entry - (stop - entry) * Decimal(3),
        decision_at=confluence.third_closed_at,
        pending_expires_at=source_setup.pending_expires_at,
        confluence=confluence,
        source_setup=source_setup,
        source_bundle_fingerprint=source_bundle_fingerprint(),
    )
    return Vt31R24Evaluation(source_evaluation, setup, None)
