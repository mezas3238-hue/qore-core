from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.production_configuration import (
    MappingProductionConfigurationSource,
    ProductionConfigurationValidationError,
    ProductionEnvironment,
    ProductionRegion,
    ProductionRuntimeMode,
    load_production_configuration,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 5, 40, tzinfo=UTC)


def _source() -> MappingProductionConfigurationSource:
    return MappingProductionConfigurationSource(
        environment=ProductionEnvironment.PRODUCTION,
        region=ProductionRegion("sa-east-1"),
        runtime_mode=ProductionRuntimeMode.SERVICE,
        values={
            "health.readiness_required": True,
            "runtime.instance_class": "standard",
            "runtime.worker_count": 2,
        },
    )


def test_mapping_source_loads_immutable_ordered_snapshot() -> None:
    result = load_production_configuration(_source(), loaded_at=_NOW)

    assert isinstance(result, Success)
    assert result.value.environment is ProductionEnvironment.PRODUCTION
    assert result.value.region == ProductionRegion("sa-east-1")
    assert tuple(result.value.values) == (
        "health.readiness_required",
        "runtime.instance_class",
        "runtime.worker_count",
    )


def test_snapshot_requires_timezone_aware_loaded_at() -> None:
    result = load_production_configuration(
        _source(),
        loaded_at=datetime(2026, 8, 8, 5, 40),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ProductionConfigurationValidationError)


def test_configuration_rejects_secret_like_keys() -> None:
    with pytest.raises(ProductionConfigurationValidationError):
        MappingProductionConfigurationSource(
            environment=ProductionEnvironment.PRODUCTION,
            region=ProductionRegion("sa-east-1"),
            runtime_mode=ProductionRuntimeMode.SERVICE,
            values={"provider.api_token": "redacted"},
        )


def test_configuration_rejects_sensitive_text_values() -> None:
    with pytest.raises(ProductionConfigurationValidationError):
        MappingProductionConfigurationSource(
            environment=ProductionEnvironment.PRODUCTION,
            region=ProductionRegion("sa-east-1"),
            runtime_mode=ProductionRuntimeMode.SERVICE,
            values={"provider.header": "Bearer must-not-appear"},
        )


def test_configuration_rejects_non_finite_float() -> None:
    with pytest.raises(ProductionConfigurationValidationError):
        MappingProductionConfigurationSource(
            environment=ProductionEnvironment.PRODUCTION,
            region=ProductionRegion("sa-east-1"),
            runtime_mode=ProductionRuntimeMode.SERVICE,
            values={"health.ratio": float("inf")},
        )


def test_region_requires_canonical_lowercase_identifier() -> None:
    with pytest.raises(ProductionConfigurationValidationError):
        ProductionRegion("SA-East-1")


def test_logical_values_are_stable_and_non_sensitive() -> None:
    result = load_production_configuration(_source(), loaded_at=_NOW)

    assert isinstance(result, Success)
    assert result.value.logical_values() == (
        "production",
        ("sa-east-1",),
        "service",
        _NOW.isoformat(),
        (
            ("health.readiness_required", True),
            ("runtime.instance_class", "standard"),
            ("runtime.worker_count", 2),
        ),
    )
