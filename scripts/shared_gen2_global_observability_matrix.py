"""Build the real 177-row GEN-2 observability matrix from frozen source metadata."""

from __future__ import annotations

import argparse
import hashlib
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
    CanonicalCalendarMappingRecord,
    CanonicalCalendarMappingRegistry,
    CanonicalCalendarMappingStatus,
    GlobalMarketCalendarRegistry,
)

IDENTITY = "QORE_SHARED_GEN2_GLOBAL_MARKET_OBSERVABILITY_MATRIX_001"
CALENDAR_REGISTRY_VERSION = "QORE_SHARED_GLOBAL_CALENDAR_REGISTRY_GEN2_001"
CANONICAL_MAPPING_REGISTRY_VERSION = (
    "QORE_SHARED_CANONICAL_CALENDAR_MAPPING_REGISTRY_GEN2_001"
)


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
    mapping_output_path: Path,
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

    schedule_fingerprint = cast(
        str,
        provider_payload["provider_schedule_catalog_fingerprint_sha256"],
    )
    sensor_by_key = {
        cast(str, item["instrument_key"]): item
        for item in sensor_rows
    }
    unresolved_records = tuple(
        CanonicalCalendarMappingRecord(
            instrument_key=key,
            provider=cast(str, sensor_by_key[key]["provider"]),
            provider_symbol=cast(str, sensor_by_key[key]["provider_symbol"]),
            provider_symbol_id=cast(int, sensor_by_key[key]["provider_symbol_id"]),
            status=CanonicalCalendarMappingStatus.UNRESOLVED,
            canonical_instrument_id=None,
            venue=None,
            calendar_id=None,
            calendar_version=None,
            iana_timezone=None,
            provider_schedule_timezone=cast(
                str | None,
                by_key[key]["schedule_timezone"],
            ),
            timezone_mapping_version=None,
            identity_evidence_refs=(),
            venue_evidence_refs=(),
            calendar_evidence_refs=(),
            provider_schedule_evidence_refs=(
                "provider-schedule:" + schedule_fingerprint,
            ),
            reason_codes=(
                "CANONICAL_CALENDAR_EVIDENCE_REQUIRED",
                "CANONICAL_IDENTITY_EVIDENCE_REQUIRED",
                "CANONICAL_VENUE_EVIDENCE_REQUIRED",
            ),
        )
        for key in sorted(by_key)
    )
    mapping_registry = CanonicalCalendarMappingRegistry(
        version=CANONICAL_MAPPING_REGISTRY_VERSION,
        records=unresolved_records,
        provenance_refs=tuple(
            sorted(
                (
                    "provider-schedule:" + schedule_fingerprint,
                    "sensor-registry:"
                    + cast(
                        str,
                        registry_payload[
                            "sensor_registry_fingerprint_sha256"
                        ],
                    ),
                )
            )
        ),
    )
    asset_classes = {
        int(item["asset_class_id"]): cast(str, item["name"])
        for item in cast(
            list[dict[str, object]],
            provider_payload.get("provider_asset_classes", []),
        )
    }
    categories = {
        int(item["symbol_category_id"]): cast(
            dict[str, object],
            item,
        )
        for item in cast(
            list[dict[str, object]],
            provider_payload.get("provider_symbol_categories", []),
        )
    }
    worklist_rows: list[dict[str, object]] = []
    asset_class_counts: dict[str, int] = {}
    schedule_timezone_counts: dict[str, int] = {}
    for record in mapping_registry.records:
        provider_row = by_key[record.instrument_key]
        category_id = provider_row.get("provider_symbol_category_id")
        if type(category_id) is not int or category_id not in categories:
            raise Gen2ObservabilityMatrixError(
                "provider mapping worklist category evidence missing"
            )
        category = categories[category_id]
        asset_class_id = category.get("asset_class_id")
        if type(asset_class_id) is not int or asset_class_id not in asset_classes:
            raise Gen2ObservabilityMatrixError(
                "provider mapping worklist asset-class evidence missing"
            )
        asset_class_name = asset_classes[asset_class_id]
        schedule_timezone = provider_row.get("schedule_timezone")
        schedule_timezone_key = (
            schedule_timezone
            if isinstance(schedule_timezone, str) and schedule_timezone
            else "UNKNOWN"
        )
        asset_class_counts[asset_class_name] = (
            asset_class_counts.get(asset_class_name, 0) + 1
        )
        schedule_timezone_counts[schedule_timezone_key] = (
            schedule_timezone_counts.get(schedule_timezone_key, 0) + 1
        )
        worklist_rows.append(
            {
                "instrument_key": record.instrument_key,
                "provider": record.provider,
                "provider_symbol": record.provider_symbol,
                "provider_symbol_id": record.provider_symbol_id,
                "provider_native_symbol_name": provider_row.get(
                    "provider_native_symbol_name"
                ),
                "provider_description": provider_row.get(
                    "provider_description"
                ),
                "provider_base_asset_id": provider_row.get(
                    "provider_base_asset_id"
                ),
                "provider_quote_asset_id": provider_row.get(
                    "provider_quote_asset_id"
                ),
                "provider_symbol_category_id": category_id,
                "provider_asset_class_id": asset_class_id,
                "provider_asset_class_name": asset_class_name,
                "provider_schedule_timezone": schedule_timezone,
                "current_mapping_status": record.status.value,
                "required_canonical_evidence": (
                    "CANONICAL_INSTRUMENT_IDENTITY",
                    "CANONICAL_MARKET_OR_VENUE",
                    "CANONICAL_VERSIONED_CALENDAR",
                ),
                "provider_metadata_is_supporting_only": True,
            }
        )
    worklist_payload = {
        "rows": worklist_rows,
        "asset_class_counts": dict(sorted(asset_class_counts.items())),
        "schedule_timezone_counts": dict(
            sorted(schedule_timezone_counts.items())
        ),
    }
    worklist_raw = json.dumps(
        worklist_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    worklist_fingerprint = hashlib.sha256(
        worklist_raw.encode("utf-8")
    ).hexdigest()

    mapping_report = {
        "identity": CANONICAL_MAPPING_REGISTRY_VERSION,
        "status": "UNRESOLVED_BASELINE_FROZEN",
        "record_count": len(mapping_registry.records),
        "verified_count": 0,
        "ambiguous_count": 0,
        "rejected_count": 0,
        "unresolved_count": len(mapping_registry.records),
        "canonical_mapping_registry_fingerprint_sha256": (
            mapping_registry.fingerprint()
        ),
        "automatic_identity_inference": False,
        "provider_schedule_is_not_canonical_identity_evidence": True,
        "provider_evidence_worklist_is_not_canonical_mapping": True,
        "provider_evidence_worklist_count": len(worklist_rows),
        "provider_evidence_worklist_fingerprint_sha256": worklist_fingerprint,
        "provider_evidence_worklist_asset_class_counts": dict(
            sorted(asset_class_counts.items())
        ),
        "provider_evidence_worklist_schedule_timezone_counts": dict(
            sorted(schedule_timezone_counts.items())
        ),
        "provider_evidence_worklist": worklist_rows,
        "records": [
            {
                "instrument_key": item.instrument_key,
                "provider": item.provider,
                "provider_symbol": item.provider_symbol,
                "provider_symbol_id": item.provider_symbol_id,
                "status": item.status.value,
                "canonical_instrument_id": item.canonical_instrument_id,
                "venue": item.venue,
                "calendar_id": item.calendar_id,
                "calendar_version": item.calendar_version,
                "iana_timezone": item.iana_timezone,
                "provider_schedule_timezone": (
                    item.provider_schedule_timezone
                ),
                "timezone_mapping_version": item.timezone_mapping_version,
                "identity_evidence_refs": list(
                    item.identity_evidence_refs
                ),
                "venue_evidence_refs": list(item.venue_evidence_refs),
                "calendar_evidence_refs": list(
                    item.calendar_evidence_refs
                ),
                "provider_schedule_evidence_refs": list(
                    item.provider_schedule_evidence_refs
                ),
                "reason_codes": list(item.reason_codes),
                "mapping_fingerprint_sha256": item.fingerprint(),
            }
            for item in mapping_registry.records
        ],
    }
    mapping_output_path.parent.mkdir(parents=True, exist_ok=True)
    mapping_output_path.write_text(
        json.dumps(mapping_report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    calendar_registry = GlobalMarketCalendarRegistry(
        version=CALENDAR_REGISTRY_VERSION,
        calendars=(),
        bindings=(),
        provenance_refs=(
            "canonical-mapping-registry:" + mapping_registry.fingerprint(),
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
            "UNRESOLVED_BASELINE_FROZEN"
        ),
        "canonical_mapping_registry_fingerprint_sha256": (
            mapping_registry.fingerprint()
        ),
        "canonical_mapping_record_count": len(mapping_registry.records),
        "canonical_mapping_verified_count": 0,
        "canonical_mapping_unresolved_count": len(mapping_registry.records),
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
                "canonical-mapping-registry:"
                + mapping_registry.fingerprint(),
                "provider-schedule:" + schedule_fingerprint,
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
            "UNRESOLVED_BASELINE_FROZEN"
        ),
        "canonical_mapping_registry_fingerprint_sha256": (
            mapping_registry.fingerprint()
        ),
        "canonical_mapping_record_count": len(mapping_registry.records),
        "canonical_mapping_verified_count": 0,
        "canonical_mapping_unresolved_count": len(mapping_registry.records),
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
    parser.add_argument("--mapping-output", type=Path, required=True)
    args = parser.parse_args()
    report = run(
        registry_path=args.registry,
        provider_schedule_path=args.provider_schedule,
        output_path=args.output,
        calendar_output_path=args.calendar_output,
        mapping_output_path=args.mapping_output,
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
                "canonical_mapping_registry_fingerprint_sha256": report[
                    "canonical_mapping_registry_fingerprint_sha256"
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
