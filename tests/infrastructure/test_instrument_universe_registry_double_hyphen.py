from __future__ import annotations

from datetime import date

import pytest

import qore.infrastructure.instrument_universe_registry as registry

_DOUBLE_HYPHEN = "\u2e40"


@pytest.mark.parametrize("label", ("api", "private"))
@pytest.mark.parametrize("delimiter", ("=", ":"))
def test_reason_constructor_rejects_double_hyphen_sensitive_assignment(
    label: str,
    delimiter: str,
) -> None:
    value = f"{label}{_DOUBLE_HYPHEN}key{delimiter}PLAINTEXT-SECRET"

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(value)


@pytest.mark.parametrize("label", ("api", "private"))
def test_reason_revalidation_rejects_double_hyphen_sensitive_assignment(
    label: str,
) -> None:
    value = f"{label}{_DOUBLE_HYPHEN}key=PLAINTEXT-SECRET"
    reason = registry.InstrumentUniverseReason("Safe retained reason")
    object.__setattr__(reason, "value", value)

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


@pytest.mark.parametrize("field_name", ("source_name", "locator"))
def test_evidence_revalidation_rejects_double_hyphen_sensitive_assignment(
    field_name: str,
) -> None:
    record = registry.InstrumentUniverseEvidenceRecord(
        evidence_ref=registry.InstrumentUniverseEvidenceRef("qore-umi05"),
        source_category=registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY,
        source_name="QORE repository",
        locator="qore://umi-05/futures",
        verified_on=date(2026, 8, 15),
    )
    object.__setattr__(
        record,
        field_name,
        f"private{_DOUBLE_HYPHEN}key=PLAINTEXT-SECRET",
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


def test_benign_double_hyphen_text_is_retained_byte_for_byte() -> None:
    value = f"Evidence{_DOUBLE_HYPHEN}reference"

    reason = registry.InstrumentUniverseReason(value)

    assert reason.logical_values() == (value,)
