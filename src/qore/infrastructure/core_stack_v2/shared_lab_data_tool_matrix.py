"""Parameterized data-reality tool matrix consuming Architect 1's registry."""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.core_stack_v2.shared_lab_tools import (
    ProbeCase,
    SharedLabToolRegistry,
    ToolFamily,
)


@dataclass(frozen=True, slots=True)
class DataToolMatrix:
    timestamp_cases: tuple[ProbeCase, ...]
    sensor_cases: tuple[ProbeCase, ...]
    provider_cases: tuple[ProbeCase, ...]
    identity_cases: tuple[ProbeCase, ...]

    @property
    def total_cases(self) -> int:
        return (
            len(self.timestamp_cases)
            + len(self.sensor_cases)
            + len(self.provider_cases)
            + len(self.identity_cases)
        )

    @property
    def covered_families(self) -> tuple[ToolFamily, ...]:
        return (
            ToolFamily.TIMESTAMP_PERTURBATION,
            ToolFamily.SENSOR_FAILURE_INJECTOR,
            ToolFamily.PROVIDER_DEGRADATION,
            ToolFamily.IDENTITY_MUTATION,
        )


def build_data_tool_matrix(
    registry: SharedLabToolRegistry,
    *,
    sensors: tuple[str, ...],
    assets: tuple[str, ...],
    regimes: tuple[str, ...],
) -> DataToolMatrix:
    timestamp_cases = registry.expand(
        "timestamp-perturbation",
        {
            "sensor": sensors,
            "asset": assets,
            "offset": ("+1ms", "+10ms", "+1s", "+30s", "+5m", "-1ms"),
            "regime": regimes,
        },
    )
    sensor_cases = registry.expand(
        "sensor-failure-injector",
        {
            "sensor": sensors,
            "missing_pct": (0.1, 0.5, 1.0),
            "duration": ("1s", "30s", "5m"),
            "regime": regimes,
            "asset": assets,
        },
    )
    provider_cases = registry.expand(
        "provider-degradation",
        {
            "provider": ("primary", "secondary"),
            "mode": ("stale", "partial", "delayed", "conflict", "disconnect", "reconnect"),
            "asset": assets,
            "duration": ("1s", "30s", "5m"),
        },
    )
    identity_cases = registry.expand(
        "identity-mutation",
        {
            "asset": assets,
            "mutation": (
                "wrong_alias",
                "wrong_asset_class",
                "ambiguous_alias",
                "changed_mapping",
                "prefix_suffix",
            ),
        },
    )
    return DataToolMatrix(timestamp_cases, sensor_cases, provider_cases, identity_cases)
