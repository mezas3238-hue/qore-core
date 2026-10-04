import pytest
from qore.infrastructure.core_stack_v2.shared_lab_data_reality import CanonicalIdentity, ProviderDatum, ProviderProvenance
from qore.infrastructure.core_stack_v2.shared_lab_sensor_harness import SensorFault, expand_required_fault_cases, inject_fault
from qore.infrastructure.core_stack_v2.shared_lab_tools import default_shared_lab_registry


def _data() -> tuple[ProviderDatum, ...]:
    identity = CanonicalIdentity("FX:EURUSD", "FX", "EUR", quote_currency="USD")
    provenance = ProviderProvenance("p1", "feed", "c" * 64, "decoder", "map")
    return tuple(ProviderDatum(datum_id=f"d{i}", provider_symbol="EURUSD", provider="p1", sequence=i,
        observed_at_ns=i * 1000, available_at_ns=i * 1000 + 10, bid=1.1 + i / 10000, ask=1.2 + i / 10000,
        metadata_asset_class="FX", provenance=provenance, canonical_identity=identity, market_open=True, session_id="LONDON")
        for i in range(1, 5))


@pytest.mark.parametrize("fault", list(SensorFault))
def test_every_sensor_fault_materially_mutates_or_removes_evidence(fault: SensorFault) -> None:
    base = _data()
    mutated = inject_fault(base, fault, amount_ns=10_000)
    assert mutated != base


def test_registry_expands_family_cross_product_not_scripts() -> None:
    count = expand_required_fault_cases(default_shared_lab_registry(), sensors=("s1", "s2"), assets=("EURUSD", "XAUUSD"), regimes=("normal", "stress"))
    assert count > 50
