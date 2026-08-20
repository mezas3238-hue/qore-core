from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest

import qore.infrastructure.crypto_perpetual_funding_semantics as crypto
import qore.infrastructure.derivative_contract_semantics as derivative
import qore.infrastructure.universal_instrument_identity as identity


def _economic_id(seed: int) -> identity.EconomicIdentityId:
    return identity.EconomicIdentityId(UUID(int=seed))


def _relationship_id(seed: int) -> identity.IdentityRelationshipId:
    return identity.IdentityRelationshipId(UUID(int=seed))


def _evidence(seed: int) -> crypto.CryptoEvidenceRef:
    return crypto.CryptoEvidenceRef(UUID(int=seed))


def _funding(**overrides: Any) -> crypto.CryptoFundingTerms:
    values: dict[str, Any] = {
        "interval": crypto.CryptoFundingInterval(fixed_seconds=28_800),
        "sign_convention": crypto.CryptoFundingSignConvention.POSITIVE_LONG_PAYS,
        "payment_identity_id": _economic_id(5),
        "evidence_ref": _evidence(101),
    }
    values.update(overrides)
    return crypto.CryptoFundingTerms(**values)


def _network(
    *,
    include_identifier: bool = True,
    **overrides: Any,
) -> crypto.CryptoNetworkBindingTerms:
    network_identifier = (
        identity.ExternalIdentifier(
            kind=identity.ExternalIdentifierKind.NETWORK_NATIVE,
            namespace=identity.ExternalIdentifierNamespace("eip155"),
            value=identity.ExternalIdentifierValue("1"),
        )
        if include_identifier
        else None
    )
    values: dict[str, Any] = {
        "terms_id": crypto.CryptoTermsId(UUID(int=30)),
        "relationship_id": _relationship_id(21),
        "role": crypto.CryptoNetworkBindingRoleCode("execution-network"),
        "evidence_ref": _evidence(103),
        "network_identifier": network_identifier,
    }
    values.update(overrides)
    return crypto.CryptoNetworkBindingTerms(**values)


def _pricing(**overrides: Any) -> crypto.CryptoPerpetualPricingTerms:
    values: dict[str, Any] = {
        "index_relationship_id": _relationship_id(20),
        "roles": (
            crypto.CryptoPerpetualPriceRole.LAST_PRICE,
            crypto.CryptoPerpetualPriceRole.MARK_PRICE,
            crypto.CryptoPerpetualPriceRole.INDEX_PRICE,
        ),
        "evidence_ref": _evidence(102),
    }
    values.update(overrides)
    return crypto.CryptoPerpetualPricingTerms(**values)


def _perpetual(
    *,
    include_tick: bool = True,
    include_network: bool = True,
    **overrides: Any,
) -> crypto.CryptoPerpetualContractTerms:
    values: dict[str, Any] = {
        "terms_id": crypto.CryptoTermsId(UUID(int=40)),
        "instrument_identity_id": _economic_id(1),
        "reference_identity_id": _economic_id(2),
        "settlement_identity_id": _economic_id(3),
        "collateral_identity_id": _economic_id(4),
        "multiplier": derivative.DerivativeContractMultiplier(
            value=Decimal("1.0000"),
            unit_identity_id=_economic_id(6),
        ),
        "tick_value": (
            derivative.DerivativeTickValue(
                value=Decimal("0.0100"),
                value_identity_id=_economic_id(7),
            )
            if include_tick
            else None
        ),
        "funding": _funding(),
        "pricing": _pricing(),
        "network_binding": _network() if include_network else None,
        "evidence_ref": _evidence(104),
    }
    values.update(overrides)
    return crypto.CryptoPerpetualContractTerms(**values)


_EXPECTED_FUNDING: tuple[object, ...] = (
    ("fixed-seconds", 28_800),
    "positive-long-pays",
    (str(UUID(int=5)),),
    (str(UUID(int=101)),),
)

_EXPECTED_PRICING: tuple[object, ...] = (
    (str(UUID(int=20)),),
    ("index-price", "last-price", "mark-price"),
    (str(UUID(int=102)),),
)

_EXPECTED_NETWORK_IDENTIFIER: tuple[object, ...] = (
    "network-native",
    ("eip155",),
    ("1",),
    None,
    None,
)

_EXPECTED_NETWORK: tuple[object, ...] = (
    "crypto-network-binding",
    (str(UUID(int=30)),),
    (str(UUID(int=21)),),
    ("execution-network",),
    _EXPECTED_NETWORK_IDENTIFIER,
    (str(UUID(int=103)),),
)

_EXPECTED_TICK: tuple[object, ...] = (
    "0.01",
    (str(UUID(int=7)),),
)


class _NonCanonicalUUID(UUID):
    def __str__(self) -> str:
        return "forged-noncanonical-uuid-material"


def test_full_closure_local_uuid_material_requires_exact_uuid_type() -> None:
    exact = UUID(int=8)
    forged = _NonCanonicalUUID(int=8)

    assert crypto.CryptoTermsId(exact).logical_values() == (str(UUID(int=8)),)
    assert crypto.CryptoEvidenceRef(exact).logical_values() == (str(UUID(int=8)),)
    assert isinstance(forged, UUID)
    assert str(forged) == "forged-noncanonical-uuid-material"

    with pytest.raises(crypto.CryptoPerpetualValidationError, match="must be UUID"):
        crypto.CryptoTermsId(forged)
    with pytest.raises(crypto.CryptoPerpetualValidationError, match="must be UUID"):
        crypto.CryptoEvidenceRef(forged)


def test_full_closure_fund_001_complete_projection_is_independent() -> None:
    assert _funding().logical_values() == _EXPECTED_FUNDING


def test_full_closure_net_001_complete_projection_with_identifier() -> None:
    assert _network(include_identifier=True).logical_values() == _EXPECTED_NETWORK


def test_full_closure_net_002_complete_projection_without_identifier() -> None:
    assert _network(include_identifier=False).logical_values() == (
        "crypto-network-binding",
        (str(UUID(int=30)),),
        (str(UUID(int=21)),),
        ("execution-network",),
        None,
        (str(UUID(int=103)),),
    )


def test_full_closure_price_001_manual_projection_canonicalizes_caller_order() -> None:
    assert _pricing().logical_values() == _EXPECTED_PRICING


def test_full_closure_perp_populated_001_complete_parent_projection() -> None:
    assert _perpetual(include_tick=True, include_network=True).logical_values() == (
        "crypto-perpetual",
        (str(UUID(int=40)),),
        (str(UUID(int=1)),),
        (str(UUID(int=2)),),
        (str(UUID(int=3)),),
        (str(UUID(int=4)),),
        ("1", (str(UUID(int=6)),)),
        _EXPECTED_TICK,
        _EXPECTED_FUNDING,
        _EXPECTED_PRICING,
        _EXPECTED_NETWORK,
        (str(UUID(int=104)),),
    )


@pytest.mark.parametrize(
    ("include_tick", "include_network", "expected_tick", "expected_network"),
    (
        (False, False, None, None),
        (True, False, _EXPECTED_TICK, None),
        (False, True, None, _EXPECTED_NETWORK),
    ),
)
def test_full_closure_perp_optional_parent_slots_are_independently_discriminated(
    include_tick: bool,
    include_network: bool,
    expected_tick: tuple[object, ...] | None,
    expected_network: tuple[object, ...] | None,
) -> None:
    assert _perpetual(
        include_tick=include_tick,
        include_network=include_network,
    ).logical_values() == (
        "crypto-perpetual",
        (str(UUID(int=40)),),
        (str(UUID(int=1)),),
        (str(UUID(int=2)),),
        (str(UUID(int=3)),),
        (str(UUID(int=4)),),
        ("1", (str(UUID(int=6)),)),
        expected_tick,
        _EXPECTED_FUNDING,
        _EXPECTED_PRICING,
        expected_network,
        (str(UUID(int=104)),),
    )


def test_full_closure_all_four_optional_parent_states_are_declared_valid() -> None:
    assert tuple(
        (include_tick, include_network)
        for include_tick in (False, True)
        for include_network in (False, True)
    ) == (
        (False, False),
        (False, True),
        (True, False),
        (True, True),
    )


def test_full_closure_historical_wrong_type_rejection_branches_are_directly_hit() -> None:
    with pytest.raises(crypto.CryptoPerpetualValidationError, match="funding interval"):
        _funding(interval=object())
    with pytest.raises(crypto.CryptoPerpetualValidationError, match="funding evidence_ref"):
        _funding(evidence_ref=object())

    with pytest.raises(crypto.CryptoPerpetualValidationError, match="network terms_id"):
        _network(terms_id=object())
    with pytest.raises(crypto.CryptoPerpetualValidationError, match="network role"):
        _network(role=object())
    with pytest.raises(crypto.CryptoPerpetualValidationError, match="network evidence_ref"):
        _network(evidence_ref=object())
    with pytest.raises(crypto.CryptoPerpetualValidationError, match="network identifier"):
        _network(network_identifier=object())

    with pytest.raises(crypto.CryptoPerpetualValidationError, match="pricing evidence_ref"):
        _pricing(evidence_ref=object())

    with pytest.raises(crypto.CryptoPerpetualValidationError, match="perpetual terms_id"):
        _perpetual(terms_id=object())
    with pytest.raises(crypto.CryptoPerpetualValidationError, match="perpetual multiplier"):
        _perpetual(multiplier=object())
    with pytest.raises(crypto.CryptoPerpetualValidationError, match="perpetual funding"):
        _perpetual(funding=object())
    with pytest.raises(crypto.CryptoPerpetualValidationError, match="perpetual pricing"):
        _perpetual(pricing=object())
    with pytest.raises(crypto.CryptoPerpetualValidationError, match="perpetual evidence_ref"):
        _perpetual(evidence_ref=object())
    with pytest.raises(crypto.CryptoPerpetualValidationError, match="perpetual tick_value"):
        _perpetual(tick_value=object())
    with pytest.raises(crypto.CryptoPerpetualValidationError, match="perpetual network_binding"):
        _perpetual(network_binding=object())
