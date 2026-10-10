from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from re import fullmatch

from qore.infrastructure.cibo_trader_capability_profile import (
    CiboEvidenceRef,
    CiboTradeableMarketRef,
    CiboTraderConfigFingerprint,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorIdentity,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_CODE_RE = r"[a-z][a-z0-9._-]*"


class CiboAtlasMarketLabError(InfrastructureError):
    """Base error for CIBO Atlas market-laboratory contracts."""

    __slots__ = ()


class CiboAtlasMarketLabValidationError(CiboAtlasMarketLabError):
    """A CIBO Atlas market-laboratory invariant was violated."""

    __slots__ = ()


def _validate_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_CODE_RE, value) is None:
        raise CiboAtlasMarketLabValidationError(
            f"{field_name} must use canonical lowercase code syntax"
        )
    return value


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise CiboAtlasMarketLabValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboAtlasMarketLabValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_decimal(value: Decimal, *, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboAtlasMarketLabValidationError(
            f"{field_name} must be a finite Decimal"
        )


class CiboAtlasMetricTiming(StrEnum):
    """When a metric becomes knowable relative to a trade decision."""

    PRE_ENTRY = "pre-entry"
    POST_OUTCOME_RESEARCH = "post-outcome-research"


class CiboAtlasGapKind(StrEnum):
    """Behavioral gap families used for bounded research diagnosis."""

    DATA_COVERAGE = "data-coverage"
    SIGNAL_TIMING = "signal-timing"
    ENTRY_GEOMETRY = "entry-geometry"
    INITIAL_INVALIDATION = "initial-invalidation"
    LIFECYCLE_MANAGEMENT = "lifecycle-management"
    MARKET_REGIME = "market-regime"
    CROSS_INDEX_CONTEXT = "cross-index-context"
    EXECUTION_PATH = "execution-path"


class CiboAtlasComparisonDirection(StrEnum):
    """Predeclared direction for a metric-gap diagnostic rule."""

    ABOVE = "above"
    BELOW = "below"
    ABSOLUTE = "absolute"


@dataclass(frozen=True, slots=True)
class CiboAtlasMetric:
    """Evidence-backed scalar used by Atlas or a market-specialist trader."""

    metric_code: str
    value: Decimal
    timing: CiboAtlasMetricTiming
    evidence_ref: CiboEvidenceRef

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "metric_code",
            _validate_code(self.metric_code, field_name="Atlas metric code"),
        )
        _validate_decimal(self.value, field_name="Atlas metric value")
        if not isinstance(self.timing, CiboAtlasMetricTiming):
            raise CiboAtlasMarketLabValidationError(
                "Atlas metric timing requires CiboAtlasMetricTiming"
            )
        if not isinstance(self.evidence_ref, CiboEvidenceRef):
            raise CiboAtlasMarketLabValidationError(
                "Atlas metric requires CiboEvidenceRef"
            )

    def logical_values(self) -> tuple[object, ...]:
        normalized = Decimal(0) if self.value == 0 else self.value.normalize()
        return (
            self.metric_code,
            format(normalized, "f"),
            self.timing.value,
            self.evidence_ref.logical_values(),
        )


def _canonical_metrics(
    values: tuple[CiboAtlasMetric, ...], *, field_name: str
) -> tuple[CiboAtlasMetric, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(value, CiboAtlasMetric) for value in values
    ):
        raise CiboAtlasMarketLabValidationError(
            f"{field_name} must be an immutable tuple of CiboAtlasMetric"
        )
    codes = [value.metric_code for value in values]
    if len(codes) != len(set(codes)):
        raise CiboAtlasMarketLabValidationError(
            f"{field_name} must not contain duplicate metric codes"
        )
    return tuple(sorted(values, key=lambda value: value.metric_code))


@dataclass(frozen=True, slots=True)
class CiboAtlasMarketSnapshot:
    """Independent market baseline produced without trader selection semantics."""

    market: CiboTradeableMarketRef
    observed_from: datetime
    observed_to: datetime
    sample_count: int
    methodology_family: str
    evidence_ref: CiboEvidenceRef
    metrics: tuple[CiboAtlasMetric, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.market, CiboTradeableMarketRef):
            raise CiboAtlasMarketLabValidationError(
                "market snapshot requires CiboTradeableMarketRef"
            )
        _validate_timestamp(self.observed_from, field_name="market observed_from")
        _validate_timestamp(self.observed_to, field_name="market observed_to")
        if self.observed_to <= self.observed_from:
            raise CiboAtlasMarketLabValidationError(
                "market snapshot observed_to must be after observed_from"
            )
        if type(self.sample_count) is not int or self.sample_count <= 0:
            raise CiboAtlasMarketLabValidationError(
                "market snapshot sample_count must be a positive exact int"
            )
        object.__setattr__(
            self,
            "methodology_family",
            _validate_code(
                self.methodology_family,
                field_name="market methodology family",
            ),
        )
        if not isinstance(self.evidence_ref, CiboEvidenceRef):
            raise CiboAtlasMarketLabValidationError(
                "market snapshot requires CiboEvidenceRef"
            )
        object.__setattr__(
            self,
            "metrics",
            _canonical_metrics(self.metrics, field_name="market snapshot metrics"),
        )


@dataclass(frozen=True, slots=True)
class CiboAtlasTraderSnapshot:
    """One exact market-specialist trader observed against the Atlas baseline."""

    trader_identity: ResearchDecisionEvaluatorIdentity
    config_fingerprint: CiboTraderConfigFingerprint
    market: CiboTradeableMarketRef
    observed_from: datetime
    observed_to: datetime
    sample_count: int
    evidence_ref: CiboEvidenceRef
    metrics: tuple[CiboAtlasMetric, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.trader_identity, ResearchDecisionEvaluatorIdentity):
            raise CiboAtlasMarketLabValidationError(
                "trader snapshot requires ResearchDecisionEvaluatorIdentity"
            )
        if not isinstance(self.config_fingerprint, CiboTraderConfigFingerprint):
            raise CiboAtlasMarketLabValidationError(
                "trader snapshot requires CiboTraderConfigFingerprint"
            )
        if not isinstance(self.market, CiboTradeableMarketRef):
            raise CiboAtlasMarketLabValidationError(
                "trader snapshot requires CiboTradeableMarketRef"
            )
        _validate_timestamp(self.observed_from, field_name="trader observed_from")
        _validate_timestamp(self.observed_to, field_name="trader observed_to")
        if self.observed_to <= self.observed_from:
            raise CiboAtlasMarketLabValidationError(
                "trader snapshot observed_to must be after observed_from"
            )
        if type(self.sample_count) is not int or self.sample_count <= 0:
            raise CiboAtlasMarketLabValidationError(
                "trader snapshot sample_count must be a positive exact int"
            )
        if not isinstance(self.evidence_ref, CiboEvidenceRef):
            raise CiboAtlasMarketLabValidationError(
                "trader snapshot requires CiboEvidenceRef"
            )
        object.__setattr__(
            self,
            "metrics",
            _canonical_metrics(self.metrics, field_name="trader snapshot metrics"),
        )


@dataclass(frozen=True, slots=True)
class CiboAtlasDiagnosticRule:
    """Predeclared consumed-evidence rule for generating a research hypothesis."""

    rule_code: str
    metric_code: str
    direction: CiboAtlasComparisonDirection
    threshold: Decimal
    gap_kind: CiboAtlasGapKind
    hypothesis_code: str
    methodology_guard_ref: CiboEvidenceRef

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rule_code",
            _validate_code(self.rule_code, field_name="Atlas diagnostic rule code"),
        )
        object.__setattr__(
            self,
            "metric_code",
            _validate_code(self.metric_code, field_name="Atlas diagnostic metric code"),
        )
        object.__setattr__(
            self,
            "hypothesis_code",
            _validate_code(self.hypothesis_code, field_name="Atlas hypothesis code"),
        )
        if not isinstance(self.direction, CiboAtlasComparisonDirection):
            raise CiboAtlasMarketLabValidationError(
                "diagnostic rule requires CiboAtlasComparisonDirection"
            )
        _validate_decimal(self.threshold, field_name="Atlas diagnostic threshold")
        if self.threshold < 0:
            raise CiboAtlasMarketLabValidationError(
                "Atlas diagnostic threshold must be non-negative"
            )
        if not isinstance(self.gap_kind, CiboAtlasGapKind):
            raise CiboAtlasMarketLabValidationError(
                "diagnostic rule requires CiboAtlasGapKind"
            )
        if not isinstance(self.methodology_guard_ref, CiboEvidenceRef):
            raise CiboAtlasMarketLabValidationError(
                "diagnostic rule requires methodology guard evidence"
            )


@dataclass(frozen=True, slots=True)
class CiboAtlasBehaviorGap:
    metric_code: str
    market_value: Decimal
    trader_value: Decimal
    trader_minus_market: Decimal
    timing: CiboAtlasMetricTiming
    evidence_refs: tuple[CiboEvidenceRef, CiboEvidenceRef]


@dataclass(frozen=True, slots=True)
class CiboAtlasResearchHypothesis:
    rule_code: str
    hypothesis_code: str
    gap_kind: CiboAtlasGapKind
    metric_code: str
    observed_gap: Decimal
    threshold: Decimal
    methodology_guard_ref: CiboEvidenceRef


@dataclass(frozen=True, slots=True)
class CiboAtlasComparison:
    """Research-only comparison; never a trader selection or execution decision."""

    market: CiboTradeableMarketRef
    trader_identity: ResearchDecisionEvaluatorIdentity
    config_fingerprint: CiboTraderConfigFingerprint
    common_from: datetime
    common_to: datetime
    behavior_gaps: tuple[CiboAtlasBehaviorGap, ...]
    hypotheses: tuple[CiboAtlasResearchHypothesis, ...]
    research_only: bool = True
    selection_prohibited: bool = True
    opens_new_holdout: bool = False
    live_authorized: bool = False
    production_authorized: bool = False

    def __post_init__(self) -> None:
        if self.research_only is not True:
            raise CiboAtlasMarketLabValidationError(
                "Atlas comparison must remain research-only"
            )
        if self.selection_prohibited is not True:
            raise CiboAtlasMarketLabValidationError(
                "Atlas comparison cannot select or drop a market"
            )
        if self.opens_new_holdout is not False:
            raise CiboAtlasMarketLabValidationError(
                "Atlas comparison cannot open a new holdout"
            )
        if self.live_authorized is not False or self.production_authorized is not False:
            raise CiboAtlasMarketLabValidationError(
                "Atlas comparison cannot grant live or production authority"
            )


def compare_cibo_atlas_market_to_trader(
    *,
    market_snapshot: CiboAtlasMarketSnapshot,
    trader_snapshot: CiboAtlasTraderSnapshot,
    rules: tuple[CiboAtlasDiagnosticRule, ...] = (),
) -> Result[CiboAtlasComparison, CiboAtlasMarketLabError]:
    """Compare independent market behavior with one exact specialist trader.

    Rules are predeclared and can only emit research hypotheses. They cannot alter
    the trader, choose a market, promote a candidate, or open fresh evidence.
    """

    try:
        if not isinstance(market_snapshot, CiboAtlasMarketSnapshot):
            raise CiboAtlasMarketLabValidationError(
                "market_snapshot requires CiboAtlasMarketSnapshot"
            )
        if not isinstance(trader_snapshot, CiboAtlasTraderSnapshot):
            raise CiboAtlasMarketLabValidationError(
                "trader_snapshot requires CiboAtlasTraderSnapshot"
            )
        if market_snapshot.market != trader_snapshot.market:
            raise CiboAtlasMarketLabValidationError(
                "Atlas market and trader market must match exactly"
            )
        if trader_snapshot.observed_from < market_snapshot.observed_from or (
            trader_snapshot.observed_to > market_snapshot.observed_to
        ):
            raise CiboAtlasMarketLabValidationError(
                "trader observation window must be contained in Atlas market window"
            )
        if not isinstance(rules, tuple) or any(
            not isinstance(rule, CiboAtlasDiagnosticRule) for rule in rules
        ):
            raise CiboAtlasMarketLabValidationError(
                "rules must be an immutable tuple of CiboAtlasDiagnosticRule"
            )
        rule_codes = [rule.rule_code for rule in rules]
        if len(rule_codes) != len(set(rule_codes)):
            raise CiboAtlasMarketLabValidationError(
                "diagnostic rule codes must be unique"
            )

        market_metrics = {
            metric.metric_code: metric for metric in market_snapshot.metrics
        }
        trader_metrics = {
            metric.metric_code: metric for metric in trader_snapshot.metrics
        }
        common_codes = sorted(set(market_metrics) & set(trader_metrics))
        gaps: list[CiboAtlasBehaviorGap] = []
        gap_by_code: dict[str, CiboAtlasBehaviorGap] = {}
        for code in common_codes:
            market_metric = market_metrics[code]
            trader_metric = trader_metrics[code]
            if market_metric.timing is not trader_metric.timing:
                raise CiboAtlasMarketLabValidationError(
                    f"metric timing mismatch for {code}"
                )
            behavior_gap = CiboAtlasBehaviorGap(
                metric_code=code,
                market_value=market_metric.value,
                trader_value=trader_metric.value,
                trader_minus_market=trader_metric.value - market_metric.value,
                timing=market_metric.timing,
                evidence_refs=(market_metric.evidence_ref, trader_metric.evidence_ref),
            )
            gaps.append(behavior_gap)
            gap_by_code[code] = behavior_gap

        hypotheses: list[CiboAtlasResearchHypothesis] = []
        for rule in sorted(rules, key=lambda item: item.rule_code):
            candidate_gap = gap_by_code.get(rule.metric_code)
            if candidate_gap is None:
                continue
            observed = candidate_gap.trader_minus_market
            if rule.direction is CiboAtlasComparisonDirection.ABOVE:
                fired = observed >= rule.threshold
            elif rule.direction is CiboAtlasComparisonDirection.BELOW:
                fired = observed <= -rule.threshold
            else:
                fired = abs(observed) >= rule.threshold
            if fired:
                hypotheses.append(
                    CiboAtlasResearchHypothesis(
                        rule_code=rule.rule_code,
                        hypothesis_code=rule.hypothesis_code,
                        gap_kind=rule.gap_kind,
                        metric_code=rule.metric_code,
                        observed_gap=observed,
                        threshold=rule.threshold,
                        methodology_guard_ref=rule.methodology_guard_ref,
                    )
                )

        comparison = CiboAtlasComparison(
            market=market_snapshot.market,
            trader_identity=trader_snapshot.trader_identity,
            config_fingerprint=trader_snapshot.config_fingerprint,
            common_from=trader_snapshot.observed_from,
            common_to=trader_snapshot.observed_to,
            behavior_gaps=tuple(gaps),
            hypotheses=tuple(hypotheses),
        )
        return Success(comparison)
    except CiboAtlasMarketLabError as error:
        return Failure(error)
