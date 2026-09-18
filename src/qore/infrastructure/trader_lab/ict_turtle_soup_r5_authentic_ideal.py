"""Authentic TTrades Ideal-Formation Turtle Soup R5 research implementation.

R5 is a new identity after the consumed/rejected R4 result.  It does not tune
R4 economics.  Its sole mechanics change is source-derived: Candle 2 itself
must create the protected swing on the same source timeframe by closing
through the contiguous opposing candle series responsible for delivery into
the swept high/low.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from time import sleep
from typing import Any, cast

from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    CHUNK_DAYS,
    H4_SOURCE_ANCHORS,
    M5,
    PAGE_COUNT,
    PRIMARY_FRICTION_R,
    REQUEST_PAUSE_SECONDS,
    STRESS_FRICTION_R,
    Bar,
    Evidence,
    Side,
    SourceCandle,
    _max_drawdown,
    _native_int,
    _price,
    _profit_factor,
    _required_env,
    _session_bucket,
    _simulate_until_daily_close,
    build_daily,
    build_h4,
)
from qore.kernel.result import Failure

IDENTITY = (
    "ICT_TURTLE_SOUP_R5_D1_AUTHENTIC_IDEAL_C2__"
    "H4_AUTHENTIC_IDEAL_C2__POSITIONAL_DAILY_DOL"
)
HOLDOUT_ID = "ICT_TS_R5_FRESH_2016_2018"
ACQUISITION_OPEN = datetime(2016, 3, 1, 22, tzinfo=UTC)
EVAL_OPEN = datetime(2016, 5, 1, 21, tzinfo=UTC)
EVAL_CLOSE = datetime(2018, 5, 1, 21, tzinfo=UTC)
EXPECTED_SYMBOLS = {
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "USDCAD",
    "USDJPY",
}


@dataclass(frozen=True, slots=True)
class IdealC2:
    side: Side
    c1_opened_at: datetime
    c2_opened_at: datetime
    opposing_series_opened_at: datetime
    opposing_series_threshold: Decimal
    protected_swing: Decimal


@dataclass(frozen=True, slots=True)
class Trade:
    symbol: str
    side: Side
    daily_c2_opened_at: datetime
    daily_c3_opened_at: datetime
    daily_series_opened_at: datetime
    h4_c1_opened_at: datetime
    h4_c2_opened_at: datetime
    h4_series_opened_at: datetime
    entry_at: datetime
    exit_at: datetime
    protected_swing: Decimal
    entry: Decimal
    stop: Decimal
    target: Decimal
    exit_price: Decimal
    projected_r: Decimal
    gross_r: Decimal
    primary_net_r: Decimal
    stress_net_r: Decimal
    exit_reason: str
    session_bucket: str
    primary_dol_opened_at: datetime


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _collect_m5(symbol_name: str) -> Evidence:
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
            client_msg_id="qore-ict-ts-r5-symbol-list",
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
            client_msg_id=f"qore-ict-ts-r5-symbol:{symbol_id}",
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
        window_start = ACQUISITION_OPEN
        window_index = 0
        while window_start < EVAL_CLOSE:
            window_end = min(
                window_start + timedelta(days=CHUNK_DAYS), EVAL_CLOSE
            )
            sleep(REQUEST_PAUSE_SECONDS)
            response = client.request(
                "ProtoOAGetTrendbarsReq",
                {
                    "ctidTraderAccountId": account_id,
                    "count": PAGE_COUNT,
                    "fromTimestamp": int(window_start.timestamp() * 1000),
                    "period": 5,
                    "symbolId": symbol_id,
                    "toTimestamp": int(window_end.timestamp() * 1000),
                },
                client_msg_id=f"qore-ict-ts-r5-m5:{symbol_id}:{window_index}",
                timeout_seconds=45.0,
            )
            if isinstance(response, Failure):
                raise RuntimeError("cTrader M5 historical read failed")
            natives = tuple(
                cast(Iterable[object], getattr(response.value, "trendbar", ()))
            )
            if len(natives) >= PAGE_COUNT and getattr(
                response.value, "hasMore", False
            ):
                raise RuntimeError("cTrader M5 chunk exceeded safe page bound")
            for native in natives:
                low_rel = _native_int(native, "low")
                opened = datetime.fromtimestamp(
                    _native_int(native, "utcTimestampInMinutes") * 60,
                    tz=UTC,
                )
                if not ACQUISITION_OPEN <= opened < EVAL_CLOSE:
                    continue
                bar = Bar(
                    opened_at=opened,
                    closed_at=opened + M5,
                    open=_price(low_rel + _native_int(native, "deltaOpen"), digits),
                    high=_price(low_rel + _native_int(native, "deltaHigh"), digits),
                    low=_price(low_rel, digits),
                    close=_price(low_rel + _native_int(native, "deltaClose"), digits),
                )
                existing = retained.get(opened)
                if existing is not None and existing != bar:
                    raise RuntimeError("contradictory historical M5 bar")
                retained[opened] = bar
            window_start = window_end
            window_index += 1
        bars = tuple(retained[key] for key in sorted(retained))
        if not bars:
            raise RuntimeError("no historical M5 evidence")
        if bars[0].opened_at > ACQUISITION_OPEN + timedelta(days=10):
            raise RuntimeError("provider history does not reach frozen warm-up boundary")
        if bars[-1].closed_at < EVAL_CLOSE - timedelta(days=10):
            raise RuntimeError("provider history is stale at frozen close boundary")
        return Evidence(symbol=symbol_name, digits=digits, bars=bars)
    finally:
        client.close()


def evidence_payload(evidence: Evidence) -> dict[str, Any]:
    return {
        "schema": "qore.ict_turtle_soup_r5.fresh_evidence.v1",
        "identity": IDENTITY,
        "holdout_id": HOLDOUT_ID,
        "fresh_relative_to_documented_repo_evidence": True,
        "acquisition_opened_at": ACQUISITION_OPEN.isoformat(),
        "evaluation_opened_at": EVAL_OPEN.isoformat(),
        "evaluation_closed_at": EVAL_CLOSE.isoformat(),
        "source_time_zone": "America/New_York",
        "forex_daily_open_ny": "17:00",
        "forex_h4_opens_ny": list(H4_SOURCE_ANCHORS),
        "symbol": {"symbol_name": evidence.symbol, "digits": evidence.digits},
        "periods": {
            "M5": [
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


def load_evidence(path: Path) -> Evidence:
    payload = json.loads(path.read_text())
    if payload.get("identity") != IDENTITY:
        raise ValueError("unexpected R5 identity")
    if payload.get("holdout_id") != HOLDOUT_ID:
        raise ValueError("unexpected R5 holdout id")
    if payload.get("read_only") is not True:
        raise ValueError("R5 evidence must be read-only")
    if _dt(payload["evaluation_opened_at"]) != EVAL_OPEN:
        raise ValueError("R5 evaluation open drift")
    if _dt(payload["evaluation_closed_at"]) != EVAL_CLOSE:
        raise ValueError("R5 evaluation close drift")
    symbol = str(payload["symbol"]["symbol_name"])
    digits = int(payload["symbol"]["digits"])
    bars = tuple(
        Bar(
            opened_at=_dt(item["opened_at"]),
            closed_at=_dt(item["closed_at"]),
            open=Decimal(item["open"]),
            high=Decimal(item["high"]),
            low=Decimal(item["low"]),
            close=Decimal(item["close"]),
        )
        for item in payload["periods"]["M5"]
    )
    return Evidence(symbol=symbol, digits=digits, bars=bars)


def _opposing(candle: SourceCandle, side: Side) -> bool:
    if candle.close == candle.open:
        return False
    return candle.close < candle.open if side is Side.LONG else candle.close > candle.open


def _body_aligned(candle: SourceCandle, side: Side) -> bool:
    return candle.close > candle.open if side is Side.LONG else candle.close < candle.open


def authentic_ideal_c2(
    candles: tuple[SourceCandle, ...], index: int
) -> IdealC2 | None:
    """Return authentic same-timeframe Ideal C2 or fail closed.

    The opposing series is contiguous and immediately precedes C2.  A doji is
    neither opposing direction and therefore terminates the series.
    """
    if index <= 0 or index >= len(candles):
        return None
    c1 = candles[index - 1]
    c2 = candles[index]
    bullish = c2.low < c1.low and c2.close > c1.low
    bearish = c2.high > c1.high and c2.close < c1.high
    if bullish == bearish:
        return None
    side = Side.LONG if bullish else Side.SHORT
    if not _body_aligned(c2, side):
        return None
    cursor = index - 1
    if not _opposing(candles[cursor], side):
        return None
    while cursor > 0 and _opposing(candles[cursor - 1], side):
        cursor -= 1
    threshold = candles[cursor].open
    confirmed = c2.close > threshold if side is Side.LONG else c2.close < threshold
    if not confirmed:
        return None
    return IdealC2(
        side=side,
        c1_opened_at=c1.opened_at,
        c2_opened_at=c2.opened_at,
        opposing_series_opened_at=candles[cursor].opened_at,
        opposing_series_threshold=threshold,
        protected_swing=c2.low if side is Side.LONG else c2.high,
    )


def _daily_swing_targets(
    daily: tuple[SourceCandle, ...],
    m5: tuple[Bar, ...],
    *,
    side: Side,
    entry: Decimal,
    entry_at: datetime,
) -> tuple[Decimal, datetime] | None:
    """Nearest untouched completed three-candle Daily swing in bias direction."""
    candidates: list[tuple[Decimal, datetime]] = []
    for index in range(1, len(daily) - 1):
        left, pivot, right = daily[index - 1], daily[index], daily[index + 1]
        if right.closed_at > entry_at:
            continue
        if side is Side.LONG:
            is_swing = pivot.high > left.high and pivot.high > right.high
            level = pivot.high
            if not is_swing or level <= entry:
                continue
            taken = any(
                bar.high >= level
                for bar in m5
                if right.closed_at <= bar.opened_at < entry_at
            )
        else:
            is_swing = pivot.low < left.low and pivot.low < right.low
            level = pivot.low
            if not is_swing or level >= entry:
                continue
            taken = any(
                bar.low <= level
                for bar in m5
                if right.closed_at <= bar.opened_at < entry_at
            )
        if not taken:
            candidates.append((level, pivot.opened_at))
    if not candidates:
        return None
    if side is Side.LONG:
        level = min(item[0] for item in candidates)
    else:
        level = max(item[0] for item in candidates)
    opened = min(moment for candidate, moment in candidates if candidate == level)
    return level, opened


def _tick_size(digits: int) -> Decimal:
    if digits <= 0:
        raise ValueError("digits must be positive")
    return Decimal(1).scaleb(-digits)


def replay_symbol(evidence: Evidence) -> tuple[list[Trade], Counter[str]]:
    h4 = build_h4(evidence.bars)
    daily = build_daily(h4)
    h4_index = {candle.opened_at: index for index, candle in enumerate(h4)}
    trades: list[Trade] = []
    funnel: Counter[str] = Counter()
    tick = _tick_size(evidence.digits)

    for day_index in range(1, len(daily) - 1):
        daily_c2 = daily[day_index]
        daily_c3 = daily[day_index + 1]
        if not EVAL_OPEN <= daily_c3.opened_at < EVAL_CLOSE:
            continue
        funnel["daily-cycles"] += 1
        daily_ideal = authentic_ideal_c2(daily, day_index)
        if daily_ideal is None:
            funnel["no-daily-authentic-ideal-c2"] += 1
            continue
        funnel["daily-authentic-ideal-c2"] += 1

        day_h4 = tuple(
            candle
            for candle in h4
            if daily_c3.opened_at <= candle.opened_at < daily_c3.closed_at
        )
        traded = False
        for candidate in day_h4:
            idx = h4_index[candidate.opened_at]
            if idx <= 0 or idx + 1 >= len(h4):
                continue
            h4_c3 = h4[idx + 1]
            if h4_c3.opened_at >= daily_c3.closed_at:
                continue
            h4_ideal = authentic_ideal_c2(h4, idx)
            if h4_ideal is None or h4_ideal.side is not daily_ideal.side:
                funnel["no-aligned-h4-authentic-ideal-c2"] += 1
                continue
            funnel["aligned-h4-authentic-ideal-c2"] += 1
            side = daily_ideal.side
            entry = h4_c3.open
            stop = (
                h4_ideal.protected_swing - tick
                if side is Side.LONG
                else h4_ideal.protected_swing + tick
            )
            risk = entry - stop if side is Side.LONG else stop - entry
            if risk <= 0:
                funnel["entry-through-protected-swing"] += 1
                continue
            dol = _daily_swing_targets(
                daily,
                evidence.bars,
                side=side,
                entry=entry,
                entry_at=h4_c3.opened_at,
            )
            if dol is None:
                funnel["no-primary-daily-swing-dol"] += 1
                continue
            target, target_opened_at = dol
            reward = target - entry if side is Side.LONG else entry - target
            if reward <= 0:
                funnel["entry-through-dol"] += 1
                continue
            exit_at, exit_price, exit_reason, gross_r = _simulate_until_daily_close(
                evidence.bars,
                side=side,
                entry_at=h4_c3.opened_at,
                daily_close=daily_c3.closed_at,
                entry=entry,
                stop=stop,
                target=target,
            )
            trades.append(
                Trade(
                    symbol=evidence.symbol,
                    side=side,
                    daily_c2_opened_at=daily_c2.opened_at,
                    daily_c3_opened_at=daily_c3.opened_at,
                    daily_series_opened_at=daily_ideal.opposing_series_opened_at,
                    h4_c1_opened_at=h4[idx - 1].opened_at,
                    h4_c2_opened_at=h4[idx].opened_at,
                    h4_series_opened_at=h4_ideal.opposing_series_opened_at,
                    entry_at=h4_c3.opened_at,
                    exit_at=exit_at,
                    protected_swing=h4_ideal.protected_swing,
                    entry=entry,
                    stop=stop,
                    target=target,
                    exit_price=exit_price,
                    projected_r=reward / risk,
                    gross_r=gross_r,
                    primary_net_r=gross_r - PRIMARY_FRICTION_R,
                    stress_net_r=gross_r - STRESS_FRICTION_R,
                    exit_reason=exit_reason,
                    session_bucket=_session_bucket(h4[idx].opened_at),
                    primary_dol_opened_at=target_opened_at,
                )
            )
            funnel["trade"] += 1
            traded = True
            break
        if not traded:
            funnel["daily-c3-no-trade"] += 1
    return trades, funnel


def _summary(trades: list[Trade]) -> dict[str, Any]:
    ordered = sorted(trades, key=lambda item: (item.entry_at, item.symbol))
    gross = [item.gross_r for item in ordered]
    primary = [item.primary_net_r for item in ordered]
    stress = [item.stress_net_r for item in ordered]
    return {
        "trades": len(ordered),
        "gross_wins": sum(value > 0 for value in gross),
        "gross_losses": sum(value < 0 for value in gross),
        "gross_total_r": str(sum(gross, Decimal(0))),
        "gross_mean_r": None if not gross else str(sum(gross, Decimal(0)) / len(gross)),
        "gross_pf": (
            None if (value := _profit_factor(gross)) is None else str(value)
        ),
        "primary_total_r": str(sum(primary, Decimal(0))),
        "primary_mean_r": (
            None if not primary else str(sum(primary, Decimal(0)) / len(primary))
        ),
        "primary_pf": (
            None if (value := _profit_factor(primary)) is None else str(value)
        ),
        "primary_max_drawdown_r": str(_max_drawdown(primary)),
        "stress_total_r": str(sum(stress, Decimal(0))),
        "stress_pf": (
            None if (value := _profit_factor(stress)) is None else str(value)
        ),
    }


def _json_trade(trade: Trade) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in asdict(trade).items():
        if isinstance(value, Decimal):
            payload[key] = str(value)
        elif isinstance(value, datetime):
            payload[key] = value.isoformat()
        elif isinstance(value, StrEnum):
            payload[key] = value.value
        else:
            payload[key] = value
    return payload


def replay_to_dir(evidence_path: Path, output: Path) -> dict[str, Any]:
    evidence = load_evidence(evidence_path)
    trades, funnel = replay_symbol(evidence)
    output.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "qore.ict_turtle_soup_r5.market_result.v1",
        "identity": IDENTITY,
        "holdout_id": HOLDOUT_ID,
        "symbol": evidence.symbol,
        "evidence_status": "FRESH_RELATIVE_TO_DOCUMENTED_REPO_EVIDENCE",
        "fresh_window_open": EVAL_OPEN.isoformat(),
        "fresh_window_close": EVAL_CLOSE.isoformat(),
        "session_filter_applied": False,
        "asia_london_new_york_all_eligible": True,
        "minimum_projected_r_gate": None,
        "r5": _summary(trades),
        "funnel": dict(sorted(funnel.items())),
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    (output / "report.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    (output / "trades.json").write_text(
        json.dumps([_json_trade(trade) for trade in trades], indent=2, sort_keys=True) + "\n"
    )
    return payload


def aggregate_results(paths: list[Path], output: Path) -> dict[str, Any]:
    reports = [json.loads(path.read_text()) for path in paths]
    if {item["symbol"] for item in reports} != EXPECTED_SYMBOLS:
        raise ValueError("aggregate requires exact seven-symbol scope")
    all_trades: list[dict[str, Any]] = []
    for path in paths:
        all_trades.extend(json.loads((path.parent / "trades.json").read_text()))
    all_trades.sort(key=lambda item: (item["entry_at"], item["symbol"]))
    gross = [Decimal(item["gross_r"]) for item in all_trades]
    primary = [Decimal(item["primary_net_r"]) for item in all_trades]
    stress = [Decimal(item["stress_net_r"]) for item in all_trades]
    payload = {
        "schema": "qore.ict_turtle_soup_r5.aggregate.v1",
        "identity": IDENTITY,
        "holdout_id": HOLDOUT_ID,
        "symbols": sorted(EXPECTED_SYMBOLS),
        "fresh_relative_to_documented_repo_evidence": True,
        "trade_count": len(all_trades),
        "gross_wins": sum(value > 0 for value in gross),
        "gross_losses": sum(value < 0 for value in gross),
        "gross_total_r": str(sum(gross, Decimal(0))),
        "gross_mean_r": None if not gross else str(sum(gross, Decimal(0)) / len(gross)),
        "gross_pf": None if (value := _profit_factor(gross)) is None else str(value),
        "primary_total_r": str(sum(primary, Decimal(0))),
        "primary_mean_r": (
            None if not primary else str(sum(primary, Decimal(0)) / len(primary))
        ),
        "primary_pf": None if (value := _profit_factor(primary)) is None else str(value),
        "primary_max_drawdown_r": str(_max_drawdown(primary)),
        "stress_total_r": str(sum(stress, Decimal(0))),
        "stress_pf": None if (value := _profit_factor(stress)) is None else str(value),
        "by_symbol": {
            report["symbol"]: report["r5"]
            for report in sorted(reports, key=lambda item: item["symbol"])
        },
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "aggregate.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    (output / "trades.json").write_text(json.dumps(all_trades, indent=2, sort_keys=True) + "\n")
    return payload


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "usage: module collect SYMBOL OUTPUT | replay EVIDENCE OUTPUT_DIR | "
            "aggregate OUTPUT_DIR REPORT..."
        )
    command = sys.argv[1]
    if command == "collect":
        if len(sys.argv) != 4:
            raise SystemExit("collect SYMBOL OUTPUT")
        symbol = sys.argv[2]
        if symbol not in EXPECTED_SYMBOLS:
            raise SystemExit("symbol outside frozen scope")
        evidence = _collect_m5(symbol)
        Path(sys.argv[3]).write_text(
            json.dumps(evidence_payload(evidence), sort_keys=True, separators=(",", ":")) + "\n"
        )
        return
    if command == "replay":
        if len(sys.argv) != 4:
            raise SystemExit("replay EVIDENCE OUTPUT_DIR")
        print(json.dumps(replay_to_dir(Path(sys.argv[2]), Path(sys.argv[3])), sort_keys=True))
        return
    if command == "aggregate":
        if len(sys.argv) < 5:
            raise SystemExit("aggregate OUTPUT_DIR REPORT...")
        print(
            json.dumps(
                aggregate_results([Path(item) for item in sys.argv[3:]], Path(sys.argv[2])),
                sort_keys=True,
            )
        )
        return
    raise SystemExit(f"unknown command: {command}")


if __name__ == "__main__":
    main()
