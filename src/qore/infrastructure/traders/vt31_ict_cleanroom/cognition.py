"""One clean-room VT31 cognition for London and New York Silver Bullets.

Deliberately independent of every legacy VT31/COMP/TTrades module. Emits the
shared OPS CognitiveDecision only after independently causal closed-M1 DOL and
displacement-confirmed market-structure shift. No trading authority.

Causal policies below are explicit, *research-only* operational hypotheses,
not claims that ICT 2023 mandates these exact displacement/HTF thresholds.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from statistics import median

from .contracts import (
    MIN_INDEX_POINTS,
    NEW_YORK,
    CognitiveDecision,
    M1Bar,
    SessionId,
    Side,
    utc,
    window_bounds,
)

VERSION = "VT31_ICT_CLEANROOM_COG_V1"
MODEL_ID = "VT31"
ASIA_WINDOW = (0, 3)
LONDON_EARLY_WINDOW = (3, 5)


@dataclass(frozen=True, slots=True)
class LiquidityPool:
    family: str
    side: Side
    level: Decimal
    confirmed_at: datetime
    source_start: datetime
    source_end: datetime

    def __post_init__(self) -> None:
        if self.level <= 0 or not self.level.is_finite():
            raise ValueError("liquidity target must be a finite positive price")
        if utc(self.source_start) > utc(self.source_end):
            raise ValueError("inverted native liquidity range")
        if utc(self.source_end) > utc(self.confirmed_at):
            raise ValueError("unconfirmed source liquidity")
        if not self.family:
            raise ValueError("missing market source family")


@dataclass(frozen=True, slots=True)
class CausalSwingBreak:
    side: Side
    level: Decimal
    pivot_confirmed_at: datetime
    break_confirmed_at: datetime
    displacement_body: Decimal
    displacement_reference: Decimal

    def __post_init__(self) -> None:
        if utc(self.pivot_confirmed_at) >= utc(self.break_confirmed_at):
            raise ValueError("structure must be confirmed before its break")
        if self.level <= 0 or self.displacement_body <= 0:
            raise ValueError("positive structure and displacement required")


@dataclass(frozen=True, slots=True)
class CognitiveAssessment:
    as_of: datetime
    session: SessionId
    decision: CognitiveDecision | None
    state: str
    causal_closed_m1_count: int
    verified_htf: tuple[str, ...]
    source_pool_count: int
    structure_shift_detected: bool
    missing: tuple[str, ...]
    research_only: bool = True
    trade_authorized: bool = False


def _ny_day(value: datetime):
    return utc(value).astimezone(NEW_YORK).date()


def _ohlc_bucket(
    closed: tuple[M1Bar, ...], minutes: int
) -> tuple[tuple[datetime, Decimal, Decimal, Decimal], ...]:
    """Never aggregate incomplete HTF candles or bars crossing UTC buckets."""
    buckets: dict[datetime, list[M1Bar]] = defaultdict(list)
    step_seconds = minutes * 60
    for bar in closed:
        epoch = int(utc(bar.opened_at).timestamp())
        bucket_epoch = (epoch // step_seconds) * step_seconds
        key = datetime.fromtimestamp(bucket_epoch, tz=UTC)
        buckets[key].append(bar)
    confirmed: list[tuple[datetime, Decimal, Decimal, Decimal]] = []
    for opened, rows in sorted(buckets.items()):
        ordered = sorted(rows, key=lambda b: utc(b.opened_at))
        if len(ordered) != minutes:
            continue
        if any(
            utc(bar.opened_at) != opened + timedelta(minutes=i)
            for i, bar in enumerate(ordered)
        ):
            continue
        end = opened + timedelta(minutes=minutes)
        if utc(ordered[-1].closed_at) != end:
            continue
        confirmed.append((
            end,
            max(item.high for item in ordered),
            min(item.low for item in ordered),
            ordered[-1].close,
        ))
    return tuple(confirmed)


def _htf_context(
    closed: tuple[M1Bar, ...],
) -> tuple[tuple[str, ...], dict[str, str]]:
    seen: list[str] = []
    state: dict[str, str] = {}
    for interval, label in ((15, "M15"), (60, "H1"), (240, "H4")):
        candles = _ohlc_bucket(closed, interval)
        if len(candles) < 2:
            state[label] = "NOT_EVALUABLE"
            continue
        now, prior = candles[-1], candles[-2]
        latest_close = utc(closed[-1].closed_at)
        # An H1 completed Friday cannot masquerade as current H1
        # during Tuesday's market; no carrying stale HTF as "observed".
        max_age = timedelta(minutes=interval * 2)
        if latest_close - now[0] > max_age:
            state[label] = "STALE"
            continue
        # Transparent market-only two-close directional diagnostic, not
        # an invented categorical trade permission.
        direction = (
            "BULLISH" if now[3] > prior[3]
            else "BEARISH" if now[3] < prior[3] else "FLAT"
        )
        state[label] = direction
        seen.append(label)
    return tuple(seen), state


def _range_pool(
    *,
    bars: tuple[M1Bar, ...],
    name: str,
    minimum_bars: int,
) -> tuple[LiquidityPool, LiquidityPool] | None:
    if len(bars) < minimum_bars:
        return None
    ordered = sorted(bars, key=lambda b: utc(b.opened_at))
    if len({utc(b.opened_at) for b in ordered}) != len(ordered):
        raise ValueError("overlapping pool M1 timestamps")
    if any(
        utc(left.closed_at) != utc(right.opened_at)
        for left, right in zip(ordered, ordered[1:], strict=False)
    ):
        # An incomplete source must NEVER masquerade as its genuine extreme.
        return None
    confirmed = utc(ordered[-1].closed_at)
    source_start = utc(ordered[0].opened_at)
    source_end = confirmed
    return (
        LiquidityPool(
            name + "_HIGH", Side.LONG, max(b.high for b in ordered),
            confirmed, source_start, source_end,
        ),
        LiquidityPool(
            name + "_LOW", Side.SHORT, min(b.low for b in ordered),
            confirmed, source_start, source_end,
        ),
    )


def _verified_pools(
    closed: tuple[M1Bar, ...], as_of: datetime, session: SessionId
) -> tuple[LiquidityPool, ...]:
    """Source pools must be fully in the past at as_of; no current-day high
    may be passed off as a completed prior-day high.
    """
    local_day = _ny_day(as_of)
    candidates: list[LiquidityPool] = []
    previous_days = sorted({
        _ny_day(b.opened_at) for b in closed
        if _ny_day(b.opened_at) < local_day
    })
    if previous_days:
        prior = previous_days[-1]
        # Previous *full NY cash session* only (09:30-16:00 New York).
        # A partial 3-hour bar sample cannot truthfully be called PDH/PDL.
        # Wider ICT daily dealing-range provenance must be designed and
        # certified separately rather than mislabelled by this producer.
        cash_bars = tuple(
            b for b in closed
            if _ny_day(b.opened_at) == prior
            and (
                9 * 60 + 30
                <= (
                    utc(b.opened_at).astimezone(NEW_YORK).hour * 60
                    + utc(b.opened_at).astimezone(NEW_YORK).minute
                ) < 16 * 60
            )
        )
        if len(cash_bars) == 390:
            first_local = utc(cash_bars[0].opened_at).astimezone(NEW_YORK)
            final_local = utc(cash_bars[-1].opened_at).astimezone(NEW_YORK)
            if (
                (first_local.hour, first_local.minute) == (9, 30)
                and (final_local.hour, final_local.minute) == (15, 59)
                and utc(as_of) - utc(cash_bars[-1].closed_at)
                <= timedelta(days=5)
            ):
                pair = _range_pool(
                    bars=cash_bars, name="PRIOR_NY_CASH_SESSION",
                    minimum_bars=390,
                )
                if pair:
                    candidates.extend(pair)

    def add_local_window(family: str, start_hour: int, end_hour: int) -> None:
        window_bars = tuple(
            b for b in closed
            if _ny_day(b.opened_at) == local_day
            and start_hour <= utc(b.opened_at).astimezone(NEW_YORK).hour < end_hour
        )
        # Never call a partially forming range a frozen source pool.
        if len(window_bars) != (end_hour - start_hour) * 60:
            return
        first = utc(window_bars[0].opened_at).astimezone(NEW_YORK)
        last = utc(window_bars[-1].opened_at).astimezone(NEW_YORK)
        if (
            (first.hour, first.minute) != (start_hour, 0)
            or (last.hour, last.minute) != (end_hour - 1, 59)
        ):
            return
        pair = _range_pool(
            bars=window_bars, name=family,
            minimum_bars=(end_hour - start_hour) * 60,
        )
        if pair:
            candidates.extend(pair)

    add_local_window("ASIA_NY_CLOCK", *ASIA_WINDOW)
    if session in (SessionId.NY_AM, SessionId.NY_PM):
        add_local_window("LONDON_NY_CLOCK", *LONDON_EARLY_WINDOW)
    def still_available(pool: LiquidityPool) -> bool:
        if utc(pool.confirmed_at) > utc(as_of):
            return False
        # A level traded through after it was first confirmed is mitigated.
        # Reversion back below a swept high does not resurrect that DOL.
        return not any(
            utc(bar.opened_at) >= utc(pool.confirmed_at)
            and utc(bar.closed_at) <= utc(as_of)
            and (
                bar.high >= pool.level
                if pool.side is Side.LONG else bar.low <= pool.level
            )
            for bar in closed
        )

    return tuple(pool for pool in candidates if still_available(pool))


def _confirmed_break(
    closed: tuple[M1Bar, ...],
) -> CausalSwingBreak | None:
    """Strict local pivot confirmed by the following CLOSED candle.

    A shift fires only when the final M1 CLOSE crosses an already confirmed
    pivot in the appropriate direction, with a recorded body-displacement.
    """
    if len(closed) < 10:
        return None
    candles = closed[-95:]
    current = candles[-1]
    previous = candles[-2]
    if utc(previous.closed_at) != utc(current.opened_at):
        return None
    reference = median(
        [abs(b.close - b.open) for b in candles[-7:-2]]
    )
    if reference <= 0:
        return None
    body = abs(current.close - current.open)
    # Research-only displacement/impulse threshold; no retroactive fitting.
    if body < reference * Decimal("1.25"):
        return None
    for i in range(len(candles) - 3, 0, -1):
        left, pivot, right = candles[i - 1:i + 2]
        if (
            utc(left.closed_at) != utc(pivot.opened_at)
            or utc(pivot.closed_at) != utc(right.opened_at)
        ):
            continue
        confirmed_at = utc(right.closed_at)
        if confirmed_at >= utc(current.closed_at):
            continue
        if (
            pivot.high > left.high
            and pivot.high > right.high
            and previous.close <= pivot.high < current.close
            and current.close > current.open
        ):
            return CausalSwingBreak(
                Side.LONG, pivot.high, confirmed_at,
                utc(current.closed_at), body, reference,
            )
        if (
            pivot.low < left.low
            and pivot.low < right.low
            and previous.close >= pivot.low > current.close
            and current.close < current.open
        ):
            return CausalSwingBreak(
                Side.SHORT, pivot.low, confirmed_at,
                utc(current.closed_at), body, reference,
            )
    return None


class VT31CleanroomCognition:
    """Single persistent market memory shared by both VT31 session models."""

    def __init__(self, *, max_m1_history: int = 22000) -> None:
        if max_m1_history < 1440:
            raise ValueError("require enough history for prior session context")
        self._history: deque[M1Bar] = deque(maxlen=max_m1_history)
        self.latest_assessment: CognitiveAssessment | None = None

    def observe_closed_m1(self, bar: M1Bar) -> None:
        if not isinstance(bar, M1Bar):
            raise ValueError("requires validated cleanroom M1Bar")
        if self._history and utc(bar.opened_at) < utc(self._history[-1].closed_at):
            raise ValueError("duplicate/overlapping/out-of-order M1")
        self._history.append(bar)

    def assess(
        self, *, session: SessionId, as_of: datetime
    ) -> CognitiveAssessment:
        at = utc(as_of)
        if not isinstance(session, SessionId):
            raise ValueError("no unknown or dynamically registered sessions")
        if not self._history or utc(self._history[-1].closed_at) != at:
            raise ValueError("cognition must evaluate exactly latest closed M1")
        begin, end = window_bounds(at - timedelta(microseconds=1), session)
        if not begin < at <= end:
            raise ValueError("cognition outside its original ICT source window")
        closed = tuple(self._history)
        if any(utc(b.closed_at) > at for b in closed):
            raise AssertionError("future M1 in frozen cognition")
        verified, htf = _htf_context(closed)
        pools = _verified_pools(closed, at, session)
        shift = _confirmed_break(closed)
        missing: list[str] = []
        if htf.get("H1") in {"NOT_EVALUABLE", "STALE"}:
            missing.append("H1_CLOSED_CONTEXT")
        if htf.get("M15") in {"NOT_EVALUABLE", "STALE"}:
            missing.append("M15_CLOSED_CONTEXT")
        if not pools:
            missing.append("LIQUIDITY_POOL")
        if shift is None:
            missing.append("CONFIRMED_DISPLACEMENT_MSS")
        decision: CognitiveDecision | None = None
        if not missing and shift is not None:
            last = closed[-1]
            # A market-origin draw must be a confirmed *future destination*
            # in the breakout direction, not whichever past level eventually
            # paid out after the trade ended.
            eligible = sorted(
                (
                    p for p in pools
                    if p.side is shift.side
                    and (
                        p.level >= last.close + MIN_INDEX_POINTS
                        if shift.side is Side.LONG
                        else p.level <= last.close - MIN_INDEX_POINTS
                    )
                ),
                key=lambda p: (
                    abs(p.level - last.close), p.family,
                    utc(p.confirmed_at),
                ),
            )
            if eligible:
                target = eligible[0]
                decision = CognitiveDecision(
                    session=session,
                    side=shift.side,
                    observed_at=at,
                    draw_target=target.level,
                    draw_family=target.family,
                    draw_level_observed_at=target.confirmed_at,
                    structure_level=shift.level,
                    structure_level_confirmed_at=shift.pivot_confirmed_at,
                    structure_break_confirmed_at=shift.break_confirmed_at,
                    source_provenance=(
                        f"CLEANROOM_CLOSED_M1|{target.family}|"
                        f"MSS_PIVOT_CONFIRMED|"
                        f"BODY_1P25X_MEDIAN5|HTF_{','.join(verified)}"
                    ),
                    cognitive_version=VERSION,
                )
            else:
                missing.append("NO_CAUSAL_NEXT_DRAW_MIN10")
        status = (
            "CAUSAL_DRAW_AND_SHIFT_PROVEN" if decision is not None
            else "NO_VALID_CAUSAL_COGNITION"
        )
        result = CognitiveAssessment(
            as_of=at, session=session, decision=decision,
            state=status,
            causal_closed_m1_count=len(closed),
            verified_htf=verified,
            source_pool_count=len(pools),
            structure_shift_detected=shift is not None,
            missing=tuple(missing),
        )
        self.latest_assessment = result
        return result
