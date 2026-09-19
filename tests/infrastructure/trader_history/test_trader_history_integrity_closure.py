"""Post-falsification integrity closure for Trader Historical Intelligence.

These tests close the remaining causal-family gaps (D1-D3 plus hardening) that
were not yet covered by the foundation test files:

- D1 supersession lookahead (non-certified superseder, certification-time).
- D2 joint (non-Cartesian) market/timeframe scope at the CIBO boundary.
- D3 ledger truncation refused against an authoritative external root.
- F1 certification envelope (authority kind/id/issued_at) — CERTIFIED is never
  caller assertion.
- F3 contradiction fail-closed at the CIBO boundary.
- F5 supersession cycle/inversion and hypothesis temporal order.
- F6 lineage-scoped and derived_at-scoped consumed holdouts.
- F8 canonical identity family (``virtual.trader.*``).
- F9 duplicate dataset fingerprint within one study.
- Superseded records excluded from ``market_evidence`` / ``diff_versions``.
- Adapter schema-version binding.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from qore.infrastructure.cibo_trader_capability_profile import (
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
    TraderHistoryAuthorityKind,
    TraderHistoryBlockedError,
    TraderHistoryCertification,
    TraderHistoryEpistemicStatus,
    TraderHistoryEvidenceRef,
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
    TraderHistoryValidationError,
    TraderVersionIdentity,
    build_study_record,
    build_trader_version_identity,
    compute_trader_identity_family,
)
from qore.infrastructure.trader_history.registry import (
    TraderHistoricalIntelligenceRegistry,
    compute_trader_history_ledger_root,
    diff_versions,
    market_evidence,
    project_current_capability,
    reconstruct_trader_history,
    verify_reconstructed_history,
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


def _version(
    code: str = "vt-08",
    version: str = "v1",
    config: int = 1,
) -> TraderVersionIdentity:
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
    value: str = "0.10",
    *,
    code: str = "expectancy",
    ref: str = "evidence:replay",
) -> TraderHistoryMetric:
    return TraderHistoryMetric(code, Decimal(value), (_ref(ref),))


def _partition(
    role: SampleRole,
    n: int,
    *,
    partition_id: UUID | None = None,
) -> TraderHistoryPartitionIdentity:
    return TraderHistoryPartitionIdentity(
        partition_id if partition_id is not None else uuid4(),
        _fp(n),
        role,
    )


_AUTHORITY_KIND_BY_KIND = {
    TraderHistoryStudyKind.INDEPENDENT_VALIDATION: (
        TraderHistoryAuthorityKind.INDEPENDENT_VALIDATION
    ),
    TraderHistoryStudyKind.RISK_REVIEW: TraderHistoryAuthorityKind.RISK,
    TraderHistoryStudyKind.CIBO_REVIEW: TraderHistoryAuthorityKind.CIBO,
    TraderHistoryStudyKind.ECONOMIC_EVALUATION: TraderHistoryAuthorityKind.ECONOMIC,
}

_AUTHORITY_ID = UUID("00000000-0000-4000-8000-0000000000aa")


def _certification(
    kind: TraderHistoryStudyKind,
    produced_at: datetime = _NOW,
    authority_kind: TraderHistoryAuthorityKind | None = None,
    *,
    study_id: TraderHistoryStudyId | None = None,
    study_version: str = "v1",
) -> TraderHistoryCertification:
    kind_authority = authority_kind or _AUTHORITY_KIND_BY_KIND.get(
        kind, TraderHistoryAuthorityKind.TRADER_LAB
    )
    # Mint a sealed certification as an owning authority would (the production
    # in-repo constructors cannot set the sealed ``_issued`` marker).
    certification = object.__new__(TraderHistoryCertification)
    object.__setattr__(certification, "authority_kind", kind_authority)
    object.__setattr__(certification, "authority_id", _AUTHORITY_ID)
    object.__setattr__(certification, "issued_at", produced_at)
    object.__setattr__(
        certification,
        "study_id",
        study_id if study_id is not None else TraderHistoryStudyId(uuid4()),
    )
    object.__setattr__(
        certification,
        "study_version",
        TraderHistoryStudyVersion(study_version),
    )
    object.__setattr__(certification, "_issued", True)
    return certification


def _rebind_certification(
    certification: TraderHistoryCertification,
    study_id: TraderHistoryStudyId,
    study_version: TraderHistoryStudyVersion,
) -> TraderHistoryCertification:
    """Re-mint an existing envelope bound to the exact study identity."""
    if (
        certification.study_id == study_id
        and certification.study_version == study_version
    ):
        return certification
    rebound = object.__new__(TraderHistoryCertification)
    object.__setattr__(rebound, "authority_kind", certification.authority_kind)
    object.__setattr__(rebound, "authority_id", certification.authority_id)
    object.__setattr__(rebound, "issued_at", certification.issued_at)
    object.__setattr__(rebound, "study_id", study_id)
    object.__setattr__(rebound, "study_version", study_version)
    object.__setattr__(rebound, "_issued", True)
    return rebound


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
    certification: TraderHistoryCertification | None = None,
    supersedes: tuple[TraderHistoryStudyId, ...] = (),
    hypothesis_id: TraderHistoryHypothesisId | None = None,
    parent_study: TraderHistoryStudyId | None = None,
) -> TraderHistoryStudyRecord:
    if partitions is None:
        partitions = (_partition(SampleRole.DEVELOPMENT, 900),)
    sid = study_id if study_id is not None else TraderHistoryStudyId(uuid4())
    sver = TraderHistoryStudyVersion(study_version)
    if certification is None and status is TraderHistoryEpistemicStatus.CERTIFIED:
        certification = _certification(
            kind, produced_at, study_id=sid, study_version=sver.value
        )
    elif certification is not None:
        certification = _rebind_certification(certification, sid, sver)
    return build_study_record(
        study_id=sid,
        study_version=sver,
        trader_version=version if version is not None else _version(),
        kind=kind,
        epistemic_status=status,
        sufficiency=sufficiency,
        produced_at=produced_at,
        producer=TraderHistoryProducerId("trader-lab"),
        certification=certification,
        market_scope=tuple(TraderHistoryMarketRef(m) for m in markets),
        timeframe_scope=tuple(TraderHistoryTimeframeRef(t) for t in timeframes),
        partitions=partitions,
        quantitative_claims=metrics,
        supersedes=supersedes,
        hypothesis_id=hypothesis_id,
        parent_study=parent_study,
    )


def _identity(schema_version: str = "v1") -> ResearchDecisionEvaluatorIdentity:
    return ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily("virtual.trader.vt08"),
        schema_version=ResearchDecisionEvaluatorSchemaVersion(schema_version),
        software_revision=ResearchSoftwareRevision("rev-1"),
    )


# ---------------------------------------------------------------------------
# D1 — supersession lookahead and epistemic/certification-time causality.
# ---------------------------------------------------------------------------


def test_non_certified_superseder_does_not_suppress_certified_evidence() -> None:
    version = _version()
    certified = _study(version=version, metrics=(_metric("0.10"),))
    hypothesis = _study(
        version=version,
        kind=TraderHistoryStudyKind.HYPOTHESIS,
        status=TraderHistoryEpistemicStatus.HYPOTHESIS,
        sufficiency=TraderHistorySufficiency.UNKNOWN,
        metrics=(),
        supersedes=(certified.study_id,),
        hypothesis_id=TraderHistoryHypothesisId("HYP-VT08-D1-001"),
    )
    registry = TraderHistoricalIntelligenceRegistry(records=(certified, hypothesis))
    result = project_current_capability(registry, version, derived_at=_NOW)
    assert isinstance(result, Success)
    view = result.value
    assert [m.value for m in view.certified_metrics] == [Decimal("0.10")]
    assert view.stale_records == ()
    assert len(view.exploratory_records) == 1


def test_future_certification_does_not_leak_into_earlier_projection() -> None:
    version = _version()
    older = _study(
        version=version,
        metrics=(_metric("0.10", ref="evidence:old"),),
        produced_at=_NOW,
    )
    superseder = _study(
        version=version,
        metrics=(_metric("0.20", ref="evidence:new"),),
        produced_at=_NOW + timedelta(days=1),
        certification=_certification(
            TraderHistoryStudyKind.REPLAY, _NOW + timedelta(days=2)
        ),
        supersedes=(older.study_id,),
    )
    registry = TraderHistoricalIntelligenceRegistry(records=(older, superseder))
    # At day 1 (between produced_at and issued_at of the superseder), the
    # superseder is not yet certified: older evidence remains current.
    mid = project_current_capability(
        registry, version, derived_at=_NOW + timedelta(days=1)
    )
    assert isinstance(mid, Success)
    assert [m.value for m in mid.value.certified_metrics] == [Decimal("0.10")]
    assert mid.value.stale_records == ()
    # After issuance, the superseder becomes current and the older study is stale.
    late = project_current_capability(
        registry, version, derived_at=_NOW + timedelta(days=3)
    )
    assert isinstance(late, Success)
    assert [m.value for m in late.value.certified_metrics] == [Decimal("0.20")]
    assert [r.study_id for r in late.value.stale_records] == [older.study_id]


def test_supersession_inversion_is_rejected() -> None:
    version = _version()
    later = _study(
        version=version,
        produced_at=_NOW + timedelta(days=1),
        metrics=(_metric("0.10"),),
    )
    earlier = _study(
        version=version,
        produced_at=_NOW,
        metrics=(_metric("0.20"),),
        supersedes=(later.study_id,),
    )
    # A study cannot supersede evidence produced after it (inversion).
    with pytest.raises(TraderHistoryValidationError):
        TraderHistoricalIntelligenceRegistry(records=(earlier, later))


def test_supersession_certification_inversion_is_rejected() -> None:
    version = _version()
    target = _study(
        version=version,
        metrics=(_metric("0.10"),),
        produced_at=_NOW,
        certification=_certification(
            TraderHistoryStudyKind.REPLAY, _NOW + timedelta(days=2)
        ),
    )
    superseder = _study(
        version=version,
        metrics=(_metric("0.20"),),
        produced_at=_NOW + timedelta(days=1),
        certification=_certification(
            TraderHistoryStudyKind.REPLAY, _NOW + timedelta(days=1)
        ),
        supersedes=(target.study_id,),
    )
    # The superseder becomes certified (day 1) before the target (day 2): it can
    # never suppress evidence that only became knowledge later (D1/F5).
    with pytest.raises(TraderHistoryValidationError):
        TraderHistoricalIntelligenceRegistry(records=(target, superseder))


def test_supersession_cycle_is_rejected() -> None:
    version = _version()
    a = _study(version=version, metrics=(_metric("0.10"),), produced_at=_NOW)
    b = _study(
        version=version,
        metrics=(_metric("0.20"),),
        produced_at=_NOW,
        supersedes=(a.study_id,),
    )
    a_prime = _study(
        version=version,
        metrics=(_metric("0.30"),),
        produced_at=_NOW,
        supersedes=(b.study_id,),
        study_id=a.study_id,
    )
    # a <-> b forms a cycle (a supersedes b, b supersedes a).
    with pytest.raises(TraderHistoryValidationError):
        TraderHistoricalIntelligenceRegistry(records=(a, b, a_prime))


def test_hypothesis_confirmation_cannot_predate_hypothesis() -> None:
    version = _version(config=1)
    changed = _version(config=2)
    hypothesis_id = TraderHistoryHypothesisId("HYP-VT08-TEMPORAL-001")
    hypothesis = _study(
        version=version,
        kind=TraderHistoryStudyKind.HYPOTHESIS,
        status=TraderHistoryEpistemicStatus.HYPOTHESIS,
        sufficiency=TraderHistorySufficiency.UNKNOWN,
        produced_at=_NOW + timedelta(days=1),
        metrics=(),
        hypothesis_id=hypothesis_id,
    )
    confirmation = _study(
        version=changed,
        kind=TraderHistoryStudyKind.HYPOTHESIS_CONFIRMATION,
        status=TraderHistoryEpistemicStatus.CERTIFIED,
        produced_at=_NOW,
        metrics=(),
        partitions=(_partition(SampleRole.EXTERNAL_VALIDATION, 801),),
        hypothesis_id=hypothesis_id,
        parent_study=hypothesis.study_id,
    )
    with pytest.raises(TraderHistoryValidationError):
        TraderHistoricalIntelligenceRegistry(records=(hypothesis, confirmation))


# ---------------------------------------------------------------------------
# D2 — joint market/timeframe scope (never Cartesian).
# ---------------------------------------------------------------------------


def test_adapter_rejects_cartesian_scope_laundering() -> None:
    version = _version()
    eur_h1 = _study(
        version=version,
        markets=("EUR/USD",),
        timeframes=("h1",),
        metrics=(_metric("0.10"),),
    )
    gbp_d1 = _study(
        version=version,
        markets=("GBP/USD",),
        timeframes=("d1",),
        metrics=(_metric("0.20"),),
    )
    registry = TraderHistoricalIntelligenceRegistry(records=(eur_h1, gbp_d1))
    # Both markets and both timeframes are individually backed, but the cross
    # pairs (EUR/USD, d1) and (GBP/USD, h1) are not jointly backed.
    result = project_cibo_capability_profile(
        registry,
        version,
        trader_identity=_identity(),
        qualified_markets=(
            CiboTradeableMarketRef("EUR/USD"),
            CiboTradeableMarketRef("GBP/USD"),
        ),
        qualified_timeframes=(CiboTimeframeCode("h1"), CiboTimeframeCode("d1")),
        evidence_as_of=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboTraderHistoryAdapterError)


def test_adapter_accepts_jointly_backed_scope() -> None:
    version = _version()
    eur_h1 = _study(
        version=version,
        markets=("EUR/USD",),
        timeframes=("h1",),
        metrics=(_metric("0.10"),),
    )
    gbp_h1 = _study(
        version=version,
        markets=("GBP/USD",),
        timeframes=("h1",),
        metrics=(_metric("0.20"),),
    )
    registry = TraderHistoricalIntelligenceRegistry(records=(eur_h1, gbp_h1))
    result = project_cibo_capability_profile(
        registry,
        version,
        trader_identity=_identity(),
        qualified_markets=(
            CiboTradeableMarketRef("EUR/USD"),
            CiboTradeableMarketRef("GBP/USD"),
        ),
        qualified_timeframes=(CiboTimeframeCode("h1"),),
        evidence_as_of=_NOW,
    )
    assert isinstance(result, Success)


def test_adapter_rejects_single_study_multi_market_multi_timeframe_ambiguity() -> None:
    version = _version()
    ambiguous = _study(
        version=version,
        markets=("EUR/USD", "GBP/USD"),
        timeframes=("h1", "d1"),
        metrics=(_metric("0.10"),),
    )
    registry = TraderHistoricalIntelligenceRegistry(records=(ambiguous,))
    # A single study declaring multi-market x multi-timeframe has no explicit
    # joint tuples; its Cartesian cross product must fail closed (D2).
    result = project_cibo_capability_profile(
        registry,
        version,
        trader_identity=_identity(),
        qualified_markets=(
            CiboTradeableMarketRef("EUR/USD"),
            CiboTradeableMarketRef("GBP/USD"),
        ),
        qualified_timeframes=(CiboTimeframeCode("h1"), CiboTimeframeCode("d1")),
        evidence_as_of=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboTraderHistoryAdapterError)


def test_adapter_accepts_single_market_multi_timeframe_scope() -> None:
    version = _version()
    study = _study(
        version=version,
        markets=("EUR/USD",),
        timeframes=("h1", "d1"),
        metrics=(_metric("0.10"),),
    )
    registry = TraderHistoricalIntelligenceRegistry(records=(study,))
    # One market across several timeframes is joint and unambiguous.
    result = project_cibo_capability_profile(
        registry,
        version,
        trader_identity=_identity(),
        qualified_markets=(CiboTradeableMarketRef("EUR/USD"),),
        qualified_timeframes=(CiboTimeframeCode("h1"), CiboTimeframeCode("d1")),
        evidence_as_of=_NOW,
    )
    assert isinstance(result, Success)


def test_adapter_accepts_multi_market_single_timeframe_scope() -> None:
    version = _version()
    study = _study(
        version=version,
        markets=("EUR/USD", "GBP/USD"),
        timeframes=("h1",),
        metrics=(_metric("0.10"),),
    )
    registry = TraderHistoricalIntelligenceRegistry(records=(study,))
    # Several markets at one timeframe are joint and unambiguous.
    result = project_cibo_capability_profile(
        registry,
        version,
        trader_identity=_identity(),
        qualified_markets=(
            CiboTradeableMarketRef("EUR/USD"),
            CiboTradeableMarketRef("GBP/USD"),
        ),
        qualified_timeframes=(CiboTimeframeCode("h1"),),
        evidence_as_of=_NOW,
    )
    assert isinstance(result, Success)


def test_adapter_does_not_use_future_certified_scope_for_current_qualification() -> (
    None
):
    version = _version()
    future_certified = _study(
        version=version,
        metrics=(_metric("0.10"),),
        produced_at=_NOW,
        certification=_certification(
            TraderHistoryStudyKind.REPLAY, _NOW + timedelta(days=2)
        ),
    )
    registry = TraderHistoricalIntelligenceRegistry(records=(future_certified,))
    # Produced now but certified in the future: at day 1 the certification has
    # not been issued, so its scope must not back a current CIBO qualification.
    result = project_cibo_capability_profile(
        registry,
        version,
        trader_identity=_identity(),
        qualified_markets=(CiboTradeableMarketRef("EUR/USD"),),
        qualified_timeframes=(CiboTimeframeCode("h1"),),
        evidence_as_of=_NOW + timedelta(days=1),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboTraderHistoryAdapterError)


def test_adapter_does_not_fabricate_stage_from_future_certification() -> None:
    version = _version()
    current = _study(
        version=version,
        kind=TraderHistoryStudyKind.REPLAY,
        metrics=(_metric("0.10", ref="evidence:replay"),),
    )
    future_oos = _study(
        version=version,
        kind=TraderHistoryStudyKind.OOS,
        metrics=(_metric("0.20", ref="evidence:replay"),),
        produced_at=_NOW,
        certification=_certification(
            TraderHistoryStudyKind.OOS, _NOW + timedelta(days=2)
        ),
        partitions=(_partition(SampleRole.EXTERNAL_VALIDATION, 901),),
    )
    registry = TraderHistoricalIntelligenceRegistry(records=(current, future_oos))
    # At day 1 the future OOS certification has not been issued, so it must not
    # fabricate an "oos" stage for the shared evidence ref.
    result = project_cibo_capability_profile(
        registry,
        version,
        trader_identity=_identity(),
        qualified_markets=(CiboTradeableMarketRef("EUR/USD"),),
        qualified_timeframes=(CiboTimeframeCode("h1"),),
        evidence_as_of=_NOW + timedelta(days=1),
    )
    assert isinstance(result, Success)
    stages = {ref.stage.value for ref in result.value.certified_lab_evidence}
    assert stages == {"replay"}


# ---------------------------------------------------------------------------
# D3 — ledger truncation refused against an authoritative external root.
# ---------------------------------------------------------------------------


def test_truncated_ledger_fails_closed_against_external_root() -> None:
    version = _version()
    first = _study(version=version, metrics=(_metric("0.10"),))
    second = _study(version=version, metrics=(_metric("0.05", code="drawdown"),))
    full = TraderHistoricalIntelligenceRegistry(records=(first, second))
    root = full.ledger_root()

    truncated = TraderHistoricalIntelligenceRegistry(records=(first,))
    # The truncated ledger is internally self-consistent but must not
    # authenticate itself.
    assert truncated.ledger_root() != root
    verified = verify_reconstructed_history(truncated, root)
    assert isinstance(verified, Failure)
    assert isinstance(verified.error, TraderHistoryBlockedError)

    # Benign control: the full ledger matches the authoritative root.
    ok = verify_reconstructed_history(full, root)
    assert isinstance(ok, Success)
    assert ok.value is full


def test_ledger_root_is_reorder_invariant() -> None:
    version = _version()
    first = _study(version=version, metrics=(_metric("0.10"),))
    second = _study(version=version, metrics=(_metric("0.05", code="drawdown"),))
    left = TraderHistoricalIntelligenceRegistry(records=(first, second))
    right = TraderHistoricalIntelligenceRegistry(records=(second, first))
    assert compute_trader_history_ledger_root(left) == compute_trader_history_ledger_root(right)


# ---------------------------------------------------------------------------
# F1 — certification envelope.
# ---------------------------------------------------------------------------


def test_certified_requires_certification_envelope() -> None:
    with pytest.raises(TraderHistoryValidationError):
        build_study_record(
            study_id=TraderHistoryStudyId(uuid4()),
            study_version=TraderHistoryStudyVersion("v1"),
            trader_version=_version(),
            kind=TraderHistoryStudyKind.REPLAY,
            epistemic_status=TraderHistoryEpistemicStatus.CERTIFIED,
            sufficiency=TraderHistorySufficiency.SUFFICIENT,
            produced_at=_NOW,
            producer=TraderHistoryProducerId("trader-lab"),
            market_scope=(TraderHistoryMarketRef("EUR/USD"),),
            timeframe_scope=(TraderHistoryTimeframeRef("h1"),),
            partitions=(_partition(SampleRole.DEVELOPMENT, 800),),
            quantitative_claims=(_metric("0.10"),),
        )


def test_caller_cannot_mint_certification_envelope() -> None:
    # A certification is sealed: the ordinary constructor can never set the
    # ``_issued`` marker, so a caller cannot forge an authority-backed
    # certification for a study (F1).
    with pytest.raises(TraderHistoryValidationError):
        TraderHistoryCertification(
            TraderHistoryAuthorityKind.CIBO,
            _AUTHORITY_ID,
            _NOW,
            TraderHistoryStudyId(uuid4()),
            TraderHistoryStudyVersion("v1"),
        )


def test_non_certified_rejects_certification_envelope() -> None:
    with pytest.raises(TraderHistoryValidationError):
        _study(
            kind=TraderHistoryStudyKind.CHARACTERIZATION,
            status=TraderHistoryEpistemicStatus.OBSERVED,
            certification=_certification(TraderHistoryStudyKind.CHARACTERIZATION),
        )


def test_certification_authority_kind_must_match_study_kind() -> None:
    with pytest.raises(TraderHistoryValidationError):
        _study(
            kind=TraderHistoryStudyKind.INDEPENDENT_VALIDATION,
            status=TraderHistoryEpistemicStatus.CERTIFIED,
            partitions=(_partition(SampleRole.EXTERNAL_VALIDATION, 802),),
            certification=_certification(
                TraderHistoryStudyKind.INDEPENDENT_VALIDATION,
                authority_kind=TraderHistoryAuthorityKind.TRADER_LAB,
            ),
        )


def test_certification_issued_at_cannot_predate_produced_at() -> None:
    with pytest.raises(TraderHistoryValidationError):
        _study(
            produced_at=_NOW,
            certification=_certification(
                TraderHistoryStudyKind.REPLAY, _NOW - timedelta(seconds=1)
            ),
        )


def test_certification_is_bound_into_study_fingerprint() -> None:
    left = _study(metrics=(_metric("0.10"),))
    different_issued_at = _study(
        metrics=(_metric("0.10"),),
        study_id=left.study_id,
        certification=_certification(
            TraderHistoryStudyKind.REPLAY,
            _NOW + timedelta(minutes=1),
        ),
    )
    # Same study content but a different certification issuance changes the
    # fingerprint: the certification envelope is cryptographically bound.
    assert left.fingerprint != different_issued_at.fingerprint


# ---------------------------------------------------------------------------
# F3 — contradiction fail-closed at the CIBO boundary.
# ---------------------------------------------------------------------------


def test_adapter_fails_closed_on_unresolved_contradiction() -> None:
    version = _version()
    left = _study(version=version, metrics=(_metric("0.10", ref="evidence:a"),))
    right = _study(version=version, metrics=(_metric("-0.05", ref="evidence:b"),))
    registry = TraderHistoricalIntelligenceRegistry(records=(left, right))
    result = project_cibo_capability_profile(
        registry,
        version,
        trader_identity=_identity(),
        qualified_markets=(CiboTradeableMarketRef("EUR/USD"),),
        qualified_timeframes=(CiboTimeframeCode("h1"),),
        evidence_as_of=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboTraderHistoryAdapterError)


# ---------------------------------------------------------------------------
# F6 — lineage-scoped, derived_at-scoped consumed holdouts.
# ---------------------------------------------------------------------------


def test_projection_does_not_leak_other_trader_holdouts() -> None:
    vt08 = _version(code="vt-08", config=401)
    vt01 = _version(code="vt-01", config=402)
    vt08_holdout = _partition(SampleRole.EXTERNAL_VALIDATION, 403)
    vt01_holdout = _partition(SampleRole.EXTERNAL_VALIDATION, 404)
    registry = TraderHistoricalIntelligenceRegistry(
        records=(
            _study(version=vt08, kind=TraderHistoryStudyKind.OOS, partitions=(vt08_holdout,)),
            _study(version=vt01, kind=TraderHistoryStudyKind.OOS, partitions=(vt01_holdout,)),
        )
    )
    view = project_current_capability(registry, vt08, derived_at=_NOW)
    assert isinstance(view, Success)
    assert view.value.consumed_holdouts == (vt08_holdout,)


def test_projection_does_not_leak_future_holdout_consumption() -> None:
    version = _version()
    past = _study(
        version=version,
        metrics=(_metric("0.10"),),
        produced_at=_NOW,
    )
    future_holdout = _partition(SampleRole.EXTERNAL_VALIDATION, 405)
    future = _study(
        version=version,
        kind=TraderHistoryStudyKind.OOS,
        metrics=(_metric("0.05", code="drawdown"),),
        produced_at=_NOW + timedelta(days=10),
        partitions=(future_holdout,),
    )
    registry = TraderHistoricalIntelligenceRegistry(records=(past, future))
    view = project_current_capability(registry, version, derived_at=_NOW)
    assert isinstance(view, Success)
    assert view.value.consumed_holdouts == ()


# ---------------------------------------------------------------------------
# F8 — canonical identity family.
# ---------------------------------------------------------------------------


def test_canonical_identity_family_is_virtual_trader() -> None:
    assert (
        compute_trader_identity_family(DemoTradingTraderCode("vt-08"))
        == "virtual.trader.vt08"
    )
    assert (
        compute_trader_identity_family(DemoTradingTraderCode("vt-31"))
        == "virtual.trader.vt31"
    )


def test_adapter_rejects_divergent_identity_family() -> None:
    version = _version()
    registry = TraderHistoricalIntelligenceRegistry(
        records=(_study(version=version, metrics=(_metric("0.10"),)),)
    )
    wrong = ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily("qore.trader.vt08"),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision("rev-1"),
    )
    result = project_cibo_capability_profile(
        registry,
        version,
        trader_identity=wrong,
        qualified_markets=(CiboTradeableMarketRef("EUR/USD"),),
        qualified_timeframes=(CiboTimeframeCode("h1"),),
        evidence_as_of=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboTraderHistoryAdapterError)


def test_adapter_rejects_schema_version_mismatch() -> None:
    version = _version()
    registry = TraderHistoricalIntelligenceRegistry(
        records=(_study(version=version, metrics=(_metric("0.10"),)),)
    )
    result = project_cibo_capability_profile(
        registry,
        version,
        trader_identity=_identity(schema_version="v2"),
        qualified_markets=(CiboTradeableMarketRef("EUR/USD"),),
        qualified_timeframes=(CiboTimeframeCode("h1"),),
        evidence_as_of=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboTraderHistoryAdapterError)


# ---------------------------------------------------------------------------
# F9 — duplicate dataset fingerprint within one study.
# ---------------------------------------------------------------------------


def test_duplicate_dataset_fingerprint_within_study_fails_closed() -> None:
    version = _version()
    first = _partition(SampleRole.DEVELOPMENT, 501)
    second = _partition(SampleRole.DEVELOPMENT, 501)  # same content, new partition id
    with pytest.raises(TraderHistoryValidationError):
        _study(version=version, partitions=(first, second))


def test_distinct_dataset_fingerprints_within_study_succeed() -> None:
    version = _version()
    first = _partition(SampleRole.DEVELOPMENT, 502)
    second = _partition(SampleRole.DEVELOPMENT, 503)
    study = _study(version=version, partitions=(first, second))
    assert len(study.partitions) == 2


# ---------------------------------------------------------------------------
# Hardening — superseded records leave market evidence and version diffs.
# ---------------------------------------------------------------------------


def test_superseded_record_is_excluded_from_market_evidence() -> None:
    version = _version()
    old = _study(version=version, markets=("EUR/USD",), metrics=(_metric("0.10"),))
    newer = _study(
        version=version,
        markets=("EUR/USD",),
        metrics=(_metric("0.20"),),
        supersedes=(old.study_id,),
    )
    registry = TraderHistoricalIntelligenceRegistry(records=(old, newer))
    evidence = market_evidence(registry, version, derived_at=_NOW)
    eur = next(item for item in evidence if item.market.value == "EUR/USD")
    assert [m.value for m in eur.certified_metrics] == [Decimal("0.20")]


def test_superseded_record_is_excluded_from_version_diff() -> None:
    v1 = _version(version="v1", config=601)
    old = _study(version=v1, metrics=(_metric("0.10"),))
    newer = _study(
        version=v1,
        metrics=(_metric("0.20"),),
        supersedes=(old.study_id,),
    )
    registry = TraderHistoricalIntelligenceRegistry(records=(old, newer))
    diff = diff_versions(registry, v1, v1, derived_at=_NOW)
    assert [m.value for m in diff.left_certified_metrics] == [Decimal("0.20")]


# ---------------------------------------------------------------------------
# Benign control — a full, valid capability projection still succeeds.
# ---------------------------------------------------------------------------


def test_benign_control_full_capability_projection_succeeds() -> None:
    version = _version()
    registry = TraderHistoricalIntelligenceRegistry(
        records=(_study(version=version, metrics=(_metric("0.12"),)),)
    )
    result = project_cibo_capability_profile(
        registry,
        version,
        trader_identity=_identity(),
        qualified_markets=(CiboTradeableMarketRef("EUR/USD"),),
        qualified_timeframes=(CiboTimeframeCode("h1"),),
        evidence_as_of=_NOW,
    )
    assert isinstance(result, Success)
    assert [m.metric_code for m in result.value.economic_metrics] == ["expectancy"]
    assert result.value.trader_identity.family.value == "virtual.trader.vt08"


# ---------------------------------------------------------------------------
# L6 repairs — F1 subject binding, F7 walk-forward holdout, D1 market/diff
# epistemic time, D3 sanctioned reconstruction, F7 zero-evidence fail-closed.
# ---------------------------------------------------------------------------


def test_certification_must_bind_exact_study_identity() -> None:
    version = _version()
    sid = TraderHistoryStudyId(uuid4())
    foreign = _certification(
        TraderHistoryStudyKind.REPLAY,
        study_id=TraderHistoryStudyId(uuid4()),  # bound to a different study
    )
    with pytest.raises(TraderHistoryValidationError):
        build_study_record(
            study_id=sid,
            study_version=TraderHistoryStudyVersion("v1"),
            trader_version=version,
            kind=TraderHistoryStudyKind.REPLAY,
            epistemic_status=TraderHistoryEpistemicStatus.CERTIFIED,
            sufficiency=TraderHistorySufficiency.SUFFICIENT,
            produced_at=_NOW,
            producer=TraderHistoryProducerId("trader-lab"),
            certification=foreign,
            market_scope=(TraderHistoryMarketRef("EUR/USD"),),
            timeframe_scope=(TraderHistoryTimeframeRef("h1"),),
            partitions=(_partition(SampleRole.DEVELOPMENT, 920),),
            quantitative_claims=(_metric("0.10"),),
        )


def test_walk_forward_requires_external_validation_holdout() -> None:
    version = _version()
    # A walk-forward study projects an out-of-sample CIBO stage, so it must
    # consume a held-out external-validation partition (F7 stage laundering).
    with pytest.raises(TraderHistoryValidationError):
        _study(
            version=version,
            kind=TraderHistoryStudyKind.WALK_FORWARD,
            metrics=(_metric("0.10"),),
            partitions=(_partition(SampleRole.DEVELOPMENT, 930),),
        )
    held_out = _study(
        version=version,
        kind=TraderHistoryStudyKind.WALK_FORWARD,
        metrics=(_metric("0.10"),),
        partitions=(_partition(SampleRole.EXTERNAL_VALIDATION, 931),),
    )
    assert held_out.kind is TraderHistoryStudyKind.WALK_FORWARD


def test_market_evidence_does_not_leak_future_certified_superseder() -> None:
    version = _version()
    target = _study(
        version=version,
        markets=("EUR/USD",),
        metrics=(_metric("0.10", ref="evidence:old"),),
    )
    superseder = _study(
        version=version,
        markets=("EUR/USD",),
        metrics=(_metric("0.20", ref="evidence:new"),),
        produced_at=_NOW,
        certification=_certification(
            TraderHistoryStudyKind.REPLAY, _NOW + timedelta(days=2)
        ),
        supersedes=(target.study_id,),
    )
    registry = TraderHistoricalIntelligenceRegistry(records=(target, superseder))
    # At day 1 the superseder's certification has not been issued: target remains
    # the active market evidence (D1 epistemic-time lookahead refused).
    evidence = market_evidence(
        registry, version, derived_at=_NOW + timedelta(days=1)
    )
    eur = next(item for item in evidence if item.market.value == "EUR/USD")
    assert [m.value for m in eur.certified_metrics] == [Decimal("0.10")]


def test_diff_versions_does_not_leak_future_certified_superseder() -> None:
    v1 = _version(version="v1", config=701)
    target = _study(version=v1, metrics=(_metric("0.10", ref="evidence:old"),))
    superseder = _study(
        version=v1,
        metrics=(_metric("0.20", ref="evidence:new"),),
        certification=_certification(
            TraderHistoryStudyKind.REPLAY, _NOW + timedelta(days=2)
        ),
        supersedes=(target.study_id,),
    )
    registry = TraderHistoricalIntelligenceRegistry(records=(target, superseder))
    diff = diff_versions(
        registry, v1, v1, derived_at=_NOW + timedelta(days=1)
    )
    assert [m.value for m in diff.left_certified_metrics] == [Decimal("0.10")]


def test_reconstruct_trader_history_refuses_truncation_without_matching_root() -> None:
    version = _version()
    first = _study(version=version, metrics=(_metric("0.10"),))
    second = _study(version=version, metrics=(_metric("0.05", code="drawdown"),))
    full = TraderHistoricalIntelligenceRegistry(records=(first, second))
    root = full.ledger_root()

    # Sanctioned reconstruction of a truncated record set must fail closed.
    truncated = reconstruct_trader_history((first,), root)
    assert isinstance(truncated, Failure)
    assert isinstance(truncated.error, TraderHistoryBlockedError)

    # Benign control: the complete record set matches the authoritative root.
    rebuilt = reconstruct_trader_history((first, second), root)
    assert isinstance(rebuilt, Success)
    assert rebuilt.value.records == full.records


def test_adapter_fails_closed_without_certified_quantitative_evidence() -> None:
    version = _version()
    # A CERTIFIED study with zero quantitative claims cannot fabricate a
    # collected/current capability profile (F7 freshness fabrication refused).
    empty = _study(version=version, metrics=())
    registry = TraderHistoricalIntelligenceRegistry(records=(empty,))
    result = project_cibo_capability_profile(
        registry,
        version,
        trader_identity=_identity(),
        qualified_markets=(CiboTradeableMarketRef("EUR/USD"),),
        qualified_timeframes=(CiboTimeframeCode("h1"),),
        evidence_as_of=_NOW,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboTraderHistoryAdapterError)
    assert "no current certified quantitative evidence" in str(result.error)
