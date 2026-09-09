from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.ctrader_demo_lab_index_identity import (
    CTraderDemoIndexEconomicIdentity,
)
from qore.infrastructure.ctrader_demo_lab_probe import (
    CTraderDemoLabProbeError,
    CTraderDemoLabSymbolEvidence,
)


def _symbol(name: str) -> CTraderDemoLabSymbolEvidence:
    return CTraderDemoLabSymbolEvidence(
        symbol_id=101,
        symbol_name=name,
        digits=2,
        min_volume_units=100,
        max_volume_units=100000,
        step_volume_units=100,
    )


def _identity(
    *,
    target: str,
    symbol_name: str,
    description: str,
) -> CTraderDemoIndexEconomicIdentity:
    return CTraderDemoIndexEconomicIdentity(
        economic_target=target,
        provider_symbol=_symbol(symbol_name),
        provider_description=description,
        provider_symbol_category_id=7,
        account_fingerprint="a" * 64,
        checked_at=datetime(2026, 9, 9, tzinfo=UTC),
    )


@pytest.mark.parametrize(
    ("target", "symbol_name", "description"),
    [
        ("US30", "US30", "Dow Jones Industrial Average 30 Index"),
        ("US30", "WS30", "Wall Street 30 Index"),
        ("NAS100", "US100", "Nasdaq 100 Index"),
        ("SP500", "US500", "S&P 500 Index"),
    ],
)
def test_exact_alias_and_target_specific_provider_description_certify(
    target: str,
    symbol_name: str,
    description: str,
) -> None:
    identity = _identity(
        target=target,
        symbol_name=symbol_name,
        description=description,
    )
    payload = identity.payload()
    assert payload["economic_target"] == target
    assert payload["economic_identity_certified"] is True
    assert payload["binding_basis"] == (
        "enabled-alias+provider-target-description+exact-symbol-details-v1"
    )
    assert payload["category_semantics_resolved"] is False
    assert payload["category_semantics_used_for_certification"] is False


def test_alias_without_target_description_fails_closed() -> None:
    with pytest.raises(CTraderDemoLabProbeError, match="description"):
        _identity(
            target="US30",
            symbol_name="US30",
            description="Generic equity CFD",
        )


def test_cross_target_alias_fails_closed() -> None:
    with pytest.raises(CTraderDemoLabProbeError, match="alias"):
        _identity(
            target="SP500",
            symbol_name="US30",
            description="S&P 500 Index",
        )


def test_target_description_cannot_launder_wrong_index() -> None:
    with pytest.raises(CTraderDemoLabProbeError, match="description"):
        _identity(
            target="NAS100",
            symbol_name="US100",
            description="Dow Jones Industrial Average 30 Index",
        )


def test_generic_us_equity_description_cannot_certify_nas100() -> None:
    with pytest.raises(CTraderDemoLabProbeError, match="description"):
        _identity(
            target="NAS100",
            symbol_name="USTEC",
            description="US technology equity CFD",
        )
