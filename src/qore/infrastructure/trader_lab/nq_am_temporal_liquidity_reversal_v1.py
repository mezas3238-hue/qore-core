"""QORE NQ AM Temporal Liquidity Reversal V1.

Research-only mechanical translation of the NQ AM-session operation reviewed in
YouTube video UVVmS0de0g0.  The implementation is deliberately causal: it can
only use bars whose close is available at the decision timestamp.  It never
labels or consumes the final low of day at entry time.

V1 is LONG-only and uses cTrader DEMO NAS100 CFD as the repository-available
research instrument.  NAS100 CFD is not exchange NQ futures; the evidence
identity records that limitation explicitly.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from statistics import mean
from time import sleep
from typing import Any, cast
from zoneinfo import ZoneInfo

from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    Evidence,
    _max_drawdown,
    _native_int,
    _price,
    _profit_factor,
    _required_env,
)
from qore.kernel.result import Failure

IDENTITY = "QORE_NQ_AM_TEMPORAL_LIQUIDITY_REVERSAL_V1"
SOURCE_VIDEO_ID = "UVVmS0de0g0"
SOURCE_OPERATION = "NQ_AM_SESSION_LOW_OF_DAY_LONG_REVIEW"
SYMBOL = "NAS100"
PROVIDER_SYMBOL = "USTEC"
PROVIDER = "ctrader-demo"
INSTRUMENT_CLASS = "CFD_INDEX_NOT_EXCHANGE_NQ_FUTURES"

NY = ZoneInfo("America/New_York")
M1 = timedelta(minutes=1)
RTH_OPEN = time(9, 30)
RTH_SETTLE_BAR = time(16, 14)
EARLY_GAP_END = time(9, 35)
MACRO_FIRST_HALF_OPEN = time(10, 50)
MACRO_FIRST_HALF_CLOSE = time(11, 0)
MACRO_CLOSE = time(11, 10)
AM_EXPIRY = time(12, 0)

PRIOR_REFERENCE_LOOKBACK = 5
FVG_LOOKBACK_MINUTES = 60
PRIMARY_FRICTION_R = Decimal("0.05")
STRESS_FRICTION_R = Decimal("0.10")
BOOTSTRAP_SEED = 20260928

DEV_EVIDENCE_ID = "NQ_AM_TLR_V1_CONSUMED_DEV_2024_08_13_2025_08_13"
DEV_EVAL_OPEN_NY = date(2024, 8, 13)
DEV_EVAL_CLOSE_NY = date(2025, 8, 13)
DEV_ACQUISITION_OPEN = datetime(2024, 7, 29, 0, tzinfo=UTC)
DEV_ACQUISITION_CLOSE = datetime(2025, 8, 14, 23, 59, tzinfo=UTC)

PAGE_COUNT = 5000
CHUNK_DAYS = 3
REQUEST_PAUSE_SECONDS = 0.22


class Variant(StrEnum):
    FULL = "FULL"
    NO_MACRO = "NO_MACRO"
    NO_GAP_EXTENSION = "NO_GAP_EXTENSION"
    NO_IFVG = "NO_IFVG"
    NO_ACCEPTANCE_TEST = "NO_ACCEPTANCE_TEST"
    NO_RTH_GAP_CONTEXT = "NO_RTH_GAP_CONTEXT"


@dataclass(frozen=True, slots=True)
class RthSession:
    ny_day: date
    open_at: datetime
    settle_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    settle: Decimal
    bars: tuple[Bar, ...]


@dataclass(frozen=True, slots=True)
class BearishFvg:
    created_at: datetime
    low: Decimal
    high: Decimal

    @property
    def midpoint(self) -> Decimal:
        return (self.low + self.high) / Decimal(2)


@dataclass(frozen=True, slots=True)
class Trade:
    ny_day: date
    variant: str
    entry_at: datetime
    exit_at: datetime
    reference_day: date
    reference_low: Decimal
    gap: Decimal
    gap_lower_octant: Decimal
    gap_lower_quadrant: Decimal
    gap_extension_2: Decimal
    sweep_at: datetime
    sweep_low: Decimal
    ifvg_created_at: datetime | None
    ifvg_low: Decimal | None
    ifvg_high: Decimal | None
    entry: Decimal
    stop: Decimal
    target: Decimal
    exit_price: Decimal
    gross_r: Decimal
    primary_net_r: Decimal
    stress_net_r: Decimal
    mfe_r: Decimal
    mae_r: Decimal
    exit_reason: str


@dataclass(frozen=True, slots=True)
class DayRecord:
    ny_day: date
    variant: str
    eligible: bool
    terminal_stage: str
    reason: str
    gap: Decimal | None
    reference_day: date | None
    reference_low: Decimal | None
    extension_2: Decimal | None
    sweep_at: datetime | None
    sweep_low: Decimal | None
    rejection_confirmed: bool
    ifvg_confirmed: bool
    entry_at: datetime | None
    false_bottom: bool
    trade: Trade | None


def _wall(moment: datetime) -> time:
    return moment.astimezone(NY).timetz().replace(tzinfo=None)


def _ny_day(moment: datetime) -> date:
    return moment.astimezone(NY).date()


def _at_ny(day: date, wall: time) -> datetime:
    return datetime.combine(day, wall, tzinfo=NY).astimezone(UTC)


def _tick_size(digits: int) -> Decimal:
    if digits <= 0:
        raise ValueError("digits must be positive")
    return Decimal(1).scaleb(-digits)


def _collect_m1(
    symbol_name: str,
    *,
    acquisition_open: datetime,
    acquisition_close: datetime,
) -> Evidence:
    credentials = CTraderOpenApiCredentials(
        client_id=_required_env(
            "QORE_CTRADER_CLIENT_ID", "QORE_CTRADER_DEMO_CLIENT_ID"
        ),
        client_secret=_required_env(
            "QORE_CTRADER_CLIENT_SECRET", "QORE_CTRADER_DEMO_CLIENT_SECRET"
        ),
        access_token=_required_env(
            "QORE_CTRADER_ACCESS_TOKEN", "QORE_CTRADER_DEMO_ACCESS_TOKEN"
        ),
        refresh_token=_required_env(
            "QORE_CTRADER_REFRESH_TOKEN", "QORE_CTRADER_DEMO_REFRESH_TOKEN"
        ),
        ctid_trader_account_id=int(
            _required_env("QORE_CTRADER_DEMO_ACCOUNT_ID", "QORE_CTRADER_ACCOUNT_ID")
        ),
    )
    client = SpotwareCTraderOpenApiClient(credentials=credentials)
    try:
        connected = client.connect_and_authenticate()
        if isinstance(connected, Failure):
            raise RuntimeError("cTrader DEMO authentication failed")
        account_id = client.account_id
        listed = client.request(
            "ProtoOASymbolsListReq",
            {"ctidTraderAccountId": account_id, "includeArchivedSymbols": False},
            client_msg_id="qore-nq-am-tlr-v1-symbol-list",
            timeout_seconds=30.0,
        )
        if isinstance(listed, Failure):
            raise RuntimeError("cTrader symbol list failed")
        native_symbols = tuple(
            cast(Iterable[object], getattr(listed.value, "symbol", ()))
        )
        selected = next(
            (
                item
                for item in native_symbols
                if getattr(item, "symbolName", None) == symbol_name
                and getattr(item, "enabled", None) is True
            ),
            None,
        )
        if selected is None:
            raise RuntimeError(f"symbol unavailable: {symbol_name}")
        symbol_id = _native_int(selected, "symbolId")
        details = client.request(
            "ProtoOASymbolByIdReq",
            {"ctidTraderAccountId": account_id, "symbolId": [symbol_id]},
            client_msg_id=f"qore-nq-am-tlr-v1-symbol:{symbol_id}",
            timeout_seconds=30.0,
        )
        if isinstance(details, Failure):
            raise RuntimeError("cTrader symbol details failed")
        detail = next(
            (
                item
                for item in cast(
                    Iterable[object], getattr(details.value, "symbol", ())
                )
                if getattr(item, "symbolId", None) == symbol_id
            ),
            None,
        )
        if detail is None:
            raise RuntimeError("exact symbol details missing")
        digits = _native_int(detail, "digits")

        retained: dict[datetime, Bar] = {}
        window_start = acquisition_open
        window_index = 0
        while window_start < acquisition_close:
            window_end = min(
                window_start + timedelta(days=CHUNK_DAYS), acquisition_close
            )
            sleep(REQUEST_PAUSE_SECONDS)
            response = client.request(
                "ProtoOAGetTrendbarsReq",
                {
                    "ctidTraderAccountId": account_id,
                    "count": PAGE_COUNT,
                    "fromTimestamp": int(window_start.timestamp() * 1000),
                    "period": 1,
                    "symbolId": symbol_id,
                    "toTimestamp": int(window_end.timestamp() * 1000),
                },
                client_msg_id=f"qore-nq-am-tlr-v1-m1:{symbol_id}:{window_index}",
                timeout_seconds=45.0,
            )
            if isinstance(response, Failure):
                raise RuntimeError("cTrader M1 historical read failed")
            natives = tuple(
                cast(Iterable[object], getattr(response.value, "trendbar", ()))
            )
            if len(natives) >= PAGE_COUNT and getattr(
                response.value, "hasMore", False
            ):
                raise RuntimeError("cTrader M1 chunk exceeded safe page bound")
            for native in natives:
                low_rel = _native_int(native, "low")
                opened = datetime.fromtimestamp(
                    _native_int(native, "utcTimestampInMinutes") * 60,
                    tz=UTC,
                )
                if not acquisition_open <= opened < acquisition_close:
                    continue
                bar = Bar(
                    opened_at=opened,
                    closed_at=opened + M1,
                    open=_price(low_rel + _native_int(native, "deltaOpen"), digits),
                    high=_price(low_rel + _native_int(native, "deltaHigh"), digits),
                    low=_price(low_rel, digits),
                    close=_price(low_rel + _native_int(native, "deltaClose"), digits),
                )
                previous = retained.get(opened)
                if previous is not None and previous != bar:
                    raise RuntimeError("contradictory historical M1 bar")
                retained[opened] = bar
            window_start = window_end
            window_index += 1

        bars = tuple(retained[key] for key in sorted(retained))
        if not bars:
            raise RuntimeError("no historical M1 evidence")
        if bars[0].opened_at > acquisition_open + timedelta(days=10):
            raise RuntimeError("provider history does not reach warm-up boundary")
        if bars[-1].closed_at < acquisition_close - timedelta(days=10):
            raise RuntimeError("provider history is stale at close boundary")
        return Evidence(symbol=SYMBOL, digits=digits, bars=bars)
    finally:
        client.close()


def evidence_payload(
    evidence: Evidence,
    *,
    evidence_id: str,
    acquisition_open: datetime,
    acquisition_close: datetime,
    eval_open_ny: date,
    eval_close_ny: date,
    evidence_status: str,
) -> dict[str, Any]:
    return {
        "schema": "qore.nq_am_temporal_liquidity_reversal.evidence.v1",
        "identity": IDENTITY,
        "source_video_id": SOURCE_VIDEO_ID,
        "evidence_id": evidence_id,
        "evidence_status": evidence_status,
        "provider": PROVIDER,
        "provider_symbol": PROVIDER_SYMBOL,
        "instrument_class": INSTRUMENT_CLASS,
        "acquisition_opened_at": acquisition_open.isoformat(),
        "acquisition_closed_at": acquisition_close.isoformat(),
        "evaluation_open_ny": eval_open_ny.isoformat(),
        "evaluation_close_ny": eval_close_ny.isoformat(),
        "symbol": {"symbol_name": evidence.symbol, "digits": evidence.digits},
        "periods": {
            "M1": [
                {
                    "opened_at": bar.opened_at.isoformat(),
                    "closed_at": bar.closed_at.isoformat(),
                    "open": str(bar.open),
                    "high": str(bar.high),
                    "low": str(bar.low),
                    "close": str(bar.close),
                }
                for bar in evidence.bars
            ]
        },
        "read_only": True,
    }


def load_evidence(path: Path) -> tuple[Evidence, dict[str, Any]]:
    payload = json.loads(path.read_text())
    if payload.get("identity") != IDENTITY:
        raise ValueError("unexpected candidate identity")
    if payload.get("read_only") is not True:
        raise ValueError("evidence must be read-only")
    symbol = str(payload["symbol"]["symbol_name"])
    if symbol != SYMBOL:
        raise ValueError("V1 is frozen to NAS100")
    digits = int(payload["symbol"]["digits"])
    raw = payload.get("periods", {}).get("M1")
    if not isinstance(raw, list) or not raw:
        raise ValueError("M1 evidence missing")
    bars = tuple(
        Bar(
            opened_at=datetime.fromisoformat(str(item["opened_at"])).astimezone(UTC),
            closed_at=datetime.fromisoformat(str(item["closed_at"])).astimezone(UTC),
            open=Decimal(str(item["open"])),
            high=Decimal(str(item["high"])),
            low=Decimal(str(item["low"])),
            close=Decimal(str(item["close"])),
        )
        for item in raw
    )
    return Evidence(symbol=symbol, digits=digits, bars=bars), payload


def build_rth_sessions(bars: Sequence[Bar]) -> tuple[RthSession, ...]:
    by_day: dict[date, list[Bar]] = {}
    for bar in bars:
        wall = _wall(bar.opened_at)
        if RTH_OPEN <= wall <= RTH_SETTLE_BAR:
            by_day.setdefault(_ny_day(bar.opened_at), []).append(bar)
    sessions: list[RthSession] = []
    for day, raw in sorted(by_day.items()):
        ordered = tuple(sorted(raw, key=lambda item: item.opened_at))
        open_at = _at_ny(day, RTH_OPEN)
        settle_at = _at_ny(day, RTH_SETTLE_BAR)
        opening = next((item for item in ordered if item.opened_at == open_at), None)
        settlement = next(
            (item for item in ordered if item.opened_at == settle_at), None
        )
        if opening is None or settlement is None:
            continue
        sessions.append(
            RthSession(
                ny_day=day,
                open_at=open_at,
                settle_at=settle_at,
                open=opening.open,
                high=max(item.high for item in ordered),
                low=min(item.low for item in ordered),
                settle=settlement.close,
                bars=ordered,
            )
        )
    return tuple(sessions)


def _bars_between(
    bars: Sequence[Bar], start: datetime, end: datetime
) -> tuple[Bar, ...]:
    return tuple(item for item in bars if start <= item.opened_at < end)


def _daily_context_bullish(previous: RthSession, current: RthSession) -> bool:
    midpoint = (previous.high + previous.low) / Decimal(2)
    return previous.settle >= midpoint and previous.high > current.open


def _untouched_sellside_reference(
    sessions: Sequence[RthSession],
    index: int,
    all_bars: Sequence[Bar],
) -> tuple[RthSession, Decimal] | None:
    current = sessions[index]
    candidates: list[tuple[RthSession, Decimal]] = []
    for prior in sessions[max(0, index - PRIOR_REFERENCE_LOOKBACK) : index]:
        if prior.low >= current.open:
            continue
        touched = any(
            item.low <= prior.low
            for item in all_bars
            if prior.settle_at + M1 <= item.opened_at < current.open_at
        )
        if not touched:
            candidates.append((prior, prior.low))
    if not candidates:
        return None
    # Nearest still-untouched sell-side pool below the 09:30 open.
    return max(candidates, key=lambda item: item[1])


def _bearish_fvgs(
    bars: Sequence[Bar],
    *,
    start: datetime,
    end: datetime,
) -> tuple[BearishFvg, ...]:
    sample = tuple(item for item in bars if start <= item.opened_at < end)
    result: list[BearishFvg] = []
    for index in range(2, len(sample)):
        first = sample[index - 2]
        third = sample[index]
        if third.high < first.low:
            result.append(
                BearishFvg(
                    created_at=third.closed_at,
                    low=third.high,
                    high=first.low,
                )
            )
    return tuple(result)


def _ifvg_entry(
    bars: Sequence[Bar],
    *,
    sweep_at: datetime,
    deadline: datetime,
) -> tuple[BearishFvg, datetime, Decimal] | None:
    lookback = sweep_at - timedelta(minutes=FVG_LOOKBACK_MINUTES)
    zones = _bearish_fvgs(bars, start=lookback, end=sweep_at + M1)
    if not zones:
        return None
    after = tuple(
        item for item in bars if sweep_at <= item.opened_at < deadline
    )
    # Prefer the most recently created bearish imbalance from the delivery leg.
    for zone in reversed(zones):
        inversion_index = next(
            (
                idx
                for idx, bar in enumerate(after)
                if bar.close > zone.high
            ),
            None,
        )
        if inversion_index is None:
            continue
        for bar in after[inversion_index:]:
            overlaps = bar.low <= zone.high and bar.high >= zone.low
            if overlaps and bar.close >= zone.midpoint:
                return zone, bar.closed_at, bar.close
    return None


def _simulate(
    bars: Sequence[Bar],
    *,
    entry_at: datetime,
    expiry: datetime,
    entry: Decimal,
    stop: Decimal,
    target: Decimal,
) -> tuple[datetime, Decimal, str, Decimal, Decimal, Decimal]:
    risk = entry - stop
    if risk <= 0 or target <= entry:
        raise ValueError("invalid long trade geometry")
    path = tuple(item for item in bars if entry_at <= item.opened_at < expiry)
    if not path:
        raise ValueError("empty post-entry path")
    max_high = entry
    min_low = entry
    for bar in path:
        max_high = max(max_high, bar.high)
        min_low = min(min_low, bar.low)
        if bar.open <= stop:
            gross = (bar.open - entry) / risk
            return (
                bar.opened_at,
                bar.open,
                "gap-stop",
                gross,
                max((max_high - entry) / risk, Decimal(0)),
                max((entry - min_low) / risk, Decimal(0)),
            )
        if bar.open >= target:
            gross = (target - entry) / risk
            return (
                bar.opened_at,
                target,
                "gap-target-capped",
                gross,
                max((max_high - entry) / risk, Decimal(0)),
                max((entry - min_low) / risk, Decimal(0)),
            )
        stop_touch = bar.low <= stop
        target_touch = bar.high >= target
        if stop_touch and target_touch:
            # M1 cannot prove intrabar path; fail conservative.
            gross = Decimal(-1)
            return (
                bar.closed_at,
                stop,
                "stop-first-collision",
                gross,
                max((max_high - entry) / risk, Decimal(0)),
                max((entry - min_low) / risk, Decimal(0)),
            )
        if stop_touch:
            return (
                bar.closed_at,
                stop,
                "stop",
                Decimal(-1),
                max((max_high - entry) / risk, Decimal(0)),
                max((entry - min_low) / risk, Decimal(0)),
            )
        if target_touch:
            gross = (target - entry) / risk
            return (
                bar.closed_at,
                target,
                "target-0930-open",
                gross,
                max((max_high - entry) / risk, Decimal(0)),
                max((entry - min_low) / risk, Decimal(0)),
            )
    final = path[-1]
    gross = (final.close - entry) / risk
    return (
        final.closed_at,
        final.close,
        "am-expiry",
        gross,
        max((max_high - entry) / risk, Decimal(0)),
        max((entry - min_low) / risk, Decimal(0)),
    )


def _false_bottom(
    bars: Sequence[Bar],
    *,
    start: datetime,
    expiry: datetime,
    sweep_low: Decimal,
    target: Decimal,
) -> bool:
    for bar in bars:
        if not start <= bar.opened_at < expiry:
            continue
        # If both occur in one M1 bar, count failure conservatively.
        if bar.low < sweep_low:
            return True
        if bar.high >= target:
            return False
    return False


def _day_record(
    current: RthSession,
    variant: Variant,
    *,
    terminal_stage: str,
    reason: str,
    eligible: bool = False,
    gap: Decimal | None = None,
    reference_day: date | None = None,
    reference_low: Decimal | None = None,
    extension_2: Decimal | None = None,
    sweep_at: datetime | None = None,
    sweep_low: Decimal | None = None,
    rejection_confirmed: bool = False,
    ifvg_confirmed: bool = False,
    entry_at: datetime | None = None,
    false_bottom: bool = False,
    trade: Trade | None = None,
) -> DayRecord:
    return DayRecord(
        ny_day=current.ny_day,
        variant=variant.value,
        eligible=eligible,
        terminal_stage=terminal_stage,
        reason=reason,
        gap=gap,
        reference_day=reference_day,
        reference_low=reference_low,
        extension_2=extension_2,
        sweep_at=sweep_at,
        sweep_low=sweep_low,
        rejection_confirmed=rejection_confirmed,
        ifvg_confirmed=ifvg_confirmed,
        entry_at=entry_at,
        false_bottom=false_bottom,
        trade=trade,
    )


def evaluate_day(
    evidence: Evidence,
    sessions: Sequence[RthSession],
    index: int,
    *,
    variant: Variant = Variant.FULL,
) -> DayRecord:
    current = sessions[index]
    previous = sessions[index - 1]
    tick = _tick_size(evidence.digits)

    if not _daily_context_bullish(previous, current):
        return _day_record(
            current,
            variant,
            terminal_stage="context",
            reason="daily-context-not-bullish",
        )

    gap = previous.settle - current.open
    if gap <= 0:
        return _day_record(
            current,
            variant,
            terminal_stage="gap",
            reason="not-gap-down",
        )

    lower_octant = current.open + gap / Decimal(8)
    lower_quadrant = current.open + gap / Decimal(4)
    extension_2 = current.open - Decimal(2) * gap
    early = _bars_between(
        evidence.bars,
        current.open_at,
        _at_ny(current.ny_day, EARLY_GAP_END),
    )
    if not early:
        return _day_record(
            current,
            variant,
            terminal_stage="data",
            reason="missing-early-rth-bars",
        )
    if variant is not Variant.NO_RTH_GAP_CONTEXT:
        if max(item.high for item in early) >= lower_quadrant:
            return _day_record(
                current,
                variant,
                terminal_stage="gap-repair",
                reason="lower-quadrant-repaired",
                eligible=True,
                gap=gap,
                extension_2=extension_2,
            )
        if max(item.close for item in early) >= lower_octant:
            return _day_record(
                current,
                variant,
                terminal_stage="gap-repair",
                reason="lowest-octant-body-accepted",
                eligible=True,
                gap=gap,
                extension_2=extension_2,
            )

    reference = _untouched_sellside_reference(sessions, index, evidence.bars)
    if reference is None:
        return _day_record(
            current,
            variant,
            terminal_stage="liquidity",
            reason="no-untouched-prior-rth-low",
            eligible=True,
            gap=gap,
            extension_2=extension_2,
        )
    ref_session, ref_low = reference

    if variant is not Variant.NO_GAP_EXTENSION:
        if abs(ref_low - extension_2) > gap / Decimal(8):
            return _day_record(
                current,
                variant,
                terminal_stage="confluence",
                reason="sellside-not-within-2sd-octant",
                eligible=True,
                gap=gap,
                reference_day=ref_session.ny_day,
                reference_low=ref_low,
                extension_2=extension_2,
            )

    macro_open = _at_ny(current.ny_day, MACRO_FIRST_HALF_OPEN)
    first_half_close = _at_ny(current.ny_day, MACRO_FIRST_HALF_CLOSE)
    sweep_search_open = (
        _at_ny(current.ny_day, EARLY_GAP_END)
        if variant is Variant.NO_MACRO
        else macro_open
    )

    if variant is not Variant.NO_MACRO:
        pre_macro = _bars_between(evidence.bars, current.open_at, macro_open)
        if any(item.low < ref_low for item in pre_macro):
            return _day_record(
                current,
                variant,
                terminal_stage="timing",
                reason="sellside-swept-before-macro",
                eligible=True,
                gap=gap,
                reference_day=ref_session.ny_day,
                reference_low=ref_low,
                extension_2=extension_2,
            )

    sweep_window = _bars_between(evidence.bars, sweep_search_open, first_half_close)
    sweep = next((item for item in sweep_window if item.low < ref_low), None)
    if sweep is None:
        return _day_record(
            current,
            variant,
            terminal_stage="sweep",
            reason="no-sellside-sweep",
            eligible=True,
            gap=gap,
            reference_day=ref_session.ny_day,
            reference_low=ref_low,
            extension_2=extension_2,
        )

    after_sweep_first_half = tuple(
        item for item in sweep_window if item.opened_at >= sweep.opened_at
    )
    sweep_low = min(item.low for item in after_sweep_first_half)
    acceptance_floor = max(ref_low, extension_2)
    rejection = all(
        item.close > acceptance_floor for item in after_sweep_first_half
    )
    if variant is not Variant.NO_ACCEPTANCE_TEST and not rejection:
        return _day_record(
            current,
            variant,
            terminal_stage="acceptance",
            reason="body-accepted-below-reference-or-2sd",
            eligible=True,
            gap=gap,
            reference_day=ref_session.ny_day,
            reference_low=ref_low,
            extension_2=extension_2,
            sweep_at=sweep.opened_at,
            sweep_low=sweep_low,
        )

    deadline = _at_ny(current.ny_day, MACRO_CLOSE)
    zone: BearishFvg | None
    if variant is Variant.NO_IFVG:
        entry_bar = next(
            (
                item
                for item in evidence.bars
                if first_half_close <= item.opened_at < deadline
                and item.close > acceptance_floor
            ),
            None,
        )
        if entry_bar is None:
            return _day_record(
                current,
                variant,
                terminal_stage="entry",
                reason="no-post-rejection-entry-bar",
                eligible=True,
                gap=gap,
                reference_day=ref_session.ny_day,
                reference_low=ref_low,
                extension_2=extension_2,
                sweep_at=sweep.opened_at,
                sweep_low=sweep_low,
                rejection_confirmed=rejection,
            )
        zone = None
        entry_at = entry_bar.closed_at
        entry_price = entry_bar.close
    else:
        ifvg = _ifvg_entry(
            evidence.bars,
            sweep_at=sweep.opened_at,
            deadline=deadline,
        )
        if ifvg is None:
            false_bottom = _false_bottom(
                evidence.bars,
                start=first_half_close,
                expiry=_at_ny(current.ny_day, AM_EXPIRY),
                sweep_low=sweep_low,
                target=current.open,
            )
            return _day_record(
                current,
                variant,
                terminal_stage="ifvg",
                reason="no-causal-ifvg-inversion-entry",
                eligible=True,
                gap=gap,
                reference_day=ref_session.ny_day,
                reference_low=ref_low,
                extension_2=extension_2,
                sweep_at=sweep.opened_at,
                sweep_low=sweep_low,
                rejection_confirmed=rejection,
                false_bottom=false_bottom,
            )
        zone, entry_at, entry_price = ifvg

    stop = sweep_low - tick
    target = current.open
    if entry_price <= stop:
        return _day_record(
            current,
            variant,
            terminal_stage="geometry",
            reason="entry-through-structural-stop",
            eligible=True,
            gap=gap,
            reference_day=ref_session.ny_day,
            reference_low=ref_low,
            extension_2=extension_2,
            sweep_at=sweep.opened_at,
            sweep_low=sweep_low,
            rejection_confirmed=rejection,
            ifvg_confirmed=zone is not None,
            entry_at=entry_at,
        )
    if target <= entry_price:
        return _day_record(
            current,
            variant,
            terminal_stage="geometry",
            reason="entry-at-or-above-0930-open",
            eligible=True,
            gap=gap,
            reference_day=ref_session.ny_day,
            reference_low=ref_low,
            extension_2=extension_2,
            sweep_at=sweep.opened_at,
            sweep_low=sweep_low,
            rejection_confirmed=rejection,
            ifvg_confirmed=zone is not None,
            entry_at=entry_at,
        )

    expiry = _at_ny(current.ny_day, AM_EXPIRY)
    exit_at, exit_price, exit_reason, gross_r, mfe_r, mae_r = _simulate(
        evidence.bars,
        entry_at=entry_at,
        expiry=expiry,
        entry=entry_price,
        stop=stop,
        target=target,
    )
    trade = Trade(
        ny_day=current.ny_day,
        variant=variant.value,
        entry_at=entry_at,
        exit_at=exit_at,
        reference_day=ref_session.ny_day,
        reference_low=ref_low,
        gap=gap,
        gap_lower_octant=lower_octant,
        gap_lower_quadrant=lower_quadrant,
        gap_extension_2=extension_2,
        sweep_at=sweep.opened_at,
        sweep_low=sweep_low,
        ifvg_created_at=None if zone is None else zone.created_at,
        ifvg_low=None if zone is None else zone.low,
        ifvg_high=None if zone is None else zone.high,
        entry=entry_price,
        stop=stop,
        target=target,
        exit_price=exit_price,
        gross_r=gross_r,
        primary_net_r=gross_r - PRIMARY_FRICTION_R,
        stress_net_r=gross_r - STRESS_FRICTION_R,
        mfe_r=mfe_r,
        mae_r=mae_r,
        exit_reason=exit_reason,
    )
    false_bottom = _false_bottom(
        evidence.bars,
        start=entry_at,
        expiry=expiry,
        sweep_low=sweep_low,
        target=target,
    )
    return _day_record(
        current,
        variant,
        terminal_stage="trade",
        reason="trade",
        eligible=True,
        gap=gap,
        reference_day=ref_session.ny_day,
        reference_low=ref_low,
        extension_2=extension_2,
        sweep_at=sweep.opened_at,
        sweep_low=sweep_low,
        rejection_confirmed=rejection,
        ifvg_confirmed=zone is not None,
        entry_at=entry_at,
        false_bottom=false_bottom,
        trade=trade,
    )

def replay(
    evidence: Evidence,
    *,
    eval_open_ny: date,
    eval_close_ny: date,
    variant: Variant = Variant.FULL,
) -> list[DayRecord]:
    sessions = build_rth_sessions(evidence.bars)
    records: list[DayRecord] = []
    for index in range(1, len(sessions)):
        day = sessions[index].ny_day
        if not eval_open_ny <= day < eval_close_ny:
            continue
        records.append(evaluate_day(evidence, sessions, index, variant=variant))
    return records


def _max_losing_streak(values: Sequence[Decimal]) -> int:
    best = current = 0
    for value in values:
        if value < 0:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def _month_key(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def _quarter_key(day: date) -> str:
    return f"{day.year:04d}-Q{((day.month - 1) // 3) + 1}"


def _bucket_trades(
    trades: Sequence[Trade], key_fn: Any
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[Trade]] = {}
    for trade in trades:
        grouped.setdefault(key_fn(trade.ny_day), []).append(trade)
    result: dict[str, dict[str, Any]] = {}
    for key, items in sorted(grouped.items()):
        primary = [item.primary_net_r for item in items]
        result[key] = {
            "trades": len(items),
            "total_r": str(sum(primary, Decimal(0))),
            "mean_r": str(sum(primary, Decimal(0)) / len(primary)),
            "wins": sum(value > 0 for value in primary),
            "losses": sum(value < 0 for value in primary),
        }
    return result


def _bootstrap_mean_ci(values: Sequence[Decimal]) -> tuple[str | None, str | None]:
    if not values:
        return None, None
    if len(values) == 1:
        value = str(values[0])
        return value, value
    rng = random.Random(BOOTSTRAP_SEED)
    estimates: list[float] = []
    raw = [float(item) for item in values]
    for _ in range(2000):
        sample = [rng.choice(raw) for _ in raw]
        estimates.append(mean(sample))
    estimates.sort()
    low = estimates[int(0.025 * (len(estimates) - 1))]
    high = estimates[int(0.975 * (len(estimates) - 1))]
    return f"{low:.9f}", f"{high:.9f}"


def summarize(records: Sequence[DayRecord]) -> dict[str, Any]:
    trades = sorted(
        (item.trade for item in records if item.trade is not None),
        key=lambda item: item.entry_at,
    )
    primary = [item.primary_net_r for item in trades]
    stress = [item.stress_net_r for item in trades]
    gross = [item.gross_r for item in trades]
    stages = Counter(item.terminal_stage for item in records)
    reasons = Counter(item.reason for item in records)
    setups = [item for item in records if item.rejection_confirmed]
    false_bottoms = [item for item in setups if item.false_bottom]
    low_ci, high_ci = _bootstrap_mean_ci(primary)
    return {
        "identity": IDENTITY,
        "source_video_id": SOURCE_VIDEO_ID,
        "variant": records[0].variant if records else Variant.FULL.value,
        "eligible_sessions": sum(item.eligible for item in records),
        "evaluated_sessions": len(records),
        "opportunity_count": sum(
            item.reference_low is not None and item.sweep_at is not None
            for item in records
        ),
        "setup_count": len(setups),
        "trade_count": len(trades),
        "wins": sum(value > 0 for value in primary),
        "losses": sum(value < 0 for value in primary),
        "breakeven": sum(value == 0 for value in primary),
        "gross_total_r": str(sum(gross, Decimal(0))),
        "gross_mean_r": None
        if not gross
        else str(sum(gross, Decimal(0)) / len(gross)),
        "gross_pf": None
        if (value := _profit_factor(gross)) is None
        else str(value),
        "primary_total_r": str(sum(primary, Decimal(0))),
        "primary_mean_r": None
        if not primary
        else str(sum(primary, Decimal(0)) / len(primary)),
        "primary_pf": None
        if (value := _profit_factor(primary)) is None
        else str(value),
        "primary_max_drawdown_r": str(_max_drawdown(primary)),
        "primary_max_losing_streak": _max_losing_streak(primary),
        "stress_total_r": str(sum(stress, Decimal(0))),
        "stress_pf": None
        if (value := _profit_factor(stress)) is None
        else str(value),
        "bootstrap_primary_mean_r_95ci": [low_ci, high_ci],
        "false_bottom_count": len(false_bottoms),
        "false_bottom_rate": (
            None if not setups else len(false_bottoms) / len(setups)
        ),
        "mean_mfe_r": None
        if not trades
        else str(sum((item.mfe_r for item in trades), Decimal(0)) / len(trades)),
        "mean_mae_r": None
        if not trades
        else str(sum((item.mae_r for item in trades), Decimal(0)) / len(trades)),
        "exit_reasons": dict(
            sorted(Counter(item.exit_reason for item in trades).items())
        ),
        "stage_funnel": dict(sorted(stages.items())),
        "reason_funnel": dict(sorted(reasons.items())),
        "by_month": _bucket_trades(trades, _month_key),
        "by_quarter": _bucket_trades(trades, _quarter_key),
    }


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


def _json_dataclass(value: Any) -> dict[str, Any]:
    raw = asdict(value)
    return {key: _json_value(item) for key, item in raw.items()}


def write_replay(
    evidence_path: Path,
    output: Path,
    *,
    variant: Variant,
) -> dict[str, Any]:
    evidence, payload = load_evidence(evidence_path)
    eval_open = date.fromisoformat(str(payload["evaluation_open_ny"]))
    eval_close = date.fromisoformat(str(payload["evaluation_close_ny"]))
    records = replay(
        evidence,
        eval_open_ny=eval_open,
        eval_close_ny=eval_close,
        variant=variant,
    )
    output.mkdir(parents=True, exist_ok=True)
    summary = summarize(records)
    summary.update(
        {
            "schema": "qore.nq_am_temporal_liquidity_reversal.result.v1",
            "evidence_id": payload["evidence_id"],
            "evidence_status": payload["evidence_status"],
            "provider": payload["provider"],
            "instrument_class": payload["instrument_class"],
            "evaluation_open_ny": eval_open.isoformat(),
            "evaluation_close_ny": eval_close.isoformat(),
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        }
    )
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    (output / "day-records.json").write_text(
        json.dumps(
            [_json_dataclass(item) for item in records],
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    (output / "trades.json").write_text(
        json.dumps(
            [_json_dataclass(item.trade) for item in records if item.trade is not None],
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return summary


def write_ablation_suite(evidence_path: Path, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {}
    for variant in Variant:
        results[variant.value] = write_replay(
            evidence_path,
            output / variant.value.lower(),
            variant=variant,
        )
    payload = {
        "schema": "qore.nq_am_temporal_liquidity_reversal.ablation.v1",
        "identity": IDENTITY,
        "selection_authority": False,
        "full_identity_is_only_future_holdout_candidate": True,
        "variants": results,
    }
    (output / "ablation.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    return payload


def collect_dev(output: Path) -> dict[str, Any]:
    evidence = _collect_m1(
        PROVIDER_SYMBOL,
        acquisition_open=DEV_ACQUISITION_OPEN,
        acquisition_close=DEV_ACQUISITION_CLOSE,
    )
    payload = evidence_payload(
        evidence,
        evidence_id=DEV_EVIDENCE_ID,
        acquisition_open=DEV_ACQUISITION_OPEN,
        acquisition_close=DEV_ACQUISITION_CLOSE,
        eval_open_ny=DEV_EVAL_OPEN_NY,
        eval_close_ny=DEV_EVAL_CLOSE_NY,
        evidence_status="CONSUMED_DEVELOPMENT_ONLY",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n")
    return {
        "identity": IDENTITY,
        "evidence_id": DEV_EVIDENCE_ID,
        "bars": len(evidence.bars),
        "first_bar": evidence.bars[0].opened_at.isoformat(),
        "last_bar": evidence.bars[-1].closed_at.isoformat(),
        "evidence_status": "CONSUMED_DEVELOPMENT_ONLY",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    collect = sub.add_parser("collect-dev")
    collect.add_argument("output", type=Path)
    replay_parser = sub.add_parser("replay")
    replay_parser.add_argument("evidence", type=Path)
    replay_parser.add_argument("output", type=Path)
    replay_parser.add_argument(
        "--variant", choices=[item.value for item in Variant], default="FULL"
    )
    ablate = sub.add_parser("ablate")
    ablate.add_argument("evidence", type=Path)
    ablate.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "collect-dev":
        print(json.dumps(collect_dev(args.output), sort_keys=True))
        return
    if args.command == "replay":
        print(
            json.dumps(
                write_replay(
                    args.evidence,
                    args.output,
                    variant=Variant(args.variant),
                ),
                sort_keys=True,
            )
        )
        return
    if args.command == "ablate":
        print(json.dumps(write_ablation_suite(args.evidence, args.output), sort_keys=True))
        return
    raise SystemExit("unknown command")


if __name__ == "__main__":
    main()
