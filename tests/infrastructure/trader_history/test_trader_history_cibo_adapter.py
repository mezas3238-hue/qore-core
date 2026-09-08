from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from qore.infrastructure.cibo_trader_capability_profile import (
    CiboCertificationState,
    CiboEvidenceFreshness,
    CiboEvidenceFreshnessState,
    CiboSpecialtyCode,
    CiboTimeframeCode,
    CiboTradeableMarketRef,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.infrastructure.research_sample_partition import SampleRole
from qore.infrastructure.trader_history.cibo_adapter import (
    CiboTraderHistoryAdapterError,
    project_cibo_capability_profile,
)
from qore.infrastructure.trader_history.contracts import (
    TraderHistoryEpistemicStatus,
    TraderHistoryEvidenceRef,
    TraderHistoryFavorableKind,
    TraderHistoryHypothesisId,
    TraderHistoryMarketRef,
    TraderHistoryMetric,
    TraderHistoryPartitionIdentity,
    TraderHistoryProducerId,
    TraderHistorySoftwareSha,
    TraderHistoryStudyId,
    TraderHistoryStudyKind,
    TraderHistoryStudyRecord,
    TraderHistoryStudyVersion,
    TraderHistorySufficiency,
    TraderHistoryTimeframeRef,
    TraderVersionIdentity,
    build_study_record,
    build_trader_version_identity,
)
from qore.infrastructure.trader_history.registry import (
    TraderHistoricalIntelligenceRegistry,
)
from qore.infrastructure.traders.contracts import (
    DemoTradingConfigFingerprint,
    DemoTradingMethodologyFingerprint,
    DemoTradingMethodologyId,
    DemoTradingMethodologyVersion,
    DemoTradingTraderCode,
    DemoTradingTraderVersion,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def _fp(n: int) -> str:
    return f"{n:064x}"


def _fp40(n: int) -> str:
    return f"{n:040x}"


def _version(config: int = 1) -> TraderVersionIdentity:
    return build_trader_version_identity(
        trader_code=DemoTradingTraderCode("vt-08"),
        version=DemoTradingTraderVersion("v1"),
        config_fingerprint=DemoTradingConfigFingerprint(_fp(config)),
        methodology_id=DemoTradingMethodologyId("ny-precision-core"),
        methodology_version=DemoTradingMethodologyVersion("v1"),
        methodology_fingerprint=DemoTradingMethodologyFingerprint(_fp(2)),
        software_sha=TraderHistorySoftwareSha(_fp40(3)),
    )


def _identity() -> ResearchDecisionEvaluatorIdentity:
    return ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily("virtual.trader.vt08"),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision("rev-1"),
    )


def _ref(value: str = "evidence:replay") -> TraderHistoryEvidenceRef:
    return TraderHistoryEvidenceRef(value)


def _metric(value: str = "0.10") -> TraderHistoryMetric:
    return TraderHistoryMetric("expectancy", Decimal(value), (_ref(),))


_DEV_PARTITION_ID = UUID("00000000-0000-0000-0000-000000000001")


def _dev_partition(n: int = 90) -> TraderHistoryPartitionIdentity:
    return TraderHistoryPartitionIdentity(
        _DEV_PARTITION_ID,
        _fp(n),
        SampleRole.DEVELOPMENT,
    )


def _study(
    *,
    version: TraderVersionIdentity,
    metrics: tuple[TraderHistoryMetric, ...],
    condition: TraderHistoryFavorableKind | None = None,
    kind: TraderHistoryStudyKind = TraderHistoryStudyKind.REPLAY,
) -> TraderHistoryStudyRecord:
    return build_study_record(
        study_id=TraderHistoryStudyId(uuid4()),
        study_version=TraderHistoryStudyVersion("v1"),
        trader_version=version,
        kind=kind,
        epistemic_status=TraderHistoryEpistemicStatus.CERTIFIED,
        sufficiency=TraderHistorySufficiency.SUFFICIENT,
        produced_at=_NOW,
        producer=TraderHistoryProducerId("trader-lab"),
        market_scope=(TraderHistoryMarketRef("EUR/USD"),),
        timeframe_scope=(TraderHistoryTimeframeRef("h1"),),
        partitions=(_dev_partition(),),
        quantitative_claims=metrics,
        condition=condition,
    )


def _freshness() -> CiboEvidenceFreshness:
    return CiboEvidenceFreshness(
        state=CiboEvidenceFreshnessState.CURRENT,
        as_of=_NOW,
    )


def _profile_kwargs(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "trader_identity": _identity(),
        "specialty": CiboSpecialtyCode("trend-following"),
        "qualified_markets": (CiboTradeableMarketRef("EUR/USD"),),
        "qualified_timeframes": (CiboTimeframeCode("h1"),),
        "certification_state": CiboCertificationState.EVIDENCE_COLLECTED,
        "freshness": _freshness(),
    }
    kwargs.update(overrides)
    return kwargs


def test_adapter_rejects_cross_trader_identity_binding() -> None:
    version = _version()
    registry = TraderHistoricalIntelligenceRegistry(
        records=(_study(version=version, metrics=(_metric("0.12"),)),)
    )
    wrong_identity = ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily("virtual.trader.vt01"),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision("rev-1"),
    )

    result = project_cibo_capability_profile(
        registry,
        version,
        **_profile_kwargs(trader_identity=wrong_identity),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboTraderHistoryAdapterError)
    assert "must match the exact Trader version code" in str(result.error)


def test_adapter_projects_certified_metrics() -> None:
    version = _version()
    registry = TraderHistoricalIntelligenceRegistry(
        records=(_study(version=version, metrics=(_metric("0.12"),)),)
    )
    result = project_cibo_capability_profile(
        registry,
        version,
        **_profile_kwargs(),
    )
    assert isinstance(result, Success)
    profile = result.value
    assert [m.metric_code for m in profile.economic_metrics] == ["expectancy"]
    assert profile.economic_metrics[0].value == Decimal("0.12")


def test_adapter_never_manufactures_demo_eligibility() -> None:
    version = _version()
    registry = TraderHistoricalIntelligenceRegistry(
        records=(_study(version=version, metrics=(_metric("0.12"),)),)
    )
    result = project_cibo_capability_profile(
        registry,
        version,
        **_profile_kwargs(),
    )
    assert isinstance(result, Success)
    profile = result.value
    states = {state.value for state in CiboCertificationState}
    assert "demo-eligible" not in states
    assert profile.certification_state is not CiboCertificationState.PROMOTION_RECOMMENDED


def test_adapter_maps_condition_to_regime_evidence() -> None:
    version = _version()
    registry = TraderHistoricalIntelligenceRegistry(
        records=(
            _study(
                version=version,
                metrics=(_metric("0.12"),),
                condition=TraderHistoryFavorableKind.FAVORABLE,
            ),
        )
    )
    result = project_cibo_capability_profile(
        registry,
        version,
        **_profile_kwargs(),
    )
    assert isinstance(result, Success)
    profile = result.value
    assert profile.regime_evidence
    assert profile.regime_evidence[0].regime.value == "favorable"


def test_adapter_excludes_insufficient_and_exploratory() -> None:
    version = _version()
    exploratory = build_study_record(
        study_id=TraderHistoryStudyId(uuid4()),
        study_version=TraderHistoryStudyVersion("v1"),
        trader_version=version,
        kind=TraderHistoryStudyKind.CHARACTERIZATION,
        epistemic_status=TraderHistoryEpistemicStatus.OBSERVED,
        sufficiency=TraderHistorySufficiency.INSUFFICIENT,
        produced_at=_NOW,
        producer=TraderHistoryProducerId("trader-lab"),
        market_scope=(TraderHistoryMarketRef("EUR/USD"),),
        timeframe_scope=(TraderHistoryTimeframeRef("h1"),),
        quantitative_claims=(_metric("0.99"),),
    )
    registry = TraderHistoricalIntelligenceRegistry(records=(exploratory,))
    result = project_cibo_capability_profile(
        registry,
        version,
        **_profile_kwargs(),
    )
    assert isinstance(result, Success)
    assert result.value.economic_metrics == ()


def test_adapter_does_not_mutate_history() -> None:
    version = _version()
    study = _study(version=version, metrics=(_metric("0.12"),))
    registry = TraderHistoricalIntelligenceRegistry(records=(study,))
    before = registry.logical_values()
    result = project_cibo_capability_profile(
        registry,
        version,
        **_profile_kwargs(),
    )
    assert isinstance(result, Success)
    assert registry.logical_values() == before
    assert registry.records == (study,)


def test_adapter_skips_divergent_scoped_values() -> None:
    version = _version()
    eur = _study(version=version, metrics=(_metric("0.12"),))
    gbp = build_study_record(
        study_id=TraderHistoryStudyId(uuid4()),
        study_version=TraderHistoryStudyVersion("v1"),
        trader_version=version,
        kind=TraderHistoryStudyKind.REPLAY,
        epistemic_status=TraderHistoryEpistemicStatus.CERTIFIED,
        sufficiency=TraderHistorySufficiency.SUFFICIENT,
        produced_at=_NOW,
        producer=TraderHistoryProducerId("trader-lab"),
        market_scope=(TraderHistoryMarketRef("GBP/USD"),),
        timeframe_scope=(TraderHistoryTimeframeRef("h1"),),
        partitions=(_dev_partition(),),
        quantitative_claims=(
            TraderHistoryMetric("expectancy", Decimal("-0.05"), (_ref(),)),
        ),
    )
    registry = TraderHistoricalIntelligenceRegistry(records=(eur, gbp))
    result = project_cibo_capability_profile(
        registry,
        version,
        **_profile_kwargs(),
    )
    assert isinstance(result, Success)
    # "expectancy" diverges across scopes, so it is not collapsed into one value.
    assert result.value.economic_metrics == ()


def test_adapter_preserves_config_fingerprint_binding() -> None:
    version = _version(config=7)
    registry = TraderHistoricalIntelligenceRegistry(
        records=(_study(version=version, metrics=(_metric("0.12"),)),)
    )
    result = project_cibo_capability_profile(
        registry,
        version,
        **_profile_kwargs(),
    )
    assert isinstance(result, Success)
    assert result.value.config_fingerprint.value == _fp(7)


def test_adapter_resolves_stage_by_study_id_and_version() -> None:
    version = _version()
    study_id = TraderHistoryStudyId(uuid4())
    replay = build_study_record(
        study_id=study_id,
        study_version=TraderHistoryStudyVersion("v1"),
        trader_version=version,
        kind=TraderHistoryStudyKind.REPLAY,
        epistemic_status=TraderHistoryEpistemicStatus.CERTIFIED,
        sufficiency=TraderHistorySufficiency.SUFFICIENT,
        produced_at=_NOW,
        producer=TraderHistoryProducerId("trader-lab"),
        market_scope=(TraderHistoryMarketRef("EUR/USD"),),
        timeframe_scope=(TraderHistoryTimeframeRef("h1"),),
        partitions=(_dev_partition(),),
        quantitative_claims=(
            TraderHistoryMetric("expectancy", Decimal("0.10"), (_ref("evidence:r"),)),
        ),
    )
    oos = build_study_record(
        study_id=study_id,
        study_version=TraderHistoryStudyVersion("v2"),
        trader_version=version,
        kind=TraderHistoryStudyKind.OOS,
        epistemic_status=TraderHistoryEpistemicStatus.CERTIFIED,
        sufficiency=TraderHistorySufficiency.SUFFICIENT,
        produced_at=_NOW,
        producer=TraderHistoryProducerId("trader-lab"),
        market_scope=(TraderHistoryMarketRef("EUR/USD"),),
        timeframe_scope=(TraderHistoryTimeframeRef("h1"),),
        partitions=(_dev_partition(),),
        quantitative_claims=(
            TraderHistoryMetric("drawdown", Decimal("0.05"), (_ref("evidence:o"),)),
        ),
    )
    registry = TraderHistoricalIntelligenceRegistry(records=(replay, oos))
    result = project_cibo_capability_profile(
        registry,
        version,
        **_profile_kwargs(),
    )
    assert isinstance(result, Success)
    by_ref = {ref.ref.value: ref.stage.value for ref in result.value.certified_lab_evidence}
    assert by_ref["evidence:r"] == "replay"
    assert by_ref["evidence:o"] == "oos"


def test_adapter_projects_hypothesis_confirmation_as_oos() -> None:
    v1 = _version(config=1)
    v2 = _version(config=2)
    hypothesis_id = TraderHistoryHypothesisId("HYP-VT08-001")
    hypothesis = build_study_record(
        study_id=TraderHistoryStudyId(uuid4()),
        study_version=TraderHistoryStudyVersion("v1"),
        trader_version=v1,
        kind=TraderHistoryStudyKind.HYPOTHESIS,
        epistemic_status=TraderHistoryEpistemicStatus.HYPOTHESIS,
        sufficiency=TraderHistorySufficiency.UNKNOWN,
        produced_at=_NOW,
        producer=TraderHistoryProducerId("trader-lab"),
        market_scope=(TraderHistoryMarketRef("EUR/USD"),),
        timeframe_scope=(TraderHistoryTimeframeRef("h1"),),
        hypothesis_id=hypothesis_id,
    )
    holdout = TraderHistoryPartitionIdentity(
        uuid4(), _fp(77), SampleRole.EXTERNAL_VALIDATION
    )
    confirmation = build_study_record(
        study_id=TraderHistoryStudyId(uuid4()),
        study_version=TraderHistoryStudyVersion("v1"),
        trader_version=v2,
        kind=TraderHistoryStudyKind.HYPOTHESIS_CONFIRMATION,
        epistemic_status=TraderHistoryEpistemicStatus.CERTIFIED,
        sufficiency=TraderHistorySufficiency.SUFFICIENT,
        produced_at=_NOW,
        producer=TraderHistoryProducerId("trader-lab"),
        market_scope=(TraderHistoryMarketRef("EUR/USD"),),
        timeframe_scope=(TraderHistoryTimeframeRef("h1"),),
        partitions=(holdout,),
        quantitative_claims=(
            TraderHistoryMetric(
                "expectancy", Decimal("0.15"), (_ref("evidence:confirm"),)
            ),
        ),
        hypothesis_id=hypothesis_id,
        parent_study=hypothesis.study_id,
    )
    registry = TraderHistoricalIntelligenceRegistry(records=(hypothesis, confirmation))
    result = project_cibo_capability_profile(registry, v2, **_profile_kwargs())
    assert isinstance(result, Success)
    assert [
        (m.metric_code, str(m.value)) for m in result.value.economic_metrics
    ] == [("expectancy", "0.15")]
    assert {
        (ref.stage.value, ref.ref.value)
        for ref in result.value.certified_lab_evidence
    } == {("oos", "evidence:confirm")}


def test_adapter_projects_independent_validation_as_oos() -> None:
    version = _version()
    study = build_study_record(
        study_id=TraderHistoryStudyId(uuid4()),
        study_version=TraderHistoryStudyVersion("v1"),
        trader_version=version,
        kind=TraderHistoryStudyKind.INDEPENDENT_VALIDATION,
        epistemic_status=TraderHistoryEpistemicStatus.CERTIFIED,
        sufficiency=TraderHistorySufficiency.SUFFICIENT,
        produced_at=_NOW,
        producer=TraderHistoryProducerId("trader-lab"),
        market_scope=(TraderHistoryMarketRef("EUR/USD"),),
        timeframe_scope=(TraderHistoryTimeframeRef("h1"),),
        partitions=(
            TraderHistoryPartitionIdentity(
                uuid4(), _fp(88), SampleRole.EXTERNAL_VALIDATION
            ),
        ),
        quantitative_claims=(_metric("0.20"),),
    )
    registry = TraderHistoricalIntelligenceRegistry(records=(study,))
    result = project_cibo_capability_profile(registry, version, **_profile_kwargs())
    assert isinstance(result, Success)
    assert [m.metric_code for m in result.value.economic_metrics] == ["expectancy"]
    assert {
        (ref.stage.value, ref.ref.value)
        for ref in result.value.certified_lab_evidence
    } == {("oos", "evidence:replay")}


def test_adapter_preserves_per_ref_stage_for_merged_scope() -> None:
    version = _version()
    replay = _study(
        version=version,
        metrics=(_metric("0.10"),),
        kind=TraderHistoryStudyKind.REPLAY,
    )
    oos = _study(
        version=version,
        metrics=(
            TraderHistoryMetric(
                "expectancy", Decimal("0.10"), (_ref("evidence:oos"),)
            ),
        ),
        kind=TraderHistoryStudyKind.OOS,
    )
    registry = TraderHistoricalIntelligenceRegistry(records=(replay, oos))
    result = project_cibo_capability_profile(registry, version, **_profile_kwargs())
    assert isinstance(result, Success)
    assert {
        (ref.stage.value, ref.ref.value)
        for ref in result.value.certified_lab_evidence
    } == {("replay", "evidence:replay"), ("oos", "evidence:oos")}


def test_adapter_fails_closed_for_certified_unmapped_kind() -> None:
    version = _version()
    study = build_study_record(
        study_id=TraderHistoryStudyId(uuid4()),
        study_version=TraderHistoryStudyVersion("v1"),
        trader_version=version,
        kind=TraderHistoryStudyKind.DEMO,
        epistemic_status=TraderHistoryEpistemicStatus.CERTIFIED,
        sufficiency=TraderHistorySufficiency.SUFFICIENT,
        produced_at=_NOW,
        producer=TraderHistoryProducerId("trader-lab"),
        market_scope=(TraderHistoryMarketRef("EUR/USD"),),
        timeframe_scope=(TraderHistoryTimeframeRef("h1"),),
        partitions=(_dev_partition(),),
        quantitative_claims=(_metric("0.10"),),
    )
    registry = TraderHistoricalIntelligenceRegistry(records=(study,))
    result = project_cibo_capability_profile(registry, version, **_profile_kwargs())
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboTraderHistoryAdapterError)


def test_adapter_returns_failure_not_raise_on_sensitive_corruption() -> None:
    version = _version()
    ref = _ref("evidence:replay")
    metric = TraderHistoryMetric("expectancy", Decimal("0.10"), (ref,))
    study = _study(version=version, metrics=(metric,))
    registry = TraderHistoricalIntelligenceRegistry(records=(study,))
    object.__setattr__(ref, "value", "client_secret")
    result = project_cibo_capability_profile(registry, version, **_profile_kwargs())
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboTraderHistoryAdapterError)
