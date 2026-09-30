from qore.infrastructure.trader_lab.capitalizer_v49_migration_manifest import (
    ITEMS,
    V49_MIGRATION_MANIFEST,
    V49MigrationAction,
)


def _action(item_id: str) -> V49MigrationAction:
    return next(item.action for item in ITEMS if item.item_id == item_id)


def test_daily_h4_and_159_density_are_superseded_for_v49() -> None:
    assert _action("V48_DAILY_H4_ASIA_LONDON_DECISION_ROUTES") is (
        V49MigrationAction.SUPERSEDE_FOR_V49
    )
    assert _action("V48_159_PER_YEAR_DENSITY_PROFILE") is (
        V49MigrationAction.SUPERSEDE_FOR_V49
    )
    assert _action("FRESH_H1_EVENT_PER_TRADE_TOPOLOGY") is (
        V49MigrationAction.SUPERSEDE_FOR_V49
    )


def test_provider_truth_and_governance_are_preserved() -> None:
    assert _action("PROVIDER_NATIVE_M1_EXACT_TICKS_CAUSAL_TIMESTAMPS") is (
        V49MigrationAction.PRESERVE
    )
    assert _action("MAX3_SESSION_CEILING") is V49MigrationAction.PRESERVE


def test_v49_preserves_v48_evidence_but_removes_daily_h4_from_active_identity() -> None:
    state = V49_MIGRATION_MANIFEST
    assert state.v48_evidence_deleted is False
    assert state.v48_results_rewritten is False
    assert state.daily_h4_active_in_v49 is False
    assert state.fresh_holdout_authorized is False
    assert state.economics_authorized is False
    assert state.live_authorized is False
