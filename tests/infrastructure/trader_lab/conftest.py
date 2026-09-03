"""Shared fixture factories for Trader Lab tests."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.historical_dataset import (
    HistoricalDatasetId,
    HistoricalDatasetNormalizationVersion,
    HistoricalDatasetRevisionId,
    HistoricalDatasetSchemaVersion,
    HistoricalOhlcDatasetScope,
    build_historical_ohlc_replay_dataset,
)
from qore.infrastructure.historical_market_data import HistoricalOhlcWindow
from qore.infrastructure.market_data import (
    Instrument,
    MarketDataSnapshotId,
    OhlcSnapshot,
    Timeframe,
)
from qore.infrastructure.market_event_replay import (
    MarketCaptureLineageId,
    MarketCaptureSessionId,
    MarketCaptureSessionOrdinal,
    MarketEventAvailabilityBasis,
    MarketEventAvailabilityEvidenceReference,
    MarketEventObservationId,
    MarketIngressSequence,
    RetainedMarketEventObservation,
)
from qore.infrastructure.market_observation import (
    MarketObservationEvidenceReference,
    MarketObservationId,
    MarketPrice,
    QualifiedQuoteTickObservation,
)
from qore.infrastructure.ports import (
    AdapterId,
    ExternalSourceDescriptor,
    PortName,
    SourceId,
)
from qore.infrastructure.proprietary_accounts import CurrencyCode, MoneyAmount
from qore.infrastructure.replay_availability import (
    ReplayAvailabilityBasis,
    ReplayAvailabilityEvidenceReference,
    ReplayMarketDataObservation,
    ReplayObservationId,
)
from qore.infrastructure.research_block_bootstrap import (
    ResearchBlockBootstrapDistribution,
    ResearchBlockBootstrapDistributionId,
    ResearchBlockBootstrapPolicy,
)
from qore.infrastructure.research_economic_evidence import (
    ResearchGrossEconomicResult,
    ResearchReturnObservation,
    ResearchReturnObservationId,
)
from qore.infrastructure.research_evaluation_freeze import (
    ResearchEvaluationFreezeEvidence,
    ResearchEvaluationFreezeEvidenceId,
    ResearchEvaluationFreezeFingerprint,
)
from qore.infrastructure.research_frozen_oos_evidence import (
    ResearchFrozenOosEvidence,
    ResearchFrozenOosEvidenceId,
    ResearchFrozenOosFingerprint,
)
from qore.infrastructure.research_resampling_envelope import (
    ResearchResamplingEnvelope,
    ResearchResamplingEnvelopeId,
    ResearchResamplingEnvelopePolicy,
)
from qore.infrastructure.research_run import (
    ResearchRandomnessMode,
    ResearchReplayPolicyVersion,
    ResearchRunEvidence,
    ResearchRunId,
    ResearchSoftwareRevision,
    ResearchStrategyConfigurationId,
    build_research_run_evidence,
)
from qore.infrastructure.research_sampling_frame import ResearchSamplingFrame
from qore.infrastructure.research_serial_dependence import (
    ResearchLagOneCorrelationStatus,
    ResearchSerialDependenceDiagnostic,
    ResearchSerialDependenceDiagnosticId,
)
from qore.infrastructure.research_strategy_freeze import (
    ResearchRunStrategyBinding,
    ResearchStrategyFreezeEvidenceReference,
    ResearchStrategyParameter,
    ResearchStrategySchemaVersion,
    build_research_run_strategy_binding,
    build_research_strategy_configuration_manifest,
)
from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateBinding,
    TraderLabCandidateId,
    TraderLabCandidateVersion,
    build_trader_lab_candidate_binding,
)
from qore.infrastructure.trader_lab.fast_forward import (
    TraderLabFastForwardFingerprint,
    TraderLabFastForwardQualification,
    TraderLabFastForwardQualificationId,
    reference_trader_lab_fast_forward,
)
from qore.infrastructure.trader_lab.governed_gate import (
    TraderLabGovernedAuthenticityProof,
    TraderLabGovernedAuthorityKind,
    TraderLabGovernedDecision,
    TraderLabGovernedGate,
    TraderLabGovernedGateEvidence,
    TraderLabGovernedGateEvidenceId,
    compute_trader_lab_governed_authenticity_proof_fingerprint,
    compute_trader_lab_governed_gate_fingerprint,
    verify_governed_gate_evidence,
)
from qore.infrastructure.trader_lab.robustness import (
    TraderLabExperimentId,
    TraderLabMonteCarloEvidenceId,
    TraderLabMonteCarloExperimentEvidence,
    TraderLabRobustnessFamily,
    TraderLabStressEvidence,
    TraderLabStressEvidenceId,
    TraderLabStressStatus,
    TraderLabThreshold,
    build_trader_lab_experiment_registration,
    build_trader_lab_monte_carlo_experiment_evidence,
    build_trader_lab_stress_evidence,
    reference_trader_lab_monte_carlo,
    reference_trader_lab_stress,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceDigest,
    TraderLabEvidenceReference,
    TraderLabStage,
    TraderLabStageEvidenceId,
    TraderLabStageEvidenceRecord,
    build_trader_lab_stage_evidence,
    reference_replay_chronology,
    reference_research_economic,
    reference_research_evaluation_freeze,
    reference_research_frozen_oos,
)
from qore.kernel.result import Success

_PROCESS_TIME = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
_BASE = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
_SOURCE = ExternalSourceDescriptor(
    adapter_id=AdapterId(UUID("71000000-0000-0000-0000-000000000001")),
    source_id=SourceId(UUID("71000000-0000-0000-0000-000000000002")),
    port_name=PortName("market-data.trader-lab-test"),
)
_SCHEMA = ResearchStrategySchemaVersion("strategy-config-v1")


def _uuid(suffix: int) -> UUID:
    return UUID(f"71000000-0000-0000-0000-{suffix:012d}")


@pytest.fixture
def strategy_binding_factory() -> Callable[..., ResearchRunStrategyBinding]:
    """Return a factory that builds a valid ResearchRunStrategyBinding."""

    def _build(
        *,
        configuration_id_suffix: int = 10,
        created_at: datetime = _PROCESS_TIME,
    ) -> ResearchRunStrategyBinding:
        instrument = Instrument("EURUSD")
        timeframe = Timeframe(300)
        window = HistoricalOhlcWindow(
            instrument=instrument,
            timeframe=timeframe,
            opened_at=_BASE,
            closed_at=_BASE + timedelta(hours=1),
        )
        snapshot = OhlcSnapshot(
            snapshot_id=MarketDataSnapshotId(_uuid(20)),
            instrument=instrument,
            source=_SOURCE,
            timeframe=timeframe,
            opened_at=_BASE,
            closed_at=_BASE + timedelta(minutes=5),
            open=1.10,
            high=1.11,
            low=1.09,
            close=1.105,
        )
        replay = ReplayMarketDataObservation(
            observation_id=ReplayObservationId(_uuid(21)),
            payload=snapshot,
            availability_evidence_at=snapshot.closed_at,
            available_at=snapshot.closed_at,
            availability_basis=ReplayAvailabilityBasis.STRUCTURAL_BOUNDARY,
            availability_evidence_ref=ReplayAvailabilityEvidenceReference(_uuid(22)),
        )
        dataset = build_historical_ohlc_replay_dataset(
            dataset_id=HistoricalDatasetId(_uuid(23)),
            revision_id=HistoricalDatasetRevisionId(_uuid(24)),
            parent_revision_id=None,
            revision_reason=None,
            scope=HistoricalOhlcDatasetScope(source=_SOURCE, window=window),
            assembled_at=_PROCESS_TIME - timedelta(days=2),
            schema_version=HistoricalDatasetSchemaVersion("ohlc-replay-v1"),
            normalization_version=HistoricalDatasetNormalizationVersion("ingestion-v1"),
            observations=(replay,),
        )
        assert isinstance(dataset, Success)
        configuration_id = ResearchStrategyConfigurationId(
            _uuid(configuration_id_suffix)
        )
        built_run = build_research_run_evidence(
            run_id=ResearchRunId(_uuid(25)),
            created_at=created_at,
            datasets=(dataset.value.manifest,),
            replay_policy_version=ResearchReplayPolicyVersion("point-in-time-v1"),
            simulated_start=_BASE,
            simulated_end=_BASE + timedelta(minutes=30),
            strategy_configuration_id=configuration_id,
            software_revision=ResearchSoftwareRevision("a8a17b1c"),
            execution_model_id=None,
            transaction_cost_model_id=None,
            randomness_mode=ResearchRandomnessMode.DETERMINISTIC,
            random_seed=None,
        )
        assert isinstance(built_run, Success)
        run: ResearchRunEvidence = built_run.value
        manifest = build_research_strategy_configuration_manifest(
            configuration_id=configuration_id,
            schema_version=_SCHEMA,
            parameters=(
                ResearchStrategyParameter("entry.threshold", Decimal("0.7500")),
                ResearchStrategyParameter("risk.enabled", True),
                ResearchStrategyParameter("risk.max_positions", 2),
                ResearchStrategyParameter("session.name", "new-york"),
            ),
            frozen_at=_PROCESS_TIME - timedelta(minutes=1),
            evidence_ref=ResearchStrategyFreezeEvidenceReference(_uuid(30)),
        )
        assert isinstance(manifest, Success)
        built_binding = build_research_run_strategy_binding(
            run=run,
            manifest=manifest.value,
        )
        assert isinstance(built_binding, Success)
        return built_binding.value

    return _build


@pytest.fixture
def candidate_factory(
    strategy_binding_factory: Callable[..., ResearchRunStrategyBinding],
) -> Callable[..., TraderLabCandidateBinding]:
    """Return a factory that builds a TraderLabCandidateBinding."""

    def _build(
        *,
        candidate_suffix: int = 1,
        version: str = "v1",
        binding: ResearchRunStrategyBinding | None = None,
    ) -> TraderLabCandidateBinding:
        strategy_binding = binding if binding is not None else strategy_binding_factory()
        built = build_trader_lab_candidate_binding(
            candidate_id=_make_candidate_id(candidate_suffix),
            version=TraderLabCandidateVersion(version),
            strategy_binding=strategy_binding,
        )
        assert isinstance(built, Success)
        return built.value

    return _build


def _make_candidate_id(suffix: int) -> TraderLabCandidateId:
    return TraderLabCandidateId(_uuid(suffix))


def _evaluation_freeze(
    candidate: TraderLabCandidateBinding,
    *,
    suffix: int,
) -> ResearchEvaluationFreezeEvidence:
    """Build a minimal evaluation-freeze evidence bound to the candidate lineage.

    ``reference_research_evaluation_freeze`` only reads ``evidence_id``,
    ``strategy_binding``, and ``fingerprint``, so a hollow frozen object suffices.
    """

    freeze = object.__new__(ResearchEvaluationFreezeEvidence)
    object.__setattr__(
        freeze, "evidence_id", ResearchEvaluationFreezeEvidenceId(_uuid(suffix))
    )
    object.__setattr__(freeze, "strategy_binding", candidate.strategy_binding)
    object.__setattr__(
        freeze, "fingerprint", ResearchEvaluationFreezeFingerprint("f" * 64)
    )
    return freeze


def _frozen_oos(
    candidate: TraderLabCandidateBinding,
    *,
    suffix: int,
) -> ResearchFrozenOosEvidence:
    """Build a frozen-OOS evidence object bound to the candidate strategy lineage."""

    freeze = object.__new__(ResearchEvaluationFreezeEvidence)
    object.__setattr__(freeze, "strategy_binding", candidate.strategy_binding)
    frozen = object.__new__(ResearchFrozenOosEvidence)
    object.__setattr__(frozen, "evidence_id", ResearchFrozenOosEvidenceId(_uuid(suffix)))
    object.__setattr__(frozen, "evaluation_freeze", freeze)
    object.__setattr__(frozen, "fingerprint", ResearchFrozenOosFingerprint("f" * 64))
    return frozen


def _stress_evidence(
    candidate: TraderLabCandidateBinding,
    *,
    suffix: int,
) -> TraderLabStressEvidence:
    """Build a QUALIFIED typed stress-evidence object bound to the candidate.

    Uses the real builder so the fingerprint is exact and the fail-closed status
    gate in ``reference_trader_lab_stress`` passes.
    """

    built = build_trader_lab_stress_evidence(
        evidence_id=TraderLabStressEvidenceId(_uuid(suffix)),
        candidate=candidate,
        family=TraderLabRobustnessFamily.COST_PERTURBATION,
        scenario="cost-perturbation-2x",
        bounds=(Decimal("0.000"), Decimal("0.010")),
        status=TraderLabStressStatus.QUALIFIED,
        certified_at=_PROCESS_TIME,
    )
    assert isinstance(built, Success)
    return built.value


_GATE_AUTHORITY_KIND: dict[
    TraderLabGovernedGate, TraderLabGovernedAuthorityKind
] = {
    TraderLabGovernedGate.RISK_REVIEW: TraderLabGovernedAuthorityKind.RISK,
    TraderLabGovernedGate.CIBO_REVIEW: TraderLabGovernedAuthorityKind.CIBO,
    TraderLabGovernedGate.INDEPENDENT_VALIDATION: (
        TraderLabGovernedAuthorityKind.INDEPENDENT_VALIDATION
    ),
}


def _governed_gate_evidence(
    candidate: TraderLabCandidateBinding,
    *,
    gate: TraderLabGovernedGate,
    suffix: int,
) -> TraderLabGovernedGateEvidence:
    """Build an APPROVED governed review evidence carrier bound to the candidate.

    This is a typed carrier only (a locally constructed APPROVED record). It is
    NOT authentic governed evidence; only ``verify_governed_gate_evidence``
    through an externally issued authenticity proof can make it qualify a stage.
    """

    authority_kind = _GATE_AUTHORITY_KIND[gate]
    authority_name = f"{authority_kind.value}-authority"
    fingerprint = compute_trader_lab_governed_gate_fingerprint(
        evidence_id=TraderLabGovernedGateEvidenceId(_uuid(suffix)),
        gate=gate,
        authority_kind=authority_kind,
        candidate=candidate,
        authority_id=_uuid(suffix + 100000),
        authority_name=authority_name,
        decision=TraderLabGovernedDecision.APPROVED,
        decided_at=_PROCESS_TIME,
        authority_evidence_digest=TraderLabEvidenceDigest("b" * 64),
    )
    return TraderLabGovernedGateEvidence(
        evidence_id=TraderLabGovernedGateEvidenceId(_uuid(suffix)),
        gate=gate,
        authority_kind=authority_kind,
        candidate=candidate,
        authority_id=_uuid(suffix + 100000),
        authority_name=authority_name,
        decision=TraderLabGovernedDecision.APPROVED,
        decided_at=_PROCESS_TIME,
        authority_evidence_digest=TraderLabEvidenceDigest("b" * 64),
        fingerprint=fingerprint,
    )


def _issue_external_authenticity_proof(
    *,
    evidence: TraderLabGovernedGateEvidence,
    candidate: TraderLabCandidateBinding,
    issued_at: datetime = _PROCESS_TIME,
) -> TraderLabGovernedAuthenticityProof:
    """Issue a sealed authenticity proof as an EXTERNAL authority (test double).

    This represents the owning authority's issuance capability, which the
    production Trader Lab does not possess. It deliberately constructs the frozen
    proof with ``object.__new__``/``object.__setattr__`` to set the sealed
    ``_issued`` marker, exactly as an authority OUTSIDE the Lab would. The issuer
    is bound to the evidence's exact deciding authority, and the proof is issued
    at or after the decision.
    """

    proof_fingerprint = compute_trader_lab_governed_authenticity_proof_fingerprint(
        evidence_fingerprint=evidence.fingerprint,
        candidate=candidate,
        gate=evidence.gate,
        authority_kind=evidence.authority_kind,
        issuer_id=evidence.authority_id,
        issued_at=issued_at,
    )
    proof = object.__new__(TraderLabGovernedAuthenticityProof)
    object.__setattr__(proof, "evidence_fingerprint", evidence.fingerprint)
    object.__setattr__(proof, "candidate", candidate)
    object.__setattr__(proof, "gate", evidence.gate)
    object.__setattr__(proof, "authority_kind", evidence.authority_kind)
    object.__setattr__(proof, "issuer_id", evidence.authority_id)
    object.__setattr__(proof, "issued_at", issued_at)
    object.__setattr__(proof, "proof_fingerprint", proof_fingerprint)
    object.__setattr__(proof, "_issued", True)
    return proof


def _governed_reference(
    candidate: TraderLabCandidateBinding,
    *,
    gate: TraderLabGovernedGate,
    suffix: int,
) -> TraderLabEvidenceReference:
    """Verify a governed carrier through an externally issued authenticity proof."""

    evidence = _governed_gate_evidence(candidate, gate=gate, suffix=suffix)
    proof = _issue_external_authenticity_proof(evidence=evidence, candidate=candidate)
    built = verify_governed_gate_evidence(candidate, evidence, proof)
    assert isinstance(built, Success), built
    return built.value


def _return_observation(
    candidate: TraderLabCandidateBinding,
    *,
    suffix: int,
) -> ResearchReturnObservation:
    """Build a minimal research return observation bound to the candidate run.

    ``reference_research_economic`` reads the derived ``run``/``basis`` properties
    plus ``observation_id``/``capital_basis``/``return_rate``/``observed_at``, so a
    hollow gross-result source bound to the candidate run suffices.
    """

    gross = object.__new__(ResearchGrossEconomicResult)
    object.__setattr__(gross, "run", candidate.strategy_binding.run)
    observation = object.__new__(ResearchReturnObservation)
    object.__setattr__(
        observation, "observation_id", ResearchReturnObservationId(_uuid(suffix))
    )
    object.__setattr__(observation, "source_result", gross)
    object.__setattr__(
        observation,
        "capital_basis",
        MoneyAmount(currency=CurrencyCode("USD"), amount=Decimal("100000")),
    )
    object.__setattr__(observation, "observed_at", _PROCESS_TIME)
    object.__setattr__(observation, "return_rate", Decimal("0.05"))
    return observation


def _distribution(
    candidate: TraderLabCandidateBinding,
    *,
    suffix: int,
) -> ResearchBlockBootstrapDistribution:
    """Build a block-bootstrap distribution object bound to the candidate lineage."""

    frozen = _frozen_oos(candidate, suffix=suffix + 2000)
    frame = object.__new__(ResearchSamplingFrame)
    object.__setattr__(frame, "frozen_oos", frozen)
    diagnostic = object.__new__(ResearchSerialDependenceDiagnostic)
    object.__setattr__(
        diagnostic,
        "diagnostic_id",
        ResearchSerialDependenceDiagnosticId(_uuid(suffix + 2001)),
    )
    object.__setattr__(diagnostic, "frame", frame)
    object.__setattr__(
        diagnostic, "status", ResearchLagOneCorrelationStatus.DEFINED
    )
    distribution = object.__new__(ResearchBlockBootstrapDistribution)
    object.__setattr__(
        distribution,
        "distribution_id",
        ResearchBlockBootstrapDistributionId(_uuid(suffix + 2002)),
    )
    object.__setattr__(distribution, "diagnostic", diagnostic)
    object.__setattr__(
        distribution,
        "policy",
        ResearchBlockBootstrapPolicy(block_length=2, resample_count=16, seed=42),
    )
    object.__setattr__(distribution, "sample_size", 4)
    object.__setattr__(distribution, "source_mean", Decimal("0.05"))
    object.__setattr__(
        distribution, "resampled_means", (Decimal("0.04"), Decimal("0.06"))
    )
    return distribution


def _envelope(
    candidate: TraderLabCandidateBinding,
    *,
    suffix: int,
) -> ResearchResamplingEnvelope:
    """Build a resampling envelope object bound to the candidate lineage."""

    distribution = _distribution(candidate, suffix=suffix)
    envelope = object.__new__(ResearchResamplingEnvelope)
    object.__setattr__(
        envelope, "envelope_id", ResearchResamplingEnvelopeId(_uuid(suffix + 3000))
    )
    object.__setattr__(envelope, "distribution", distribution)
    object.__setattr__(
        envelope,
        "policy",
        ResearchResamplingEnvelopePolicy(
            lower_quantile_bps=500, upper_quantile_bps=9500
        ),
    )
    object.__setattr__(envelope, "empirical_sample_size", 4)
    object.__setattr__(envelope, "lower_mean", Decimal("0.04"))
    object.__setattr__(envelope, "median_mean", Decimal("0.05"))
    object.__setattr__(envelope, "upper_mean", Decimal("0.06"))
    return envelope


def _fast_forward_qualification(
    candidate: TraderLabCandidateBinding,
    *,
    suffix: int,
) -> TraderLabFastForwardQualification:
    """Build a fast-forward qualification object bound to the candidate."""

    qualification = object.__new__(TraderLabFastForwardQualification)
    object.__setattr__(
        qualification,
        "qualification_id",
        TraderLabFastForwardQualificationId(_uuid(suffix)),
    )
    object.__setattr__(qualification, "candidate", candidate)
    object.__setattr__(
        qualification, "fingerprint", TraderLabFastForwardFingerprint("a" * 64)
    )
    return qualification


def _replay_price(value: str) -> MarketPrice:
    return MarketPrice(Decimal(value))


def _replay_source() -> ExternalSourceDescriptor:
    return ExternalSourceDescriptor(
        adapter_id=AdapterId(UUID(int=7000001)),
        source_id=SourceId(UUID(int=7000002)),
        port_name=PortName("market-data.trader-lab-conftest"),
    )


def _replay_quote(*, observation_id: int, observed_at: datetime) -> QualifiedQuoteTickObservation:
    return QualifiedQuoteTickObservation(
        observation_id=MarketObservationId(UUID(int=observation_id)),
        instrument=Instrument("EURUSD"),
        source=_replay_source(),
        observed_at=observed_at,
        bid=_replay_price("1.10000"),
        ask=_replay_price("1.10010"),
        evidence_ref=MarketObservationEvidenceReference(UUID(int=observation_id + 100000)),
    )


def _replay_event(
    *,
    event_id: int,
    sequence: int,
    observed_at: datetime,
    available_at: datetime,
) -> RetainedMarketEventObservation:
    received = observed_at + timedelta(seconds=1)
    ingress = received + timedelta(milliseconds=1)
    return RetainedMarketEventObservation(
        event_id=MarketEventObservationId(UUID(int=event_id)),
        payload=_replay_quote(observation_id=event_id + 50, observed_at=observed_at),
        capture_lineage_id=MarketCaptureLineageId(UUID(int=400)),
        capture_session_id=MarketCaptureSessionId(UUID(int=500)),
        capture_session_ordinal=MarketCaptureSessionOrdinal(0),
        ingress_sequence=MarketIngressSequence(sequence),
        boundary_received_at=received,
        core_ingress_at=ingress,
        availability_evidence_at=ingress,
        available_at=available_at,
        availability_basis=MarketEventAvailabilityBasis.CORE_INGRESS,
        availability_evidence_ref=MarketEventAvailabilityEvidenceReference(
            UUID(int=event_id + 200000)
        ),
    )


def _replay_observations() -> tuple[RetainedMarketEventObservation, ...]:
    return (
        _replay_event(
            event_id=10,
            sequence=0,
            observed_at=_BASE,
            available_at=_BASE + timedelta(minutes=1),
        ),
        _replay_event(
            event_id=11,
            sequence=1,
            observed_at=_BASE + timedelta(minutes=2),
            available_at=_BASE + timedelta(minutes=3),
        ),
        _replay_event(
            event_id=12,
            sequence=2,
            observed_at=_BASE + timedelta(minutes=4),
            available_at=_BASE + timedelta(minutes=5),
        ),
    )


def _monte_carlo_evidence(
    candidate: TraderLabCandidateBinding,
    *,
    suffix: int,
) -> TraderLabMonteCarloExperimentEvidence:
    """Build a QUALIFIED Monte Carlo experiment evidence bound to the candidate.

    Reuses the hollow block-bootstrap envelope fixtures plus a real frozen
    registration whose threshold actually participates in the derived status.
    """

    registration_built = build_trader_lab_experiment_registration(
        experiment_id=TraderLabExperimentId(_uuid(suffix)),
        candidate=candidate,
        family=TraderLabRobustnessFamily.BLOCK_BOOTSTRAP,
        algorithm="research.circular_block_bootstrap",
        algorithm_version="v1",
        block_length=2,
        seed=42,
        simulation_count=16,
        min_sample_size=4,
        thresholds=(
            TraderLabThreshold("distribution.source_mean", Decimal("-1.0"), None),
        ),
        registered_at=_PROCESS_TIME,
    )
    assert isinstance(registration_built, Success)
    envelope = _envelope(candidate, suffix=suffix + 4000)
    built = build_trader_lab_monte_carlo_experiment_evidence(
        evidence_id=TraderLabMonteCarloEvidenceId(_uuid(suffix + 8000)),
        registration=registration_built.value,
        policy=ResearchBlockBootstrapPolicy(
            block_length=2, resample_count=16, seed=42
        ),
        distribution=envelope.distribution,
        envelope=envelope,
    )
    assert isinstance(built, Success), built
    return built.value


def _stage_reference(
    stage: TraderLabStage,
    candidate: TraderLabCandidateBinding,
    suffix: int,
) -> TraderLabEvidenceReference:
    if stage is TraderLabStage.RESEARCH:
        return reference_research_evaluation_freeze(
            candidate, _evaluation_freeze(candidate, suffix=suffix)
        )
    if stage is TraderLabStage.REPLAY:
        return reference_replay_chronology(_replay_observations())
    if stage is TraderLabStage.FAST_FORWARD:
        return reference_trader_lab_fast_forward(
            candidate, _fast_forward_qualification(candidate, suffix=suffix)
        )
    if stage is TraderLabStage.OOS:
        return reference_research_frozen_oos(
            candidate, _frozen_oos(candidate, suffix=suffix + 1000)
        )
    if stage is TraderLabStage.STRESS:
        return reference_trader_lab_stress(
            candidate, _stress_evidence(candidate, suffix=suffix)
        )
    if stage is TraderLabStage.MONTE_CARLO:
        return reference_trader_lab_monte_carlo(
            candidate, _monte_carlo_evidence(candidate, suffix=suffix)
        )
    if stage is TraderLabStage.RISK_REVIEW:
        return _governed_reference(
            candidate, gate=TraderLabGovernedGate.RISK_REVIEW, suffix=suffix
        )
    if stage is TraderLabStage.CIBO_REVIEW:
        return _governed_reference(
            candidate, gate=TraderLabGovernedGate.CIBO_REVIEW, suffix=suffix
        )
    if stage is TraderLabStage.INDEPENDENT_VALIDATION:
        return _governed_reference(
            candidate,
            gate=TraderLabGovernedGate.INDEPENDENT_VALIDATION,
            suffix=suffix,
        )
    raise AssertionError(f"unexpected stage: {stage}")


@pytest.fixture
def stage_evidence_factory() -> Callable[..., TraderLabStageEvidenceRecord]:
    """Return a factory that builds a stage evidence record with the correct kind."""

    def _build(
        *,
        stage: TraderLabStage,
        candidate: TraderLabCandidateBinding,
        evidence_suffix: int,
        produced_at: datetime = _PROCESS_TIME,
    ) -> TraderLabStageEvidenceRecord:
        reference = _stage_reference(stage, candidate, evidence_suffix + 500)
        built = build_trader_lab_stage_evidence(
            evidence_id=TraderLabStageEvidenceId(_uuid(evidence_suffix)),
            stage=stage,
            candidate=candidate,
            source_reference=reference,
            produced_at=produced_at,
        )
        assert isinstance(built, Success)
        return built.value

    return _build


@pytest.fixture
def frozen_oos_factory() -> Callable[..., ResearchFrozenOosEvidence]:
    """Return a factory that builds a frozen-OOS evidence object."""

    def _build(
        candidate: TraderLabCandidateBinding,
        *,
        suffix: int,
    ) -> ResearchFrozenOosEvidence:
        return _frozen_oos(candidate, suffix=suffix)

    return _build


@pytest.fixture
def replay_observations_factory() -> Callable[[], tuple[RetainedMarketEventObservation, ...]]:
    """Return a factory that builds a replay chronology observation tuple."""

    return _replay_observations


@pytest.fixture
def economic_reference_factory() -> Callable[
    [TraderLabCandidateBinding], TraderLabEvidenceReference
]:
    """Return a factory that builds a candidate-bound economic evidence reference."""

    def _build(candidate: TraderLabCandidateBinding) -> TraderLabEvidenceReference:
        return reference_research_economic(
            candidate, _return_observation(candidate, suffix=900)
        )

    return _build


@pytest.fixture
def return_observation_factory() -> Callable[..., ResearchReturnObservation]:
    """Return a factory that builds a research return observation with tunable scale."""

    def _build(
        candidate: TraderLabCandidateBinding,
        *,
        return_rate: str = "0.05",
        amount: str = "100000",
        suffix: int = 800,
    ) -> ResearchReturnObservation:
        gross = object.__new__(ResearchGrossEconomicResult)
        object.__setattr__(gross, "run", candidate.strategy_binding.run)
        observation = object.__new__(ResearchReturnObservation)
        object.__setattr__(
            observation,
            "observation_id",
            ResearchReturnObservationId(_uuid(suffix)),
        )
        object.__setattr__(observation, "source_result", gross)
        object.__setattr__(
            observation,
            "capital_basis",
            MoneyAmount(currency=CurrencyCode("USD"), amount=Decimal(amount)),
        )
        object.__setattr__(observation, "observed_at", _PROCESS_TIME)
        object.__setattr__(observation, "return_rate", Decimal(return_rate))
        return observation

    return _build


@pytest.fixture
def governed_reference_factory() -> Callable[..., TraderLabEvidenceReference]:
    """Return a factory that builds an APPROVED governed review reference."""

    def _build(
        candidate: TraderLabCandidateBinding,
        *,
        gate: TraderLabGovernedGate,
        suffix: int = 700,
    ) -> TraderLabEvidenceReference:
        return _governed_reference(candidate, gate=gate, suffix=suffix)

    return _build


@pytest.fixture
def research_reference_factory() -> Callable[..., TraderLabEvidenceReference]:
    """Return a factory that builds the RESEARCH-stage evaluation-freeze reference."""

    def _build(
        candidate: TraderLabCandidateBinding,
        *,
        suffix: int,
    ) -> TraderLabEvidenceReference:
        return reference_research_evaluation_freeze(
            candidate, _evaluation_freeze(candidate, suffix=suffix)
        )

    return _build
