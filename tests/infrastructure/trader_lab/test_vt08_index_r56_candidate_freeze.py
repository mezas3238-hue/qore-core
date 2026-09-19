from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r56_candidate_freeze as freeze,
)


def test_r56_binds_exact_r55_identity() -> None:
    assert freeze.CANDIDATE_ID == (
        "VT08_INDEX_R55_DISTRIBUTED_CAUSAL_RISK_001"
    )
    assert freeze.CANDIDATE_RULE_FINGERPRINT == (
        "5b7a19b1dace3c1e92f021fdcbde9cc0ff8175633fc1c2a6892ffdf85bee2d13"
    )
    assert freeze.SOURCE_RUN_ID == 35456567688
    assert freeze.SOURCE_ARTIFACT_ID == 10587569792
    assert freeze.dependency_contract_matches() is True


def test_r56_freeze_forbids_robustness_retuning() -> None:
    governance = freeze.GOVERNANCE
    assert governance["candidate_frozen"] is True
    assert governance["development_pass"] is True
    assert governance["robustness_retuning_permitted"] is False
    assert governance["bootstrap_retuning_permitted"] is False
    assert governance["certified"] is False
    assert governance["live_authorized"] is False
