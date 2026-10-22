"""Synthetic R21 QORE physical diagnostics never become TTrades author POI."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import qore.infrastructure.trader_lab.vt08_b_r21_intraday_low_source_context_v1 as audit

M = "EURJPY"
T0 = datetime(2026, 1, 5, 6, tzinfo=UTC)
SHA = "d" * 64
ID = hashlib.sha256(
    f"{M}|{T0.isoformat()}|{(T0+timedelta(minutes=30)).isoformat()}".encode()
).hexdigest()


def _run(monkeypatch: pytest.MonkeyPatch, *, first_half_low: str = "101",
         gap: bool = False, wrong_sha: bool = False,
         wrong_low: bool = False):
    day_start = T0 - timedelta(hours=1)
    raw = {}
    for i in range(20):
        opened = day_start+timedelta(minutes=3*i)
        if gap and i == 4:
            continue
        raw[opened] = {
            "opened_at": opened.isoformat(),
            "closed_at": (opened + timedelta(minutes=3)).isoformat(),
            "open": "101.5",
            "high": "104",
            "low": first_half_low if i < 10 else "100",
            "close": "101.5",
        }
    def prior(_r3: object, _r7: object, *, market: str,
              native_m3_file: Path) -> dict[str, object]:
        assert market == M
        return {
            "source_m3_sha256": SHA,
            "cases_audited": 1,
            "all_case_causal_index": [
                {"case_id_sha256": ID, "c1_low_physical_only": "100"},
            ],
            "blind_packet_causal_evidence": [{"case_id_sha256": ID}],
        }
    def raw_source(_path: Path, profile: str, market: str):
        assert profile == "M3" and market == M
        return ("f" * 64 if wrong_sha else SHA), raw
    monkeypatch.setattr(audit, "audit_intrac2_sweep_cisd_source", prior)
    monkeypatch.setattr(audit, "_raw_bars", raw_source)
    c2low = "100.5" if wrong_low else "99"
    case = {
        "c2_opened_at_utc": T0.isoformat(),
        "decision_at_utc": (T0+timedelta(minutes=30)).isoformat(),
        "c2_m3_raw_bar_receipts": [
            {"ohlc": ["101","104",c2low,"102"]},
        ],
    }
    return audit.inspect_intraday_low_context(
        {"examples_by_stage": {
            "UNIQUE_M3_CISD_PS_SHAPE_REQUIRES_AUTHOR_ADJUDICATION": [case],
        }},
        {}, market=M, native_m3_file=Path("/synthetic/original-m3.json"),
    )


def test_ny_prior_day_low_swept_only_contextual_not_author_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _run(monkeypatch)
    assert result["day_low_category_counts"][audit.LABEL_YES] == 1
    assert result["day_low_category_counts"][audit.LABEL_NO] == 0
    assert result["c1_low_vs_completed_ny_context_counts"] == {
        "C1_LOW_EQUAL_PRIOR_DAY_TO_DATE_LOW": 1,
    }
    assert result["source_complete_entries"] == 0
    assert not result["all_source_author_poi_signatures_present"]
    assert result["blind_review_day_context"][0][
        "important_level_ttrades_author_confirmed"
    ] is False


def test_prior_day_low_was_lower_so_only_c1_local_level_swept(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _run(monkeypatch, first_half_low="98")
    assert result["day_low_category_counts"][audit.LABEL_NO] == 1
    assert result["c1_low_vs_completed_ny_context_counts"] == {
        "C1_LOW_ABOVE_PRIOR_DAY_TO_DATE_LOW": 1,
    }
    assert result["source_complete_entries"] == 0


def test_missing_earlier_source_bar_is_quarantined_not_treated_as_low(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _run(monkeypatch, gap=True)
    assert result["day_low_category_counts"][audit.LABEL_GAP] == 1
    assert not result["blind_review_day_context"][0]["day_context_complete"]
    assert result["blind_review_day_context"][0][
        "ny_midnight_to_c2_prior_low"
    ] is None


@pytest.mark.parametrize("attack", ["sha", "contradict_c1_sweep"])
def test_no_raw_retarget_or_forged_c1_sweep(
    monkeypatch: pytest.MonkeyPatch, attack: str,
) -> None:
    with pytest.raises(ValueError):
        _run(monkeypatch, wrong_sha=attack=="sha",
             wrong_low=attack=="contradict_c1_sweep")
