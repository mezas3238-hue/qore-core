"""Operational evaluation of the exact five-Trader first DEMO cohort."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.trader_lab.candidate import TraderLabValidationError
from qore.infrastructure.trader_lab.cohort import (
    FIRST_DEMO_COHORT_CODES,
    FirstCohortDemoSelection,
    FirstCohortTraderLabEntry,
)
from qore.infrastructure.traders.contracts import DemoTradingError
from qore.infrastructure.traders.evaluators import (
    Vt01NyPrecisionCore,
    Vt08Crt4hAmd,
    Vt09TurtleSoup,
    Vt17QtScalper,
    Vt31SilverBullet,
)
from qore.infrastructure.traders.instrument_binding import (
    DemoTradingEvaluatorBoundary,
    InstrumentBoundDemoTradingOutput,
    build_instrument_bound_demo_trading_input,
    evaluate_instrument_bound_demo_trader,
)
from qore.kernel.result import Failure, Result, Success

_EXECUTION_SECONDS = {"vt-01": 300, "vt-08": 300, "vt-09": 900, "vt-17": 300, "vt-31": 300}
_EVALUATORS: dict[str, DemoTradingEvaluatorBoundary] = {
    "vt-01": Vt01NyPrecisionCore(),
    "vt-08": Vt08Crt4hAmd(),
    "vt-09": Vt09TurtleSoup(),
    "vt-17": Vt17QtScalper(),
    "vt-31": Vt31SilverBullet(),
}


class FirstCohortRuntimeError(DemoTradingError):
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class FirstCohortTraderEvaluation:
    entry: FirstCohortTraderLabEntry
    output: InstrumentBoundDemoTradingOutput

    def __post_init__(self) -> None:
        if not isinstance(self.entry, FirstCohortTraderLabEntry):
            raise FirstCohortRuntimeError("evaluation entry must be canonical")
        self.entry.__post_init__()
        if type(self.output) is not InstrumentBoundDemoTradingOutput:
            raise FirstCohortRuntimeError("evaluation output must be instrument-bound")
        self.output.__post_init__()
        trader = self.output.trader_output
        if (
            trader.trader_code != self.entry.trader_code
            or trader.version != self.entry.trader_version
            or trader.config_fingerprint != self.entry.config_fingerprint
            or trader.methodology_id != self.entry.methodology_id
            or trader.methodology_version != self.entry.methodology_version
            or trader.methodology_fingerprint != self.entry.methodology_fingerprint
            or self.output.instrument != self.entry.instrument
        ):
            raise FirstCohortRuntimeError("Trader output does not match governed Lab identity")


@dataclass(frozen=True, slots=True)
class FirstCohortOperationalEvaluation:
    selection: FirstCohortDemoSelection
    evaluations: tuple[FirstCohortTraderEvaluation, ...]
    selected_output: InstrumentBoundDemoTradingOutput | None
    evaluated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.selection, FirstCohortDemoSelection):
            raise FirstCohortRuntimeError("evaluation requires canonical selection")
        self.selection.__post_init__()
        if len(self.evaluations) != 5 or any(
            not isinstance(item, FirstCohortTraderEvaluation) for item in self.evaluations
        ):
            raise FirstCohortRuntimeError("evaluation requires five individual results")
        for item in self.evaluations:
            item.__post_init__()
        if (
            tuple(item.entry.trader_code.value for item in self.evaluations)
            != FIRST_DEMO_COHORT_CODES
        ):
            raise FirstCohortRuntimeError("results must be VT-01/08/09/17/31 in order")
        selected = self.selection.selected
        expected = None
        if selected is not None:
            expected = next(
                item.output
                for item in self.evaluations
                if item.entry.trader_code == selected.trader_code
            )
        if self.selected_output != expected:
            raise FirstCohortRuntimeError("selected output must be the sole Lab winner")
        if self.evaluated_at.tzinfo is None or self.evaluated_at.utcoffset() is None:
            raise FirstCohortRuntimeError("evaluated_at must be timezone-aware")
        if any(
            item.output.trader_output.evaluated_at != self.evaluated_at
            for item in self.evaluations
        ):
            raise FirstCohortRuntimeError("all results must bind one evaluation instant")


def evaluate_first_demo_cohort(
    selection: FirstCohortDemoSelection,
    *,
    snapshots: tuple[OhlcSnapshot, ...],
    evaluated_at: datetime,
) -> Result[FirstCohortOperationalEvaluation, DemoTradingError]:
    """Evaluate all five Traders from canonical closed snapshots exactly once."""
    if not isinstance(selection, FirstCohortDemoSelection):
        return Failure(FirstCohortRuntimeError("selection must be canonical"))
    try:
        selection.__post_init__()
        if not snapshots or any(type(item) is not OhlcSnapshot for item in snapshots):
            raise FirstCohortRuntimeError("snapshots must contain exact OHLC values")
        for item in snapshots:
            item.__post_init__()
        entries = {
            assessment.entry.trader_code.value: assessment.entry
            for assessment in selection.assessments
        }
        evaluations: list[FirstCohortTraderEvaluation] = []
        for code in FIRST_DEMO_COHORT_CODES:
            execution = tuple(
                item for item in snapshots if item.timeframe.seconds == _EXECUTION_SECONDS[code]
            )
            context = (
                tuple(item for item in snapshots if item.timeframe.seconds == 14_400)
                if code == "vt-08"
                else ()
            )
            bound_input = build_instrument_bound_demo_trading_input(
                execution_evidence=execution,
                context_evidence=context,
                as_of=evaluated_at,
            )
            evaluated = evaluate_instrument_bound_demo_trader(_EVALUATORS[code], bound_input)
            if isinstance(evaluated, Failure):
                return evaluated
            evaluations.append(
                FirstCohortTraderEvaluation(entry=entries[code], output=evaluated.value)
            )
        selected = selection.selected
        selected_output = None
        if selected is not None:
            selected_output = next(
                item.output
                for item in evaluations
                if item.entry.trader_code == selected.trader_code
            )
        return Success(
            FirstCohortOperationalEvaluation(
                selection=selection,
                evaluations=tuple(evaluations),
                selected_output=selected_output,
                evaluated_at=evaluated_at,
            )
        )
    except (DemoTradingError, TraderLabValidationError) as error:
        return Failure(FirstCohortRuntimeError(str(error)))
