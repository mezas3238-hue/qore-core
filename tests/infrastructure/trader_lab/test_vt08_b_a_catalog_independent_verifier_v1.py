"""B-only physical catalog audit: forged source maps and group linking fail."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from test_vt08_b_r3_frozen_source_independent_v1 import _case

from qore.infrastructure.trader_lab.vt08_b_a_catalog_independent_verifier_v1 import (
    verify_native_catalog,
)


def _test_case(tmp_path: Path):
    r3, m3, m15, example = _case(tmp_path)
    raw3 = json.loads(m3.read_text())["bars"]
    raw15 = json.loads(m15.read_text())["periods"]["M15"]
    sha3 = hashlib.sha256(m3.read_bytes()).hexdigest()
    sha15 = hashlib.sha256(m15.read_bytes()).hexdigest()
    records: dict[str, dict[str, object]] = {}

    def ins(item: dict[str, str], profile: str, digest: str) -> str:
        body = {
            "profile": profile,
            "source_raw_sha256": digest,
            "opened_at_utc": item["opened_at"],
            "closed_at_utc": item["closed_at"],
            "ohlc": tuple(item[k] for k in ("open", "high", "low", "close")),
        }
        bar_id = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        records[bar_id] = {
            **body, "source_bar_id": bar_id,
            "available_at_utc": item["closed_at"],
            "market": "EURJPY",
            "semantics": "OBSERVED_OHLC_ONLY_NOT_TTRADES_RULE",
        }
        return bar_id

    ids3 = [ins(x, "M3", sha3) for x in raw3]
    ids15 = [ins(x, "M15", sha15) for x in raw15]
    clock = example["c2_opened_at_utc"]
    event = {
        "market": "EURJPY",
        "c2_opened_at_utc": clock,
        "decision_at_utc": example["decision_at_utc"],
        "source_bar_groups": {
            "c1_m3_raw_bar_receipts": ids3[:10],
            "c2_m3_raw_bar_receipts": ids3[10:],
            "c2_m15_raw_bar_receipts": ids15[12:],
            "pre_c2_h1_m15_raw_bar_receipts": ids15[:12],
        },
        "author_relevant_swing_verified": False,
        "author_poi_verified": False,
        "author_cisd_ps_verified": False,
        "author_breaker_verified": False,
        "author_target_verified": False,
        "cognitive_situation_27_fields_verified": False,
        "source_complete": False,
    }
    catalog = {
        "schema": "qore.vt08.a_b.market_raw_custody_catalog.v1",
        "market": "EURJPY",
        "source_raw_market_map": {sha3: "EURJPY", sha15: "EURJPY"},
        "pinned_raw_shas": sorted([sha3, sha15]),
        "bar_catalog": records,
        "source_only_events": [event],
        "catalog_unique_bars": len(records),
        "source_only_event_count": 1,
        "author_fidelity_certified": False,
        "cognitive_certified": False,
        "economic_gates_certified": False,
        "independent_B_verified": False,
        "signed_A_B_manifest_sha256": None,
        "pnl_evaluated": False,
        "orders": 0,
        "fills": 0,
    }
    return catalog, r3, m3, m15


def _run(catalog, r3, m3, m15):
    return verify_native_catalog(catalog, r3, m3_file=m3, m15_file=m15)


def test_independent_full_catalog_binds_every_bar_and_source_group(
    tmp_path: Path,
) -> None:
    catalog, r3, m3, m15 = _test_case(tmp_path)
    result = _run(catalog, r3, m3, m15)
    assert result["unique_physical_bar_ids_reverified"] == 34
    assert result["source_only_events_reverified"] == 1
    assert result["events_with_full_pre_c2_h1"] == 1
    assert result["event_source_groups_reverified"] == 4
    assert result["catalog_all_bars_linked"]
    assert not result["cognitive_real_admission_authorized"]
    assert not result["economic_gates_evaluated"]


@pytest.mark.parametrize(
    ("attack", "expected"),
    [
        ("cross_market", "cross-market"),
        ("fake_raw_sha", "raw SHA custody"),
        ("fake_bar_id", "source bar key drift"),
        ("changed_ohlc", "source_bar_id invalid"),
        ("extra_orphan", "orphaned"),
        ("wrong_group", "future or wrong group clock"),
        ("missing_event", "missing events or bars"),
        ("missing_h1", "missing bar IDs"),
        ("fake_author", "fake author complete"),
        ("fake_fill", "manufactured authority"),
        ("duplicate_event", "missing events or bars"),
        ("wrong_market_map", "raw SHA custody"),
    ],
)
def test_catalog_forgery_rejected(
    tmp_path: Path, attack: str, expected: str
) -> None:
    catalog, r3, m3, m15 = _test_case(tmp_path)
    bars = catalog["bar_catalog"]
    events = catalog["source_only_events"]
    assert isinstance(bars, dict) and isinstance(events, list)
    event = events[0]
    if attack == "cross_market":
        next(iter(bars.values()))["market"] = "USDCHF"
    elif attack == "fake_raw_sha":
        catalog["pinned_raw_shas"] = ["c" * 64, "d" * 64]
    elif attack == "fake_bar_id":
        next(iter(bars.values()))["source_bar_id"] = "e" * 64
    elif attack == "changed_ohlc":
        next(iter(bars.values()))["ohlc"] = ("100", "110", "99", "101")
    elif attack == "extra_orphan":
        item = dict(next(iter(bars.values())))
        bars["d" * 64] = item
        catalog["catalog_unique_bars"] = len(bars)
    elif attack == "wrong_group":
        groups = event["source_bar_groups"]
        groups["c1_m3_raw_bar_receipts"][0] = groups["c2_m3_raw_bar_receipts"][0]
    elif attack == "missing_event":
        events.clear()
        catalog["source_only_event_count"] = 0
    elif attack == "missing_h1":
        event["source_bar_groups"]["pre_c2_h1_m15_raw_bar_receipts"] = []
    elif attack == "fake_author":
        event["author_relevant_swing_verified"] = True
    elif attack == "fake_fill":
        catalog["fills"] = 1
    elif attack == "duplicate_event":
        events.append(dict(event))
    elif attack == "wrong_market_map":
        sha = next(iter(catalog["source_raw_market_map"]))
        catalog["source_raw_market_map"][sha] = "CADJPY"
    with pytest.raises(ValueError, match=expected):
        _run(catalog, r3, m3, m15)


def test_independent_source_catalog_detects_changed_physical_raw(
    tmp_path: Path,
) -> None:
    catalog, r3, m3, m15 = _test_case(tmp_path)
    m3.write_bytes(m3.read_bytes() + b" ")
    with pytest.raises(ValueError, match="raw SHA custody"):
        _run(catalog, r3, m3, m15)
