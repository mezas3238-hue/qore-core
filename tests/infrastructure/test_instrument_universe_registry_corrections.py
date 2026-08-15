from __future__ import annotations

from datetime import date
from typing import cast
from unittest.mock import Mock

import pytest

import qore.infrastructure.instrument_universe_registry as registry


class _DeceptiveLowerStr(str):
    def lower(self) -> str:
        return "safe"


class _BypassReason(registry.InstrumentUniverseReason):
    def __post_init__(self) -> None:
        pass


class _BypassEvidenceRef(registry.InstrumentUniverseEvidenceRef):
    def __post_init__(self) -> None:
        pass


class _BypassOwnerRef(registry.InstrumentUniverseOwnerRef):
    def __post_init__(self) -> None:
        pass


class _BypassSemanticRef(registry.InstrumentUniverseSemanticRef):
    def __post_init__(self) -> None:
        pass


class _BypassHashEvidenceRef(registry.InstrumentUniverseEvidenceRef):
    def __eq__(self, other: object) -> bool:
        return True

    def __hash__(self) -> int:
        return 0


class _BypassEntry(registry.InstrumentUniverseEntry):
    def __post_init__(self) -> None:
        pass


class _BypassEvidenceRecord(registry.InstrumentUniverseEvidenceRecord):
    def __post_init__(self) -> None:
        pass


def _valid_evidence() -> tuple[
    registry.InstrumentUniverseEvidenceRef,
    registry.InstrumentUniverseEvidenceRecord,
]:
    evidence_ref = registry.InstrumentUniverseEvidenceRef("qore-evidence")
    evidence = registry.InstrumentUniverseEvidenceRecord(
        evidence_ref=evidence_ref,
        source_category=registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY,
        source_name="QORE repository",
        locator="qore://umi-13/evidence",
        verified_on=date(2026, 8, 15),
    )
    return evidence_ref, evidence


def _valid_entry(
    *,
    family: registry.IdentityFamilyCode | None = None,
) -> registry.InstrumentUniverseEntry:
    evidence_ref, _ = _valid_evidence()
    return registry.InstrumentUniverseEntry(
        family=family or registry.IdentityFamilyCode("equities"),
        coverage_status=registry.InstrumentUniverseCoverageStatus.COVERED,
        owner_status=registry.InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
        owner_refs=(registry.InstrumentUniverseOwnerRef("umi-06"),),
        unresolved_semantics=(),
        evidence_refs=(evidence_ref,),
        reason=registry.InstrumentUniverseReason("Bounded equity semantics certified"),
    )


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
            source_name=_DeceptiveLowerStr("token=do-not-retain"),
            locator="https://official.example/evidence",
            verified_on=date(2026, 8, 15),
        )


def test_canonical_ref_rejects_str_subclass() -> None:
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        registry.InstrumentUniverseEvidenceRef(_DeceptiveLowerStr("unsafe-evidence"))


def test_entry_rejects_reason_subclass_that_skips_validation() -> None:
    evidence_ref, _ = _valid_evidence()
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        registry.InstrumentUniverseEntry(
            family=registry.IdentityFamilyCode("equities"),
            coverage_status=registry.InstrumentUniverseCoverageStatus.COVERED,
            owner_status=registry.InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
            owner_refs=(registry.InstrumentUniverseOwnerRef("umi-06"),),
            unresolved_semantics=(),
            evidence_refs=(evidence_ref,),
            reason=_BypassReason("token=do-not-retain"),
        )


def test_evidence_record_rejects_evidence_ref_subclass() -> None:
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        registry.InstrumentUniverseEvidenceRecord(
            evidence_ref=_BypassEvidenceRef("NOT CANONICAL"),
            source_category=registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY,
            source_name="QORE repository",
            locator="qore://umi-13/evidence",
            verified_on=date(2026, 8, 15),
        )


def test_entry_rejects_owner_and_semantic_ref_subclasses() -> None:
    evidence_ref, _ = _valid_evidence()
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        registry.InstrumentUniverseEntry(
            family=registry.IdentityFamilyCode("equities"),
            coverage_status=registry.InstrumentUniverseCoverageStatus.COVERED,
            owner_status=registry.InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
            owner_refs=(_BypassOwnerRef("umi-06"),),
            unresolved_semantics=(),
            evidence_refs=(evidence_ref,),
            reason=registry.InstrumentUniverseReason("Bounded equity semantics certified"),
        )
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        registry.InstrumentUniverseEntry(
            family=registry.IdentityFamilyCode("equities"),
            coverage_status=registry.InstrumentUniverseCoverageStatus.PARTIAL,
            owner_status=registry.InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
            owner_refs=(registry.InstrumentUniverseOwnerRef("umi-06"),),
            unresolved_semantics=(_BypassSemanticRef("umi13-unr-023"),),
            evidence_refs=(evidence_ref,),
            reason=registry.InstrumentUniverseReason("Qualification remains open"),
        )


def test_entry_rejects_custom_hash_evidence_ref_subclass_before_uniqueness() -> None:
    ref = _BypassHashEvidenceRef("qore-evidence")
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        registry.InstrumentUniverseEntry(
            family=registry.IdentityFamilyCode("equities"),
            coverage_status=registry.InstrumentUniverseCoverageStatus.COVERED,
            owner_status=registry.InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
            owner_refs=(registry.InstrumentUniverseOwnerRef("umi-06"),),
            unresolved_semantics=(),
            evidence_refs=(ref, ref),
            reason=registry.InstrumentUniverseReason("Bounded equity semantics certified"),
        )


def test_snapshot_rejects_entry_subclass_that_skips_invariants() -> None:
    evidence_ref, evidence = _valid_evidence()
    bypass_entry = _BypassEntry(
        family=registry.IdentityFamilyCode("equities"),
        coverage_status=registry.InstrumentUniverseCoverageStatus.COVERED,
        owner_status=registry.InstrumentUniverseOwnerStatus.NO_CERTIFIED_OWNER,
        owner_refs=(),
        unresolved_semantics=(),
        evidence_refs=(evidence_ref,),
        reason=registry.InstrumentUniverseReason("Bypassed entry"),
    )
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        registry.InstrumentUniverseRegistrySnapshot(
            as_of=date(2026, 8, 15),
            revision=1,
            entries=(bypass_entry,),
            evidence=(evidence,),
        )


def test_snapshot_rejects_evidence_record_subclass() -> None:
    evidence_ref, _ = _valid_evidence()
    entry = _valid_entry()
    bypass_evidence = _BypassEvidenceRecord(
        evidence_ref=evidence_ref,
        source_category=registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY,
        source_name="QORE repository",
        locator="qore://umi-13/evidence",
        verified_on=date(2026, 8, 15),
    )
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        registry.InstrumentUniverseRegistrySnapshot(
            as_of=date(2026, 8, 15),
            revision=1,
            entries=(entry,),
            evidence=(bypass_evidence,),
        )


def test_entry_and_lookup_reject_identity_family_with_str_subclass_value() -> None:
    unsafe_family = registry.IdentityFamilyCode(_DeceptiveLowerStr("equities"))
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        _valid_entry(family=unsafe_family)

    evidence_ref, evidence = _valid_evidence()
    entry = _valid_entry()
    snapshot = registry.InstrumentUniverseRegistrySnapshot(
        as_of=date(2026, 8, 15),
        revision=1,
        entries=(entry,),
        evidence=(evidence,),
    )
    assert entry.evidence_refs == (evidence_ref,)
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        snapshot.entry_for_family(unsafe_family)


def test_mock_spec_enums_cannot_launder_isinstance_boundaries() -> None:
    evidence_ref, _ = _valid_evidence()
    fake_source = cast(
        registry.InstrumentUniverseEvidenceSourceCategory,
        Mock(spec=registry.InstrumentUniverseEvidenceSourceCategory),
    )
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        registry.InstrumentUniverseEvidenceRecord(
            evidence_ref=evidence_ref,
            source_category=fake_source,
            source_name="QORE repository",
            locator="qore://umi-13/evidence",
            verified_on=date(2026, 8, 15),
        )

    fake_coverage = cast(
        registry.InstrumentUniverseCoverageStatus,
        Mock(spec=registry.InstrumentUniverseCoverageStatus),
    )
    fake_owner = cast(
        registry.InstrumentUniverseOwnerStatus,
        Mock(spec=registry.InstrumentUniverseOwnerStatus),
    )
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        registry.InstrumentUniverseEntry(
            family=registry.IdentityFamilyCode("equities"),
            coverage_status=fake_coverage,
            owner_status=registry.InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
            owner_refs=(registry.InstrumentUniverseOwnerRef("umi-06"),),
            unresolved_semantics=(),
            evidence_refs=(evidence_ref,),
            reason=registry.InstrumentUniverseReason("Bounded equity semantics certified"),
        )
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        registry.InstrumentUniverseEntry(
            family=registry.IdentityFamilyCode("equities"),
            coverage_status=registry.InstrumentUniverseCoverageStatus.COVERED,
            owner_status=fake_owner,
            owner_refs=(),
            unresolved_semantics=(),
            evidence_refs=(evidence_ref,),
            reason=registry.InstrumentUniverseReason("Bounded equity semantics certified"),
        )


def test_plain_str_and_exact_nested_boundaries_remain_valid() -> None:
    evidence_ref, evidence = _valid_evidence()
    entry = _valid_entry()
    snapshot = registry.InstrumentUniverseRegistrySnapshot(
        as_of=date(2026, 8, 15),
        revision=1,
        entries=(entry,),
        evidence=(evidence,),
    )

    assert type(entry.reason.value) is str
    assert type(evidence.source_name) is str
    assert type(evidence.locator) is str
    assert snapshot.entry_for_family(registry.IdentityFamilyCode("equities")) == entry
    assert entry.evidence_refs == (evidence_ref,)


def test_owner_status_is_explicitly_non_self_certifying() -> None:
    owner_doc = registry.InstrumentUniverseOwnerStatus.__doc__ or ""
    snapshot_doc = registry.InstrumentUniverseRegistrySnapshot.__doc__ or ""

    assert "never authority proof" in owner_doc
    assert "never self-certifying authority" in snapshot_doc
