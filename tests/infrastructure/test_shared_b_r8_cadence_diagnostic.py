from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from qore.infrastructure.core_stack_v2.shared_b_r8_cadence_diagnostic import (
    SharedBR8CadenceDiagnosticError,
    build_r8_empirical_cadence_diagnostic,
)

CHECKPOINTS = (0, 736, 1473, 2210, 2947)
SENSORS = (("US2000", 10012), ("XAUUSD", 41), ("XTIUSD", 10019))


def _write_shard(
    root: Path,
    *,
    symbol: str,
    symbol_id: int,
    side: str,
    window: int,
    times: tuple[str, ...],
) -> dict[str, object]:
    rel = f"{side}/w{window:06d}-p000000-test.jsonl.gz"
    path = root / symbol / "data" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    record: dict[str, object] = {
        "quote_side": side,
        "window_index": window,
        "page_index": 0,
        "tick_count": len(times),
        "provenance_sha256": f"prov-{symbol}-{side}-{window}",
        "content_sha256": f"content-{symbol}-{side}-{window}",
        "relative_path": rel,
    }
    header = {
        "header": {
            "provider_symbol": symbol if times else None,
            "provider_symbol_id": symbol_id if times else None,
            **{
                key: record[key]
                for key in (
                    "quote_side",
                    "window_index",
                    "page_index",
                    "tick_count",
                    "provenance_sha256",
                    "content_sha256",
                )
            },
        }
    }
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(json.dumps(header) + "\n")
        for index, timestamp in enumerate(times):
            handle.write(
                json.dumps(
                    {
                        "tick": {
                            "price": str(100 + index),
                            "provider_event_at": timestamp,
                        }
                    }
                )
                + "\n"
            )
    return record


def _fixture(root: Path) -> dict[str, object]:
    reports: list[dict[str, object]] = []
    base_times = (
        "2017-01-01T00:00:00+00:00",
        "2017-01-01T00:00:01+00:00",
        "2017-01-01T00:00:03+00:00",
    )
    for symbol, symbol_id in SENSORS:
        records: list[dict[str, object]] = []
        for side in ("bid", "ask"):
            for window in CHECKPOINTS:
                times = (
                    base_times
                    if symbol != "XTIUSD" or window in (2210, 2947)
                    else ()
                )
                records.append(
                    _write_shard(
                        root,
                        symbol=symbol,
                        symbol_id=symbol_id,
                        side=side,
                        window=window,
                        times=times,
                    )
                )
        reports.append(
            {
                "provider_symbol": symbol,
                "provider_symbol_id": symbol_id,
                "records": records,
            }
        )
    return {
        "identity": "SHARED_B_WP05_CROSS_ASSET_AVAILABILITY_RAW_001",
        "source_manifest_sha256": (
            "2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191"
        ),
        "selected_manifest_indices": list(CHECKPOINTS),
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
        "candidate_reports": reports,
    }


def test_reducer_is_descriptive_and_fail_closed(tmp_path: Path) -> None:
    manifest = _fixture(tmp_path)
    reports = manifest["candidate_reports"]
    assert isinstance(reports, list)
    for report in reports:
        assert isinstance(report, dict)
        records = report["records"]
        assert isinstance(records, list)
        assert all(
            "provider_symbol" not in record
            and "provider_symbol_id" not in record
            for record in records
            if isinstance(record, dict)
        )

    payload = build_r8_empirical_cadence_diagnostic(
        raw_root=tmp_path,
        raw_manifest=manifest,
    )
    assert payload["sensor_count"] == 3
    assert payload["sensor_side_count"] == 6
    assert payload["cadence_policy_registry_frozen"] is False
    assert payload["stale_thresholds_frozen"] is False
    assert payload["global_threshold_extrapolation_authorized"] is False
    assert payload["relational_comparability_authorized"] is False
    assert payload["b08_complete"] is False

    records = payload["records"]
    us_bid = next(
        row
        for row in records
        if row["provider_symbol"] == "US2000"
        and row["quote_side"] == "bid"
    )
    assert us_bid["populated_checkpoint_count"] == 5
    assert us_bid["aggregate"]["p50_ms"] == 1500.0

    xti_bid = next(
        row
        for row in records
        if row["provider_symbol"] == "XTIUSD"
        and row["quote_side"] == "bid"
    )
    assert xti_bid["populated_checkpoint_count"] == 2


def test_rejects_checkpoint_drift(tmp_path: Path) -> None:
    manifest = _fixture(tmp_path)
    manifest["selected_manifest_indices"] = [0, 736]
    with pytest.raises(
        SharedBR8CadenceDiagnosticError,
        match="checkpoint selection drift",
    ):
        build_r8_empirical_cadence_diagnostic(
            raw_root=tmp_path,
            raw_manifest=manifest,
        )


def test_rejects_forbidden_outcome_read(tmp_path: Path) -> None:
    manifest = _fixture(tmp_path)
    manifest["target_or_outcome_read"] = True
    with pytest.raises(
        SharedBR8CadenceDiagnosticError,
        match="target_or_outcome_read",
    ):
        build_r8_empirical_cadence_diagnostic(
            raw_root=tmp_path,
            raw_manifest=manifest,
        )
