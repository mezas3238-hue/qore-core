"""TTrades written *basic* H1 swing points before frozen C2, no relevance claim.

The author defines a basic bullish swing low with a higher low to the left
and a higher low to the right (bearish high analog). The author explicitly
states that VALID SEPARATION and relevance have no strict numeric formula.
Three fully closed H1 before C2 are a source-only conservative QORE-C
inspection window, not an asserted universal TTrades swing selector.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Final

SOURCE: Final = "https://ttrades.com/relevant-swings-which-swing-highs-and-lows-matter-in-trading/"
SCHEMA: Final = "qore.vt08.a.pre_c2_h1_basic_swing_physical_witness.v1"
CATALOG: Final = "qore.vt08.a_b.market_raw_custody_catalog.v1"


def _parse(t: object) -> datetime:
    if not isinstance(t, str):
        raise ValueError("swing H1 source timestamp invalid")
    try:
        v = datetime.fromisoformat(t)
    except ValueError as exc:
        raise ValueError("swing source datetime invalid") from exc
    if v.utcoffset() is None:
        raise ValueError("swing source timezone absent")
    return v.astimezone(UTC)


def _values(raw: object) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    if not isinstance(raw, (tuple, list)) or len(raw) != 4:
        raise ValueError("swing candle missing physical OHLC")
    try:
        vals = tuple(Decimal(str(x)) for x in raw)
    except (TypeError, InvalidOperation, ValueError) as exc:
        raise ValueError("swing OHLC decimal invalid") from exc
    if any(not x.is_finite() or x <= 0 for x in vals):
        raise ValueError("swing source non-finite OHLC")
    o, h, low, close = vals
    if h < max(o, close) or low > min(o, close) or low > h:
        raise ValueError("swing candle source OHLC impossible")
    return o, h, low, close


def basic_swing_witnesses(source_catalog: Mapping[str, object]) -> dict[str, object]:
    """Compute strict centered 3-H1 basic swing from pre-C2 12-M15 only."""
    if source_catalog.get("schema") != CATALOG:
        raise ValueError("wrong frozen catalog schema")
    market = source_catalog.get("market")
    shas = source_catalog.get("pinned_raw_shas")
    raw_map = source_catalog.get("source_raw_market_map")
    bars = source_catalog.get("bar_catalog")
    events = source_catalog.get("source_only_events")
    if (
        not isinstance(market, str) or not isinstance(shas, list)
        or not isinstance(raw_map, dict) or set(shas) != set(raw_map)
        or any(m != market for m in raw_map.values())
        or not isinstance(bars, dict) or not isinstance(events, list)
        or len(events) != source_catalog.get("source_only_event_count")
    ):
        raise ValueError("frozen raw-market custody inconsistent")
    if (
        source_catalog.get("author_fidelity_certified") is not False
        or source_catalog.get("cognitive_certified") is not False
        or source_catalog.get("economic_gates_certified") is not False
        or source_catalog.get("orders") != 0
        or source_catalog.get("fills") != 0
        or source_catalog.get("pnl_evaluated") is not False
    ):
        raise ValueError("synthetic source claimed trade authority")
    record: list[dict[str, object]] = []
    incomplete = 0
    low_count = 0
    high_count = 0
    both = 0
    decisions: set[str] = set()
    for event in events:
        if not isinstance(event, dict) or event.get("market") != market:
            raise ValueError("cross-market H1 swing review event")
        if event.get("source_complete") is not False:
            raise ValueError("false complete TTrades source event")
        c2 = _parse(event.get("c2_opened_at_utc"))
        c3 = _parse(event.get("decision_at_utc"))
        if c3 - c2 != timedelta(minutes=30):
            raise ValueError("source C2/C3 time invalid")
        key = c3.isoformat()
        if key in decisions:
            raise ValueError("duplicate source C3 event")
        decisions.add(key)
        groups = event.get("source_bar_groups")
        if not isinstance(groups, dict):
            raise ValueError("H1 source bar group absent")
        ids = groups.get("pre_c2_h1_m15_raw_bar_receipts")
        if not isinstance(ids, list) or len(ids) not in (0, 12):
            raise ValueError("incomplete 3 H1 window mislabeled as complete")
        if not ids:
            incomplete += 1
            record.append({
                "market": market, "c2_opened_at_utc": c2.isoformat(),
                "decision_at_utc": key,
                "pre_c2_h1_complete": False,
                "basic_swing_bullish_low": False,
                "basic_swing_bearish_high": False,
                "author_relevant_swing_verified": False,
                "review_status": "INCOMPLETE_PHYSICAL_H1",
            })
            continue
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate physical H1 bar source")
        h1_end = c2.replace(minute=0, second=0, microsecond=0)
        start = h1_end - timedelta(hours=3)
        intervals: list[tuple[Decimal, Decimal, Decimal, Decimal]] = []
        for i, bar_id in enumerate(ids):
            raw = bars.get(bar_id)
            if not isinstance(raw, dict):
                raise ValueError("physical source H1 M15 missing")
            opened = _parse(raw.get("opened_at_utc"))
            closed = _parse(raw.get("closed_at_utc"))
            if (
                raw.get("profile") != "M15" or raw.get("market") != market
                or raw_map.get(raw.get("source_raw_sha256")) != market
                or raw.get("semantics") != "OBSERVED_OHLC_ONLY_NOT_TTRADES_RULE"
                or _parse(raw.get("available_at_utc")) != closed
                or opened != start + i * timedelta(minutes=15)
                or closed != opened + timedelta(minutes=15)
                or closed > c2
            ):
                raise ValueError("physical H1 pre-C2 custody/clock invalid")
            body = {
                "profile": "M15",
                "source_raw_sha256": raw["source_raw_sha256"],
                "opened_at_utc": opened.isoformat(),
                "closed_at_utc": closed.isoformat(),
                "ohlc": tuple(raw.get("ohlc", ())),
            }
            digest = hashlib.sha256(json.dumps(
                body, sort_keys=True, separators=(",", ":"), allow_nan=False,
            ).encode("utf-8")).hexdigest()
            if digest != bar_id or raw.get("source_bar_id") != bar_id:
                raise ValueError("physical H1 bar sha drift")
            intervals.append(_values(raw.get("ohlc")))
        hourly: list[tuple[Decimal, Decimal, Decimal, Decimal]] = []
        for j in range(3):
            quartet = intervals[j * 4:(j + 1) * 4]
            hourly.append((
                quartet[0][0],
                max(row[1] for row in quartet),
                min(row[2] for row in quartet),
                quartet[-1][3],
            ))
        mid = hourly[1]
        bullish_pivot = mid[2] < hourly[0][2] and mid[2] < hourly[2][2]
        bearish_pivot = mid[1] > hourly[0][1] and mid[1] > hourly[2][1]
        low_count += int(bullish_pivot)
        high_count += int(bearish_pivot)
        both += int(bullish_pivot and bearish_pivot)
        record.append({
            "market": market,
            "c2_opened_at_utc": c2.isoformat(),
            "decision_at_utc": key,
            "pre_c2_h1_complete": True,
            "h1_candle_available_at_utc": h1_end.isoformat(),
            "h1_ohlc": [
                [str(v) for v in quartet] for quartet in hourly
            ],
            "h1_source_bar_id_groups": [
                ids[0:4], ids[4:8], ids[8:12],
            ],
            "basic_swing_bullish_low": bullish_pivot,
            "basic_swing_bearish_high": bearish_pivot,
            "basic_pivot_h1_opened_at_utc": (
                start + timedelta(hours=1)
            ).isoformat(),
            "source_author_pivot_definition_observable": True,
            "source_author_valid_separation_established": False,
            "source_author_relevant_swing_verified": False,
            "eq_regime_authorized": False,
            "methodology_source_complete": False,
            "review_status": "BASIC_PIVOT_SHAPE_NOT_AUTHOR_RELEVANCE",
        })
    return {
        "schema": SCHEMA,
        "market": market,
        "source_reference": SOURCE,
        "input_contexts": len(record),
        "missing_pre_c2_h1_context": incomplete,
        "strict_3h1_bullish_basic_pivot_count": low_count,
        "strict_3h1_bearish_basic_pivot_count": high_count,
        "outside_h1_middle_bar_both_pivots": both,
        "review_witnesses": record,
        "source_complete": False,
        "cognitive_certified": False,
        "broker_fills": 0,
        "profit_factor": None,
        "sizing_used": False,
        "holdout_7y_accessed": False,
    }
