from qore.infrastructure.trader_lab.vt08_cognitive_latest_ps_core_stack_frontier_v1 import (
    CORE_STACK_ID,
    SCHEMA,
)
from qore.infrastructure.trader_lab.vt08_cognitive_latest_ps_density_recovery_v1 import (
    PROFILES,
    SELECTOR_ID,
)


def test_latest_ps_core_stack_frontier_freezes_global_profiles() -> None:
    assert SCHEMA.endswith("latest_ps_core_stack_frontier.v1")
    assert SELECTOR_ID == "LATEST_CONFIRMED_PROTECTED_SWING_V1"
    assert CORE_STACK_ID == "VT08_COGNITIVE_CORE_STACK_DEV_V1"
    assert PROFILES == ("M15_STANDARD", "M5_FRACTAL", "M3_FRACTAL")
