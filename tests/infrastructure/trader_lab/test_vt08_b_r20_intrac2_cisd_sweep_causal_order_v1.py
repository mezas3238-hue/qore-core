"""Synthetic R20 timing cases; real price custody is checked in Actions."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

import qore.infrastructure.trader_lab.vt08_b_r20_intrac2_cisd_sweep_causal_order_v1 as r20

T0 = datetime(2026, 1, 5, 12, tzinfo=UTC)
M = "EURJPY"
SHA = "a" * 64


def _case(sweep_index: int, cisd_index: int = 5) -> dict[str, object]:
    c1 = []
    c2 = []
    for i in range(10):
        a = (T0 - timedelta(minutes=30) + i * r20.M3).isoformat()
        b = (T0 + i * r20.M3).isoformat()
        c1.append({
            "source_bar_id": hashlib.sha256(a.encode()).hexdigest(),
            "opened_at_utc": a, "ohlc": ["104", "108", "100", "104"],
        })
        c2.append({
            "source_bar_id": hashlib.sha256(b.encode()).hexdigest(),
            "opened_at_utc": b,
            "ohlc": ["104", "107", "99" if i == sweep_index else "101",
                     "106" if i == 9 else "104"],
        })
    return {
        "market": M,
        "c2_opened_at_utc": T0.isoformat(),
        "decision_at_utc": (T0+r20.M30).isoformat(),
        "c1_m3_raw_bar_receipts": c1,
        "c2_m3_raw_bar_receipts": c2,
        "details": {
            "m3_ps_proxy_count": 1,
            "proxy_not_author_validated": True,
            "methodology_complete": False,
            "cisd_confirmed_at_utc": (
                T0+(cisd_index+1)*r20.M3
            ).isoformat(),
            "opposing_series_opened_at_utc": (T0+r20.M3).isoformat(),
        },
    }


def _perform(monkeypatch: pytest.MonkeyPatch, item: dict[str, object]) -> dict[str, object]:
    mid = hashlib.sha256(
        f"{M}|{T0.isoformat()}|{(T0+r20.M30).isoformat()}".encode()
    ).hexdigest()
    def verified(_case: dict[str, object], _r7: dict[str, object], *,
                 expected_market: str, per_category: int = 3) -> dict[str, object]:
        assert expected_market == M and per_category == 3
        return {
            "all_cases_census": 1, "review_packets": [{"case_id_sha256": mid}],
            "frozen_r3_sha256": "b" * 64, "frozen_r7_sha256": "c" * 64,
        }
    def raw_file(_path: Path, profile: str, market: str):
        assert profile == "M3" and market == M
        return SHA, {}
    def verify(item: dict[str, object], *, expected_open: datetime, minutes: int,
               profile: str, source_sha: str, raw: object) -> tuple[Decimal, ...]:
        assert profile == "M3" and source_sha == SHA and minutes == 3
        assert item["opened_at_utc"] == expected_open.isoformat()
        return tuple(Decimal(s) for s in item["ohlc"])
    monkeypatch.setattr(r20, "build_blind_semantic_review_packets", verified)
    monkeypatch.setattr(r20, "_raw_bars", raw_file)
    monkeypatch.setattr(r20, "_verify_bar", verify)
    return r20.audit_intrac2_sweep_cisd_source(
        {"source_m3_sha256": SHA, "examples_by_stage": {r20.R3_STAGE: [item]}},
        {}, market=M, native_m3_file=Path("/synthetic/m3.json"),
    )


@pytest.mark.parametrize(
    ("sweep_i", "wanted"),
    [
        (2, "SWEEP_OBSERVED_BEFORE_CISD_M3_CLOSE"),
        (5, "SWEEP_AND_CISD_SAME_M3_CLOSE_INTRABAR_UNRESOLVED"),
        (8, "SWEEP_OBSERVED_AFTER_CISD_M3_CLOSE_FIRST_FAIL"),
    ],
)
def test_classifies_sweep_order_without_making_a_trade(
    monkeypatch: pytest.MonkeyPatch, sweep_i: int, wanted: str,
) -> None:
    result = _perform(monkeypatch, _case(sweep_i))
    assert result["cases_audited"] == 1
    assert result["first_sweep_vs_cisd_counts"] == {wanted: 1}
    assert result["intrac2_cisd_vs_c2_close_counts"] == {"CISD_BEFORE_C2_CLOSE": 1}
    assert result["blind_packet_causal_evidence"][0]["m3_sweep_vs_cisd"] == wanted
    assert not result["source_complete_entries"]
    assert not result["cognitive_admissions"]
    assert not result["economic_gates_evaluated"]


def test_same_c2_closing_m3_cisd_is_not_required_after_c2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _perform(monkeypatch, _case(2, 9))
    assert result["intrac2_cisd_vs_c2_close_counts"] == {"CISD_AT_C2_CLOSE": 1}
    assert result["blind_packet_causal_evidence"][0][
        "m30_c2_closed_at_entry_decision"
    ] is True


@pytest.mark.parametrize("mutation", [
    "no_sweep", "high_swept", "bearish_c2", "bad_c3", "missing_m3",
    "false_ps", "future_cisd", "cisd_before_opposing_series", "non_bar_close",
    "duplicate_sweep_illegal_time",
])
def test_rejects_incompatible_physical_or_proxy_evidence(
    monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    case = _case(2)
    if mutation == "no_sweep":
        for bar in case["c2_m3_raw_bar_receipts"]:
            bar["ohlc"][2] = "101"
    elif mutation == "high_swept":
        case["c2_m3_raw_bar_receipts"][0]["ohlc"][1] = "110"
    elif mutation == "bearish_c2":
        case["c2_m3_raw_bar_receipts"][-1]["ohlc"][3] = "103"
    elif mutation == "bad_c3":
        case["decision_at_utc"] = (T0+timedelta(minutes=27)).isoformat()
    elif mutation == "missing_m3":
        case["c2_m3_raw_bar_receipts"].pop()
    elif mutation == "false_ps":
        case["details"]["methodology_complete"] = True
    elif mutation == "future_cisd":
        case["details"]["cisd_confirmed_at_utc"] = (
            T0 + timedelta(minutes=33)
        ).isoformat()
    elif mutation == "cisd_before_opposing_series":
        case["details"]["opposing_series_opened_at_utc"] = (
            T0 + timedelta(minutes=20)
        ).isoformat()
    elif mutation == "non_bar_close":
        case["details"]["cisd_confirmed_at_utc"] = (
            T0 + timedelta(minutes=17)
        ).isoformat()
    elif mutation == "duplicate_sweep_illegal_time":
        case["c2_m3_raw_bar_receipts"][0]["opened_at_utc"] = (
            T0 + timedelta(minutes=3)
        ).isoformat()
    with pytest.raises((ValueError, AssertionError)):
        _perform(monkeypatch, case)
