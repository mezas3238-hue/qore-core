"""VT-31 R2.2 source model and explicitly separate execution policy.

The primary authority is Human Owner file ``1000856441.mp4`` (TTrades AM
Silver Bullet). The source model retains entry evidence as zones/candles and
never silently converts a zone into an executable price. Any exact price
selection lives in :class:`Vt31R22ExecutionPolicy` and is fingerprinted as
``source_rule=False``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, time
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from zoneinfo import ZoneInfo

from qore.infrastructure.market_data import Instrument, OhlcSnapshot
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.kernel.errors import InfrastructureError

_NY = ZoneInfo("America/New_York")
_M1_SECONDS = 60
SOURCE_FILE = "1000856441.mp4"
SOURCE_SHA256 = "bd729056fadc30d20045e4677240b3a6cbb65123ced317e7413b6ffe81936ddf"
SOURCE_VIDEO = "youtube:o0v4KQxZbpU"
TRADER_CODE = "vt-31"
TRADER_VERSION = "r2.2"
METHODOLOGY_ID = "ttrades-am-silver-bullet-nq-r2.2"
AUTHORIZED_MARKET = "NAS100"


class Vt31R22Error(InfrastructureError):
    __slots__ = ()


class Vt31R22ValidationError(Vt31R22Error):
    __slots__ = ()


class Vt31R22EvidenceClass(StrEnum):
    SOURCE_EXPLICIT = "source-explicit"
    REPEATED_BEHAVIOR = "repeated-behavior"
    SOURCE_FORMALIZATION = "source-formalization"
    OPERATIONAL_CONTAINMENT = "operational-containment"
    HUMAN_OWNER_EXECUTION_POLICY = "human-owner-execution-policy"
    UNRESOLVED = "unresolved"


class Vt31R22EntryFamily(StrEnum):
    BREAKER = "breaker"
    ORDER_BLOCK = "order-block"
    FAIR_VALUE_GAP = "fair-value-gap"


class Vt31R22AbstainReason(StrEnum):
    UNSUPPORTED_MARKET = "unsupported-market"
    WINDOW_CLOSED = "window-closed"
    REFERENCE_INCOMPLETE = "reference-incomplete"
    SESSION_EVIDENCE_INCOMPLETE = "session-evidence-incomplete"
    NO_RAID = "no-raid"
    BOTH_SIDES_SWEPT = "both-sides-swept"
    NO_STRUCTURE_CONFIRMATION = "no-structure-confirmation"
    NO_ENTRY_EVIDENCE = "no-entry-evidence"
    AMBIGUOUS_ENTRY_FAMILY = "ambiguous-entry-family"
    INVALID_EXECUTION_GEOMETRY = "invalid-execution-geometry"


@dataclass(frozen=True, slots=True)
class Vt31R22ReferenceRange:
    high: Decimal
    low: Decimal
    opened_at: datetime
    closed_at: datetime

    def __post_init__(self) -> None:
        if not self.high.is_finite() or not self.low.is_finite() or self.low >= self.high:
            raise Vt31R22ValidationError("reference range must have finite low < high")
        _aware(self.opened_at, "reference opened_at")
        _aware(self.closed_at, "reference closed_at")
        if self.closed_at <= self.opened_at:
            raise Vt31R22ValidationError("reference range timestamps are invalid")


@dataclass(frozen=True, slots=True)
class Vt31R22StructureEvidence:
    raid_at: datetime
    confirmation_at: datetime
    side: DemoTradingSetupSide
    swing_extreme: Decimal
    structural_level: Decimal
    extreme_candle_open: Decimal
    extreme_candle_high: Decimal
    extreme_candle_low: Decimal
    extreme_candle_close: Decimal
    evidence_class: Vt31R22EvidenceClass = Vt31R22EvidenceClass.SOURCE_FORMALIZATION


@dataclass(frozen=True, slots=True)
class Vt31R22EntryEvidence:
    family: Vt31R22EntryFamily
    formed_at: datetime
    source_candle_open: Decimal
    source_candle_high: Decimal
    source_candle_low: Decimal
    source_candle_close: Decimal
    zone_lower: Decimal
    zone_upper: Decimal
    zone_class: Vt31R22EvidenceClass
    source_timestamps: tuple[str, ...]

    def __post_init__(self) -> None:
        _aware(self.formed_at, "entry evidence formed_at")
        values = (
            self.source_candle_open,
            self.source_candle_high,
            self.source_candle_low,
            self.source_candle_close,
            self.zone_lower,
            self.zone_upper,
        )
        if any(not item.is_finite() or item <= 0 for item in values):
            raise Vt31R22ValidationError("entry evidence prices must be positive finite")
        if self.zone_lower > self.zone_upper:
            raise Vt31R22ValidationError("entry zone must be ordered")
        if not self.source_timestamps:
            raise Vt31R22ValidationError("entry evidence requires source timestamps")


@dataclass(frozen=True, slots=True)
class Vt31R22SourceSetup:
    side: DemoTradingSetupSide
    reference: Vt31R22ReferenceRange
    structure: Vt31R22StructureEvidence
    candidates: tuple[Vt31R22EntryEvidence, ...]
    target_price: Decimal
    pending_expires_at: datetime
    source_fingerprint: str
    evidence_fingerprint: str

    def __post_init__(self) -> None:
        if not self.candidates:
            raise Vt31R22ValidationError("source setup requires entry evidence")
        _aware(self.pending_expires_at, "pending_expires_at")
        if not self.target_price.is_finite() or self.target_price <= 0:
            raise Vt31R22ValidationError("target must be positive finite")
        _sha256(self.source_fingerprint, "source_fingerprint")
        _sha256(self.evidence_fingerprint, "evidence_fingerprint")


@dataclass(frozen=True, slots=True)
class Vt31R22SourceEvaluation:
    setup: Vt31R22SourceSetup | None
    abstain_reason: Vt31R22AbstainReason | None
    both_sides_swept: bool

    def __post_init__(self) -> None:
        if (self.setup is None) == (self.abstain_reason is None):
            raise Vt31R22ValidationError("evaluation must contain setup xor abstain reason")


@dataclass(frozen=True, slots=True)
class Vt31R22ExecutionPolicy:
    """Versioned QORE translation from source zone to replay price.

    It deliberately reproduces midpoint/CE research geometry for baseline
    comparability, but this policy is never represented as a TTrades rule.
    """

    policy_id: str = "qore-vt31-r2.2-zone-midpoint-ce-earliest-v1"
    source_rule: bool = False
    breaker_price_policy: str = "body-midpoint"
    order_block_price_policy: str = "body-midpoint"
    fvg_price_policy: str = "consequent-encroachment"
    family_selection_policy: str = "earliest-actionable-fail-closed-confluence"
    stop_policy: str = "swing-extreme-no-buffer"
    same_bar_policy: str = "stop-first-before-be-be-first-after-be"

    def __post_init__(self) -> None:
        if self.source_rule:
            raise Vt31R22ValidationError("execution policy is not a source rule")

    def fingerprint(self) -> str:
        return _digest(
            {
                "schema": "qore.trader.vt31.r2.2.execution-policy.v1",
                "policy_id": self.policy_id,
                "source_rule": self.source_rule,
                "breaker_price_policy": self.breaker_price_policy,
                "order_block_price_policy": self.order_block_price_policy,
                "fvg_price_policy": self.fvg_price_policy,
                "family_selection_policy": self.family_selection_policy,
                "stop_policy": self.stop_policy,
                "same_bar_policy": self.same_bar_policy,
            }
        )


@dataclass(frozen=True, slots=True)
class Vt31R22ExecutableSetup:
    side: DemoTradingSetupSide
    entry_price: Decimal
    stop_price: Decimal
    target_price: Decimal
    three_r_price: Decimal
    selected_family: Vt31R22EntryFamily
    candidate_families: tuple[Vt31R22EntryFamily, ...]
    decision_at: datetime
    pending_expires_at: datetime
    source_setup: Vt31R22SourceSetup
    execution_policy_fingerprint: str

    @property
    def initial_risk(self) -> Decimal:
        return abs(self.entry_price - self.stop_price)


@dataclass(frozen=True, slots=True)
class _Raid:
    index: int
    side: DemoTradingSetupSide
    high_taken: bool
    low_taken: bool


def _digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _sha256(value: str, field: str) -> None:
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise Vt31R22ValidationError(f"{field} must be lowercase sha256")


def source_fingerprint() -> str:
    return _digest(
        {
            "schema": "qore.trader.vt31.r2.2.source.v1",
            "file": SOURCE_FILE,
            "sha256": SOURCE_SHA256,
            "video": SOURCE_VIDEO,
            "market": AUTHORIZED_MARKET,
            "reference": "09:00-10:00 America/New_York H1 from closed M1",
            "setup_window": "10:00-11:00 America/New_York",
            "raid": "strict-penetration-equality-is-not-sweep",
            "direction": "high->short low->long",
            "confirmation": "post-raid-structural-close-source-formalization",
            "entry_families": [item.value for item in Vt31R22EntryFamily],
            "stop": "methodological-swing-extreme",
            "target": "opposite-frozen-reference-side",
            "pending_expiry": "11:00 America/New_York",
            "filled_survives_11": True,
            "management": "3R->breakeven",
            "unresolved": [
                "breaker-exact-price",
                "order-block-exact-price",
                "generic-fvg-exact-price",
                "family-priority",
                "reentry",
                "numeric-displacement-threshold",
                "stop-tolerance",
            ],
        }
    )


def _aware(value: datetime, field: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise Vt31R22ValidationError(f"{field} must be timezone-aware")


def _d(value: float) -> Decimal:
    return Decimal(str(value))


def _wall(value: datetime) -> tuple[int, int, int]:
    local = value.astimezone(_NY)
    return local.hour, local.minute, local.second


def _same_day(value: datetime, as_of: datetime) -> bool:
    return value.astimezone(_NY).date() == as_of.astimezone(_NY).date()


def _window_close(as_of: datetime) -> datetime:
    local = as_of.astimezone(_NY)
    return datetime.combine(local.date(), time(11, 0), tzinfo=_NY).astimezone(UTC)


def _validate_evidence(
    instrument: Instrument,
    as_of: datetime,
    bars: tuple[OhlcSnapshot, ...],
) -> None:
    _aware(as_of, "as_of")
    if not isinstance(instrument, Instrument):
        raise Vt31R22ValidationError("instrument must be Instrument")
    previous: OhlcSnapshot | None = None
    seen: set[tuple[datetime, datetime]] = set()
    for bar in bars:
        if not isinstance(bar, OhlcSnapshot):
            raise Vt31R22ValidationError("M1 evidence must contain OhlcSnapshot")
        if bar.instrument != instrument:
            raise Vt31R22ValidationError("evidence instrument substitution is prohibited")
        if bar.timeframe.seconds != _M1_SECONDS:
            raise Vt31R22ValidationError("VT-31 R2.2 requires exact M1 evidence")
        if bar.closed_at > as_of:
            raise Vt31R22ValidationError("future/still-open evidence is prohibited")
        identity = (bar.opened_at.astimezone(UTC), bar.closed_at.astimezone(UTC))
        if identity in seen:
            raise Vt31R22ValidationError("duplicate M1 evidence is prohibited")
        seen.add(identity)
        if previous is not None and bar.opened_at < previous.opened_at:
            raise Vt31R22ValidationError("M1 evidence must be chronological")
        previous = bar


def build_reference_range(
    *,
    instrument: Instrument,
    as_of: datetime,
    bars: tuple[OhlcSnapshot, ...],
) -> Vt31R22ReferenceRange | None:
    _validate_evidence(instrument, as_of, bars)
    selected = tuple(
        bar
        for bar in bars
        if _same_day(bar.opened_at, as_of)
        and (9, 0, 0) <= _wall(bar.opened_at) < (10, 0, 0)
    )
    if len(selected) != 60 or _wall(selected[0].opened_at) != (9, 0, 0):
        return None
    if _wall(selected[-1].closed_at) != (10, 0, 0):
        return None
    if any(
        cur.opened_at != prev.closed_at
        for prev, cur in zip(selected, selected[1:], strict=False)
    ):
        return None
    return Vt31R22ReferenceRange(
        high=max(_d(item.high) for item in selected),
        low=min(_d(item.low) for item in selected),
        opened_at=selected[0].opened_at.astimezone(UTC),
        closed_at=selected[-1].closed_at.astimezone(UTC),
    )


def _session_bars(
    as_of: datetime,
    bars: tuple[OhlcSnapshot, ...],
) -> tuple[OhlcSnapshot, ...]:
    return tuple(
        bar
        for bar in bars
        if _same_day(bar.opened_at, as_of)
        and (10, 0, 0) <= _wall(bar.opened_at) < (11, 0, 0)
        and bar.closed_at <= as_of
    )


def _detect_raid(
    bars: tuple[OhlcSnapshot, ...],
    reference: Vt31R22ReferenceRange,
) -> _Raid | None:
    high_seen = False
    low_seen = False
    first_index: int | None = None
    first_side: DemoTradingSetupSide | None = None
    for index, bar in enumerate(bars):
        high = _d(bar.high) > reference.high
        low = _d(bar.low) < reference.low
        high_seen = high_seen or high
        low_seen = low_seen or low
        if first_index is None and (high or low):
            first_index = index
            if high and not low:
                first_side = DemoTradingSetupSide.SHORT
            elif low and not high:
                first_side = DemoTradingSetupSide.LONG
        if high_seen and low_seen:
            return _Raid(
                index if first_index is None else first_index,
                DemoTradingSetupSide.SHORT,
                True,
                True,
            )
    if first_index is None or first_side is None:
        return None
    return _Raid(first_index, first_side, high_seen, low_seen)


def _structure(
    bars: tuple[OhlcSnapshot, ...],
    raid: _Raid,
) -> tuple[int, int, Decimal, Decimal] | None:
    extreme_index = raid.index
    first = bars[raid.index]
    if raid.side is DemoTradingSetupSide.SHORT:
        extreme = _d(first.high)
        anchor = _d(first.low)
        for index in range(raid.index + 1, len(bars)):
            bar = bars[index]
            if _d(bar.high) > extreme:
                extreme = _d(bar.high)
                anchor = _d(bar.low)
                extreme_index = index
                continue
            if _d(bar.close) < anchor:
                return index, extreme_index, extreme, anchor
        return None
    extreme = _d(first.low)
    anchor = _d(first.high)
    for index in range(raid.index + 1, len(bars)):
        bar = bars[index]
        if _d(bar.low) < extreme:
            extreme = _d(bar.low)
            anchor = _d(bar.high)
            extreme_index = index
            continue
        if _d(bar.close) > anchor:
            return index, extreme_index, extreme, anchor
    return None


def _body_zone(bar: OhlcSnapshot) -> tuple[Decimal, Decimal]:
    opened = _d(bar.open)
    closed = _d(bar.close)
    return min(opened, closed), max(opened, closed)


def _candidate(
    *,
    family: Vt31R22EntryFamily,
    formed_at: datetime,
    source_bar: OhlcSnapshot,
    zone_lower: Decimal,
    zone_upper: Decimal,
    zone_class: Vt31R22EvidenceClass,
    timestamps: tuple[str, ...],
) -> Vt31R22EntryEvidence:
    return Vt31R22EntryEvidence(
        family=family,
        formed_at=formed_at.astimezone(UTC),
        source_candle_open=_d(source_bar.open),
        source_candle_high=_d(source_bar.high),
        source_candle_low=_d(source_bar.low),
        source_candle_close=_d(source_bar.close),
        zone_lower=zone_lower,
        zone_upper=zone_upper,
        zone_class=zone_class,
        source_timestamps=timestamps,
    )


def _entry_evidence(
    bars: tuple[OhlcSnapshot, ...],
    raid: _Raid,
    confirmation_index: int,
    extreme_index: int,
) -> tuple[Vt31R22EntryEvidence, ...]:
    result: list[Vt31R22EntryEvidence] = []
    extreme_bar = bars[extreme_index]
    opened = _d(extreme_bar.open)
    closed = _d(extreme_bar.close)
    opposite = (
        closed > opened
        if raid.side is DemoTradingSetupSide.SHORT
        else closed < opened
    )
    if opposite:
        lower, upper = _body_zone(extreme_bar)
        result.append(
            _candidate(
                family=Vt31R22EntryFamily.BREAKER,
                formed_at=bars[confirmation_index].closed_at,
                source_bar=extreme_bar,
                zone_lower=lower,
                zone_upper=upper,
                zone_class=Vt31R22EvidenceClass.SOURCE_FORMALIZATION,
                timestamps=("05:31-06:01", "07:18-07:43", "22:31-23:10"),
            )
        )
    opposite_bars: list[OhlcSnapshot] = []
    for bar in bars[raid.index : confirmation_index + 1]:
        opened = _d(bar.open)
        closed = _d(bar.close)
        if (raid.side is DemoTradingSetupSide.SHORT and closed > opened) or (
            raid.side is DemoTradingSetupSide.LONG and closed < opened
        ):
            opposite_bars.append(bar)
    if len(opposite_bars) == 1:
        source_bar = opposite_bars[0]
        lower, upper = _body_zone(source_bar)
        result.append(
            _candidate(
                family=Vt31R22EntryFamily.ORDER_BLOCK,
                formed_at=bars[confirmation_index].closed_at,
                source_bar=source_bar,
                zone_lower=lower,
                zone_upper=upper,
                zone_class=Vt31R22EvidenceClass.SOURCE_FORMALIZATION,
                timestamps=("10:32-10:49", "16:07-17:14"),
            )
        )
    for third_index in range(max(2, confirmation_index), len(bars)):
        first = bars[third_index - 2]
        third = bars[third_index]
        if raid.side is DemoTradingSetupSide.SHORT and _d(third.high) < _d(first.low):
            result.append(
                _candidate(
                    family=Vt31R22EntryFamily.FAIR_VALUE_GAP,
                    formed_at=third.closed_at,
                    source_bar=third,
                    zone_lower=_d(third.high),
                    zone_upper=_d(first.low),
                    zone_class=Vt31R22EvidenceClass.SOURCE_EXPLICIT,
                    timestamps=("02:26-02:56", "12:03-12:15", "22:31-23:10"),
                )
            )
            break
        if raid.side is DemoTradingSetupSide.LONG and _d(third.low) > _d(first.high):
            result.append(
                _candidate(
                    family=Vt31R22EntryFamily.FAIR_VALUE_GAP,
                    formed_at=third.closed_at,
                    source_bar=third,
                    zone_lower=_d(first.high),
                    zone_upper=_d(third.low),
                    zone_class=Vt31R22EvidenceClass.SOURCE_EXPLICIT,
                    timestamps=("21:12-21:37", "24:02-24:14"),
                )
            )
            break
    return tuple(sorted(result, key=lambda item: (item.formed_at, item.family.value)))


def evaluate_vt31_r2_2_source(
    *,
    instrument: Instrument,
    as_of: datetime,
    m1_candles: tuple[OhlcSnapshot, ...],
    evidence_fingerprint: str,
) -> Vt31R22SourceEvaluation:
    _validate_evidence(instrument, as_of, m1_candles)
    _sha256(evidence_fingerprint, "evidence_fingerprint")
    if instrument.symbol != AUTHORIZED_MARKET:
        return Vt31R22SourceEvaluation(
            None,
            Vt31R22AbstainReason.UNSUPPORTED_MARKET,
            False,
        )
    wall = _wall(as_of)
    if not (10, 0, 0) <= wall <= (11, 0, 0):
        return Vt31R22SourceEvaluation(None, Vt31R22AbstainReason.WINDOW_CLOSED, False)
    reference = build_reference_range(
        instrument=instrument,
        as_of=as_of,
        bars=m1_candles,
    )
    if reference is None:
        return Vt31R22SourceEvaluation(
            None,
            Vt31R22AbstainReason.REFERENCE_INCOMPLETE,
            False,
        )
    session = _session_bars(as_of, m1_candles)
    if not session:
        return Vt31R22SourceEvaluation(None, Vt31R22AbstainReason.NO_RAID, False)
    raid = _detect_raid(session, reference)
    if raid is None:
        return Vt31R22SourceEvaluation(None, Vt31R22AbstainReason.NO_RAID, False)
    if raid.high_taken and raid.low_taken:
        return Vt31R22SourceEvaluation(
            None,
            Vt31R22AbstainReason.BOTH_SIDES_SWEPT,
            True,
        )
    structure = _structure(session, raid)
    if structure is None:
        return Vt31R22SourceEvaluation(
            None,
            Vt31R22AbstainReason.NO_STRUCTURE_CONFIRMATION,
            False,
        )
    confirmation_index, extreme_index, extreme, anchor = structure
    candidates = _entry_evidence(session, raid, confirmation_index, extreme_index)
    if not candidates:
        return Vt31R22SourceEvaluation(
            None,
            Vt31R22AbstainReason.NO_ENTRY_EVIDENCE,
            False,
        )
    extreme_bar = session[extreme_index]
    structure_evidence = Vt31R22StructureEvidence(
        raid_at=session[raid.index].closed_at.astimezone(UTC),
        confirmation_at=session[confirmation_index].closed_at.astimezone(UTC),
        side=raid.side,
        swing_extreme=extreme,
        structural_level=anchor,
        extreme_candle_open=_d(extreme_bar.open),
        extreme_candle_high=_d(extreme_bar.high),
        extreme_candle_low=_d(extreme_bar.low),
        extreme_candle_close=_d(extreme_bar.close),
    )
    target = reference.low if raid.side is DemoTradingSetupSide.SHORT else reference.high
    return Vt31R22SourceEvaluation(
        Vt31R22SourceSetup(
            side=raid.side,
            reference=reference,
            structure=structure_evidence,
            candidates=candidates,
            target_price=target,
            pending_expires_at=_window_close(as_of),
            source_fingerprint=source_fingerprint(),
            evidence_fingerprint=evidence_fingerprint,
        ),
        None,
        False,
    )


def _execution_price(
    candidate: Vt31R22EntryEvidence,
    policy: Vt31R22ExecutionPolicy,
) -> Decimal:
    if candidate.family is Vt31R22EntryFamily.FAIR_VALUE_GAP:
        if policy.fvg_price_policy != "consequent-encroachment":
            raise Vt31R22ValidationError("unsupported FVG execution policy")
    elif candidate.family is Vt31R22EntryFamily.BREAKER:
        if policy.breaker_price_policy != "body-midpoint":
            raise Vt31R22ValidationError("unsupported breaker execution policy")
    elif policy.order_block_price_policy != "body-midpoint":
        raise Vt31R22ValidationError("unsupported order-block execution policy")
    return (candidate.zone_lower + candidate.zone_upper) / Decimal(2)


def make_executable_setup(
    source: Vt31R22SourceSetup,
    policy: Vt31R22ExecutionPolicy | None = None,
) -> tuple[Vt31R22ExecutableSetup | None, Vt31R22AbstainReason | None]:
    selected_policy = policy or Vt31R22ExecutionPolicy()
    earliest = min(item.formed_at for item in source.candidates)
    contemporaneous = tuple(
        item for item in source.candidates if item.formed_at == earliest
    )
    prices = tuple(_execution_price(item, selected_policy) for item in contemporaneous)
    if len(set(prices)) != 1:
        return None, Vt31R22AbstainReason.AMBIGUOUS_ENTRY_FAMILY
    chosen = contemporaneous[0]
    entry = prices[0]
    stop = source.structure.swing_extreme
    target = source.target_price
    if source.side is DemoTradingSetupSide.SHORT:
        valid = target < entry < stop
        three_r = entry - (stop - entry) * Decimal(3)
    else:
        valid = stop < entry < target
        three_r = entry + (entry - stop) * Decimal(3)
    if not valid:
        return None, Vt31R22AbstainReason.INVALID_EXECUTION_GEOMETRY
    return (
        Vt31R22ExecutableSetup(
            side=source.side,
            entry_price=entry,
            stop_price=stop,
            target_price=target,
            three_r_price=three_r,
            selected_family=chosen.family,
            candidate_families=tuple(item.family for item in contemporaneous),
            decision_at=earliest,
            pending_expires_at=source.pending_expires_at,
            source_setup=source,
            execution_policy_fingerprint=selected_policy.fingerprint(),
        ),
        None,
    )
