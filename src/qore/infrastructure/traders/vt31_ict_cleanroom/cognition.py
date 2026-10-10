"""One clean-room VT31 cognition for London and New York Silver Bullets.

Deliberately independent of every legacy VT31/COMP/TTrades module. Emits the
shared OPS CognitiveDecision only after independently causal closed-M1 DOL and
displacement-confirmed market-structure shift. No trading authority.

Causal policies below are explicit, *research-only* operational hypotheses,
not claims that ICT 2023 mandates these exact displacement/HTF thresholds.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, replace
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
    }, reverse=True)
    for prior in previous_days:
        # The last *completed NY cash session* may be Friday while Sunday
        # evening trades exist. Skip incomplete/weekend days; do not infer a
        # previous full daily candle from their partial M1 coverage.
        cash_bars = tuple(
            b for b in closed
            if _ny_day(b.opened_at) == prior
            and 9 * 60 + 30 <= (
                utc(b.opened_at).astimezone(NEW_YORK).hour * 60
                + utc(b.opened_at).astimezone(NEW_YORK).minute
            ) < 16 * 60
        )
        if len(cash_bars) != 390:
            continue
        first_local = utc(cash_bars[0].opened_at).astimezone(NEW_YORK)
        final_local = utc(cash_bars[-1].opened_at).astimezone(NEW_YORK)
        if (
            (first_local.hour, first_local.minute) != (9, 30)
            or (final_local.hour, final_local.minute) != (15, 59)
            or utc(as_of) - utc(cash_bars[-1].closed_at)
            > timedelta(days=5)
        ):
            continue
        pair = _range_pool(
            bars=cash_bars, name="PRIOR_NY_CASH_SESSION",
            minimum_bars=390,
        )
        if pair:
            candidates.extend(pair)
            break

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


class _OnlineCausalIndex:
    """Constant-work closed-M1 cache for real 3Y streaming replays.

    Every incremental fact is emitted ONLY once its entire source bar/window
    has closed. A missing M1 never manufactures a complete M15/H1/H4 or
    intra-session reference. Unswept pool membership is updated per M1.
    """

    def __init__(self) -> None:
        self._htf_active: dict[int, tuple[datetime, list[M1Bar]]] = {}
        self._htf_completed: dict[
            int, deque[tuple[datetime, Decimal, Decimal, Decimal]]
        ] = {i: deque(maxlen=2) for i in (15, 60, 240)}
        self._window_active: dict[
            str, tuple[object, list[M1Bar]]
        ] = {}
        self._available_pools: dict[str, LiquidityPool] = {}
        self._recent_mss: deque[M1Bar] = deque(maxlen=95)

    def observe(self, bar: M1Bar) -> None:
        opened = utc(bar.opened_at)
        closed_at = utc(bar.closed_at)
        self._recent_mss.append(bar)

        # Previously confirmed pools are invalid if any *later* completed M1
        # wicks through the corresponding liquidity. Never resurrect them.
        for key, pool in tuple(self._available_pools.items()):
            if (
                opened >= utc(pool.confirmed_at)
                and (
                    bar.high >= pool.level if pool.side is Side.LONG
                    else bar.low <= pool.level
                )
            ):
                del self._available_pools[key]

        for interval in (15, 60, 240):
            minute = opened.hour * 60 + opened.minute
            begin = opened - timedelta(minutes=minute % interval)
            old = self._htf_active.get(interval)
            if old is None or old[0] != begin:
                samples = [bar]
            else:
                samples = old[1]
                if samples[-1].closed_at != opened:
                    samples = [bar]
                else:
                    samples.append(bar)
            self._htf_active[interval] = (begin, samples)
            if (
                len(samples) == interval
                and utc(samples[0].opened_at) == begin
                and closed_at == begin + timedelta(minutes=interval)
            ):
                self._htf_completed[interval].append((
                    closed_at,
                    max(row.high for row in samples),
                    min(row.low for row in samples),
                    samples[-1].close,
                ))

        local = opened.astimezone(NEW_YORK)
        minute = local.hour * 60 + local.minute
        source: tuple[str, int, int] | None = None
        if 0 <= minute < 180:
            source = ("ASIA_NY_CLOCK", 0, 180)
        elif 180 <= minute < 300:
            source = ("LONDON_NY_CLOCK", 180, 300)
        elif 570 <= minute < 960:
            source = ("PRIOR_NY_CASH_SESSION", 570, 960)
        if source is None:
            return
        family, first_minute, last_minute = source
        day = local.date()
        old_source = self._window_active.get(family)
        if old_source is None or old_source[0] != day:
            observed = [bar]
        else:
            observed = old_source[1]
            if utc(observed[-1].closed_at) != opened:
                observed = [bar]
            else:
                observed.append(bar)
        self._window_active[family] = (day, observed)
        if minute != last_minute - 1:
            return
        if len(observed) != last_minute - first_minute:
            return
        first_local = utc(observed[0].opened_at).astimezone(NEW_YORK)
        if first_local.hour * 60 + first_local.minute != first_minute:
            return
        pair = _range_pool(
            bars=tuple(observed), name=family,
            minimum_bars=last_minute - first_minute,
        )
        if pair is not None:
            for pool in pair:
                self._available_pools[pool.family] = pool

    def context(
        self, as_of: datetime
    ) -> tuple[tuple[str, ...], dict[str, str]]:
        at = utc(as_of)
        names: list[str] = []
        states: dict[str, str] = {}
        for interval, label in ((15, "M15"), (60, "H1"), (240, "H4")):
            candles = self._htf_completed[interval]
            if len(candles) < 2:
                states[label] = "NOT_EVALUABLE"
                continue
            previous, latest = candles[-2], candles[-1]
            if at - latest[0] > timedelta(minutes=interval * 2):
                states[label] = "STALE"
                continue
            states[label] = (
                "BULLISH" if latest[3] > previous[3]
                else "BEARISH" if latest[3] < previous[3]
                else "FLAT"
            )
            names.append(label)
        return tuple(names), states

    def pools(
        self, as_of: datetime, session: SessionId
    ) -> tuple[LiquidityPool, ...]:
        at = utc(as_of)
        local_day = _ny_day(at)
        pools: list[LiquidityPool] = []
        for pool in self._available_pools.values():
            if pool.confirmed_at > at:
                continue
            source_day = _ny_day(pool.source_start)
            if pool.family.startswith("PRIOR_NY_CASH_SESSION"):
                if source_day >= local_day:
                    continue
                if at - pool.confirmed_at > timedelta(days=5):
                    continue
            elif pool.family.startswith("ASIA_NY_CLOCK"):
                if source_day != local_day:
                    continue
            elif pool.family.startswith("LONDON_NY_CLOCK"):
                if session not in (SessionId.NY_AM, SessionId.NY_PM):
                    continue
                if source_day != local_day:
                    continue
            else:
                raise ValueError("unrecognized cleanroom liquidity family")
            pools.append(pool)
        return tuple(pools)

    def shift(self) -> CausalSwingBreak | None:
        return _confirmed_break(tuple(self._recent_mss))


class VT31CleanroomCognition:
    """Single persistent market memory shared by both VT31 session models."""

    def __init__(self, *, max_m1_history: int = 22000) -> None:
        if max_m1_history < 1440:
            raise ValueError("require enough history for prior session context")
        self._history: deque[M1Bar] = deque(maxlen=max_m1_history)
        self._index = _OnlineCausalIndex()
        self._observed_count = 0
        # Single-trader M1 thesis by NY-date/ICT source-window, NOT another
        # trader/memory. Subsequent FVG candles may follow the confirmed MSS.
        self._active_m1_mss: dict[
            tuple[object, SessionId], CognitiveDecision
        ] = {}
        self.latest_assessment: CognitiveAssessment | None = None

    def observe_closed_m1(self, bar: M1Bar) -> None:
        if not isinstance(bar, M1Bar):
            raise ValueError("requires validated cleanroom M1Bar")
        if self._history and utc(bar.opened_at) < utc(self._history[-1].closed_at):
            raise ValueError("duplicate/overlapping/out-of-order M1")
        self._history.append(bar)
        self._index.observe(bar)
        self._observed_count += 1

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
        # O(1) indexed facts; no tuple(22k-history) and no three full
        # M15/H1/H4 repartitions for each of ~137k Silver Bullet M1.
        verified, htf = self._index.context(at)
        pools = self._index.pools(at, session)
        shift = self._index.shift()
        source_day_key = (_ny_day(at - timedelta(microseconds=1)), session)
        active = self._active_m1_mss.get(source_day_key)
        # Source month/day/window + confirmed DOL + pivot are immutable,
        # but their continued validity is NOT: a later bar may consume the
        # target or close back through the broken M1 pivot.
        if active is not None:
            same_dol_still_unswept = any(
                pool.family == active.draw_family
                and pool.level == active.draw_target
                and pool.confirmed_at == active.draw_level_observed_at
                for pool in pools
            )
            current_close = self._history[-1].close
            pivot_survived = (
                current_close > active.structure_level
                if active.side is Side.LONG
                else current_close < active.structure_level
            )
            new_opposite_shift = (
                shift is not None and shift.side is not active.side
            )
            if (
                not same_dol_still_unswept
                or not pivot_survived
                or new_opposite_shift
            ):
                del self._active_m1_mss[source_day_key]
                active = None
        missing: list[str] = []
        if htf.get("H1") in {"NOT_EVALUABLE", "STALE"}:
            missing.append("H1_CLOSED_CONTEXT")
        if htf.get("M15") in {"NOT_EVALUABLE", "STALE"}:
            missing.append("M15_CLOSED_CONTEXT")
        if not pools:
            missing.append("LIQUIDITY_POOL")
        if shift is None and active is None:
            missing.append("CONFIRMED_DISPLACEMENT_MSS")
        # A current observed M1 MSS can refresh a thesis. A prior already
        # confirmed M1 MSS can persist only under revalidated DOL/pivot,
        # not as a stale no-longer-true duplicate break.
        decision: CognitiveDecision | None = None
        if not missing and shift is not None:
            last = self._history[-1]
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
                self._active_m1_mss[source_day_key] = decision
            else:
                missing.append("NO_CAUSAL_NEXT_DRAW_MIN10")
        elif not missing and active is not None:
            decision = replace(
                active,
                observed_at=at,
                source_provenance=(
                    active.source_provenance.split("|M1_MSS_REVALIDATED")[0]
                    + "|M1_MSS_REVALIDATED_AT_EACH_CLOSED_M1"
                ),
            )
        # An opposite shift or exhausted draw never resurrects yesterday's
        # thesis; it remains absent until another current M1 MSS proves one.
        status = (
            "CAUSAL_DRAW_AND_SHIFT_PROVEN" if decision is not None
            else "NO_VALID_CAUSAL_COGNITION"
        )
        result = CognitiveAssessment(
            as_of=at, session=session, decision=decision,
            state=status,
            causal_closed_m1_count=self._observed_count,
            verified_htf=verified,
            source_pool_count=len(pools),
            structure_shift_detected=shift is not None,
            missing=tuple(missing),
        )
        self.latest_assessment = result
        return result
