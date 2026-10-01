"""Architect-B empirical cadence diagnostic over sealed R8 raw quotes.

The reducer is descriptive only. It measures provider-event inter-arrival
distributions at preregistered R8 checkpoints and explicitly refuses to turn
those measurements into cadence, stale, liquidity, skew, or comparability
thresholds.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import cast

IDENTITY = "SHARED_B_R8_EMPIRICAL_CADENCE_DIAGNOSTIC_001"
EXPECTED_RAW_IDENTITY = "SHARED_B_WP05_CROSS_ASSET_AVAILABILITY_RAW_001"
EXPECTED_SOURCE_MANIFEST_SHA256 = (
    "2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191"
)
EXPECTED_CHECKPOINTS = (0, 736, 1473, 2210, 2947)
EXPECTED_SENSORS = {
    "US2000": 10012,
    "XAUUSD": 41,
    "XTIUSD": 10019,
}


class SharedBR8CadenceDiagnosticError(ValueError):
    """Empirical cadence evidence failed closed."""


def _sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _quantile(values: list[int], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return float(ordered[low])
    fraction = position - low
    return (
        float(ordered[low]) * (1.0 - fraction)
        + float(ordered[high]) * fraction
    )


def _stats(intervals_ms: list[int]) -> dict[str, object]:
    return {
        "interval_count": len(intervals_ms),
        "p50_ms": _quantile(intervals_ms, 0.50),
        "p90_ms": _quantile(intervals_ms, 0.90),
        "p95_ms": _quantile(intervals_ms, 0.95),
        "p99_ms": _quantile(intervals_ms, 0.99),
        "max_ms": float(max(intervals_ms)) if intervals_ms else None,
    }


def _event_times(path: Path, expected: dict[str, object]) -> list[datetime]:
    if not path.is_file():
        raise SharedBR8CadenceDiagnosticError(
            f"sealed raw shard missing: {path}"
        )
    times: list[datetime] = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        first = handle.readline()
        if not first:
            raise SharedBR8CadenceDiagnosticError("raw shard is empty")
        header = json.loads(first).get("header")
        if not isinstance(header, dict):
            raise SharedBR8CadenceDiagnosticError(
                "raw shard header missing"
            )
        for key in (
            "provider_symbol",
            "provider_symbol_id",
            "quote_side",
            "window_index",
            "page_index",
            "tick_count",
            "provenance_sha256",
            "content_sha256",
        ):
            if header.get(key) != expected.get(key):
                raise SharedBR8CadenceDiagnosticError(
                    f"raw shard header mismatch: {key}"
                )
        for line in handle:
            if not line.strip():
                continue
            tick = json.loads(line).get("tick")
            if not isinstance(tick, dict):
                raise SharedBR8CadenceDiagnosticError(
                    "raw shard tick missing"
                )
            raw_time = tick.get("provider_event_at")
            if not isinstance(raw_time, str):
                raise SharedBR8CadenceDiagnosticError(
                    "provider_event_at missing"
                )
            parsed = datetime.fromisoformat(raw_time)
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise SharedBR8CadenceDiagnosticError(
                    "provider_event_at must be timezone-aware"
                )
            times.append(parsed)
    if len(times) != expected.get("tick_count"):
        raise SharedBR8CadenceDiagnosticError(
            "raw shard tick count mismatch"
        )
    return times


def build_r8_empirical_cadence_diagnostic(
    *,
    raw_root: Path,
    raw_manifest: dict[str, object],
) -> dict[str, object]:
    if raw_manifest.get("identity") != EXPECTED_RAW_IDENTITY:
        raise SharedBR8CadenceDiagnosticError(
            "unexpected raw manifest identity"
        )
    if (
        raw_manifest.get("source_manifest_sha256")
        != EXPECTED_SOURCE_MANIFEST_SHA256
    ):
        raise SharedBR8CadenceDiagnosticError(
            "source manifest hash drift"
        )
    selected_manifest_indices = raw_manifest.get("selected_manifest_indices")
    if (
        not isinstance(selected_manifest_indices, list)
        or tuple(selected_manifest_indices) != EXPECTED_CHECKPOINTS
    ):
        raise SharedBR8CadenceDiagnosticError(
            "R8 checkpoint selection drift"
        )
    for field in (
        "target_or_outcome_read",
        "r6_r5_read",
        "fresh_holdout_opened",
        "broker_mutation",
    ):
        if raw_manifest.get(field) is not False:
            raise SharedBR8CadenceDiagnosticError(
                f"forbidden governance state: {field}"
            )

    reports = raw_manifest.get("candidate_reports")
    if not isinstance(reports, list) or len(reports) != 3:
        raise SharedBR8CadenceDiagnosticError(
            "expected exact three source candidates"
        )

    output: list[dict[str, object]] = []
    observed_sensors: dict[str, int] = {}

    for raw_report in reports:
        if not isinstance(raw_report, dict):
            raise SharedBR8CadenceDiagnosticError(
                "candidate report must be object"
            )
        report = cast(dict[str, object], raw_report)
        symbol = report.get("provider_symbol")
        symbol_id = report.get("provider_symbol_id")
        if (
            not isinstance(symbol, str)
            or symbol not in EXPECTED_SENSORS
            or type(symbol_id) is not int
            or symbol_id != EXPECTED_SENSORS[symbol]
        ):
            raise SharedBR8CadenceDiagnosticError(
                "unexpected provider sensor identity"
            )
        if symbol in observed_sensors:
            raise SharedBR8CadenceDiagnosticError(
                "duplicate provider sensor"
            )
        observed_sensors[symbol] = symbol_id

        records = report.get("records")
        if not isinstance(records, list):
            raise SharedBR8CadenceDiagnosticError(
                "candidate records missing"
            )
        grouped: dict[tuple[str, int], list[datetime]] = defaultdict(list)
        for raw_record in records:
            if not isinstance(raw_record, dict):
                raise SharedBR8CadenceDiagnosticError(
                    "candidate record invalid"
                )
            record = cast(dict[str, object], raw_record)
            side = record.get("quote_side")
            window = record.get("window_index")
            relative = record.get("relative_path")
            if side not in {"bid", "ask"}:
                raise SharedBR8CadenceDiagnosticError(
                    "quote side must be bid/ask"
                )
            if type(window) is not int or window not in EXPECTED_CHECKPOINTS:
                raise SharedBR8CadenceDiagnosticError(
                    "unexpected R8 checkpoint"
                )
            if not isinstance(relative, str) or not relative:
                raise SharedBR8CadenceDiagnosticError(
                    "relative shard path missing"
                )
            shard = raw_root / symbol / "data" / relative
            grouped[(side, window)].extend(
                _event_times(shard, record)
            )

        for side in ("bid", "ask"):
            checkpoint_rows: list[dict[str, object]] = []
            aggregate_intervals: list[int] = []
            for window in EXPECTED_CHECKPOINTS:
                timestamps = sorted(set(grouped.get((side, window), ())))
                intervals = [
                    round((right - left).total_seconds() * 1000)
                    for left, right in zip(timestamps, timestamps[1:], strict=False)
                    if right >= left
                ]
                aggregate_intervals.extend(intervals)
                row = {
                    "window_index": window,
                    "unique_provider_event_count": len(timestamps),
                    **_stats(intervals),
                }
                checkpoint_rows.append(row)

            populated = sum(
                int(row["unique_provider_event_count"]) > 0
                for row in checkpoint_rows
            )
            p99_values: list[float] = []
            for checkpoint_row in checkpoint_rows:
                p99_value = checkpoint_row["p99_ms"]
                if isinstance(p99_value, (int, float)):
                    p99_values.append(float(p99_value))
            p99_min = min(p99_values) if p99_values else None
            p99_max = max(p99_values) if p99_values else None
            ratio_bps = (
                round(p99_max / p99_min * 10_000)
                if (
                    p99_min is not None
                    and p99_min != 0.0
                    and p99_max is not None
                )
                else None
            )
            output.append(
                {
                    "provider_symbol": symbol,
                    "provider_symbol_id": symbol_id,
                    "quote_side": side,
                    "checkpoint_count": len(EXPECTED_CHECKPOINTS),
                    "populated_checkpoint_count": populated,
                    "checkpoint_reports": checkpoint_rows,
                    "aggregate": _stats(aggregate_intervals),
                    "checkpoint_p99_min_ms": p99_min,
                    "checkpoint_p99_max_ms": p99_max,
                    "checkpoint_p99_max_min_ratio_bps": ratio_bps,
                    "cadence_threshold_frozen": False,
                    "global_threshold_authorized": False,
                }
            )

    if observed_sensors != EXPECTED_SENSORS:
        raise SharedBR8CadenceDiagnosticError(
            "source sensor population drift"
        )

    output.sort(
        key=lambda item: (
            str(item["provider_symbol"]),
            str(item["quote_side"]),
        )
    )
    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "EMPIRICAL_CADENCE_DIAGNOSTIC_ONLY",
        "source_identity": EXPECTED_RAW_IDENTITY,
        "source_manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
        "checkpoint_indices": EXPECTED_CHECKPOINTS,
        "sensor_count": 3,
        "sensor_side_count": len(output),
        "method": (
            "UNIQUE_PROVIDER_EVENT_TIMESTAMPS_WITHIN_EACH_FROZEN_R8_WINDOW"
        ),
        "records": output,
        "cadence_policy_registry_frozen": False,
        "stale_thresholds_frozen": False,
        "liquidity_thresholds_frozen": False,
        "temporal_skew_thresholds_frozen": False,
        "comparability_thresholds_frozen": False,
        "global_threshold_extrapolation_authorized": False,
        "relational_comparability_authorized": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
        "productive_authority": False,
        "b08_complete": False,
    }
    payload["diagnostic_fingerprint_sha256"] = _sha256(payload)
    return payload
