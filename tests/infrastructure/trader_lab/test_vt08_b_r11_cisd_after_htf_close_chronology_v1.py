"""R11 physical C2/CISD clock tests on isolated fake demo M3 bars."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.vt08_b_r11_cisd_after_htf_close_chronology_v1 import (
    STAGE,
    audit_cisd_htf_sequence,
)

M = "EURJPY"
T0 = datetime(2026, 3, 1, 12, tzinfo=UTC)


def _fixture(tmp_path: Path) -> tuple[dict[str, object], Path]:
    bars = []
    for i in range(20):
        start = T0 + timedelta(minutes=3 * i)
        bars.append({
            "opened_at": start.isoformat(),
            "closed_at": (start + timedelta(minutes=3)).isoformat(),
            "open": "120", "high": "121", "low": "119", "close": "120",
        })
    native = {
        "environment": "demo", "read_only": True, "account_is_live": False,
        "symbol": {"symbol_name": M}, "period": "M3", "bars": bars,
    }
    path = tmp_path / "m3.json"
    path.write_text(json.dumps(native), encoding="utf-8")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    cases = []
    for j in range(2):
        c2 = T0 + timedelta(minutes=30 * j)
        cutoff = c2 + timedelta(minutes=30)
        confirm = c2 + timedelta(minutes=15 if j == 0 else 30)
        receipts = []
        for i in range(10):
            original = bars[j * 10 + i]
            source = {
                "profile": "M3", "source_raw_sha256": sha,
                "opened_at_utc": original["opened_at"],
                "closed_at_utc": original["closed_at"],
                "ohlc": ("120", "121", "119", "120"),
            }
            rid = hashlib.sha256(json.dumps(
                source, sort_keys=True, separators=(",", ":")
            ).encode()).hexdigest()
            receipts.append({
                **source, "source_bar_id": rid, "market": M,
                "available_at_utc": original["closed_at"],
                "semantics": "OBSERVED_OHLC_ONLY_NOT_TTRADES_RULE",
            })
        cases.append({
            "market": M, "stage": STAGE,
            "c1_opened_at_utc": (c2 - timedelta(minutes=30)).isoformat(),
            "c2_opened_at_utc": c2.isoformat(),
            "decision_at_utc": cutoff.isoformat(),
            "A_rule_complete": False, "B_signoff": False,
            "cognitive_ready": False, "broker_fill": False, "pnl_read": False,
            "details": {
                "m3_ps_proxy_count": 1,
                "proxy_not_author_validated": True,
                "reference_swing_author_valid": False,
                "significant_poi_author_valid": False,
                "breaker_low_author_valid": False,
                "methodology_complete": False,
                "cisd_confirmed_at_utc": confirm.isoformat(),
                "opposing_series_opened_at_utc": c2.isoformat(),
            },
            "c2_m3_raw_bar_receipts": receipts,
        })
    return {
        "schema": "qore.vt08.a.frozen_bullish_m30m3.source_funnel.v1",
        "market": M,
        "source_m3_sha256": sha,
        "stage_counts": {STAGE: 2},
        "all_unique_proxy_cases_with_raw_receipts": 2,
        "examples_by_stage": {STAGE: cases},
    }, path


def _check(report: dict[str, object], path: Path) -> dict[str, object]:
    return audit_cisd_htf_sequence(report, expected_market=M, native_m3_file=path)


def test_two_cisd_clocks_one_before_one_simultaneous(tmp_path: Path) -> None:
    report, path = _fixture(tmp_path)
    result = _check(report, path)
    assert result["r3_unique_m3_proxy_source_cases"] == 2
    assert result["confirmed_while_c2_in_progress"] == 1
    assert result["confirmed_exactly_at_c2_close"] == 1
    assert result["confirmed_after_c2_close"] == 0
    assert result["minutes_before_c2_close_histogram"] == {"0": 1, "15": 1}
    assert result["source_author_complete_entries"] == 0


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("A_rule_complete", True, "masquerading"),
        ("B_signoff", True, "masquerading"),
        ("cognitive_ready", True, "masquerading"),
        ("broker_fill", True, "masquerading"),
        ("pnl_read", True, "masquerading"),
    ],
)
def test_never_promote_proxy(tmp_path: Path, field: str, value: object, message: str) -> None:
    report, path = _fixture(tmp_path)
    report["examples_by_stage"][STAGE][0][field] = value
    with pytest.raises(ValueError, match=message):
        _check(report, path)


def test_report_market_mismatch(tmp_path: Path) -> None:
    report, path = _fixture(tmp_path)
    report["market"] = "USDCHF"
    with pytest.raises(ValueError, match="identity"):
        _check(report, path)


def test_future_cisd_clock(tmp_path: Path) -> None:
    report, path = _fixture(tmp_path)
    report["examples_by_stage"][STAGE][0]["details"]["cisd_confirmed_at_utc"] = (
        T0 + timedelta(minutes=33)
    ).isoformat()
    with pytest.raises(ValueError, match="causal window"):
        _check(report, path)


def test_duplicated_c2(tmp_path: Path) -> None:
    report, path = _fixture(tmp_path)
    cases = report["examples_by_stage"][STAGE]
    cases[1] = dict(cases[0])
    with pytest.raises(ValueError, match="duplicate"):
        _check(report, path)


def test_raw_bar_tampering(tmp_path: Path) -> None:
    report, path = _fixture(tmp_path)
    report["examples_by_stage"][STAGE][0]["c2_m3_raw_bar_receipts"][3]["ohlc"] = (
        "120", "130", "119", "120",
    )
    with pytest.raises(ValueError, match="OHLC|digest|raw"):
        _check(report, path)


def test_proxy_m3_series_missing(tmp_path: Path) -> None:
    report, path = _fixture(tmp_path)
    report["examples_by_stage"][STAGE][1]["c2_m3_raw_bar_receipts"].pop()
    with pytest.raises(ValueError, match="10 native"):
        _check(report, path)


def test_report_cardinality_drift(tmp_path: Path) -> None:
    report, path = _fixture(tmp_path)
    report["stage_counts"][STAGE] = 1
    with pytest.raises(ValueError, match="universe"):
        _check(report, path)
