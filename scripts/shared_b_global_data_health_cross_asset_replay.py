"""Replicate Architect-B global data-health states on sealed cross-asset ticks.

The raw ticks and their retrieval timestamps are immutable upstream evidence.
Fault flags are injected only to isolate deterministic health-state semantics;
they never rewrite provider_event_at or retrieved_at. In particular, a freshly
retrieved historical event must remain stale for market inference.
"""

from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b_cross_asset_source_replay import (
    SHARED_B_CROSS_ASSET_RAW_IDENTITY,
    verify_historical_quote_shard,
)
from qore.infrastructure.core_stack_v2.shared_b_global_data_health import (
    SharedBGlobalDataObservation,
    SharedBGlobalDataState,
    assess_shared_b_global_data_health,
)

IDENTITY = "SHARED_B_GLOBAL_DATA_HEALTH_CROSS_ASSET_REPLICATION_001"

_SCENARIOS: dict[str, tuple[SharedBGlobalDataState, dict[str, object]]] = {
    "HISTORICAL_FRESH_DOWNLOAD": (
        SharedBGlobalDataState.STALE_UNEXPECTED,
        {},
    ),
    "PROVIDER_UNAVAILABLE": (
        SharedBGlobalDataState.PROVIDER_UNAVAILABLE,
        {"provider_available": False},
    ),
    "FEED_UNAVAILABLE": (
        SharedBGlobalDataState.FEED_UNAVAILABLE,
        {"feed_available": False},
    ),
    "PROVIDER_DEGRADED": (
        SharedBGlobalDataState.PROVIDER_DEGRADED,
        {"provider_degraded": True},
    ),
    "PARTIAL_DEGRADATION": (
        SharedBGlobalDataState.PARTIAL_DEGRADATION,
        {"partial_degradation": True},
    ),
    "CROSSED_QUOTE": (
        SharedBGlobalDataState.CROSSED_QUOTE,
        {"crossed_quote": True},
    ),
    "IMPOSSIBLE_VALUE": (
        SharedBGlobalDataState.IMPOSSIBLE_VALUE,
        {"impossible_value": True},
    ),
    "UNKNOWN_MARKET_STATE": (
        SharedBGlobalDataState.MARKET_STATE_UNKNOWN,
        {"canonical_market_open": None},
    ),
    "IDENTITY_AMBIGUITY": (
        SharedBGlobalDataState.IDENTITY_AMBIGUITY,
        {"canonical_identity_verified": False},
    ),
}


class SharedBGlobalDataHealthReplayError(ValueError):
    """Sealed real-source data-health replication failed closed."""


def _parse_aware(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise SharedBGlobalDataHealthReplayError(f"{field} missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SharedBGlobalDataHealthReplayError(
            f"{field} must be ISO timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SharedBGlobalDataHealthReplayError(
            f"{field} must be timezone-aware"
        )
    return parsed


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SharedBGlobalDataHealthReplayError(
            f"{path} must contain an object"
        )
    return cast(dict[str, Any], payload)


def _first_tick(path: Path) -> dict[str, object]:
    try:
        raw = gzip.decompress(path.read_bytes()).decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise SharedBGlobalDataHealthReplayError(
            f"cannot decode raw shard: {path}"
        ) from exc
    lines = [line for line in raw.splitlines() if line]
    if len(lines) < 2:
        raise SharedBGlobalDataHealthReplayError(
            "positive-count raw shard omitted tick row"
        )
    try:
        envelope = json.loads(lines[1])
    except json.JSONDecodeError as exc:
        raise SharedBGlobalDataHealthReplayError(
            "raw tick JSON invalid"
        ) from exc
    if not isinstance(envelope, dict) or set(envelope) != {"tick"}:
        raise SharedBGlobalDataHealthReplayError(
            "raw tick envelope invalid"
        )
    tick = envelope["tick"]
    if not isinstance(tick, dict):
        raise SharedBGlobalDataHealthReplayError("raw tick invalid")
    return cast(dict[str, object], tick)


def _observation(
    *,
    instrument_key: str,
    provider_event_at: datetime,
    retrieved_at: datetime,
    scenario_overrides: dict[str, object],
) -> SharedBGlobalDataObservation:
    values: dict[str, object] = {
        "instrument_key": instrument_key,
        "decision_time": retrieved_at,
        "provider_event_at": provider_event_at,
        "retrieved_at": retrieved_at,
        "previous_provider_event_at": None,
        "expected_cadence_ms": 1_000,
        "validity_horizon_ms": 5_000,
        "decay_horizon_ms": 30_000,
        "canonical_market_open": True,
        "provider_available": True,
        "feed_available": True,
        "provider_degraded": False,
        "partial_degradation": False,
        "missing": False,
        "duplicate": False,
        "sequence_monotonic": True,
        "crossed_quote": False,
        "impossible_value": False,
        # Fault-isolation test input only. It is not an identity-certification claim.
        "canonical_identity_verified": True,
        "roll_identity_unambiguous": True,
        "relation_evidence_age_ms": None,
        "relation_validity_horizon_ms": None,
        "provenance_refs": ("sealed-cross-asset-raw",),
    }
    values.update(scenario_overrides)
    return SharedBGlobalDataObservation(**values)  # type: ignore[arg-type]


def run(
    *,
    raw_root: Path,
    raw_manifest_path: Path,
    output_path: Path,
    max_samples_per_symbol: int = 20,
) -> dict[str, object]:
    if max_samples_per_symbol <= 0:
        raise SharedBGlobalDataHealthReplayError(
            "max_samples_per_symbol must be positive"
        )
    manifest = _load_json(raw_manifest_path)
    if manifest.get("identity") != SHARED_B_CROSS_ASSET_RAW_IDENTITY:
        raise SharedBGlobalDataHealthReplayError("raw identity mismatch")
    if manifest.get("partition") != "r8_source_only":
        raise SharedBGlobalDataHealthReplayError("raw partition mismatch")
    for key in (
        "target_or_outcome_read",
        "r6_r5_read",
        "fresh_holdout_opened",
        "scientific_v15_opened",
        "broker_mutation",
        "shared_methodology_authority",
        "shared_sizing_authority",
        "shared_risk_authority",
        "shared_order_authority",
        "shared_execution_authority",
    ):
        if manifest.get(key) is not False:
            raise SharedBGlobalDataHealthReplayError(
                f"upstream governance violation: {key}"
            )

    candidates = manifest.get("candidate_reports")
    if not isinstance(candidates, list):
        raise SharedBGlobalDataHealthReplayError(
            "candidate reports missing"
        )

    symbol_reports: list[dict[str, object]] = []
    total_source_samples = 0
    total_scenario_checks = 0
    for candidate_any in candidates:
        if not isinstance(candidate_any, dict):
            raise SharedBGlobalDataHealthReplayError(
                "candidate report invalid"
            )
        candidate = cast(dict[str, object], candidate_any)
        symbol = candidate.get("provider_symbol")
        symbol_id = candidate.get("provider_symbol_id")
        records = candidate.get("records")
        data_root = candidate.get("data_root")
        if not isinstance(symbol, str) or not symbol:
            raise SharedBGlobalDataHealthReplayError(
                "provider symbol missing"
            )
        if type(symbol_id) is not int or symbol_id <= 0:
            raise SharedBGlobalDataHealthReplayError(
                "provider symbol id invalid"
            )
        if not isinstance(records, list):
            raise SharedBGlobalDataHealthReplayError(
                "raw records missing"
            )
        if not isinstance(data_root, str):
            # Technical-error candidate may legally have no materialized pages.
            symbol_reports.append(
                {
                    "provider_symbol": symbol,
                    "provider_symbol_id": symbol_id,
                    "source_sample_count": 0,
                    "scenario_check_count": 0,
                    "scenario_correct_counts": {},
                    "skipped_reason": "NO_RAW_DATA_ROOT",
                }
            )
            continue

        counts: Counter[str] = Counter()
        source_samples = 0
        for record_any in records:
            if source_samples >= max_samples_per_symbol:
                break
            if not isinstance(record_any, dict):
                raise SharedBGlobalDataHealthReplayError(
                    "raw record invalid"
                )
            record = cast(dict[str, object], record_any)
            if record.get("tick_count") == 0:
                continue
            relative = record.get("relative_path")
            if not isinstance(relative, str) or not relative:
                raise SharedBGlobalDataHealthReplayError(
                    "raw record path missing"
                )
            path = raw_root / data_root / relative
            verify_historical_quote_shard(
                path=path,
                expected=record,
            )
            tick = _first_tick(path)
            provider_event_at = _parse_aware(
                tick.get("provider_event_at"),
                field="provider_event_at",
            )
            retrieved_at = _parse_aware(
                record.get("retrieved_at"),
                field="retrieved_at",
            )
            if provider_event_at > retrieved_at:
                raise SharedBGlobalDataHealthReplayError(
                    "historical event cannot postdate retrieval"
                )

            instrument_key = f"CTRADER_DEMO:{symbol}:{symbol_id}"
            for scenario, (expected, overrides) in _SCENARIOS.items():
                assessment = assess_shared_b_global_data_health(
                    _observation(
                        instrument_key=instrument_key,
                        provider_event_at=provider_event_at,
                        retrieved_at=retrieved_at,
                        scenario_overrides=overrides,
                    )
                )
                if assessment.state is not expected:
                    raise SharedBGlobalDataHealthReplayError(
                        f"{symbol} {scenario} produced "
                        f"{assessment.state.value}, expected {expected.value}"
                    )
                if assessment.new_market_change_inference_allowed:
                    raise SharedBGlobalDataHealthReplayError(
                        f"{symbol} {scenario} allowed new market inference"
                    )
                if assessment.relational_claim_allowed:
                    raise SharedBGlobalDataHealthReplayError(
                        f"{symbol} {scenario} allowed relational claim"
                    )
                if scenario == "HISTORICAL_FRESH_DOWNLOAD":
                    if assessment.transport_age_ms != 0:
                        raise SharedBGlobalDataHealthReplayError(
                            "fresh historical download transport age must be zero"
                        )
                    if (
                        assessment.provider_event_age_ms is None
                        or assessment.provider_event_age_ms <= 5_000
                    ):
                        raise SharedBGlobalDataHealthReplayError(
                            "historical market event did not remain stale"
                        )
                    if assessment.reason_codes != ("MARKET_EVENT_STALE",):
                        raise SharedBGlobalDataHealthReplayError(
                            "historical stale reason drifted"
                        )
                counts[scenario] += 1
                total_scenario_checks += 1
            source_samples += 1
            total_source_samples += 1

        symbol_reports.append(
            {
                "provider_symbol": symbol,
                "provider_symbol_id": symbol_id,
                "source_sample_count": source_samples,
                "scenario_check_count": source_samples * len(_SCENARIOS),
                "scenario_correct_counts": dict(sorted(counts.items())),
                "skipped_reason": None,
            }
        )

    proven_symbols = [
        item
        for item in symbol_reports
        if int(item["source_sample_count"]) > 0
    ]
    if len(proven_symbols) < 2:
        raise SharedBGlobalDataHealthReplayError(
            "need at least two real cross-asset symbols"
        )
    if total_source_samples <= 0 or total_scenario_checks <= 0:
        raise SharedBGlobalDataHealthReplayError(
            "real source replication produced no checks"
        )

    report: dict[str, object] = {
        "identity": IDENTITY,
        "status": "REAL_CROSS_ASSET_DATA_HEALTH_REPLICATION_PASS",
        "source_identity": manifest["identity"],
        "source_partition": manifest["partition"],
        "source_manifest_sha256": manifest.get("source_manifest_sha256"),
        "provider_catalog_sha256": manifest.get("provider_catalog_sha256"),
        "real_cross_asset_symbol_count": len(proven_symbols),
        "real_source_sample_count": total_source_samples,
        "scenario_count": len(_SCENARIOS),
        "scenario_check_count": total_scenario_checks,
        "symbol_reports": symbol_reports,
        "fresh_download_cannot_reset_market_event_freshness": True,
        "fault_flags_only_for_state_isolation": True,
        "provider_and_retrieval_timestamps_rewritten": False,
        "stale_relation_empirical_isolation_complete": False,
        "stale_relation_reason": (
            "Historical raw evidence cannot be relabeled as point-in-time "
            "available relation evidence; empirical relation-state isolation "
            "remains gated by B-07/B-08 temporal comparability."
        ),
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
        "productive_authority": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--raw-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-samples-per-symbol", type=int, default=20)
    args = parser.parse_args()
    report = run(
        raw_root=args.raw_root,
        raw_manifest_path=args.raw_manifest,
        output_path=args.output,
        max_samples_per_symbol=args.max_samples_per_symbol,
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "real_cross_asset_symbol_count": report[
                    "real_cross_asset_symbol_count"
                ],
                "real_source_sample_count": report[
                    "real_source_sample_count"
                ],
                "scenario_check_count": report["scenario_check_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
