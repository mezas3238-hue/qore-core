from qore.infrastructure.trader_lab.vt08_cognitive_m3_cautious_state_shield_v1 import (
    MIN_RETENTION,
    MIN_SHIELD_PF,
    PROFILE,
    SCHEMA,
    TRAIN_FRACTION,
)


def test_m3_cautious_state_shield_freeze() -> None:
    assert PROFILE == "M3_FRACTAL"
    assert str(TRAIN_FRACTION) == "0.70"
    assert str(MIN_RETENTION) == "0.70"
    assert str(MIN_SHIELD_PF) == "1.20"
    assert SCHEMA.endswith("m3_cautious_state_shield.v1")
