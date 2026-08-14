from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import pytest

from qore.infrastructure.crypto_perpetual_funding_semantics import (
    CryptoEvidenceRef,
    CryptoFundingInterval,
    CryptoFundingScheduleCode,
    CryptoFundingSignConvention,
    CryptoFundingTerms,
    CryptoNetworkBindingRoleCode,
    CryptoNetworkBindingTerms,
    CryptoPerpetualContractTerms,
    CryptoPerpetualPriceRole,
    CryptoPerpetualPricingTerms,
    CryptoPerpetualValidationError,
    CryptoTermsId,
)
from qore.infrastructure.derivative_contract_semantics import (
    DerivativeContractMultiplier,
    DerivativeTickValue,
)
from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentityId,
    ExternalIdentifier,
    ExternalIdentifierKind,
    ExternalIdentifierNamespace,
    ExternalIdentifierValue,
    IdentityRelationshipId,
)


def _economic_id(seed: int) -> EconomicIdentityId:
    return EconomicIdentityId(UUID(int=seed))


def _relationship_id(seed: int) -> IdentityRelationshipId:
    return IdentityRelationshipId(UUID(int=seed))


def _evidence(seed: int = 100) -> CryptoEvidenceRef:
    return CryptoEvidenceRef(UUID(int=seed))


def _funding(
    *,
    payment_identity_id: EconomicIdentityId | None = None,
    interval: CryptoFundingInterval | None = None,
) -> CryptoFundingTerms:
    return CryptoFundingTerms(
        interval=interval or CryptoFundingInterval(fixed_seconds=28_800),
        sign_convention=CryptoFundingSignConvention.POSITIVE_LONG_PAYS,
        payment_identity_id=payment_identity_id or _economic_id(5),
        evidence_ref=_evidence(101),
    )


def _pricing(
    roles: tuple[CryptoPerpetualPriceRole, ...] | None = None,
) -> CryptoPerpetualPricingTerms:
    return CryptoPerpetualPricingTerms(
        index_relationship_id=_relationship_id(20),
        roles=roles
        or (
            CryptoPerpetualPriceRole.LAST_PRICE,
            CryptoPerpetualPriceRole.MARK_PRICE,
            CryptoPerpetualPriceRole.INDEX_PRICE,
        ),
        evidence_ref=_evidence(102),
    )


def _network_identifier(
    kind: ExternalIdentifierKind = ExternalIdentifierKind.NETWORK_NATIVE,
) -> ExternalIdentifier:
    return ExternalIdentifier(
        kind=kind,
        namespace=ExternalIdentifierNamespace("eip155"),
        value=ExternalIdentifierValue("1"),
    )


def _network() -> CryptoNetworkBindingTerms:
    return CryptoNetworkBindingTerms(
        terms_id=CryptoTermsId(UUID(int=30)),
        relationship_id=_relationship_id(21),
        role=CryptoNetworkBindingRoleCode("execution-network"),
        network_identifier=_network_identifier(),
        evidence_ref=_evidence(103),
    )


def _perpetual(
    *,
    instrument_identity_id: EconomicIdentityId | None = None,
    reference_identity_id: EconomicIdentityId | None = None,
    settlement_identity_id: EconomicIdentityId | None = None,
    collateral_identity_id: EconomicIdentityId | None = None,
    funding: CryptoFundingTerms | None = None,
    pricing: CryptoPerpetualPricingTerms | None = None,
    network_binding: CryptoNetworkBindingTerms | None = None,
) -> CryptoPerpetualContractTerms:
    reference = reference_identity_id or _economic_id(2)
    return CryptoPerpetualContractTerms(
        terms_id=CryptoTermsId(UUID(int=40)),
        instrument_identity_id=instrument_identity_id or _economic_id(1),
        reference_identity_id=reference,
        settlement_identity_id=settlement_identity_id or _economic_id(3),
        collateral_identity_id=collateral_identity_id or _economic_id(4),
        multiplier=DerivativeContractMultiplier(
            value=Decimal("1.0000"),
            unit_identity_id=reference,
        ),
        tick_value=DerivativeTickValue(
            value=Decimal("0.0100"),
            value_identity_id=settlement_identity_id or _economic_id(3),
        ),
        funding=funding or _funding(),
        pricing=pricing or _pricing(),
        network_binding=network_binding,
        evidence_ref=_evidence(104),
    )


def test_local_ids_require_uuid_and_do_not_become_economic_identity() -> None:
    terms_id = CryptoTermsId(UUID(int=1))
    evidence = CryptoEvidenceRef(UUID(int=2))

    assert terms_id.logical_values() == (str(UUID(int=1)),)
    assert evidence.logical_values() == (str(UUID(int=2)),)
    assert not isinstance(terms_id, EconomicIdentityId)
    assert not isinstance(evidence, EconomicIdentityId)

    with pytest.raises(CryptoPerpetualValidationError, match="must be UUID"):
        CryptoTermsId(cast(Any, "not-a-uuid"))
    with pytest.raises(CryptoPerpetualValidationError, match="must be UUID"):
        CryptoEvidenceRef(cast(Any, "not-a-uuid"))


def test_price_roles_are_distinct_semantics_without_observed_values() -> None:
    assert CryptoPerpetualPriceRole.MARK_PRICE.value == "mark-price"
    assert CryptoPerpetualPriceRole.INDEX_PRICE.value == "index-price"
    assert CryptoPerpetualPriceRole.LAST_PRICE.value == "last-price"
    assert len(set(CryptoPerpetualPriceRole)) == 3


@pytest.mark.parametrize("value", [0, -1, True])
def test_fixed_funding_interval_rejects_non_positive_or_bool(value: object) -> None:
    with pytest.raises(CryptoPerpetualValidationError, match="positive int"):
        CryptoFundingInterval(fixed_seconds=cast(Any, value))


def test_funding_interval_fixed_duration_is_explicit_and_deterministic() -> None:
    interval = CryptoFundingInterval(fixed_seconds=28_800)
    assert interval.logical_values() == ("fixed-seconds", 28_800)


def test_funding_interval_schedule_code_is_distinct_from_fixed_duration() -> None:
    interval = CryptoFundingInterval(
        schedule_code=CryptoFundingScheduleCode("venue-funding-calendar")
    )
    assert interval.logical_values() == (
        "schedule-code",
        ("venue-funding-calendar",),
    )


def test_funding_interval_requires_exactly_one_mode() -> None:
    with pytest.raises(CryptoPerpetualValidationError, match="exactly one"):
        CryptoFundingInterval()
    with pytest.raises(CryptoPerpetualValidationError, match="exactly one"):
        CryptoFundingInterval(
            fixed_seconds=28_800,
            schedule_code=CryptoFundingScheduleCode("venue-schedule"),
        )


def test_funding_interval_rejects_raw_schedule_code_laundering() -> None:
    with pytest.raises(CryptoPerpetualValidationError, match="schedule_code"):
        CryptoFundingInterval(schedule_code=cast(Any, "venue-schedule"))


def test_funding_terms_keep_sign_interval_payment_identity_but_no_rate_value() -> None:
    terms = _funding()
    assert terms.logical_values()[0] == ("fixed-seconds", 28_800)
    assert terms.logical_values()[1] == "positive-long-pays"
    assert terms.logical_values()[2] == _economic_id(5).logical_values()
    assert not hasattr(terms, "funding_rate")
    assert not hasattr(terms, "rate")


def test_funding_terms_reject_raw_payment_identity_and_wrong_sign_type() -> None:
    with pytest.raises(CryptoPerpetualValidationError, match="EconomicIdentityId"):
        CryptoFundingTerms(
            interval=CryptoFundingInterval(fixed_seconds=28_800),
            sign_convention=CryptoFundingSignConvention.POSITIVE_LONG_PAYS,
            payment_identity_id=cast(Any, UUID(int=5)),
            evidence_ref=_evidence(),
        )
    with pytest.raises(CryptoPerpetualValidationError, match="sign_convention"):
        CryptoFundingTerms(
            interval=CryptoFundingInterval(fixed_seconds=28_800),
            sign_convention=cast(Any, "positive-long-pays"),
            payment_identity_id=_economic_id(5),
            evidence_ref=_evidence(),
        )


@pytest.mark.parametrize("value", ["token=abc", "UPPER", "has space", "a/b"])
def test_crypto_codes_reject_noncanonical_or_credential_like_material(value: str) -> None:
    with pytest.raises(CryptoPerpetualValidationError):
        CryptoFundingScheduleCode(value)
    with pytest.raises(CryptoPerpetualValidationError):
        CryptoNetworkBindingRoleCode(value)


def test_network_binding_reuses_umi02_relationship_and_network_native_identifier() -> None:
    network = _network()
    assert network.relationship_id == _relationship_id(21)
    assert network.network_identifier is not None
    assert network.network_identifier.kind is ExternalIdentifierKind.NETWORK_NATIVE
    assert not hasattr(network, "source_identity_id")
    assert not hasattr(network, "target_identity_id")
    assert not hasattr(network, "effective_from")
    assert not hasattr(network, "effective_until")


def test_network_binding_rejects_raw_relationship_id() -> None:
    with pytest.raises(CryptoPerpetualValidationError, match="IdentityRelationshipId"):
        CryptoNetworkBindingTerms(
            terms_id=CryptoTermsId(UUID(int=30)),
            relationship_id=cast(Any, UUID(int=21)),
            role=CryptoNetworkBindingRoleCode("execution-network"),
            evidence_ref=_evidence(),
        )


def test_network_binding_rejects_non_network_native_external_identifier() -> None:
    with pytest.raises(CryptoPerpetualValidationError, match="NETWORK_NATIVE"):
        CryptoNetworkBindingTerms(
            terms_id=CryptoTermsId(UUID(int=30)),
            relationship_id=_relationship_id(21),
            role=CryptoNetworkBindingRoleCode("execution-network"),
            network_identifier=_network_identifier(ExternalIdentifierKind.STANDARD),
            evidence_ref=_evidence(),
        )


def test_pricing_requires_exact_mark_index_last_role_set_and_canonicalizes_order() -> None:
    left = _pricing(
        (
            CryptoPerpetualPriceRole.LAST_PRICE,
            CryptoPerpetualPriceRole.MARK_PRICE,
            CryptoPerpetualPriceRole.INDEX_PRICE,
        )
    )
    right = _pricing(
        (
            CryptoPerpetualPriceRole.INDEX_PRICE,
            CryptoPerpetualPriceRole.LAST_PRICE,
            CryptoPerpetualPriceRole.MARK_PRICE,
        )
    )

    assert left.roles == right.roles
    assert left.logical_values() == right.logical_values()
    assert tuple(role.value for role in left.roles) == (
        "index-price",
        "last-price",
        "mark-price",
    )


def test_pricing_rejects_mutable_missing_duplicate_and_wrong_role_material() -> None:
    with pytest.raises(CryptoPerpetualValidationError, match="immutable tuple"):
        CryptoPerpetualPricingTerms(
            index_relationship_id=_relationship_id(20),
            roles=cast(Any, [CryptoPerpetualPriceRole.MARK_PRICE]),
            evidence_ref=_evidence(),
        )
    with pytest.raises(CryptoPerpetualValidationError, match="mark, index, and last"):
        _pricing(
            (
                CryptoPerpetualPriceRole.MARK_PRICE,
                CryptoPerpetualPriceRole.INDEX_PRICE,
            )
        )
    with pytest.raises(CryptoPerpetualValidationError, match="unique"):
        CryptoPerpetualPricingTerms(
            index_relationship_id=_relationship_id(20),
            roles=(
                CryptoPerpetualPriceRole.MARK_PRICE,
                CryptoPerpetualPriceRole.MARK_PRICE,
                CryptoPerpetualPriceRole.INDEX_PRICE,
            ),
            evidence_ref=_evidence(),
        )
    with pytest.raises(CryptoPerpetualValidationError, match="CryptoPerpetualPriceRole"):
        CryptoPerpetualPricingTerms(
            index_relationship_id=_relationship_id(20),
            roles=cast(
                Any,
                (
                    "mark-price",
                    CryptoPerpetualPriceRole.INDEX_PRICE,
                    CryptoPerpetualPriceRole.LAST_PRICE,
                ),
            ),
            evidence_ref=_evidence(),
        )


def test_pricing_rejects_raw_index_relationship_id() -> None:
    with pytest.raises(CryptoPerpetualValidationError, match="IdentityRelationshipId"):
        CryptoPerpetualPricingTerms(
            index_relationship_id=cast(Any, UUID(int=20)),
            roles=tuple(CryptoPerpetualPriceRole),
            evidence_ref=_evidence(),
        )


def test_perpetual_does_not_launder_dated_futures_lifecycle() -> None:
    terms = _perpetual()
    for forbidden in (
        "contract_month",
        "expiry_date",
        "first_notice_date",
        "last_trade_date",
        "settlement_style",
    ):
        assert not hasattr(terms, forbidden)


@pytest.mark.parametrize(
    "field_name",
    [
        "reference_identity_id",
        "settlement_identity_id",
        "collateral_identity_id",
        "funding_payment_identity_id",
    ],
)
def test_perpetual_instrument_identity_cannot_collide_with_economic_roles(
    field_name: str,
) -> None:
    instrument = _economic_id(1)
    kwargs: dict[str, Any] = {"instrument_identity_id": instrument}
    if field_name == "funding_payment_identity_id":
        kwargs["funding"] = _funding(payment_identity_id=instrument)
    else:
        kwargs[field_name] = instrument

    with pytest.raises(CryptoPerpetualValidationError, match="must differ"):
        _perpetual(**kwargs)


def test_inverse_style_role_coincidence_remains_representable() -> None:
    shared = _economic_id(2)
    terms = _perpetual(
        reference_identity_id=shared,
        settlement_identity_id=shared,
        collateral_identity_id=shared,
        funding=_funding(payment_identity_id=shared),
    )
    assert terms.reference_identity_id == shared
    assert terms.settlement_identity_id == shared
    assert terms.collateral_identity_id == shared
    assert terms.funding.payment_identity_id == shared


def test_perpetual_reuses_umi05_multiplier_and_tick_primitives() -> None:
    terms = _perpetual()
    assert isinstance(terms.multiplier, DerivativeContractMultiplier)
    assert isinstance(terms.tick_value, DerivativeTickValue)
    assert terms.multiplier.logical_values() == (
        "1",
        _economic_id(2).logical_values(),
    )
    assert terms.tick_value is not None
    assert terms.tick_value.logical_values() == (
        "0.01",
        _economic_id(3).logical_values(),
    )


def test_perpetual_contains_no_observed_mark_index_last_or_funding_values() -> None:
    terms = _perpetual()
    for forbidden in (
        "mark_price",
        "index_price",
        "last_price",
        "funding_rate",
        "funding_rate_value",
    ):
        assert not hasattr(terms, forbidden)


def test_perpetual_contracts_are_immutable_and_logical_values_repeat() -> None:
    terms = _perpetual(network_binding=_network())
    first = terms.logical_values()
    second = terms.logical_values()

    assert first == second
    attribute = "collateral_identity_id"
    with pytest.raises(FrozenInstanceError):
        setattr(terms, attribute, _economic_id(99))


def test_candidate_exposes_no_wallet_custody_chain_execution_or_risk_engine() -> None:
    objects: tuple[object, ...] = (
        _funding(),
        _pricing(),
        _network(),
        _perpetual(network_binding=_network()),
    )
    forbidden = (
        "observe",
        "calculate",
        "calculate_funding",
        "price",
        "wallet",
        "custody",
        "sign",
        "send_transaction",
        "rpc",
        "oracle",
        "liquidate",
        "margin",
        "settle",
        "execute",
        "route",
        "provider",
        "amm",
        "adjust_balance",
        "adjust_position",
    )
    for value in objects:
        for name in forbidden:
            assert not hasattr(value, name)


def test_logical_material_is_secret_free() -> None:
    material = repr(_perpetual(network_binding=_network()).logical_values()).lower()
    for marker in ("token=", "secret=", "password=", "bearer "):
        assert marker not in material
