from qore.infrastructure.trader_lab.vt08_index_v5_d1_relative_strength_candidate import (
    CANDIDATE_ID,
    RULE_FINGERPRINT,
    _accept_peer_counts,
)


def test_d1_candidate_identity_is_frozen() -> None:
    assert CANDIDATE_ID == "VT08_INDEX_V5_D1_RELATIVE_STRENGTH_001"
    assert len(RULE_FINGERPRINT) == 64


def test_peer_nonconfirmation_predicate_is_exact() -> None:
    assert _accept_peer_counts(2, 0)
    assert not _accept_peer_counts(1, 0)
    assert not _accept_peer_counts(3, 0)
    assert not _accept_peer_counts(2, 1)
