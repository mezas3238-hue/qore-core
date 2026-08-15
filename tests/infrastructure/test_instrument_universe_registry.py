from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from typing import cast

import pytest

from qore.infrastructure.instrument_universe_registry import (
    InstrumentUniverseCoverageStatus,
    InstrumentUniverseEntry,
    InstrumentUniverseEvidenceRecord,
    InstrumentUniverseEvidenceRef,
    InstrumentUniverseEvidenceSourceCategory,
    InstrumentUniverseOwnerRef,
    InstrumentUniverseOwnerStatus,
    InstrumentUniverseReason,
    InstrumentUniverseRegistrySnapshot,
    InstrumentUniverseRegistryValidationError,
    InstrumentUniverseSemanticRef,
)
from qore.infrastructure.universal_instrument_identity import IdentityFamilyCode


SNAPSHOT_DATE = date(2026, 8, 15)


def _evidence(
    value: str,
    *,
    category: InstrumentUniverseEvidenceSourceCategory = (
        InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY
    ),
    source_name: str = "QORE repository",
    locator: str | None = None,
    verified_on: date = SNAPSHOT_DATE,
) -> InstrumentUniverseEvidenceRecord:
    return InstrumentUniverseEvidenceRecord(
        evidence_ref=InstrumentUniverseEvidenceRef(value),
        source_category=category,
        source_name=source_name,
        locator=locator or f"github://mezas3238-hue/qore-core/{value}",
        verified_on=verified_on,
    )


def _entry(
    family: str = "futures",
    *,
    coverage: InstrumentUniverseCoverageStatus = InstrumentUniverseCoverageStatus.COVERED,
    owner_status: InstrumentUniverseOwnerStatus = (
        InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT
    ),
    owner_values: tuple[str, ...] = ("umi-05.derivatives",),
    unresolved_values: tuple[str, ...] = (),
    evidence_values: tuple[str, ...] = ("qore-umi05",),
    reason: str = "Bounded semantic coverage exists at the retained repository baseline.",
) -> InstrumentUniverseEntry:
    return InstrumentUniverseEntry(
        family=IdentityFamilyCode(family),
        coverage_status=coverage,
        owner_status=owner_status,
        owner_refs=tuple(InstrumentUniverseOwnerRef(value) for value in owner_values),
        unresolved_semantics=tuple(
            InstrumentUniverseSemanticRef(value) for value in unresolved_values
        ),
        evidence_refs=tuple(
            InstrumentUniverseEvidenceRef(value) for value in evidence_values
        ),
        reason=InstrumentUniverseReason(reason),
    )


def _snapshot(
    *,
    entries: tuple[InstrumentUniverseEntry, ...] | None = None,
    evidence: tuple[InstrumentUniverseEvidenceRecord, ...] | None = None,
    as_of: date = SNAPSHOT_DATE,
    revision: int = 1,
) -> InstrumentUniverseRegistrySnapshot:
    return InstrumentUniverseRegistrySnapshot(
        as_of=as_of,
        revision=revision,
        entries=entries or (_entry(),),
        evidence=evidence or (_evidence("qore-umi05"),),
    )


def test_snapshot_canonicalizes_entries_evidence_and_lookup() -> None:
    partial = _entry(
        "options",
        coverage=InstrumentUniverseCoverageStatus.PARTIAL,
        owner_status=InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
        owner_values=("umi-09.structured", "umi-05.derivatives"),
        unresolved_values=("barrier-payoff", "digital-payoff"),
        evidence_values=("external-fpml", "qore-umi05"),
        reason="Vanilla terms exist while exotic payoff semantics remain unresolved.",
    )
    covered = _entry()
    external = _evidence(
        "external-fpml",
        category=InstrumentUniverseEvidenceSourceCategory.STANDARDS_INDUSTRY_BODY,
        source_name="ISDA FpML",
        locator="https://www.fpml.org/about/product-summary/",
    )
    qore = _evidence("qore-umi05")

    snapshot = _snapshot(
        entries=(partial, covered),
        evidence=(qore, external),
    )

    assert tuple(entry.family.value for entry in snapshot.entries) == (
        "futures",
        "options",
    )
    assert tuple(record.evidence_ref.value for record in snapshot.evidence) == (
        "external-fpml",
        "qore-umi05",
    )
    assert snapshot.entry_for_family(IdentityFamilyCode("options")) == partial
    assert partial.owner_refs == (
        InstrumentUniverseOwnerRef("umi-05.derivatives"),
        InstrumentUniverseOwnerRef("umi-09.structured"),
    )
    assert partial.unresolved_semantics == (
        InstrumentUniverseSemanticRef("barrier-payoff"),
        InstrumentUniverseSemanticRef("digital-payoff"),
    )
    assert partial.evidence_refs == (
        InstrumentUniverseEvidenceRef("external-fpml"),
        InstrumentUniverseEvidenceRef("qore-umi05"),
    )


def test_logical_values_are_order_insensitive_after_canonicalization() -> None:
    entry_a = _entry(
        "options",
        coverage=InstrumentUniverseCoverageStatus.PARTIAL,
        owner_values=("umi-09.structured", "umi-05.derivatives"),
        unresolved_values=("digital-payoff", "barrier-payoff"),
        evidence_values=("qore-umi05", "external-fpml"),
    )
    entry_b = _entry(
        "options",
        coverage=InstrumentUniverseCoverageStatus.PARTIAL,
        owner_values=("umi-05.derivatives", "umi-09.structured"),
        unresolved_values=("barrier-payoff", "digital-payoff"),
        evidence_values=("external-fpml", "qore-umi05"),
    )
    external = _evidence(
        "external-fpml",
        category=InstrumentUniverseEvidenceSourceCategory.STANDARDS_INDUSTRY_BODY,
        source_name="ISDA FpML",
        locator="https://www.fpml.org/about/product-summary/",
    )
    qore = _evidence("qore-umi05")

    snapshot_a = _snapshot(entries=(entry_a,), evidence=(qore, external))
    snapshot_b = _snapshot(entries=(entry_b,), evidence=(external, qore))

    assert snapshot_a.logical_values() == snapshot_b.logical_values()


@pytest.mark.parametrize(
    ("as_of", "revision"),
    [
        (cast(date, datetime(2026, 8, 15, tzinfo=UTC)), 1),
        (SNAPSHOT_DATE, 0),
        (SNAPSHOT_DATE, -1),
        (SNAPSHOT_DATE, cast(int, True)),
    ],
)
def test_snapshot_requires_exact_date_and_positive_strict_revision(
    as_of: date,
    revision: int,
) -> None:
    with pytest.raises(InstrumentUniverseRegistryValidationError):
        _snapshot(as_of=as_of, revision=revision)


def test_duplicate_family_conflict_fails_deterministically() -> None:
    first = _entry()
    second = _entry(
        coverage=InstrumentUniverseCoverageStatus.PARTIAL,
        unresolved_values=("specialized-future",),
        reason="Conflicting duplicate row must not be accepted.",
    )

    with pytest.raises(
        InstrumentUniverseRegistryValidationError,
        match="family may appear only once",
    ):
        _snapshot(entries=(first, second))


def test_duplicate_evidence_reference_and_duplicate_content_are_rejected() -> None:
    duplicate_ref_a = _evidence("qore-umi05")
    duplicate_ref_b = _evidence(
        "qore-umi05",
        source_name="Different source label",
        locator="github://different/location",
    )
    with pytest.raises(
        InstrumentUniverseRegistryValidationError,
        match="evidence references must be unique",
    ):
        _snapshot(evidence=(duplicate_ref_a, duplicate_ref_b))

    duplicate_content_a = _evidence("qore-a")
    duplicate_content_b = _evidence("qore-b")
    entry = _entry(evidence_values=("qore-a", "qore-b"))
    with pytest.raises(
        InstrumentUniverseRegistryValidationError,
        match="duplicate evidence content",
    ):
        _snapshot(entries=(entry,), evidence=(duplicate_content_a, duplicate_content_b))


def test_dangling_and_orphan_evidence_are_rejected() -> None:
    dangling = _entry(evidence_values=("missing-evidence",))
    with pytest.raises(
        InstrumentUniverseRegistryValidationError,
        match="dangling evidence",
    ):
        _snapshot(entries=(dangling,), evidence=(_evidence("qore-umi05"),))

    orphan = _evidence(
        "external-unused",
        category=InstrumentUniverseEvidenceSourceCategory.REGULATORY_OFFICIAL,
        source_name="Official source",
        locator="https://example.invalid/official-source",
    )
    with pytest.raises(
        InstrumentUniverseRegistryValidationError,
        match="must all be referenced",
    ):
        _snapshot(evidence=(_evidence("qore-umi05"), orphan))


def test_evidence_verified_after_snapshot_is_rejected() -> None:
    future_evidence = _evidence(
        "qore-umi05",
        verified_on=date(2026, 8, 16),
    )
    with pytest.raises(
        InstrumentUniverseRegistryValidationError,
        match="after snapshot",
    ):
        _snapshot(evidence=(future_evidence,))


@pytest.mark.parametrize(
    "coverage",
    [
        InstrumentUniverseCoverageStatus.COVERED,
        InstrumentUniverseCoverageStatus.PARTIAL,
    ],
)
def test_external_evidence_alone_cannot_establish_qore_semantic_coverage(
    coverage: InstrumentUniverseCoverageStatus,
) -> None:
    unresolved = (
        ("unresolved-variant",)
        if coverage is InstrumentUniverseCoverageStatus.PARTIAL
        else ()
    )
    entry = _entry(
        coverage=coverage,
        unresolved_values=unresolved,
        evidence_values=("provider-official",),
    )
    provider_evidence = _evidence(
        "provider-official",
        category=InstrumentUniverseEvidenceSourceCategory.PROVIDER_PLATFORM_OFFICIAL,
        source_name="Provider documentation",
        locator="https://provider.example/instruments",
    )

    with pytest.raises(
        InstrumentUniverseRegistryValidationError,
        match="requires retained QORE repository evidence",
    ):
        _snapshot(entries=(entry,), evidence=(provider_evidence,))


def test_partial_coverage_cannot_drop_unresolved_semantics() -> None:
    with pytest.raises(
        InstrumentUniverseRegistryValidationError,
        match="partial family must retain unresolved semantics",
    ):
        _entry(
            coverage=InstrumentUniverseCoverageStatus.PARTIAL,
            unresolved_values=(),
        )


def test_covered_family_cannot_hide_unresolved_semantics() -> None:
    with pytest.raises(
        InstrumentUniverseRegistryValidationError,
        match="covered family must not retain unresolved semantics",
    ):
        _entry(unresolved_values=("hidden-gap",))


@pytest.mark.parametrize(
    ("coverage", "owner_status", "owner_values", "unresolved_values"),
    [
        (
            InstrumentUniverseCoverageStatus.COVERED,
            InstrumentUniverseOwnerStatus.PARTIAL_CONTRACT,
            ("umi-05.derivatives",),
            (),
        ),
        (
            InstrumentUniverseCoverageStatus.PARTIAL,
            InstrumentUniverseOwnerStatus.NO_CERTIFIED_OWNER,
            (),
            ("gap",),
        ),
        (
            InstrumentUniverseCoverageStatus.UNRESOLVED,
            InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
            ("umi-05.derivatives",),
            ("gap",),
        ),
        (
            InstrumentUniverseCoverageStatus.DEFERRED,
            InstrumentUniverseOwnerStatus.PARTIAL_CONTRACT,
            ("umi-05.derivatives",),
            ("gap",),
        ),
        (
            InstrumentUniverseCoverageStatus.EXCLUDED,
            InstrumentUniverseOwnerStatus.NO_CERTIFIED_OWNER,
            (),
            (),
        ),
    ],
)
def test_conflicting_coverage_owner_status_combinations_fail(
    coverage: InstrumentUniverseCoverageStatus,
    owner_status: InstrumentUniverseOwnerStatus,
    owner_values: tuple[str, ...],
    unresolved_values: tuple[str, ...],
) -> None:
    with pytest.raises(InstrumentUniverseRegistryValidationError):
        _entry(
            coverage=coverage,
            owner_status=owner_status,
            owner_values=owner_values,
            unresolved_values=unresolved_values,
        )


def test_unresolved_deferred_and_excluded_have_bounded_valid_shapes() -> None:
    unresolved = _entry(
        "securities-financing",
        coverage=InstrumentUniverseCoverageStatus.UNRESOLVED,
        owner_status=InstrumentUniverseOwnerStatus.NO_CERTIFIED_OWNER,
        owner_values=(),
        unresolved_values=("repo-terms", "securities-lending-terms"),
        evidence_values=("external-fsb",),
        reason="No certified D04 semantic owner exists for SFT terms at this snapshot.",
    )
    deferred = _entry(
        "event-contracts",
        coverage=InstrumentUniverseCoverageStatus.DEFERRED,
        owner_status=InstrumentUniverseOwnerStatus.NO_CERTIFIED_OWNER,
        owner_values=(),
        unresolved_values=("event-resolution",),
        evidence_values=("external-cftc",),
        reason="Material family discovered; implementation belongs to a later owner slice.",
    )
    excluded = _entry(
        "out-of-scope-example",
        coverage=InstrumentUniverseCoverageStatus.EXCLUDED,
        owner_status=InstrumentUniverseOwnerStatus.NOT_APPLICABLE,
        owner_values=(),
        unresolved_values=(),
        evidence_values=("external-official",),
        reason="Governed evidence demonstrates this row is outside UMI scope.",
    )
    evidence = (
        _evidence(
            "external-fsb",
            category=InstrumentUniverseEvidenceSourceCategory.REGULATORY_OFFICIAL,
            source_name="FSB",
            locator="https://www.fsb.org/securities-financing/",
        ),
        _evidence(
            "external-cftc",
            category=InstrumentUniverseEvidenceSourceCategory.REGULATORY_OFFICIAL,
            source_name="CFTC",
            locator="https://www.cftc.gov/event-contracts/",
        ),
        _evidence(
            "external-official",
            category=InstrumentUniverseEvidenceSourceCategory.REGULATORY_OFFICIAL,
            source_name="Official evidence",
            locator="https://example.invalid/exclusion-evidence",
        ),
    )

    snapshot = _snapshot(
        entries=(excluded, unresolved, deferred),
        evidence=evidence,
    )

    assert snapshot.entry_for_family(
        IdentityFamilyCode("securities-financing")
    ).coverage_status is InstrumentUniverseCoverageStatus.UNRESOLVED
    assert snapshot.entry_for_family(
        IdentityFamilyCode("event-contracts")
    ).coverage_status is InstrumentUniverseCoverageStatus.DEFERRED


def test_owner_presence_rules_fail_closed() -> None:
    with pytest.raises(
        InstrumentUniverseRegistryValidationError,
        match="requires explicit owner_refs",
    ):
        _entry(owner_values=())

    with pytest.raises(
        InstrumentUniverseRegistryValidationError,
        match="must not retain owner_refs",
    ):
        _entry(
            coverage=InstrumentUniverseCoverageStatus.UNRESOLVED,
            owner_status=InstrumentUniverseOwnerStatus.NO_CERTIFIED_OWNER,
            owner_values=("unsafe-owner",),
            unresolved_values=("gap",),
        )


def test_duplicate_entry_refs_fail_before_canonicalization() -> None:
    duplicate_owner = InstrumentUniverseOwnerRef("umi-05.derivatives")
    with pytest.raises(
        InstrumentUniverseRegistryValidationError,
        match="owner_refs must be unique",
    ):
        InstrumentUniverseEntry(
            family=IdentityFamilyCode("options"),
            coverage_status=InstrumentUniverseCoverageStatus.PARTIAL,
            owner_status=InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
            owner_refs=(duplicate_owner, duplicate_owner),
            unresolved_semantics=(InstrumentUniverseSemanticRef("gap"),),
            evidence_refs=(InstrumentUniverseEvidenceRef("qore-umi05"),),
            reason=InstrumentUniverseReason("Duplicate owners must fail."),
        )

    duplicate_semantic = InstrumentUniverseSemanticRef("gap")
    with pytest.raises(
        InstrumentUniverseRegistryValidationError,
        match="unresolved_semantics must be unique",
    ):
        InstrumentUniverseEntry(
            family=IdentityFamilyCode("options"),
            coverage_status=InstrumentUniverseCoverageStatus.PARTIAL,
            owner_status=InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
            owner_refs=(InstrumentUniverseOwnerRef("umi-05.derivatives"),),
            unresolved_semantics=(duplicate_semantic, duplicate_semantic),
            evidence_refs=(InstrumentUniverseEvidenceRef("qore-umi05"),),
            reason=InstrumentUniverseReason("Duplicate semantics must fail."),
        )

    duplicate_evidence = InstrumentUniverseEvidenceRef("qore-umi05")
    with pytest.raises(
        InstrumentUniverseRegistryValidationError,
        match="evidence_refs must be unique",
    ):
        InstrumentUniverseEntry(
            family=IdentityFamilyCode("options"),
            coverage_status=InstrumentUniverseCoverageStatus.PARTIAL,
            owner_status=InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
            owner_refs=(InstrumentUniverseOwnerRef("umi-05.derivatives"),),
            unresolved_semantics=(InstrumentUniverseSemanticRef("gap"),),
            evidence_refs=(duplicate_evidence, duplicate_evidence),
            reason=InstrumentUniverseReason("Duplicate evidence refs must fail."),
        )


def test_evidence_and_reason_reject_credential_like_or_non_normalized_text() -> None:
    with pytest.raises(
        InstrumentUniverseRegistryValidationError,
        match="credential-like",
    ):
        _evidence(
            "unsafe-evidence",
            locator="https://official.example/?token=do-not-retain",
        )

    with pytest.raises(InstrumentUniverseRegistryValidationError):
        InstrumentUniverseReason(" leading-space")

    with pytest.raises(InstrumentUniverseRegistryValidationError):
        InstrumentUniverseReason("")


def test_code_wrappers_reject_noncanonical_codes() -> None:
    with pytest.raises(InstrumentUniverseRegistryValidationError):
        InstrumentUniverseEvidenceRef("Provider Symbol")
    with pytest.raises(InstrumentUniverseRegistryValidationError):
        InstrumentUniverseOwnerRef("UMI-05")
    with pytest.raises(InstrumentUniverseRegistryValidationError):
        InstrumentUniverseSemanticRef("gap/value")


def test_wrong_family_and_lookup_types_fail_closed() -> None:
    with pytest.raises(
        InstrumentUniverseRegistryValidationError,
        match="must be UMI-02 IdentityFamilyCode",
    ):
        InstrumentUniverseEntry(
            family=cast(IdentityFamilyCode, "provider-symbol"),
            coverage_status=InstrumentUniverseCoverageStatus.COVERED,
            owner_status=InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
            owner_refs=(InstrumentUniverseOwnerRef("umi-05.derivatives"),),
            unresolved_semantics=(),
            evidence_refs=(InstrumentUniverseEvidenceRef("qore-umi05"),),
            reason=InstrumentUniverseReason("Wrong family type must fail."),
        )

    snapshot = _snapshot()
    with pytest.raises(
        InstrumentUniverseRegistryValidationError,
        match="family lookup requires",
    ):
        snapshot.entry_for_family(cast(IdentityFamilyCode, "provider-symbol"))

    with pytest.raises(
        InstrumentUniverseRegistryValidationError,
        match="exact instrument-universe family entry not found",
    ):
        snapshot.entry_for_family(IdentityFamilyCode("options"))


def test_registry_values_are_immutable() -> None:
    entry = _entry()
    snapshot = _snapshot(entries=(entry,))

    with pytest.raises(FrozenInstanceError):
        entry.family = IdentityFamilyCode("options")  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        snapshot.revision = 2  # type: ignore[misc]
