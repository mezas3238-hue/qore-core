"""D2 closure: every exact Trader version dimension is representable by the
evidence-bound capability profile (CF-03/CF-04 ownership).

The capability profile contract itself is predecessor material and is not
modified; this test proves the profile can carry evidence-bound material for
every dimension required by D2:

- exact trader/methodology/config version;
- specialty;
- qualified markets/instruments/timeframes;
- favorable and degraded regimes;
- calibration and recurring errors;
- transaction-cost sensitivity;
- drawdown/tail behavior;
- known limitations;
- correlation/dependence;
- Risk envelope and qualification/certification state.

All evidence is referenced (opaque, sanitized) rather than embedded; nothing here
manufactures DEMO eligibility, promotion, Risk approval, or execution authority.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.cibo_trader_capability_profile import (
    CiboCertificationState,
    CiboEconomicMetric,
    CiboEvidenceFreshness,
    CiboEvidenceFreshnessState,
    CiboEvidenceRef,
    CiboLabEvidenceRef,
    CiboLabEvidenceStage,
    CiboOperatingAction,
    CiboOperatingCondition,
    CiboRegimeEvidenceRef,
    CiboRegimeKind,
    CiboSpecialtyCode,
    CiboTimeframeCode,
    CiboTradeableMarketRef,
    CiboTraderConfigFingerprint,
    build_cibo_trader_capability_profile,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.kernel.result import Success

_NOW = datetime(2026, 8, 9, 0, 0, tzinfo=UTC)


def _ref(name: str) -> CiboEvidenceRef:
    return CiboEvidenceRef(f"evidence:{name}")


def test_full_capability_profile_represents_every_dimension() -> None:
    # exact trader/methodology/config version
    identity = ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily("virtual.trader.vt01"),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision("rev-1"),
    )
    fingerprint = CiboTraderConfigFingerprint(f"{1:064x}")

    # calibration + drawdown/tail + recurring errors are represented as certified
    # economic metrics backed by certified Lab evidence (OOS/STRESS calibration
    # stages plus economic stage).
    calibration_ref = _ref("calibration-oos")
    drawdown_ref = _ref("drawdown-tail")
    certified_lab_evidence = (
        CiboLabEvidenceRef(stage=CiboLabEvidenceStage.OOS, ref=calibration_ref),
        CiboLabEvidenceRef(stage=CiboLabEvidenceStage.STRESS, ref=_ref("stress-recurring")),
        CiboLabEvidenceRef(stage=CiboLabEvidenceStage.ECONOMIC, ref=drawdown_ref),
    )
    economic_metrics = (
        CiboEconomicMetric(
            metric_code="calibration.error.mean",
            value=Decimal("0.12"),
            evidence_ref=calibration_ref,
        ),
        CiboEconomicMetric(
            metric_code="drawdown.max",
            value=Decimal("0.18"),
            evidence_ref=drawdown_ref,
        ),
        CiboEconomicMetric(
            metric_code="tail.var.95",
            value=Decimal("0.09"),
            evidence_ref=drawdown_ref,
        ),
    )

    result = build_cibo_trader_capability_profile(
        trader_identity=identity,
        config_fingerprint=fingerprint,
        specialty=CiboSpecialtyCode("trend-following"),
        qualified_markets=(CiboTradeableMarketRef("EUR/USD"),),
        qualified_timeframes=(CiboTimeframeCode("h1"),),
        certified_lab_evidence=certified_lab_evidence,
        regime_evidence=(
            CiboRegimeEvidenceRef(regime=CiboRegimeKind.FAVORABLE, ref=_ref("favorable")),
            CiboRegimeEvidenceRef(regime=CiboRegimeKind.DEGRADED, ref=_ref("degraded")),
        ),
        economic_metrics=economic_metrics,
        cost_sensitivity=(_ref("cost-sensitivity"),),
        correlation_evidence=(_ref("correlation"),),
        risk_envelope=(_ref("risk-envelope"),),
        operating_conditions=(
            CiboOperatingCondition(
                action=CiboOperatingAction.REDUCE,
                reason_code="drawdown-limit",
                evidence_ref=drawdown_ref,
            ),
        ),
        certification_state=CiboCertificationState.EVIDENCE_COLLECTED,
        freshness=CiboEvidenceFreshness(
            state=CiboEvidenceFreshnessState.CURRENT,
            as_of=_NOW,
        ),
        limitations=("high-frequency-cost", "tail-dependence"),
    )

    assert isinstance(result, Success)
    profile = result.value
    # every dimension is materially present, exact, and deterministic.
    assert profile.trader_identity == identity
    assert profile.config_fingerprint == fingerprint
    assert profile.specialty == CiboSpecialtyCode("trend-following")
    assert profile.qualified_markets == (CiboTradeableMarketRef("EUR/USD"),)
    assert profile.qualified_timeframes == (CiboTimeframeCode("h1"),)
    assert any(item.stage is CiboLabEvidenceStage.OOS for item in profile.certified_lab_evidence)
    assert any(item.stage is CiboLabEvidenceStage.STRESS for item in profile.certified_lab_evidence)
    assert any(
        item.regime is CiboRegimeKind.FAVORABLE for item in profile.regime_evidence
    )
    assert any(item.regime is CiboRegimeKind.DEGRADED for item in profile.regime_evidence)
    metric_codes = {item.metric_code for item in profile.economic_metrics}
    assert {"calibration.error.mean", "drawdown.max", "tail.var.95"} <= metric_codes
    assert profile.cost_sensitivity == (_ref("cost-sensitivity"),)
    assert profile.correlation_evidence == (_ref("correlation"),)
    assert profile.risk_envelope == (_ref("risk-envelope"),)
    assert profile.limitations == ("high-frequency-cost", "tail-dependence")
    assert profile.certification_state is CiboCertificationState.EVIDENCE_COLLECTED
    # DEMO_ELIGIBLE is structurally absent: capability never manufactures eligibility.
    assert not hasattr(CiboCertificationState, "DEMO_ELIGIBLE")


def test_capability_profile_cannot_manufacture_demo_eligibility() -> None:
    # The certification state catalog has no DEMO_ELIGIBLE member; a capability
    # profile is capability material, never a promotion/eligibility receipt.
    for member in CiboCertificationState:
        assert member.value != "demo-eligible"
