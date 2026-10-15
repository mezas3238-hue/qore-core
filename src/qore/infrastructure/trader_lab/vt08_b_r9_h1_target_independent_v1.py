"""VT08 B R9 independent native-M15 audit of A R6 untouched H1 targets.

Reconstructs every as-of-C3 observed H1 high without importing A producers.
Separates levels formed before C2 from levels born while C2 was open.
Neither class implies TTrades target relevance, an executable signal or PnL.
"""
from __future__ import annotations

import hashlib
import json
from collections import deque
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_5m_b_independent_raw_receipts_v1 import (
    _instant,
    _prices,
    _raw_bars,
)

TARGET_SCHEMA = "qore.vt08.a.observed_h1_untouched_high_witness.v1"
JOIN_SCHEMA = "qore.vt08.a.blind_three_source_review_join.v1"
M15 = timedelta(minutes=15)


def _id(bar: Mapping[str, object], sha: str) -> str:
    opened = _instant(bar.get("opened_at"))
    closed = _instant(bar.get("closed_at"))
    body = {
        "profile": "M15",
        "source_raw_sha256": sha,
        "opened_at_utc": opened.isoformat(),
        "closed_at_utc": closed.isoformat(),
        "ohlc": tuple(str(bar.get(k)) for k in ("open", "high", "low", "close")),
    }
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def independently_reconstruct(
    bars: Mapping[datetime, Mapping[str, object]],
    sha: str,
    requests: list[tuple[datetime, datetime]],
) -> list[list[dict[str, object]]]:
    """Source-only chronological scan; resets on any unobserved M15 gap."""
    ordered = sorted(bars.items())
    if requests != sorted(requests) or len(set(requests)) != len(requests):
        raise ValueError("B R9 duplicate/unsorted C2/C3 requests")
    active: list[tuple[datetime, datetime, Decimal, tuple[str, ...]]] = []
    group: deque[tuple[datetime, Decimal, str]] = deque(maxlen=4)
    last_close: datetime | None = None
    index = 0
    snapshots: list[list[dict[str, object]]] = []
    for c2, decision in requests:
        if decision - c2 != timedelta(minutes=30):
            raise ValueError("B R9 C3 decision is not C2 close")
        while index < len(ordered):
            opened, bar = ordered[index]
            closed = _instant(bar.get("closed_at"))
            if closed > decision:
                break
            if closed != opened + M15:
                raise ValueError("B R9 invalid native M15 duration")
            if last_close is not None and opened != last_close:
                active.clear()
                group.clear()
            _, high, _, _ = _prices(
                tuple(str(bar.get(k)) for k in ("open", "high", "low", "close"))
            )
            # Invalidate on equal touch, even by a partial current H1.
            active = [candidate for candidate in active if high < candidate[2]]
            group.append((opened, high, _id(bar, sha)))
            last_close = closed
            if closed.minute == 0 and closed.second == 0 and len(group) == 4:
                quartet = list(group)
                if all(
                    v[0] == closed - timedelta(hours=1) + i * M15
                    for i, v in enumerate(quartet)
                ):
                    active.append((
                        quartet[0][0], closed,
                        max(v[1] for v in quartet),
                        tuple(v[2] for v in quartet),
                    ))
            index += 1
        if last_close != decision:
            snapshots.append([])
            continue
        snapshots.append([
            {
                "high": str(level),
                "origin_h1_opened_at_utc": start.isoformat(),
                "origin_h1_available_at_utc": known.isoformat(),
                "origin_source_m15_bar_ids": list(ids),
                "continuity_since_origin": "OBSERVED_GAP_FREE_M15_ONLY",
                "author_target_relevance_verified": False,
            }
            for start, known, level, ids in active
        ])
    return snapshots


def audit_a_r6_r7_native(
    target: Mapping[str, object],
    joined: Mapping[str, object],
    *,
    market: str,
    m15_file: Path,
) -> dict[str, object]:
    """Compare full A inventories to independent native reconstruction."""
    if target.get("schema") != TARGET_SCHEMA or joined.get("schema") != JOIN_SCHEMA:
        raise ValueError("B R9 wrong A schema")
    if target.get("market") != market or joined.get("market") != market:
        raise ValueError("B R9 cross-market report")
    if (
        target.get("source_complete_entries") != 0
        or target.get("broker_fills") != 0
        or target.get("profit_factor") is not None
        or joined.get("source_complete_entries") != 0
        or joined.get("broker_fills") != 0
        or joined.get("profit_factor") is not None
        or joined.get("signed_A_B_manifest") is not None
        or joined.get("certified") is not False
    ):
        raise ValueError("B R9 manufactured certification or PnL")
    sha, raw = _raw_bars(m15_file, "M15", market)
    if target.get("input_m15_source_sha256") != sha:
        raise ValueError("B R9 raw M15 SHA mismatch")
    rows = target.get("witnesses")
    linked = joined.get("all_source_only_cases")
    if not isinstance(rows, list) or not isinstance(linked, list):
        raise ValueError("B R9 missing complete A inventories")
    if (
        not rows or len(rows) != len(linked)
        or len(rows) != target.get("frozen_source_events")
        or len(rows) != joined.get("frozen_event_count")
    ):
        raise ValueError("B R9 lost/duplicated case count")
    by_key: dict[tuple[datetime, datetime], Mapping[str, object]] = {}
    for item in linked:
        if not isinstance(item, dict) or item.get("market") != market:
            raise ValueError("B R9 foreign R7 case")
        key = (_instant(item.get("c2_opened_at_utc")), _instant(item.get("decision_at_utc")))
        if key in by_key:
            raise ValueError("B R9 duplicate R7 identity")
        by_key[key] = item
    by_case: dict[tuple[datetime, datetime], Mapping[str, object]] = {}
    for item in rows:
        if not isinstance(item, dict) or item.get("market") != market:
            raise ValueError("B R9 foreign R6 case")
        key = (_instant(item.get("c2_opened_at_utc")), _instant(item.get("decision_at_utc")))
        if key in by_case or key not in by_key:
            raise ValueError("B R9 duplicate/alien R6 case")
        by_case[key] = item
    if set(by_case) != set(by_key):
        raise ValueError("B R9 source universe differs")
    keys = sorted(by_case)
    expected = independently_reconstruct(raw, sha, keys)
    pre_c2 = 0
    newly_known_during_c2 = 0
    cases_no_pre_c2_level = 0
    count_only_one_pre_c2 = 0
    for key, physical in zip(keys, expected, strict=True):
        c2, decision = key
        witness = by_case[key]
        review = by_key[key]
        reported = witness.get("untouched_h1_high_candidates")
        linked_levels = review.get("source_unconsumed_h1_highs")
        if not isinstance(reported, list) or not isinstance(linked_levels, list):
            raise ValueError("B R9 missing target inventories")
        if (
            len(reported) != witness.get("witness_count")
            or len(linked_levels) != len(reported)
            or len(reported) != len(physical)
            or review.get("target_cardinality") != len(physical)
            or witness.get("author_target_selected") is not False
            or review.get("source_author_target_selected") is not False
        ):
            raise ValueError("B R9 target cardinality/authority drift")
        if reported != linked_levels:
            raise ValueError("B R9 R6/R7 target identity disagreement")
        close = Decimal(str(witness.get("c2_close_price_source_proxy")))
        if not close.is_finite() or close <= 0:
            raise ValueError("B R9 invalid C2 close")
        for actual, original in zip(reported, physical, strict=True):
            if not isinstance(actual, dict):
                raise ValueError("B R9 target non-object")
            for field, value in original.items():
                if field == "high":
                    if Decimal(str(actual.get(field))) != Decimal(str(value)):
                        raise ValueError("B R9 native target high differs")
                elif actual.get(field) != value:
                    raise ValueError(f"B R9 target source drift: {field}")
            if (Decimal(str(actual.get("high"))) > close) != (
                actual.get("higher_than_c2_close_proxy") is True
            ):
                raise ValueError("B R9 target-vs-C2-close drift")
            origin = _instant(actual.get("origin_h1_available_at_utc"))
            if origin > decision:
                raise ValueError("B R9 future H1 source")
        prior = sum(
            _instant(x["origin_h1_available_at_utc"]) <= c2 for x in physical
        )
        during = len(physical) - prior
        pre_c2 += prior
        newly_known_during_c2 += during
        cases_no_pre_c2_level += int(prior == 0)
        count_only_one_pre_c2 += int(prior == 1)
    return {
        "schema": "qore.vt08.b.r9.native_h1_target_independent_audit.v1",
        "market": market,
        "native_m15_sha256": sha,
        "all_cases_reconstructed": len(keys),
        "candidate_levels_known_before_c2": pre_c2,
        "candidate_levels_newly_known_during_c2": newly_known_during_c2,
        "cases_without_pre_c2_known_level": cases_no_pre_c2_level,
        "cases_with_exactly_one_pre_c2_known_level": count_only_one_pre_c2,
        "a_r6_r7_native_identical": True,
        "ttrades_target_relevance_certified": False,
        "cognitive_admission_authorized": False,
        "economic_gates_evaluated": False,
        "broker_fills": 0,
        "holdout_7y_accessed": False,
        "sizing_used": False,
    }
