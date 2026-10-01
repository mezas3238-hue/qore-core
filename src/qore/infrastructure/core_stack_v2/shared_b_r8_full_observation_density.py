"""Architect-B full-R8 observation-density diagnostic.

Reduces the 32 compact B-04 source-only shard reports for US2000 and XAUUSD.
The reducer never opens raw tick blobs, target/outcome evidence, R6/R5 or the
fresh holdout. It computes only exact descriptive source-observability metrics
that can be derived from per-window count/first/last timestamps.

No cadence, liquidity, skew or relational threshold is frozen by this module.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import cast

IDENTITY = "SHARED_B_R8_FULL_OBSERVATION_DENSITY_DIAGNOSTIC_001"
EXPECTED_REPORT_IDENTITY = (
    "QORE_SHARED_WP05_V15_CROSS_ASSET_R8_ACQUISITION_001"
)
EXPECTED_MANIFEST_SHA256 = (
    "2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191"
)
EXPECTED_WINDOW_COUNT = 2948
EXPECTED_SHARD_COUNT = 16
EXPECTED_FAMILIES: dict[str, tuple[str, int]] = {
    "US2000_BREADTH_PROXY": ("US2000", 10012),
    "XAUUSD_DEFENSIVE_PROXY": ("XAUUSD", 41),
}


class SharedBR8FullObservationDensityError(ValueError):
    """Full-R8 compact-report evidence failed closed."""


def _sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _aware(value: object, *, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise SharedBR8FullObservationDensityError(f"{field} missing")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SharedBR8FullObservationDensityError(
            f"{field} invalid"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SharedBR8FullObservationDensityError(
            f"{field} must be timezone-aware"
        )
    return parsed


def _nearest_rank(values: list[int], percentile_bps: int) -> int | None:
    if not values:
        return None
    if not 0 <= percentile_bps <= 10_000:
        raise SharedBR8FullObservationDensityError(
            "percentile_bps outside 0..10000"
        )
    ordered = sorted(values)
    if percentile_bps == 0:
        return ordered[0]
    rank = (percentile_bps * len(ordered) + 9_999) // 10_000
    index = max(0, min(len(ordered) - 1, rank - 1))
    return ordered[index]


def _side_metrics(
    windows: list[dict[str, object]],
    *,
    side: str,
) -> dict[str, object]:
    count_key = f"{side}_count"
    first_key = f"{side}_first_at"
    last_key = f"{side}_last_at"

    total_ticks = 0
    empty_indices: list[int] = []
    single_event_count = 0
    multi_event_count = 0
    interval_denominator = 0
    total_interval_span_ms = 0
    per_window_mean_intervals_ms: list[int] = []
    observed_span_ratio_bps: list[int] = []
    tick_counts: list[int] = []

    for row in windows:
        index = row["manifest_index"]
        count = row[count_key]
        from_at = row["from_at"]
        to_at = row["to_at"]
        if type(index) is not int or type(count) is not int:
            raise SharedBR8FullObservationDensityError(
                "normalized window integer drift"
            )
        if not isinstance(from_at, datetime) or not isinstance(to_at, datetime):
            raise SharedBR8FullObservationDensityError(
                "normalized window datetime drift"
            )

        tick_counts.append(count)
        total_ticks += count
        duration_ms = round((to_at - from_at).total_seconds() * 1000)
        if duration_ms <= 0:
            raise SharedBR8FullObservationDensityError(
                "window duration must be positive"
            )

        first_at = row[first_key]
        last_at = row[last_key]
        if count == 0:
            if first_at is not None or last_at is not None:
                raise SharedBR8FullObservationDensityError(
                    "zero-event window cannot carry event timestamps"
                )
            empty_indices.append(index)
            observed_span_ratio_bps.append(0)
            continue

        if not isinstance(first_at, datetime) or not isinstance(last_at, datetime):
            raise SharedBR8FullObservationDensityError(
                "populated window timestamps missing"
            )
        if not (from_at <= first_at <= last_at <= to_at):
            raise SharedBR8FullObservationDensityError(
                "event timestamps escaped source window"
            )

        span_ms = round((last_at - first_at).total_seconds() * 1000)
        observed_span_ratio_bps.append(
            min(10_000, round(span_ms / duration_ms * 10_000))
        )
        if count == 1:
            if first_at != last_at:
                raise SharedBR8FullObservationDensityError(
                    "single-event window must have identical first/last"
                )
            single_event_count += 1
            continue

        multi_event_count += 1
        intervals = count - 1
        interval_denominator += intervals
        total_interval_span_ms += span_ms
        per_window_mean_intervals_ms.append(round(span_ms / intervals))

    weighted_mean = (
        round(total_interval_span_ms / interval_denominator)
        if interval_denominator
        else None
    )
    return {
        "tick_count": total_ticks,
        "populated_window_count": len(windows) - len(empty_indices),
        "empty_window_count": len(empty_indices),
        "empty_window_indices": tuple(empty_indices),
        "single_event_window_count": single_event_count,
        "multi_event_window_count": multi_event_count,
        "weighted_mean_interarrival_ms": weighted_mean,
        "per_window_mean_interarrival_p50_ms": _nearest_rank(
            per_window_mean_intervals_ms, 5_000
        ),
        "per_window_mean_interarrival_p95_ms": _nearest_rank(
            per_window_mean_intervals_ms, 9_500
        ),
        "per_window_mean_interarrival_p99_ms": _nearest_rank(
            per_window_mean_intervals_ms, 9_900
        ),
        "window_tick_count_p50": _nearest_rank(tick_counts, 5_000),
        "window_tick_count_p95": _nearest_rank(tick_counts, 9_500),
        "window_tick_count_p99": _nearest_rank(tick_counts, 9_900),
        "observed_span_ratio_p50_bps": _nearest_rank(
            observed_span_ratio_bps, 5_000
        ),
        "observed_span_ratio_p95_bps": _nearest_rank(
            observed_span_ratio_bps, 9_500
        ),
        "threshold_authority": False,
    }


def build_r8_full_observation_density_diagnostic(
    reports: tuple[dict[str, object], ...],
) -> dict[str, object]:
    if len(reports) != len(EXPECTED_FAMILIES) * EXPECTED_SHARD_COUNT:
        raise SharedBR8FullObservationDensityError(
            "expected exact 32 compact B-04 reports"
        )

    by_family: dict[str, list[dict[str, object]]] = {
        family: [] for family in EXPECTED_FAMILIES
    }
    for report in reports:
        family = report.get("family")
        if not isinstance(family, str) or family not in EXPECTED_FAMILIES:
            raise SharedBR8FullObservationDensityError(
                "unexpected B-04 family"
            )
        by_family[family].append(report)

    sensor_payloads: dict[str, object] = {}
    for family in sorted(EXPECTED_FAMILIES):
        provider_symbol, provider_symbol_id = EXPECTED_FAMILIES[family]
        family_reports = sorted(
            by_family[family],
            key=lambda item: cast(int, item.get("shard_index")),
        )
        shard_indices: list[int] = []
        normalized_windows: list[dict[str, object]] = []

        for report in family_reports:
            if report.get("identity") != EXPECTED_REPORT_IDENTITY:
                raise SharedBR8FullObservationDensityError(
                    "unexpected compact report identity"
                )
            if report.get("partition") != "r8_source_only":
                raise SharedBR8FullObservationDensityError(
                    "unexpected compact report partition"
                )
            if report.get("manifest_sha256") != EXPECTED_MANIFEST_SHA256:
                raise SharedBR8FullObservationDensityError(
                    "source manifest hash drift"
                )
            if report.get("family") != family:
                raise SharedBR8FullObservationDensityError(
                    "family report drift"
                )
            if report.get("provider_symbol") != provider_symbol:
                raise SharedBR8FullObservationDensityError(
                    "provider symbol drift"
                )
            if report.get("provider_symbol_id") != provider_symbol_id:
                raise SharedBR8FullObservationDensityError(
                    "provider symbol id drift"
                )
            if report.get("shard_count") != EXPECTED_SHARD_COUNT:
                raise SharedBR8FullObservationDensityError(
                    "shard count drift"
                )
            if report.get("total_manifest_windows") != EXPECTED_WINDOW_COUNT:
                raise SharedBR8FullObservationDensityError(
                    "manifest window count drift"
                )
            if report.get("assignment_rule") != "MANIFEST_INDEX_MOD_16":
                raise SharedBR8FullObservationDensityError(
                    "assignment rule drift"
                )
            if report.get("read_only_message_firewall") is not True:
                raise SharedBR8FullObservationDensityError(
                    "read-only firewall not sealed"
                )
            for key in (
                "target_or_outcome_read",
                "r6_r5_read",
                "fresh_holdout_opened",
                "scientific_v15_outcomes_opened",
                "shared_methodology_authority",
                "shared_sizing_authority",
                "shared_risk_authority",
                "shared_order_authority",
                "shared_execution_authority",
            ):
                if report.get(key) is not False:
                    raise SharedBR8FullObservationDensityError(
                        f"forbidden report authority/state: {key}"
                    )

            shard_index = report.get("shard_index")
            if type(shard_index) is not int or not 0 <= shard_index < 16:
                raise SharedBR8FullObservationDensityError(
                    "invalid shard index"
                )
            shard_indices.append(shard_index)

            windows = report.get("window_reports")
            attempted = report.get("attempted_manifest_indices")
            assigned_count = report.get("assigned_window_count")
            if not isinstance(windows, list) or not isinstance(attempted, list):
                raise SharedBR8FullObservationDensityError(
                    "compact window population missing"
                )
            if type(assigned_count) is not int or assigned_count != len(windows):
                raise SharedBR8FullObservationDensityError(
                    "assigned window count mismatch"
                )

            attempted_ints: list[int] = []
            for item in attempted:
                if type(item) is not int:
                    raise SharedBR8FullObservationDensityError(
                        "attempted manifest index invalid"
                    )
                attempted_ints.append(item)

            report_indices: list[int] = []
            for raw_window in windows:
                if not isinstance(raw_window, dict):
                    raise SharedBR8FullObservationDensityError(
                        "compact window row invalid"
                    )
                row = cast(dict[str, object], raw_window)
                manifest_index = row.get("manifest_index")
                if (
                    type(manifest_index) is not int
                    or not 0 <= manifest_index < EXPECTED_WINDOW_COUNT
                    or manifest_index % EXPECTED_SHARD_COUNT != shard_index
                ):
                    raise SharedBR8FullObservationDensityError(
                        "window escaped deterministic shard assignment"
                    )
                report_indices.append(manifest_index)

                from_at = _aware(
                    row.get("from_at"),
                    field=f"{family}:{manifest_index}:from_at",
                )
                to_at = _aware(
                    row.get("to_at"),
                    field=f"{family}:{manifest_index}:to_at",
                )
                if to_at <= from_at:
                    raise SharedBR8FullObservationDensityError(
                        "source window is not forward"
                    )

                normalized: dict[str, object] = {
                    "manifest_index": manifest_index,
                    "from_at": from_at,
                    "to_at": to_at,
                }
                for side in ("bid", "ask"):
                    count = row.get(f"{side}_count")
                    first_raw = row.get(f"{side}_first_at")
                    last_raw = row.get(f"{side}_last_at")
                    if type(count) is not int or count < 0:
                        raise SharedBR8FullObservationDensityError(
                            f"{side} count invalid"
                        )
                    normalized[f"{side}_count"] = count
                    if count == 0:
                        if first_raw is not None or last_raw is not None:
                            raise SharedBR8FullObservationDensityError(
                                "zero-event source window has timestamps"
                            )
                        normalized[f"{side}_first_at"] = None
                        normalized[f"{side}_last_at"] = None
                    else:
                        first_at = _aware(
                            first_raw,
                            field=f"{family}:{manifest_index}:{side}_first_at",
                        )
                        last_at = _aware(
                            last_raw,
                            field=f"{family}:{manifest_index}:{side}_last_at",
                        )
                        normalized[f"{side}_first_at"] = first_at
                        normalized[f"{side}_last_at"] = last_at
                normalized_windows.append(normalized)

            if report_indices != attempted_ints:
                raise SharedBR8FullObservationDensityError(
                    "attempted/report manifest population drift"
                )

        if shard_indices != list(range(EXPECTED_SHARD_COUNT)):
            raise SharedBR8FullObservationDensityError(
                "exact shard population incomplete"
            )
        normalized_windows.sort(
            key=lambda row: cast(int, row["manifest_index"])
        )
        indices = [cast(int, row["manifest_index"]) for row in normalized_windows]
        if indices != list(range(EXPECTED_WINDOW_COUNT)):
            raise SharedBR8FullObservationDensityError(
                "exact 2948-window population incomplete"
            )

        compact_fingerprint_rows = [
            {
                "manifest_index": row["manifest_index"],
                "from_at": cast(datetime, row["from_at"]).isoformat(),
                "to_at": cast(datetime, row["to_at"]).isoformat(),
                "bid_count": row["bid_count"],
                "bid_first_at": (
                    None
                    if row["bid_first_at"] is None
                    else cast(datetime, row["bid_first_at"]).isoformat()
                ),
                "bid_last_at": (
                    None
                    if row["bid_last_at"] is None
                    else cast(datetime, row["bid_last_at"]).isoformat()
                ),
                "ask_count": row["ask_count"],
                "ask_first_at": (
                    None
                    if row["ask_first_at"] is None
                    else cast(datetime, row["ask_first_at"]).isoformat()
                ),
                "ask_last_at": (
                    None
                    if row["ask_last_at"] is None
                    else cast(datetime, row["ask_last_at"]).isoformat()
                ),
            }
            for row in normalized_windows
        ]
        bid = _side_metrics(normalized_windows, side="bid")
        ask = _side_metrics(normalized_windows, side="ask")
        bid_empty = set(cast(tuple[int, ...], bid["empty_window_indices"]))
        ask_empty = set(cast(tuple[int, ...], ask["empty_window_indices"]))
        sensor_payloads[family] = {
            "provider_symbol": provider_symbol,
            "provider_symbol_id": provider_symbol_id,
            "shard_count": EXPECTED_SHARD_COUNT,
            "window_count": EXPECTED_WINDOW_COUNT,
            "bid": bid,
            "ask": ask,
            "both_sides_empty_window_count": len(bid_empty & ask_empty),
            "one_side_only_empty_window_count": len(bid_empty ^ ask_empty),
            "window_population_fingerprint_sha256": _sha256(
                compact_fingerprint_rows
            ),
            "cadence_policy_frozen": False,
            "liquidity_policy_frozen": False,
            "temporal_skew_policy_frozen": False,
            "comparability_policy_frozen": False,
        }

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "FULL_R8_OBSERVATION_DENSITY_DIAGNOSTIC_ONLY",
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "sensor_count": len(EXPECTED_FAMILIES),
        "sensor_window_count": len(EXPECTED_FAMILIES) * EXPECTED_WINDOW_COUNT,
        "sensors": sensor_payloads,
        "compact_reports_only": True,
        "raw_tick_blob_read": False,
        "cadence_policy_registry_frozen": False,
        "liquidity_policy_registry_frozen": False,
        "temporal_skew_policy_registry_frozen": False,
        "comparability_policy_registry_frozen": False,
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
