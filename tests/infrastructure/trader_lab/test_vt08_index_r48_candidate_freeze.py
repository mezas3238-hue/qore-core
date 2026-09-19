from __future__ import annotations

from qore.infrastructure.trader_lab import vt08_index_r48_candidate_freeze as r48


def test_r48_freezes_exact_r47_identity() -> None:
    assert r48.CANDIDATE_ID == "VT08_INDEX_R47_TRANSPORT_SAFE_STRUCTURAL_DEMOTION_001"
    assert (
        r48.CANDIDATE_RULE_FINGERPRINT
        == "013bffb847dff546cdb2a31ac9931bdb1336596c540f6a72c5c729d1762c36c8"
    )
    assert r48.dependency_contract_matches() is True
    assert len(r48.FREEZE_EVIDENCE_FINGERPRINT) == 64


def test_r48_binds_official_dual_window_evidence() -> None:
    assert r48.SOURCE_RUN_ID == 35439293342
    assert r48.SOURCE_ARTIFACT_ID == 10583234011
    assert r48.FIVE_YEAR["sample"] == 2448
    assert r48.RECENT_TWO_YEAR["sample"] == 1017
    assert r48.FIVE_YEAR["secondary_pf"] == "2.231715266927497713808336872"
    assert r48.RECENT_TWO_YEAR["secondary_pf"] == "1.777798685467245655581477532"


def test_r48_governance_is_fail_closed() -> None:
    g = r48.GOVERNANCE
    assert g["candidate_frozen"] is True
    assert g["robustness_retuning_permitted"] is False
    assert g["walk_forward_retuning_permitted"] is False
    assert g["stress_retuning_permitted"] is False
    assert g["bootstrap_retuning_permitted"] is False
    assert g["certified"] is False
    assert g["demo_eligible"] is False
    assert g["live_authorized"] is False
    assert g["real_capital_authorized"] is False
    assert g["production_authorized"] is False
