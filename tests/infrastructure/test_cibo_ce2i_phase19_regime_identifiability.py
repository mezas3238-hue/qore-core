from __future__ import annotations

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
)
from qore.infrastructure.cibo_ce2i_phase19_regime_identifiability import (
    CANONICAL_REGIME_FIELDS,
    VT31_BESPOKE_REGIME_FIELDS,
    Phase19RegimeEvidenceClass,
    audit_phase19_regime_rows,
    build_phase19_regime_identifiability,
)


def _canonical_row() -> dict[str, object]:
    return {
        "regime": {
            field: f"value:{field}" for field in CANONICAL_REGIME_FIELDS
        }
    }


def _bespoke_row() -> dict[str, object]:
    return {
        field: f"value:{field}" for field in VT31_BESPOKE_REGIME_FIELDS
    }


def test_regime_audit_classifies_shared_bespoke_and_missing_schema() -> None:
    shared = audit_phase19_regime_rows(
        trader_id=TraderLineage.R38_GBPJPY,
        rows=(_canonical_row(), _canonical_row()),
    )
    bespoke = audit_phase19_regime_rows(
        trader_id=TraderLineage.VT31_NAS100,
        rows=(_bespoke_row(), _bespoke_row()),
    )
    missing = audit_phase19_regime_rows(
        trader_id=TraderLineage.R34_XAUUSD,
        rows=({"side": "long"}, {"side": "short"}),
    )

    assert (
        shared.evidence_class
        is Phase19RegimeEvidenceClass.CANONICAL_SHARED_SCHEMA
    )
    assert (
        bespoke.evidence_class
        is Phase19RegimeEvidenceClass.BESPOKE_UNMAPPED_SCHEMA
    )
    assert (
        missing.evidence_class
        is Phase19RegimeEvidenceClass.MISSING_SHARED_SCHEMA
    )


def test_regime_audit_marks_partial_rows_as_noncanonical() -> None:
    audit = audit_phase19_regime_rows(
        trader_id=TraderLineage.R38_GBPJPY,
        rows=(_canonical_row(), {"regime": {"h1_range_state": "balanced"}}),
    )

    assert audit.evidence_class is Phase19RegimeEvidenceClass.MIXED_OR_PARTIAL
    assert audit.canonical_regime_rows == 1
    assert audit.missing_regime_rows == 1


def test_portfolio_identifiability_requires_canonical_coverage_7_of_7() -> None:
    audits = []
    for trader in PHASE19_REQUIRED_TRADERS:
        if trader is TraderLineage.VT31_NAS100:
            rows = (_bespoke_row(),)
        elif trader in {
            TraderLineage.R38_GBPJPY,
            TraderLineage.R43_GBPUSD,
            TraderLineage.R42_AUDJPY,
        }:
            rows = (_canonical_row(),)
        else:
            rows = ({"side": "long"},)
        audits.append(
            audit_phase19_regime_rows(
                trader_id=trader,
                rows=rows,
            )
        )

    evidence = build_phase19_regime_identifiability(tuple(audits))

    assert len(evidence.canonical_lineages) == 3
    assert evidence.bespoke_unmapped_lineages == (
        TraderLineage.VT31_NAS100,
    )
    assert len(evidence.missing_lineages) == 3
    assert evidence.portfolio_regime_state_identified is False
