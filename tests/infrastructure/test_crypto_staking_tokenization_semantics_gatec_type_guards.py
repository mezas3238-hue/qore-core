from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import pytest

from qore.infrastructure.crypto_perpetual_funding_semantics import (
    CryptoEvidenceRef,
    CryptoTermsId,
)
from qore.infrastructure.crypto_staking_tokenization_semantics import (
    CryptoRepresentationBinding,
    CryptoRepresentationRoleCode,
    CryptoStakingTokenizationValidationError,
    CryptoTokenizedSecurityForm,
    CryptoTokenizedSecurityQualificationTerms,
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


def _evidence(value: int) -> CryptoEvidenceRef:
    return CryptoEvidenceRef(_uuid(value))


def _relationship() -> IdentityRelationship:
    return IdentityRelationship(
        relationship_id=IdentityRelationshipId(_uuid(1)),
        source_identity_id=_identity(2),
        target_identity_id=_identity(3),
        relationship=IdentityRelationshipCode("tokenized-representation-of"),
        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
        effective_until=None,
        evidence_ref=IdentityEvidenceRef(_uuid(4)),
    )


def test_representation_binding_rejects_raw_relationship() -> None:
    with pytest.raises(CryptoStakingTokenizationValidationError):
        CryptoRepresentationBinding(
            relationship=cast(Any, "raw-relationship"),
            role=CryptoRepresentationRoleCode("tokenized-representation-of"),
            evidence_ref=_evidence(5),
        )


def test_representation_binding_rejects_raw_role() -> None:
    with pytest.raises(CryptoStakingTokenizationValidationError):
        CryptoRepresentationBinding(
            relationship=_relationship(),
            role=cast(Any, "tokenized-representation-of"),
            evidence_ref=_evidence(6),
        )


def test_representation_binding_rejects_raw_evidence_ref() -> None:
    with pytest.raises(CryptoStakingTokenizationValidationError):
        CryptoRepresentationBinding(
            relationship=_relationship(),
            role=CryptoRepresentationRoleCode("tokenized-representation-of"),
            evidence_ref=cast(Any, _uuid(7)),
        )


def test_tokenized_security_rejects_raw_terms_id() -> None:
    with pytest.raises(CryptoStakingTokenizationValidationError):
        CryptoTokenizedSecurityQualificationTerms(
            terms_id=cast(Any, _uuid(8)),
            token_security_identity_id=_identity(9),
            form=CryptoTokenizedSecurityForm.NATIVE_ONCHAIN_ISSUANCE,
            evidence_ref=_evidence(10),
        )


def test_tokenized_security_rejects_raw_evidence_ref() -> None:
    with pytest.raises(CryptoStakingTokenizationValidationError):
        CryptoTokenizedSecurityQualificationTerms(
            terms_id=CryptoTermsId(_uuid(11)),
            token_security_identity_id=_identity(12),
            form=CryptoTokenizedSecurityForm.NATIVE_ONCHAIN_ISSUANCE,
            evidence_ref=cast(Any, _uuid(13)),
        )


def test_tokenized_security_rejects_raw_token_security_identity_id() -> None:
    with pytest.raises(
        CryptoStakingTokenizationValidationError,
        match="crypto tokenized-security identity must be EconomicIdentityId",
    ):
        CryptoTokenizedSecurityQualificationTerms(
            terms_id=CryptoTermsId(_uuid(14)),
            token_security_identity_id=cast(Any, _uuid(15)),
            form=CryptoTokenizedSecurityForm.NATIVE_ONCHAIN_ISSUANCE,
            evidence_ref=_evidence(16),
        )


def test_tokenized_security_rejects_raw_underlying_security_identity_id() -> None:
    binding = CryptoRepresentationBinding(
        relationship=_relationship(),
        role=CryptoRepresentationRoleCode("tokenized-representation-of"),
        evidence_ref=_evidence(17),
    )
    with pytest.raises(
        CryptoStakingTokenizationValidationError,
        match="represented security identity must be EconomicIdentityId",
    ):
        CryptoTokenizedSecurityQualificationTerms(
            terms_id=CryptoTermsId(_uuid(18)),
            token_security_identity_id=_identity(2),
            form=CryptoTokenizedSecurityForm.TOKENIZED_REPRESENTATION,
            evidence_ref=_evidence(19),
            underlying_security_identity_id=cast(Any, _uuid(20)),
            representation_binding=binding,
        )


def test_tokenized_security_rejects_raw_representation_binding() -> None:
    with pytest.raises(
        CryptoStakingTokenizationValidationError,
        match="tokenized representation requires exact representation binding",
    ):
        CryptoTokenizedSecurityQualificationTerms(
            terms_id=CryptoTermsId(_uuid(21)),
            token_security_identity_id=_identity(22),
            form=CryptoTokenizedSecurityForm.TOKENIZED_REPRESENTATION,
            evidence_ref=_evidence(23),
            underlying_security_identity_id=_identity(24),
            representation_binding=cast(Any, "raw-representation-binding"),
        )
