from __future__ import annotations

from datetime import date

import pytest

import qore.infrastructure.instrument_universe_registry as registry

_EMBEDDED_URL_USERINFO = (
    "https://safe.example/https://alice:password@example.invalid/evidence"
)
_EMBEDDED_SCHEME_RELATIVE_USERINFO = (
    "Evidence //alice:password@example.invalid/evidence"
)
_CONFUSABLE_SLASH_INSIDE_USERINFO = (
    "https://alice:password∕foo@example.invalid/evidence"
)
_CONFUSABLE_SCHEME_AND_USERINFO_SLASH = (
    "https:∕∕alice:password∕foo@example.invalid/evidence"
)
_CONFUSABLE_SCHEME_RELATIVE_AND_USERINFO_SLASH = (
    "Evidence ∕∕alice:password∕foo@example.invalid/evidence"
)

_URL_USERINFO_WITNESSES = (
    _EMBEDDED_URL_USERINFO,
    _EMBEDDED_SCHEME_RELATIVE_USERINFO,
    _CONFUSABLE_SLASH_INSIDE_USERINFO,
    _CONFUSABLE_SCHEME_AND_USERINFO_SLASH,
    _CONFUSABLE_SCHEME_RELATIVE_AND_USERINFO_SLASH,
)


@pytest.mark.parametrize("value", _URL_USERINFO_WITNESSES)
def test_reason_constructor_rejects_embedded_url_userinfo(value: str) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseReason(value)


@pytest.mark.parametrize("value", _URL_USERINFO_WITNESSES)
def test_reason_revalidation_rejects_embedded_url_userinfo(value: str) -> None:
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


@pytest.mark.parametrize(
    "value",
    [
        _EMBEDDED_URL_USERINFO,
        _CONFUSABLE_SLASH_INSIDE_USERINFO,
        _CONFUSABLE_SCHEME_AND_USERINFO_SLASH,
    ],
)
@pytest.mark.parametrize("field_name", ["source_name", "locator"])
def test_evidence_record_constructor_rejects_later_url_userinfo(
    field_name: str,
    value: str,
) -> None:
    source_name = value if field_name == "source_name" else "QORE repository"
    locator = value if field_name == "locator" else "qore://umi-13/r9"

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseEvidenceRecord(
            evidence_ref=registry.InstrumentUniverseEvidenceRef("qore-umi13-r9"),
            source_category=(
                registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY
            ),
            source_name=source_name,
            locator=locator,
            verified_on=date(2026, 8, 31),
        )


@pytest.mark.parametrize(
    "value",
    [
        _EMBEDDED_URL_USERINFO,
        _CONFUSABLE_SLASH_INSIDE_USERINFO,
        _CONFUSABLE_SCHEME_AND_USERINFO_SLASH,
    ],
)
@pytest.mark.parametrize("field_name", ["source_name", "locator"])
def test_evidence_record_revalidation_rejects_later_url_userinfo(
    field_name: str,
    value: str,
) -> None:
    record = registry.InstrumentUniverseEvidenceRecord(
        evidence_ref=registry.InstrumentUniverseEvidenceRef("qore-umi13-r9"),
        source_category=registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY,
        source_name="QORE repository",
        locator="qore://umi-13/r9",
        verified_on=date(2026, 8, 31),
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


@pytest.mark.parametrize(
    "value",
    [
        "https://safe.example/path//nested/resource",
        "Contact alice@example.invalid for evidence",
        "https://safe.example/ https://other.example/evidence",
        "https://safe.example/path∕foo@example.invalid/evidence",
        "Evidence ∕∕nested/resource without userinfo",
    ],
)
def test_reason_preserves_benign_urlish_text(value: str) -> None:
    reason = registry.InstrumentUniverseReason(value)

    assert reason.logical_values() == (value,)
