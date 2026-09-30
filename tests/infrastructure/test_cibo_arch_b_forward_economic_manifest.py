from dataclasses import replace

import pytest

from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
    build_arch_b_forward_economic_manifest,
)
from qore.infrastructure.cibo_ce2i_phase20_execution_risk_store import (
    VersionedPhase20ExecutedRiskBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_cma_settlement_store import (
    VersionedCmaSettlementBook,
)
from qore.infrastructure.cibo_t20_capital_release_evidence import (
    VersionedT20CapitalReleaseBook,
)


def _empty_manifest():
    return build_arch_b_forward_economic_manifest(
        evidence_book=VersionedPhase20ForwardEvidenceBook(generation=0),
        policy_book=VersionedPhase20ForwardPolicyBook(generation=0),
        executed_risk_book=VersionedPhase20ExecutedRiskBook(generation=0),
        settlement_book=VersionedCmaSettlementBook(generation=0),
        release_book=VersionedT20CapitalReleaseBook(generation=0),
    )


def test_arch_b_manifest_fails_closed_without_forward_population() -> None:
    manifest = _empty_manifest()

    assert manifest.manifest_id == ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID
    assert manifest.qualification_status == "NOT_READY"
    assert manifest.decision_epochs == 0
    assert manifest.candidate_rows == 0
    assert manifest.complete_lineage_rows == 0
    assert manifest.rows == ()
    assert manifest.gaps == ()
    assert manifest.ready_for_scientific_consumption is False
    assert manifest.certification_ready is False
    assert manifest.productive_authority is False
    assert manifest.fingerprint().startswith("sha256:")


def test_arch_b_empty_manifest_is_deterministic() -> None:
    left = _empty_manifest()
    right = _empty_manifest()

    assert left == right
    assert left.fingerprint() == right.fingerprint()


def test_arch_b_manifest_cannot_mint_scientific_readiness_without_rows() -> None:
    manifest = _empty_manifest()

    with pytest.raises(
        ValueError,
        match="non-empty qualified lineage",
    ):
        replace(
            manifest,
            qualification_status="PASS",
            decision_epochs=80,
            candidate_rows=200,
            complete_lineage_rows=0,
            ready_for_scientific_consumption=True,
        )
