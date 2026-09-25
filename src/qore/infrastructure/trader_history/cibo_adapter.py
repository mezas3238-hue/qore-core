"""Deterministic projection seam from historical intelligence into CIBO.

This adapter composes (never replaces) the existing immutable
``CiboTraderCapabilityProfile``. It projects only certified, sufficient,
evidence-backed quantitative claims from the append-only history into a profile,
maps the backing study kind to the exact ``CiboLabEvidenceStage``, and maps
favorable/weak/degraded/adverse conditions to ``CiboRegimeEvidenceRef``.

The adapter is read-only over history (it never mutates the registry) and it can
never manufacture ``DEMO_ELIGIBLE``: ``CiboTraderCapabilityProfile`` has no such
state, and this module constructs no ``CiboDemoEligibilityEvidence``, no order,
no execution/custody authority, and no Risk bypass.
"""

from __future__ import annotations

from datetime import datetime

from qore.infrastructure.cibo_trader_capability_profile import (
    CiboCapabilityProfileError,
    CiboCertificationState,
    CiboEconomicMetric,
    CiboEvidenceFreshness,
    CiboEvidenceFreshnessState,
    CiboEvidenceRef,
    CiboLabEvidenceRef,
    CiboLabEvidenceStage,
    CiboRegimeEvidenceRef,
    CiboRegimeKind,
    CiboSpecialtyCode,
    CiboTimeframeCode,
    CiboTradeableMarketRef,
    CiboTraderCapabilityProfile,
    CiboTraderConfigFingerprint,
    build_cibo_trader_capability_profile,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorIdentity,
)
from qore.infrastructure.trader_history.contracts import (
    TraderHistoryEpistemicStatus,
    TraderHistoryError,
    TraderHistoryFavorableKind,
    TraderHistoryStudyKind,
    TraderVersionIdentity,
    compute_trader_identity_family,
)
from qore.infrastructure.trader_history.registry import (
    TraderHistoricalIntelligenceRegistry,
    TraderHistoryMetricView,
    _certified_superseded_ids,
    _epistemic_moment,
    project_current_capability,
)
from qore.kernel.result import Failure, Result, Success

_STAGE_BY_KIND: dict[TraderHistoryStudyKind, CiboLabEvidenceStage] = {
    TraderHistoryStudyKind.REPLAY: CiboLabEvidenceStage.REPLAY,
    TraderHistoryStudyKind.BACKTEST: CiboLabEvidenceStage.REPLAY,
    TraderHistoryStudyKind.FAST_FORWARD: CiboLabEvidenceStage.FAST_FORWARD,
    TraderHistoryStudyKind.WALK_FORWARD: CiboLabEvidenceStage.OOS,
    TraderHistoryStudyKind.OOS: CiboLabEvidenceStage.OOS,
    TraderHistoryStudyKind.INDEPENDENT_VALIDATION: CiboLabEvidenceStage.OOS,
    TraderHistoryStudyKind.STRESS: CiboLabEvidenceStage.STRESS,
    TraderHistoryStudyKind.MONTE_CARLO: CiboLabEvidenceStage.MONTE_CARLO,
    TraderHistoryStudyKind.ECONOMIC_EVALUATION: CiboLabEvidenceStage.ECONOMIC,
    TraderHistoryStudyKind.RISK_REVIEW: CiboLabEvidenceStage.RISK,
    TraderHistoryStudyKind.HYPOTHESIS_CONFIRMATION: CiboLabEvidenceStage.OOS,
}

_REGIME_BY_CONDITION: dict[TraderHistoryFavorableKind, CiboRegimeKind] = {
    TraderHistoryFavorableKind.FAVORABLE: CiboRegimeKind.FAVORABLE,
    TraderHistoryFavorableKind.WEAK: CiboRegimeKind.WEAK,
    TraderHistoryFavorableKind.DEGRADED: CiboRegimeKind.DEGRADED,
    TraderHistoryFavorableKind.ADVERSE: CiboRegimeKind.DEGRADED,
}


class CiboTraderHistoryAdapterError(TraderHistoryError):
    """Fail-closed error for the historical intelligence -> CIBO projection seam."""

    __slots__ = ()


def _stages_for_evidence_ref(
    registry: TraderHistoricalIntelligenceRegistry,
    trader_version: TraderVersionIdentity,
    ref_value: str,
    *,
    derived_at: datetime,
) -> tuple[CiboLabEvidenceStage, ...]:
    """Resolve the exact CIBO lab evidence stages of one evidence ref.

    The current capability view merges evidence refs across every study that
    certifies the same metric/scope/value, so a single view can carry refs from
    studies of different kinds. Staging must therefore recover each ref's own
    backing study kind (never the first study of the merged view), otherwise
    out-of-sample evidence can be mislabeled as a development stage and vice
    versa. Only studies bound to the exact requested Trader version whose
    epistemic moment is on or before ``derived_at`` (and which are not
    superseded) are considered, so a future-certified or superseded study can
    never fabricate a stage. A certified study whose kind has no exact CIBO lab
    evidence stage fails closed rather than silently dropping certified evidence.
    """
    records = tuple(
        record
        for record in registry.records
        if record.trader_version.fingerprint == trader_version.fingerprint
        and _epistemic_moment(record) <= derived_at
    )
    superseded_ids = _certified_superseded_ids(records)
    stages: list[CiboLabEvidenceStage] = []
    found = False
    for record in records:
        if record.study_id in superseded_ids:
            continue
        if record.epistemic_status is not TraderHistoryEpistemicStatus.CERTIFIED:
            continue
        if not any(
            item.value == ref_value
            for metric in record.quantitative_claims
            for item in metric.evidence_refs
        ):
            continue
        found = True
        stage = _STAGE_BY_KIND.get(record.kind)
        if stage is None:
            raise CiboTraderHistoryAdapterError(
                f"certified study kind {record.kind.value!r} has no exact CIBO "
                "lab evidence stage; refusing to drop certified evidence"
            )
        if stage not in stages:
            stages.append(stage)
    if not found:
        raise CiboTraderHistoryAdapterError(
            f"evidence ref {ref_value!r} is not backed by a certified study"
        )
    return tuple(stages)


def project_cibo_capability_profile(
    registry: TraderHistoricalIntelligenceRegistry,
    trader_version: TraderVersionIdentity,
    *,
    trader_identity: ResearchDecisionEvaluatorIdentity,
    qualified_markets: tuple[CiboTradeableMarketRef, ...],
    qualified_timeframes: tuple[CiboTimeframeCode, ...],
    evidence_as_of: datetime,
    limitations: tuple[str, ...] = (),
) -> Result[CiboTraderCapabilityProfile, CiboTraderHistoryAdapterError]:
    """Project certified history into an immutable CIBO capability profile.

    Only certified + sufficient + evidence-backed claims are projected. Specialty
    is derived from the exact Trader methodology (never caller-asserted), scopes
    must be jointly backed by certified history, and unresolved current
    contradictions fail closed. ``certification_state`` and ``freshness`` are
    derived from the governed evidence at ``evidence_as_of`` (never caller
    assertion): a projection that reaches profile construction has current
    certified evidence, so the state is ``EVIDENCE_COLLECTED`` and the freshness
    is ``CURRENT``. Metric codes whose value diverges across scopes are
    deliberately not collapsed into a single global value (evidence specificity
    is preserved).
    """
    if type(registry) is not TraderHistoricalIntelligenceRegistry:
        return Failure(
            CiboTraderHistoryAdapterError(
                "adapter requires TraderHistoricalIntelligenceRegistry"
            )
        )
    if type(trader_version) is not TraderVersionIdentity:
        return Failure(
            CiboTraderHistoryAdapterError("adapter requires TraderVersionIdentity")
        )
    if type(trader_identity) is not ResearchDecisionEvaluatorIdentity:
        return Failure(
            CiboTraderHistoryAdapterError(
                "adapter requires ResearchDecisionEvaluatorIdentity"
            )
        )
    expected_identity_family = compute_trader_identity_family(
        trader_version.trader_code
    )
    if trader_identity.family.value != expected_identity_family:
        return Failure(
            CiboTraderHistoryAdapterError(
                "trader identity family must match the exact Trader version code: "
                f"expected {expected_identity_family!r}, got "
                f"{trader_identity.family.value!r}"
            )
        )
    if trader_identity.schema_version.value != trader_version.version.value:
        return Failure(
            CiboTraderHistoryAdapterError(
                "trader identity schema version must match the exact Trader version: "
                f"expected {trader_version.version.value!r}, got "
                f"{trader_identity.schema_version.value!r}"
            )
        )
    if type(evidence_as_of) is not datetime:
        return Failure(
            CiboTraderHistoryAdapterError("adapter requires evidence_as_of datetime")
        )
    if evidence_as_of.tzinfo is None or evidence_as_of.utcoffset() is None:
        return Failure(
            CiboTraderHistoryAdapterError("evidence_as_of must be timezone-aware")
        )
    if type(qualified_markets) is not tuple or any(
        type(item) is not CiboTradeableMarketRef for item in qualified_markets
    ):
        return Failure(
            CiboTraderHistoryAdapterError(
                "qualified_markets must be an exact CiboTradeableMarketRef tuple"
            )
        )
    if type(qualified_timeframes) is not tuple or any(
        type(item) is not CiboTimeframeCode for item in qualified_timeframes
    ):
        return Failure(
            CiboTraderHistoryAdapterError(
                "qualified_timeframes must be an exact CiboTimeframeCode tuple"
            )
        )
    try:
        projection = project_current_capability(
            registry,
            trader_version,
            derived_at=evidence_as_of,
        )
        if isinstance(projection, Failure):
            return Failure(
                CiboTraderHistoryAdapterError(
                    f"current capability projection failed: {projection.error}"
                )
            )
        view = projection.value

        # F3: unresolved current certified contradictions must never disappear at
        # the CIBO boundary. They fail closed rather than silently vanishing.
        if view.contradictions:
            raise CiboTraderHistoryAdapterError(
                "unresolved certified contradictions prevent a CIBO capability "
                "projection; refusing to drop contradictory evidence"
            )

        # A CIBO capability is a projection of verified current certified
        # quantitative evidence. With no certified quantitative claims to
        # project, claiming EVIDENCE_COLLECTED/CURRENT would be fabrication (F7).
        if not view.certified_metrics:
            raise CiboTraderHistoryAdapterError(
                "no current certified quantitative evidence to project; refusing "
                "to fabricate a collected/current certification state"
            )

        current_records = tuple(
            record
            for record in registry.records
            if record.trader_version.fingerprint == trader_version.fingerprint
            and _epistemic_moment(record) <= evidence_as_of
        )
        superseded_ids = {
            target
            for record in current_records
            if record.epistemic_status is TraderHistoryEpistemicStatus.CERTIFIED
            for target in record.supersedes
        }
        certified_scope_records = tuple(
            record
            for record in current_records
            if record.epistemic_status is TraderHistoryEpistemicStatus.CERTIFIED
            and record.study_id not in superseded_ids
        )
        # D2: market/timeframe scope is JOINT, never Cartesian. Each requested
        # (market, timeframe) pair must be explicitly backed by certified history.
        # A certified study that declares both multi-market and multi-timeframe
        # scope has no explicit joint tuples, so its Cartesian cross product is
        # ambiguous and must fail closed rather than fabricate pairings.
        backed_joint_scopes: set[tuple[str, str]] = set()
        for record in certified_scope_records:
            if len(record.market_scope) > 1 and len(record.timeframe_scope) > 1:
                raise CiboTraderHistoryAdapterError(
                    "certified study declares multi-market x multi-timeframe scope "
                    "without explicit joint tuples; ambiguous joint scope refused"
                )
            for market in record.market_scope:
                for timeframe in record.timeframe_scope:
                    backed_joint_scopes.add((market.value, timeframe.value))
        requested_joint_scopes = {
            (market.value, timeframe.value)
            for market in qualified_markets
            for timeframe in qualified_timeframes
        }
        unsupported_joint_scopes = tuple(
            sorted(requested_joint_scopes - backed_joint_scopes)
        )
        if unsupported_joint_scopes:
            raise CiboTraderHistoryAdapterError(
                "qualified market/timeframe combinations are not backed by current "
                "certified historical evidence: "
                f"{unsupported_joint_scopes!r}"
            )

        by_code: dict[str, list[TraderHistoryMetricView]] = {}
        for metric in view.certified_metrics:
            by_code.setdefault(metric.metric_code, []).append(metric)

        economic_metrics: list[CiboEconomicMetric] = []
        lab_evidence: dict[tuple[str, str], CiboLabEvidenceRef] = {}
        regime_evidence: dict[tuple[str, str], CiboRegimeEvidenceRef] = {}
        for code, metric_views in sorted(by_code.items()):
            distinct_values = {item.value for item in metric_views}
            if len(distinct_values) != 1:
                # Divergent market/regime-specific values are never collapsed.
                continue
            all_refs: set[str] = set()
            for item in metric_views:
                for ref in item.evidence_refs:
                    cibo_ref = CiboEvidenceRef(ref.value)
                    for stage in _stages_for_evidence_ref(
                        registry,
                        trader_version,
                        ref.value,
                        derived_at=evidence_as_of,
                    ):
                        lab_evidence[(stage.value, cibo_ref.value)] = CiboLabEvidenceRef(
                            stage, cibo_ref
                        )
                    all_refs.add(ref.value)
            if not all_refs:
                continue
            primary_ref = sorted(all_refs)[0]
            economic_metrics.append(
                CiboEconomicMetric(
                    metric_code=code,
                    value=distinct_values.pop(),
                    evidence_ref=CiboEvidenceRef(primary_ref),
                )
            )

        for metric in view.certified_metrics:
            condition = metric.condition
            if condition is None:
                continue
            for ref in metric.evidence_refs:
                cibo_ref = CiboEvidenceRef(ref.value)
                regime = _REGIME_BY_CONDITION[condition]
                regime_evidence.setdefault(
                    (regime.value, cibo_ref.value),
                    CiboRegimeEvidenceRef(regime, cibo_ref),
                )

        profile = build_cibo_trader_capability_profile(
            trader_identity=trader_identity,
            config_fingerprint=CiboTraderConfigFingerprint(
                trader_version.config_fingerprint.value
            ),
            specialty=CiboSpecialtyCode(trader_version.methodology_id.value),
            qualified_markets=qualified_markets,
            qualified_timeframes=qualified_timeframes,
            certified_lab_evidence=tuple(
                sorted(
                    lab_evidence.values(),
                    key=lambda item: (item.stage.value, item.ref.value),
                )
            ),
            regime_evidence=tuple(
                sorted(
                    regime_evidence.values(),
                    key=lambda item: (item.regime.value, item.ref.value),
                )
            ),
            economic_metrics=tuple(
                sorted(economic_metrics, key=lambda item: item.metric_code)
            ),
            certification_state=CiboCertificationState.EVIDENCE_COLLECTED,
            freshness=CiboEvidenceFreshness(
                state=CiboEvidenceFreshnessState.CURRENT,
                as_of=evidence_as_of,
            ),
            limitations=limitations,
        )
    except CiboCapabilityProfileError as error:
        return Failure(
            CiboTraderHistoryAdapterError(
                f"CIBO capability profile projection failed: {error}"
            )
        )
    except CiboTraderHistoryAdapterError as error:
        return Failure(error)
    if isinstance(profile, Failure):
        return Failure(
            CiboTraderHistoryAdapterError(
                f"CIBO capability profile construction failed: {profile.error}"
            )
        )
    return Success(profile.value)


__all__ = [
    "CiboTraderHistoryAdapterError",
    "project_cibo_capability_profile",
]
