"""Research-only custody of independent M3/M15 source bars for VT08 A -> B.

No strategy selection, no PnL, no execution and no false SOURCE_COMPLETE.
The scanner samples predeclared NY owner anchor windows chronologically,
attests raw-file SHA256, reconstructs M30 from ten M3 and two M15 bars
and records exact per-bar IDs and availability clocks for independent review.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_5m_a_native_m30_m3_favorable_entry_v1 import (
    aggregate,
    closed_source_window,
    same_ohlc,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    load_market_evidence,
)
from qore.infrastructure.trader_lab.vt08_cognitive_m3_fractal_density_recovery_v1 import (
    _load_m3,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

SCHEMA: Final = "qore.vt08.a.m30m3.raw_bar_custody.v1"
MARKETS: Final = frozenset(("EURJPY", "USDCHF", "NZDUSD", "CADJPY", "USDCAD"))
NY: Final = ZoneInfo("America/New_York")
ANCHORS: Final = frozenset((1, 5, 9))
LIMIT_PER_MARKET: Final = 24


def _iso(t: datetime) -> str:
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("a source timestamp must have UTC offset")
    return t.astimezone(UTC).isoformat()


def _bar_receipt(bar: Vt08B01Bar, raw_sha: str, profile: str) -> dict[str, object]:
    if bar.closed_at.astimezone(UTC) <= bar.opened_at.astimezone(UTC):
        raise ValueError("invalid bar interval")
    body = {
        "profile": profile,
        "source_raw_sha256": raw_sha,
        "opened_at_utc": _iso(bar.opened_at),
        "closed_at_utc": _iso(bar.closed_at),
        "ohlc": tuple(str(getattr(bar, key)) for key in ("open", "high", "low", "close")),
    }
    payload = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {
        **body,
        "source_bar_id": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "available_at_utc": _iso(bar.closed_at),
        "semantics": "OBSERVED_OHLC_ONLY_NOT_TTRADES_RULE",
    }


def attest_anchor_window(
    *,
    market: str,
    m3_bars: dict[datetime, Vt08B01Bar],
    m15_bars: dict[datetime, Vt08B01Bar],
    opened_at: datetime,
    raw_m3_sha: str,
    raw_m15_sha: str,
) -> dict[str, object]:
    """Attest M30 equivalence, without labeling a setup/trade.

    Callers choose a start that is chronologically allowed. Source must
    include all ten closed M3 and two closed M15 candles. Fail closed on
    any price or time mismatch (do not auto-repair missing feed).
    """
    if market not in MARKETS:
        raise ValueError("market outside fixed five-market VT08 universe")
    t = opened_at.astimezone(UTC)
    local = t.astimezone(NY)
    if (local.hour not in ANCHORS or local.minute != 0
            or local.second != 0 or local.microsecond != 0):
        raise ValueError("NY owner anchor required")
    if any(len(h) != 64 or any(ch not in "0123456789abcdef" for ch in h)
           for h in (raw_m3_sha, raw_m15_sha)):
        raise ValueError("source raw SHA256 digest invalid")
    m3 = closed_source_window(m3_bars, begin=t, count=10, minutes=3)
    m15 = closed_source_window(m15_bars, begin=t, count=2, minutes=15)
    if m3 is None or m15 is None:
        raise ValueError("source M3/M15 source window incomplete")
    a = aggregate(m3, period_minutes=30, member_minutes=3)
    b = aggregate(m15, period_minutes=30, member_minutes=15)
    if not same_ohlc(a, b):
        raise ValueError("M3 and M15 disagree on source M30 OHLC")
    if a.closed_at.astimezone(UTC) != t + timedelta(minutes=30):
        raise ValueError("M30 not available 30 minutes after anchor")
    return {
        "schema": SCHEMA,
        "market": market,
        "ny_anchor_hour": local.hour,
        "ny_date": local.date().isoformat(),
        "m30_opened_at_utc": _iso(a.opened_at),
        "m30_available_at_utc": _iso(a.closed_at),
        "m30_ohlc": tuple(str(getattr(a, k)) for k in ("open", "high", "low", "close")),
        "m3_bar_receipts": [_bar_receipt(x, raw_m3_sha, "M3") for x in m3],
        "m15_bar_receipts": [_bar_receipt(x, raw_m15_sha, "M15") for x in m15],
        "source_m30_cross_attested": True,
        "source_author_fidelity_verified": False,
        "cognitive_ready": False,
        "broker_quotes_verified": False,
        "source_complete_candidate_events": 0,
        "orders": 0,
        "fills": 0,
        "pnl_measured": False,
        "holdout_7y_accessed": False,
    }


def attest_market_files(
    market: str, m3_path: Path, m15_path: Path,
) -> dict[str, object]:
    """Audit ALL native anchors; publish 24 time-stratified source receipts.

    No selection by pattern, win/loss, signal, spread or any price level.
    Physical source gaps and disagreements are counted, never hidden.
    All evidence is a *development source audit*, never holdout testing.
    """
    if market not in MARKETS or not m3_path.is_file() or not m15_path.is_file():
        raise ValueError("market or native source files invalid")
    m3_sha = hashlib.sha256(m3_path.read_bytes()).hexdigest()
    m15_sha = hashlib.sha256(m15_path.read_bytes()).hexdigest()
    _, parsed_market, _, _, m15 = load_market_evidence(m15_path)
    if parsed_market != market:
        raise ValueError("M15 source symbol mismatch")
    m3 = _load_m3(m3_path, expected_symbol=market)
    idx3 = {bar.opened_at.astimezone(UTC): bar for bar in m3}
    idx15 = {bar.opened_at.astimezone(UTC): bar for bar in m15}
    if len(idx3) != len(m3) or len(idx15) != len(m15):
        raise ValueError("duplicate source timestamps detected")
    valid_starts: list[datetime] = []
    observed_anchors = 0
    incomplete = 0
    mismatched = 0
    incomplete_sources: list[dict[str, object]] = []
    # Audit ALL source-visible Owner 01/05/09 anchors, outcome-blind.
    for when in sorted(idx3):
        local = when.astimezone(NY)
        if local.hour not in ANCHORS or local.minute or local.second or local.microsecond:
            continue
        observed_anchors += 1
        try:
            attest_anchor_window(
                market=market, m3_bars=idx3, m15_bars=idx15,
                opened_at=when, raw_m3_sha=m3_sha, raw_m15_sha=m15_sha,
            )
            valid_starts.append(when)
        except ValueError as exc:
            if "incomplete" in str(exc):
                incomplete += 1
                incomplete_sources.append({
                    "anchor_utc": _iso(when),
                    "missing_or_unclosed_m3_utc": [
                        _iso(when + timedelta(minutes=3*i)) for i in range(10)
                        if (when + timedelta(minutes=3*i)) not in idx3
                        or idx3[when + timedelta(minutes=3*i)].closed_at.astimezone(UTC)
                           != when + timedelta(minutes=3*(i+1))
                    ],
                    "missing_or_unclosed_m15_utc": [
                        _iso(when + timedelta(minutes=15*i)) for i in range(2)
                        if (when + timedelta(minutes=15*i)) not in idx15
                        or idx15[when + timedelta(minutes=15*i)].closed_at.astimezone(UTC)
                           != when + timedelta(minutes=15*(i+1))
                    ],
                })
            elif "disagree" in str(exc):
                mismatched += 1
            else:
                raise
    complete = len(valid_starts)
    if not valid_starts or observed_anchors != complete + incomplete + mismatched:
        raise ValueError("source census empty or first-failure counts inconsistent")
    # Deterministic chronological spread across whole already-consumed DEV
    # history. Never select a receipt by structure, pattern, trade or PnL.
    n = min(LIMIT_PER_MARKET, complete)
    positions = [0] if n == 1 else [
        i*(complete-1)//(n-1) for i in range(n)
    ]
    selected = [
        attest_anchor_window(
            market=market, m3_bars=idx3, m15_bars=idx15,
            opened_at=valid_starts[i], raw_m3_sha=m3_sha, raw_m15_sha=m15_sha,
        )
        for i in positions
    ]
    return {
        "schema": SCHEMA + ".inventory",
        "market": market,
        "scope": "DEV_RAW_SOURCE_CUSTODY_ONLY",
        "m3_raw_sha256": m3_sha, "m15_raw_sha256": m15_sha,
        "m3_bars_total": len(m3), "m15_bars_total": len(m15),
        "first_m3_at_utc": _iso(min(idx3)),
        "last_m3_at_utc": _iso(max(idx3)),
        "first_m15_at_utc": _iso(min(idx15)),
        "last_m15_at_utc": _iso(max(idx15)),
        "attested_windows": len(selected),
        "source_anchor_windows_observed": observed_anchors,
        "source_anchor_windows_complete": complete,
        "skipped_incomplete": incomplete,
        "skipped_mismatched": mismatched,
        "incomplete_source_windows": incomplete_sources,
        "sample_selection": "EQUALLY_SPACED_DEV_CHRONOLOGY_NO_OUTCOME",
        "receipts": selected,
        "author_fidelity_certified": False,
        "cognitive_certified": False,
        "economic_gates_evaluated": False,
        "sealed_holdout_accessed": False,
    }
