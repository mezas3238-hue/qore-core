"""R14 independent bearish sequence/closed-cross adversarial tests."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import vt08_b_r14_opposing_series_native_cisd_v1 as b

T = datetime(2025, 8, 5, 9, tzinfo=UTC)
M = "EURJPY"


def m3_sequence(*, low="98", bullish_close="101", confirming=True):
    result = []
    for i in range(10):
        t = T + i * timedelta(minutes=3)
        if i == 0:
            vals = ("100", "100.5", low, "99.5")
        elif i == 1:
            vals = ("99.5", "100", low if Decimal(low) >= 99 else "98.5", "99")
        elif i == 2:
            vals = ("99", "101", "98.8", bullish_close)
        else:
            vals = ("100", "101", "99", "100")
        if not confirming and i == 2:
            vals = ("99", "100", "98.8", "99.5")
        result.append((t, tuple(Decimal(v) for v in vals)))
    return result


def test_independent_bullish_series_native_prices():
    got = b.independent_m3_cisd_proxy(
        m3_sequence(), prior_low=Decimal("99"),
    )
    assert len(got) == 1
    assert got[0]["opposing_series_opened_at_utc"] == T.isoformat()
    assert got[0]["cisd_proxy_confirmed_at_utc"] == (
        T + timedelta(minutes=9)
    ).isoformat()
    assert got[0]["cisd_level_proxy"] == "100"
    assert got[0]["ps_low_proxy"] == "98"


@pytest.mark.parametrize(
    ("low", "close"),
    [("99", "101"), ("100", "101"), ("98", "100"), ("98", "99.5")],
)
def test_no_close_or_no_low_sweep_means_no_proxy(low: str, close: str):
    assert b.independent_m3_cisd_proxy(
        m3_sequence(low=low, bullish_close=close),
        prior_low=Decimal("99"),
    ) == []


def test_candle_close_required_not_high_only():
    seq = m3_sequence()
    when, (o, _, lo, _) = seq[2]
    seq[2] = when, (o, Decimal("120"), lo, Decimal("99.5"))
    assert b.independent_m3_cisd_proxy(
        seq, prior_low=Decimal("99"),
    ) == []


def test_discontinuous_candles_cannot_be_reconstructed():
    seq = m3_sequence()
    when, x = seq[3]
    seq[3] = when + timedelta(minutes=2), x
    with pytest.raises(ValueError, match="discontinuous"):
        b.independent_m3_cisd_proxy(
            seq, prior_low=Decimal("99"),
        )


def fixture(tmp_path: Path):
    src = []
    for i in range(20):
        when = T - timedelta(minutes=30) + i * timedelta(minutes=3)
        if i < 10:
            o, h, low, close = "100", "101", "99", "100"
        else:
            (_, _vals) = m3_sequence()[i - 10]
            o, h, low, close = (str(v) for v in _vals)
        src.append({
            "opened_at": when.isoformat(),
            "closed_at": (when + timedelta(minutes=3)).isoformat(),
            "open": o, "high": h, "low": low, "close": close,
        })
    p = tmp_path / "m3.json"
    p.write_text(json.dumps({
        "environment": "demo", "read_only": True,
        "account_is_live": False, "symbol": {"symbol_name": M},
        "period": "M3", "bars": src,
    }), encoding="utf-8")
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    def receipts(offset: int):
        collected = []
        for bar in src[offset:offset+10]:
            body = {
                "profile": "M3", "source_raw_sha256": sha,
                "opened_at_utc": bar["opened_at"],
                "closed_at_utc": bar["closed_at"],
                "ohlc": tuple(bar[k] for k in (
                    "open", "high", "low", "close",
                )),
            }
            digest = hashlib.sha256(json.dumps(
                body, sort_keys=True, separators=(",", ":"),
            ).encode()).hexdigest()
            collected.append({
                **body, "source_bar_id": digest,
                "available_at_utc": bar["closed_at"],
                "semantics": "OBSERVED_OHLC_ONLY_NOT_TTRADES_RULE",
            })
        return collected
    c1 = T - timedelta(minutes=30)
    c3 = T + timedelta(minutes=30)
    case = {
        "market": M, "stage": b.STAGE,
        "c1_opened_at_utc": c1.isoformat(),
        "c2_opened_at_utc": T.isoformat(),
        "decision_at_utc": c3.isoformat(),
        "A_rule_complete": False, "B_signoff": False,
        "cognitive_ready": False, "broker_fill": False, "pnl_read": False,
        "details": {
            "m3_ps_proxy_count": 1, "proxy_not_author_validated": True,
            "reference_swing_author_valid": False,
            "significant_poi_author_valid": False,
            "breaker_low_author_valid": False,
            "methodology_complete": False,
            "opposing_series_opened_at_utc": T.isoformat(),
            "cisd_confirmed_at_utc": (T+timedelta(minutes=9)).isoformat(),
            "ps_proxy_price": "98", "cisd_level_proxy": "100",
        },
        "c1_m3_raw_bar_receipts": receipts(0),
        "c2_m3_raw_bar_receipts": receipts(10),
    }
    report = {
        "schema": "qore.vt08.a.frozen_bullish_m30m3.source_funnel.v1",
        "market": M, "source_m3_sha256": sha,
        "all_unique_proxy_cases_with_raw_receipts": 1,
        "stage_counts": {b.STAGE: 1},
        "examples_by_stage": {b.STAGE: [case]},
    }
    return report, p


def test_full_native_cisd_independent_rebuild(tmp_path: Path):
    report, p = fixture(tmp_path)
    result = b.audit_m3_opposing_series(report, market=M, native_m3=p)
    assert result["frozen_source_cases"] == 1
    assert result["counts"]["independent_unique_m3_opposing_series_proxy"] == 1
    assert result["counts"]["cisd_proxy_known_asof_c3"] == 1
    assert result["author_cisd_and_ps_validated"] is False
    assert result["broker_fills"] == 0
    assert len(b.result_sha256(result)) == 64


def test_contradictory_a_proxy_level_rejected(tmp_path: Path):
    report, p = fixture(tmp_path)
    report["examples_by_stage"][b.STAGE][0]["details"]["ps_proxy_price"] = "88"
    with pytest.raises(ValueError, match="differs from A"):
        b.audit_m3_opposing_series(report, market=M, native_m3=p)


def test_forged_c2_m3_candle_rejected(tmp_path: Path):
    report, p = fixture(tmp_path)
    report["examples_by_stage"][b.STAGE][0][
        "c2_m3_raw_bar_receipts"
    ][0]["ohlc"] = ("100", "100.5", "1", "99.5")
    with pytest.raises(ValueError, match="OHLC"):
        b.audit_m3_opposing_series(report, market=M, native_m3=p)


def test_false_author_signoff_rejected(tmp_path: Path):
    report, p = fixture(tmp_path)
    report["examples_by_stage"][b.STAGE][0]["A_rule_complete"] = True
    with pytest.raises(ValueError, match="masquerading"):
        b.audit_m3_opposing_series(report, market=M, native_m3=p)
