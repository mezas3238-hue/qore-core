from __future__ import annotations

from datetime import date

import pytest

import qore.infrastructure.instrument_universe_registry as registry


class _DeceptiveLowerStr(str):
    def lower(self) -> str:
        return "safe"


@pytest.mark.parametrize(
    "unsafe_locator",
    [
        "https://official.example/?access_token=do-not-retain",
        "https://official.example/?access-token=do-not-retain",
        "https://official.example/?client_secret=do-not-retain",
        "https://official.example/?client-secret=do-not-retain",
        "https://official.example/?private_key=do-not-retain",
        "https://official.example/?private-key=do-not-retain",
        "https://official.example/?jwt=do-not-retain",
        "https://official.example/?credential=do-not-retain",
        "https://official.example/password:do-not-retain",
        "https://official.example/token:do-not-retain",
        "https://official.example/secret:do-not-retain",
        "https://user:password@official.example/evidence",
    ],
)
def test_evidence_locator_rejects_extended_credential_shapes(
    unsafe_locator: str,
) -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like",
    ):
        registry.InstrumentUniverseEvidenceRecord(
            evidence_ref=registry.InstrumentUniverseEvidenceRef("unsafe-evidence"),
            source_category=(
                registry.InstrumentUniverseEvidenceSourceCategory.REGULATORY_OFFICIAL
            ),
            source_name="Official source",
            locator=unsafe_locator,
            verified_on=date(2026, 8, 15),
        )


def test_credential_detection_is_case_insensitive() -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like",
    ):
        registry.InstrumentUniverseEvidenceRecord(
            evidence_ref=registry.InstrumentUniverseEvidenceRef("unsafe-evidence"),
            source_category=(
                registry.InstrumentUniverseEvidenceSourceCategory.REGULATORY_OFFICIAL
            ),
            source_name="Official source",
            locator="https://official.example/?Private_Key=do-not-retain",
            verified_on=date(2026, 8, 15),
        )


def test_evidence_text_rejects_control_characters() -> None:
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        registry.InstrumentUniverseEvidenceRecord(
            evidence_ref=registry.InstrumentUniverseEvidenceRef("unsafe-evidence"),
            source_category=(
                registry.InstrumentUniverseEvidenceSourceCategory.REGULATORY_OFFICIAL
            ),
            source_name="Official\nsource",
            locator="https://official.example/evidence",
            verified_on=date(2026, 8, 15),
        )


def test_reason_rejects_str_subclass_that_launders_lower() -> None:
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        registry.InstrumentUniverseReason(_DeceptiveLowerStr("token=do-not-retain"))


def test_evidence_locator_rejects_str_subclass_that_launders_lower() -> None:
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        registry.InstrumentUniverseEvidenceRecord(
            evidence_ref=registry.InstrumentUniverseEvidenceRef("unsafe-evidence"),
            source_category=(
                registry.InstrumentUniverseEvidenceSourceCategory.REGULATORY_OFFICIAL
            ),
            source_name="Official source",
            locator=_DeceptiveLowerStr(
                "https://user:password@official.example/evidence"
            ),
            verified_on=date(2026, 8, 15),
        )


def test_evidence_source_name_rejects_str_subclass() -> None:
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        registry.InstrumentUniverseEvidenceRecord(
            evidence_ref=registry.InstrumentUniverseEvidenceRef("unsafe-evidence"),
            source_category=(
                registry.InstrumentUniverseEvidenceSourceCategory.REGULATORY_OFFICIAL
            ),
            source_name=_DeceptiveLowerStr("Official source"),
            locator="https://official.example/evidence",
            verified_on=date(2026, 8, 15),
        )


def test_canonical_ref_rejects_str_subclass() -> None:
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        registry.InstrumentUniverseEvidenceRef(_DeceptiveLowerStr("unsafe-evidence"))


def test_plain_str_boundaries_remain_valid() -> None:
    reason = registry.InstrumentUniverseReason("Inventory qualification remains open")
    evidence = registry.InstrumentUniverseEvidenceRecord(
        evidence_ref=registry.InstrumentUniverseEvidenceRef("plain-evidence"),
        source_category=(
            registry.InstrumentUniverseEvidenceSourceCategory.REGULATORY_OFFICIAL
        ),
        source_name="Official source",
        locator="https://official.example/evidence",
        verified_on=date(2026, 8, 15),
    )

    assert type(reason.value) is str
    assert type(evidence.source_name) is str
    assert type(evidence.locator) is str


def test_owner_status_is_explicitly_non_self_certifying() -> None:
    owner_doc = registry.InstrumentUniverseOwnerStatus.__doc__ or ""
    snapshot_doc = registry.InstrumentUniverseRegistrySnapshot.__doc__ or ""

    assert "never authority proof" in owner_doc
    assert "never self-certifying authority" in snapshot_doc
