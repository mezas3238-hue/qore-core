from __future__ import annotations

from datetime import date

import qore.infrastructure.instrument_universe_registry as registry
from qore.infrastructure.universal_instrument_identity import IdentityFamilyCode

CURRENT_RECERTIFICATION_DATE = date(2026, 8, 21)

CURRENT_FAMILY_COVERAGE: tuple[tuple[str, str], ...] = (
    ("cash-money-market", "partial"),
    ("fixed-income-credit", "partial"),
    ("rates-term-structures", "partial"),
    ("equities", "partial"),
    ("funds-pooled-vehicles", "partial"),
    ("indices-benchmarks", "partial"),
    ("fx", "partial"),
    ("futures", "partial"),
    ("options", "partial"),
    ("forwards-swaps-otc", "partial"),
    ("commodities", "partial"),
    ("crypto-digital-assets", "partial"),
    ("structured-hybrid-products", "partial"),
    ("volatility-variance-products", "partial"),
    ("securities-financing", "unresolved"),
    ("cross-asset-compositions", "partial"),
    ("event-contracts", "unresolved"),
    ("contracts-for-difference", "unresolved"),
    ("loans-credit-facilities", "partial"),
)


def _owner_ref(family: str) -> str:
    return f"fixture.owner.{family}"


def _semantic_ref(family: str) -> str:
    return f"fixture.unresolved.{family}"


def _evidence_ref(family: str) -> str:
    return f"fixture.evidence.{family}"


def _reason(family: str) -> str:
    return f"Current recertification fixture for {family}."


def _entry(family: str, coverage: str) -> registry.InstrumentUniverseEntry:
    evidence_ref = registry.InstrumentUniverseEvidenceRef(_evidence_ref(family))
    if coverage == "partial":
        return registry.InstrumentUniverseEntry(
            family=IdentityFamilyCode(family),
            coverage_status=registry.InstrumentUniverseCoverageStatus.PARTIAL,
            owner_status=registry.InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT,
            owner_refs=(registry.InstrumentUniverseOwnerRef(_owner_ref(family)),),
            unresolved_semantics=(
                registry.InstrumentUniverseSemanticRef(_semantic_ref(family)),
            ),
            evidence_refs=(evidence_ref,),
            reason=registry.InstrumentUniverseReason(_reason(family)),
        )
    return registry.InstrumentUniverseEntry(
        family=IdentityFamilyCode(family),
        coverage_status=registry.InstrumentUniverseCoverageStatus.UNRESOLVED,
        owner_status=registry.InstrumentUniverseOwnerStatus.NO_CERTIFIED_OWNER,
        owner_refs=(),
        unresolved_semantics=(
            registry.InstrumentUniverseSemanticRef(_semantic_ref(family)),
        ),
        evidence_refs=(evidence_ref,),
        reason=registry.InstrumentUniverseReason(_reason(family)),
    )


def _evidence(family: str) -> registry.InstrumentUniverseEvidenceRecord:
    return registry.InstrumentUniverseEvidenceRecord(
        evidence_ref=registry.InstrumentUniverseEvidenceRef(_evidence_ref(family)),
        source_category=(
            registry.InstrumentUniverseEvidenceSourceCategory.QORE_REPOSITORY
        ),
        source_name="QORE current-main recertification fixture",
        locator=f"qore://umi-13/full-closure/{family}",
        verified_on=CURRENT_RECERTIFICATION_DATE,
    )


def _snapshot() -> registry.InstrumentUniverseRegistrySnapshot:
    return registry.InstrumentUniverseRegistrySnapshot(
        as_of=CURRENT_RECERTIFICATION_DATE,
        revision=2,
        entries=tuple(
            _entry(family, coverage) for family, coverage in CURRENT_FAMILY_COVERAGE
        ),
        evidence=tuple(_evidence(family) for family, _ in CURRENT_FAMILY_COVERAGE),
    )


def _expected_entry(family: str, coverage: str) -> tuple[object, ...]:
    owner_status = (
        "certified-contract" if coverage == "partial" else "no-certified-owner"
    )
    owner_refs: tuple[tuple[str, ...], ...] = (
        ((_owner_ref(family),),) if coverage == "partial" else ()
    )
    return (
        (family,),
        coverage,
        owner_status,
        owner_refs,
        ((_semantic_ref(family),),),
        ((_evidence_ref(family),),),
        (_reason(family),),
    )


def _expected_evidence(family: str) -> tuple[object, ...]:
    return (
        (_evidence_ref(family),),
        "qore-repository",
        "QORE current-main recertification fixture",
        f"qore://umi-13/full-closure/{family}",
        "2026-08-21",
    )


def test_current_19_family_snapshot_has_independent_complete_projection_oracle() -> None:
    snapshot = _snapshot()
    ordered_rows = tuple(sorted(CURRENT_FAMILY_COVERAGE))
    expected = (
        "2026-08-21",
        2,
        tuple(_expected_entry(family, coverage) for family, coverage in ordered_rows),
        tuple(_expected_evidence(family) for family, _ in ordered_rows),
    )

    assert snapshot.logical_values() == expected


def test_current_family_universe_is_exact_and_has_no_duplicates() -> None:
    snapshot = _snapshot()
    expected_families = tuple(sorted(family for family, _ in CURRENT_FAMILY_COVERAGE))

    assert len(CURRENT_FAMILY_COVERAGE) == 19
    assert len(set(expected_families)) == 19
    assert tuple(entry.family.value for entry in snapshot.entries) == expected_families


def test_current_coverage_statuses_preserve_partial_vs_unresolved_distinction() -> None:
    snapshot = _snapshot()
    expected_status_by_family = dict(CURRENT_FAMILY_COVERAGE)

    assert {
        entry.family.value: entry.coverage_status.value for entry in snapshot.entries
    } == expected_status_by_family
    assert {
        entry.family.value
        for entry in snapshot.entries
        if entry.coverage_status is registry.InstrumentUniverseCoverageStatus.UNRESOLVED
    } == {
        "contracts-for-difference",
        "event-contracts",
        "securities-financing",
    }


def test_loans_family_can_now_be_represented_as_partial_with_explicit_owner() -> None:
    snapshot = _snapshot()
    loans = snapshot.entry_for_family(IdentityFamilyCode("loans-credit-facilities"))

    assert loans.coverage_status is registry.InstrumentUniverseCoverageStatus.PARTIAL
    assert loans.owner_status is registry.InstrumentUniverseOwnerStatus.CERTIFIED_CONTRACT
    assert loans.owner_refs == (
        registry.InstrumentUniverseOwnerRef(
            "fixture.owner.loans-credit-facilities"
        ),
    )
    assert loans.unresolved_semantics == (
        registry.InstrumentUniverseSemanticRef(
            "fixture.unresolved.loans-credit-facilities"
        ),
    )


def test_current_snapshot_is_order_independent_without_using_sut_expected_helpers() -> None:
    forward = _snapshot()
    reverse = registry.InstrumentUniverseRegistrySnapshot(
        as_of=CURRENT_RECERTIFICATION_DATE,
        revision=2,
        entries=tuple(
            _entry(family, coverage)
            for family, coverage in reversed(CURRENT_FAMILY_COVERAGE)
        ),
        evidence=tuple(
            _evidence(family) for family, _ in reversed(CURRENT_FAMILY_COVERAGE)
        ),
    )

    assert forward.logical_values() == reverse.logical_values()
