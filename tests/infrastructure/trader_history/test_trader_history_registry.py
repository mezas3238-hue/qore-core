from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from qore.infrastructure.research_sample_partition import SampleRole
from qore.infrastructure.trader_history.contracts import (
    TraderHistoryBlockedError,
    TraderHistoryEpistemicStatus,
    TraderHistoryEvidenceRef,
    TraderHistoryFavorableKind,
    TraderHistoryHypothesisId,
    TraderHistoryMarketRef,
    TraderHistoryMetric,
    TraderHistoryPartitionIdentity,
    TraderHistoryProducerId,
    TraderHistoryRegimeRef,
    TraderHistorySessionRef,
    TraderHistorySoftwareSha,
    TraderHistoryStudyId,
    TraderHistoryStudyKind,
    TraderHistoryStudyRecord,
    TraderHistoryStudyVersion,
    TraderHistorySufficiency,
    TraderHistoryTimeframeRef,
    TraderHistoryValidationError,
    TraderVersionIdentity,
    build_study_record,
    build_trader_version_identity,
)
from qore.infrastructure.trader_history.registry import (
    TraderHistoricalIntelligenceRegistry,
    TraderHistoryCurrentView,
    consumed_holdouts,
    diff_versions,
    hypothesis_lineage,
    market_evidence,
    project_current_capability,
    studies_by_kind,
    studies_for_version,
)
from qore.infrastructure.traders.contracts import (
    DemoTradingConfigFingerprint,
    DemoTradingMethodologyFingerprint,
    DemoTradingMethodologyId,
    DemoTradingMethodologyVersion,
    DemoTradingTraderCode,
    DemoTradingTraderVersion,
    DemoTradingValidationError,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def _fp(n: int) -> str:
    return f"{n:064x}"


def _fp40(n: int) -> str:
    return f"{n:040x}"


def _version(code: str = "vt-08", version: str = "v1", config: int = 1) -> TraderVersionIdentity:
    return build_trader_version_identity(
        trader_code=DemoTradingTraderCode(code),
        version=DemoTradingTraderVersion(version),
        config_fingerprint=DemoTradingConfigFingerprint(_fp(config)),
        methodology_id=DemoTradingMethodologyId("ny-precision-core"),
        methodology_version=DemoTradingMethodologyVersion("v1"),
        methodology_fingerprint=DemoTradingMethodologyFingerprint(_fp(2)),
        software_sha=TraderHistorySoftwareSha(_fp40(3)),
    )


def _ref(value: str = "evidence:replay") -> TraderHistoryEvidenceRef:
    return TraderHistoryEvidenceRef(value)


def _metric(
    code: str = "expectancy",
    value: str = "0.10",
    ref: str = "evidence:replay",
) -> TraderHistoryMetric:
    return TraderHistoryMetric(code, Decimal(value), (_ref(ref),))


def _partition(role: SampleRole, n: int = 1) -> TraderHistoryPartitionIdentity:
    return TraderHistoryPartitionIdentity(
        partition_id=uuid4(),
        dataset_fingerprint=_fp(n),
        role=role,
    )


_DEV_PARTITION_ID = UUID("00000000-0000-0000-0000-000000000001")


def _dev_partition(n: int = 90) -> TraderHistoryPartitionIdentity:
    return TraderHistoryPartitionIdentity(
        _DEV_PARTITION_ID,
        _fp(n),
        SampleRole.DEVELOPMENT,
    )


def _study(
    *,
    version: TraderVersionIdentity | None = None,
    kind: TraderHistoryStudyKind = TraderHistoryStudyKind.REPLAY,
    status: TraderHistoryEpistemicStatus = TraderHistoryEpistemicStatus.CERTIFIED,
    sufficiency: TraderHistorySufficiency = TraderHistorySufficiency.SUFFICIENT,
    study_id: TraderHistoryStudyId | None = None,
    study_version: str = "v1",
    markets: tuple[str, ...] = ("EUR/USD",),
    timeframes: tuple[str, ...] = ("h1",),
    metrics: tuple[TraderHistoryMetric, ...] = (),
    produced_at: datetime = _NOW,
    partitions: tuple[TraderHistoryPartitionIdentity, ...] | None = None,
    hypothesis_id: TraderHistoryHypothesisId | None = None,
    parent_study: TraderHistoryStudyId | None = None,
    condition: TraderHistoryFavorableKind | None = None,
    regime: TraderHistoryRegimeRef | None = None,
    session: TraderHistorySessionRef | None = None,
    supersedes: tuple[TraderHistoryStudyId, ...] = (),
) -> TraderHistoryStudyRecord:
    return build_study_record(
        study_id=study_id if study_id is not None else TraderHistoryStudyId(uuid4()),
        study_version=TraderHistoryStudyVersion(study_version),
        trader_version=version if version is not None else _version(),
        kind=kind,
        epistemic_status=status,
        sufficiency=sufficiency,
        produced_at=produced_at,
        producer=TraderHistoryProducerId("trader-lab"),
        market_scope=tuple(TraderHistoryMarketRef(m) for m in markets),
        timeframe_scope=tuple(TraderHistoryTimeframeRef(t) for t in timeframes),
        partitions=partitions if partitions is not None else (_dev_partition(),),
        quantitative_claims=metrics,
        hypothesis_id=hypothesis_id,
        parent_study=parent_study,
        condition=condition,
        regime=regime,
        session=session,
        supersedes=supersedes,
    )


def _registry(*records: TraderHistoryStudyRecord) -> TraderHistoricalIntelligenceRegistry:
    return TraderHistoricalIntelligenceRegistry(records=records)


def _project(
    registry: TraderHistoricalIntelligenceRegistry,
    version: TraderVersionIdentity,
) -> TraderHistoryCurrentView:
    result = project_current_capability(registry, version, derived_at=_NOW)
    assert isinstance(result, Success)
    return result.value


def test_append_is_idempotent_for_identical_replay() -> None:
    study = _study(metrics=(_metric(),))
    registry = _registry()
    first = registry.append_study(study)
    assert isinstance(first, Success)
    second = first.value.append_study(study)
    assert isinstance(second, Success)
    assert second.value is first.value
    assert len(second.value.records) == 1


def test_contradictory_duplicate_fails_closed() -> None:
    study_id = TraderHistoryStudyId(uuid4())
    left = _study(study_id=study_id, metrics=(_metric(value="0.10"),))
    right = _study(study_id=study_id, metrics=(_metric(value="0.99"),))
    registry = _registry(left)
    result = registry.append_study(right)
    assert isinstance(result, Failure)
    assert isinstance(result.error, TraderHistoryBlockedError)
    assert len(registry.records) == 1  # nothing overwritten


def test_append_only_never_deletes_old_version_evidence() -> None:
    v1 = _version(version="v1", config=1)
    v2 = _version(version="v2", config=2)
    registry = _registry(_study(version=v1, metrics=(_metric(value="0.10"),)))
    second = registry.append_study(_study(version=v2, metrics=(_metric(value="0.20"),)))
    assert isinstance(second, Success)
    assert len(second.value.records) == 2
    assert len(registry.records) == 1  # original unchanged
    assert {r.trader_version.version.value for r in second.value.records} == {"v1", "v2"}


def test_old_version_evidence_cannot_certify_new_version() -> None:
    v1 = _version(version="v1", config=1)
    v2 = _version(version="v2", config=2)
    registry = _registry(_study(version=v1, metrics=(_metric(value="0.10"),)))
    view = _project(registry, v2)
    assert view.certified_metrics == ()
    assert studies_for_version(registry, v2) == ()


def test_config_mismatch_fails_closed() -> None:
    v_original = _version(config=1)
    v_mismatch = _version(config=2)
    registry = _registry(_study(version=v_original, metrics=(_metric(value="0.10"),)))
    view = _project(registry, v_mismatch)
    assert view.certified_metrics == ()
    assert view.insufficient_metrics == ()


def test_insufficient_sample_cannot_become_certified() -> None:
    version = _version()
    study = _study(
        version=version,
        kind=TraderHistoryStudyKind.CHARACTERIZATION,
        status=TraderHistoryEpistemicStatus.OBSERVED,
        sufficiency=TraderHistorySufficiency.INSUFFICIENT,
        metrics=(_metric(),),
    )
    registry = _registry(study)
    view = _project(registry, version)
    assert view.certified_metrics == ()
    assert view.insufficient_metrics == ("expectancy",)


def test_contradictory_evidence_remains_visible() -> None:
    version = _version()
    left = _study(version=version, metrics=(_metric(value="0.10", ref="evidence:a"),))
    right = _study(version=version, metrics=(_metric(value="-0.05", ref="evidence:b"),))
    registry = _registry(left, right)
    view = _project(registry, version)
    assert view.certified_metrics == ()
    assert len(view.contradictions) == 1
    contradiction = view.contradictions[0]
    assert contradiction.metric_code == "expectancy"
    assert set(contradiction.values) == {Decimal("0.10"), Decimal("-0.05")}
    assert len(contradiction.evidence_refs) == 2


def test_different_scope_is_not_a_contradiction() -> None:
    version = _version()
    left = _study(
        version=version,
        markets=("EUR/USD",),
        metrics=(_metric(value="0.10"),),
    )
    right = _study(
        version=version,
        markets=("GBP/USD",),
        metrics=(_metric(value="-0.05"),),
    )
    registry = _registry(left, right)
    view = _project(registry, version)
    assert view.contradictions == ()
    assert len(view.certified_metrics) == 2  # per-market specificity preserved


def test_consumed_holdout_cannot_be_relabeled_fresh() -> None:
    version = _version()
    holdout = _partition(SampleRole.EXTERNAL_VALIDATION, n=11)
    first = _study(version=version, kind=TraderHistoryStudyKind.OOS, partitions=(holdout,))
    registry = _registry(first)
    second = _study(
        version=version,
        kind=TraderHistoryStudyKind.INDEPENDENT_VALIDATION,
        partitions=(holdout,),
    )
    result = registry.append_study(second)
    assert isinstance(result, Failure)
    assert isinstance(result.error, TraderHistoryBlockedError)


def test_development_partition_can_be_shared() -> None:
    version = _version()
    dev = _partition(SampleRole.DEVELOPMENT, n=12)
    first = _study(version=version, kind=TraderHistoryStudyKind.REPLAY, partitions=(dev,))
    second = _study(version=version, kind=TraderHistoryStudyKind.BACKTEST, partitions=(dev,))
    registry = _registry(first)
    result = registry.append_study(second)
    assert isinstance(result, Success)


def test_hypothesis_confirmation_requires_fresh_holdout() -> None:
    version = _version(config=1)
    changed_version = _version(config=2)
    hypothesis_id = TraderHistoryHypothesisId("HYP-VT08-001")
    hypothesis = _study(
        version=version,
        kind=TraderHistoryStudyKind.HYPOTHESIS,
        status=TraderHistoryEpistemicStatus.HYPOTHESIS,
        hypothesis_id=hypothesis_id,
        metrics=(),
    )
    registry = _registry(hypothesis)
    confirmation = _study(
        version=changed_version,
        kind=TraderHistoryStudyKind.HYPOTHESIS_CONFIRMATION,
        status=TraderHistoryEpistemicStatus.CERTIFIED,
        hypothesis_id=hypothesis_id,
        parent_study=hypothesis.study_id,
        metrics=(),
        partitions=(),
    )
    result = registry.append_study(confirmation)
    assert isinstance(result, Failure)
    assert isinstance(result.error, TraderHistoryBlockedError)


def test_hypothesis_confirmation_with_fresh_holdout_succeeds() -> None:
    version = _version(config=1)
    changed_version = _version(config=2)
    hypothesis_id = TraderHistoryHypothesisId("HYP-VT08-001")
    hypothesis = _study(
        version=version,
        kind=TraderHistoryStudyKind.HYPOTHESIS,
        status=TraderHistoryEpistemicStatus.HYPOTHESIS,
        hypothesis_id=hypothesis_id,
        metrics=(),
    )
    registry = _registry(hypothesis)
    holdout = _partition(SampleRole.EXTERNAL_VALIDATION, n=13)
    confirmation = _study(
        version=changed_version,
        kind=TraderHistoryStudyKind.HYPOTHESIS_CONFIRMATION,
        status=TraderHistoryEpistemicStatus.CERTIFIED,
        hypothesis_id=hypothesis_id,
        parent_study=hypothesis.study_id,
        partitions=(holdout,),
        metrics=(_metric(value="0.15"),),
    )
    result = registry.append_study(confirmation)
    assert isinstance(result, Success)
    lineage = hypothesis_lineage(result.value, "HYP-VT08-001")
    assert len(lineage) == 2
    assert {r.kind for r in lineage} == {
        TraderHistoryStudyKind.HYPOTHESIS,
        TraderHistoryStudyKind.HYPOTHESIS_CONFIRMATION,
    }


def test_confirmation_must_reference_existing_hypothesis() -> None:
    version = _version()
    hypothesis_id = TraderHistoryHypothesisId("HYP-VT08-002")
    confirmation = _study(
        version=version,
        kind=TraderHistoryStudyKind.HYPOTHESIS_CONFIRMATION,
        status=TraderHistoryEpistemicStatus.CERTIFIED,
        hypothesis_id=hypothesis_id,
        parent_study=TraderHistoryStudyId(uuid4()),
        partitions=(_partition(SampleRole.EXTERNAL_VALIDATION, n=14),),
        metrics=(),
    )
    registry = _registry()
    result = registry.append_study(confirmation)
    assert isinstance(result, Failure)
    assert isinstance(result.error, TraderHistoryBlockedError)


def test_canonical_ordering_is_deterministic_under_reordering() -> None:
    version = _version()
    first = _study(
        version=version,
        produced_at=_NOW,
        metrics=(_metric(value="0.10", ref="evidence:a"),),
    )
    second = _study(
        version=version,
        produced_at=_NOW + timedelta(seconds=1),
        metrics=(_metric(value="0.20", ref="evidence:b"),),
    )
    left = TraderHistoricalIntelligenceRegistry(records=(first, second))
    right = TraderHistoricalIntelligenceRegistry(records=(second, first))
    assert left.records == right.records
    assert left.logical_values() == right.logical_values()


def test_stale_and_superseded_evidence_is_not_deleted() -> None:
    version = _version()
    stale = _study(
        version=version,
        status=TraderHistoryEpistemicStatus.STALE,
        sufficiency=TraderHistorySufficiency.SUFFICIENT,
        metrics=(),
    )
    current = _study(version=version, metrics=(_metric(),))
    registry = _registry(stale, current)
    assert len(registry.records) == 2
    view = _project(registry, version)
    assert len(view.stale_records) == 1
    assert view.stale_records[0].study_id == stale.study_id


def test_consumed_holdouts_are_tracked() -> None:
    version = _version()
    holdout = _partition(SampleRole.EXTERNAL_VALIDATION, n=15)
    registry = _registry(
        _study(version=version, kind=TraderHistoryStudyKind.OOS, partitions=(holdout,))
    )
    assert consumed_holdouts(registry) == (holdout,)


def test_studies_by_kind_are_filtered() -> None:
    version = _version()
    replay = _study(version=version, kind=TraderHistoryStudyKind.REPLAY)
    stress = _study(version=version, kind=TraderHistoryStudyKind.STRESS)
    registry = _registry(replay, stress)
    assert studies_by_kind(registry, version, TraderHistoryStudyKind.REPLAY) == (replay,)
    assert studies_by_kind(registry, version, TraderHistoryStudyKind.STRESS) == (stress,)


def test_market_evidence_never_ranks_best_market() -> None:
    version = _version()
    eur = _study(
        version=version,
        markets=("EUR/USD",),
        metrics=(_metric(value="0.10"),),
    )
    gbp = _study(
        version=version,
        markets=("GBP/USD",),
        metrics=(_metric(value="-0.05"),),
    )
    registry = _registry(eur, gbp)
    evidence = market_evidence(registry, version)
    assert {e.market.value for e in evidence} == {"EUR/USD", "GBP/USD"}
    by_market = {e.market.value: e for e in evidence}
    assert by_market["EUR/USD"].certified_metrics[0].value == Decimal("0.10")
    assert by_market["GBP/USD"].certified_metrics[0].value == Decimal("-0.05")


def test_diff_versions_reports_kind_and_metric_differences() -> None:
    v1 = _version(version="v1", config=1)
    v2 = _version(version="v2", config=2)
    registry = _registry(
        _study(version=v1, kind=TraderHistoryStudyKind.REPLAY, metrics=(_metric(value="0.10"),)),
        _study(version=v2, kind=TraderHistoryStudyKind.STRESS, metrics=(_metric(value="0.30"),)),
    )
    diff = diff_versions(registry, v1, v2)
    assert diff.left_only_kinds == ("replay",)
    assert diff.right_only_kinds == ("stress",)
    assert diff.left_certified_metrics[0].value == Decimal("0.10")
    assert diff.right_certified_metrics[0].value == Decimal("0.30")


def test_projection_is_deterministic_for_identical_history() -> None:
    version = _version()
    study = _study(version=version, metrics=(_metric(),))
    registry = _registry(study)
    left = _project(registry, version)
    right = _project(registry, version)
    assert left.logical_values() == right.logical_values()
    assert left == right


def test_projection_rejects_timezone_naive_derived_at() -> None:
    version = _version()
    result = project_current_capability(
        _registry(),
        version,
        derived_at=datetime(2026, 1, 1),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, TraderHistoryBlockedError)


def test_regime_specificity_preserved() -> None:
    version = _version()
    regime = TraderHistoryRegimeRef("trend-up")
    trend = _study(
        version=version,
        regime=regime,
        metrics=(_metric(value="0.20"),),
    )
    ranging = _study(
        version=version,
        regime=TraderHistoryRegimeRef("range"),
        metrics=(_metric(value="0.02"),),
    )
    registry = _registry(trend, ranging)
    view = _project(registry, version)
    assert len(view.certified_metrics) == 2
    regimes = {m.regime.value for m in view.certified_metrics if m.regime is not None}
    assert regimes == {"trend-up", "range"}


def test_all_31_trader_identities_representable() -> None:
    for index in range(1, 32):
        code = f"vt-{index:02d}"
        version = _version(code=code, config=index)
        assert version.trader_code.value == code
    with pytest.raises(DemoTradingValidationError):
        DemoTradingTraderCode("vt-00")
    with pytest.raises(DemoTradingValidationError):
        DemoTradingTraderCode("vt-32")


def test_core_contracts_carry_no_authority_fields() -> None:
    forbidden = {
        "order",
        "quantity",
        "execution",
        "custody",
        "account",
        "live",
        "production",
        "demo_eligible",
        "risk_bypass",
        "authority",
    }
    for cls in (
        TraderVersionIdentity,
        TraderHistoryStudyRecord,
        TraderHistoryCurrentView,
    ):
        fields = set(getattr(cls, "__dataclass_fields__", {}))
        overlap = fields & forbidden
        assert not overlap, f"{cls.__name__} carries forbidden fields: {overlap}"


def test_holdout_content_cannot_be_relabeled_as_development() -> None:
    version = _version()
    holdout = _partition(SampleRole.EXTERNAL_VALIDATION, n=11)
    registry = _registry(
        _study(version=version, kind=TraderHistoryStudyKind.OOS, partitions=(holdout,))
    )
    relabeled = TraderHistoryPartitionIdentity(
        uuid4(), _fp(11), SampleRole.DEVELOPMENT
    )
    result = registry.append_study(
        _study(version=version, kind=TraderHistoryStudyKind.REPLAY, partitions=(relabeled,))
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, TraderHistoryBlockedError)


def test_development_content_cannot_be_relabeled_as_holdout() -> None:
    version = _version()
    dev = _partition(SampleRole.DEVELOPMENT, n=12)
    registry = _registry(
        _study(version=version, kind=TraderHistoryStudyKind.REPLAY, partitions=(dev,))
    )
    relabeled = TraderHistoryPartitionIdentity(
        uuid4(), _fp(12), SampleRole.EXTERNAL_VALIDATION
    )
    result = registry.append_study(
        _study(version=version, kind=TraderHistoryStudyKind.OOS, partitions=(relabeled,))
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, TraderHistoryBlockedError)


def test_superseded_evidence_is_not_current_capability() -> None:
    version = _version()
    old = _study(version=version, metrics=(_metric(value="0.10"),))
    newer = _study(
        version=version,
        metrics=(_metric(value="0.20"),),
        supersedes=(old.study_id,),
    )
    registry = _registry(old, newer)
    view = _project(registry, version)
    assert len(view.certified_metrics) == 1
    assert view.certified_metrics[0].value == Decimal("0.20")
    assert view.certified_metrics[0].source_study == newer.study_id
    assert len(view.stale_records) == 1
    assert view.stale_records[0].study_id == old.study_id


def test_duplicate_hypothesis_identity_fails_closed() -> None:
    version = _version()
    hypothesis_id = TraderHistoryHypothesisId("HYP-VT08-009")
    first = _study(
        version=version,
        kind=TraderHistoryStudyKind.HYPOTHESIS,
        status=TraderHistoryEpistemicStatus.HYPOTHESIS,
        hypothesis_id=hypothesis_id,
        metrics=(),
    )
    second = _study(
        version=version,
        kind=TraderHistoryStudyKind.HYPOTHESIS,
        status=TraderHistoryEpistemicStatus.HYPOTHESIS,
        hypothesis_id=hypothesis_id,
        metrics=(),
    )
    with pytest.raises(TraderHistoryValidationError):
        _registry(first, second)


def test_confirmation_on_same_version_fails_closed() -> None:
    version = _version()
    hypothesis_id = TraderHistoryHypothesisId("HYP-VT08-010")
    hypothesis = _study(
        version=version,
        kind=TraderHistoryStudyKind.HYPOTHESIS,
        status=TraderHistoryEpistemicStatus.HYPOTHESIS,
        hypothesis_id=hypothesis_id,
        metrics=(),
    )
    registry = _registry(hypothesis)
    holdout = _partition(SampleRole.EXTERNAL_VALIDATION, n=16)
    confirmation = _study(
        version=version,
        kind=TraderHistoryStudyKind.HYPOTHESIS_CONFIRMATION,
        status=TraderHistoryEpistemicStatus.CERTIFIED,
        hypothesis_id=hypothesis_id,
        parent_study=hypothesis.study_id,
        partitions=(holdout,),
        metrics=(),
    )
    result = registry.append_study(confirmation)
    assert isinstance(result, Failure)
    assert isinstance(result.error, TraderHistoryBlockedError)


def test_projection_excludes_evidence_after_derived_at() -> None:
    version = _version()
    future = _study(
        version=version,
        metrics=(_metric(value="0.10"),),
        produced_at=_NOW + timedelta(days=30),
    )
    registry = _registry(future)
    view = _project(registry, version)  # derived_at defaults to _NOW
    assert view.certified_metrics == ()
    assert view.insufficient_metrics == ()


def test_projection_handles_mixed_regime_and_unscoped_evidence() -> None:
    version = _version()
    unscoped = _study(version=version, metrics=(_metric(value="0.10"),), regime=None)
    trend = _study(
        version=version,
        metrics=(_metric(value="0.20"),),
        regime=TraderHistoryRegimeRef("trend-up"),
    )
    registry = _registry(unscoped, trend)
    view = _project(registry, version)
    assert len(view.certified_metrics) == 2
    assert view.contradictions == ()


def test_session_scope_is_preserved_in_projection() -> None:
    version = _version()
    asia = _study(
        version=version,
        metrics=(_metric(value="0.10"),),
        session=TraderHistorySessionRef("asia"),
    )
    london = _study(
        version=version,
        metrics=(_metric(value="-0.05"),),
        session=TraderHistorySessionRef("london"),
    )
    registry = _registry(asia, london)
    view = _project(registry, version)
    assert len(view.certified_metrics) == 2
    assert view.contradictions == ()
    sessions = {m.session.value for m in view.certified_metrics if m.session is not None}
    assert sessions == {"asia", "london"}


def test_metric_view_carries_exact_source_study_version() -> None:
    version = _version()
    study_id = TraderHistoryStudyId(uuid4())
    study = _study(
        version=version,
        metrics=(_metric(value="0.10"),),
        study_id=study_id,
        study_version="v3",
    )
    registry = _registry(study)
    view = _project(registry, version)
    assert view.certified_metrics[0].source_study == study_id
    assert view.certified_metrics[0].source_study_version.value == "v3"


def test_projection_revalidates_corrupted_record_fails_closed() -> None:
    version = _version()
    study = _study(version=version, metrics=(_metric(value="0.10"),))
    registry = _registry(study)
    object.__setattr__(study, "epistemic_status", "certified")
    result = project_current_capability(registry, version, derived_at=_NOW)
    assert isinstance(result, Failure)
    assert isinstance(result.error, TraderHistoryBlockedError)
