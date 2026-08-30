from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

import qore.infrastructure.instrument_universe_registry as registry
from qore.infrastructure.universal_instrument_identity import IdentityFamilyCode

_AS_OF = date(2026, 8, 15)
_REASON = "Bounded futures semantics retain two explicit specialization gaps."

_CodeRef = (
    registry.InstrumentUniverseEvidenceRef
    | registry.InstrumentUniverseOwnerRef
    | registry.InstrumentUniverseSemanticRef
)


def _record(
    value: str,
    *,
    category: registry.InstrumentUniverseEvidenceSourceCategory,
    source_name: str,
    locator: str,
) -> registry.InstrumentUniverseEvidenceRecord:
    return registry.InstrumentUniverseEvidenceRecord(
        evidence_ref=registry.InstrumentUniverseEvidenceRef(value),
        source_category=category,
        source_name=source_name,
        locator=locator,
        verified_on=_AS_OF,
    )


def _entry() -> registry.InstrumentUniverseEntry:
    return registry.InstrumentUniverseEntry(
        family=IdentityFamilyCode("futures"),
        coverage_status=registry.InstrumentUniverseCoverageStatus.PARTIAL,
        owner_status=registry.InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
        owner_refs=(
            registry.InstrumentUniverseOwnerRef("umi-09.structured"),
            registry.InstrumentUniverseOwnerRef("umi-05.derivatives"),
        ),
        unresolved_semantics=(
            registry.InstrumentUniverseSemanticRef("final-settlement"),
            registry.InstrumentUniverseSemanticRef("deliverable-basket"),
        ),
        evidence_refs=(
            registry.InstrumentUniverseEvidenceRef("qore-umi05"),
            registry.InstrumentUniverseEvidenceRef("external-cme"),
        ),
        reason=registry.InstrumentUniverseReason(_REASON),
    )


def _snapshot() -> registry.InstrumentUniverseRegistrySnapshot:
    return registry.InstrumentUniverseRegistrySnapshot(
        as_of=_AS_OF,
        revision=1,
        entries=(_entry(),),
        evidence=(
            _record(
                "qore-umi05",
                category=(
                    registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY
                ),
                source_name="QORE repository",
                locator="qore://umi-05/futures",
            ),
            _record(
                "external-cme",
                category=(
                    registry.InstrumentUniverseEvidenceSourceCategory.EXCHANGE_CLEARING_VENUE
                ),
                source_name="CME",
                locator="https://www.cmegroup.com/markets.html",
            ),
        ),
    )


@pytest.mark.parametrize(
    "value",
    [
        registry.InstrumentUniverseEvidenceRef("qore-evidence"),
        registry.InstrumentUniverseOwnerRef("umi-05.derivatives"),
        registry.InstrumentUniverseSemanticRef("deliverable-basket"),
    ],
)
def test_code_ref_logical_values_revalidates_corrupted_local_state(
    value: _CodeRef,
) -> None:
    object.__setattr__(value, "value", "NOT CANONICAL")

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="canonical lowercase code syntax",
    ):
        value.logical_values()


def test_reason_logical_values_rejects_corrupted_credential_material() -> None:
    reason = registry.InstrumentUniverseReason("Safe retained reason")
    object.__setattr__(reason, "value", "token=PLAINTEXT-SECRET")

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        reason.logical_values()


def test_evidence_record_revalidates_content_at_every_public_projection() -> None:
    record = _record(
        "external-source",
        category=registry.InstrumentUniverseEvidenceSourceCategory.REGULATORY_OFFICIAL,
        source_name="Official source",
        locator="https://official.example/evidence",
    )
    object.__setattr__(
        record,
        "locator",
        "https://alice:password@example.invalid/evidence",
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


def test_evidence_record_revalidates_corrupted_evidence_ref() -> None:
    record = _record(
        "qore-evidence",
        category=registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY,
        source_name="QORE repository",
        locator="qore://umi-13/evidence",
    )
    object.__setattr__(record.evidence_ref, "value", "NOT CANONICAL")

    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        record.__post_init__()
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        record.content_logical_values()
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        record.logical_values()


@pytest.mark.parametrize("ref_kind", ["owner", "semantic", "evidence"])
def test_entry_revalidates_corrupted_local_ref_before_hash_or_sort(
    ref_kind: str,
) -> None:
    entry = _entry()
    value: _CodeRef
    if ref_kind == "owner":
        value = entry.owner_refs[0]
    elif ref_kind == "semantic":
        value = entry.unresolved_semantics[0]
    else:
        value = entry.evidence_refs[0]
    object.__setattr__(value, "value", "NOT CANONICAL")

    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        entry.__post_init__()
    with pytest.raises(registry.InstrumentUniverseRegistryValidationError):
        entry.logical_values()


def test_entry_revalidates_corrupted_reason_and_imported_family_state() -> None:
    entry = _entry()
    object.__setattr__(entry.reason, "value", "token=PLAINTEXT-SECRET")

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        entry.__post_init__()
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        entry.logical_values()

    entry = _entry()
    object.__setattr__(entry.family, "value", "NOT CANONICAL")

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="canonical UMI-02 IdentityFamilyCode state",
    ):
        entry.__post_init__()
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="canonical UMI-02 IdentityFamilyCode state",
    ):
        entry.logical_values()


def test_new_entry_revalidates_exact_corrupted_children_before_acceptance() -> None:
    reason = registry.InstrumentUniverseReason("Safe retained reason")
    object.__setattr__(reason, "value", "token=PLAINTEXT-SECRET")

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseEntry(
            family=IdentityFamilyCode("futures"),
            coverage_status=registry.InstrumentUniverseCoverageStatus.COVERED,
            owner_status=registry.InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
            owner_refs=(registry.InstrumentUniverseOwnerRef("umi-05.derivatives"),),
            unresolved_semantics=(),
            evidence_refs=(registry.InstrumentUniverseEvidenceRef("qore-umi05"),),
            reason=reason,
        )


def test_new_entry_rejects_unhashable_corrupted_ref_with_owner_error() -> None:
    owner_ref = registry.InstrumentUniverseOwnerRef("umi-05.derivatives")
    object.__setattr__(owner_ref, "value", [])

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="canonical lowercase code syntax",
    ) as error:
        registry.InstrumentUniverseEntry(
            family=IdentityFamilyCode("futures"),
            coverage_status=registry.InstrumentUniverseCoverageStatus.COVERED,
            owner_status=registry.InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
            owner_refs=(owner_ref,),
            unresolved_semantics=(),
            evidence_refs=(registry.InstrumentUniverseEvidenceRef("qore-umi05"),),
            reason=registry.InstrumentUniverseReason("Bounded futures coverage."),
        )

    assert type(error.value) is registry.InstrumentUniverseRegistryValidationError


def test_new_snapshot_revalidates_exact_corrupted_entry_before_graph_operations() -> None:
    entry = _entry()
    object.__setattr__(entry.reason, "value", "token=PLAINTEXT-SECRET")

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseRegistrySnapshot(
            as_of=_AS_OF,
            revision=1,
            entries=(entry,),
            evidence=(
                _record(
                    "qore-umi05",
                    category=(
                        registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY
                    ),
                    source_name="QORE repository",
                    locator="qore://umi-05/futures",
                ),
                _record(
                    "external-cme",
                    category=(
                        registry.InstrumentUniverseEvidenceSourceCategory.EXCHANGE_CLEARING_VENUE
                    ),
                    source_name="CME",
                    locator="https://www.cmegroup.com/markets.html",
                ),
            ),
        )


def test_new_snapshot_revalidates_exact_corrupted_evidence_record() -> None:
    record = _record(
        "qore-umi05",
        category=registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY,
        source_name="QORE repository",
        locator="qore://umi-05/futures",
    )
    object.__setattr__(
        record,
        "locator",
        "https://alice:password@example.invalid/evidence",
    )

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        registry.InstrumentUniverseRegistrySnapshot(
            as_of=_AS_OF,
            revision=1,
            entries=(
                registry.InstrumentUniverseEntry(
                    family=IdentityFamilyCode("futures"),
                    coverage_status=registry.InstrumentUniverseCoverageStatus.COVERED,
                    owner_status=(
                        registry.InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT
                    ),
                    owner_refs=(
                        registry.InstrumentUniverseOwnerRef("umi-05.derivatives"),
                    ),
                    unresolved_semantics=(),
                    evidence_refs=(
                        registry.InstrumentUniverseEvidenceRef("qore-umi05"),
                    ),
                    reason=registry.InstrumentUniverseReason(
                        "Bounded futures coverage."
                    ),
                ),
            ),
            evidence=(record,),
        )


def test_snapshot_revalidates_corrupted_entry_before_reentry_projection_or_lookup() -> None:
    snapshot = _snapshot()
    object.__setattr__(snapshot.entries[0].reason, "value", "token=PLAINTEXT-SECRET")

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        snapshot.__post_init__()
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        snapshot.logical_values()
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        snapshot.entry_for_family(IdentityFamilyCode("futures"))


def test_snapshot_revalidates_corrupted_evidence_graph() -> None:
    snapshot = _snapshot()
    object.__setattr__(
        snapshot.evidence[0],
        "locator",
        "https://alice:password@example.invalid/evidence",
    )

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        snapshot.__post_init__()
    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="credential-like material",
    ):
        snapshot.logical_values()


def test_family_lookup_revalidates_query_identity_family_state() -> None:
    snapshot = _snapshot()
    query = IdentityFamilyCode("futures")
    object.__setattr__(query, "value", "NOT CANONICAL")

    with pytest.raises(
        registry.InstrumentUniverseRegistryValidationError,
        match="family lookup requires canonical UMI-02 IdentityFamilyCode state",
    ):
        snapshot.entry_for_family(query)


def test_valid_canonical_projection_and_order_remain_unchanged() -> None:
    snapshot = _snapshot()
    expected = (
        "2026-08-15",
        1,
        (
            (
                ("futures",),
                "partial",
                "certified-contract",
                (("umi-05.derivatives",), ("umi-09.structured",)),
                (("deliverable-basket",), ("final-settlement",)),
                (("external-cme",), ("qore-umi05",)),
                (_REASON,),
            ),
        ),
        (
            (
                ("external-cme",),
                "exchange-clearing-venue",
                "CME",
                "https://www.cmegroup.com/markets.html",
                "2026-08-15",
            ),
            (
                ("qore-umi05",),
                "qore-repository",
                "QORE repository",
                "qore://umi-05/futures",
                "2026-08-15",
            ),
        ),
    )

    assert snapshot.logical_values() == expected
    assert snapshot.logical_values() == expected
    assert snapshot.entry_for_family(IdentityFamilyCode("futures")) is snapshot.entries[0]


def test_recursive_revalidation_architecture_evidence_is_retained() -> None:
    root = Path(__file__).resolve().parents[2]
    evidence = (
        root
        / "docs"
        / "architecture"
        / "QORE-UMI-13-RECURSIVE-REGISTRY-REVALIDATION-001.md"
    ).read_text(encoding="utf-8")

    assert "UMI14-R2-UMI13-REVALIDATION-001" in evidence
    assert "Issue #465" in evidence
    assert "entry_for_family()" in evidence
    assert "DOES NOT AUTHORIZE PRODUCTION" in evidence
