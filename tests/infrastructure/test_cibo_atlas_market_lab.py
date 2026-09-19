from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.cibo_atlas_market_lab import (
    CiboAtlasComparisonDirection,
    CiboAtlasDiagnosticRule,
    CiboAtlasGapKind,
    CiboAtlasMarketLabValidationError,
    CiboAtlasMarketSnapshot,
    CiboAtlasMetric,
    CiboAtlasMetricTiming,
    CiboAtlasTraderSnapshot,
    compare_cibo_atlas_market_to_trader,
)
from qore.infrastructure.cibo_trader_capability_profile import (
    CiboEvidenceRef,
    CiboTradeableMarketRef,
    CiboTraderConfigFingerprint,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision
from qore.kernel.result import Failure, Success

_START = datetime(2016, 1, 1, tzinfo=UTC)
_END = datetime(2022, 7, 1, tzinfo=UTC)
_TRADER_START = datetime(2018, 1, 1, tzinfo=UTC)
_TRADER_END = datetime(2022, 1, 1, tzinfo=UTC)


def _ref(value: str) -> CiboEvidenceRef:
    return CiboEvidenceRef(value)


def _identity() -> ResearchDecisionEvaluatorIdentity:
    return ResearchDecisionEvaluatorIdentity(
        family=ResearchDecisionEvaluatorFamily("virtual.trader.vt31.nas100"),
        schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
        software_revision=ResearchSoftwareRevision("rev-1"),
    )


def _metric(
    code: str,
    value: str,
    *,
    timing: CiboAtlasMetricTiming = CiboAtlasMetricTiming.POST_OUTCOME_RESEARCH,
    evidence: str | None = None,
) -> CiboAtlasMetric:
    return CiboAtlasMetric(
        metric_code=code,
        value=Decimal(value),
        timing=timing,
        evidence_ref=_ref(evidence or f"atlas:{code}"),
    )


def _market(market: str = "NAS100") -> CiboAtlasMarketSnapshot:
    return CiboAtlasMarketSnapshot(
        market=CiboTradeableMarketRef(market),
        observed_from=_START,
        observed_to=_END,
        sample_count=1000,
        methodology_family="vt31-silver-bullet",
        evidence_ref=_ref("atlas:market-baseline"),
        metrics=(
            _metric("initial-stop-rate", "0.31", evidence="atlas:market-stop"),
            _metric(
                "raid-depth-reference",
                "0.06",
                timing=CiboAtlasMetricTiming.PRE_ENTRY,
                evidence="atlas:market-raid",
            ),
            _metric("target-rate", "0.37", evidence="atlas:market-target"),
        ),
    )


def _trader(market: str = "NAS100") -> CiboAtlasTraderSnapshot:
    return CiboAtlasTraderSnapshot(
        trader_identity=_identity(),
        config_fingerprint=CiboTraderConfigFingerprint("1" * 64),
        market=CiboTradeableMarketRef(market),
        observed_from=_TRADER_START,
        observed_to=_TRADER_END,
        sample_count=200,
        evidence_ref=_ref("atlas:trader-observation"),
        metrics=(
            _metric("initial-stop-rate", "0.47", evidence="atlas:trader-stop"),
            _metric(
                "raid-depth-reference",
                "0.08",
                timing=CiboAtlasMetricTiming.PRE_ENTRY,
                evidence="atlas:trader-raid",
            ),
            _metric("target-rate", "0.25", evidence="atlas:trader-target"),
        ),
    )


def test_market_metrics_are_canonical_and_immutable() -> None:
    market = _market()
    assert tuple(metric.metric_code for metric in market.metrics) == (
        "initial-stop-rate",
        "raid-depth-reference",
        "target-rate",
    )


def test_duplicate_market_metric_code_rejected() -> None:
    try:
        CiboAtlasMarketSnapshot(
            market=CiboTradeableMarketRef("NAS100"),
            observed_from=_START,
            observed_to=_END,
            sample_count=10,
            methodology_family="vt31-silver-bullet",
            evidence_ref=_ref("atlas:market"),
            metrics=(
                _metric("initial-stop-rate", "0.3"),
                _metric("initial-stop-rate", "0.4", evidence="atlas:duplicate"),
            ),
        )
    except CiboAtlasMarketLabValidationError:
        pass
    else:
        raise AssertionError("duplicate metric codes must fail closed")


def test_bool_cannot_launder_as_sample_count() -> None:
    try:
        CiboAtlasMarketSnapshot(
            market=CiboTradeableMarketRef("NAS100"),
            observed_from=_START,
            observed_to=_END,
            sample_count=True,
            methodology_family="vt31-silver-bullet",
            evidence_ref=_ref("atlas:market"),
            metrics=(),
        )
    except CiboAtlasMarketLabValidationError:
        pass
    else:
        raise AssertionError("bool sample count must fail closed")


def test_market_and_trader_must_match_exactly() -> None:
    result = compare_cibo_atlas_market_to_trader(
        market_snapshot=_market("NAS100"),
        trader_snapshot=_trader("SP500"),
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, CiboAtlasMarketLabValidationError)


def test_trader_window_must_be_contained_in_atlas_window() -> None:
    trader = CiboAtlasTraderSnapshot(
        trader_identity=_identity(),
        config_fingerprint=CiboTraderConfigFingerprint("1" * 64),
        market=CiboTradeableMarketRef("NAS100"),
        observed_from=datetime(2015, 1, 1, tzinfo=UTC),
        observed_to=_TRADER_END,
        sample_count=200,
        evidence_ref=_ref("atlas:trader-observation"),
        metrics=(),
    )
    result = compare_cibo_atlas_market_to_trader(
        market_snapshot=_market(),
        trader_snapshot=trader,
    )
    assert isinstance(result, Failure)


def test_comparison_emits_metric_gaps_without_selecting_market() -> None:
    result = compare_cibo_atlas_market_to_trader(
        market_snapshot=_market(),
        trader_snapshot=_trader(),
    )
    assert isinstance(result, Success)
    comparison = result.value
    gaps = {gap.metric_code: gap for gap in comparison.behavior_gaps}
    assert gaps["initial-stop-rate"].trader_minus_market == Decimal("0.16")
    assert gaps["target-rate"].trader_minus_market == Decimal("-0.12")
    assert comparison.research_only is True
    assert comparison.selection_prohibited is True
    assert comparison.opens_new_holdout is False
    assert comparison.live_authorized is False
    assert comparison.production_authorized is False


def test_predeclared_rule_fires_research_hypothesis_only() -> None:
    rule = CiboAtlasDiagnosticRule(
        rule_code="initial-stop-excess-v1",
        metric_code="initial-stop-rate",
        direction=CiboAtlasComparisonDirection.ABOVE,
        threshold=Decimal("0.10"),
        gap_kind=CiboAtlasGapKind.INITIAL_INVALIDATION,
        hypothesis_code="investigate-initial-invalidation",
        methodology_guard_ref=_ref("methodology:vt31-silver-bullet"),
    )
    result = compare_cibo_atlas_market_to_trader(
        market_snapshot=_market(),
        trader_snapshot=_trader(),
        rules=(rule,),
    )
    assert isinstance(result, Success)
    assert len(result.value.hypotheses) == 1
    hypothesis = result.value.hypotheses[0]
    assert hypothesis.hypothesis_code == "investigate-initial-invalidation"
    assert hypothesis.observed_gap == Decimal("0.16")


def test_rule_does_not_fire_below_threshold() -> None:
    rule = CiboAtlasDiagnosticRule(
        rule_code="initial-stop-excess-v1",
        metric_code="initial-stop-rate",
        direction=CiboAtlasComparisonDirection.ABOVE,
        threshold=Decimal("0.20"),
        gap_kind=CiboAtlasGapKind.INITIAL_INVALIDATION,
        hypothesis_code="investigate-initial-invalidation",
        methodology_guard_ref=_ref("methodology:vt31-silver-bullet"),
    )
    result = compare_cibo_atlas_market_to_trader(
        market_snapshot=_market(),
        trader_snapshot=_trader(),
        rules=(rule,),
    )
    assert isinstance(result, Success)
    assert result.value.hypotheses == ()


def test_metric_timing_mismatch_fails_closed() -> None:
    market = CiboAtlasMarketSnapshot(
        market=CiboTradeableMarketRef("NAS100"),
        observed_from=_START,
        observed_to=_END,
        sample_count=100,
        methodology_family="vt31-silver-bullet",
        evidence_ref=_ref("atlas:market"),
        metrics=(
            _metric(
                "raid-depth-reference",
                "0.06",
                timing=CiboAtlasMetricTiming.PRE_ENTRY,
            ),
        ),
    )
    trader = CiboAtlasTraderSnapshot(
        trader_identity=_identity(),
        config_fingerprint=CiboTraderConfigFingerprint("1" * 64),
        market=CiboTradeableMarketRef("NAS100"),
        observed_from=_TRADER_START,
        observed_to=_TRADER_END,
        sample_count=100,
        evidence_ref=_ref("atlas:trader"),
        metrics=(
            _metric(
                "raid-depth-reference",
                "0.08",
                timing=CiboAtlasMetricTiming.POST_OUTCOME_RESEARCH,
                evidence="atlas:trader-raid",
            ),
        ),
    )
    result = compare_cibo_atlas_market_to_trader(
        market_snapshot=market,
        trader_snapshot=trader,
    )
    assert isinstance(result, Failure)


def test_duplicate_rule_codes_fail_closed() -> None:
    rule = CiboAtlasDiagnosticRule(
        rule_code="same-code",
        metric_code="initial-stop-rate",
        direction=CiboAtlasComparisonDirection.ABOVE,
        threshold=Decimal("0.10"),
        gap_kind=CiboAtlasGapKind.INITIAL_INVALIDATION,
        hypothesis_code="investigate-initial-invalidation",
        methodology_guard_ref=_ref("methodology:vt31-silver-bullet"),
    )
    result = compare_cibo_atlas_market_to_trader(
        market_snapshot=_market(),
        trader_snapshot=_trader(),
        rules=(rule, rule),
    )
    assert isinstance(result, Failure)
