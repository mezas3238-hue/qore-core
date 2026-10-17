"""B R3 source audit tests, independent of the A producer and shared PS."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.vt08_b_r3_frozen_source_independent_v1 import (
    POSITIVE_STAGE,
    verify_a_r3_raw_bundle,
)

T = datetime(2026, 1, 5, 6, tzinfo=UTC)


def _bar(time: datetime, minutes: int, *, is_c2: bool = False) -> dict[str, str]:
    high = "102" if is_c2 else "103"
    low = "98" if is_c2 else "99"
    return {
        "opened_at": time.isoformat(),
        "closed_at": (time + timedelta(minutes=minutes)).isoformat(),
        "open": "100", "high": high, "low": low, "close": "101",
    }


def _receipt(raw: dict[str, str], sha: str, profile: str) -> dict[str, object]:
    data: dict[str, object] = {
        "profile": profile, "source_raw_sha256": sha,
        "opened_at_utc": raw["opened_at"],
        "closed_at_utc": raw["closed_at"],
        "ohlc": tuple(raw[k] for k in ("open", "high", "low", "close")),
    }
    return {
        **data,
        "source_bar_id": hashlib.sha256(
            json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "available_at_utc": raw["closed_at"],
        "semantics": "OBSERVED_OHLC_ONLY_NOT_TTRADES_RULE",
    }


def _case(tmp_path: Path):
    m3 = [
        _bar(T - timedelta(minutes=30) + timedelta(minutes=3*i), 3)
        for i in range(10)
    ] + [
        _bar(T + timedelta(minutes=3*i), 3, is_c2=True)
        for i in range(10)
    ]
    m15 = [
        _bar(T - timedelta(hours=3) + timedelta(minutes=15*i), 15)
        for i in range(12)
    ] + [
        _bar(T + timedelta(minutes=15*i), 15, is_c2=True)
        for i in range(2)
    ]
    identity = {
        "environment": "demo", "read_only": True,
        "account_is_live": False, "symbol": {"symbol_name": "EURJPY"},
    }
    m3path, m15path = tmp_path / "m3.json", tmp_path / "m15.json"
    m3path.write_text(json.dumps({**identity, "period": "M3", "bars": m3}))
    m15path.write_text(json.dumps({**identity, "periods": {"M15": m15}}))
    sha3 = hashlib.sha256(m3path.read_bytes()).hexdigest()
    sha15 = hashlib.sha256(m15path.read_bytes()).hexdigest()
    case: dict[str, object] = {
        "market": "EURJPY",
        "family": "BULLISH_M30_C2_REVERSAL_M3_CISD_C3_POSITIONAL",
        "stage": POSITIVE_STAGE,
        "c1_opened_at_utc": (T - timedelta(minutes=30)).isoformat(),
        "c2_opened_at_utc": T.isoformat(),
        "decision_at_utc": (T + timedelta(minutes=30)).isoformat(),
        "ny_date": "2026-01-05",
        "source_m3_file_sha256": sha3,
        "source_m15_file_sha256": sha15,
        "c1_m3_raw_bar_receipts": [
            _receipt(x, sha3, "M3") for x in m3[:10]
        ],
        "c2_m3_raw_bar_receipts": [
            _receipt(x, sha3, "M3") for x in m3[10:]
        ],
        "c2_m15_raw_bar_receipts": [
            _receipt(x, sha15, "M15") for x in m15[12:]
        ],
        "pre_c2_h1_m15_raw_bar_receipts": [
            _receipt(x, sha15, "M15_PRE_C2_H1") for x in m15[:12]
        ],
        "pre_c2_h1_context_available": True,
        "reference_swing_author_relevance_validated": False,
        "A_rule_complete": False, "B_signoff": False,
        "cognitive_ready": False, "broker_fill": False, "pnl_read": False,
        "details": {
            "m3_ps_proxy_count": 1,
            "proxy_not_author_validated": True,
            "methodology_complete": False,
            "cisd_confirmed_at_utc": (T + timedelta(minutes=24)).isoformat(),
            "opposing_series_opened_at_utc": (T + timedelta(minutes=6)).isoformat(),
        },
    }
    report: dict[str, object] = {
        "schema": "qore.vt08.a.frozen_bullish_m30m3.source_funnel.v1",
        "market": "EURJPY",
        "source_m3_sha256": sha3,
        "source_m15_sha256": sha15,
        "c2_windows_total": 1,
        "stage_counts": {
            "MISSING_M30_M3_OR_M15": 0,
            "M30_CROSS_SOURCE_MISMATCH": 0,
            "C2_NOT_BULLISH_SINGLE_LOW_SWEEP": 0,
            "NO_M3_CISD_PS_SHAPE": 0,
            "MULTIPLE_M3_CISD_PS_SHAPES_D": 0,
            POSITIVE_STAGE: 1,
        },
        "examples_by_stage": {POSITIVE_STAGE: [case]},
        "all_unique_proxy_cases_with_raw_receipts": 1,
        "unique_ps_proxy_cases_with_three_closed_pre_c2_h1": 1,
        "distinct_ny_days_with_h1_and_unique_ps_proxy": 1,
        "earliest_unique_proxy_per_market_ny_day_upper_bound": 1,
        "A_B_signed_manifest": False,
        "pnl_evaluated": False, "sealed_holdout_accessed": False,
        "sizing_applied": False, "source_complete_entries": 0,
        "real_cognitive_admissions": 0, "fills": 0,
    }
    return report, m3path, m15path, case


def test_r3_full_positive_receipt_can_be_reverified_without_trade_authority(
    tmp_path: Path,
) -> None:
    report, m3, m15, _ = _case(tmp_path)
    audit = verify_a_r3_raw_bundle(report, m3, m15)
    assert audit["c2_windows_total"] == 1
    assert audit["all_positive_proxy_receipts_reverified"] == 1
    assert audit["pre_c2_h1_12bars_verified"] == 1
    assert audit["source_author_entries_certified"] == 0


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ("false_source_auth", "false source/trading authority"),
        ("future_cisd", "confirms after C3"),
        ("wrong_c2_bar_id", "source_bar_id invalid"),
        ("wrong_h1_bar_id", "source_bar_id invalid"),
        ("mixed_raw_sha", "source SHA mismatch"),
        ("omitted_positive", "missing any positive"),
        ("wrong_first_fail", "independent 93k C2 funnel"),
        ("future_h1_clock", "source candle available_at/clock contradiction"),
    ],
)
def test_r3_mixed_source_or_future_tampering_rejected(
    tmp_path: Path, change: str, expected: str
) -> None:
    report, m3, m15, case = _case(tmp_path)
    if change == "false_source_auth":
        case["A_rule_complete"] = True
    elif change == "future_cisd":
        details = case["details"]
        assert isinstance(details, dict)
        details["cisd_confirmed_at_utc"] = (T + timedelta(minutes=33)).isoformat()
    elif change == "wrong_c2_bar_id":
        items = case["c2_m3_raw_bar_receipts"]
        assert isinstance(items, list)
        items[0]["source_bar_id"] = "f" * 64
    elif change == "wrong_h1_bar_id":
        items = case["pre_c2_h1_m15_raw_bar_receipts"]
        assert isinstance(items, list)
        items[3]["source_bar_id"] = "f" * 64
    elif change == "mixed_raw_sha":
        report["source_m3_sha256"] = "b" * 64
    elif change == "omitted_positive":
        rows = report["examples_by_stage"]
        assert isinstance(rows, dict)
        rows[POSITIVE_STAGE] = []
    elif change == "wrong_first_fail":
        counts = report["stage_counts"]
        assert isinstance(counts, dict)
        counts["C2_NOT_BULLISH_SINGLE_LOW_SWEEP"] = 1
    elif change == "future_h1_clock":
        items = case["pre_c2_h1_m15_raw_bar_receipts"]
        assert isinstance(items, list)
        items[-1]["available_at_utc"] = (T + timedelta(minutes=3)).isoformat()
    with pytest.raises(ValueError, match=expected):
        verify_a_r3_raw_bundle(report, m3, m15)
