from qore.infrastructure.trader_lab.vt08_cognitive_m3_all_valid_anchors_frontier_v1 import (
    PROFILE,
    SCHEMA,
)


def test_m3_all_valid_anchors_frontier_freeze() -> None:
    assert PROFILE == "M3_FRACTAL"
    assert SCHEMA.endswith("m3_all_valid_anchors_frontier.v1")
