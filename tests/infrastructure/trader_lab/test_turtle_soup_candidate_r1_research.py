from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from qore.infrastructure.historical_dataset import (
    HistoricalDatasetDigest,
    HistoricalDatasetDigestAlgorithm,
    HistoricalDatasetId,
    HistoricalDatasetManifest,
    HistoricalDatasetNormalizationVersion,
    HistoricalDatasetRevisionId,
    HistoricalDatasetSchemaVersion,
    HistoricalOhlcDatasetScope,
)
from qore.infrastructure.historical_market_data import HistoricalOhlcWindow
from qore.infrastructure.market_data import Instrument, Timeframe
from qore.infrastructure.ports import AdapterId, ExternalSourceDescriptor, PortName, SourceId
from qore.infrastructure.research_run import (
    ResearchExecutionModelId,
    ResearchRunId,
    ResearchSoftwareRevision,
    ResearchTransactionCostModelId,
)
from qore.infrastructure.trader_lab.turtle_soup_candidate_r1 import TurtleSoupR1Config
from qore.infrastructure.trader_lab.turtle_soup_candidate_r1_management import (
    TurtleSoupR1ExperimentalPolicyId,
    policy_for,
)
from qore.infrastructure.trader_lab.turtle_soup_candidate_r1_research import (
    bind_research_configuration,
    build_turtle_soup_r1_development_run_evidence,
)
from qore.kernel.result import Success

_BASE = datetime(2020, 1, 2, tzinfo=UTC)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("72000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("72000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.turtle-soup-research-test"),
)
_EXECUTION = ResearchExecutionModelId(
    UUID("72000000-0000-0000-0000-000000000003")
)
_COSTS = ResearchTransactionCostModelId(
    UUID("72000000-0000-0000-0000-000000000004")
)
_SOFTWARE = ResearchSoftwareRevision("88b63e1fad236555b14931ed446ad86abbf54cce")


def _manifest(*, revision_suffix: int = 11) -> HistoricalDatasetManifest:
    return HistoricalDatasetManifest(
        dataset_id=HistoricalDatasetId(
            UUID("72000000-0000-0000-0000-000000000010")
        ),
        revision_id=HistoricalDatasetRevisionId(
            UUID(f"72000000-0000-0000-0000-{revision_suffix:012d}")
        ),
        parent_revision_id=None,
        revision_reason=None,
        scope=HistoricalOhlcDatasetScope(
            source=_SOURCE,
            window=HistoricalOhlcWindow(
                instrument=Instrument("ES"),
                timeframe=Timeframe(86400),
                opened_at=_BASE,
                closed_at=_BASE + timedelta(days=100),
            ),
        ),
        assembled_at=_BASE + timedelta(days=101),
        schema_version=HistoricalDatasetSchemaVersion("ohlc-replay-v1"),
        normalization_version=HistoricalDatasetNormalizationVersion(
            "day-session-only-v1"
        ),
        observation_count=100,
        actual_opened_at=_BASE,
        actual_closed_at=_BASE + timedelta(days=100),
        gaps=(),
        digest_algorithm=HistoricalDatasetDigestAlgorithm.SHA256,
        evidence_digest=HistoricalDatasetDigest("a" * 64),
    )


def test_combined_configuration_identity_is_deterministic() -> None:
    source = TurtleSoupR1Config(tick_size=Decimal("0.25"))
    policy = policy_for(TurtleSoupR1ExperimentalPolicyId.C_TRAIL1_H3)
    left = bind_research_configuration(source_config=source, management_policy=policy)
    right = bind_research_configuration(source_config=source, management_policy=policy)
    assert left.fingerprint() == right.fingerprint()
    assert left.strategy_configuration_id() == right.strategy_configuration_id()


def test_management_policy_changes_strategy_configuration_identity() -> None:
    source = TurtleSoupR1Config(tick_size=Decimal("0.25"))
    one = bind_research_configuration(
        source_config=source,
        management_policy=policy_for(TurtleSoupR1ExperimentalPolicyId.C_TRAIL1_H3),
    )
    two = bind_research_configuration(
        source_config=source,
        management_policy=policy_for(TurtleSoupR1ExperimentalPolicyId.C_TRAIL2_H3),
    )
    assert one.fingerprint() != two.fingerprint()
    assert one.strategy_configuration_id() != two.strategy_configuration_id()


def test_source_config_changes_strategy_configuration_identity() -> None:
    policy = policy_for(TurtleSoupR1ExperimentalPolicyId.C_TRAIL1_H3)
    five_ticks = bind_research_configuration(
        source_config=TurtleSoupR1Config(
            tick_size=Decimal("0.25"),
            classic_entry_offset_ticks=5,
        ),
        management_policy=policy,
    )
    six_ticks = bind_research_configuration(
        source_config=TurtleSoupR1Config(
            tick_size=Decimal("0.25"),
            classic_entry_offset_ticks=6,
        ),
        management_policy=policy,
    )
    assert five_ticks.fingerprint() != six_ticks.fingerprint()
    assert five_ticks.strategy_configuration_id() != six_ticks.strategy_configuration_id()


def _run(*, execution: ResearchExecutionModelId = _EXECUTION, costs: ResearchTransactionCostModelId = _COSTS, software: ResearchSoftwareRevision = _SOFTWARE, manifest: HistoricalDatasetManifest | None = None):
    return build_turtle_soup_r1_development_run_evidence(
        run_id=ResearchRunId(UUID("72000000-0000-0000-0000-000000000020")),
        created_at=_BASE + timedelta(days=102),
        datasets=(manifest or _manifest(),),
        simulated_start=_BASE,
        simulated_end=_BASE + timedelta(days=99),
        source_config=TurtleSoupR1Config(tick_size=Decimal("0.25")),
        management_policy=policy_for(TurtleSoupR1ExperimentalPolicyId.C_TRAIL1_H3),
        software_revision=software,
        execution_model_id=execution,
        transaction_cost_model_id=costs,
    )


def test_development_run_binds_all_material_inputs() -> None:
    built = _run()
    assert isinstance(built, Success)
    run = built.value
    assert run.execution_model_id == _EXECUTION
    assert run.transaction_cost_model_id == _COSTS
    assert run.software_revision == _SOFTWARE
    assert run.datasets == (_manifest(),)


def test_dataset_execution_cost_and_software_changes_change_run_fingerprint() -> None:
    baseline = _run()
    revised_dataset = _run(manifest=_manifest(revision_suffix=12))
    execution = _run(
        execution=ResearchExecutionModelId(
            UUID("72000000-0000-0000-0000-000000000030")
        )
    )
    costs = _run(
        costs=ResearchTransactionCostModelId(
            UUID("72000000-0000-0000-0000-000000000031")
        )
    )
    software = _run(software=ResearchSoftwareRevision("software-revision-2"))
    assert isinstance(baseline, Success)
    assert isinstance(revised_dataset, Success)
    assert isinstance(execution, Success)
    assert isinstance(costs, Success)
    assert isinstance(software, Success)
    fingerprints = {
        baseline.value.input_fingerprint,
        revised_dataset.value.input_fingerprint,
        execution.value.input_fingerprint,
        costs.value.input_fingerprint,
        software.value.input_fingerprint,
    }
    assert len(fingerprints) == 5
