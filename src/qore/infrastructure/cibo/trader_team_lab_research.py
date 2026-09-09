"""Post-decision research, memory and characterization for CIBO routing.

Everything in this module consumes an already-frozen CIBO decision.  The oracle
and all future outcomes live exclusively here and cannot flow back into the
decision-time API in :mod:`trader_team_lab`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from qore.infrastructure.cibo.trader_team_lab import (
    CiboFiveTraderShadowEvaluation,
    CiboMetaSelectionDecision,
    TraderTeamLabError,
    TraderTeamLabValidationError,
    _aware,
    _code,
    _codes,
    _decimal,
    _fingerprint,
    _utc,
)
from qore.infrastructure.traders.contracts import (
    DemoTradingDecision,
    DemoTradingTraderIdentity,
)
from qore.kernel.result import Failure, Result, Success


class CiboFailureFamily(StrEnum):
    NONE = "none"
    MARKET_UNDERSTANDING = "market-understanding"
    TRADER_SELECTION = "trader-selection"
    SELECTED_TRADER = "selected-trader"
    REGIME_CHANGE = "regime-change"
    EXECUTION_COST = "execution-cost"
    LUCKY_PROFIT = "lucky-profit"


@dataclass(frozen=True, slots=True)
class TraderCounterfactualOutcome:
    """Future outcome of one exact decision-time Trader output."""

    trader_identity: DemoTradingTraderIdentity
    output_fingerprint: str
    realized_return: Decimal
    r_multiple: Decimal | None
    won: bool | None
    mae: Decimal
    mfe: Decimal
    duration_seconds: int
    cost_adjusted_return: Decimal
    abstained: bool
    drawdown_contribution: Decimal
    outcome_at: datetime
    provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        self.trader_identity.__post_init__()
        if type(self.output_fingerprint) is not str or len(self.output_fingerprint) != 64:
            raise TraderTeamLabValidationError("outcome requires output SHA-256")
        for field, value in (
            ("realized return", self.realized_return),
            ("mae", self.mae),
            ("mfe", self.mfe),
            ("cost adjusted return", self.cost_adjusted_return),
            ("drawdown contribution", self.drawdown_contribution),
        ):
            _decimal(value, field)
        if self.r_multiple is not None:
            _decimal(self.r_multiple, "R multiple")
        if self.won is not None and type(self.won) is not bool:
            raise TraderTeamLabValidationError("won must be bool or None")
        if type(self.duration_seconds) is not int or self.duration_seconds < 0:
            raise TraderTeamLabValidationError("duration must be non-negative int")
        if type(self.abstained) is not bool:
            raise TraderTeamLabValidationError("abstained must be bool")
        if self.abstained and (
            self.realized_return != 0
            or self.cost_adjusted_return != 0
            or self.r_multiple is not None
            or self.won is not None
        ):
            raise TraderTeamLabValidationError("abstention must retain a zero/no-trade outcome")
        _aware(self.outcome_at, "outcome_at")
        object.__setattr__(self, "provenance", _codes(self.provenance, "outcome provenance"))
        if not self.provenance:
            raise TraderTeamLabValidationError("outcome requires provenance")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.trader_identity.logical_values(),
            self.output_fingerprint,
            format(self.realized_return.normalize(), "f"),
            None if self.r_multiple is None else format(self.r_multiple.normalize(), "f"),
            self.won,
            format(self.mae.normalize(), "f"),
            format(self.mfe.normalize(), "f"),
            self.duration_seconds,
            format(self.cost_adjusted_return.normalize(), "f"),
            self.abstained,
            format(self.drawdown_contribution.normalize(), "f"),
            _utc(self.outcome_at),
            self.provenance,
        )


@dataclass(frozen=True, slots=True)
class CiboMarketReadingAssessment:
    predicted_regime: str
    realized_regime: str
    correct: bool
    regime_changed_after_decision: bool
    assessed_at: datetime
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _code(self.predicted_regime, "predicted regime")
        _code(self.realized_regime, "realized regime")
        if type(self.correct) is not bool or type(self.regime_changed_after_decision) is not bool:
            raise TraderTeamLabValidationError("market reading flags must be bool")
        _aware(self.assessed_at, "market reading assessed_at")
        object.__setattr__(
            self, "evidence_refs", _codes(self.evidence_refs, "market reading evidence")
        )
        if not self.evidence_refs:
            raise TraderTeamLabValidationError("market reading requires evidence")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.predicted_regime,
            self.realized_regime,
            self.correct,
            self.regime_changed_after_decision,
            _utc(self.assessed_at),
            self.evidence_refs,
        )


@dataclass(frozen=True, slots=True)
class CiboCounterfactualEvaluation:
    decision: CiboMetaSelectionDecision
    outcomes: tuple[TraderCounterfactualOutcome, ...]
    market_reading: CiboMarketReadingAssessment
    selected_outcome: Decimal
    best_available_outcome: Decimal
    worst_available_outcome: Decimal
    none_outcome: Decimal
    selection_correct: bool
    selection_regret: Decimal
    opportunity_regret: Decimal
    abstention_quality: bool | None
    unnecessary_trade: bool
    missed_opportunity: bool
    failure_family: CiboFailureFamily
    evaluated_at: datetime
    fingerprint: str
    oracle_evaluation_only: bool = True

    def __post_init__(self) -> None:
        self.decision.__post_init__()
        if type(self.outcomes) is not tuple or len(self.outcomes) != 5:
            raise TraderTeamLabValidationError("counterfactual requires five outcomes")
        for item in self.outcomes:
            item.__post_init__()
            if item.outcome_at <= self.decision.decided_at:
                raise TraderTeamLabValidationError("future outcome must postdate frozen decision")
        codes = tuple(item.trader_identity.trader_code.value for item in self.outcomes)
        if tuple(sorted(codes)) != codes or len(set(codes)) != 5:
            raise TraderTeamLabValidationError(
                "counterfactual outcomes must be unique and canonical"
            )
        self.market_reading.__post_init__()
        if self.market_reading.assessed_at <= self.decision.decided_at:
            raise TraderTeamLabValidationError("market reading outcome must be post-decision")
        for field, value in (
            ("selected outcome", self.selected_outcome),
            ("best outcome", self.best_available_outcome),
            ("worst outcome", self.worst_available_outcome),
            ("none outcome", self.none_outcome),
            ("selection regret", self.selection_regret),
            ("opportunity regret", self.opportunity_regret),
        ):
            _decimal(value, field)
        if self.none_outcome != 0:
            raise TraderTeamLabValidationError("NONE baseline outcome must be zero")
        if any(
            type(value) is not bool
            for value in (self.selection_correct, self.unnecessary_trade, self.missed_opportunity)
        ):
            raise TraderTeamLabValidationError("counterfactual flags must be bool")
        if self.abstention_quality is not None and type(self.abstention_quality) is not bool:
            raise TraderTeamLabValidationError("abstention quality must be bool or None")
        if type(self.failure_family) is not CiboFailureFamily:
            raise TraderTeamLabValidationError("failure family must be exact")
        _aware(self.evaluated_at, "counterfactual evaluated_at")
        if self.evaluated_at < max(item.outcome_at for item in self.outcomes):
            raise TraderTeamLabValidationError("evaluation cannot precede outcomes")
        if self.oracle_evaluation_only is not True:
            raise TraderTeamLabValidationError("oracle must remain evaluation-only")
        returns = tuple(item.cost_adjusted_return for item in self.outcomes)
        expected_best = max((*returns, Decimal(0)))
        expected_worst = min((*returns, Decimal(0)))
        by_code = {item.trader_identity.trader_code.value: item for item in self.outcomes}
        expected_selected = (
            Decimal(0)
            if self.decision.selected is None
            else by_code[self.decision.selected.trader_code.value].cost_adjusted_return
        )
        raw_selected = (
            Decimal(0)
            if self.decision.selected is None
            else by_code[self.decision.selected.trader_code.value].realized_return
        )
        expected_abstention = None if self.decision.selected is not None else expected_best <= 0
        expected_values = (
            expected_selected,
            expected_best,
            expected_worst,
            expected_best - expected_selected,
            max(Decimal(0), expected_best) - expected_selected,
            expected_selected == expected_best,
            expected_abstention,
            self.decision.selected is not None and expected_selected <= 0,
            self.decision.selected is None and expected_best > 0,
        )
        retained_values = (
            self.selected_outcome,
            self.best_available_outcome,
            self.worst_available_outcome,
            self.selection_regret,
            self.opportunity_regret,
            self.selection_correct,
            self.abstention_quality,
            self.unnecessary_trade,
            self.missed_opportunity,
        )
        if retained_values != expected_values:
            raise TraderTeamLabValidationError(
                "counterfactual metrics must equal canonical recomputation"
            )
        expected_failure = _diagnose(
            decision=self.decision,
            selected_outcome=expected_selected,
            best_outcome=expected_best,
            market_reading=self.market_reading,
            cost_harmed=raw_selected > 0 >= expected_selected,
        )
        if self.failure_family is not expected_failure:
            raise TraderTeamLabValidationError(
                "counterfactual failure family must equal canonical diagnosis"
            )
        if self.fingerprint != self.compute_fingerprint():
            raise TraderTeamLabValidationError("counterfactual fingerprint mismatch")

    def compute_fingerprint(self) -> str:
        return _fingerprint(
            (
                "qore.cibo.counterfactual.v1",
                self.decision.fingerprint,
                tuple(item.logical_values() for item in self.outcomes),
                self.market_reading.logical_values(),
                format(self.selected_outcome.normalize(), "f"),
                format(self.best_available_outcome.normalize(), "f"),
                format(self.worst_available_outcome.normalize(), "f"),
                self.selection_correct,
                format(self.selection_regret.normalize(), "f"),
                format(self.opportunity_regret.normalize(), "f"),
                self.abstention_quality,
                self.unnecessary_trade,
                self.missed_opportunity,
                self.failure_family.value,
                _utc(self.evaluated_at),
                self.oracle_evaluation_only,
            )
        )


def _diagnose(
    *,
    decision: CiboMetaSelectionDecision,
    selected_outcome: Decimal,
    best_outcome: Decimal,
    market_reading: CiboMarketReadingAssessment,
    cost_harmed: bool,
) -> CiboFailureFamily:
    if market_reading.regime_changed_after_decision:
        return CiboFailureFamily.REGIME_CHANGE
    if not market_reading.correct:
        return (
            CiboFailureFamily.LUCKY_PROFIT
            if selected_outcome > 0
            else CiboFailureFamily.MARKET_UNDERSTANDING
        )
    if selected_outcome < best_outcome:
        return CiboFailureFamily.TRADER_SELECTION
    if selected_outcome < 0:
        return CiboFailureFamily.SELECTED_TRADER
    if cost_harmed:
        return CiboFailureFamily.EXECUTION_COST
    if decision.selected is None and best_outcome > 0:
        return CiboFailureFamily.TRADER_SELECTION
    return CiboFailureFamily.NONE


def evaluate_counterfactuals(
    decision: CiboMetaSelectionDecision,
    shadow: CiboFiveTraderShadowEvaluation,
    outcomes: tuple[TraderCounterfactualOutcome, ...],
    *,
    market_reading: CiboMarketReadingAssessment,
    evaluated_at: datetime,
) -> Result[CiboCounterfactualEvaluation, TraderTeamLabError]:
    """Reveal future outcomes only after binding them to the frozen decision."""

    try:
        decision.__post_init__()
        shadow.__post_init__()
        if decision.shadow_fingerprint != shadow.fingerprint:
            raise TraderTeamLabValidationError("decision/shadow fingerprint mismatch")
        if type(outcomes) is not tuple or len(outcomes) != 5:
            raise TraderTeamLabValidationError("five outcomes are required")
        outcome_by_code = {item.trader_identity.trader_code.value: item for item in outcomes}
        output_by_code = {item.trader_code.value: item for item in shadow.outputs}
        if set(outcome_by_code) != set(output_by_code):
            raise TraderTeamLabValidationError("outcomes do not cover shadow Traders")
        for code, outcome in outcome_by_code.items():
            output = output_by_code[code]
            if outcome.trader_identity != next(
                member.trader_identity
                for member in shadow.team.members
                if member.trader_identity.trader_code.value == code
            ):
                raise TraderTeamLabValidationError("outcome identity does not match frozen team")
            if outcome.output_fingerprint != output.output_fingerprint.value:
                raise TraderTeamLabValidationError("outcome output fingerprint mismatch")
            if outcome.abstained != (output.decision is DemoTradingDecision.ABSTAIN):
                raise TraderTeamLabValidationError(
                    "outcome abstention does not match Trader output"
                )
        ordered = tuple(outcome_by_code[code] for code in sorted(outcome_by_code))
        returns = tuple(item.cost_adjusted_return for item in ordered)
        best = max((*returns, Decimal(0)))
        worst = min((*returns, Decimal(0)))
        selected = (
            Decimal(0)
            if decision.selected is None
            else outcome_by_code[decision.selected.trader_code.value].cost_adjusted_return
        )
        raw_selected = (
            Decimal(0)
            if decision.selected is None
            else outcome_by_code[decision.selected.trader_code.value].realized_return
        )
        correct = selected == best
        regret = best - selected
        opportunity = max(Decimal(0), best) - selected
        abstention_quality = None if decision.selected is not None else best <= 0
        unnecessary = decision.selected is not None and selected <= 0
        missed = decision.selected is None and best > 0
        failure = _diagnose(
            decision=decision,
            selected_outcome=selected,
            best_outcome=best,
            market_reading=market_reading,
            cost_harmed=raw_selected > 0 >= selected,
        )
        value = object.__new__(CiboCounterfactualEvaluation)
        fields: dict[str, object] = {
            "decision": decision,
            "outcomes": ordered,
            "market_reading": market_reading,
            "selected_outcome": selected,
            "best_available_outcome": best,
            "worst_available_outcome": worst,
            "none_outcome": Decimal(0),
            "selection_correct": correct,
            "selection_regret": regret,
            "opportunity_regret": opportunity,
            "abstention_quality": abstention_quality,
            "unnecessary_trade": unnecessary,
            "missed_opportunity": missed,
            "failure_family": failure,
            "evaluated_at": evaluated_at,
            "oracle_evaluation_only": True,
            "fingerprint": "0" * 64,
        }
        for name, item in fields.items():
            object.__setattr__(value, name, item)
        object.__setattr__(value, "fingerprint", value.compute_fingerprint())
        value.__post_init__()
        return Success(value)
    except TraderTeamLabError as error:
        return Failure(error)


@dataclass(frozen=True, slots=True)
class CiboDecisionMemoryRecord:
    decision: CiboMetaSelectionDecision
    shadow: CiboFiveTraderShadowEvaluation
    outcome: CiboCounterfactualEvaluation | None = None

    def __post_init__(self) -> None:
        self.decision.__post_init__()
        self.shadow.__post_init__()
        if self.decision.shadow_fingerprint != self.shadow.fingerprint:
            raise TraderTeamLabValidationError("memory decision does not match shadow")
        if self.outcome is not None:
            self.outcome.__post_init__()
            if self.outcome.decision != self.decision:
                raise TraderTeamLabValidationError("memory outcome does not match decision")


class CiboDecisionHistoryPort(Protocol):
    def append(self, record: CiboDecisionMemoryRecord) -> Result[None, TraderTeamLabError]: ...
    def finalize(
        self, decision_id: UUID, outcome: CiboCounterfactualEvaluation
    ) -> Result[CiboDecisionMemoryRecord, TraderTeamLabError]: ...
    def records(self) -> tuple[CiboDecisionMemoryRecord, ...]: ...


class InMemoryCiboDecisionHistory:
    """Deterministic append-only fake/reference adapter for Lab and tests."""

    def __init__(self) -> None:
        self._decisions: list[CiboDecisionMemoryRecord] = []
        self._outcomes: list[tuple[UUID, CiboCounterfactualEvaluation]] = []

    def append(self, record: CiboDecisionMemoryRecord) -> Result[None, TraderTeamLabError]:
        try:
            record.__post_init__()
            if any(
                item.decision.decision_id == record.decision.decision_id for item in self._decisions
            ):
                raise TraderTeamLabValidationError("historical decision cannot be overwritten")
            if record.outcome is not None:
                raise TraderTeamLabValidationError(
                    "decision and future outcome must be appended separately"
                )
            self._decisions.append(record)
            return Success(None)
        except TraderTeamLabError as error:
            return Failure(error)

    def finalize(
        self, decision_id: UUID, outcome: CiboCounterfactualEvaluation
    ) -> Result[CiboDecisionMemoryRecord, TraderTeamLabError]:
        try:
            matches = [item for item in self._decisions if item.decision.decision_id == decision_id]
            if len(matches) != 1:
                raise TraderTeamLabValidationError("decision history entry not found exactly once")
            current = matches[0]
            if any(item[0] == decision_id for item in self._outcomes):
                raise TraderTeamLabValidationError("historical outcome cannot be overwritten")
            updated = replace(current, outcome=outcome)
            updated.__post_init__()
            self._outcomes.append((decision_id, outcome))
            return Success(updated)
        except TraderTeamLabError as error:
            return Failure(error)

    def records(self) -> tuple[CiboDecisionMemoryRecord, ...]:
        outcomes = dict(self._outcomes)
        return tuple(
            replace(item, outcome=outcomes.get(item.decision.decision_id))
            for item in self._decisions
        )


@dataclass(frozen=True, slots=True)
class CiboCharacterizationSlice:
    key: tuple[str, ...]
    sample_size: int
    selection_accuracy: Decimal
    mean_selection_regret: Decimal
    abstention_quality: Decimal
    market_classification_accuracy: Decimal
    unnecessary_trade_rate: Decimal
    missed_opportunity_rate: Decimal
    expectancy: Decimal
    profit_factor: Decimal | None
    max_drawdown_contribution: Decimal
    tail_risk: Decimal
    mean_cost_drag: Decimal
    selection_stability: Decimal
    excessive_switching_rate: Decimal
    confidence_calibration: Decimal | None
    per_trader_frequency: tuple[tuple[str, int], ...]
    per_trader_success: tuple[tuple[str, int], ...]
    sample_sufficient: bool


def characterize_cibo(
    records: tuple[CiboDecisionMemoryRecord, ...],
    *,
    min_sample_size: int,
) -> tuple[CiboCharacterizationSlice, ...]:
    """Characterize by market/regime/session/timeframe/direction/selection/uncertainty."""

    if type(min_sample_size) is not int or min_sample_size <= 0:
        raise TraderTeamLabValidationError("characterization minimum sample must be positive")
    completed = tuple(item for item in records if item.outcome is not None)
    buckets: dict[tuple[str, ...], list[CiboDecisionMemoryRecord]] = {}
    for record in completed:
        state = record.shadow.market_state
        selected = (
            "none"
            if record.decision.selected is None
            else record.decision.selected.trader_code.value
        )
        output = (
            None
            if record.decision.selected is None
            else next(
                item
                for item in record.shadow.outputs
                if item.trader_code == record.decision.selected.trader_code
            )
        )
        direction = "abstain" if output is None or output.side is None else output.side.value
        uncertainty_bucket = (
            "low"
            if record.decision.uncertainty < Decimal("0.34")
            else "medium"
            if record.decision.uncertainty < Decimal("0.67")
            else "high"
        )
        key: tuple[str, ...] = (
            state.market_code,
            state.instrument.symbol.lower(),
            state.regime_hypothesis.value,
            state.session_code,
            "+".join(state.timeframe_codes),
            selected,
            direction,
            uncertainty_bucket,
            "confidence-unsupported",
        )
        buckets.setdefault(key, []).append(record)
    result: list[CiboCharacterizationSlice] = []
    for key, values in sorted(buckets.items()):
        outcomes = [item.outcome for item in values]
        if any(item is None for item in outcomes):
            raise TraderTeamLabValidationError("characterization received incomplete outcome")
        exact = [item for item in outcomes if item is not None]
        count = len(exact)
        returns = [item.selected_outcome for item in exact]
        positives = sum((value for value in returns if value > 0), Decimal(0))
        losses = -sum((value for value in returns if value < 0), Decimal(0))
        abstentions = [
            item.abstention_quality for item in exact if item.abstention_quality is not None
        ]
        frequencies: dict[str, int] = {}
        successes: dict[str, int] = {}
        selected_codes: list[str] = []
        for item in values:
            code = (
                "none"
                if item.decision.selected is None
                else item.decision.selected.trader_code.value
            )
            frequencies[code] = frequencies.get(code, 0) + 1
            selected_codes.append(code)
            item_outcome = item.outcome
            if item_outcome is not None and item_outcome.selected_outcome > 0:
                successes[code] = successes.get(code, 0) + 1
        stable_transitions = sum(
            left == right
            for left, right in zip(
                selected_codes,
                selected_codes[1:],
                strict=False,
            )
        )
        transition_count = max(0, count - 1)
        stability = (
            Decimal(1)
            if transition_count == 0
            else Decimal(stable_transitions) / Decimal(transition_count)
        )
        cost_drags: list[Decimal] = []
        for record, evaluated in zip(values, exact, strict=True):
            if record.decision.selected is None:
                cost_drags.append(Decimal(0))
            else:
                selected_code = record.decision.selected.trader_code.value
                selected_counterfactual = next(
                    outcome
                    for outcome in evaluated.outcomes
                    if outcome.trader_identity.trader_code.value == selected_code
                )
                cost_drags.append(
                    selected_counterfactual.realized_return
                    - selected_counterfactual.cost_adjusted_return
                )
        denominator = Decimal(count)
        result.append(
            CiboCharacterizationSlice(
                key=key,
                sample_size=count,
                selection_accuracy=Decimal(sum(item.selection_correct for item in exact))
                / denominator,
                mean_selection_regret=sum((item.selection_regret for item in exact), Decimal(0))
                / denominator,
                abstention_quality=Decimal(sum(bool(item) for item in abstentions))
                / Decimal(len(abstentions))
                if abstentions
                else Decimal(0),
                market_classification_accuracy=Decimal(
                    sum(item.market_reading.correct for item in exact)
                )
                / denominator,
                unnecessary_trade_rate=Decimal(sum(item.unnecessary_trade for item in exact))
                / denominator,
                missed_opportunity_rate=Decimal(sum(item.missed_opportunity for item in exact))
                / denominator,
                expectancy=sum(returns, Decimal(0)) / denominator,
                profit_factor=None if losses == 0 else positives / losses,
                max_drawdown_contribution=min(returns, default=Decimal(0)),
                tail_risk=min(returns, default=Decimal(0)),
                mean_cost_drag=sum(cost_drags, Decimal(0)) / denominator,
                selection_stability=stability,
                excessive_switching_rate=Decimal(1) - stability,
                confidence_calibration=None,
                per_trader_frequency=tuple(sorted(frequencies.items())),
                per_trader_success=tuple(sorted(successes.items())),
                sample_sufficient=count >= min_sample_size,
            )
        )
    return tuple(result)


@dataclass(frozen=True, slots=True)
class CiboBaselineComparison:
    label: str
    sample_size: int
    cumulative_return: Decimal
    expectancy: Decimal


def compare_baselines(
    records: tuple[CiboDecisionMemoryRecord, ...],
) -> tuple[CiboBaselineComparison, ...]:
    """Compare five always-own-logic Traders, dynamic CIBO, CIBO+NONE and oracle."""

    completed = [item for item in records if item.outcome is not None]
    labels = (
        "vt-01",
        "vt-08",
        "vt-09",
        "vt-17",
        "vt-31",
        "cibo-dynamic",
        "cibo-with-none",
        "oracle",
    )
    totals = {label: Decimal(0) for label in labels}
    for record in completed:
        outcome = record.outcome
        if outcome is None:
            continue
        by_code = {
            item.trader_identity.trader_code.value: item.cost_adjusted_return
            for item in outcome.outcomes
        }
        for code in _trader_labels():
            totals[code] += by_code[code]
        dynamic_candidates = [
            alternative
            for alternative in record.decision.alternatives
            if alternative.score is not None
        ]
        dynamic_candidates.sort(
            key=lambda item: (
                -item.score if item.score is not None else Decimal(0),
                item.trader_identity.trader_code.value,
            )
        )
        dynamic_return = (
            Decimal(0)
            if not dynamic_candidates
            else by_code[dynamic_candidates[0].trader_identity.trader_code.value]
        )
        totals["cibo-dynamic"] += dynamic_return
        totals["cibo-with-none"] += outcome.selected_outcome
        totals["oracle"] += outcome.best_available_outcome
    count = len(completed)
    denominator = Decimal(count) if count else Decimal(1)
    return tuple(
        CiboBaselineComparison(
            label, count, totals[label], totals[label] / denominator if count else Decimal(0)
        )
        for label in labels
    )


def _trader_labels() -> tuple[str, ...]:
    return "vt-01", "vt-08", "vt-09", "vt-17", "vt-31"


class CiboResearchStage(StrEnum):
    REPLAY = "replay"
    TRAIN_RESEARCH = "train-research"
    WALK_FORWARD = "walk-forward"
    UNTOUCHED_OOS = "untouched-oos"
    STRESS = "stress"
    CALIBRATION = "calibration"
    ECONOMIC_EVALUATION = "economic-evaluation"


@dataclass(frozen=True, slots=True)
class CiboResearchWindow:
    stage: CiboResearchStage
    starts_at: datetime
    ends_at: datetime

    def __post_init__(self) -> None:
        if type(self.stage) is not CiboResearchStage:
            raise TraderTeamLabValidationError("research stage must be exact")
        _aware(self.starts_at, "window start")
        _aware(self.ends_at, "window end")
        if self.ends_at <= self.starts_at:
            raise TraderTeamLabValidationError("research window must be positive")


@dataclass(frozen=True, slots=True)
class CiboWalkForwardPlan:
    methodology_version: str
    policy_version: str
    frozen_at: datetime
    windows: tuple[CiboResearchWindow, ...]
    fingerprint: str

    def __post_init__(self) -> None:
        _code(self.methodology_version, "methodology version")
        _code(self.policy_version, "policy version")
        _aware(self.frozen_at, "methodology frozen_at")
        expected = tuple(CiboResearchStage)
        if (
            type(self.windows) is not tuple
            or tuple(item.stage for item in self.windows) != expected
        ):
            raise TraderTeamLabValidationError(
                "walk-forward plan requires the complete ordered stage chain"
            )
        for item in self.windows:
            item.__post_init__()
        if any(
            right.starts_at < left.ends_at
            for left, right in zip(self.windows, self.windows[1:], strict=False)
        ):
            raise TraderTeamLabValidationError("research windows must not overlap")
        if self.frozen_at > self.windows[0].starts_at:
            raise TraderTeamLabValidationError("methodology must freeze before replay")
        if self.fingerprint != self.compute_fingerprint():
            raise TraderTeamLabValidationError("walk-forward plan fingerprint mismatch")

    def compute_fingerprint(self) -> str:
        return _fingerprint(
            (
                "qore.cibo.walk-forward.v1",
                self.methodology_version,
                self.policy_version,
                _utc(self.frozen_at),
                tuple(
                    (item.stage.value, _utc(item.starts_at), _utc(item.ends_at))
                    for item in self.windows
                ),
            )
        )


def build_walk_forward_plan(
    *,
    methodology_version: str,
    policy_version: str,
    frozen_at: datetime,
    windows: tuple[CiboResearchWindow, ...],
) -> CiboWalkForwardPlan:
    value = object.__new__(CiboWalkForwardPlan)
    object.__setattr__(value, "methodology_version", methodology_version)
    object.__setattr__(value, "policy_version", policy_version)
    object.__setattr__(value, "frozen_at", frozen_at)
    object.__setattr__(value, "windows", windows)
    object.__setattr__(value, "fingerprint", "0" * 64)
    object.__setattr__(value, "fingerprint", value.compute_fingerprint())
    value.__post_init__()
    return value


@dataclass(frozen=True, slots=True)
class CiboWalkForwardResult:
    plan_fingerprint: str
    stage_counts: tuple[tuple[CiboResearchStage, int], ...]
    records: tuple[CiboDecisionMemoryRecord, ...]


def run_walk_forward(
    plan: CiboWalkForwardPlan,
    records: tuple[CiboDecisionMemoryRecord, ...],
) -> CiboWalkForwardResult:
    """Validate chronological assignment under one frozen methodology/policy."""

    plan.__post_init__()
    ordered = tuple(sorted(records, key=lambda item: item.decision.information_cutoff))
    if ordered != records:
        raise TraderTeamLabValidationError("research records must preserve chronology")
    if any(item.decision.policy.version != plan.policy_version for item in records):
        raise TraderTeamLabValidationError("policy-version laundering across holdout")
    counts: list[tuple[CiboResearchStage, int]] = []
    seen: set[UUID] = set()
    for window in plan.windows:
        matches = tuple(
            item
            for item in records
            if window.starts_at <= item.decision.information_cutoff < window.ends_at
        )
        for item in matches:
            if item.decision.decision_id in seen:
                raise TraderTeamLabValidationError("research record assigned to multiple stages")
            seen.add(item.decision.decision_id)
        counts.append((window.stage, len(matches)))
    if len(seen) != len(records):
        raise TraderTeamLabValidationError("research record lies outside frozen windows")
    return CiboWalkForwardResult(plan.fingerprint, tuple(counts), records)


__all__ = [
    "CiboBaselineComparison",
    "CiboCharacterizationSlice",
    "CiboCounterfactualEvaluation",
    "CiboDecisionHistoryPort",
    "CiboDecisionMemoryRecord",
    "CiboFailureFamily",
    "CiboMarketReadingAssessment",
    "CiboResearchStage",
    "CiboResearchWindow",
    "CiboWalkForwardPlan",
    "CiboWalkForwardResult",
    "InMemoryCiboDecisionHistory",
    "TraderCounterfactualOutcome",
    "build_walk_forward_plan",
    "characterize_cibo",
    "compare_baselines",
    "evaluate_counterfactuals",
    "run_walk_forward",
]
