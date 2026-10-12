"""Research-only first 12+11 M5 source union: archive SHA, fixed roster, zero PnL."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_cohort23_m5_source_union_v1 as u


def test_frozen_original_and_new_cohorts_do_not_overlap() -> None:
    u.check_universe()
    assert len(u.EXISTING) == 12
    assert len(u.NEW) == 11
    assert len(set(u.ALL)) == 23
    assert set(u.NEW).isdisjoint(u.EXISTING)
    assert "GBPNZD" not in u.NEW  # subsequent artifact, NOT hidden 12th promotion
    assert "USDCHF" in u.NEW
    assert "EURJPY" in u.NEW


def test_capture_identity_and_date_are_frozen() -> None:
    assert u.NEW_SOURCE_RUN == 38193802541
    assert u.NEW_SOURCE_SHA == "e0ca5a13c866a19d8505c68cffc473598984b340"
    assert u.g0.SOURCE_RUN == 35166210458
    assert u.ORIGINAL_G0B_RUN == 38201368296
    assert u.g0.FIRST == datetime(2016, 9, 17, tzinfo=UTC)
    assert u.g0.LAST_EXCLUSIVE == datetime(2026, 9, 17, tzinfo=UTC)


def test_new_source_missing_archive_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="original archive absent"):
        u.audit_new_symbol("NZDUSD", tmp_path / "nonexistent")


def test_new_source_unknown_or_old_symbol_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not in frozen new"):
        u.audit_new_symbol("NAS100", tmp_path)


def test_missing_manifest_witness_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="required original hash"):
        u.audit_new_symbol("USDCHF", tmp_path)


def test_self_asserted_manifest_does_not_pass_without_sha(tmp_path: Path) -> None:
    (tmp_path / "symbol-consumption-manifest.json").write_text("{}")
    (tmp_path / "MANIFEST_SHA256SUMS.txt").write_text("")
    with pytest.raises(ValueError, match="wrong scope"):
        u.audit_new_symbol("USDCHF", tmp_path)


def test_source_authorization_flags_must_all_deny_trading() -> None:
    safe = {
        "read_only": True, "research_evidence_consumed": True,
        "demo_eligible": False, "live_authorized": False,
        "real_capital_authorized": False, "production_authorized": False,
    }
    u._strict_flags(safe)
    for key in ("live_authorized", "production_authorized", "read_only"):
        tampered = safe.copy()
        tampered[key] = False if key == "read_only" else True
        with pytest.raises(ValueError, match="production"):
            u._strict_flags(tampered)


def test_exact_sha_scope_rejects_unknown_and_duplicate_paths(tmp_path: Path) -> None:
    p = tmp_path / "MANIFEST_SHA256SUMS.txt"
    value = hashlib.sha256(b"test").hexdigest()
    p.write_text(f"{value}  good.json\n{value}  extra.txt\n")
    with pytest.raises(ValueError, match="wrong scope"):
        u._hash_scope(p, {"good.json"})
    p.write_text(f"{value}  good.json\n{value}  good.json\n")
    with pytest.raises(ValueError, match="duplicate"):
        u._hash_scope(p, {"good.json"})


def test_combine_rejects_empty_or_fake_broker_original(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        u.combine(tmp_path / "original", tmp_path / "new")


def test_no_pnl_or_execution_or_price_reads() -> None:
    code = Path(u.__file__).read_text()
    forbidden = (
        'row["open_relative"]', 'row["close_relative"]',
        'row["high_relative"]', 'row["low_relative"]',
        'row["volume"]', "backtest(", "profit_factor(",
        "sharpe_ratio(", "place_order(", "order_request(",
    )
    assert not any(token in code for token in forbidden)


def test_combined_status_does_not_certify_net_execution() -> None:
    assert "ECONOMICS_NOT_AUTHORIZED" in u.FINAL_STATUS
    assert u.NEW_CAPTURE_IDENTITY.endswith("NEW_CAPTURE_V1")
    assert u.NEW_RAW_SCHEMA.endswith(".raw")
