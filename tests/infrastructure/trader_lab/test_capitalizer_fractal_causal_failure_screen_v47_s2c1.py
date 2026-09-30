from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_fractal_causal_failure_screen_v47_s2c1 as screen,
)


def test_target_r_bands_are_frozen_and_exhaustive() -> None:
    assert screen._target_r_band(Decimal("1.999")) == "<2R"
    assert screen._target_r_band(Decimal("2")) == "[2,4)R"
    assert screen._target_r_band(Decimal("4")) == "[4,8)R"
    assert screen._target_r_band(Decimal("8")) == "[8,16)R"
    assert screen._target_r_band(Decimal("16")) == ">=16R"


def test_screen_source_evidence_is_frozen() -> None:
    assert screen.PREDECLARATION_COMMENT_ID == 5901906100
    assert screen.SOURCE_S2A_RUN_ID == 36642644284
    assert screen.SOURCE_S2B_RUN_ID == 36651366703
