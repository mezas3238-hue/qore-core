"""Build the real 177-row GEN-2 observability matrix from frozen source metadata."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.global_observability_matrix import (
    AvailabilityState,
    CalendarMappingState,
    GlobalSensorTemporalMetadata,
    build_global_market_observability_matrix,
)
from qore.infrastructure.core_stack_v2.global_sensor_registry import (
    GlobalPerceptionSensorRegistry,
    GlobalSensorDisposition,
    GlobalSensorGovernanceStage,
    GlobalSensorRecord,
)
from qore.infrastructure.core_stack_v2.global_temporal_comparability import (
    GlobalMarketCalendarRegistry,
)

IDENTITY = "QORE_SHARED_GEN2_GLOBAL_MARKET_OBSERVABILITY_MATRIX_001"
CALENDAR_REGISTRY_VERSION = "QORE_SHARED_GLOBAL_CALENDAR_REGISTRY_GEN2_001"


class Gen2ObservabilityMatrixError(RuntimeError):
    """The real global observability matrix could not be built lawfully."""


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise Gen2ObservabilityMatrixError(
            "matrix timestamp must be timezone-aware"
        )
    return parsed


def _load(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise Gen2ObservabilityMatrixError(
            f"{path} must contain JSON object"
        )
    return cast(dict[str, Any], raw)


def _registry(payload: dict[str, Any]) -> GlobalPerceptionSensorRegistry:
    rows = payload.get("sensors")
    if not isinstance(rows, list):
        raise Gen2ObservabilityMatrixError(
            "global registry sensors missing"
        )
    sensors = tuple(
        GlobalSensorRecord(
            instrument_key=cast(str, row["instrument_key"]),
            provider=cast(str, row["provider"]),
            provider_symbol=cast(str, row["provider_symbol"]),
            provider_symbol_id=cast(int, row["provider_symbol_id"]),
            family=cast(str | None, row["family"]),
            observed_at=_aware(cast(str, row["observed_at"])),
            evidence_cutoff_at=_aware(
                cast(str, row["evidence_cutoff_at"])
            ),
            completed_stages=tuple(
                GlobalSensorGovernanceStage(item)
                for item in cast(list[str], row["completed_stages"])
            ),
            disposition=GlobalSensorDisposition(
                cast(str, row["disposition"])
            ),
            uncertainty_bps=cast(int, row["uncertainty_bps"]),
            provenance_refs=tuple(
                cast(list[str], row["provenance_refs"])
            ),
            reason_codes=tuple(cast(list[str], row["reason_codes"])),
            execution_authority=cast(
                bool,
                row["execution_authority"],
            ),
            risk_authority=cast(bool, row["risk_authority"]),
            sizing_authority=cast(bool, row["sizing_authority"]),
            strategy_mutation_authority=cast(
                bool,
                row["strategy_mutation_authority"],
            ),
        )
        for row in rows
    )
    return GlobalPerceptionSensorRegistry(
        as_of=_aware(cast(str, payload["catalog_frozen_at"])),
        provider_catalog_sha256=cast(
            str,
            payload["provider_catalog_sha256"],
        ),
        sensors=sensors,
    )


def run(
    *,
    registry_path: Path,
    provider_schedule_path: Path,
    output_path: Path,
    calendar_output_path: Path,
) -> dict[str, object]:
    registry_payload = _load(registry_path)
    provider_payload = _load(provider_schedule_path)
    if provider_payload.get("source_registry_fingerprint") != (
        registry_payload.get("sensor_registry_fingerprint_sha256")
    ):
        raise Gen2ObservabilityMatrixError(
            "provider schedule source registry drift"
        )
    schedule_rows = provider_payload.get("symbols")
    if not isinstance(schedule_rows, list):
        raise Gen2ObservabilityMatrixError(
            "provider schedule symbol rows missing"
        )
    by_key = {
        cast(str, item["instrument_key"]): item
        for item in schedule_rows
    }
    sensor_rows = cast(list[dict[str, object]], registry_payload["sensors"])
    if set(by_key) != {
        cast(str, item["instrument_key"])
        for item in sensor_rows
    }:
        raise Gen2ObservabilityMatrixError(
            "provider schedule coverage does not match GEN-1 registry"
        )

    calendar_registry = GlobalMarketCalendarRegistry(
        version=CALENDAR_REGISTRY_VERSION,
        calendars=(),
        bindings=(),
        provenance_refs=(
            "gen2:canonical-calendar-mapping-not-yet-authorized",
        ),
    )
    calendar_fingerprint = calendar_registry.fingerprint()
    calendar_report = {
        "identity": CALENDAR_REGISTRY_VERSION,
        "status": "SOURCE_ONLY_UNMAPPED",
        "calendar_count": 0,
        "binding_count": 0,
        "calendar_registry_fingerprint_sha256": calendar_fingerprint,
        "provider_schedule_is_not_canonical_market_calendar": True,
        "canonical_mapping_governance_status": (
            "IMPLEMENTED_NOT_POPULATED"
        ),
        "canonical_mapping_verified_count": 0,
    }
    calendar_output_path.parent.mkdir(parents=True, exist_ok=True)
    calendar_output_path.write_text(
        json.dumps(calendar_report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    metadata = tuple(
        GlobalSensorTemporalMetadata(
            instrument_key=key,
            canonical_instrument_id=None,
            family=None,
            calendar_mapping=CalendarMappingState.UNMAPPED,
            calendar_id=None,
            calendar_version=None,
            iana_timezone=None,
            provider_schedule_available=(
                len(cast(list[object], item["schedule_intervals"])) > 0
            ),
            provider_schedule_timezone=cast(
                str | None,
                item["schedule_timezone"],
            ),
            historical_availability=AvailabilityState.UNKNOWN,
            realtime_availability=AvailabilityState.UNKNOWN,
            expected_cadence_capability=False,
            liquidity_observability=False,
            comparability_ready=False,
            provenance_refs=(
                "provider-schedule:"
                + cast(
                    str,
                    provider_payload[
                        "provider_schedule_catalog_fingerprint_sha256"
                    ],
                ),
            ),
        )
        for key, item in sorted(by_key.items())
    )
    registry = _registry(registry_payload)
    matrix = build_global_market_observability_matrix(
        registry=registry,
        sensor_registry_fingerprint=cast(
            str,
            registry_payload["sensor_registry_fingerprint_sha256"],
        ),
        metadata=metadata,
        as_of=_aware(cast(str, provider_payload["captured_at"])),
    )
    rows = [
        {
            "instrument_key": item.instrument_key,
            "provider": item.provider,
            "provider_symbol": item.provider_symbol,
            "provider_symbol_id": item.provider_symbol_id,
            "family": item.family,
            "canonical_instrument_id": item.canonical_instrument_id,
            "calendar_mapping": item.calendar_mapping.value,
            "calendar_id": item.calendar_id,
            "calendar_version": item.calendar_version,
            "iana_timezone": item.iana_timezone,
            "provider_schedule_available": (
                item.provider_schedule_available
            ),
            "provider_schedule_timezone": (
                item.provider_schedule_timezone
            ),
            "historical_availability": (
                item.historical_availability.value
            ),
            "realtime_availability": (
                item.realtime_availability.value
            ),
            "expected_cadence_capability": (
                item.expected_cadence_capability
            ),
            "liquidity_observability": item.liquidity_observability,
            "readiness": item.readiness.value,
            "scientific_disposition": (
                item.scientific_disposition.value
            ),
            "provenance_refs": list(item.provenance_refs),
        }
        for item in matrix.rows
    ]
    readiness_counts: dict[str, int] = {}
    for item in rows:
        readiness = cast(str, item["readiness"])
        readiness_counts[readiness] = readiness_counts.get(readiness, 0) + 1

    report: dict[str, object] = {
        "identity": IDENTITY,
        "status": "GEN2_SOURCE_CENSUS_NOT_RELATIONAL_ADMISSION",
        "as_of": matrix.as_of.isoformat(timespec="microseconds"),
        "sensor_count": len(rows),
        "sensor_registry_fingerprint_sha256": (
            matrix.sensor_registry_fingerprint
        ),
        "provider_schedule_catalog_fingerprint_sha256": provider_payload[
            "provider_schedule_catalog_fingerprint_sha256"
        ],
        "calendar_registry_fingerprint_sha256": calendar_fingerprint,
        "global_observability_matrix_fingerprint_sha256": (
            matrix.fingerprint()
        ),
        "readiness_counts": dict(sorted(readiness_counts.items())),
        "canonical_calendar_mapping_complete": False,
        "canonical_mapping_governance_status": (
            "IMPLEMENTED_NOT_POPULATED"
        ),
        "canonical_mapping_verified_count": 0,
        "cadence_policy_registry_architecture_status": (
            "IMPLEMENTED_NOT_FROZEN"
        ),
        "liquidity_policy_architecture_status": (
            "IMPLEMENTED_NOT_FROZEN"
        ),
        "temporal_skew_policy_registry_architecture_status": (
            "IMPLEMENTED_NOT_FROZEN"
        ),
        "comparability_policy_registry_architecture_status": (
            "IMPLEMENTED_NOT_FROZEN"
        ),
        "comparability_policy_registry_status": "NOT_FROZEN",
        "relational_claims_authorized": False,
        "automatic_sensor_admission": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "scientific_v15_opened": False,
        "execution_authority": False,
        "risk_authority": False,
        "sizing_authority": False,
        "strategy_mutation_authority": False,
        "rows": rows,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--provider-schedule", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--calendar-output", type=Path, required=True)
    args = parser.parse_args()
    report = run(
        registry_path=args.registry,
        provider_schedule_path=args.provider_schedule,
        output_path=args.output,
        calendar_output_path=args.calendar_output,
    )
    print(
        json.dumps(
            {
                "identity": report["identity"],
                "sensor_count": report["sensor_count"],
                "readiness_counts": report["readiness_counts"],
                "calendar_registry_fingerprint_sha256": report[
                    "calendar_registry_fingerprint_sha256"
                ],
                "global_observability_matrix_fingerprint_sha256": report[
                    "global_observability_matrix_fingerprint_sha256"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
