"""VT08 B R13 native bars and M30 pivot timing adversarial contracts."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import vt08_b_r13_m30_swept_pivot_temporal_v1 as r13

T = datetime(2025, 5, 8, 8, tzinfo=UTC)
M = "EURJPY"


def fixture(tmp_path: Path, monkeypatch):
    m3_bars = []
    for i in range(20):
        when = T + i * timedelta(minutes=3)
        on_c2 = i >= 10
        low = "98" if i == 10 else ("99" if on_c2 else "99")
        high = "101" if on_c2 else "102"
        close = "100.5" if i == 19 else "100"
        m3_bars.append({
            "opened_at": when.isoformat(),
            "closed_at": (when + timedelta(minutes=3)).isoformat(),
            "open": "100", "high": high, "low": low, "close": close,
        })
    m15_bars = [
        {
            "opened_at": (T + i * timedelta(minutes=15)).isoformat(),
            "closed_at": (T + (i + 1) * timedelta(minutes=15)).isoformat(),
            "open": "100", "high": "101" if i >= 2 else "102",
            "low": "98" if i == 2 else "99",
            "close": "100.5" if i == 3 else "100",
        }
        for i in range(4)
    ]
    def write(name, rows, period):
        p = tmp_path / name
        p.write_text(json.dumps({
            "environment": "demo", "read_only": True,
            "account_is_live": False, "symbol": {"symbol_name": M},
            **({"period": period, "bars": rows} if period == "M3"
               else {"periods": {"M15": rows}}),
        }), encoding="utf-8")
        return p, hashlib.sha256(p.read_bytes()).hexdigest()
    p3, sha3 = write("m3.json", m3_bars, "M3")
    p15, sha15 = write("m15.json", m15_bars, "M15")
    monkeypatch.setitem(r13.PINNED_M15, M, sha15)

    def receipts(bars, start, stop, sha, period):
        result = []
        for b in bars[start:stop]:
            body = {
                "profile": period, "source_raw_sha256": sha,
                "opened_at_utc": b["opened_at"],
                "closed_at_utc": b["closed_at"],
                "ohlc": tuple(b[k] for k in ("open","high","low","close")),
            }
            checksum = hashlib.sha256(json.dumps(
                body, sort_keys=True, separators=(",", ":"),
            ).encode()).hexdigest()
            result.append({
                **body, "source_bar_id": checksum,
                "available_at_utc": b["closed_at"],
                "semantics": "OBSERVED_OHLC_ONLY_NOT_TTRADES_RULE",
            })
        return result
    c2 = T + timedelta(minutes=30)
    c3 = c2 + timedelta(minutes=30)
    case = {
        "market": M, "stage": r13.STAGE,
        "c1_opened_at_utc": T.isoformat(),
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
            "cisd_confirmed_at_utc": (c2 + timedelta(minutes=15)).isoformat(),
            "opposing_series_opened_at_utc": c2.isoformat(),
        },
        "c1_m3_raw_bar_receipts": receipts(m3_bars, 0, 10, sha3, "M3"),
        "c2_m3_raw_bar_receipts": receipts(m3_bars, 10, 20, sha3, "M3"),
        "c2_m15_raw_bar_receipts": receipts(m15_bars, 2, 4, sha15, "M15"),
    }
    report = {
        "schema": "qore.vt08.a.frozen_bullish_m30m3.source_funnel.v1",
        "market": M, "source_m3_sha256": sha3, "source_m15_sha256": sha15,
        "stage_counts": {r13.STAGE: 1},
        "all_unique_proxy_cases_with_raw_receipts": 1,
        "examples_by_stage": {r13.STAGE: [case]},
    }
    return report, p3, p15


def run(report, m3, m15):
    return r13.audit_m30_pivot_temporal_non_equivalence(
        report, market=M, original_m3=m3, original_m15=m15,
    )


def test_c1_three_m30_pivot_impossible_from_real_low_sweep(
    tmp_path: Path, monkeypatch,
) -> None:
    report, m3, m15 = fixture(tmp_path, monkeypatch)
    result = run(report, m3, m15)
    assert result["frozen_events"] == 1
    row = result["all_case_native_clock_witnesses"][0]
    assert row["c1_low_native"] == "99"
    assert row["c2_low_native"] == "98"
    assert row["c1_center_pivot_right_side_pass"] is False
    assert row["c2_center_m30_pivot_right_side_asof_c3_open"] is None
    assert row["c2_center_m30_pivot_earliest_confirmation_at_utc"] == (
        T + timedelta(minutes=90)
    ).isoformat()
    assert result["counts"]["bullish_c2_source_closure_physical"] == 1
    assert result["ttrades_protected_swing_validated"] is False
    assert result["fills"] == 0
    assert len(r13.result_sha256(result)) == 64


def test_fake_m15_low_sweep_gets_rejected(tmp_path: Path, monkeypatch) -> None:
    report, m3, m15 = fixture(tmp_path, monkeypatch)
    d = json.loads(m15.read_text())
    d["periods"]["M15"][2]["low"] = "100"
    m15.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(ValueError, match="digest"):
        run(report, m3, m15)


def test_m15_receipt_tampering_cannot_pass(tmp_path: Path, monkeypatch) -> None:
    report, m3, m15 = fixture(tmp_path, monkeypatch)
    report["examples_by_stage"][r13.STAGE][0]["c2_m15_raw_bar_receipts"][0][
        "ohlc"
    ] = ("100", "101", "90", "100")
    with pytest.raises(ValueError, match="OHLC"):
        run(report, m3, m15)


def test_m3_vs_m15_c1_disagreement_rejected(tmp_path: Path, monkeypatch) -> None:
    report, m3, m15 = fixture(tmp_path, monkeypatch)
    x = json.loads(m15.read_text())
    x["periods"]["M15"][0]["low"] = "98.5"
    m15.write_text(json.dumps(x), encoding="utf-8")
    sha = hashlib.sha256(m15.read_bytes()).hexdigest()
    monkeypatch.setitem(r13.PINNED_M15, M, sha)
    report["source_m15_sha256"] = sha
    with pytest.raises(ValueError, match="aggregates disagree"):
        run(report, m3, m15)


def test_source_fabricated_signoff_rejected(tmp_path: Path, monkeypatch) -> None:
    report, m3, m15 = fixture(tmp_path, monkeypatch)
    report["examples_by_stage"][r13.STAGE][0]["A_rule_complete"] = True
    with pytest.raises(ValueError, match="masquerading"):
        run(report, m3, m15)


def test_missing_native_c2_receipt_rejected(tmp_path: Path, monkeypatch) -> None:
    report, m3, m15 = fixture(tmp_path, monkeypatch)
    report["examples_by_stage"][r13.STAGE][0][
        "c2_m15_raw_bar_receipts"
    ].pop()
    with pytest.raises(ValueError, match="cross-feed receipts"):
        run(report, m3, m15)


def test_future_m3_cisd_rejected(tmp_path: Path, monkeypatch) -> None:
    report, m3, m15 = fixture(tmp_path, monkeypatch)
    report["examples_by_stage"][r13.STAGE][0]["details"][
        "cisd_confirmed_at_utc"
    ] = (T + timedelta(minutes=63)).isoformat()
    with pytest.raises(ValueError, match="causal window"):
        run(report, m3, m15)
