from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_b_r8_full_observation_density import (
    EXPECTED_MANIFEST_SHA256,
    EXPECTED_SHARD_COUNT,
    EXPECTED_WINDOW_COUNT,
    SharedBR8FullObservationDensityError,
    build_r8_full_observation_density_diagnostic,
)


def _reports() -> tuple[dict[str, object], ...]:
    base = datetime(2016, 1, 1, tzinfo=UTC)
    reports: list[dict[str, object]] = []
    for family, symbol, symbol_id, empty_every in (
        ("US2000_BREADTH_PROXY", "US2000", 10012, 127),
        ("XAUUSD_DEFENSIVE_PROXY", "XAUUSD", 41, 0),
    ):
        for shard in range(EXPECTED_SHARD_COUNT):
            rows: list[dict[str, object]] = []
            indices = list(range(shard, EXPECTED_WINDOW_COUNT, 16))
            for index in indices:
                start = base + timedelta(minutes=index * 2)
                end = start + timedelta(minutes=1)
                empty = empty_every > 0 and index % empty_every == 0
                count = 0 if empty else 3
                first = None if empty else (start + timedelta(seconds=5)).isoformat()
                last = None if empty else (start + timedelta(seconds=35)).isoformat()
                rows.append(
                    {
                        "manifest_index": index,
                        "from_at": start.isoformat(),
                        "to_at": end.isoformat(),
                        "bid_count": count,
                        "bid_first_at": first,
                        "bid_last_at": last,
                        "ask_count": count,
                        "ask_first_at": first,
                        "ask_last_at": last,
                    }
                )
            reports.append(
                {
                    "identity": (
                        "QORE_SHARED_WP05_V15_CROSS_ASSET_R8_ACQUISITION_001"
                    ),
                    "partition": "r8_source_only",
                    "family": family,
                    "provider_symbol": symbol,
                    "provider_symbol_id": symbol_id,
                    "manifest_sha256": EXPECTED_MANIFEST_SHA256,
                    "shard_index": shard,
                    "shard_count": EXPECTED_SHARD_COUNT,
                    "total_manifest_windows": EXPECTED_WINDOW_COUNT,
                    "assignment_rule": "MANIFEST_INDEX_MOD_16",
                    "assigned_window_count": len(rows),
                    "attempted_manifest_indices": indices,
                    "window_reports": rows,
                    "read_only_message_firewall": True,
                    "target_or_outcome_read": False,
                    "r6_r5_read": False,
                    "fresh_holdout_opened": False,
                    "scientific_v15_outcomes_opened": False,
                    "shared_methodology_authority": False,
                    "shared_sizing_authority": False,
                    "shared_risk_authority": False,
                    "shared_order_authority": False,
                    "shared_execution_authority": False,
                }
            )
    return tuple(reports)


def test_full_r8_density_reducer_covers_exact_source_population() -> None:
    payload = build_r8_full_observation_density_diagnostic(_reports())

    assert payload["sensor_count"] == 2
    assert payload["sensor_window_count"] == 5896
    assert payload["compact_reports_only"] is True
    assert payload["raw_tick_blob_read"] is False
    assert payload["cadence_policy_registry_frozen"] is False
    assert payload["liquidity_policy_registry_frozen"] is False
    assert payload["temporal_skew_policy_registry_frozen"] is False
    assert payload["comparability_policy_registry_frozen"] is False
    assert payload["global_threshold_extrapolation_authorized"] is False
    assert payload["relational_comparability_authorized"] is False
    assert payload["b08_complete"] is False

    sensors = payload["sensors"]
    assert isinstance(sensors, dict)
    us = sensors["US2000_BREADTH_PROXY"]
    gold = sensors["XAUUSD_DEFENSIVE_PROXY"]
    assert isinstance(us, dict)
    assert isinstance(gold, dict)
    us_bid = us["bid"]
    gold_bid = gold["bid"]
    assert isinstance(us_bid, dict)
    assert isinstance(gold_bid, dict)
    assert us_bid["empty_window_count"] > 0
    assert gold_bid["empty_window_count"] == 0
    assert us["one_side_only_empty_window_count"] == 0
    assert gold["one_side_only_empty_window_count"] == 0
    assert us_bid["weighted_mean_interarrival_ms"] == 15000
    assert gold_bid["weighted_mean_interarrival_ms"] == 15000
    assert len(payload["diagnostic_fingerprint_sha256"]) == 64


def test_duplicate_or_missing_window_population_fails_closed() -> None:
    reports = list(deepcopy(_reports()))
    first = reports[0]
    rows = first["window_reports"]
    attempted = first["attempted_manifest_indices"]
    assert isinstance(rows, list)
    assert isinstance(attempted, list)
    rows.pop()
    first["assigned_window_count"] = len(rows)

    with pytest.raises(
        SharedBR8FullObservationDensityError,
        match="attempted/report manifest population drift",
    ):
        build_r8_full_observation_density_diagnostic(tuple(reports))


def test_zero_event_window_cannot_carry_fake_timestamps() -> None:
    reports = list(deepcopy(_reports()))
    first = reports[0]
    rows = first["window_reports"]
    assert isinstance(rows, list)
    row = rows[0]
    assert isinstance(row, dict)
    assert row["bid_count"] == 0
    row["bid_first_at"] = row["from_at"]

    with pytest.raises(
        SharedBR8FullObservationDensityError,
        match="zero-event source window has timestamps",
    ):
        build_r8_full_observation_density_diagnostic(tuple(reports))


def test_provider_identity_drift_fails_closed() -> None:
    reports = list(deepcopy(_reports()))
    reports[0]["provider_symbol_id"] = 999999
    with pytest.raises(
        SharedBR8FullObservationDensityError,
        match="provider symbol id drift",
    ):
        build_r8_full_observation_density_diagnostic(tuple(reports))
