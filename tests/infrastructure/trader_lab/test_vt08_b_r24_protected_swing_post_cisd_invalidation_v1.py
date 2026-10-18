"""R24 adversarial physical survivability of originating protected-low proxy."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

import qore.infrastructure.trader_lab.vt08_b_r24_protected_swing_post_cisd_invalidation_v1 as r24

T = datetime(2026, 4, 6, 12, tzinfo=UTC)
M = "EURJPY"
SHA = "a"*64


def _bars(low_at: int = 3, cisd: int = 6, later: str = "no") -> list[tuple[Decimal, ...]]:
    rows = []
    for ix in range(10):
        op = Decimal("100")
        close = Decimal("99.8") if ix < cisd-1 else Decimal("101")
        lo = Decimal("98") if ix == low_at else Decimal("99")
        if ix > cisd-1 and later == "lower" and ix == cisd:
            lo = Decimal("97")
        elif ix > cisd-1 and later == "touch" and ix == cisd:
            lo = Decimal("98")
        if ix == cisd-1 and later == "confirm_lower":
            lo = Decimal("97")
        rows.append((op, Decimal("102"), lo, close))
    return rows


@pytest.mark.parametrize(("later", "expected"), [
    ("no", "NO_POST_CISD_LOWER_LOW_OBSERVED"),
    ("lower", "ORIGINAL_PS_PROXY_LOW_BROKEN_AFTER_CISD_BEFORE_C3"),
    ("touch", "PS_PROXY_LOW_RETOUCHED_AFTER_CISD"),
])
def test_post_cisd_lower_low_falsifies_original_proxy(
    later: str, expected: str,
) -> None:
    state = r24.classify_post_cisd_original_ps(
        _bars(later=later), proxy_low=Decimal("98"), cisd_closed_m3_index=6,
    )
    assert state["post_cisd_original_ps_proxy_state"] == expected
    assert state["post_cisd_m3_count"] == 4
    assert state["new_author_ps_reestablished"] == "D_NOT_ASSESSED"
    assert state["cisd_bar_intrabar_sequence_proven"] is False


def test_confirming_cisd_bar_lower_low_does_not_create_false_tick_order() -> None:
    state = r24.classify_post_cisd_original_ps(
        _bars(later="confirm_lower"), proxy_low=Decimal("98"), cisd_closed_m3_index=6,
    )
    assert state["cisd_m3_confirmation_bar_low_below_proxy"] is True
    assert state["post_cisd_original_ps_proxy_state"] == "NO_POST_CISD_LOWER_LOW_OBSERVED"
    assert state["cisd_bar_intrabar_sequence_proven"] is False


def test_cisd_at_c2_close_has_no_future_m3_bar() -> None:
    state = r24.classify_post_cisd_original_ps(
        _bars(cisd=10), proxy_low=Decimal("98"), cisd_closed_m3_index=10,
    )
    assert state["post_cisd_original_ps_proxy_state"] == (
        "CISD_AT_C2_CLOSE_NO_LATER_M3"
    )
    assert state["post_cisd_m3_count"] == 0


@pytest.mark.parametrize("attack", [
    "n0", "n9", "cisd_outside", "negative_low", "nan_candle", "invalid_ohlc",
])
def test_classifier_rejects_corrupt_candles_or_time(
    attack: str,
) -> None:
    bars = _bars()
    low = Decimal("98")
    closing = 6
    if attack == "n0":
        bars = []
    elif attack == "n9":
        bars.pop()
    elif attack == "cisd_outside":
        closing = 11
    elif attack == "negative_low":
        low = Decimal("-1")
    elif attack == "nan_candle":
        bars[8] = (Decimal("NaN"), *bars[8][1:])
    elif attack == "invalid_ohlc":
        bars[8] = (Decimal("105"), Decimal("100"), Decimal("99"), Decimal("101"))
    with pytest.raises(ValueError):
        r24.classify_post_cisd_original_ps(
            bars, proxy_low=low, cisd_closed_m3_index=closing,
        )


def _audit(monkeypatch: pytest.MonkeyPatch, *, forged: str = ""):
    cid = hashlib.sha256(
        f"{M}|{T.isoformat()}|{(T+timedelta(minutes=30)).isoformat()}".encode()
    ).hexdigest()
    monkeypatch.setitem(r24.MARKET_EXPECTED, M, (1, "c"*64))
    monkeypatch.setitem(r24.PINNED_R19_REPORT_DIGESTS, M, "d"*64)
    monkeypatch.setattr(r24, "digest_r19", lambda _: "d"*64)
    old = [{
        "case_id_sha256": cid,
        "cisd_proxy_confirmed_at_utc": (T+timedelta(minutes=18)).isoformat(),
        "ps_low_proxy": "98",
    }]
    def r14(_r3: object, *, market: str, native_m3: Path):
        assert market == M
        return {
            "native_m3_sha256": SHA,
            "frozen_source_cases": 1,
            "all_source_only_witnesses": old,
        }
    def raw(_path: Path, profile: str, market: str):
        assert profile == "M3" and market == M
        return SHA, {}
    def rec(_obj, *, expected_open, minutes, profile, source_sha, raw):
        assert source_sha == SHA and profile == "M3" and minutes == 3
        i = int((expected_open - T)/timedelta(minutes=3))
        return _bars()[i]
    monkeypatch.setattr(r24, "audit_m3_opposing_series", r14)
    monkeypatch.setattr(r24, "_raw_bars", raw)
    monkeypatch.setattr(r24, "_verify_bar", rec)
    blind = {
        "market": M, "original_r18_sha256": "c"*64,
        "original_r18_cases": 1,
        "rater_A_signed": 0, "rater_B_signed": 0,
        "source_complete_entries": 0, "cognitive_admissions": 0,
        "broker_fills": 0, "holdout_7y_accessed": False,
        "sizing_used": False, "selected_source_only_cases": 1,
        "review_packets": [{
            "market": M, "case_id_sha256": cid,
            "category": "BULLISH_FVG_TOUCHED_PRE_CISD",
            "selection_rank_sha256": "e"*64,
            "human_rater_A_source_signoff": None,
            "human_rater_B_independent_signoff": None,
            "source_complete": False, "orders_authorized": False,
        }],
    }
    case = {
        "market": M, "c2_opened_at_utc": T.isoformat(),
        "decision_at_utc": (T+timedelta(minutes=30)).isoformat(),
        "c2_m3_raw_bar_receipts": [{
            "source_bar_id": hashlib.sha256(str(i).encode()).hexdigest(),
        } for i in range(10)],
    }
    if forged == "missing_bar":
        case["c2_m3_raw_bar_receipts"].pop()
    elif forged == "false_sign":
        blind["review_packets"][0]["human_rater_A_source_signoff"] = "FORGED"
    elif forged == "wrong_source":
        blind["original_r18_sha256"] = "z"*64
    elif forged == "wrong_cisd":
        old[0]["cisd_proxy_confirmed_at_utc"] = (
            T+timedelta(minutes=31)
        ).isoformat()
    elif forged == "no_ps_low":
        old[0]["ps_low_proxy"] = "97"
    elif forged == "reused_7y":
        blind["holdout_7y_accessed"] = True
    return r24.audit_original_ps_proxy_survival(
        {"examples_by_stage": {
            "UNIQUE_M3_CISD_PS_SHAPE_REQUIRES_AUTHOR_ADJUDICATION": [case],
        }},
        blind, market=M, native_m3=Path("/synthetic.json"),
    )


def test_source_full_audit_does_not_pretend_ps_validity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _audit(monkeypatch)
    assert result["original_frozen_case_count"] == 1
    assert result["blind_review_107_sample_cases"] == 1
    assert not result["real_cognitive_admissions"]
    assert not result["source_complete_author_entries"]
    assert result["same_107_blind_review_with_post_cisd_causality"][0][
        "A_author_source_decision"
    ] is None


@pytest.mark.parametrize("attack", [
    "missing_bar", "false_sign", "wrong_source", "wrong_cisd", "no_ps_low", "reused_7y",
])
def test_full_audit_rejects_original_case_attestation_tampering(
    monkeypatch: pytest.MonkeyPatch, attack: str,
) -> None:
    with pytest.raises((ValueError, IndexError)):
        _audit(monkeypatch, forged=attack)
