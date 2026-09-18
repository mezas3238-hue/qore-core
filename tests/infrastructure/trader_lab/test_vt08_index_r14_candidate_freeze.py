from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r14_candidate_freeze as freeze


def test_r14_frozen_candidate_identity() -> None:
    assert freeze.CANDIDATE_ID == "VT08_INDEX_R14_ROLLING_1574_001"
    assert freeze.FIVE_YEAR_SAMPLE == 1574
    assert freeze.FIVE_YEAR_PRIMARY_PF == "1.522470915576582435504401155"
    assert freeze.FIVE_YEAR_PRIMARY_DD_R == "5.396620098039215686274509804"
    assert freeze.FIVE_YEAR_SECONDARY_PF == "1.316158221647938784106714952"
    assert freeze.FIVE_YEAR_SECONDARY_DD_R == "7.201995098039215686274509804"


def test_r14_frozen_scheme_matches_passing_contract() -> None:
    scheme = freeze.frozen_refined_scheme()
    assert scheme.scheme_id == freeze.SCHEME_ID
    assert scheme.aligned_weight == Decimal("0.25")
    assert scheme.warn_dd_r == Decimal("1.75")
    assert scheme.warn_multiplier == Decimal("0.15")
    assert scheme.hard_dd_r == Decimal("2.50")
    assert scheme.hard_multiplier == Decimal("0.10")
    assert scheme.loss_multiplier == Decimal("0.20")
    assert freeze.GOVERNANCE["candidate_frozen"] is True
    assert freeze.GOVERNANCE["live_authorized"] is False
