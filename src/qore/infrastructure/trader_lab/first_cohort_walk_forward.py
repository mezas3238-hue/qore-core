"""Frozen walk-forward research screen for the first DEMO cohort.

The configuration grid and thresholds in this module are source-controlled
before the workflow observes its fresh cTrader DEMO evidence. Configuration
selection reads only the chronological 70% in-sample partition; the final 30%
is retained as OOS and never participates in ranking.

Every assessed configuration is retained in the evidence payload so a later
failure-analysis cycle can diagnose parameter sensitivity without re-running
or reconstructing hidden candidates. This remains research evidence only.
``oos_pass`` is not DEMO_ELIGIBLE; a passing candidate must still traverse
canonical OOS, Stress, Monte Carlo, Risk, CIBO and Independent Validation.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Protocol, cast

from qore.infrastructure.trader_lab.first_cohort_backtest import (
    FirstCohortBacktestError,
    FirstCohortBacktestResult,
    FirstCohortBacktestTrade,
    _backtest,
    _load,
)
from qore.infrastructure.traders.evaluators import (
    Vt01NyPrecisionCore,
    Vt08Crt4hAmd,
    Vt09TurtleSoup,
    Vt17QtScalper,
    Vt31SilverBullet,
)
from qore.infrastructure.traders.instrument_binding import DemoTradingEvaluatorBoundary

_SCHEMA = "qore.trader_lab.first_cohort_walk_forward.v2"
_POLICY_ID = "first-demo-economic-v1"
_MIN_SAMPLE = 4
_MIN_MEAN = Decimal("0")
_MIN_WIN_RATE = Decimal("0.50")
_MAX_VARIANCE = Decimal("0.01")
_STRESS_HAIRCUT = Decimal("0.0002")


class _ConfiguredEvaluator(DemoTradingEvaluatorBoundary, Protocol):
    @property
    def trader_code(self) -> str: ...

    def config_fingerprint(self) -> object: ...


@dataclass(frozen=True, slots=True)
class SegmentMetrics:
    sample_size: int
    mean_return: Decimal
    win_rate: Decimal
    population_variance: Decimal

    def payload(self) -> dict[str, object]:
        return {
            "sample_size": self.sample_size,
            "mean_return": format(self.mean_return, "f"),
            "win_rate": format(self.win_rate, "f"),
            "population_variance": format(self.population_variance, "f"),
        }


@dataclass(frozen=True, slots=True)
class ConfigurationAssessment:
    parameters: tuple[tuple[str, int], ...]
    config_fingerprint: str
    in_sample: SegmentMetrics
    in_sample_pass: bool
    oos: SegmentMetrics
    oos_pass: bool
    stressed_oos: SegmentMetrics
    stress_pass: bool

    def payload(self) -> dict[str, object]:
        return {
            "parameters": dict(self.parameters),
            "config_fingerprint": self.config_fingerprint,
            "in_sample": self.in_sample.payload(),
            "in_sample_pass": self.in_sample_pass,
            "oos": self.oos.payload(),
            "oos_pass": self.oos_pass,
            "stressed_oos": self.stressed_oos.payload(),
            "stress_pass": self.stress_pass,
        }


@dataclass(frozen=True, slots=True)
class TraderWalkForwardResult:
    trader_code: str
    selected: ConfigurationAssessment | None
    assessments: tuple[ConfigurationAssessment, ...]

    @property
    def assessed_configurations(self) -> int:
        return len(self.assessments)

    def payload(self) -> dict[str, object]:
        return {
            "trader_code": self.trader_code,
            "assessed_configurations": self.assessed_configurations,
            "selected": self.selected.payload() if self.selected is not None else None,
            "assessments": [item.payload() for item in self.assessments],
        }


def _metrics(
    trades: tuple[FirstCohortBacktestTrade, ...], *, haircut: Decimal = Decimal("0")
) -> SegmentMetrics:
    values = tuple(trade.return_rate - haircut for trade in trades)
    if not values:
        return SegmentMetrics(0, Decimal(0), Decimal(0), Decimal(0))
    size = Decimal(len(values))
    mean = sum(values, Decimal(0)) / size
    win_rate = Decimal(sum(value > 0 for value in values)) / size
    variance = sum(((value - mean) ** 2 for value in values), Decimal(0)) / size
    return SegmentMetrics(len(values), mean, win_rate, variance)


def _passes(metrics: SegmentMetrics) -> bool:
    return (
        metrics.sample_size >= _MIN_SAMPLE
        and metrics.mean_return >= _MIN_MEAN
        and metrics.win_rate >= _MIN_WIN_RATE
        and metrics.population_variance <= _MAX_VARIANCE
    )


def _parameters(evaluator: object) -> tuple[tuple[str, int], ...]:
    if isinstance(evaluator, Vt01NyPrecisionCore):
        return (("sweep_strength", evaluator.sweep_strength),)
    if isinstance(evaluator, Vt08Crt4hAmd):
        return (("range_length", evaluator.range_length),)
    if isinstance(evaluator, Vt09TurtleSoup):
        return (("swing_strength", evaluator.swing_strength),)
    if isinstance(evaluator, Vt17QtScalper):
        return ()
    if isinstance(evaluator, Vt31SilverBullet):
        return (("sweep_strength", evaluator.sweep_strength),)
    raise FirstCohortBacktestError("unsupported first-cohort evaluator")


def _fingerprint(evaluator: object) -> str:
    if isinstance(
        evaluator,
        (Vt01NyPrecisionCore, Vt08Crt4hAmd, Vt09TurtleSoup, Vt17QtScalper, Vt31SilverBullet),
    ):
        return evaluator.config_fingerprint().value
    raise FirstCohortBacktestError("unsupported first-cohort evaluator")


def _grids() -> dict[str, tuple[_ConfiguredEvaluator, ...]]:
    return {
        "vt-01": tuple(
            cast(_ConfiguredEvaluator, Vt01NyPrecisionCore(sweep_strength=value))
            for value in (1, 2, 3, 4)
        ),
        "vt-08": tuple(
            cast(_ConfiguredEvaluator, Vt08Crt4hAmd(range_length=value))
            for value in (2, 3, 4, 5, 6, 8)
        ),
        "vt-09": tuple(
            cast(_ConfiguredEvaluator, Vt09TurtleSoup(swing_strength=value))
            for value in (1, 2, 3, 4)
        ),
        "vt-17": (cast(_ConfiguredEvaluator, Vt17QtScalper()),),
        "vt-31": tuple(
            cast(_ConfiguredEvaluator, Vt31SilverBullet(sweep_strength=value))
            for value in (1, 2, 3, 4)
        ),
    }


def _assessment(
    result: FirstCohortBacktestResult,
    *,
    evaluator: _ConfiguredEvaluator,
    split_at: datetime,
) -> ConfigurationAssessment:
    train = tuple(trade for trade in result.trades if trade.signal_at < split_at)
    oos = tuple(trade for trade in result.trades if trade.signal_at >= split_at)
    in_sample = _metrics(train)
    oos_metrics = _metrics(oos)
    stressed = _metrics(oos, haircut=_STRESS_HAIRCUT)
    return ConfigurationAssessment(
        parameters=_parameters(evaluator),
        config_fingerprint=_fingerprint(evaluator),
        in_sample=in_sample,
        in_sample_pass=_passes(in_sample),
        oos=oos_metrics,
        oos_pass=_passes(oos_metrics),
        stressed_oos=stressed,
        stress_pass=_passes(stressed),
    )


def _rank(assessment: ConfigurationAssessment) -> tuple[Decimal, Decimal, Decimal, int, str]:
    metrics = assessment.in_sample
    return (
        metrics.mean_return,
        metrics.win_rate,
        -metrics.population_variance,
        metrics.sample_size,
        assessment.config_fingerprint,
    )


def run_walk_forward(path: Path) -> dict[str, object]:
    series, fingerprint, symbol, checked_at = _load(path)
    m5 = series["M5"]
    split_index = (len(m5) * 7) // 10
    if split_index <= 0 or split_index >= len(m5):
        raise FirstCohortBacktestError("market evidence is too small for 70/30 split")
    split_at = m5[split_index].opened_at
    results: list[TraderWalkForwardResult] = []
    for trader_code, grid in _grids().items():
        assessments: list[ConfigurationAssessment] = []
        for evaluator in grid:
            backtest = _backtest(
                cast(DemoTradingEvaluatorBoundary, evaluator),
                trader_code=trader_code,
                series=series,
            )
            assessments.append(_assessment(backtest, evaluator=evaluator, split_at=split_at))
        train_qualified = [item for item in assessments if item.in_sample_pass]
        selected = max(train_qualified, key=_rank) if train_qualified else None
        results.append(
            TraderWalkForwardResult(
                trader_code=trader_code,
                selected=selected,
                assessments=tuple(assessments),
            )
        )
    return {
        "schema": _SCHEMA,
        "environment": "demo",
        "read_only": True,
        "account_fingerprint": fingerprint,
        "symbol": symbol,
        "checked_at": checked_at.astimezone(UTC).isoformat(),
        "split_at": split_at.astimezone(UTC).isoformat(),
        "in_sample_fraction": "0.70",
        "oos_fraction": "0.30",
        "policy": {
            "policy_id": _POLICY_ID,
            "min_sample_size": _MIN_SAMPLE,
            "min_mean_return": format(_MIN_MEAN, "f"),
            "min_win_rate": format(_MIN_WIN_RATE, "f"),
            "max_population_variance": format(_MAX_VARIANCE, "f"),
            "stress_return_haircut": format(_STRESS_HAIRCUT, "f"),
        },
        "results": [item.payload() for item in results],
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 1:
        print("usage: python -m qore.infrastructure.trader_lab.first_cohort_walk_forward PATH")
        return 2
    try:
        payload = run_walk_forward(Path(arguments[0]))
    except FirstCohortBacktestError as error:
        print(f"first-cohort walk-forward failed: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
