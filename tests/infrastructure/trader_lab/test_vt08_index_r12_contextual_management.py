from decimal import Decimal

from qore.infrastructure.trader_lab import vt08_index_r10_contextual_risk as r10
from qore.infrastructure.trader_lab import vt08_index_r12_contextual_management as mod


def test_r12_contract() -> None:
    assert mod.MIN_TRADES == 1500
    assert mod.MAX_TRADES == 1600
    assert mod.PRIMARY_STRESS == Decimal("0.05")
    assert mod.SECONDARY_STRESS == Decimal("0.10")


def test_r12_pair_space_is_bounded() -> None:
    pairs = mod._pairs()
    assert len(pairs) == 18
    assert len({pair.pair_id for pair in pairs}) == 18


def test_r12_strong_context_definition_is_pre_entry() -> None:
    strong = r10.Context(True, False, False, False)
    rearm = r10.Context(False, True, False, False)
    weak = r10.Context(False, False, False, False)
    assert mod._is_strong(strong)
    assert mod._is_strong(rearm)
    assert not mod._is_strong(weak)
