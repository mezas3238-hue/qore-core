from __future__ import annotations

from datetime import date

import pytest

import qore.infrastructure.instrument_universe_registry as registry


@pytest.mark.parametrize(
    "corrupted_value",
    [
        "token = PLAINTEXT-SECRET",
        "password : PLAINTEXT-SECRET",
        "secret = PLAINTEXT-SECRET",
        "credential = PLAINTEXT-SECRET",
        "jwt = PLAINTEXT-SECRET",
        "authorization : PLAINTEXT-SECRET",
        "api key = PLAINTEXT-SECRET",
        "access token = PLAINTEXT-SECRET",
        "client secret = PLAINTEXT-SECRET",
        "private key = PLAINTEXT-SECRET",
    ],
)
def test_reason_revalidation_rejects_spaced_sensitive_assignments(
    corrupted_value: str,
) -> None:
    reason = registry.InstrumentUniverseReason("Safe retained reason")
    object.__setattr__(reason, "value", corrupted_value)

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        reason.__post_init__()
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        reason.logical_values()


def test_reason_constructor_rejects_spaced_token_assignment() -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason("token = PLAINTEXT-SECRET")


def test_evidence_record_rejects_scheme_relative_userinfo_after_corruption() -> None:
    record = registry.InstrumentUniverseEvidenceRecord(
        evidence_ref=registry.InstrumentUniverseEvidenceRef("qore-umi05"),
        source_category=registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY,
        source_name="QORE repository",
        locator="qore://umi-05/futures",
        verified_on=date(2026, 8, 15),
    )
    object.__setattr__(
        record,
        "locator",
        "//alice:password@example.invalid/evidence",
    )

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        record.__post_init__()
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        record.content_logical_values()
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        record.logical_values()


def test_evidence_record_constructor_rejects_scheme_relative_userinfo() -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseEvidenceRecord(
            evidence_ref=registry.InstrumentUniverseEvidenceRef("qore-umi05"),
            source_category=(
                registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY
            ),
            source_name="QORE repository",
            locator="//alice:password@example.invalid/evidence",
            verified_on=date(2026, 8, 15),
        )
