from dataclasses import replace

from qore.infrastructure.core_stack_v2.shared_lab_data_provenance import (
    RawProviderEvidence,
    verify_decode_lineage,
)
from qore.infrastructure.core_stack_v2.shared_lab_data_reality import (
    CanonicalIdentity,
    ProviderDatum,
    ProviderProvenance,
)


def _raw() -> RawProviderEvidence:
    return RawProviderEvidence("p1", "socket-A", b"EURUSD,1.1000,1.1002", 1000, "text/csv", 7)


def _datum(raw: RawProviderEvidence) -> ProviderDatum:
    identity = CanonicalIdentity("FX:EURUSD", "FX", "EUR", quote_currency="USD")
    provenance = ProviderProvenance("p1", "socket-A", raw.raw_sha256, "csv-decoder-v1", "map-v1")
    return ProviderDatum("d1", "EURUSD", "p1", 1, 900, 1000, 1.1, 1.1002, "FX", provenance, identity, True, "LONDON")


def test_raw_received_evidence_reconstructs_exact_decode_lineage() -> None:
    raw = _raw()
    receipt = verify_decode_lineage(raw, _datum(raw))
    assert receipt.passed
    assert receipt.raw_sha256 == raw.raw_sha256


def test_fake_provider_provenance_fails_exact_lineage() -> None:
    raw = _raw()
    datum = _datum(raw)
    fake = replace(
        datum,
        provenance=ProviderProvenance("p1", "socket-A", "0" * 64, "csv-decoder-v1", "map-v1"),
    )
    assert not verify_decode_lineage(raw, fake).passed
