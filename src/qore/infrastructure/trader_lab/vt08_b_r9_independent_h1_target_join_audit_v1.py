"""R9 B independent native-M15 oracle for A R6 untouched highs and R7 joins.

Source-only research. Never import any A producer, read outcomes, select
author swings/targets, create fills, or promote a physical witness to a trade.
A separate B R7 audit already attests every frozen catalog source bar ID.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_5m_b_independent_raw_receipts_v1 import (
    _instant,
    _prices,
    _raw_bars,
)

MARKETS = frozenset(("EURJPY", "USDCHF", "NZDUSD", "CADJPY", "USDCAD"))
TARGET_SCHEMA = "qore.vt08.a.observed_h1_untouched_high_witness.v1"
JOIN_SCHEMA = "qore.vt08.a.blind_three_source_review_join.v1"
CATALOG_SCHEMA = "qore.vt08.a_b.market_raw_custody_catalog.v1"
INCOMPLETE = "MISSING_PRE_C2_H1_SOURCE"
NO_PIVOT = "NO_CLOSED_THREE_H1_BULLISH_BASIC_PIVOT_SHAPE"
NO_TARGET = "NO_UNTOUCHED_H1_HIGH_IN_OBSERVED_SEGMENT"
MULTIPLE = "MULTIPLE_UNTOUCHED_H1_HIGHS_D"
REVIEW = "UNIQUE_OBSERVED_H1_HIGH_AND_BASIC_PIVOT_FOR_BLIND_REVIEW_ONLY"
STEP = timedelta(minutes=15)


def canonical_sha256(report: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()


def _items(value: object, label: str) -> list[dict[str, object]]:
    if not isinstance(value, list) or any(not isinstance(x, dict) for x in value):
        raise ValueError(f"R9 missing {label} rows")
    return value


def _identity(row: dict[str, object], market: str) -> tuple[datetime, datetime]:
    if row.get("market") != market:
        raise ValueError("R9 cross-market source identity")
    c2 = _instant(row.get("c2_opened_at_utc"))
    c3 = _instant(row.get("decision_at_utc"))
    if c3 - c2 != timedelta(minutes=30):
        raise ValueError("R9 future or distorted C2/C3 clock")
    return c2, c3


def _index(rows: object, market: str, label: str) -> dict[tuple[datetime, datetime], dict[str, object]]:
    found: dict[tuple[datetime, datetime], dict[str, object]] = {}
    for row in _items(rows, label):
        k = _identity(row, market)
        if k in found:
            raise ValueError(f"R9 repeated {label} identity")
        found[k] = row
    return found


def _receipt_id(row: dict[str, object], opened: datetime, sha: str) -> str:
    """B-native bar fingerprint, never accepts an identity supplied by A."""
    close = _instant(row.get("closed_at"))
    if _instant(row.get("opened_at")) != opened or close != opened + STEP:
        raise ValueError("R9 native M15 clock invalid")
    ohlc = tuple(str(v) for v in _prices(
        tuple(str(row.get(k)) for k in ("open", "high", "low", "close"))
    ))
    payload = {
        "profile": "M15", "source_raw_sha256": sha,
        "opened_at_utc": opened.isoformat(),
        "closed_at_utc": close.isoformat(), "ohlc": ohlc,
    }
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def _source_bars(
    original: dict[datetime, dict[str, object]], sha: str,
) -> tuple[list[tuple[datetime, Decimal, Decimal, Decimal, str]], list[int]]:
    bars: list[tuple[datetime, Decimal, Decimal, Decimal, str]] = []
    segments: list[int] = []
    prior: datetime | None = None
    segment = 0
    for start, row in sorted(original.items()):
        if prior is not None and start != prior + STEP:
            if start <= prior:
                raise ValueError("R9 duplicate/out of order original M15")
            segment += 1  # physical observation gap: quarantine older levels
        _, high, low, close = _prices(
            tuple(str(row.get(k)) for k in ("open", "high", "low", "close"))
        )
        bars.append((start, high, low, close, _receipt_id(row, start, sha)))
        segments.append(segment)
        prior = start
    if not bars:
        raise ValueError("R9 empty native M15")
    return bars, segments


def audit_native_r9(
    *, market: str, catalog: dict[str, object],
    target: dict[str, object], joined: dict[str, object],
    native: dict[datetime, dict[str, object]], raw_sha: str,
) -> dict[str, object]:
    """Reconstruct ALL target highs from native bars and R7 pivot from 12 M15."""
    if market not in MARKETS or any(x.get("market") != market for x in (catalog, target, joined)):
        raise ValueError("R9 wrong market")
    if (catalog.get("schema"), target.get("schema"), joined.get("schema")) != (
        CATALOG_SCHEMA, TARGET_SCHEMA, JOIN_SCHEMA,
    ):
        raise ValueError("R9 source schema changed")
    if catalog.get("source_raw_market_map", {}).get(raw_sha) != market or target.get(
        "input_m15_source_sha256"
    ) != raw_sha:
        raise ValueError("R9 original M15 SHA not pinned to market")
    for record in (target, joined):
        if (record.get("source_complete_entries") != 0 or record.get("broker_fills") != 0
                or record.get("profit_factor") is not None or record.get("certified") is not False
                or record.get("sizing_used") is not False or record.get("holdout_7y_accessed") is not False):
            raise ValueError("R9 economic/author claim in physical source-only audit")
    if joined.get("signed_A_B_manifest") is not None or joined.get(
        "B_independent_semantic_review_complete"
    ) is not False:
        raise ValueError("R9 fabricated independent author signature")
    src = _index(catalog.get("source_only_events"), market, "catalog")
    dst = _index(target.get("witnesses"), market, "target")
    blind = _index(joined.get("all_source_only_cases"), market, "join")
    if not src or set(src) != set(dst) or set(src) != set(blind):
        raise ValueError("R9 lost/added physical source events")
    if not (len(src) == catalog.get("source_only_event_count")
            == target.get("frozen_source_events") == joined.get("frozen_event_count")):
        raise ValueError("R9 mismatched source population")
    bars, segments = _source_bars(native, raw_sha)
    where = {x[0]: i for i, x in enumerate(bars)}
    # Independent construction of physical H1 origins: four contiguous M15
    # finishing on the hour, strictly inside the same observed segment.
    origins: list[tuple[int, Decimal, list[str]]] = []
    for i in range(3, len(bars)):
        end = bars[i][0] + STEP
        if end.minute != 0 or end.second or end.microsecond:
            continue
        if segments[i] != segments[i - 3]:
            continue
        origins.append((
            i, max(x[1] for x in bars[i - 3:i + 1]),
            [x[4] for x in bars[i - 3:i + 1]],
        ))
    by_segment: dict[int, list[tuple[int, Decimal, list[str]]]] = {}
    for origin in origins:
        by_segment.setdefault(segments[origin[0]], []).append(origin)
    classes: Counter[str] = Counter()
    checked_levels = 0
    missing_h1 = 0
    for (c2, decision), case in sorted(src.items()):
        witness = dst[(c2, decision)]
        review = blind[(c2, decision)]
        if case.get("source_complete") is not False:
            raise ValueError("R9 source-only candidate promoted")
        k = where.get(decision - STEP)
        if k is None or bars[k][0] + STEP != decision:
            raise ValueError("R9 missing complete native M15 at C3 cutoff")
        if c2 not in where or c2 + STEP not in where:
            raise ValueError("R9 missing C2 native pair")
        n1, n2 = where[c2], where[c2 + STEP]
        if n2 != n1 + 1 or k != n2:
            raise ValueError("R9 C3 cutoff and native C2 M15 not aligned")
        c2close = bars[n2][3]
        high = max(bars[n1][1], bars[n2][1])
        low = min(bars[n1][2], bars[n2][2])
        if Decimal(str(witness.get("c2_close_price_source_proxy"))) != c2close:
            raise ValueError("R9 C2 close proxy altered")
        if Decimal(str(review.get("c2_eq_full_conditional"))) != (high + low) / 2:
            raise ValueError("R9 full EQ tampered")
        if Decimal(str(review.get("c2_eq_close_to_low_conditional"))) != (c2close + low) / 2:
            raise ValueError("R9 against EQ tampered")
        # Walk backwards from cutoff. Suffix max is known for each H1 origin;
        # a later high EQUAL to the level invalidates untouched.
        suffix: dict[int, Decimal] = {}
        max_after: Decimal | None = None
        j = k
        while j >= 0 and segments[j] == segments[k]:
            if max_after is not None:
                suffix[j] = max_after
            max_after = bars[j][1] if max_after is None else max(max_after, bars[j][1])
            j -= 1
        expected: list[tuple[Decimal, datetime, list[str]]] = []
        for idx, price, ids in by_segment.get(segments[k], []):
            if idx > k:
                break
            if idx in suffix and suffix[idx] >= price:
                continue
            expected.append((price, bars[idx][0] + STEP, ids))
        levels = _items(witness.get("untouched_h1_high_candidates"), "H1 levels")
        if witness.get("witness_count") != len(expected) or len(levels) != len(expected):
            raise ValueError("R9 source H1 untouched cardinality divergence")
        for got, (price, closed, ids) in zip(levels, expected, strict=True):
            checked_levels += 1
            if (Decimal(str(got.get("high"))) != price
                    or _instant(got.get("origin_h1_available_at_utc")) != closed
                    or _instant(got.get("origin_h1_opened_at_utc")) != closed - timedelta(hours=1)
                    or list(got.get("origin_source_m15_bar_ids", [])) != ids
                    or got.get("higher_than_c2_close_proxy") is not (price > c2close)
                    or got.get("continuity_since_origin") != "OBSERVED_GAP_FREE_M15_ONLY"
                    or got.get("author_target_relevance_verified") is not False):
                raise ValueError("R9 altered/future/foreign native H1 target")
        if review.get("source_unconsumed_h1_highs") != levels or review.get(
            "target_cardinality"
        ) != len(levels):
            raise ValueError("R9 triple join loses/changes H1 target lineage")
        groups = case.get("source_bar_groups")
        if not isinstance(groups, dict):
            raise ValueError("R9 missing frozen source bar groups")
        ids = groups.get("pre_c2_h1_m15_raw_bar_receipts")
        if not isinstance(ids, list) or len(ids) not in (0, 12):
            raise ValueError("R9 invalid previous 3H1 source groups")
        available = len(ids) == 12
        pivot_low = pivot_high = False
        if available:
            if len(set(ids)) != 12:
                raise ValueError("R9 duplicate previous H1 M15")
            # H1 group ends at whole-hour PRE-C2, not the C2 close.
            h1end = c2.replace(minute=0, second=0, microsecond=0)
            start = h1end - timedelta(hours=3)
            three: list[tuple[Decimal, Decimal]] = []
            for h in range(3):
                block = []
                for m in range(4):
                    opened = start + timedelta(hours=h, minutes=15 * m)
                    i = where.get(opened)
                    if i is None or bars[i][4] != ids[h * 4 + m] or opened + STEP > c2:
                        raise ValueError("R9 3H1 origin/time or native bar SHA invalid")
                    block.append(bars[i])
                three.append((max(x[1] for x in block), min(x[2] for x in block)))
            pivot_low = three[1][1] < min(three[0][1], three[2][1])
            pivot_high = three[1][0] > max(three[0][0], three[2][0])
            if review.get("h1_swing_source_ids") != [
                ids[:4], ids[4:8], ids[8:12],
            ]:
                raise ValueError("R9 swing triple join bar IDs diverge")
        else:
            missing_h1 += 1
            if review.get("h1_swing_source_ids") != []:
                raise ValueError("R9 incomplete H1 incorrectly imputed")
        if (review.get("pre_c2_three_h1_physically_complete") is not available
                or review.get("basic_bullish_h1_pivot") is not pivot_low
                or review.get("basic_bearish_h1_pivot") is not pivot_high):
            raise ValueError("R9 basic physical H1 pivot falsified")
        label = (INCOMPLETE if not available else
                 NO_PIVOT if not pivot_low else
                 NO_TARGET if not expected else
                 MULTIPLE if len(expected) > 1 else REVIEW)
        if review.get("diagnostic_review_class") != label:
            raise ValueError("R9 full universe class/bucket mismatch")
        for authority in (
            "source_author_relevant_swing_verified", "source_author_target_selected",
            "source_author_breaker_verified", "source_author_ps_cisd_verified",
            "source_author_poi_verified", "methodology_source_complete",
            "cognitive_verified", "broker_fill_verified",
        ):
            if review.get(authority) is not False:
                raise ValueError("R9 false source/cognitive/broker permission")
        if review.get("author_adjudication") != "NOT_STARTED_D":
            raise ValueError("R9 disguised TTrades adjudication")
        classes[label] += 1
    if joined.get("category_counts") != {
        name: classes[name] for name in (INCOMPLETE, NO_PIVOT, NO_TARGET, MULTIPLE, REVIEW)
    }:
        raise ValueError("R9 reported category counts differ from native calculation")
    return {
        "market": market,
        "source_events_audited": len(src),
        "native_m15_sha256": raw_sha,
        "r6_native_high_levels_checked": checked_levels,
        "r7_three_h1_incomplete": missing_h1,
        "r7_physical_classes": dict(classes),
        "source_method_author_validated": False,
        "approved_a_b_manifest_sha256": None,
        "source_complete_entries": 0,
        "broker_fills": 0,
        "economic_gates_evaluated": False,
        "holdout_7y_accessed": False,
        "sizing_used": False,
        "verdict": "SOURCE_PHYSICAL_ONLY_NO_CERTIFICATION",
    }


def run_from_files(
    *, market: str, catalog_path: Path, target_path: Path,
    join_path: Path, m15_path: Path,
) -> dict[str, object]:
    sha, native = _raw_bars(m15_path, "M15", market)
    return audit_native_r9(
        market=market,
        catalog=json.loads(catalog_path.read_text(encoding="utf-8")),
        target=json.loads(target_path.read_text(encoding="utf-8")),
        joined=json.loads(join_path.read_text(encoding="utf-8")),
        native={k: dict(v) for k, v in native.items()}, raw_sha=sha,
    )
