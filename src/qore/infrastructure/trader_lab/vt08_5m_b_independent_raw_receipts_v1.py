"""B-independent raw M3/M15 verifier for Architect A VT08 window receipts.

The A producer module is NEVER imported. Verify raw file bytes, each cited
bar's exact OHLC/time and SHA, contiguous M30 aggregation and NY clocks.
This authenticates *data lineage*, NOT author POI/swing or economic edge.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

SCHEMA = "qore.vt08.a.m30m3.raw_bar_custody.v1"
MARKETS = frozenset(("EURJPY", "USDCHF", "NZDUSD", "CADJPY", "USDCAD"))
NY = ZoneInfo("America/New_York")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _record(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict) or not all(isinstance(k, str) for k in value):
        raise ValueError("VT08 B requires a JSON object")
    return value


def _instant(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("VT08 B timestamp must be offset-aware ISO string")
    try:
        when = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError("VT08 B invalid ISO time") from error
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError("VT08 B naive clock cannot establish source custody")
    return when.astimezone(UTC)


def _prices(raw: object) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        raise ValueError("VT08 B OHLC requires four prices")
    parsed: list[Decimal] = []
    for value in raw:
        if not isinstance(value, str):
            raise ValueError("VT08 B price must be source Decimal string")
        try:
            number = Decimal(value)
        except InvalidOperation as error:
            raise ValueError("VT08 B invalid price") from error
        if not number.is_finite() or number <= 0:
            raise ValueError("VT08 B non-finite/invalid source price")
        parsed.append(number)
    op, high, low, close = parsed
    if low > min(op, close) or high < max(op, close) or high < low:
        raise ValueError("VT08 B invalid OHLC geometry")
    return op, high, low, close


def _raw_bars(
    path: Path, profile: str, market: str
) -> tuple[str, dict[datetime, Mapping[str, object]]]:
    source = path.read_bytes()
    sha = hashlib.sha256(source).hexdigest()
    try:
        document = _record(json.loads(source))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("VT08 B cannot decode raw source") from error
    if (
        document.get("environment") != "demo"
        or document.get("read_only") is not True
        or document.get("account_is_live") is not False
        or _record(document.get("symbol")).get("symbol_name") != market
    ):
        raise ValueError("VT08 B rejected source feed identity/authority")
    if profile == "M3":
        if document.get("period") != "M3":
            raise ValueError("VT08 B source M3 period mismatch")
        source_bars = document.get("bars")
    else:
        source_bars = _record(document.get("periods")).get("M15")
    if not isinstance(source_bars, list):
        raise ValueError("VT08 B source bars missing")
    mapped: dict[datetime, Mapping[str, object]] = {}
    previous: datetime | None = None
    for item in source_bars:
        row = _record(item)
        start = _instant(row.get("opened_at"))
        end = _instant(row.get("closed_at"))
        if end - start != timedelta(minutes=3 if profile == "M3" else 15):
            raise ValueError("VT08 B source candle duration mismatch")
        if previous is not None and start <= previous:
            raise ValueError("VT08 B raw bars unsorted or duplicated")
        _prices(tuple(row.get(k) for k in ("open", "high", "low", "close")))
        mapped[start] = row
        previous = start
    return sha, mapped


def _verify_bar(
    observed: object,
    *,
    expected_open: datetime,
    minutes: int,
    profile: str,
    source_sha: str,
    raw: Mapping[datetime, Mapping[str, object]],
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    item = _record(observed)
    source_row = raw.get(expected_open)
    if source_row is None:
        raise ValueError("VT08 B referenced bar absent from real source")
    if item.get("profile") != profile or item.get("source_raw_sha256") != source_sha:
        raise ValueError("VT08 B raw source identity does not match receipt")
    opened = _instant(item.get("opened_at_utc"))
    closed = _instant(item.get("closed_at_utc"))
    available = _instant(item.get("available_at_utc"))
    if not (
        opened == expected_open
        and closed == available == expected_open + timedelta(minutes=minutes)
    ):
        raise ValueError("VT08 B source candle available_at/clock contradiction")
    values = _prices(item.get("ohlc"))
    exact_raw = _prices(tuple(str(source_row.get(k)) for k in ("open", "high", "low", "close")))
    if values != exact_raw:
        raise ValueError("VT08 B source receipt OHLC differs from raw")
    body = {
        "profile": profile,
        "source_raw_sha256": source_sha,
        "opened_at_utc": opened.isoformat(),
        "closed_at_utc": closed.isoformat(),
        "ohlc": tuple(str(v) for v in item.get("ohlc", ())),
    }
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if item.get("source_bar_id") != digest:
        raise ValueError("VT08 B source_bar_id invalid")
    if item.get("semantics") != "OBSERVED_OHLC_ONLY_NOT_TTRADES_RULE":
        raise ValueError("VT08 B source falsely promotes observed OHLC to author rule")
    return values


def _aggregate(rows: list[tuple[Decimal, Decimal, Decimal, Decimal]]) -> tuple[Decimal, ...]:
    return rows[0][0], max(x[1] for x in rows), min(x[2] for x in rows), rows[-1][3]


def verify_raw_window(
    receipt: Mapping[str, object], *, m3_file: Path, m15_file: Path
) -> dict[str, object]:
    """Fail closed on forged/partial A receipt without using A's implementation."""
    if receipt.get("schema") != SCHEMA:
        raise ValueError("VT08 B source receipt schema invalid")
    market = receipt.get("market")
    if not isinstance(market, str) or market not in MARKETS:
        raise ValueError("VT08 B market outside frozen universe")
    opened = _instant(receipt.get("m30_opened_at_utc"))
    local = opened.astimezone(NY)
    if (
        local.hour not in (1, 5, 9)
        or local.minute or local.second or local.microsecond
        or receipt.get("ny_anchor_hour") != local.hour
        or receipt.get("ny_date") != local.date().isoformat()
    ):
        raise ValueError("VT08 B owner anchor or NY date wrong")
    if _instant(receipt.get("m30_available_at_utc")) != opened + timedelta(minutes=30):
        raise ValueError("VT08 B M30 available before completion or inconsistent")
    for state, expected in (
        ("source_m30_cross_attested", True),
        ("source_author_fidelity_verified", False),
        ("cognitive_ready", False),
        ("broker_quotes_verified", False),
        ("pnl_measured", False),
        ("holdout_7y_accessed", False),
        ("source_complete_candidate_events", 0),
        ("orders", 0),
        ("fills", 0),
    ):
        value = receipt.get(state)
        if type(value) is not type(expected) or value != expected:
            raise ValueError("VT08 B custody receipt claims unauthorized certification")
    m3sha, m3raw = _raw_bars(m3_file, "M3", market)
    m15sha, m15raw = _raw_bars(m15_file, "M15", market)
    m3receipts = receipt.get("m3_bar_receipts")
    m15receipts = receipt.get("m15_bar_receipts")
    if not isinstance(m3receipts, list) or len(m3receipts) != 10:
        raise ValueError("VT08 B M3 receipts incomplete")
    if not isinstance(m15receipts, list) or len(m15receipts) != 2:
        raise ValueError("VT08 B M15 receipts incomplete")
    m3 = [
        _verify_bar(
            r, expected_open=opened + timedelta(minutes=3 * i), minutes=3,
            profile="M3", source_sha=m3sha, raw=m3raw,
        )
        for i, r in enumerate(m3receipts)
    ]
    m15 = [
        _verify_bar(
            r, expected_open=opened + timedelta(minutes=15 * i), minutes=15,
            profile="M15", source_sha=m15sha, raw=m15raw,
        )
        for i, r in enumerate(m15receipts)
    ]
    if _aggregate(m3) != _aggregate(m15):
        raise ValueError("VT08 B raw M3/M15 M30 OHLC disagree")
    if _aggregate(m3) != _prices(receipt.get("m30_ohlc")):
        raise ValueError("VT08 B claimed M30 OHLC differs from raw")
    return {
        "market": market,
        "m30_opened_at_utc": opened.isoformat(),
        "m3_raw_sha256": m3sha,
        "m15_raw_sha256": m15sha,
        "m3_bars_reverified": 10,
        "m15_bars_reverified": 2,
        "author_certified": False,
        "economic_certified": False,
        "operational_authority": False,
    }
