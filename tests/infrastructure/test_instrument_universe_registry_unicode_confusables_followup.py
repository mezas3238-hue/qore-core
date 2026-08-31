from __future__ import annotations

from datetime import date

import pytest

import qore.infrastructure.instrument_universe_registry as registry


@pytest.mark.parametrize(
    "obfuscated_value",
    [
        "tok\u0435n=PLAINTEXT-SECRET",  # Cyrillic e
        "t\u03bfken=PLAINTEXT-SECRET",  # Greek omicron
        "toke\u03b7=PLAINTEXT-SECRET",  # Greek eta for n
        "authorizatio\u03b7=PLAINTEXT-SECRET",  # Greek eta for n
        "a\u0438thorization=PLAINTEXT-SECRET",  # Cyrillic i for u
        "a\u0438thorization:PLAINTEXT-SECRET",  # Cyrillic i for u
        "pa\u0455\u0455word=PLAINTEXT-SECRET",  # Cyrillic dze
        "pa\u03c2\u03c2word=PLAINTEXT-SECRET",  # Greek final sigma -> sigma on casefold
        "authori\u0437ation=PLAINTEXT-SECRET",  # Cyrillic ze
        "autho\u0433ization=PLAINTEXT-SECRET",  # Cyrillic ghe for r
        "bea\u0433er=PLAINTEXT-SECRET",  # Cyrillic ghe for r
        "\u0432earer=PLAINTEXT-SECRET",  # Cyrillic ve for b
        "token\u2236PLAINTEXT-SECRET",  # ratio sign for colon
        "token\u02d0PLAINTEXT-SECRET",  # modifier letter triangular colon
        "api\u2011key=PLAINTEXT-SECRET",  # non-breaking hyphen
        "api\u2015key=PLAINTEXT-SECRET",  # horizontal bar
        "private\u2015key=PLAINTEXT-SECRET",  # horizontal bar
    ],
)
def test_reason_constructor_rejects_cross_script_sensitive_assignments(
    obfuscated_value: str,
) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(obfuscated_value)


@pytest.mark.parametrize(
    "assignment",
    [
        "bearer=PLAINTEXT-SECRET",
        "bearer : PLAINTEXT-SECRET",
        "BEARER=PLAINTEXT-SECRET",
    ],
)
def test_reason_constructor_rejects_bearer_assignments(assignment: str) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(assignment)


@pytest.mark.parametrize(
    "corrupted_value",
    [
        "tok\u0435n=PLAINTEXT-SECRET",
        "toke\u03b7=PLAINTEXT-SECRET",
        "authorizatio\u03b7=PLAINTEXT-SECRET",
        "a\u0438thorization=PLAINTEXT-SECRET",
        "a\u0438thorization:PLAINTEXT-SECRET",
        "pa\u03c2\u03c2word=PLAINTEXT-SECRET",
        "authori\u0437ation=PLAINTEXT-SECRET",
        "autho\u0433ization=PLAINTEXT-SECRET",
        "bea\u0433er=PLAINTEXT-SECRET",
        "bearer=PLAINTEXT-SECRET",
        "token\u02d0PLAINTEXT-SECRET",
        "api\u2015key=PLAINTEXT-SECRET",
        "private\u2015key=PLAINTEXT-SECRET",
        "private\u2010key\u2236PLAINTEXT-SECRET",
    ],
)
def test_reason_revalidation_rejects_followup_confusable_assignments(
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


def test_evidence_record_revalidation_rejects_cross_script_source_name() -> None:
    record = registry.InstrumentUniverseEvidenceRecord(
        evidence_ref=registry.InstrumentUniverseEvidenceRef("qore-umi05"),
        source_category=registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY,
        source_name="QORE repository",
        locator="qore://umi-05/futures",
        verified_on=date(2026, 8, 15),
    )
    object.__setattr__(record, "source_name", "tok\u0435n=PLAINTEXT-SECRET")

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


def test_legitimate_cross_script_printable_unicode_remains_unchanged() -> None:
    value = "Αγορά evidence — рынок reference"

    reason = registry.InstrumentUniverseReason(value)

    assert reason.logical_values() == (value,)
