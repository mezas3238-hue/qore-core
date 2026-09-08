from __future__ import annotations

from datetime import date

import pytest

import qore.infrastructure.instrument_universe_registry as registry


@pytest.mark.parametrize(
    "obfuscated_value",
    [
        "token\uFF1DPLAINTEXT-SECRET",
        "token\uFE0F=PLAINTEXT-SECRET",
        "api\uFE0F key = PLAINTEXT-SECRET",
        "api key \uFF1D PLAINTEXT-SECRET",
    ],
)
def test_reason_constructor_rejects_printable_unicode_credential_obfuscation(
    obfuscated_value: str,
) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(obfuscated_value)


@pytest.mark.parametrize(
    "corrupted_value",
    [
        "token\uFF1DPLAINTEXT-SECRET",
        "token\uFE0F=PLAINTEXT-SECRET",
        "private\uFE0F key = PLAINTEXT-SECRET",
    ],
)
def test_reason_revalidation_rejects_printable_unicode_credential_obfuscation(
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


def test_evidence_record_constructor_rejects_fullwidth_userinfo_separator() -> None:
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
            locator="https://alice:password\uFF20example.invalid/evidence",
            verified_on=date(2026, 8, 15),
        )


def test_evidence_record_revalidation_rejects_fullwidth_userinfo_separator() -> None:
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
        "https://alice:password\uFF20example.invalid/evidence",
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


def test_reason_preserves_legitimate_printable_combining_unicode() -> None:
    value = "Cafe\u0301 market evidence"

    reason = registry.InstrumentUniverseReason(value)

    assert reason.logical_values() == (value,)
