"""Provider reality harness for exact lineage and degradation detection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_lab_data_reality import ProviderDatum, provider_disagreement


class ProviderFailure(StrEnum):
    MISSING = "MISSING"
    DELAYED = "DELAYED"
    PARTIAL = "PARTIAL"
    STALE = "STALE"
    CONFLICT = "CONFLICT"
    CORRUPTED_PAYLOAD = "CORRUPTED_PAYLOAD"
    INCOMPLETE_METADATA = "INCOMPLETE_METADATA"
    WRONG_SYMBOL = "WRONG_SYMBOL"
    DUPLICATE_EVENT = "DUPLICATE_EVENT"
    DROPPED_EVENT = "DROPPED_EVENT"
    SEQUENCE_GAP = "SEQUENCE_GAP"


@dataclass(frozen=True, slots=True)
class ProviderRealityReceipt:
    provider: str
    datum_id: str
    raw_sha256: str
    decoder_id: str
    mapping_revision: str
    lineage_exact: bool
    failures: tuple[ProviderFailure, ...]

    @property
    def passed(self) -> bool:
        return self.lineage_exact and not self.failures


def assess_provider(datum: ProviderDatum, *, expected_provider: str, max_latency_ns: int) -> ProviderRealityReceipt:
    failures: list[ProviderFailure] = []
    if datum.provider != expected_provider:
        failures.append(ProviderFailure.MISSING)
    if datum.available_at_ns - datum.observed_at_ns > max_latency_ns:
        failures.append(ProviderFailure.DELAYED)
    if not datum.provider_symbol:
        failures.append(ProviderFailure.WRONG_SYMBOL)
    lineage_exact = datum.provider == datum.provenance.provider and len(datum.provenance.raw_sha256) == 64
    return ProviderRealityReceipt(
        datum.provider, datum.datum_id, datum.provenance.raw_sha256,
        datum.provenance.decoder_id, datum.provenance.mapping_revision,
        lineage_exact, tuple(failures),
    )


def assess_sequence_gap(items: tuple[ProviderDatum, ...]) -> tuple[ProviderFailure, ...]:
    if any(b.sequence != a.sequence + 1 for a, b in zip(items, items[1:])):
        return (ProviderFailure.SEQUENCE_GAP,)
    return ()


def assess_cross_provider(left: ProviderDatum, right: ProviderDatum, tolerance: float) -> tuple[ProviderFailure, ...]:
    return (ProviderFailure.CONFLICT,) if provider_disagreement(left, right, tolerance) else ()
