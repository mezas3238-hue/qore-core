"""R12 adversarial tests: physical formation != author temporal approval."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.vt08_b_r11_cisd_after_htf_close_chronology_v1 import (
    STAGE,
)
from qore.infrastructure.trader_lab.vt08_b_r12_dual_clock_cisd_source_v1 import (
    canonical_digest,
    dual_clock_cisd_source_gate,
)

M = "EURJPY"
T = datetime(2025, 4, 10, 12, tzinfo=UTC)


def source(tmp_path: Path) -> tuple[dict[str, object], Path]:
    candles = []
    for i in range(20):
        started = T + timedelta(minutes=3 * i)
        candles.append({
            "opened_at": started.isoformat(),
            "closed_at": (started + timedelta(minutes=3)).isoformat(),
            "open": "120", "high": "121", "low": "119", "close": "120",
        })
    native = {
        "environment": "demo", "read_only": True, "account_is_live": False,
        "period": "M3", "symbol": {"symbol_name": M}, "bars": candles,
    }
    p = tmp_path / "source-m3.json"
    p.write_text(json.dumps(native), encoding="utf-8")
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    records = []
    for j in range(2):
        c2 = T + j * timedelta(minutes=30)
        c3 = c2 + timedelta(minutes=30)
        conf = c2 + timedelta(minutes=15 if j == 0 else 30)
        receipts = []
        for i in range(10):
            c = candles[j * 10 + i]
            receipt = {
                "profile": "M3", "source_raw_sha256": sha,
                "opened_at_utc": c["opened_at"],
                "closed_at_utc": c["closed_at"],
                "ohlc": ("120", "121", "119", "120"),
            }
            digest = hashlib.sha256(json.dumps(
                receipt, sort_keys=True, separators=(",", ":"),
            ).encode()).hexdigest()
            receipts.append({
                **receipt, "source_bar_id": digest,
                "available_at_utc": c["closed_at"],
                "semantics": "OBSERVED_OHLC_ONLY_NOT_TTRADES_RULE",
            })
        records.append({
            "market": M, "stage": STAGE,
            "c1_opened_at_utc": (c2 - timedelta(minutes=30)).isoformat(),
            "c2_opened_at_utc": c2.isoformat(),
            "decision_at_utc": c3.isoformat(),
            "A_rule_complete": False, "B_signoff": False,
            "cognitive_ready": False, "broker_fill": False, "pnl_read": False,
            "details": {
                "m3_ps_proxy_count": 1, "proxy_not_author_validated": True,
                "reference_swing_author_valid": False,
                "significant_poi_author_valid": False,
                "breaker_low_author_valid": False,
                "methodology_complete": False,
                "cisd_confirmed_at_utc": conf.isoformat(),
                "opposing_series_opened_at_utc": c2.isoformat(),
            },
            "c2_m3_raw_bar_receipts": receipts,
        })
    return {
        "schema": "qore.vt08.a.frozen_bullish_m30m3.source_funnel.v1",
        "market": M, "source_m3_sha256": sha,
        "all_unique_proxy_cases_with_raw_receipts": 2,
        "stage_counts": {STAGE: 2}, "examples_by_stage": {STAGE: records},
    }, p


def test_dual_clock_both_jointly_available_only_at_c3(tmp_path: Path) -> None:
    r3, p = source(tmp_path)
    result = dual_clock_cisd_source_gate(r3, market=M, original_m3=p)
    assert result["full_r3_unique_source_cases"] == 2
    assert result["counts"] == {
        "cisds_formed_before_c2_closed": 1,
        "cisds_formed_simultaneously_with_c2_close": 1,
        "cisds_physically_formed_after_c2_close": 0,
        "joint_c2_and_m3_evidence_known_at_c3_open": 2,
    }
    a, b = result["all_case_clocks_before_outcome"]
    assert a["m3_cisd_before_c2_close"] is True
    assert b["m3_cisd_simultaneous_with_c2_close"] is True
    assert a["earliest_jointly_observable_at_utc"] == a["decision_at_utc"]
    assert result["author_temporal_interpretation"] == "D_UNADJUDICATED"
    assert result["author_complete_events"] == result["broker_fills"] == 0
    assert result["a_b_signed_manifest"] is None
    assert len(canonical_digest(result)) == 64


@pytest.mark.parametrize(
    ("field", "value"),
    [("A_rule_complete", True), ("B_signoff", True), ("broker_fill", True)],
)
def test_false_author_or_broker_rejected(
    tmp_path: Path, field: str, value: bool,
) -> None:
    r3, p = source(tmp_path)
    r3["examples_by_stage"][STAGE][0][field] = value
    with pytest.raises(ValueError, match="masquerading"):
        dual_clock_cisd_source_gate(r3, market=M, original_m3=p)


def test_fabricated_cisd_after_c2_not_accepted(tmp_path: Path) -> None:
    r3, p = source(tmp_path)
    c2 = T
    r3["examples_by_stage"][STAGE][0]["details"]["cisd_confirmed_at_utc"] = (
        c2 + timedelta(minutes=33)
    ).isoformat()
    with pytest.raises(ValueError, match="causal window"):
        dual_clock_cisd_source_gate(r3, market=M, original_m3=p)


def test_corrupt_native_original_fails_even_if_report_same(tmp_path: Path) -> None:
    r3, p = source(tmp_path)
    native = json.loads(p.read_text())
    native["bars"][0]["high"] = "140"
    p.write_text(json.dumps(native), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA mismatched"):
        dual_clock_cisd_source_gate(r3, market=M, original_m3=p)


def test_duplicate_and_future_source_receipts_not_admitted(tmp_path: Path) -> None:
    r3, p = source(tmp_path)
    r3["examples_by_stage"][STAGE][1] = dict(r3["examples_by_stage"][STAGE][0])
    with pytest.raises(ValueError, match="duplicate"):
        dual_clock_cisd_source_gate(r3, market=M, original_m3=p)
    r3, p = source(tmp_path)
    r3["examples_by_stage"][STAGE][1]["c2_m3_raw_bar_receipts"][0][
        "available_at_utc"
    ] = (T + timedelta(days=1)).isoformat()
    with pytest.raises(ValueError, match="available_at|clock"):
        dual_clock_cisd_source_gate(r3, market=M, original_m3=p)
