from dataclasses import replace

from qore.infrastructure.core_stack_v2.shared_lab_data_reality import CanonicalIdentity, ProviderDatum, ProviderProvenance
from qore.infrastructure.core_stack_v2.shared_lab_provider_harness import ProviderFailure, assess_cross_provider, assess_provider, assess_sequence_gap


def _d(seq: int, provider: str = "p1", bid: float = 1.1) -> ProviderDatum:
    prov = ProviderProvenance(provider, "source", ("a" if provider == "p1" else "b") * 64, "decoder", "map")
    ident = CanonicalIdentity("FX:EURUSD", "FX", "EUR", quote_currency="USD")
    return ProviderDatum(f"d{seq}", "EURUSD", provider, seq, seq * 1000, seq * 1000 + 10, bid, bid + 0.0002, "FX", prov, ident, True, "LONDON")


def test_provider_lineage_and_gap_detection() -> None:
    assert assess_provider(_d(1), expected_provider="p1", max_latency_ns=100).passed
    assert assess_sequence_gap((_d(1), _d(3))) == (ProviderFailure.SEQUENCE_GAP,)


def test_cross_provider_conflict() -> None:
    assert assess_cross_provider(_d(1), _d(1, "p2", 1.2), 0.001) == (ProviderFailure.CONFLICT,)
