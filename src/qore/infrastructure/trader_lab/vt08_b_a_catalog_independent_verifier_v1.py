"""B-side raw custody audit of A's market-specific physical catalog.

Never imports an A producer, validates all bars against raw cTrader files,
and matches ALL R3 frozen positive C2 clocks. This is raw source evidence,
NOT TTrades methodological fidelity, cognitive source admission or fills.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_5m_b_independent_raw_receipts_v1 import (
    _instant,
    _raw_bars,
    _verify_bar,
)

NY = ZoneInfo("America/New_York")
SCHEMA = "qore.vt08.a_b.market_raw_custody_catalog.v1"
R3_STAGE = "UNIQUE_M3_CISD_PS_SHAPE_REQUIRES_AUTHOR_ADJUDICATION"
GROUPS = {
    "c1_m3_raw_bar_receipts": ("M3", 10),
    "c2_m3_raw_bar_receipts": ("M3", 10),
    "c2_m15_raw_bar_receipts": ("M15", 2),
    "pre_c2_h1_m15_raw_bar_receipts": ("M15", 12),
}
NOT_SIGNED_FLAGS = (
    "author_relevant_swing_verified",
    "author_poi_verified",
    "author_cisd_ps_verified",
    "author_breaker_verified",
    "author_target_verified",
    "cognitive_situation_27_fields_verified",
    "source_complete",
)
NO_AUTHS = (
    "author_fidelity_certified",
    "cognitive_certified",
    "economic_gates_certified",
    "independent_B_verified",
)


def _record(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, dict) or any(
        not isinstance(k, str) for k in value
    ):
        raise ValueError(f"VT08 B A-catalog {name} is not an object")
    return value


def _audit_one(
    catalog: Mapping[str, object], r3: Mapping[str, object],
    *, m3_file: Path, m15_file: Path,
) -> dict[str, object]:
    if catalog.get("schema") != SCHEMA:
        raise ValueError("VT08 B A-catalog wrong schema")
    market = catalog.get("market")
    if not isinstance(market, str) or r3.get("market") != market:
        raise ValueError("VT08 B A-catalog market identity drift")
    sha3, m3 = _raw_bars(m3_file, "M3", market)
    sha15, m15 = _raw_bars(m15_file, "M15", market)
    rawmap = _record(catalog.get("source_raw_market_map"), "raw SHA market map")
    if (
        catalog.get("pinned_raw_shas") != sorted((sha3, sha15))
        or rawmap != {sha3: market, sha15: market}
        or r3.get("source_m3_sha256") != sha3
        or r3.get("source_m15_sha256") != sha15
    ):
        raise ValueError("VT08 B A-catalog raw SHA custody not source-pinned")
    for field in NO_AUTHS:
        if catalog.get(field) is not False:
            raise ValueError(f"VT08 B A-catalog unauthorized semantic gate {field}")
    if (
        catalog.get("signed_A_B_manifest_sha256") is not None
        or catalog.get("pnl_evaluated") is not False
        or type(catalog.get("orders")) is not int
        or type(catalog.get("fills")) is not int
        or catalog.get("orders") != 0 or catalog.get("fills") != 0
    ):
        raise ValueError("VT08 B A-catalog manufactured authority or fills")
    rows = _record(catalog.get("bar_catalog"), "bar catalog")
    events = catalog.get("source_only_events")
    positive = _record(r3.get("examples_by_stage"), "R3 stages").get(R3_STAGE)
    if not isinstance(events, list) or not isinstance(positive, list):
        raise ValueError("VT08 B A-catalog no event inventory")
    if (
        type(catalog.get("source_only_event_count")) is not int
        or catalog["source_only_event_count"] != len(events)
        or type(catalog.get("catalog_unique_bars")) is not int
        or catalog["catalog_unique_bars"] != len(rows)
        or len(events) != len(positive)
    ):
        raise ValueError("VT08 B A-catalog missing events or bars")
    if not rows or not events:
        raise ValueError("VT08 B A-catalog empty raw source inventory")
    # Catalog entries are verified ONCE, each against the original raw bytes.
    for bar_id, datum in rows.items():
        bar = _record(datum, "bar")
        profile = bar.get("profile")
        if profile not in ("M3", "M15") or bar.get("market") != market:
            raise ValueError("VT08 B A-catalog cross-market or aliased profile")
        if bar.get("source_bar_id") != bar_id:
            raise ValueError("VT08 B A-catalog source bar key drift")
        opened = _instant(bar.get("opened_at_utc"))
        _verify_bar(
            bar, expected_open=opened, minutes=3 if profile == "M3" else 15,
            profile=profile,
            source_sha=sha3 if profile == "M3" else sha15,
            raw=m3 if profile == "M3" else m15,
        )

    by_clock: dict[datetime, Mapping[str, object]] = {}
    for source in positive:
        original = _record(source, "positive R3")
        if original.get("market") != market:
            raise ValueError("VT08 B A-catalog positive market contradiction")
        when = _instant(original.get("c2_opened_at_utc"))
        if when in by_clock:
            raise ValueError("VT08 B A-catalog repeated R3 positive C2")
        by_clock[when] = original

    observed_ids: set[str] = set()
    observed_times: set[datetime] = set()
    with_h1 = 0
    audit_groups = 0
    for item in events:
        event = _record(item, "event")
        if event.get("market") != market:
            raise ValueError("VT08 B A-catalog foreign market event")
        c2 = _instant(event.get("c2_opened_at_utc"))
        decision = _instant(event.get("decision_at_utc"))
        if c2 in observed_times or c2 not in by_clock:
            raise ValueError("VT08 B A-catalog missing/extra/duplicate source C2")
        observed_times.add(c2)
        original = by_clock[c2]
        if (
            event.get("decision_at_utc") is None
            or decision != c2 + timedelta(minutes=30)
            or decision != _instant(original.get("decision_at_utc"))
        ):
            raise ValueError("VT08 B A-catalog C3 decision clock not causal")
        local = c2.astimezone(NY)
        if not (1 <= local.hour < 13 and local.minute in (0, 30)):
            raise ValueError("VT08 B A-catalog source C2 outside frozen hours")
        for flag in NOT_SIGNED_FLAGS:
            if event.get(flag) is not False:
                raise ValueError(f"VT08 B A-catalog fake author complete {flag}")
        groups = _record(event.get("source_bar_groups"), "source bar groups")
        if set(groups) != set(GROUPS):
            raise ValueError("VT08 B A-catalog omitted source bar group")
        for name, (profile, n) in GROUPS.items():
            ids = groups[name]
            has_h1 = original.get("pre_c2_h1_context_available") is True
            count = n if name != "pre_c2_h1_m15_raw_bar_receipts" or has_h1 else 0
            if (
                not isinstance(ids, list) or len(ids) != count
                or len(set(str(x) for x in ids)) != len(ids)
            ):
                raise ValueError(f"VT08 B A-catalog missing bar IDs in {name}")
            if name.startswith("c1_"):
                begin = c2 - timedelta(minutes=30)
                cutoff = c2
            elif name.startswith("c2_"):
                begin = c2
                cutoff = decision
            else:
                begin = c2.replace(minute=0, second=0, microsecond=0) - timedelta(
                    hours=3
                )
                cutoff = c2
            step = timedelta(minutes=3 if profile == "M3" else 15)
            # Independent reconstruction from the market's native candles,
            # not from the event's caller-provided SHA or A's detector.
            for i, bar_id in enumerate(ids):
                if not isinstance(bar_id, str) or bar_id not in rows:
                    raise ValueError("VT08 B A-catalog source group foreign bar ID")
                bar = _record(rows[bar_id], "group bar")
                when = begin + i * step
                if (
                    bar.get("profile") != profile
                    or _instant(bar.get("opened_at_utc")) != when
                    or _instant(bar.get("available_at_utc")) != when + step
                    or when + step > cutoff
                ):
                    raise ValueError("VT08 B A-catalog future or wrong group clock")
                observed_ids.add(bar_id)
            audit_groups += 1
            if name == "pre_c2_h1_m15_raw_bar_receipts" and count == 12:
                with_h1 += 1
    if len(observed_times) != len(by_clock):
        raise ValueError("VT08 B A-catalog missing R3 positive event")
    if observed_ids != set(rows):
        raise ValueError("VT08 B A-catalog orphaned or unreferenced source bars")
    if (
        with_h1 != r3.get("unique_ps_proxy_cases_with_three_closed_pre_c2_h1")
        or len(observed_times) != r3.get("all_unique_proxy_cases_with_raw_receipts")
    ):
        raise ValueError("VT08 B A-catalog source R3 count disagreement")
    return {
        "schema": "qore.vt08.b.a_catalog_independent_audit.v1",
        "market": market,
        "native_m3_sha256": sha3,
        "native_m15_sha256": sha15,
        "source_only_events_reverified": len(observed_times),
        "unique_physical_bar_ids_reverified": len(rows),
        "event_source_groups_reverified": audit_groups,
        "events_with_full_pre_c2_h1": with_h1,
        "catalog_all_bars_linked": True,
        "a_catalog_reconstructed_from_raw": True,
        "independent_b_raw_audit_passed": True,
        "author_semantics_certified": False,
        "cognitive_real_admission_authorized": False,
        "economic_gates_evaluated": False,
        "holdout_accessed": False,
        "broker_authority": False,
    }


def verify_native_catalog(
    catalog: Mapping[str, object], r3: Mapping[str, object],
    *, m3_file: Path, m15_file: Path,
) -> dict[str, object]:
    """One sealed market; deterministic B-only physical audit."""
    return _audit_one(catalog, r3, m3_file=m3_file, m15_file=m15_file)


def manifest_sha256(document: Mapping[str, object]) -> str:
    """Canonical digest is evidence identity, never an A/B author signature."""
    return hashlib.sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
