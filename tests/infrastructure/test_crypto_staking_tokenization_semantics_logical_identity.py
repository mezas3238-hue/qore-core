from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from qore.infrastructure.crypto_perpetual_funding_semantics import (
    CryptoEvidenceRef,
    CryptoNetworkBindingRoleCode,
    CryptoNetworkBindingTerms,
    CryptoTermsId,
)
from qore.infrastructure.crypto_staking_tokenization_semantics import (
    CryptoRepresentationBinding,
    CryptoRepresentationRoleCode,
    CryptoStakingExitMode,
    CryptoStakingExitScheduleCode,
    CryptoStakingExitTerms,
    CryptoStakingModeCode,
    CryptoStakingPenaltyPolicyCode,
    CryptoStakingTerms,
    CryptoTokenizedSecurityForm,
    CryptoTokenizedSecurityQualificationTerms,
    CryptoYieldBearingTokenTerms,
    CryptoYieldMechanismCode,
)
from qore.infrastructure.universal_instrument_identity import (
    EconomicIdentityId,
    IdentityEvidenceRef,
    IdentityRelationship,
    IdentityRelationshipCode,
    IdentityRelationshipId,
)


def _uuid(value: int) -> UUID:
    return UUID(int=value)


def _identity(value: int) -> EconomicIdentityId:
    return EconomicIdentityId(_uuid(value))


def _crypto_evidence(value: int) -> CryptoEvidenceRef:
    return CryptoEvidenceRef(_uuid(value))


def _uuid_expected(value: int) -> tuple[str, ...]:
    return (str(_uuid(value)),)


def _relationship(
    *,
    source: int,
    target: int,
    code: str,
    value: int,
    ordinal: int | None,
) -> IdentityRelationship:
    return IdentityRelationship(
        relationship_id=IdentityRelationshipId(_uuid(value)),
        source_identity_id=_identity(source),
        target_identity_id=_identity(target),
        relationship=IdentityRelationshipCode(code),
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
        effective_until=None,
        evidence_ref=IdentityEvidenceRef(_uuid(value + 1)),
        ordinal=ordinal,
    )


def _relationship_expected(
    *,
    source: int,
    target: int,
    code: str,
    value: int,
    ordinal: int | None,
) -> tuple[object, ...]:
    return (
        _uuid_expected(value),
        _uuid_expected(source),
        _uuid_expected(target),
        (code,),
        "2026-01-01T00:00:00.000000+00:00",
        None,
        _uuid_expected(value + 1),
        ordinal,
    )


def _binding(
    *,
    source: int,
    target: int,
    code: str,
    value: int,
    ordinal: int | None,
) -> CryptoRepresentationBinding:
    return CryptoRepresentationBinding(
        relationship=_relationship(
            source=source,
            target=target,
            code=code,
            value=value,
            ordinal=ordinal,
        ),
        role=CryptoRepresentationRoleCode(code),
        evidence_ref=_crypto_evidence(value + 2),
    )


def _binding_expected(
    *,
    source: int,
    target: int,
    code: str,
    value: int,
    ordinal: int | None,
) -> tuple[object, ...]:
    return (
        _relationship_expected(
            source=source,
            target=target,
            code=code,
            value=value,
            ordinal=ordinal,
        ),
        (code,),
        _uuid_expected(value + 2),
    )


def _network_binding(value: int) -> CryptoNetworkBindingTerms:
    return CryptoNetworkBindingTerms(
        terms_id=CryptoTermsId(_uuid(value)),
        relationship_id=IdentityRelationshipId(_uuid(value + 1)),
        role=CryptoNetworkBindingRoleCode("native-network"),
        evidence_ref=_crypto_evidence(value + 2),
    )


def _network_expected(value: int) -> tuple[object, ...]:
    return (
        "crypto-network-binding",
        _uuid_expected(value),
        _uuid_expected(value + 1),
        ("native-network",),
        None,
        _uuid_expected(value + 2),
    )


def test_gateb_exact_crypto_staking_tokenization_field_surfaces_are_closed() -> None:
    surfaces: tuple[tuple[type[Any], tuple[str, ...]], ...] = (
        (CryptoStakingModeCode, ("value",)),
        (CryptoStakingExitScheduleCode, ("value",)),
        (CryptoStakingPenaltyPolicyCode, ("value",)),
        (CryptoYieldMechanismCode, ("value",)),
        (CryptoRepresentationRoleCode, ("value",)),
        (
            CryptoStakingExitTerms,
            ("mode", "fixed_delay_seconds", "schedule_code"),
        ),
        (
            CryptoRepresentationBinding,
            ("relationship", "role", "evidence_ref"),
        ),
        (
            CryptoStakingTerms,
            (
                "terms_id",
                "staked_asset_identity_id",
                "reward_asset_identity_id",
                "mode",
                "exit_terms",
                "evidence_ref",
                "penalty_policy_code",
                "receipt_binding",
                "network_binding",
            ),
        ),
        (
            CryptoYieldBearingTokenTerms,
            (
                "terms_id",
                "token_identity_id",
                "underlying_identity_id",
                "representation_binding",
                "yield_mechanism",
                "evidence_ref",
                "network_binding",
            ),
        ),
        (
            CryptoTokenizedSecurityQualificationTerms,
            (
                "terms_id",
                "token_security_identity_id",
                "form",
                "evidence_ref",
                "underlying_security_identity_id",
                "representation_binding",
                "network_binding",
            ),
        ),
    )
    for cls, expected in surfaces:
        assert tuple(field.name for field in fields(cls)) == expected


def test_gateb_representation_binding_projection_preserves_umi02_ordinal() -> None:
    binding = _binding(
        source=10,
        target=11,
        code="staking-receipt-for",
        value=200,
        ordinal=2,
    )
    assert binding.logical_values() == _binding_expected(
        source=10,
        target=11,
        code="staking-receipt-for",
        value=200,
        ordinal=2,
    )


def test_gateb_staking_projection_is_independently_reconstructed() -> None:
    terms = CryptoStakingTerms(
        terms_id=CryptoTermsId(_uuid(20)),
        staked_asset_identity_id=_identity(21),
        reward_asset_identity_id=_identity(22),
        mode=CryptoStakingModeCode("pooled-liquid-staking"),
        exit_terms=CryptoStakingExitTerms(
            CryptoStakingExitMode.GOVERNED_SCHEDULE,
            schedule_code=CryptoStakingExitScheduleCode("protocol-exit-v1"),
        ),
        evidence_ref=_crypto_evidence(23),
        penalty_policy_code=CryptoStakingPenaltyPolicyCode("protocol-slashing"),
        receipt_binding=_binding(
            source=24,
            target=21,
            code="staking-receipt-for",
            value=220,
            ordinal=3,
        ),
        network_binding=_network_binding(300),
    )
    assert terms.logical_values() == (
        "crypto-staking",
        _uuid_expected(20),
        _uuid_expected(21),
        _uuid_expected(22),
        ("pooled-liquid-staking",),
        ("governed-schedule", None, ("protocol-exit-v1",)),
        ("protocol-slashing",),
        _binding_expected(
            source=24,
            target=21,
            code="staking-receipt-for",
            value=220,
            ordinal=3,
        ),
        _network_expected(300),
        _uuid_expected(23),
    )


def test_gateb_yield_bearing_projection_is_independently_reconstructed() -> None:
    terms = CryptoYieldBearingTokenTerms(
        terms_id=CryptoTermsId(_uuid(40)),
        token_identity_id=_identity(41),
        underlying_identity_id=_identity(42),
        representation_binding=_binding(
            source=41,
            target=42,
            code="yield-bearing-representation-of",
            value=240,
            ordinal=4,
        ),
        yield_mechanism=CryptoYieldMechanismCode("vault-share-exchange-rate"),
        evidence_ref=_crypto_evidence(43),
        network_binding=_network_binding(340),
    )
    assert terms.logical_values() == (
        "crypto-yield-bearing-token",
        _uuid_expected(40),
        _uuid_expected(41),
        _uuid_expected(42),
        _binding_expected(
            source=41,
            target=42,
            code="yield-bearing-representation-of",
            value=240,
            ordinal=4,
        ),
        ("vault-share-exchange-rate",),
        _network_expected(340),
        _uuid_expected(43),
    )


def test_gateb_tokenized_representation_projection_is_independently_reconstructed() -> None:
    terms = CryptoTokenizedSecurityQualificationTerms(
        terms_id=CryptoTermsId(_uuid(60)),
        token_security_identity_id=_identity(61),
        form=CryptoTokenizedSecurityForm.TOKENIZED_REPRESENTATION,
        evidence_ref=_crypto_evidence(62),
        underlying_security_identity_id=_identity(63),
        representation_binding=_binding(
            source=61,
            target=63,
            code="tokenized-representation-of",
            value=260,
            ordinal=5,
        ),
        network_binding=_network_binding(360),
    )
    assert terms.logical_values() == (
        "crypto-tokenized-security-qualification",
        _uuid_expected(60),
        _uuid_expected(61),
        "tokenized-representation",
        _uuid_expected(63),
        _binding_expected(
            source=61,
            target=63,
            code="tokenized-representation-of",
            value=260,
            ordinal=5,
        ),
        _network_expected(360),
        _uuid_expected(62),
    )


def test_gateb_native_onchain_projection_preserves_explicit_none_material() -> None:
    terms = CryptoTokenizedSecurityQualificationTerms(
        terms_id=CryptoTermsId(_uuid(80)),
        token_security_identity_id=_identity(81),
        form=CryptoTokenizedSecurityForm.NATIVE_ONCHAIN_ISSUANCE,
        evidence_ref=_crypto_evidence(82),
    )
    assert terms.logical_values() == (
        "crypto-tokenized-security-qualification",
        _uuid_expected(80),
        _uuid_expected(81),
        "native-onchain-issuance",
        None,
        None,
        None,
        _uuid_expected(82),
    )
