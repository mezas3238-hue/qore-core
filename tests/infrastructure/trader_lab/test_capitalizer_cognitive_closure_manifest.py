from qore.infrastructure.trader_lab.capitalizer_cognitive_closure_manifest import (
    FROZEN_COGNITIVE_CLOSURE_MANIFEST,
)
from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    COGNITIVE_LAYER_ORDER,
    CapitalizerChainStatus,
)


def test_cognitive_closure_manifest_covers_all_16_layers_in_frozen_order() -> None:
    manifest = FROZEN_COGNITIVE_CLOSURE_MANIFEST

    assert tuple(item.layer for item in manifest.layer_closures) == COGNITIVE_LAYER_ORDER
    assert len(manifest.layer_closures) == 16
    assert len({item.layer for item in manifest.layer_closures}) == 16
    assert all(
        item.status is CapitalizerChainStatus.FROZEN_APT
        for item in manifest.layer_closures
    )


def test_cognitive_closure_opens_source_strategy_but_not_later_chains() -> None:
    manifest = FROZEN_COGNITIVE_CLOSURE_MANIFEST

    assert manifest.cognitive_base_status is CapitalizerChainStatus.FROZEN_APT
    assert manifest.ready_for_source_strategy_closure is True
    assert manifest.source_strategy_closed is False
    assert manifest.final_nine_market_family_taxonomy_closed is False
    assert manifest.integrated_nine_market_replay_completed is False
    assert manifest.break_even_policy_closed is False
    assert manifest.trailing_stop_policy_closed is False
    assert manifest.trailing_target_policy_closed is False
    assert manifest.zig_zig_policy_closed is False
    assert manifest.target_intelligence_closed is False
    assert manifest.daily_loss_funded_survivability_closed is False
    assert manifest.economic_candidate_frozen is False
    assert manifest.wfo_mc_stress_holdout_completed is False
    assert manifest.trader_certified is False


def test_cognitive_closure_preserves_governance_and_no_deployment_authority() -> None:
    manifest = FROZEN_COGNITIVE_CLOSURE_MANIFEST

    assert manifest.demo_authorized is False
    assert manifest.live_authorized is False
    assert manifest.production_authorized is False

    scopes = {
        item.layer.value: set(item.invariant_scope)
        for item in manifest.layer_closures
    }
    assert "COGNITIVE_CANNOT_EXECUTE" in scopes["DECISION_SOVEREIGNTY"]
    assert "NO_WINNER_BEFORE_SOURCE_STRATEGY" in scopes["OPPORTUNITY_COMPETITION"]
    assert "STOP_IMPROVE_OR_HOLD_NEVER_WIDEN" in scopes["POSITION_INTELLIGENCE"]
    assert "DETERMINISTIC_WHY_LEDGER" in scopes["COGNITIVE_AUDIT"]
