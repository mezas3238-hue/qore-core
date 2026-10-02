"""Materialize the canonical Shared global sensor registry from a frozen provider catalogue."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.core_stack_v2.global_sensor_registry import (
    ProviderCatalogSensor,
    build_discovered_provider_registry,
)

IDENTITY = "QORE_SHARED_GLOBAL_SENSOR_REGISTRY_001"
EXPECTED_CATALOG_IDENTITY = (
    "QORE_SHARED_WP05_POST_V14_PROVIDER_CATALOG_AUDIT_001"
)


class GlobalSensorRegistryBuildError(RuntimeError):
    """The frozen provider catalogue could not form a lawful discovery registry."""


def _load_catalog(
    path: Path,
    *,
    expected_catalog_sha256: str,
) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise GlobalSensorRegistryBuildError("provider catalogue must be JSON object")
    payload = cast(dict[str, Any], raw)
    if payload.get("identity") != EXPECTED_CATALOG_IDENTITY:
        raise GlobalSensorRegistryBuildError("unexpected provider catalogue identity")
    if payload.get("provider_catalog_sha256") != expected_catalog_sha256:
        raise GlobalSensorRegistryBuildError("provider catalogue SHA mismatch")
    rows = payload.get("enabled_symbols")
    if not isinstance(rows, list) or not rows:
        raise GlobalSensorRegistryBuildError("provider catalogue has no enabled symbols")
    if payload.get("enabled_symbol_count") != len(rows):
        raise GlobalSensorRegistryBuildError("provider catalogue count drift")
    if payload.get("candidate_selection_performed") is not False:
        raise GlobalSensorRegistryBuildError("provider catalogue selected candidates")
    if payload.get("historical_market_data_read") is not False:
        raise GlobalSensorRegistryBuildError("provider catalogue read market history")
    if payload.get("target_or_outcome_read") is not False:
        raise GlobalSensorRegistryBuildError("provider catalogue read outcomes")
    return payload


def run(
    *,
    catalog_path: Path,
    output_path: Path,
    provider: str,
    expected_catalog_sha256: str,
    catalog_frozen_at: datetime,
    source_run_id: int,
    source_artifact_id: int,
    source_git_sha: str,
) -> dict[str, object]:
    catalog = _load_catalog(
        catalog_path,
        expected_catalog_sha256=expected_catalog_sha256,
    )
    rows = cast(list[dict[str, object]], catalog["enabled_symbols"])
    provider_catalog = tuple(
        ProviderCatalogSensor(
            provider=provider,
            provider_symbol=cast(str, row["provider_symbol"]),
            provider_symbol_id=cast(int, row["provider_symbol_id"]),
        )
        for row in rows
    )
    registry = build_discovered_provider_registry(
        provider=provider,
        catalog_sha256=expected_catalog_sha256,
        observed_at=catalog_frozen_at,
        catalog=provider_catalog,
    )
    sensors = [
        {
            "instrument_key": item.instrument_key,
            "provider": item.provider,
            "provider_symbol": item.provider_symbol,
            "provider_symbol_id": item.provider_symbol_id,
            "family": item.family,
            "observed_at": item.observed_at.isoformat(timespec="microseconds"),
            "evidence_cutoff_at": item.evidence_cutoff_at.isoformat(
                timespec="microseconds"
            ),
            "completed_stages": [stage.value for stage in item.completed_stages],
            "disposition": item.disposition.value,
            "uncertainty_bps": item.uncertainty_bps,
            "provenance_refs": list(item.provenance_refs),
            "reason_codes": list(item.reason_codes),
            "execution_authority": item.execution_authority,
            "risk_authority": item.risk_authority,
            "sizing_authority": item.sizing_authority,
            "strategy_mutation_authority": item.strategy_mutation_authority,
        }
        for item in registry.sensors
    ]
    report: dict[str, object] = {
        "identity": IDENTITY,
        "status": "global_provider_discovery_frozen",
        "provider": provider,
        "source_provider_catalog_run_id": source_run_id,
        "source_provider_catalog_artifact_id": source_artifact_id,
        "source_provider_catalog_git_sha": source_git_sha,
        "provider_catalog_sha256": expected_catalog_sha256,
        "catalog_frozen_at": catalog_frozen_at.isoformat(timespec="microseconds"),
        "sensor_count": registry.sensor_count,
        "sensor_registry_fingerprint_sha256": registry.fingerprint(),
        "disposition_counts": {
            "DISCOVERED": registry.sensor_count,
            "QUALIFYING": 0,
            "OBSERVE_ONLY": 0,
            "ADMITTED": 0,
            "REJECTED": 0,
        },
        "all_sensor_families_unclassified": all(
            item.family is None for item in registry.sensors
        ),
        "provider_discovery_is_not_scientific_admission": True,
        "current_trader_universe_defines_ceiling": False,
        "target_or_outcome_read": False,
        "r6_r5_read": False,
        "fresh_holdout_opened": False,
        "scientific_v15_opened": False,
        "execution_authority": False,
        "risk_authority": False,
        "sizing_authority": False,
        "capital_authority": False,
        "strategy_mutation_authority": False,
        "sensors": sensors,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def _parse_aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("timestamp must be timezone-aware")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--expected-catalog-sha256", required=True)
    parser.add_argument("--catalog-frozen-at", type=_parse_aware_datetime, required=True)
    parser.add_argument("--source-run-id", type=int, required=True)
    parser.add_argument("--source-artifact-id", type=int, required=True)
    parser.add_argument("--source-git-sha", required=True)
    args = parser.parse_args()

    report = run(
        catalog_path=args.catalog,
        output_path=args.output,
        provider=args.provider,
        expected_catalog_sha256=args.expected_catalog_sha256,
        catalog_frozen_at=args.catalog_frozen_at,
        source_run_id=args.source_run_id,
        source_artifact_id=args.source_artifact_id,
        source_git_sha=args.source_git_sha,
    )
    print(
        json.dumps(
            {
                "identity": report["identity"],
                "status": report["status"],
                "sensor_count": report["sensor_count"],
                "sensor_registry_fingerprint_sha256": report[
                    "sensor_registry_fingerprint_sha256"
                ],
                "disposition_counts": report["disposition_counts"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
