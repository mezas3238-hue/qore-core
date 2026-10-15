"""Independent B tests: raw M3/M15 files, no imports from Architect A."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.vt08_5m_b_independent_raw_receipts_v1 import (
    verify_raw_window,
)

T = datetime(2026, 1, 5, 6, tzinfo=UTC)


def _raw_row(time: datetime, minutes: int) -> dict[str, str]:
    return {
        "opened_at": time.isoformat(),
        "closed_at": (time + timedelta(minutes=minutes)).isoformat(),
        "open": "100", "high": "101", "low": "99", "close": "100",
    }


def _bar(source: dict[str, str], profile: str, file_sha: str) -> dict[str, object]:
    content: dict[str, object] = {
        "profile": profile,
        "source_raw_sha256": file_sha,
        "opened_at_utc": source["opened_at"],
        "closed_at_utc": source["closed_at"],
        "ohlc": tuple(source[k] for k in ("open", "high", "low", "close")),
    }
    digest = hashlib.sha256(
        json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        **content,
        "source_bar_id": digest,
        "available_at_utc": source["closed_at"],
        "semantics": "OBSERVED_OHLC_ONLY_NOT_TTRADES_RULE",
    }


def _case(tmp_path: Path) -> tuple[dict[str, object], Path, Path]:
    m3 = [_raw_row(T + timedelta(minutes=3 * i), 3) for i in range(10)]
    m15 = [_raw_row(T + timedelta(minutes=15 * i), 15) for i in range(2)]
    identity: dict[str, object] = {
        "environment": "demo",
        "read_only": True,
        "account_is_live": False,
        "symbol": {"symbol_name": "EURJPY"},
    }
    m3file = tmp_path / "m3.json"
    m15file = tmp_path / "m15.json"
    m3file.write_text(json.dumps({**identity, "period": "M3", "bars": m3}))
    m15file.write_text(json.dumps({**identity, "periods": {"M15": m15}}))
    sha3 = hashlib.sha256(m3file.read_bytes()).hexdigest()
    sha15 = hashlib.sha256(m15file.read_bytes()).hexdigest()
    receipt: dict[str, object] = {
        "schema": "qore.vt08.a.m30m3.raw_bar_custody.v1",
        "market": "EURJPY",
        "ny_anchor_hour": 1,
        "ny_date": "2026-01-05",
        "m30_opened_at_utc": T.isoformat(),
        "m30_available_at_utc": (T + timedelta(minutes=30)).isoformat(),
        "m30_ohlc": ("100", "101", "99", "100"),
        "m3_bar_receipts": [_bar(row, "M3", sha3) for row in m3],
        "m15_bar_receipts": [_bar(row, "M15", sha15) for row in m15],
        "source_m30_cross_attested": True,
        "source_author_fidelity_verified": False,
        "cognitive_ready": False,
        "broker_quotes_verified": False,
        "source_complete_candidate_events": 0,
        "orders": 0,
        "fills": 0,
        "pnl_measured": False,
        "holdout_7y_accessed": False,
    }
    return receipt, m3file, m15file


def _verify(receipt: dict[str, object], m3: Path, m15: Path) -> dict[str, object]:
    return verify_raw_window(receipt, m3_file=m3, m15_file=m15)


def test_custody_success_does_not_grant_source_or_economic_certificate(tmp_path: Path) -> None:
    r, m3, m15 = _case(tmp_path)
    result = _verify(r, m3, m15)
    assert result["m3_bars_reverified"] == 10
    assert result["m15_bars_reverified"] == 2
    assert result["author_certified"] is False
    assert result["economic_certified"] is False
    assert result["operational_authority"] is False


def test_modifying_raw_source_bytes_breaks_lineage(tmp_path: Path) -> None:
    r, m3, m15 = _case(tmp_path)
    m3.write_bytes(m3.read_bytes() + b" ")
    with pytest.raises(ValueError, match="raw source identity"):
        _verify(r, m3, m15)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("receipt_ohlc", "differs from raw"),
        ("bar_id", "source_bar_id invalid"),
        ("available_at", "available_at/clock contradiction"),
        ("missing_m3", "M3 receipts incomplete"),
        ("owner_hour", "owner anchor"),
        ("m30_claim", "claimed M30 OHLC differs"),
        ("author_promotion", "unauthorized certification"),
        ("cognitive_promotion", "unauthorized certification"),
        ("fake_fills", "unauthorized certification"),
        ("future_holdout", "unauthorized certification"),
    ],
)
def test_forgery_or_false_promotion_fails_closed(
    tmp_path: Path, name: str, expected: str
) -> None:
    r, m3, m15 = _case(tmp_path)
    bars = r["m3_bar_receipts"]
    assert isinstance(bars, list)
    if name == "receipt_ohlc":
        bars[0] = dict(bars[0], ohlc=("100", "102", "99", "100"))
    elif name == "bar_id":
        bars[0] = dict(bars[0], source_bar_id="e" * 64)
    elif name == "available_at":
        bars[0] = dict(
            bars[0], available_at_utc=(T + timedelta(minutes=2)).isoformat()
        )
    elif name == "missing_m3":
        bars.pop()
    elif name == "owner_hour":
        r["ny_anchor_hour"] = 13
    elif name == "m30_claim":
        r["m30_ohlc"] = ("100", "102", "99", "100")
    elif name == "author_promotion":
        r["source_author_fidelity_verified"] = True
    elif name == "cognitive_promotion":
        r["cognitive_ready"] = True
    elif name == "fake_fills":
        r["fills"] = 1
    elif name == "future_holdout":
        r["holdout_7y_accessed"] = True
    with pytest.raises(ValueError, match=expected):
        _verify(r, m3, m15)


def test_raw_file_foreign_symbol_rejected(tmp_path: Path) -> None:
    r, m3, m15 = _case(tmp_path)
    data = json.loads(m15.read_text())
    data["symbol"]["symbol_name"] = "GBPJPY"
    m15.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="identity/authority"):
        _verify(r, m3, m15)


def test_nan_raw_price_rejected(tmp_path: Path) -> None:
    r, m3, m15 = _case(tmp_path)
    data = json.loads(m3.read_text())
    data["bars"][0]["high"] = "NaN"
    m3.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="non-finite"):
        _verify(r, m3, m15)
