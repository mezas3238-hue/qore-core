"""Adversarial provider scenario generator for Shared Lab."""

from __future__ import annotations

from dataclasses import replace
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_lab_data_reality import ProviderDatum, ProviderProvenance


class ProviderScenario(StrEnum):
    MISSING = "MISSING"
    DELAYED = "DELAYED"
    PARTIAL = "PARTIAL"
    STALE = "STALE"
    CONFLICT = "CONFLICT"
    CORRUPTED_PAYLOAD = "CORRUPTED_PAYLOAD"
    INCOMPLETE_METADATA = "INCOMPLETE_METADATA"
    WRONG_SYMBOL_METADATA = "WRONG_SYMBOL_METADATA"
    DIFFERENT_DECIMALS = "DIFFERENT_DECIMALS"
    CHANGED_SYMBOL = "CHANGED_SYMBOL"
    CHANGED_MAPPING = "CHANGED_MAPPING"
    DUPLICATE_EVENT = "DUPLICATE_EVENT"
    DROPPED_EVENT = "DROPPED_EVENT"
    RECONNECT_EVENT = "RECONNECT_EVENT"
    SEQUENCE_GAP = "SEQUENCE_GAP"


def apply_provider_scenario(
    data: tuple[ProviderDatum, ...],
    scenario: ProviderScenario,
    *,
    delay_ns: int = 1_000_000_000,
) -> tuple[ProviderDatum, ...]:
    if not data:
        return data
    items = list(data)
    if scenario is ProviderScenario.MISSING:
        return ()
    if scenario is ProviderScenario.DELAYED:
        return tuple(replace(x, available_at_ns=x.available_at_ns + delay_ns) for x in items)
    if scenario is ProviderScenario.PARTIAL:
        return tuple(items[: max(1, len(items) // 2)])
    if scenario is ProviderScenario.STALE:
        return tuple(replace(x, available_at_ns=max(0, x.available_at_ns - delay_ns)) for x in items)
    if scenario is ProviderScenario.CONFLICT:
        items[0] = replace(items[0], bid=(items[0].bid or 1.0) * 1.1)
        return tuple(items)
    if scenario is ProviderScenario.CORRUPTED_PAYLOAD:
        items[0] = replace(items[0], bid=float("nan"))
        return tuple(items)
    if scenario is ProviderScenario.INCOMPLETE_METADATA:
        items[0] = replace(items[0], metadata_asset_class="")
        return tuple(items)
    if scenario is ProviderScenario.WRONG_SYMBOL_METADATA:
        items[0] = replace(items[0], provider_symbol="WRONG")
        return tuple(items)
    if scenario is ProviderScenario.DIFFERENT_DECIMALS:
        items[0] = replace(items[0], bid=round(items[0].bid or 0.0, 2), ask=round(items[0].ask or 0.0, 2))
        return tuple(items)
    if scenario is ProviderScenario.CHANGED_SYMBOL:
        items[0] = replace(items[0], provider_symbol=f"{items[0].provider_symbol}.NEW")
        return tuple(items)
    if scenario is ProviderScenario.CHANGED_MAPPING:
        p = items[0].provenance
        items[0] = replace(items[0], provenance=ProviderProvenance(p.provider, p.source_id, p.raw_sha256, p.decoder_id, "map-mutated"))
        return tuple(items)
    if scenario is ProviderScenario.DUPLICATE_EVENT:
        return tuple([items[0], *items])
    if scenario is ProviderScenario.DROPPED_EVENT:
        return tuple(items[1:])
    if scenario is ProviderScenario.RECONNECT_EVENT:
        if len(items) > 1:
            items[1] = replace(items[1], sequence=items[0].sequence + 2)
        return tuple(items)
    if scenario is ProviderScenario.SEQUENCE_GAP:
        if len(items) > 1:
            items[-1] = replace(items[-1], sequence=items[-2].sequence + 2)
        return tuple(items)
    return tuple(items)
