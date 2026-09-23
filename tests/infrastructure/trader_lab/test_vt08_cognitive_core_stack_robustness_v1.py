from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_cognitive_core_stack_robustness_v1 import (
    EXTRA_COSTS_R,
    MAX_DD_R,
    MAX_MC_P95_DD_R,
    MC_BLOCK_LENGTH,
    MC_PATHS,
    MIN_MC_POSITIVE,
    MIN_PF,
    MIN_SAMPLE,
    SURVIVOR_MARKETS,
)


def test_robustness_universe_is_frozen_from_fresh_screen() -> None:
    assert SURVIVOR_MARKETS == ("EURJPY", "NZDUSD", "CADJPY")


def test_robustness_contract_is_predeclared() -> None:
    assert MC_PATHS == 10_000
    assert MC_BLOCK_LENGTH == 5
    assert EXTRA_COSTS_R == (
        Decimal("0.01"),
        Decimal("0.02"),
        Decimal("0.05"),
    )
    assert MIN_SAMPLE == 60
    assert MIN_PF == Decimal("1.80")
    assert MAX_DD_R == Decimal("6")
    assert MIN_MC_POSITIVE == Decimal("0.90")
    assert MAX_MC_P95_DD_R == Decimal("15")
