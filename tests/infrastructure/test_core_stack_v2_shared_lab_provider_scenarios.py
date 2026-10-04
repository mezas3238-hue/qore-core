import math
import pytest

from qore.infrastructure.core_stack_v2.shared_lab_data_reality import CanonicalIdentity, ProviderDatum, ProviderProvenance
from qore.infrastructure.core_stack_v2.shared_lab_provider_scenarios import ProviderScenario, apply_provider_scenario


def _data() -> tuple[ProviderDatum, ...]:
    ident = CanonicalIdentity("FX:EURUSD", "FX", "EUR", quote_currency="USD")
    prov = ProviderProvenance("p1", "source", "b" * 64, "decoder", "map-v1")
    return tuple(
        ProviderDatum(f"d{i}", "EURUSD", "p1", i, i * 1000, i * 1000 + 10, 1.1 + i/10000, 1.2 + i/10000, "FX", prov, ident, True, "LONDON")
        for i in range(1, 5)
    )


@pytest.mark.parametrize("scenario", list(ProviderScenario))
def test_every_provider_scenario_materially_changes_evidence(scenario: ProviderScenario) -> None:
    base = _data()
    mutated = apply_provider_scenario(base, scenario)
    assert mutated != base


def test_corrupted_payload_is_nonfinite() -> None:
    corrupted = apply_provider_scenario(_data(), ProviderScenario.CORRUPTED_PAYLOAD)
    assert math.isnan(corrupted[0].bid)
