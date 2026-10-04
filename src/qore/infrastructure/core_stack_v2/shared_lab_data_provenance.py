"""Raw provider evidence and exact decode-lineage receipts for Shared Lab."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from qore.infrastructure.core_stack_v2.shared_lab_data_reality import ProviderDatum


@dataclass(frozen=True, slots=True)
class RawProviderEvidence:
    provider: str
    source_id: str
    received_payload: bytes
    received_at_ns: int
    content_type: str
    transport_sequence: int | None = None

    def __post_init__(self) -> None:
        if not self.provider or not self.source_id or not self.content_type:
            raise ValueError("raw provider evidence metadata is required")
        if self.received_at_ns < 0:
            raise ValueError("received_at_ns cannot be negative")
        if not self.received_payload:
            raise ValueError("received payload cannot be empty")

    @property
    def raw_sha256(self) -> str:
        return hashlib.sha256(self.received_payload).hexdigest()


@dataclass(frozen=True, slots=True)
class DecodeLineageReceipt:
    provider: str
    source_id: str
    raw_sha256: str
    decoder_id: str
    mapping_revision: str
    datum_id: str
    provider_match: bool
    raw_fingerprint_match: bool
    source_match: bool

    @property
    def passed(self) -> bool:
        return self.provider_match and self.raw_fingerprint_match and self.source_match


def verify_decode_lineage(
    raw: RawProviderEvidence,
    datum: ProviderDatum,
) -> DecodeLineageReceipt:
    return DecodeLineageReceipt(
        provider=raw.provider,
        source_id=raw.source_id,
        raw_sha256=raw.raw_sha256,
        decoder_id=datum.provenance.decoder_id,
        mapping_revision=datum.provenance.mapping_revision,
        datum_id=datum.datum_id,
        provider_match=raw.provider == datum.provider == datum.provenance.provider,
        raw_fingerprint_match=raw.raw_sha256 == datum.provenance.raw_sha256,
        source_match=raw.source_id == datum.provenance.source_id,
    )
