from qore.infrastructure.trader_lab.vt08_cognitive_m3_cibo_stop_only_frontier_v1 import (
    PROFILE,
    SCHEMA,
    TRAIN_FRACTION,
)


def test_m3_cibo_stop_only_frontier_freeze() -> None:
    assert PROFILE == "M3_FRACTAL"
    assert str(TRAIN_FRACTION) == "0.70"
    assert SCHEMA.endswith("m3_cibo_stop_only_frontier.v1")
