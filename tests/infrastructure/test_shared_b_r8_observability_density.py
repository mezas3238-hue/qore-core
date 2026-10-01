from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qore.infrastructure.core_stack_v2.shared_b_r8_observability_density import (
    SharedBR8ObservabilityDensityError,
    build_full_r8_observability_density,
)

FAMILIES = {
    "US2000_BREADTH_PROXY": ("US2000", 10012),
    "XAUUSD_DEFENSIVE_PROXY": ("XAUUSD", 41),
}


def _write_reports(root: Path) -> None:
    base = datetime(2017, 1, 1, tzinfo=UTC)
    for family, (symbol, symbol_id) in FAMILIES.items():
        for shard in range(16):
            rows = []
            indices = list(range(shard, 2948, 16))
            for index in indices:
                start = base + timedelta(minutes=15 * index)
                end = start + timedelta(minutes=15)
                empty = family == "US2000_BREADTH_PROXY" and index == 0
                count = 0 if empty else 10
                rows.append(
                    {
                        "manifest_index": index,
                        "from_at": start.isoformat(),
                        "to_at": end.isoformat(),
                        "bid_count": count,
                        "ask_count": count,
                        "bid_first_at": (
                            None
                            if empty
                            else (start + timedelta(seconds=1)).isoformat()
                        ),
                        "ask_first_at": (
                            None
                            if empty
                            else (start + timedelta(seconds=1)).isoformat()
                        ),
                        "bid_last_at": (
                            None
                            if empty
                            else (end - timedelta(seconds=2)).isoformat()
                        ),
                        "ask_last_at": (
                            None
                            if empty
                            else (end - timedelta(seconds=2)).isoformat()
                        ),
                    }
                )
            report = {
                "identity": "QORE_SHARED_WP05_V15_CROSS_ASSET_R8_ACQUISITION_001",
                "manifest_sha256": (
                    "2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191"
                ),
                "partition": "r8_source_only",
                "family": family,
                "provider_symbol": symbol,
                "provider_symbol_id": symbol_id,
                "canonical_instrument": symbol,
                "shard_count": 16,
                "shard_index": shard,
                "total_manifest_windows": 2948,
                "assignment_rule": "MANIFEST_INDEX_MOD_16",
                "target_or_outcome_read": False,
                "r6_r5_read": False,
                "fresh_holdout_opened": False,
                "scientific_v15_outcomes_opened": False,
                "read_only_message_firewall": True,
                "shared_methodology_authority": False,
                "shared_risk_authority": False,
                "shared_sizing_authority": False,
                "shared_order_authority": False,
                "shared_execution_authority": False,
                "window_reports": rows,
            }
            path = root / family / f"{family}-{shard:02d}-report.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report), encoding="utf-8")


def test_exact_full_r8_density_is_descriptive_only(tmp_path: Path) -> None:
    _write_reports(tmp_path)
    payload = build_full_r8_observability_density(reports_dir=tmp_path)
    assert payload["family_count"] == 2
    assert payload["total_window_family_observations"] == 5896
    assert payload["observability_policy_registry_frozen"] is False
    assert payload["liquidity_policy_registry_frozen"] is False
    assert payload["stale_policy_registry_frozen"] is False
    assert payload["comparability_policy_registry_frozen"] is False
    assert payload["global_threshold_extrapolation_authorized"] is False
    assert payload["relational_comparability_authorized"] is False
    assert payload["b08_complete"] is False

    us = payload["families"]["US2000_BREADTH_PROXY"]
    assert us["window_count"] == 2948
    assert us["empty_bid_window_count"] == 1
    assert us["empty_ask_window_count"] == 1
    assert us["full_bid_window_presence"] is False
    assert us["bid_first_event_lag_ms_distribution"]["min"] == 1000.0

    gold = payload["families"]["XAUUSD_DEFENSIVE_PROXY"]
    assert gold["window_count"] == 2948
    assert gold["empty_bid_window_count"] == 0
    assert gold["full_bid_window_presence"] is True


def test_duplicate_window_fails_closed(tmp_path: Path) -> None:
    _write_reports(tmp_path)
    paths = sorted(tmp_path.rglob("*-report.json"))
    report = json.loads(paths[1].read_text())
    first_path = paths[0]
    first = json.loads(first_path.read_text())
    report["window_reports"][0]["manifest_index"] = (
        first["window_reports"][0]["manifest_index"]
    )
    paths[1].write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(
        SharedBR8ObservabilityDensityError,
        match="duplicate manifest index",
    ):
        build_full_r8_observability_density(reports_dir=tmp_path)


def test_productive_authority_drift_fails_closed(tmp_path: Path) -> None:
    _write_reports(tmp_path)
    path = sorted(tmp_path.rglob("*-report.json"))[0]
    report = json.loads(path.read_text())
    report["shared_execution_authority"] = True
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(
        SharedBR8ObservabilityDensityError,
        match="shared_execution_authority",
    ):
        build_full_r8_observability_density(reports_dir=tmp_path)
