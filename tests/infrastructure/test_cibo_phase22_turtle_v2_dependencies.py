from qore.infrastructure.cibo_phase22_turtle_v2_dependencies import (
    V2_M5_SOURCE_IDENTITY,
    lineage_for_symbol,
    phase22_dependency_lineage,
)
from qore.infrastructure.trader_lab import (
    cibo_market_atlas_journey_extractor_v1 as journey,
)
from qore.infrastructure.trader_lab import (
    cibo_market_atlas_target_destination_v2 as target,
)


def test_phase22_dependency_context_rebinds_and_restores_lineage() -> None:
    original = (
        journey.SOURCE_IDENTITY,
        journey.SOURCE_RUN_ID,
        journey.SOURCE_GIT_SHA,
        target.SOURCE_JOURNEY_RUN_ID,
        target.SOURCE_JOURNEY_GIT_SHA,
        target.SOURCE_M5_RUN_ID,
        target.SOURCE_M5_GIT_SHA,
    )
    lineage = lineage_for_symbol(
        symbol="EURUSD",
        journey_build_run_id=123456789,
        journey_build_git_sha="1" * 40,
    )

    with phase22_dependency_lineage(lineage):
        assert journey.SOURCE_IDENTITY == V2_M5_SOURCE_IDENTITY
        assert journey.SOURCE_RUN_ID == lineage.source_run_id
        assert journey.SOURCE_GIT_SHA == lineage.source_collector_git_sha
        assert target.SOURCE_JOURNEY_RUN_ID == 123456789
        assert target.SOURCE_JOURNEY_GIT_SHA == "1" * 40
        assert target.SOURCE_M5_RUN_ID == lineage.source_run_id
        assert target.SOURCE_M5_GIT_SHA == lineage.source_collector_git_sha

    assert (
        journey.SOURCE_IDENTITY,
        journey.SOURCE_RUN_ID,
        journey.SOURCE_GIT_SHA,
        target.SOURCE_JOURNEY_RUN_ID,
        target.SOURCE_JOURNEY_GIT_SHA,
        target.SOURCE_M5_RUN_ID,
        target.SOURCE_M5_GIT_SHA,
    ) == original


def test_phase22_dependency_lineage_binds_exact_source_artifact() -> None:
    lineage = lineage_for_symbol(
        symbol="XAUUSD",
        journey_build_run_id=1,
        journey_build_git_sha="2" * 40,
    )

    assert lineage.source_run_id == 36892253124
    assert lineage.source_artifact_id == 11177635981
    assert lineage.source_artifact_digest.startswith("sha256:")
