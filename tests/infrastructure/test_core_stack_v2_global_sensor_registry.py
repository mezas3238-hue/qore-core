from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.core_stack_v2.global_sensor_registry import (
    GLOBAL_SENSOR_GOVERNANCE_PIPELINE,
    GlobalSensorDisposition,
    GlobalSensorGovernanceStage,
    GlobalSensorRecord,
    ProviderCatalogSensor,
    build_discovered_provider_registry,
)

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
CATALOG_SHA = "4c10aede99704b937caa772e1ae07257c8e12c3d0644c06ca751b6885b9a363f"


def test_global_sensor_registry_scales_without_trader_allowlist() -> None:
    catalog = tuple(
        ProviderCatalogSensor(
            provider="CTRADER_DEMO",
            provider_symbol=f"MARKET_{index:03d}",
            provider_symbol_id=index + 1,
        )
        for index in range(500)
    )

    registry = build_discovered_provider_registry(
        provider="CTRADER_DEMO",
        catalog_sha256=CATALOG_SHA,
        observed_at=NOW,
        catalog=catalog,
    )

    assert registry.sensor_count == 500
    assert registry.current_trader_universe_defines_ceiling is False
    assert all(
        item.disposition is GlobalSensorDisposition.DISCOVERED
        for item in registry.sensors
    )
    assert registry.execution_authority is False
    assert registry.risk_authority is False


def test_provider_discovery_does_not_auto_admit_sensor() -> None:
    registry = build_discovered_provider_registry(
        provider="CTRADER_DEMO",
        catalog_sha256=CATALOG_SHA,
        observed_at=NOW,
        catalog=(
            ProviderCatalogSensor(
                provider="CTRADER_DEMO",
                provider_symbol="US2000",
                provider_symbol_id=10012,
            ),
        ),
    )

    sensor = registry.sensors[0]
    assert sensor.disposition is GlobalSensorDisposition.DISCOVERED
    assert sensor.family is None
    assert sensor.uncertainty_bps == 10_000
    assert "PROVIDER_DISCOVERED_NOT_ADMITTED" in sensor.reason_codes


def test_admitted_sensor_requires_full_governance_pipeline() -> None:
    with pytest.raises(ValueError, match="full pipeline"):
        GlobalSensorRecord(
            instrument_key="CTRADER_DEMO:US2000:10012",
            provider="CTRADER_DEMO",
            provider_symbol="US2000",
            provider_symbol_id=10012,
            family="indices-benchmarks",
            observed_at=NOW,
            evidence_cutoff_at=NOW,
            completed_stages=(
                GlobalSensorGovernanceStage.DISCOVER_PROVIDER_SYMBOL,
                GlobalSensorGovernanceStage.VERIFY_IDENTITY,
            ),
            disposition=GlobalSensorDisposition.ADMITTED,
            uncertainty_bps=5000,
            provenance_refs=("evidence:1",),
            reason_codes=("TEST",),
        )


def test_sensor_pipeline_matches_owner_order() -> None:
    assert tuple(stage.value for stage in GLOBAL_SENSOR_GOVERNANCE_PIPELINE) == (
        "DISCOVER_PROVIDER_SYMBOL",
        "VERIFY_IDENTITY",
        "VERIFY_HISTORICAL_AVAILABILITY",
        "VERIFY_TIMESTAMP_INTEGRITY",
        "VERIFY_MARKET_DATA_QUALITY",
        "CLASSIFY_SENSOR_FAMILY",
        "MEASURE_REDUNDANCY",
        "MEASURE_INFORMATION_GAIN",
        "CAUSAL_VALIDATION",
        "TEMPORAL_REPLICATION",
        "ADMISSION_DECISION",
    )
