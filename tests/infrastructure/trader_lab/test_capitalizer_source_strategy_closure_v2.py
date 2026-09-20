from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    CapitalizerChainStatus,
)
from qore.infrastructure.trader_lab.capitalizer_source_strategy_closure_v2 import (
    FROZEN_SOURCE_STRATEGY_CLOSURE,
)


def test_source_strategy_closure_is_frozen_and_ready_for_replay() -> None:
    closure = FROZEN_SOURCE_STRATEGY_CLOSURE

    assert closure.cognitive_dependency_status is CapitalizerChainStatus.FROZEN_APT
    assert closure.source_inventory_status is CapitalizerChainStatus.FROZEN_APT
    assert closure.deterministic_grammar_status is CapitalizerChainStatus.FROZEN_APT
    assert closure.provenance_status is CapitalizerChainStatus.FROZEN_APT
    assert closure.source_strategy_status is CapitalizerChainStatus.FROZEN_APT
    assert closure.ready_for_integrated_nine_market_replay is True
    assert closure.integrated_nine_market_replay_completed is False


def test_source_strategy_closure_preserves_source_time_boundaries() -> None:
    closure = FROZEN_SOURCE_STRATEGY_CLOSURE

    assert closure.asian_session_requires_historical_open_reference is True
    assert closure.london_source_window_frozen is True
    assert closure.new_york_source_window_frozen is True
    assert closure.qore_surveillance_bucket_equated_to_source_killzone is False


def test_source_strategy_closure_does_not_claim_later_research_or_certification() -> None:
    closure = FROZEN_SOURCE_STRATEGY_CLOSURE

    assert closure.final_nine_market_family_taxonomy_closed is False
    assert closure.stop_intelligence_closed is False
    assert closure.target_intelligence_closed is False
    assert closure.break_even_policy_closed is False
    assert closure.trailing_stop_policy_closed is False
    assert closure.trailing_target_policy_closed is False
    assert closure.zig_zig_policy_closed is False
    assert closure.daily_loss_funded_survivability_closed is False
    assert closure.economic_edge_claimed is False
    assert closure.trader_certified is False
    assert closure.demo_authorized is False
    assert closure.live_authorized is False
    assert closure.production_authorized is False
