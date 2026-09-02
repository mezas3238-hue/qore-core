from __future__ import annotations

from datetime import date

import pytest

import qore.infrastructure.instrument_universe_registry as registry

# Printable invisible fillers already accepted by the text contract. Each is
# printable (passes isprintable()) yet renders invisibly, so it can act as a
# detection-only token boundary before a scheme-relative "//" authority start.
_INVISIBLE_FILLERS = (
    "\u115f",  # HANGUL CHOSEONG FILLER
    "\u1160",  # HANGUL JUNGSEONG FILLER
    "\u3164",  # HANGUL FILLER -> U+1160 under NFKC
    "\uffa0",  # HALFWIDTH HANGUL FILLER -> U+1160 under NFKC
    "\u2800",  # BRAILLE PATTERN BLANK
)

# R18B root-cause witness: a filler boundary directly before a scheme-relative
# authority. Removing the filler would concatenate the alphanumeric prefix with
# the "//" start and defeat the negative-lookbehind boundary guard.
_SCHEME_RELATIVE_FILLER_WITNESSES = tuple(
    f"Evidence{filler}//alice:password@example.invalid/evidence"
    for filler in _INVISIBLE_FILLERS
)
_ALNUM_PREFIX_FILLER_WITNESSES = tuple(
    f"abc{filler}//user@host" for filler in _INVISIBLE_FILLERS
)
_FILLER_BETWEEN_AUTHORITY_SLASHES = tuple(
    f"/{filler}/user@host" for filler in _INVISIBLE_FILLERS
)
_FILLER_INSIDE_USERINFO = tuple(
    f"//us{filler}er@host" for filler in _INVISIBLE_FILLERS
)
_FILLER_INSIDE_SCHEME = tuple(
    f"http{filler}s://user@host" for filler in _INVISIBLE_FILLERS
)
_MULTI_AUTHORITY_FILLER = tuple(
    f"https://safe.example/Evidence{filler}//alice:password@example.invalid/evidence"
    for filler in _INVISIBLE_FILLERS
)


@pytest.mark.parametrize("value", _SCHEME_RELATIVE_FILLER_WITNESSES)
def test_reason_constructor_rejects_filler_boundary_scheme_relative_userinfo(
    value: str,
) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(value)


@pytest.mark.parametrize("value", _ALNUM_PREFIX_FILLER_WITNESSES)
def test_reason_constructor_rejects_alnum_prefix_filler_userinfo(value: str) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(value)


@pytest.mark.parametrize("value", _SCHEME_RELATIVE_FILLER_WITNESSES)
def test_reason_revalidation_rejects_filler_boundary_userinfo(value: str) -> None:
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
@pytest.mark.parametrize("value", _SCHEME_RELATIVE_FILLER_WITNESSES)
def test_evidence_record_constructor_rejects_filler_boundary_userinfo(
    field_name: str,
    value: str,
) -> None:
    source_name = value if field_name == "source_name" else "QORE repository"
    locator = value if field_name == "locator" else "qore://umi-13/r18b"

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseEvidenceRecord(
            evidence_ref=registry.InstrumentUniverseEvidenceRef("qore-umi13-r18b"),
            source_category=(
                registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY
            ),
            source_name=source_name,
            locator=locator,
            verified_on=date(2026, 9, 1),
        )


@pytest.mark.parametrize("field_name", ("source_name", "locator"))
@pytest.mark.parametrize("value", _SCHEME_RELATIVE_FILLER_WITNESSES)
def test_evidence_record_revalidation_rejects_filler_boundary_userinfo(
    field_name: str,
    value: str,
) -> None:
    record = registry.InstrumentUniverseEvidenceRecord(
        evidence_ref=registry.InstrumentUniverseEvidenceRef("qore-umi13-r18b"),
        source_category=registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY,
        source_name="QORE repository",
        locator="qore://umi-13/r18b",
        verified_on=date(2026, 9, 1),
    )
    object.__setattr__(record, field_name, value)

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


@pytest.mark.parametrize("value", _FILLER_BETWEEN_AUTHORITY_SLASHES)
def test_reason_constructor_rejects_filler_between_authority_slashes(
    value: str,
) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(value)


@pytest.mark.parametrize("value", _FILLER_INSIDE_USERINFO)
def test_reason_constructor_rejects_filler_inside_userinfo(value: str) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(value)


@pytest.mark.parametrize("value", _FILLER_INSIDE_SCHEME)
def test_reason_constructor_rejects_filler_inside_scheme(value: str) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(value)


@pytest.mark.parametrize("value", _MULTI_AUTHORITY_FILLER)
def test_reason_constructor_rejects_multi_authority_filler_boundary(value: str) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(value)


@pytest.mark.parametrize("filler", _INVISIBLE_FILLERS)
def test_benign_filler_outside_url_pattern_is_retained_byte_for_byte(
    filler: str,
) -> None:
    value = f"Evidence{filler}reference"

    reason = registry.InstrumentUniverseReason(value)

    assert reason.logical_values() == (value,)


@pytest.mark.parametrize("filler", _INVISIBLE_FILLERS)
def test_benign_filler_before_path_without_userinfo_is_retained(filler: str) -> None:
    value = f"Evidence{filler}//nested/resource"

    reason = registry.InstrumentUniverseReason(value)

    assert reason.logical_values() == (value,)


@pytest.mark.parametrize("filler", _INVISIBLE_FILLERS)
def test_benign_filler_in_urlish_path_is_retained(filler: str) -> None:
    value = f"https://safe.example/path{filler}//nested/resource"

    reason = registry.InstrumentUniverseReason(value)

    assert reason.logical_values() == (value,)
