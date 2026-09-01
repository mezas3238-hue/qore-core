from __future__ import annotations

from datetime import date

import pytest

import qore.infrastructure.instrument_universe_registry as registry


_INVISIBLE_FILLERS = (
    "\u115f",  # HANGUL CHOSEONG FILLER
    "\u1160",  # HANGUL JUNGSEONG FILLER
    "\u3164",  # HANGUL FILLER -> U+1160 under NFKC
    "\uffa0",  # HALFWIDTH HANGUL FILLER -> U+1160 under NFKC
    "\u2800",  # BRAILLE PATTERN BLANK
)


@pytest.mark.parametrize("filler", _INVISIBLE_FILLERS)
def test_reason_constructor_rejects_invisible_filler_sensitive_assignment(
    filler: str,
) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(f"tok{filler}en=PLAINTEXT-SECRET")


@pytest.mark.parametrize("filler", _INVISIBLE_FILLERS)
def test_composite_sensitive_label_rejects_invisible_filler(filler: str) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(f"api{filler}key=PLAINTEXT-SECRET")


@pytest.mark.parametrize("filler", _INVISIBLE_FILLERS)
def test_reason_revalidation_rejects_invisible_filler_sensitive_assignment(
    filler: str,
) -> None:
    reason = registry.InstrumentUniverseReason("Safe retained reason")
    object.__setattr__(reason, "value", f"tok{filler}en=PLAINTEXT-SECRET")

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
@pytest.mark.parametrize("filler", _INVISIBLE_FILLERS)
def test_evidence_revalidation_rejects_invisible_filler_sensitive_assignment(
    field_name: str,
    filler: str,
) -> None:
    record = registry.InstrumentUniverseEvidenceRecord(
        evidence_ref=registry.InstrumentUniverseEvidenceRef("qore-umi05"),
        source_category=registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY,
        source_name="QORE repository",
        locator="qore://umi-05/futures",
        verified_on=date(2026, 8, 15),
    )
    object.__setattr__(record, field_name, f"tok{filler}en=PLAINTEXT-SECRET")

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


@pytest.mark.parametrize("filler", _INVISIBLE_FILLERS)
def test_benign_printable_filler_text_is_retained_byte_for_byte(filler: str) -> None:
    value = f"Evidence{filler}reference"

    reason = registry.InstrumentUniverseReason(value)

    assert reason.logical_values() == (value,)
