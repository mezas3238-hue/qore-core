from qore.infrastructure.trader_lab.capitalizer_historical_specification_lineage_v48 import (
    DECISIONS,
    V48_HISTORICAL_SPECIFICATION_LINEAGE,
    V48HistoricalAuthority,
    V48HistoricalDecision,
)


def _decision(decision_id: str) -> V48HistoricalDecision:
    return next(item for item in DECISIONS if item.decision_id == decision_id)


def test_m1_tri_ad_is_explicitly_historical_qore_contract_not_author_rule() -> None:
    item = _decision("M1_MSS_FVG_OB_DECLARED_QORE_CONTRACT")
    assert item.authority is V48HistoricalAuthority.OWNER_QORE_CONTRACT
    assert item.github_comment_id == 5752850268
    assert item.source_fidelity_proof is False


def test_green_ci_only_proves_implementation_conformance() -> None:
    item = _decision("DUAL_SOURCE_GATE_IMPLEMENTATION_CI_GREEN")
    assert item.authority is V48HistoricalAuthority.IMPLEMENTATION_VERIFICATION
    assert item.source_fidelity_proof is False
    assert V48_HISTORICAL_SPECIFICATION_LINEAGE.ci_green_implies_source_fidelity is False


def test_v48_preserves_history_without_relabeling_qore_as_source() -> None:
    state = V48_HISTORICAL_SPECIFICATION_LINEAGE
    assert state.qore_contract_may_be_reclassified_as_author_rule is False
    assert state.historical_evidence_must_be_preserved is True
    assert state.fresh_holdout_authorized is False
