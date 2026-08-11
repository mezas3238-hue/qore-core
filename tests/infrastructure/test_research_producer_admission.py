from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest

from qore.infrastructure.dataset_integrity_qualification import (
    build_dataset_integrity_qualification,
    build_integrity_qualified_research_run,
)
from qore.infrastructure.historical_dataset import (
    HistoricalDatasetId,
    HistoricalDatasetNormalizationVersion,
    HistoricalDatasetRevisionId,
    HistoricalDatasetSchemaVersion,
    HistoricalOhlcDatasetScope,
    build_historical_ohlc_replay_dataset,
)
from qore.infrastructure.historical_market_data import HistoricalOhlcWindow
from qore.infrastructure.hosting_latency_safety import HostingLatencyDuration
from qore.infrastructure.hosting_reliability_lab import HostingReliabilityEvidenceReference
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.market_data_integrity import (
    MarketDataIngressRecord,
    MarketDataIntegrityAssessmentId,
    MarketDataIntegrityCertificateId,
    MarketDataIntegrityPolicy,
    evaluate_market_data_integrity,
    issue_market_data_integrity_certificate,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.replay_availability import (
    ReplayAvailabilityBasis,
    ReplayAvailabilityEvidenceReference,
    ReplayMarketDataObservation,
    ReplayObservationId,
)
from qore.infrastructure.research_lineage_errors import ResearchLineageFingerprintError
from qore.infrastructure.research_producer_admission import (
    ResearchProducerAdmissionEvidence,
    ResearchProducerAdmissionFingerprint,
    ResearchProducerAdmissionValidationError,
    _compute_admission_fingerprint,
)
from qore.infrastructure.research_run import (
    ResearchRandomnessMode,
    ResearchReplayPolicyVersion,
    ResearchRunId,
    ResearchSoftwareRevision,
    ResearchStrategyConfigurationId,
    build_research_run_evidence,
)
from qore.infrastructure.research_strategy_freeze import (
    ResearchStrategyFreezeEvidenceReference,
    ResearchStrategyParameter,
    ResearchStrategySchemaVersion,
    build_research_run_strategy_binding,
    build_research_strategy_configuration_manifest,
)
from qore.kernel.result import Success

_BASE = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
_REVISION = ResearchSoftwareRevision("phase1b-test-revision")
_POLICY = MarketDataIntegrityPolicy(
    max_delivery_delay=HostingLatencyDuration.from_milliseconds(2_000)
)


def _uuid(suffix: int) -> UUID:
    return UUID(f"8b000000-0000-0000-0000-{suffix:012d}")


def _admission(*, run_suffix: int = 1) -> ResearchProducerAdmissionEvidence:
    source = ExternalSourceDescriptor(
        adapter_id=AdapterId(_uuid(10_000)),
        source_id=SourceId(_uuid(20_000)),
        port_name=PortName("market-data.phase1b-admission-test"),
    )
    instrument = Instrument("EURUSD")
    timeframe = Timeframe(60)
    snapshot = OhlcSnapshot(
        snapshot_id=MarketDataSnapshotId(_uuid(30_000)),
        instrument=instrument,
        source=source,
        timeframe=timeframe,
        opened_at=_BASE,
        closed_at=_BASE + timedelta(minutes=1),
        open=1.10,
        high=1.11,
        low=1.09,
        close=1.105,
    )
    hosting_received_at = snapshot.closed_at + timedelta(milliseconds=100)
    record = MarketDataIngressRecord(
        snapshot=snapshot,
        hosting_received_at=hosting_received_at,
        core_ingress_at=hosting_received_at + timedelta(milliseconds=1),
        normalization_evidence_ref=HostingReliabilityEvidenceReference(
            _uuid(40_000)
        ),
    )
    assessed = evaluate_market_data_integrity(
        record=record,
        accepted_history=(),
        policy=_POLICY,
        assessment_id=MarketDataIntegrityAssessmentId(_uuid(50_000)),
        assessed_at=record.core_ingress_at + timedelta(milliseconds=1),
    )
    assert isinstance(assessed, Success)
    issued = issue_market_data_integrity_certificate(
        assessed.value,
        certificate_id=MarketDataIntegrityCertificateId(_uuid(60_000)),
        issued_at=assessed.value.assessed_at + timedelta(milliseconds=1),
        evidence_ref=HostingReliabilityEvidenceReference(_uuid(70_000)),
    )
    assert isinstance(issued, Success)

    observation = ReplayMarketDataObservation(
        observation_id=ReplayObservationId(_uuid(80_000)),
        payload=snapshot,
        availability_evidence_at=snapshot.closed_at,
        available_at=snapshot.closed_at + timedelta(milliseconds=200),
        availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
        availability_evidence_ref=ReplayAvailabilityEvidenceReference(
            _uuid(90_000)
        ),
    )
    dataset_result = build_historical_ohlc_replay_dataset(
        dataset_id=HistoricalDatasetId(_uuid(100_000)),
        revision_id=HistoricalDatasetRevisionId(_uuid(110_000)),
        parent_revision_id=None,
        revision_reason=None,
        scope=HistoricalOhlcDatasetScope(
            source=source,
            window=HistoricalOhlcWindow(
                instrument=instrument,
                timeframe=timeframe,
                opened_at=_BASE,
                closed_at=_BASE + timedelta(minutes=1),
            ),
        ),
        assembled_at=_BASE + timedelta(days=1),
        schema_version=HistoricalDatasetSchemaVersion("ohlc-replay-v1"),
        normalization_version=HistoricalDatasetNormalizationVersion(
            "canonical-ingestion-v1"
        ),
        observations=(observation,),
    )
    assert isinstance(dataset_result, Success)
    qualified_dataset = build_dataset_integrity_qualification(
        dataset=dataset_result.value,
        qualification_policy=_POLICY,
        predecessor_certificate=None,
        certificates=(issued.value,),
    )
    assert isinstance(qualified_dataset, Success)

    configuration_id = ResearchStrategyConfigurationId(_uuid(120_000))
    strategy_manifest = build_research_strategy_configuration_manifest(
        configuration_id=configuration_id,
        schema_version=ResearchStrategySchemaVersion("v1"),
        parameters=(ResearchStrategyParameter("alpha", 1),),
        frozen_at=_BASE + timedelta(hours=1),
        evidence_ref=ResearchStrategyFreezeEvidenceReference(_uuid(130_000)),
    )
    assert isinstance(strategy_manifest, Success)
    run_result = build_research_run_evidence(
        run_id=ResearchRunId(_uuid(140_000 + run_suffix)),
        created_at=_BASE + timedelta(days=2, seconds=run_suffix),
        datasets=(dataset_result.value.manifest,),
        replay_policy_version=ResearchReplayPolicyVersion("point-in-time-v1"),
        simulated_start=_BASE,
        simulated_end=_BASE + timedelta(minutes=1),
        strategy_configuration_id=configuration_id,
        software_revision=_REVISION,
        execution_model_id=None,
        transaction_cost_model_id=None,
        randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
        random_seed=None,
    )
    assert isinstance(run_result, Success)
    qualified_run = build_integrity_qualified_research_run(
        run=run_result.value,
        qualifications=(qualified_dataset.value,),
    )
    assert isinstance(qualified_run, Success)
    binding_result = build_research_run_strategy_binding(
        run=run_result.value,
        manifest=strategy_manifest.value,
    )
    assert isinstance(binding_result, Success)
    return ResearchProducerAdmissionEvidence(
        integrity_qualified_run=qualified_run.value,
        strategy_binding=binding_result.value,
    )


def test_admission_derives_exact_session_and_single_source_fingerprint() -> None:
    admission = _admission()
    assert admission.execution_session.strategy_binding == admission.strategy_binding
    assert admission.execution_session.replay_datasets == (
        admission.integrity_qualified_run.qualifications[0].dataset,
    )
    assert admission.admission_fingerprint == _compute_admission_fingerprint(
        admission.integrity_qualified_run.fingerprint,
        admission.strategy_binding.binding_fingerprint,
        admission.execution_session.session_fingerprint,
    )


def test_admission_rejects_different_run_binding() -> None:
    first = _admission(run_suffix=1)
    second = _admission(run_suffix=2)
    with pytest.raises(ResearchProducerAdmissionValidationError):
        ResearchProducerAdmissionEvidence(
            integrity_qualified_run=first.integrity_qualified_run,
            strategy_binding=second.strategy_binding,
        )


@pytest.mark.parametrize("value", ["", "0" * 63, "0" * 65, "G" * 64])
def test_admission_fingerprint_rejects_noncanonical_values(value: str) -> None:
    with pytest.raises(ResearchLineageFingerprintError):
        ResearchProducerAdmissionFingerprint(value)


def test_admission_production_source_has_no_ellipsis_or_pass() -> None:
    path = Path("src/qore/infrastructure/research_producer_admission.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assert not any(
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and node.value.value is Ellipsis
        for node in ast.walk(tree)
    )
    assert not any(isinstance(node, ast.Pass) for node in ast.walk(tree))


def test_admission_source_extracts_qualification_dataset_without_sets() -> None:
    source = Path(
        "src/qore/infrastructure/research_producer_admission.py"
    ).read_text(encoding="utf-8")
    assert "_dataset_key(qualification.dataset)" in source
    assert "qualified_keys = {" not in source
    assert "session_keys = {" not in source
