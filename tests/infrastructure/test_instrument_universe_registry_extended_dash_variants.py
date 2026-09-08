from __future__ import annotations

from datetime import date

import pytest

import qore.infrastructure.instrument_universe_registry as registry

_EXTENDED_DASH_VARIANTS = ("\u2e3a", "\u2e3b")


@pytest.mark.parametrize("separator", _EXTENDED_DASH_VARIANTS)
@pytest.mark.parametrize("label", ("api", "private"))
@pytest.mark.parametrize("delimiter", ("=", ":"))
def test_reason_constructor_rejects_extended_dash_sensitive_assignment(
    separator: str,
    label: str,
    delimiter: str,
) -> None:
    value = f"{label}{separator}key{delimiter}PLAINTEXT-SECRET"

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(value)


@pytest.mark.parametrize("separator", _EXTENDED_DASH_VARIANTS)
@pytest.mark.parametrize("label", ("api", "private"))
def test_reason_revalidation_rejects_extended_dash_sensitive_assignment(
    separator: str,
    label: str,
) -> None:
    value = f"{label}{separator}key=PLAINTEXT-SECRET"
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


@pytest.mark.parametrize("separator", _EXTENDED_DASH_VARIANTS)
@pytest.mark.parametrize("field_name", ("source_name", "locator"))
def test_evidence_revalidation_rejects_extended_dash_sensitive_assignment(
    separator: str,
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
        f"private{separator}key=PLAINTEXT-SECRET",
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


@pytest.mark.parametrize("separator", _EXTENDED_DASH_VARIANTS)
def test_benign_extended_dash_text_is_retained_byte_for_byte(separator: str) -> None:
    value = f"Evidence{separator}reference"

    reason = registry.InstrumentUniverseReason(value)

    assert reason.logical_values() == (value,)
