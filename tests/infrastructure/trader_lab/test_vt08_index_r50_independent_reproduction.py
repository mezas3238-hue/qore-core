from __future__ import annotations

from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract
from qore.infrastructure.trader_lab import (
    vt08_index_r47_transport_safe_structural_demotion as r47,
)
from qore.infrastructure.trader_lab import vt08_index_r48_candidate_freeze as freeze
from qore.infrastructure.trader_lab import (
    vt08_index_r50_independent_reproduction as r50,
)


def test_r50_identity_is_bound_to_r48_freeze() -> None:
    assert freeze.CANDIDATE_ID == (
        "VT08_INDEX_R47_TRANSPORT_SAFE_STRUCTURAL_DEMOTION_001"
    )
    assert (
        freeze.CANDIDATE_RULE_FINGERPRINT
        == "013bffb847dff546cdb2a31ac9931bdb1336596c540f6a72c5c729d1762c36c8"
    )
    assert r50.MIN_EFFECTIVE_WEIGHT.as_tuple().exponent == -3


def test_r50_independent_rule_code_does_not_alias_r47() -> None:
    assert r50._independent_labels is not r47._rule_labels
    assert r50._independent_apply is not r47._apply_transport_rules
    assert r50._independent_cross_index_state is not r47._cross_index_state


def test_r50_cross_index_state_is_fail_closed_when_missing() -> None:
    assert contract.MARKETS == ("NAS100", "SP500", "US30")
