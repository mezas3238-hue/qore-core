"""Architect-B full-R8 observability density diagnostic.

Consumes only compact, sealed B-04 report artifacts. It measures window-level
observability density, first-event lag, terminal gap and active span without
reading target/outcome data and without freezing cadence, stale, liquidity,
skew or comparability thresholds.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from typing import cast

IDENTITY = "SHARED_B_FULL_R8_OBSERVABILITY_DENSITY_001"
EXPECTED_MANIFEST_SHA256 = (
    "2f18b9f11d5893effa46ac85c712edd6646d1d90a9de521b235143e42155d191"
)
EXPECTED_FAMILIES = {
    "US2000_BREADTH_PROXY": ("US2000", 10012),
    "XAUUSD_DEFENSIVE_PROXY": ("XAUUSD", 41),
}


class SharedBR8ObservabilityDensityError(ValueError):
    """Full-R8 observability density evidence failed closed."""


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return ordered[low]
    frac = pos - low
    return ordered[low] * (1.0 - frac) + ordered[high] * frac


def _stats(values: list[float]) -> dict[str, object]:
    return {
        "count": len(values),
        "p50": _quantile(values, 0.50),
        "p90": _quantile(values, 0.90),
        "p95": _quantile(values, 0.95),
        "p99": _quantile(values, 0.99),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def _aware(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise SharedBR8ObservabilityDensityError(f"{field} missing")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SharedBR8ObservabilityDensityError(
            f"{field} invalid"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SharedBR8ObservabilityDensityError(
            f"{field} must be timezone-aware"
        )
    return parsed


def _optional_aware(value: object, *, field: str) -> datetime | None:
    if value is None:
        return None
    return _aware(value, field=field)


def build_full_r8_observability_density(
    *,
    reports_dir: Path,
) -> dict[str, object]:
    paths = sorted(reports_dir.rglob("*-report.json"))
    if len(paths) != 32:
        raise SharedBR8ObservabilityDensityError(
            f"expected exact 32 compact reports, got {len(paths)}"
        )

    by_family: dict[str, list[dict[str, object]]] = {
        family: [] for family in EXPECTED_FAMILIES
    }
    for path in paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise SharedBR8ObservabilityDensityError(
                "compact report must be object"
            )
        report = cast(dict[str, object], raw)
        family = report.get("family")
        if not isinstance(family, str) or family not in EXPECTED_FAMILIES:
            raise SharedBR8ObservabilityDensityError(
                "unexpected report family"
            )
        symbol, symbol_id = EXPECTED_FAMILIES[family]
        required = {
            "identity": "QORE_SHARED_WP05_V15_CROSS_ASSET_R8_ACQUISITION_001",
            "manifest_sha256": EXPECTED_MANIFEST_SHA256,
            "partition": "r8_source_only",
            "provider_symbol": symbol,
            "provider_symbol_id": symbol_id,
            "canonical_instrument": symbol,
            "shard_count": 16,
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
        }
        for key, expected in required.items():
            if report.get(key) != expected:
                raise SharedBR8ObservabilityDensityError(
                    f"report invariant mismatch: {family}:{key}"
                )
        by_family[family].append(report)

    family_outputs: dict[str, object] = {}
    for family, reports in by_family.items():
        if len(reports) != 16:
            raise SharedBR8ObservabilityDensityError(
                f"{family} must contain exact 16 shards"
            )
        shard_indices = sorted(
            cast(int, report["shard_index"]) for report in reports
        )
        if shard_indices != list(range(16)):
            raise SharedBR8ObservabilityDensityError(
                f"{family} shard index drift"
            )

        seen_windows: set[int] = set()
        bid_counts: list[float] = []
        ask_counts: list[float] = []
        bid_first_lags: list[float] = []
        ask_first_lags: list[float] = []
        bid_terminal_gaps: list[float] = []
        ask_terminal_gaps: list[float] = []
        bid_active_spans: list[float] = []
        ask_active_spans: list[float] = []
        bid_ticks_per_minute: list[float] = []
        ask_ticks_per_minute: list[float] = []
        empty_bid = 0
        empty_ask = 0

        for report in reports:
            rows = report.get("window_reports")
            if not isinstance(rows, list):
                raise SharedBR8ObservabilityDensityError(
                    f"{family} window reports missing"
                )
            for raw_row in rows:
                if not isinstance(raw_row, dict):
                    raise SharedBR8ObservabilityDensityError(
                        "window report must be object"
                    )
                row = cast(dict[str, object], raw_row)
                index = row.get("manifest_index")
                if type(index) is not int or not 0 <= index < 2948:
                    raise SharedBR8ObservabilityDensityError(
                        "manifest index invalid"
                    )
                if index in seen_windows:
                    raise SharedBR8ObservabilityDensityError(
                        f"duplicate manifest index: {index}"
                    )
                seen_windows.add(index)

                start = _aware(row.get("from_at"), field="from_at")
                end = _aware(row.get("to_at"), field="to_at")
                duration_ms = (end - start).total_seconds() * 1000.0
                if duration_ms <= 0:
                    raise SharedBR8ObservabilityDensityError(
                        "window duration must be positive"
                    )
                duration_minutes = duration_ms / 60_000.0

                for side in ("bid", "ask"):
                    count_raw = row.get(f"{side}_count")
                    if type(count_raw) is not int or count_raw < 0:
                        raise SharedBR8ObservabilityDensityError(
                            f"{side}_count invalid"
                        )
                    count = count_raw
                    counts = bid_counts if side == "bid" else ask_counts
                    counts.append(float(count))
                    densities = (
                        bid_ticks_per_minute
                        if side == "bid"
                        else ask_ticks_per_minute
                    )
                    densities.append(count / duration_minutes)

                    first = _optional_aware(
                        row.get(f"{side}_first_at"),
                        field=f"{side}_first_at",
                    )
                    last = _optional_aware(
                        row.get(f"{side}_last_at"),
                        field=f"{side}_last_at",
                    )
                    if count == 0:
                        if first is not None or last is not None:
                            raise SharedBR8ObservabilityDensityError(
                                f"empty {side} window has timestamps"
                            )
                        if side == "bid":
                            empty_bid += 1
                        else:
                            empty_ask += 1
                        continue
                    if first is None or last is None:
                        raise SharedBR8ObservabilityDensityError(
                            f"populated {side} window lacks timestamps"
                        )
                    if not start <= first <= last <= end:
                        raise SharedBR8ObservabilityDensityError(
                            f"{side} timestamps escaped window"
                        )
                    first_lag = (first - start).total_seconds() * 1000.0
                    terminal_gap = (end - last).total_seconds() * 1000.0
                    active_span = (last - first).total_seconds() * 1000.0
                    if side == "bid":
                        bid_first_lags.append(first_lag)
                        bid_terminal_gaps.append(terminal_gap)
                        bid_active_spans.append(active_span)
                    else:
                        ask_first_lags.append(first_lag)
                        ask_terminal_gaps.append(terminal_gap)
                        ask_active_spans.append(active_span)

        if seen_windows != set(range(2948)):
            missing = sorted(set(range(2948)) - seen_windows)
            raise SharedBR8ObservabilityDensityError(
                f"{family} does not cover exact 2948 windows: {missing[:5]}"
            )

        family_outputs[family] = {
            "provider_symbol": EXPECTED_FAMILIES[family][0],
            "provider_symbol_id": EXPECTED_FAMILIES[family][1],
            "report_shard_count": len(reports),
            "window_count": len(seen_windows),
            "empty_bid_window_count": empty_bid,
            "empty_ask_window_count": empty_ask,
            "full_bid_window_presence": empty_bid == 0,
            "full_ask_window_presence": empty_ask == 0,
            "bid_tick_count_distribution": _stats(bid_counts),
            "ask_tick_count_distribution": _stats(ask_counts),
            "bid_ticks_per_minute_distribution": _stats(
                bid_ticks_per_minute
            ),
            "ask_ticks_per_minute_distribution": _stats(
                ask_ticks_per_minute
            ),
            "bid_first_event_lag_ms_distribution": _stats(
                bid_first_lags
            ),
            "ask_first_event_lag_ms_distribution": _stats(
                ask_first_lags
            ),
            "bid_terminal_gap_ms_distribution": _stats(
                bid_terminal_gaps
            ),
            "ask_terminal_gap_ms_distribution": _stats(
                ask_terminal_gaps
            ),
            "bid_active_span_ms_distribution": _stats(
                bid_active_spans
            ),
            "ask_active_span_ms_distribution": _stats(
                ask_active_spans
            ),
            "observability_threshold_frozen": False,
            "liquidity_threshold_frozen": False,
            "stale_threshold_frozen": False,
            "comparability_authorized": False,
        }

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "FULL_R8_OBSERVABILITY_DENSITY_DIAGNOSTIC_ONLY",
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "family_count": len(family_outputs),
        "total_window_family_observations": 2948 * len(family_outputs),
        "families": family_outputs,
        "observability_policy_registry_frozen": False,
        "liquidity_policy_registry_frozen": False,
        "stale_policy_registry_frozen": False,
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
    payload["diagnostic_fingerprint_sha256"] = _fingerprint(payload)
    return payload
