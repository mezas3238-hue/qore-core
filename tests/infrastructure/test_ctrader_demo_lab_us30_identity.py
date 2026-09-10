from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.ctrader_demo_lab_probe import (
    CTraderDemoLabProbeError,
    CTraderDemoLabSymbolEvidence,
)
from qore.infrastructure.ctrader_demo_lab_us30_identity import (
    CTraderDemoUs30ExactIdentity,
    exact_us30_provider_descriptor_matches,
)


def _symbol(name: str = "US30") -> CTraderDemoLabSymbolEvidence:
    return CTraderDemoLabSymbolEvidence(
        symbol_id=10015,
        symbol_name=name,
        digits=2,
        min_volume_units=100,
        max_volume_units=100000,
        step_volume_units=100,
    )


def test_exact_observed_provider_descriptor_certifies() -> None:
    identity = CTraderDemoUs30ExactIdentity(
        provider_symbol=_symbol(),
        provider_description="USA Dow Jones IA Index",
        provider_symbol_category_id=7,
        account_fingerprint="a" * 64,
        checked_at=datetime(2026, 9, 9, tzinfo=UTC),
    )

    payload = identity.payload()
    assert payload["economic_target"] == "US30"
    assert payload["economic_identity_certified"] is True
    assert payload["execution_authority"] is False
    assert payload["binding_basis"] == (
        "exact-us30-symbol+exact-provider-description+exact-symbol-details-v1"
    )


@pytest.mark.parametrize(
    ("symbol_name", "description"),
    [
        ("US30", "USA Dow Jones Index"),
        ("US30", "Dow Jones IA Index"),
        ("US30", "USA Dow Jones Industrial Average Index"),
        ("US30", "Generic Dow Jones IA Index"),
        ("DJ30", "USA Dow Jones IA Index"),
        ("US500", "USA Dow Jones IA Index"),
    ],
)
def test_nearby_or_generic_descriptors_stay_blocked(
    symbol_name: str,
    description: str,
) -> None:
    assert not exact_us30_provider_descriptor_matches(symbol_name, description)


def test_benign_case_and_punctuation_normalization_is_allowed() -> None:
    assert exact_us30_provider_descriptor_matches(
        " us30 ",
        "USA  Dow Jones IA-Index",
    )


def test_identity_rejects_exact_description_on_wrong_symbol() -> None:
    with pytest.raises(CTraderDemoLabProbeError, match="exact US30 identity"):
        CTraderDemoUs30ExactIdentity(
            provider_symbol=_symbol("DJ30"),
            provider_description="USA Dow Jones IA Index",
            provider_symbol_category_id=7,
            account_fingerprint="a" * 64,
            checked_at=datetime(2026, 9, 9, tzinfo=UTC),
        )
