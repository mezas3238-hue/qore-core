from qore.infrastructure.trader_lab.capitalizer_v48_migration_manifest import (
    ITEMS,
    V48_MIGRATION_MANIFEST,
    V48MigrationAction,
)


def _action(item_id: str) -> V48MigrationAction:
    return next(item.action for item in ITEMS if item.item_id == item_id)


def test_execution_truth_and_validation_infrastructure_are_preserved() -> None:
    assert _action("PROVIDER_NATIVE_M1_AND_EXACT_TICKS") is V48MigrationAction.PRESERVE
    assert _action("TIMESTAMP_AND_ANTI_LOOKAHEAD_DISCIPLINE") is V48MigrationAction.PRESERVE
    assert _action("OOS_PARTITIONS_UTC_MONTE_CARLO_COST_STRESS") is V48MigrationAction.PRESERVE


def test_faulty_composition_layers_are_superseded_not_deleted() -> None:
    assert _action("SOURCE_STRATEGY_GRAMMAR_V2") is V48MigrationAction.SUPERSEDE_FOR_V48
    assert _action("DUAL_SOURCE_ENTRY_ACCEPTANCE_V1") is V48MigrationAction.SUPERSEDE_FOR_V48
    assert _action("SOURCE_SESSION_CONTEXT_V2_GLOBAL_VETO") is V48MigrationAction.SUPERSEDE_FOR_V48
    assert _action("M1_MSS_FVG_OB_UNIVERSAL_TRIAD") is V48MigrationAction.SUPERSEDE_FOR_V48
    assert V48_MIGRATION_MANIFEST.historical_files_deleted is False
    assert V48_MIGRATION_MANIFEST.v47_evidence_rewritten is False


def test_target_candidates_can_be_reused_without_reusing_uniqueness_policy() -> None:
    assert _action("STRUCTURAL_TARGET_CANDIDATE_GENERATION") is (
        V48MigrationAction.REUSE_PRIMITIVE_ONLY
    )
    assert _action("STRUCTURAL_TARGET_EXACTLY_ONE_RESOLUTION") is (
        V48MigrationAction.SUPERSEDE_FOR_V48
    )


def test_manifest_grants_no_fresh_or_live_authority() -> None:
    assert V48_MIGRATION_MANIFEST.fresh_holdout_authorized is False
    assert V48_MIGRATION_MANIFEST.live_authorized is False
