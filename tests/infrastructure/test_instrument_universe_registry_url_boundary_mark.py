from __future__ import annotations

from datetime import date

import pytest

import qore.infrastructure.instrument_universe_registry as registry

# Printable non-alphanumeric/non-slash combining marks already accepted by the
# text contract. Each is printable (passes isprintable()) yet is deleted by the
# general credential skeleton's mark filter. R19 root-cause family: deleting
# such a mark immediately before a scheme-relative "//" authority start erases
# the real token boundary and lets an alphanumeric prefix concatenate with the
# "//", defeating the negative-lookbehind boundary guard.
_PRINTABLE_MARKS = (
    "\ufe0f",  # VARIATION SELECTOR-16 (Mn)
    "\u034f",  # COMBINING GRAPHEME JOINER (Mn)
    "\u0301",  # COMBINING ACUTE ACCENT (Mn)
    "\u0327",  # COMBINING CEDILLA (Mn)
    "\u0903",  # DEVANAGARI SIGN VISARGA (Mc)
    "\u20dd",  # COMBINING ENCLOSING CIRCLE (Me)
    "\u20e3",  # COMBINING ENCLOSING KEYCAP (Me)
)

_SCHEME_RELATIVE_MARK_WITNESSES = tuple(
    f"Evidence{mark}//alice:password@example.invalid/evidence"
    for mark in _PRINTABLE_MARKS
)
_ALNUM_PREFIX_MARK_WITNESSES = tuple(
    f"abc{mark}//user@host" for mark in _PRINTABLE_MARKS
)
_MARK_BETWEEN_AUTHORITY_SLASHES = tuple(
    f"/{mark}/user@host" for mark in _PRINTABLE_MARKS
)
_MARK_INSIDE_USERINFO = tuple(
    f"//us{mark}er@host" for mark in _PRINTABLE_MARKS
)
_MARK_INSIDE_SCHEME = tuple(
    f"http{mark}s://user@host" for mark in _PRINTABLE_MARKS
)
_MULTI_AUTHORITY_MARK = tuple(
    f"https://safe.example/Evidence{mark}//alice:password@example.invalid/evidence"
    for mark in _PRINTABLE_MARKS
)


@pytest.mark.parametrize("value", _SCHEME_RELATIVE_MARK_WITNESSES)
def test_reason_constructor_rejects_mark_boundary_scheme_relative_userinfo(
    value: str,
) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(value)


@pytest.mark.parametrize("value", _ALNUM_PREFIX_MARK_WITNESSES)
def test_reason_constructor_rejects_alnum_prefix_mark_userinfo(value: str) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(value)


@pytest.mark.parametrize("value", _SCHEME_RELATIVE_MARK_WITNESSES)
def test_reason_revalidation_rejects_mark_boundary_userinfo(value: str) -> None:
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
@pytest.mark.parametrize("value", _SCHEME_RELATIVE_MARK_WITNESSES)
def test_evidence_record_constructor_rejects_mark_boundary_userinfo(
    field_name: str,
    value: str,
) -> None:
    source_name = value if field_name == "source_name" else "QORE repository"
    locator = value if field_name == "locator" else "qore://umi-13/r19"

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseEvidenceRecord(
            evidence_ref=registry.InstrumentUniverseEvidenceRef("qore-umi13-r19"),
            source_category=(
                registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY
            ),
            source_name=source_name,
            locator=locator,
            verified_on=date(2026, 9, 1),
        )


@pytest.mark.parametrize("field_name", ("source_name", "locator"))
@pytest.mark.parametrize("value", _SCHEME_RELATIVE_MARK_WITNESSES)
def test_evidence_record_revalidation_rejects_mark_boundary_userinfo(
    field_name: str,
    value: str,
) -> None:
    record = registry.InstrumentUniverseEvidenceRecord(
        evidence_ref=registry.InstrumentUniverseEvidenceRef("qore-umi13-r19"),
        source_category=registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY,
        source_name="QORE repository",
        locator="qore://umi-13/r19",
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


@pytest.mark.parametrize("value", _MARK_BETWEEN_AUTHORITY_SLASHES)
def test_reason_constructor_rejects_mark_between_authority_slashes(
    value: str,
) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(value)


@pytest.mark.parametrize("value", _MARK_INSIDE_USERINFO)
def test_reason_constructor_rejects_mark_inside_userinfo(value: str) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(value)


@pytest.mark.parametrize("value", _MARK_INSIDE_SCHEME)
def test_reason_constructor_rejects_mark_inside_scheme(value: str) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(value)


@pytest.mark.parametrize("value", _MULTI_AUTHORITY_MARK)
def test_reason_constructor_rejects_multi_authority_mark_boundary(value: str) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(value)


@pytest.mark.parametrize("mark", _PRINTABLE_MARKS)
def test_general_skeleton_still_rejects_mark_inside_sensitive_label(
    mark: str,
) -> None:
    # The general credential skeleton must keep removing marks so a printable
    # mark obfuscating a sensitive label (e.g. token<mark>=...) stays rejected.
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(f"token{mark}=PLAINTEXT-SECRET")


@pytest.mark.parametrize("mark", _PRINTABLE_MARKS)
def test_benign_mark_outside_url_pattern_is_retained_byte_for_byte(
    mark: str,
) -> None:
    value = f"Evidence{mark}reference"

    reason = registry.InstrumentUniverseReason(value)

    assert reason.logical_values() == (value,)


@pytest.mark.parametrize("mark", _PRINTABLE_MARKS)
def test_benign_mark_before_path_without_userinfo_is_retained(mark: str) -> None:
    value = f"Evidence{mark}//nested/resource"

    reason = registry.InstrumentUniverseReason(value)

    assert reason.logical_values() == (value,)


@pytest.mark.parametrize("mark", _PRINTABLE_MARKS)
def test_benign_mark_in_urlish_path_is_retained(mark: str) -> None:
    value = f"https://safe.example/path{mark}//nested/resource"

    reason = registry.InstrumentUniverseReason(value)

    assert reason.logical_values() == (value,)


@pytest.mark.parametrize("mark", _PRINTABLE_MARKS)
def test_benign_mark_inside_non_credential_text_is_retained(mark: str) -> None:
    value = f"Cafe{mark} evidence reference"

    reason = registry.InstrumentUniverseReason(value)

    assert reason.logical_values() == (value,)
