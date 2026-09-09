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

from qore.infrastructure.cibo_trader_capability_profile import (
    CiboCapabilityProfileError,
    CiboCertificationState,
    CiboEconomicMetric,
    CiboEvidenceFreshness,
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
)
from qore.infrastructure.trader_history.registry import (
    TraderHistoricalIntelligenceRegistry,
    TraderHistoryMetricView,
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
) -> tuple[CiboLabEvidenceStage, ...]:
    """Resolve the exact CIBO lab evidence stages of one evidence ref.

    The current capability view merges evidence refs across every study that
    certifies the same metric/scope/value, so a single view can carry refs from
    studies of different kinds. Staging must therefore recover each ref's own
    backing study kind (never the first study of the merged view), otherwise
    out-of-sample evidence can be mislabeled as a development stage and vice
    versa. Only studies bound to the exact requested Trader version are
    considered. A certified study whose kind has no exact CIBO lab evidence stage
    fails closed rather than silently dropping certified evidence.
    """
    stages: list[CiboLabEvidenceStage] = []
    found = False
    for record in registry.records:
        if record.trader_version.fingerprint != trader_version.fingerprint:
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
    specialty: CiboSpecialtyCode,
    qualified_markets: tuple[CiboTradeableMarketRef, ...],
    qualified_timeframes: tuple[CiboTimeframeCode, ...],
    certification_state: CiboCertificationState,
    freshness: CiboEvidenceFreshness,
    limitations: tuple[str, ...] = (),
) -> Result[CiboTraderCapabilityProfile, CiboTraderHistoryAdapterError]:
    """Project certified history into an immutable CIBO capability profile.

    Only certified + sufficient + evidence-backed claims are projected. Metric
    codes whose value diverges across scopes are deliberately not collapsed into
    a single global value (evidence specificity is preserved), and the profile is
    built through the existing validated constructor so all CIBO invariants hold.
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
    expected_identity_family = (
        "virtual.trader." + trader_version.trader_code.value.replace("-", "")
    )
    if trader_identity.family.value != expected_identity_family:
        return Failure(
            CiboTraderHistoryAdapterError(
                "trader identity family must match the exact Trader version code: "
                f"expected {expected_identity_family!r}, got "
                f"{trader_identity.family.value!r}"
            )
        )
    if type(certification_state) is not CiboCertificationState:
        return Failure(
            CiboTraderHistoryAdapterError("adapter requires CiboCertificationState")
        )
    if type(freshness) is not CiboEvidenceFreshness:
        return Failure(
            CiboTraderHistoryAdapterError("adapter requires CiboEvidenceFreshness")
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
            derived_at=freshness.as_of,
        )
        if isinstance(projection, Failure):
            return Failure(
                CiboTraderHistoryAdapterError(
                    f"current capability projection failed: {projection.error}"
                )
            )
        view = projection.value

        current_records = tuple(
            record
            for record in registry.records
            if record.trader_version.fingerprint == trader_version.fingerprint
            and record.produced_at <= freshness.as_of
        )
        superseded_ids = {
            target for record in current_records for target in record.supersedes
        }
        certified_scope_records = tuple(
            record
            for record in current_records
            if record.epistemic_status is TraderHistoryEpistemicStatus.CERTIFIED
            and record.study_id not in superseded_ids
        )
        supported_markets = {
            market.value
            for record in certified_scope_records
            for market in record.market_scope
        }
        supported_timeframes = {
            timeframe.value
            for record in certified_scope_records
            for timeframe in record.timeframe_scope
        }
        unsupported_markets = tuple(
            sorted(
                item.value
                for item in qualified_markets
                if item.value not in supported_markets
            )
        )
        unsupported_timeframes = tuple(
            sorted(
                item.value
                for item in qualified_timeframes
                if item.value not in supported_timeframes
            )
        )
        if unsupported_markets:
            raise CiboTraderHistoryAdapterError(
                "qualified markets are not backed by current certified historical "
                f"evidence: {unsupported_markets!r}"
            )
        if unsupported_timeframes:
            raise CiboTraderHistoryAdapterError(
                "qualified timeframes are not backed by current certified historical "
                f"evidence: {unsupported_timeframes!r}"
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
                        registry, trader_version, ref.value
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
            specialty=specialty,
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
            certification_state=certification_state,
            freshness=freshness,
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
