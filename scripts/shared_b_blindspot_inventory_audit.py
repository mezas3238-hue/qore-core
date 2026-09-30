"""Audit declared-scope blindspot inventory completeness for Architect B."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.shared_b_sensor_blindspot_engine import (
    SharedBBlindspotKind,
    SharedBObservationRequirement,
    SharedBSensorCoverageFact,
    detect_sensor_blindspots,
)

IDENTITY = "SHARED_B_BLINDSPOT_DECLARED_SCOPE_INVENTORY_001"


class SharedBBlindspotInventoryAuditError(ValueError):
    """Declared-scope blindspot inventory audit failed closed."""


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SharedBBlindspotInventoryAuditError(
            f"{path} must contain a JSON object"
        )
    return cast(dict[str, Any], payload)


def _parse_aware(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise SharedBBlindspotInventoryAuditError(f"{field} missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SharedBBlindspotInventoryAuditError(
            f"{field} must be ISO timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SharedBBlindspotInventoryAuditError(
            f"{field} must be timezone-aware"
        )
    return parsed.astimezone(UTC)


def run(
    *,
    registry_path: Path,
    provider_schedule_path: Path,
    agriculture_matrix_path: Path,
    output_path: Path,
) -> dict[str, object]:
    registry = _load(registry_path)
    schedule = _load(provider_schedule_path)
    agriculture = _load(agriculture_matrix_path)

    if registry.get("identity") != "QORE_SHARED_GLOBAL_SENSOR_REGISTRY_001":
        raise SharedBBlindspotInventoryAuditError(
            "unexpected global sensor registry identity"
        )
    if schedule.get("identity") != (
        "QORE_SHARED_GEN2_CTRADER_PROVIDER_SCHEDULE_CATALOG_001"
    ):
        raise SharedBBlindspotInventoryAuditError(
            "unexpected provider schedule identity"
        )
    if agriculture.get("identity") != (
        "QORE_SHARED_GLOBAL_AGRICULTURAL_SENSOR_MATRIX_001"
    ):
        raise SharedBBlindspotInventoryAuditError(
            "unexpected agricultural matrix identity"
        )

    sensors = registry.get("sensors")
    symbols = schedule.get("symbols")
    agri_rows = agriculture.get("rows")
    if not isinstance(sensors, list) or len(sensors) != 177:
        raise SharedBBlindspotInventoryAuditError(
            "expected exact 177 registry sensors"
        )
    if not isinstance(symbols, list) or len(symbols) != 177:
        raise SharedBBlindspotInventoryAuditError(
            "expected exact 177 provider schedule symbols"
        )
    if not isinstance(agri_rows, list) or len(agri_rows) != 16:
        raise SharedBBlindspotInventoryAuditError(
            "expected exact 16 agricultural conceptual rows"
        )

    registry_by_key: dict[tuple[str, int, str], dict[str, object]] = {}
    for item_any in sensors:
        if not isinstance(item_any, dict):
            raise SharedBBlindspotInventoryAuditError(
                "registry sensor row invalid"
            )
        item = cast(dict[str, object], item_any)
        provider = item.get("provider")
        symbol_id = item.get("provider_symbol_id")
        symbol = item.get("provider_symbol")
        if (
            not isinstance(provider, str)
            or type(symbol_id) is not int
            or not isinstance(symbol, str)
        ):
            raise SharedBBlindspotInventoryAuditError(
                "registry provider identity invalid"
            )
        key = (provider, symbol_id, symbol)
        if key in registry_by_key:
            raise SharedBBlindspotInventoryAuditError(
                "duplicate registry provider identity"
            )
        registry_by_key[key] = item

    schedule_by_key: dict[tuple[str, int, str], dict[str, object]] = {}
    for item_any in symbols:
        if not isinstance(item_any, dict):
            raise SharedBBlindspotInventoryAuditError(
                "provider schedule row invalid"
            )
        item = cast(dict[str, object], item_any)
        provider = item.get("provider")
        symbol_id = item.get("provider_symbol_id")
        symbol = item.get("provider_symbol")
        if (
            not isinstance(provider, str)
            or type(symbol_id) is not int
            or not isinstance(symbol, str)
        ):
            raise SharedBBlindspotInventoryAuditError(
                "schedule provider identity invalid"
            )
        key = (provider, symbol_id, symbol)
        if key in schedule_by_key:
            raise SharedBBlindspotInventoryAuditError(
                "duplicate schedule provider identity"
            )
        schedule_by_key[key] = item

    if set(registry_by_key) != set(schedule_by_key):
        raise SharedBBlindspotInventoryAuditError(
            "registry/provider schedule populations differ"
        )

    as_of = max(
        _parse_aware(registry.get("catalog_frozen_at"), field="catalog_frozen_at"),
        _parse_aware(schedule.get("captured_at"), field="captured_at"),
        _parse_aware(agriculture.get("as_of"), field="agriculture.as_of"),
    )

    requirements: list[SharedBObservationRequirement] = []
    coverage: list[SharedBSensorCoverageFact] = []
    provider_inventory: list[dict[str, object]] = []

    for provider, symbol_id, symbol in sorted(registry_by_key):
        registry_row = registry_by_key[(provider, symbol_id, symbol)]
        schedule_row = schedule_by_key[(provider, symbol_id, symbol)]
        instrument_key = registry_row.get("instrument_key")
        if not isinstance(instrument_key, str) or not instrument_key:
            raise SharedBBlindspotInventoryAuditError(
                "registry instrument_key missing"
            )
        family = f"PROVIDER_SENSOR::{symbol_id}"
        horizon = "CATALOG_SNAPSHOT"
        requirement_id = f"B19_PROVIDER_SENSOR_{symbol_id:05d}"
        requirements.append(
            SharedBObservationRequirement(
                requirement_id=requirement_id,
                sensor_family=family,
                horizon=horizon,
                identity_required=True,
                market_hours_required=True,
                data_health_required=True,
                relation_comparability_required=True,
                provenance_refs=(
                    f"registry:{registry['sensor_registry_fingerprint_sha256']}",
                ),
            )
        )
        coverage.append(
            SharedBSensorCoverageFact(
                sensor_family=family,
                horizon=horizon,
                observed_at=as_of,
                evidence_cutoff_at=as_of,
                sensor_ids=(instrument_key,),
                provider_available=True,
                identity_resolved=False,
                market_hours_resolved=False,
                data_health_observed=False,
                relation_comparability_known=False,
                provenance_refs=(
                    f"provider-schedule:{schedule['provider_schedule_catalog_fingerprint_sha256']}",
                ),
            )
        )
        provider_inventory.append(
            {
                "instrument_key": instrument_key,
                "provider": provider,
                "provider_symbol_id": symbol_id,
                "provider_symbol": symbol,
                "provider_asset_class_name": schedule_row.get(
                    "provider_asset_class_name"
                ),
                "provider_schedule_present": True,
                "provider_available": True,
                "canonical_identity_resolved": False,
                "canonical_market_hours_resolved": False,
                "sensor_specific_data_health_proven": False,
                "relation_comparability_known": False,
                "scientific_admission": False,
            }
        )

    agricultural_requirements: list[dict[str, object]] = []
    for row_any in sorted(
        agri_rows,
        key=lambda item: str(item.get("conceptual_market_key", ""))
        if isinstance(item, dict)
        else "",
    ):
        if not isinstance(row_any, dict):
            raise SharedBBlindspotInventoryAuditError(
                "agricultural row invalid"
            )
        row = cast(dict[str, object], row_any)
        conceptual_key = row.get("conceptual_market_key")
        state = row.get("discovery_state")
        candidates = row.get("provider_candidates")
        if not isinstance(conceptual_key, str) or not conceptual_key:
            raise SharedBBlindspotInventoryAuditError(
                "agricultural conceptual key missing"
            )
        if state != "ABSENT_FROM_CURRENT_CATALOG_EVIDENCE":
            raise SharedBBlindspotInventoryAuditError(
                "agricultural discovery state drift"
            )
        if candidates != []:
            raise SharedBBlindspotInventoryAuditError(
                "agricultural provider candidates unexpectedly appeared"
            )
        requirement_id = f"B19_AGRI_{conceptual_key}"
        family = f"AGRICULTURE::{conceptual_key}"
        requirements.append(
            SharedBObservationRequirement(
                requirement_id=requirement_id,
                sensor_family=family,
                horizon="PROVIDER_DISCOVERY",
                identity_required=True,
                market_hours_required=True,
                data_health_required=True,
                relation_comparability_required=True,
                provenance_refs=(
                    f"agriculture:{agriculture['matrix_fingerprint_sha256']}",
                ),
            )
        )
        agricultural_requirements.append(
            {
                "requirement_id": requirement_id,
                "conceptual_market_key": conceptual_key,
                "world_family": row.get("world_family"),
                "provider_candidate_count": 0,
                "known_missing_from_current_provider": True,
            }
        )

    requirements_tuple = tuple(
        sorted(requirements, key=lambda item: item.requirement_id)
    )
    coverage_tuple = tuple(
        sorted(
            coverage,
            key=lambda item: (item.sensor_family, item.horizon),
        )
    )
    report = detect_sensor_blindspots(
        requirements=requirements_tuple,
        coverage=coverage_tuple,
        as_of=as_of,
        coverage_inventory_complete=True,
        open_world_boundary=True,
    )

    kind_counts: dict[str, int] = {}
    known_missing_count = 0
    for blindspot in report.blindspots:
        kind_counts[blindspot.kind.value] = (
            kind_counts.get(blindspot.kind.value, 0) + 1
        )
        if blindspot.known_missing:
            known_missing_count += 1

    if kind_counts.get(
        SharedBBlindspotKind.COVERAGE_INVENTORY_INCOMPLETE.value,
        0,
    ):
        raise SharedBBlindspotInventoryAuditError(
            "declared scope remained inventory-incomplete"
        )
    if kind_counts.get(SharedBBlindspotKind.OPEN_WORLD_BOUNDARY.value) != 1:
        raise SharedBBlindspotInventoryAuditError(
            "open-world boundary must be represented exactly once"
        )
    if kind_counts.get(SharedBBlindspotKind.SENSOR_FAMILY_ABSENT.value) != 16:
        raise SharedBBlindspotInventoryAuditError(
            "agricultural known-missing count drift"
        )

    payload: dict[str, object] = {
        "identity": IDENTITY,
        "status": "DECLARED_SCOPE_INVENTORY_COMPLETE_OPEN_WORLD_PRESERVED",
        "as_of": as_of.isoformat(timespec="microseconds"),
        "provider_sensor_inventory_count": len(provider_inventory),
        "agricultural_requirement_count": len(agricultural_requirements),
        "declared_requirement_count": len(requirements_tuple),
        "declared_coverage_fact_count": len(coverage_tuple),
        "coverage_inventory_complete": report.coverage_inventory_complete,
        "open_world_boundary": report.open_world_boundary,
        "second_order_blindspot_possible": (
            report.second_order_blindspot_possible
        ),
        "known_missing_blindspot_count": known_missing_count,
        "blindspot_kind_counts": dict(sorted(kind_counts.items())),
        "provider_inventory": provider_inventory,
        "agricultural_requirements": agricultural_requirements,
        "current_provider_universe_defines_world_ceiling": False,
        "all_unknown_unknowns_eliminated": False,
        "sensor_admission_authority": False,
        "relation_authority": False,
        "productive_authority": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "broker_mutation": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--provider-schedule", type=Path, required=True)
    parser.add_argument("--agriculture-matrix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run(
        registry_path=args.registry,
        provider_schedule_path=args.provider_schedule,
        agriculture_matrix_path=args.agriculture_matrix,
        output_path=args.output,
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "provider_sensor_inventory_count": payload[
                    "provider_sensor_inventory_count"
                ],
                "agricultural_requirement_count": payload[
                    "agricultural_requirement_count"
                ],
                "coverage_inventory_complete": payload[
                    "coverage_inventory_complete"
                ],
                "open_world_boundary": payload["open_world_boundary"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
