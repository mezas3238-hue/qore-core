from qore.infrastructure.trader_lab import (
    capitalizer_causal_probe_ranker_v10 as v10,
)
from qore.infrastructure.trader_lab import (
    capitalizer_contextual_stability_router_2r_v1 as router,
)
from qore.infrastructure.trader_lab import (
    capitalizer_surface_overlay_ablation_v23 as v23,
)


def test_v23_uses_only_existing_router_policies() -> None:
    assert v23.CONTROL_POLICY == "CONTEXT_STABILITY_STAGE"
    assert v23.POLICIES == (
        "CONTEXT_STABILITY_STAGE",
        "CONTEXT_ONLY",
        "CONTEXT_DEFENSIVE_STAGE",
        "CONTEXT_LOCK_STABILITY",
    )
    assert set(v23.POLICIES) <= set(router.POLICIES)


def test_v23_control_matches_current_surface_policy() -> None:
    assert v10.BASE_POSITION_POLICY == v23.CONTROL_POLICY
