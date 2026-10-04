"""Parameterized sensor/provider fault harness for Shared Lab data reality."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_lab_data_reality import ProviderDatum, classify_resilience
from qore.infrastructure.core_stack_v2.shared_lab_tools import SharedLabToolRegistry


class SensorFault(StrEnum):
    MISSING = "MISSING"
    DUPLICATED = "DUPLICATED"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    STALE = "STALE"
    FUTURE_TIMESTAMP = "FUTURE_TIMESTAMP"
    MALFORMED_VALUE = "MALFORMED_VALUE"
    WRONG_ASSET_CLASS = "WRONG_ASSET_CLASS"
    DISCONNECTED_PROVIDER = "DISCONNECTED_PROVIDER"
    DELAYED = "DELAYED"
    INTERMITTENT = "INTERMITTENT"
    PARTIAL_HISTORY = "PARTIAL_HISTORY"
    RECONNECT_GAP = "RECONNECT_GAP"
    SPREAD_ANOMALY = "SPREAD_ANOMALY"
    TIMESTAMP_DRIFT = "TIMESTAMP_DRIFT"
    SENSOR_STARVATION = "SENSOR_STARVATION"
    ALIAS_COLLISION = "ALIAS_COLLISION"


@dataclass(frozen=True, slots=True)
class SensorProbeReceipt:
    sensor_id: str
    fault: SensorFault
    input_count: int
    output_count: int
    detected: bool
    failure_classifications: tuple[str, ...]
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.productive_authority:
            raise ValueError("sensor laboratory grants no productive authority")


def inject_fault(data: tuple[ProviderDatum, ...], fault: SensorFault, amount_ns: int = 1_000_000) -> tuple[ProviderDatum, ...]:
    if not data:
        return data
    items = list(data)
    if fault is SensorFault.MISSING:
        return tuple(items[1:])
    if fault is SensorFault.DUPLICATED:
        return tuple([items[0], *items])
    if fault is SensorFault.OUT_OF_ORDER and len(items) > 1:
        items[0], items[1] = items[1], items[0]
        return tuple(items)
    if fault is SensorFault.STALE:
        return tuple(replace(x, available_at_ns=x.available_at_ns - amount_ns) for x in items)
    if fault is SensorFault.FUTURE_TIMESTAMP:
        return tuple(replace(x, available_at_ns=x.observed_at_ns + amount_ns) for x in items)
    if fault is SensorFault.MALFORMED_VALUE:
        items[0] = replace(items[0], bid=-1.0)
        return tuple(items)
    if fault is SensorFault.WRONG_ASSET_CLASS:
        items[0] = replace(items[0], metadata_asset_class="WRONG")
        return tuple(items)
    if fault is SensorFault.DISCONNECTED_PROVIDER:
        return ()
    if fault is SensorFault.DELAYED:
        return tuple(replace(x, available_at_ns=x.available_at_ns + amount_ns) for x in items)
    if fault is SensorFault.INTERMITTENT:
        return tuple(item for index, item in enumerate(items) if index % 2 == 0)
    if fault is SensorFault.PARTIAL_HISTORY:
        return tuple(items[: max(1, len(items) // 2)])
    if fault is SensorFault.RECONNECT_GAP:
        if len(items) > 1:
            items[1] = replace(items[1], sequence=items[0].sequence + 2)
        return tuple(items)
    if fault is SensorFault.SPREAD_ANOMALY:
        items[0] = replace(items[0], ask=(items[0].bid or 1.0) * 10.0)
        return tuple(items)
    if fault is SensorFault.TIMESTAMP_DRIFT:
        return tuple(replace(x, observed_at_ns=x.observed_at_ns + amount_ns) for x in items)
    if fault is SensorFault.SENSOR_STARVATION:
        return ()
    if fault is SensorFault.ALIAS_COLLISION:
        items[0] = replace(items[0], provider_symbol="AMBIGUOUS_ALIAS")
        return tuple(items)
    return tuple(items)


def expand_required_fault_cases(registry: SharedLabToolRegistry, *, sensors: tuple[str, ...], assets: tuple[str, ...], regimes: tuple[str, ...]) -> int:
    sensor_cases = registry.expand(
        "sensor-failure-injector",
        {"sensor": sensors, "missing_pct": (0.1, 0.5, 1.0), "duration": ("1s", "30s", "5m"), "regime": regimes, "asset": assets},
    )
    provider_cases = registry.expand(
        "provider-degradation",
        {"provider": ("primary", "secondary"), "mode": ("stale", "partial", "delayed", "conflict"), "asset": assets, "duration": ("1s", "30s")},
    )
    return len(sensor_cases) + len(provider_cases)


def degradation_classification(required: int, available: int, alternatives: int, observability: float) -> str:
    return classify_resilience(required, available, alternatives, observability).value
