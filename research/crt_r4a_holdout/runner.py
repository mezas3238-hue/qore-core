"""QORE CRT R4-A 34-instrument research trader; offline event-tape execution only.

NO BROKER CONNECTION. NO LIVE TRADING. NO AUTOMATIC CERTIFICATION.
The detector/parity event tape is an external prerequisite; this code does not
pretend to reproduce the 3546-line Pine state machine or generate CRT entries.
"""
from __future__ import annotations

import argparse
import csv
from bisect import bisect_left
from itertools import islice
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PINE_BLOB = "693e3f49719e86e2ea0702f7b355af33bd0c4c7c"
START = datetime(2024, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 1, 1, tzinfo=timezone.utc)  # exclusive: exactly 24 months
SYMBOLS = (
    "AUDJPY", "GBPUSD", "GBPJPY", "XAUUSD", "USTEC", "US500", "US30",
    "BTCUSD", "AUDUSD", "USDCAD", "USDJPY", "EURUSD", "USDCHF",
    "NZDUSD", "NZDJPY", "NZDCHF", "XAGUSD", "AUDCAD", "AUDCHF",
    "AUDNZD", "CADCHF", "CADJPY", "CHFJPY", "EURAUD", "EURCAD",
    "EURCHF", "EURGBP", "EURJPY", "EURNZD", "GBPAUD", "GBPCAD",
    "GBPCHF", "GBPNZD", "NZDCAD",
)
MODELS = ("A_2C_MSS15", "B_TRUE3C_MSS5")


def timestamp(s: str) -> datetime:
    x = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if x.tzinfo is None:
        raise ValueError("timestamps must have timezone")
    return x.astimezone(timezone.utc)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _confirmed_hash(entry: Any, path: Path, name: str, issues: list[str]) -> None:
    if not isinstance(entry, dict) or not isinstance(entry.get("sha256"), str):
        issues.append(f"{name}: missing declared sha256")
    elif not path.is_file():
        issues.append(f"{name}: missing file {path}")
    elif sha256(path) != entry["sha256"]:
        issues.append(f"{name}: SHA256 mismatch")


def readiness(root: Path) -> dict[str, Any]:
    manifest_file = root / "manifest.json"
    issues: list[str] = []
    if not manifest_file.is_file():
        return {"status": "BLOCKED", "issues": ["manifest.json missing"]}
    m = json.loads(manifest_file.read_text(encoding="utf-8"))
    if m.get("pine_git_blob_sha") != PINE_BLOB:
        issues.append("Pine R4-A blob identity not pinned")
    if m.get("start") != START.isoformat() or m.get("end_exclusive") != END.isoformat():
        issues.append("holdout must be exactly 2024-01-01 through 2025-12-31 UTC")
    if m.get("holdout_unseen_attested") is not True or not m.get("holdout_attestation_ref"):
        issues.append("24-month holdout virginity not independently attested")
    if m.get("parity_verified") is not True or not m.get("parity_evidence_ref"):
        issues.append("Pine ↔ event replay 100% causal parity not verified")
    if m.get("provider_data_verified") is not True or not m.get("data_evidence_ref"):
        issues.append("IC Markets 34-feed M5 historical provenance/coverage not certified")
    if m.get("costs_verified") is not True or not m.get("cost_evidence_ref"):
        issues.append("34-market bid/ask, slippage and commissions not certified")
    q = m.get("quotes", {})
    if set(q) != set(SYMBOLS):
        issues.append("quotes manifest must contain exactly 34 immutable IC symbols")
    for sym in SYMBOLS:
        entry = q.get(sym, {})
        path = root / "quotes" / f"IC_{sym}.csv"
        before = len(issues)
        _confirmed_hash(entry, path, f"IC:{sym}", issues)
        if before == len(issues):
            try:
                bars = read_quotes(path)
                if (len(bars) < 50_000 or
                        bars[0].opened > START - timedelta(days=10) or
                        bars[-1].opened < END - timedelta(days=10)):
                    issues.append(f"IC:{sym}: inadequate 2-year M5 coverage or warmup")
            except (ValueError, OSError, KeyError) as exc:
                issues.append(f"IC:{sym}: invalid M5 candles: {exc}")
    for field, filename in (("events", "events.csv"), ("costs", "costs.json")):
        _confirmed_hash(m.get(field), root / filename, field, issues)
    return {"status": "BLOCKED" if issues else "READY", "issues": issues,
            "symbols_required": len(SYMBOLS), "models": MODELS,
            "holdout_start": START.isoformat(), "holdout_end_exclusive": END.isoformat(),
            "pine_blob": PINE_BLOB}


@dataclass(frozen=True)
class Quote:
    opened: datetime
    bo: float
    bh: float
    bl: float
    bc: float
    ao: float
    ah: float
    al: float
    ac: float

    @staticmethod
    def parse(row: dict[str, str]) -> Quote:
        fields = [float(row[k]) for k in (
            "bid_open", "bid_high", "bid_low", "bid_close",
            "ask_open", "ask_high", "ask_low", "ask_close"
        )]
        bo, bh, bl, bc, ao, ah, al, ac = fields
        if any(not math.isfinite(x) or x <= 0 for x in fields):
            raise ValueError("invalid price")
        if not (bl <= min(bo, bc) <= max(bo, bc) <= bh and
                al <= min(ao, ac) <= max(ao, ac) <= ah):
            raise ValueError("invalid OHLC")
        if bo > ao or bc > ac or bl > ah:
            raise ValueError("invalid bid/ask ordering")
        t = timestamp(row["opened_at"])
        if t.second or t.minute % 5:
            raise ValueError("unaligned M5 time")
        return Quote(t, *fields)


@dataclass(frozen=True)
class Event:
    identity: str
    symbol: str
    model: str
    side: str
    sweep_at: datetime
    mss_at: datetime
    ratified_at: datetime
    available_at: datetime
    c1_high: float
    c1_low: float
    body_open: float  # C2 for A, C3 for B; H4 closed, known at ratified_at
    body_close: float
    sweep_high: float  # observed complete C2 (A) or C3 (B)
    sweep_low: float
    atr_h4: float

    @staticmethod
    def parse(row: dict[str, str]) -> Event:
        e = Event(
            row["event_id"], row["symbol"], row["model"], row["side"],
            timestamp(row["sweep_at"]), timestamp(row["mss_at"]),
            timestamp(row["ratified_at"]), timestamp(row["available_at"]),
            *(float(row[k]) for k in (
                "c1_high", "c1_low", "body_open", "body_close",
                "sweep_high", "sweep_low", "atr_h4"
            )),
        )
        if e.symbol not in SYMBOLS or e.model not in MODELS:
            raise ValueError("unsupported symbol/model")
        if e.side not in {"LONG", "SHORT"} or not e.identity:
            raise ValueError("invalid side/identity")
        if not (e.sweep_at < e.mss_at <= e.available_at and
                e.ratified_at <= e.available_at and
                e.c1_low < e.c1_high and e.sweep_low <= e.sweep_high):
            raise ValueError("event chronology or levels inconsistent")
        if e.model == "B_TRUE3C_MSS5" and e.mss_at > e.ratified_at:
            raise ValueError("TRUE 3C MSS5 must occur during C3 before ratification")
        if not all(math.isfinite(x) and x > 0 for x in (
            e.c1_high, e.c1_low, e.body_open, e.body_close,
            e.sweep_high, e.sweep_low, e.atr_h4
        )):
            raise ValueError("nonfinite event levels")
        if not (START <= e.available_at < END):
            raise ValueError("event outside 24-month window")
        return e


def read_quotes(path: Path) -> list[Quote]:
    with path.open(newline="", encoding="utf-8") as f:
        bars = [Quote.parse(r) for r in csv.DictReader(f)]
    if not bars or any(a.opened >= b.opened for a, b in zip(bars, bars[1:])):
        raise ValueError("missing, duplicate or unordered quotes")
    return bars


def read_events(path: Path) -> list[Event]:
    with path.open(newline="", encoding="utf-8") as f:
        events = [Event.parse(r) for r in csv.DictReader(f)]
    if len(set(e.identity for e in events)) != len(events):
        raise ValueError("duplicate event_id")
    return sorted(events, key=lambda e: (e.available_at, e.symbol, e.identity))


@dataclass(frozen=True)
class Trade:
    event_id: str
    symbol: str
    model: str
    side: str
    entered: datetime
    exited: datetime
    exit_reason: str
    r_net: float


def simulate_event(
    e: Event, quotes: list[Quote], *, commission_price: float,
    slippage_price: float, expiry_hours: int = 12, buffer_atr: float = 0.25
) -> tuple[str, Trade | None]:
    """Reference LIMIT entry, structural SL/TP, conservative intrabar execution.

    Position sizing, correlation and broker stop-level constraints are NOT
    implemented, hence only per-trade net R is claimed (not a capital curve).
    """
    if not (math.isfinite(commission_price) and commission_price >= 0 and
            math.isfinite(slippage_price) and slippage_price >= 0):
        raise ValueError("costs must be supplied as nonnegative price-equivalents")
    if expiry_hours <= 0 or buffer_atr < 0:
        raise ValueError("invalid experiment parameters")
    entry = (e.body_open + e.body_close) / 2
    signal_spread = next(
        (q.ao - q.bo for q in quotes if q.opened >= e.available_at), None
    )
    if signal_spread is None:
        return "NO_QUOTES_AFTER_CONFIRMATION", None
    buffer = max(e.atr_h4 * buffer_atr, signal_spread)
    stop = (min(e.c1_low, e.sweep_low) - buffer if e.side == "LONG"
            else max(e.c1_high, e.sweep_high) + buffer)
    target = e.c1_high if e.side == "LONG" else e.c1_low
    distance = entry - stop if e.side == "LONG" else stop - entry
    if distance <= 0 or (target <= entry if e.side == "LONG" else target >= entry):
        return "INVALID_SL_OR_TP", None
    if abs(entry - e.body_close) > 0.5 * e.atr_h4:
        return "ENTRY_TOO_FAR_FROM_CONFIRMATION", None
    # Do not execute on the confirmation bar, and never claim a fill
    # if the unfilled stop is hit at an ambiguous intrabar moment.
    deadline = e.available_at + timedelta(hours=expiry_hours)
    entered: datetime | None = None
    start_i = bisect_left(quotes, e.available_at, key=lambda q: q.opened)
    for q in islice(quotes, start_i, None):
        if entered is None:
            if q.opened >= deadline:
                return "LIMIT_EXPIRED", None
            if (q.bl <= stop if e.side == "LONG" else q.ah >= stop):
                return "UNFILLED_INVALIDATED_OR_AMBIGUOUS", None
            fill = q.al <= entry if e.side == "LONG" else q.bh >= entry
            if not fill:
                continue
            entered = q.opened
        if e.side == "LONG":
            sl_hit = q.bl <= stop
            tp_hit = q.bh >= target
            if sl_hit or tp_hit:
                exit_price = min(stop - slippage_price, q.bo) if sl_hit else target - slippage_price
                r = (exit_price - entry - commission_price) / distance
                return "TRADE", Trade(
                    e.identity, e.symbol, e.model, e.side, entered, q.opened,
                    "SL" if sl_hit else "TP", r
                )
        else:
            sl_hit = q.ah >= stop
            tp_hit = q.al <= target
            if sl_hit or tp_hit:
                exit_price = max(stop + slippage_price, q.ao) if sl_hit else target + slippage_price
                r = (entry - exit_price - commission_price) / distance
                return "TRADE", Trade(
                    e.identity, e.symbol, e.model, e.side, entered, q.opened,
                    "SL" if sl_hit else "TP", r
                )
    return ("OPEN_AT_END_OF_DATA" if entered is not None else "LIMIT_UNFILLED"), None


def report_trades(trades: list[Trade]) -> dict[str, Any]:
    rs = [t.r_net for t in sorted(trades, key=lambda x: (x.exited, x.event_id))]
    gross_win = sum(x for x in rs if x > 0)
    gross_loss = -sum(x for x in rs if x < 0)
    equity = 0.0
    peak = 0.0
    dd = 0.0
    for r in rs:
        equity += r
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    return {
        "trades": len(trades),
        "win_rate": sum(x > 0 for x in rs) / len(rs) if rs else None,
        "profit_factor": gross_win / gross_loss if gross_loss else None,
        "mean_r": sum(rs) / len(rs) if rs else None,
        "net_r": sum(rs),
        "max_dd_r_sequential": dd,
        "scope": "INSTRUMENT_OR_MODEL_R_ONLY_NOT_PORTFOLIO",
    }


def execute(root: Path) -> dict[str, Any]:
    ready = readiness(root)
    if ready["status"] != "READY":
        return ready
    events = read_events(root / "events.csv")
    costs = json.loads((root / "costs.json").read_text(encoding="utf-8"))
    if set(costs) != set(SYMBOLS):
        raise ValueError("cost schedule must cover all 34 instruments")
    quotes = {sym: read_quotes(root / "quotes" / f"IC_{sym}.csv") for sym in SYMBOLS}
    if not events:
        raise ValueError("event tape missing; cannot claim zero trading opportunities")
    trades: list[Trade] = []
    reasons: dict[str, int] = {}
    busy_until: dict[str, datetime] = {}
    for e in events:
        if busy_until.get(e.symbol, START) > e.available_at:
            reasons["SYMBOL_ALREADY_OPEN"] = reasons.get("SYMBOL_ALREADY_OPEN", 0) + 1
            continue
        c = costs[e.symbol]
        if not isinstance(c, dict) or set(c) != {"commission_price", "slippage_price"}:
            raise ValueError(f"cost evidence invalid for {e.symbol}")
        reason, trade = simulate_event(
            e, quotes[e.symbol],
            commission_price=float(c["commission_price"]),
            slippage_price=float(c["slippage_price"]),
        )
        reasons[reason] = reasons.get(reason, 0) + 1
        if reason == "OPEN_AT_END_OF_DATA":
            raise ValueError("open position unresolved; quote evidence or exit policy missing")
        if trade:
            trades.append(trade)
            busy_until[e.symbol] = trade.exited
    by_symbol = {s: report_trades([t for t in trades if t.symbol == s]) for s in SYMBOLS}
    by_model = {m: report_trades([t for t in trades if t.model == m]) for m in MODELS}
    return {
        "status": "RESEARCH_ONLY_NOT_CERTIFIED",
        "window_start": START.isoformat(),
        "window_end_exclusive": END.isoformat(),
        "pine_blob": PINE_BLOB,
        "total_events": len(events),
        "counts": reasons,
        "by_symbol": by_symbol,
        "by_model_pooled_r_only": by_model,
        "portfolio_certified": False,
        "warning": "No position sizing, margin, correlation, complete OHLC continuity certification, or Pine detector port.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preflight", "run"))
    parser.add_argument("--root", type=Path, default=Path("research/crt_r4a_holdout/data"))
    parser.add_argument("--out", type=Path, default=Path("crt_r4a_preflight.json"))
    args = parser.parse_args()
    output = readiness(args.root) if args.mode == "preflight" else execute(args.root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": output["status"], "report": str(args.out),
                      "blockers": output.get("issues", [])}, ensure_ascii=False))
    if args.mode == "run" and output["status"] == "BLOCKED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
