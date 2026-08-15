from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from typing import cast

import pytest
import qore.infrastructure.instrument_universe_registry as registry
from qore.infrastructure.universal_instrument_identity import IdentityFamilyCode


SNAPSHOT_DATE = date(2026, 8, 15)


def _evidence(
    value: str,
    *,
    category: registry.InstrumentUniverseEvidenceSourceCategory = (
        registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY
    ),
    source_name: str = "QORE repository",
    locator: str | None = None,
    verified_on: date = SNAPSHOT_DATE,
) -> registry.InstrumentUniverseEvidenceRecord:
    return registry.InstrumentUniverseEvidenceRecord(
        evidence_ref=registry.InstrumentUniverseEvidenceRef(value),
        source_category=category,
        source_name=source_name,
        locator=locator or f"github://mezas3238-hue/qore-core/{value}",
        verified_on=verified_on,
    )


def _entry(
    family: str = "futures",
    *,
    coverage: registry.InstrumentUniverseCoverageStatus = (
        registry.InstrumentUniverseCoverageStatus.COVERED
    ),
    owner_status: registry.InstrumentUniverseOwnerStatus = (
        registry.InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT
    ),
    owner_values: tuple[str, ...] = ("umi-05.derivatives",),
    unresolved_values: tuple[str, ...] = (),
    evidence_values: tuple[str, ...] = ("qore-umi05",),
    reason: str = "Bounded semantic coverage exists at the retained repository baseline.",
) -> registry.InstrumentUniverseEntry:
    return registry.InstrumentUniverseEntry(
        family=IdentityFamilyCode(family),
        coverage_status=coverage,
        owner_status=owner_status,
        owner_refs=tuple(
            registry.InstrumentUniverseOwnerRef(value) for value in owner_values
        ),
        unresolved_semantics=tuple(
            registry.InstrumentUniverseSemanticRef(value)
            for value in unresolved_values
        ),
        evidence_refs=tuple(
            registry.InstrumentUniverseEvidenceRef(value)
            for value in evidence_values
        ),
        reason=registry.InstrumentUniverseReason(reason),
    )


def _snapshot(
    *,
    entries: tuple[registry.InstrumentUniverseEntry, ...] | None = None,
    evidence: tuple[registry.InstrumentUniverseEvidenceRecord, ...] | None = None,
    as_of: date = SNAPSHOT_DATE,
    revision: int = 1,
) -> registry.InstrumentUniverseRegistrySnapshot:
    return registry.InstrumentUniverseRegistrySnapshot(
        as_of=as_of,
        revision=revision,
        entries=entries or (_entry(),),
        evidence=evidence or (_evidence("qore-umi05"),),
    )


def test_snapshot_canonicalizes_entries_evidence_and_lookup() -> None:
    partial = _entry(
        "options",
        coverage=registry.InstrumentUniverseCoverageStatus.PARTIAL,
        owner_status=registry.InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
        owner_values=("umi-09.structured", "umi-05.derivatives"),
        unresolved_values=("barrier-payoff", "digital-payoff"),
        evidence_values=("external-fpml", "qore-umi05"),
        reason="Vanilla terms exist while exotic payoff semantics remain unresolved.",
    )
    covered = _entry()
    external = _evidence(
        "external-fpml",
        category=registry.InstrumentUniverseEvidenceSourceCategory.STANDARDS_INDUSTRY_BODY,
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
        registry.InstrumentUniverseOwnerRef("umi-05.derivatives"),
        registry.InstrumentUniverseOwnerRef("umi-09.structured"),
    )
    assert partial.unresolved_semantics == (
        registry.InstrumentUniverseSemanticRef("barrier-payoff"),
        registry.InstrumentUniverseSemanticRef("digital-payoff"),
    )
    assert partial.evidence_refs == (
        registry.InstrumentUniverseEvidenceRef("external-fpml"),
        registry.InstrumentUniverseEvidenceRef("qore-umi05"),
    )


def test_logical_values_are_order_insensitive_after_canonicalization() -> None:
    entry_a = _entry(
        "options",
        coverage=registry.InstrumentUniverseCoverageStatus.PARTIAL,
        owner_values=("umi-09.structured", "umi-05.derivatives"),
        unresolved_values=("digital-payoff", "barrier-payoff"),
        evidence_values=("qore-umi05", "external-fpml"),
    )
    entry_b = _entry(
        "options",
        coverage=registry.InstrumentUniverseCoverageStatus.PARTIAL,
        owner_values=("umi-05.derivatives", "umi-09.structured"),
        unresolved_values=("barrier-payoff", "digital-payoff"),
        evidence_values=("external-fpml", "qore-umi05"),
    )
    external = _evidence(
        "external-fpml",
        category=registry.InstrumentUniverseEvidenceSourceCategory.STANDARDS_INDUSTRY_BODY,
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
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        _snapshot(as_of=as_of, revision=revision)


def test_duplicate_family_conflict_fails_deterministically() -> None:
    first = _entry()
    second = _entry(
        coverage=registry.InstrumentUniverseCoverageStatus.PARTIAL,
        unresolved_values=("specialized-future",),
        reason="Conflicting duplicate row must not be accepted.",
    )

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
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
        registry.InstrumentUniverseRegistryValidationError,
        match="evidence references must be unique",
    ):
        _snapshot(evidence=(duplicate_ref_a, duplicate_ref_b))

    duplicate_content_a = _evidence("qore-a")
    duplicate_content_b = _evidence("qore-b")
    entry = _entry(evidence_values=("qore-a", "qore-b"))
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="duplicate evidence content",
    ):
        _snapshot(
            entries=(entry,),
            evidence=(duplicate_content_a, duplicate_content_b),
        )


def test_dangling_and_orphan_evidence_are_rejected() -> None:
    dangling = _entry(evidence_values=("missing-evidence",))
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="dangling evidence",
    ):
        _snapshot(entries=(dangling,), evidence=(_evidence("qore-umi05"),))

    orphan = _evidence(
        "external-unused",
        category=registry.InstrumentUniverseEvidenceSourceCategory.REGULATORY_OFFICIAL,
        source_name="Official source",
        locator="https://example.invalid/official-source",
    )
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="must all be referenced",
    ):
        _snapshot(evidence=(_evidence("qore-umi05"), orphan))


def test_evidence_verified_after_snapshot_is_rejected() -> None:
    future_evidence = _evidence(
        "qore-umi05",
        verified_on=date(2026, 8, 16),
    )
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="after snapshot",
    ):
        _snapshot(evidence=(future_evidence,))


@pytest.mark.parametrize(
    "coverage",
    [
        registry.InstrumentUniverseCoverageStatus.COVERED,
        registry.InstrumentUniverseCoverageStatus.PARTIAL,
    ],
)
def test_external_evidence_alone_cannot_establish_qore_semantic_coverage(
    coverage: registry.InstrumentUniverseCoverageStatus,
) -> None:
    unresolved = (
        ("unresolved-variant",)
        if coverage is registry.InstrumentUniverseCoverageStatus.PARTIAL
        else ()
    )
    entry = _entry(
        coverage=coverage,
        unresolved_values=unresolved,
        evidence_values=("provider-official",),
    )
    provider_evidence = _evidence(
        "provider-official",
        category=registry.InstrumentUniverseEvidenceSourceCategory.PROVIDER_PLATFORM_OFFICIAL,
        source_name="Provider documentation",
        locator="https://provider.example/instruments",
    )

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="requires retained QORE repository evidence",
    ):
        _snapshot(entries=(entry,), evidence=(provider_evidence,))


def test_partial_coverage_cannot_drop_unresolved_semantics() -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="partial family must retain unresolved semantics",
    ):
        _entry(
            coverage=registry.InstrumentUniverseCoverageStatus.PARTIAL,
            unresolved_values=(),
        )


def test_covered_family_cannot_hide_unresolved_semantics() -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="covered family must not retain unresolved semantics",
    ):
        _entry(unresolved_values=("hidden-gap",))


@pytest.mark.parametrize(
    ("coverage", "owner_status", "owner_values", "unresolved_values"),
    [
        (
            registry.InstrumentUniverseCoverageStatus.COVERED,
            registry.InstrumentUniverseOwnerStatus.PARTIAL_CONTRACT,
            ("umi-05.derivatives",),
            (),
        ),
        (
            registry.InstrumentUniverseCoverageStatus.PARTIAL,
            registry.InstrumentUniverseOwnerStatus.NO_CERTIFIED_OWNER,
            (),
            ("gap",),
        ),
        (
            registry.InstrumentUniverseCoverageStatus.UNRESOLVED,
            registry.InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
            ("umi-05.derivatives",),
            ("gap",),
        ),
        (
            registry.InstrumentUniverseCoverageStatus.DEFERRED,
            registry.InstrumentUniverseOwnerStatus.PARTIAL_CONTRACT,
            ("umi-05.derivatives",),
            ("gap",),
        ),
        (
            registry.InstrumentUniverseCoverageStatus.EXCLUDED,
            registry.InstrumentUniverseOwnerStatus.NO_CERTIFIED_OWNER,
            (),
            (),
        ),
    ],
)
def test_conflicting_coverage_owner_status_combinations_fail(
    coverage: registry.InstrumentUniverseCoverageStatus,
    owner_status: registry.InstrumentUniverseOwnerStatus,
    owner_values: tuple[str, ...],
    unresolved_values: tuple[str, ...],
) -> None:
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        _entry(
            coverage=coverage,
            owner_status=owner_status,
            owner_values=owner_values,
            unresolved_values=unresolved_values,
        )


def test_unresolved_deferred_and_excluded_have_bounded_valid_shapes() -> None:
    unresolved = _entry(
        "securities-financing",
        coverage=registry.InstrumentUniverseCoverageStatus.UNRESOLVED,
        owner_status=registry.InstrumentUniverseOwnerStatus.NO_CERTIFIED_OWNER,
        owner_values=(),
        unresolved_values=("repo-terms", "securities-lending-terms"),
        evidence_values=("external-fsb",),
        reason="No certified D04 semantic owner exists for SFT terms at this snapshot.",
    )
    deferred = _entry(
        "event-contracts",
        coverage=registry.InstrumentUniverseCoverageStatus.DEFERRED,
        owner_status=registry.InstrumentUniverseOwnerStatus.NO_CERTIFIED_OWNER,
        owner_values=(),
        unresolved_values=("event-resolution",),
        evidence_values=("external-cftc",),
        reason="Material family discovered; implementation belongs to a later owner slice.",
    )
    excluded = _entry(
        "out-of-scope-example",
        coverage=registry.InstrumentUniverseCoverageStatus.EXCLUDED,
        owner_status=registry.InstrumentUniverseOwnerStatus.NOT_APPLICABLE,
        owner_values=(),
        unresolved_values=(),
        evidence_values=("external-official",),
        reason="Governed evidence demonstrates this row is outside UMI scope.",
    )
    evidence = (
        _evidence(
            "external-fsb",
            category=registry.InstrumentUniverseEvidenceSourceCategory.REGULATORY_OFFICIAL,
            source_name="FSB",
            locator="https://www.fsb.org/securities-financing/",
        ),
        _evidence(
            "external-cftc",
            category=registry.InstrumentUniverseEvidenceSourceCategory.REGULATORY_OFFICIAL,
            source_name="CFTC",
            locator="https://www.cftc.gov/event-contracts/",
        ),
        _evidence(
            "external-official",
            category=registry.InstrumentUniverseEvidenceSourceCategory.REGULATORY_OFFICIAL,
            source_name="Official evidence",
            locator="https://example.invalid/exclusion-evidence",
        ),
    )

    snapshot = _snapshot(
        entries=(excluded, unresolved, deferred),
        evidence=evidence,
    )

    assert (
        snapshot.entry_for_family(
            IdentityFamilyCode("securities-financing")
        ).coverage_status
        is registry.InstrumentUniverseCoverageStatus.UNRESOLVED
    )
    assert (
        snapshot.entry_for_family(IdentityFamilyCode("event-contracts")).coverage_status
        is registry.InstrumentUniverseCoverageStatus.DEFERRED
    )


def test_owner_presence_rules_fail_closed() -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="requires explicit owner_refs",
    ):
        _entry(owner_values=())

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="must not retain owner_refs",
    ):
        _entry(
            coverage=registry.InstrumentUniverseCoverageStatus.UNRESOLVED,
            owner_status=registry.InstrumentUniverseOwnerStatus.NO_CERTIFIED_OWNER,
            owner_values=("unsafe-owner",),
            unresolved_values=("gap",),
        )


def test_duplicate_entry_refs_fail_before_canonicalization() -> None:
    duplicate_owner = registry.InstrumentUniverseOwnerRef("umi-05.derivatives")
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="owner_refs must be unique",
    ):
        registry.InstrumentUniverseEntry(
            family=IdentityFamilyCode("options"),
            coverage_status=registry.InstrumentUniverseCoverageStatus.PARTIAL,
            owner_status=registry.InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
            owner_refs=(duplicate_owner, duplicate_owner),
            unresolved_semantics=(registry.InstrumentUniverseSemanticRef("gap"),),
            evidence_refs=(registry.InstrumentUniverseEvidenceRef("qore-umi05"),),
            reason=registry.InstrumentUniverseReason("Duplicate owners must fail."),
        )

    duplicate_semantic = registry.InstrumentUniverseSemanticRef("gap")
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="unresolved_semantics must be unique",
    ):
        registry.InstrumentUniverseEntry(
            family=IdentityFamilyCode("options"),
            coverage_status=registry.InstrumentUniverseCoverageStatus.PARTIAL,
            owner_status=registry.InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
            owner_refs=(registry.InstrumentUniverseOwnerRef("umi-05.derivatives"),),
            unresolved_semantics=(duplicate_semantic, duplicate_semantic),
            evidence_refs=(registry.InstrumentUniverseEvidenceRef("qore-umi05"),),
            reason=registry.InstrumentUniverseReason("Duplicate semantics must fail."),
        )

    duplicate_evidence = registry.InstrumentUniverseEvidenceRef("qore-umi05")
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="evidence_refs must be unique",
    ):
        registry.InstrumentUniverseEntry(
            family=IdentityFamilyCode("options"),
            coverage_status=registry.InstrumentUniverseCoverageStatus.PARTIAL,
            owner_status=registry.InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
            owner_refs=(registry.InstrumentUniverseOwnerRef("umi-05.derivatives"),),
            unresolved_semantics=(registry.InstrumentUniverseSemanticRef("gap"),),
            evidence_refs=(duplicate_evidence, duplicate_evidence),
            reason=registry.InstrumentUniverseReason("Duplicate evidence refs must fail."),
        )


def test_evidence_and_reason_reject_credential_like_or_non_normalized_text() -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like",
    ):
        _evidence(
            "unsafe-evidence",
            locator="https://official.example/?token=do-not-retain",
        )

    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        registry.InstrumentUniverseReason(" leading-space")

    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        registry.InstrumentUniverseReason("")


def test_code_wrappers_reject_noncanonical_codes() -> None:
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        registry.InstrumentUniverseEvidenceRef("Provider Symbol")
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        registry.InstrumentUniverseOwnerRef("UMI-05")
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        registry.InstrumentUniverseSemanticRef("gap/value")


def test_wrong_family_and_lookup_types_fail_closed() -> None:
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="must be UMI-02 IdentityFamilyCode",
    ):
        registry.InstrumentUniverseEntry(
            family=cast(IdentityFamilyCode, "provider-symbol"),
            coverage_status=registry.InstrumentUniverseCoverageStatus.COVERED,
            owner_status=registry.InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
            owner_refs=(registry.InstrumentUniverseOwnerRef("umi-05.derivatives"),),
            unresolved_semantics=(),
            evidence_refs=(registry.InstrumentUniverseEvidenceRef("qore-umi05"),),
            reason=registry.InstrumentUniverseReason("Wrong family type must fail."),
        )

    snapshot = _snapshot()
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="family lookup requires",
    ):
        snapshot.entry_for_family(cast(IdentityFamilyCode, "provider-symbol"))

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
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
