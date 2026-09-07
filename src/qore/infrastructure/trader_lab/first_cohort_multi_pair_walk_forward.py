"""Pooled six-instrument walk-forward robustness screen for the first DEMO cohort.

One configuration per Trader is selected using only the pooled chronological 70%
in-sample partitions from six distinct cTrader DEMO instruments.  The selected
configuration is then frozen and evaluated unchanged on each instrument's untouched
30% OOS partition.  This module produces research evidence only; ``robust_pass``
is not DEMO_ELIGIBLE and grants no execution authority.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.trader_lab.first_cohort_backtest import (
    FirstCohortBacktestError,
    FirstCohortBacktestTrade,
    _backtest,
    _load,
)
from qore.infrastructure.trader_lab.first_cohort_walk_forward import (
    SegmentMetrics,
    _ConfiguredEvaluator,
    _fingerprint,
    _grids,
    _metrics,
    _parameters,
    _passes,
)

_SCHEMA = "qore.trader_lab.first_cohort_multi_pair_walk_forward.v1"
_REQUIRED_PAIR_COUNT = 6
_MIN_PAIR_OOS_PASSES = 4
_MIN_PAIR_STRESS_PASSES = 4
_STRESS_HAIRCUT = Decimal("0.0002")


@dataclass(frozen=True, slots=True)
class PairPartition:
    symbol: str
    series: dict[str, tuple[OhlcSnapshot, ...]]
    account_fingerprint: str
    checked_at: datetime
    split_at: datetime


@dataclass(frozen=True, slots=True)
class PairAssessment:
    symbol: str
    oos: SegmentMetrics
    oos_pass: bool
    stressed_oos: SegmentMetrics
    stress_pass: bool

    def payload(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "oos": self.oos.payload(),
            "oos_pass": self.oos_pass,
            "stressed_oos": self.stressed_oos.payload(),
            "stress_pass": self.stress_pass,
        }


@dataclass(frozen=True, slots=True)
class MultiPairTraderResult:
    trader_code: str
    assessed_configurations: int
    selected_parameters: tuple[tuple[str, int], ...] | None
    config_fingerprint: str | None
    pooled_in_sample: SegmentMetrics | None
    pooled_oos: SegmentMetrics | None
    pooled_stressed_oos: SegmentMetrics | None
    pair_assessments: tuple[PairAssessment, ...]
    robust_pass: bool

    def payload(self) -> dict[str, object]:
        return {
            "trader_code": self.trader_code,
            "assessed_configurations": self.assessed_configurations,
            "selected_parameters": (
                dict(self.selected_parameters)
                if self.selected_parameters is not None
                else None
            ),
            "config_fingerprint": self.config_fingerprint,
            "pooled_in_sample": (
                self.pooled_in_sample.payload()
                if self.pooled_in_sample is not None
                else None
            ),
            "pooled_oos": self.pooled_oos.payload() if self.pooled_oos is not None else None,
            "pooled_stressed_oos": (
                self.pooled_stressed_oos.payload()
                if self.pooled_stressed_oos is not None
                else None
            ),
            "oos_pair_pass_count": sum(item.oos_pass for item in self.pair_assessments),
            "stress_pair_pass_count": sum(item.stress_pass for item in self.pair_assessments),
            "pair_assessments": [item.payload() for item in self.pair_assessments],
            "robust_pass": self.robust_pass,
        }


def _partition(path: Path) -> PairPartition:
    series, fingerprint, symbol, checked_at = _load(path)
    m5 = series["M5"]
    split_index = (len(m5) * 7) // 10
    if split_index <= 0 or split_index >= len(m5):
        raise FirstCohortBacktestError(
            f"market evidence for {symbol} is too small for 70/30 split"
        )
    return PairPartition(
        symbol=symbol,
        series=series,
        account_fingerprint=fingerprint,
        checked_at=checked_at,
        split_at=m5[split_index].opened_at,
    )


def _rank(metrics: SegmentMetrics, fingerprint: str) -> tuple[Decimal, Decimal, Decimal, int, str]:
    return (
        metrics.mean_return,
        metrics.win_rate,
        -metrics.population_variance,
        metrics.sample_size,
        fingerprint,
    )


def _split_trades(
    trades: tuple[FirstCohortBacktestTrade, ...],
    *,
    split_at: datetime,
) -> tuple[tuple[FirstCohortBacktestTrade, ...], tuple[FirstCohortBacktestTrade, ...]]:
    return (
        tuple(trade for trade in trades if trade.signal_at < split_at),
        tuple(trade for trade in trades if trade.signal_at >= split_at),
    )


def _select_configuration(
    trader_code: str,
    grid: tuple[_ConfiguredEvaluator, ...],
    partitions: tuple[PairPartition, ...],
) -> tuple[_ConfiguredEvaluator | None, SegmentMetrics | None]:
    qualified: list[tuple[_ConfiguredEvaluator, SegmentMetrics]] = []
    for evaluator in grid:
        pooled_train: list[FirstCohortBacktestTrade] = []
        for partition in partitions:
            result = _backtest(
                evaluator,
                trader_code=trader_code,
                series=partition.series,
            )
            train, _oos = _split_trades(result.trades, split_at=partition.split_at)
            pooled_train.extend(train)
        metrics = _metrics(tuple(pooled_train))
        if _passes(metrics):
            qualified.append((evaluator, metrics))
    if not qualified:
        return None, None
    selected, metrics = max(
        qualified,
        key=lambda item: _rank(item[1], _fingerprint(item[0])),
    )
    return selected, metrics


def _evaluate_selected(
    trader_code: str,
    evaluator: _ConfiguredEvaluator,
    partitions: tuple[PairPartition, ...],
) -> tuple[
    tuple[PairAssessment, ...],
    SegmentMetrics,
    SegmentMetrics,
]:
    pair_assessments: list[PairAssessment] = []
    pooled_oos: list[FirstCohortBacktestTrade] = []
    for partition in partitions:
        result = _backtest(
            evaluator,
            trader_code=trader_code,
            series=partition.series,
        )
        _train, oos = _split_trades(result.trades, split_at=partition.split_at)
        pooled_oos.extend(oos)
        oos_metrics = _metrics(oos)
        stressed = _metrics(oos, haircut=_STRESS_HAIRCUT)
        pair_assessments.append(
            PairAssessment(
                symbol=partition.symbol,
                oos=oos_metrics,
                oos_pass=_passes(oos_metrics),
                stressed_oos=stressed,
                stress_pass=_passes(stressed),
            )
        )
    pooled = _metrics(tuple(pooled_oos))
    pooled_stressed = _metrics(tuple(pooled_oos), haircut=_STRESS_HAIRCUT)
    return tuple(pair_assessments), pooled, pooled_stressed


def run_multi_pair_walk_forward(paths: tuple[Path, ...]) -> dict[str, object]:
    if len(paths) != _REQUIRED_PAIR_COUNT:
        raise FirstCohortBacktestError("multi-pair screen requires exactly six evidence files")
    partitions = tuple(sorted((_partition(path) for path in paths), key=lambda item: item.symbol))
    symbols = tuple(item.symbol for item in partitions)
    if len(set(symbols)) != _REQUIRED_PAIR_COUNT:
        raise FirstCohortBacktestError("multi-pair screen requires six distinct symbols")
    fingerprints = {item.account_fingerprint for item in partitions}
    if len(fingerprints) != 1:
        raise FirstCohortBacktestError("all six instruments must bind the same DEMO account")

    results: list[MultiPairTraderResult] = []
    for trader_code, grid in _grids().items():
        selected, in_sample = _select_configuration(trader_code, grid, partitions)
        if selected is None or in_sample is None:
            results.append(
                MultiPairTraderResult(
                    trader_code=trader_code,
                    assessed_configurations=len(grid),
                    selected_parameters=None,
                    config_fingerprint=None,
                    pooled_in_sample=None,
                    pooled_oos=None,
                    pooled_stressed_oos=None,
                    pair_assessments=(),
                    robust_pass=False,
                )
            )
            continue
        assessments, pooled_oos, pooled_stressed = _evaluate_selected(
            trader_code,
            selected,
            partitions,
        )
        robust_pass = (
            _passes(pooled_oos)
            and _passes(pooled_stressed)
            and sum(item.oos_pass for item in assessments) >= _MIN_PAIR_OOS_PASSES
            and sum(item.stress_pass for item in assessments) >= _MIN_PAIR_STRESS_PASSES
        )
        results.append(
            MultiPairTraderResult(
                trader_code=trader_code,
                assessed_configurations=len(grid),
                selected_parameters=_parameters(selected),
                config_fingerprint=_fingerprint(selected),
                pooled_in_sample=in_sample,
                pooled_oos=pooled_oos,
                pooled_stressed_oos=pooled_stressed,
                pair_assessments=assessments,
                robust_pass=robust_pass,
            )
        )

    return {
        "schema": _SCHEMA,
        "environment": "demo",
        "read_only": True,
        "pair_count": _REQUIRED_PAIR_COUNT,
        "symbols": list(symbols),
        "account_fingerprint": next(iter(fingerprints)),
        "policy": {
            "selection_scope": "pooled-six-instrument-in-sample-only",
            "in_sample_fraction": "0.70",
            "oos_fraction": "0.30",
            "minimum_pair_oos_passes": _MIN_PAIR_OOS_PASSES,
            "minimum_pair_stress_passes": _MIN_PAIR_STRESS_PASSES,
            "stress_return_haircut": format(_STRESS_HAIRCUT, "f"),
        },
        "results": [item.payload() for item in results],
        "robust_candidate_count": sum(item.robust_pass for item in results),
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != _REQUIRED_PAIR_COUNT:
        print(
            "usage: python -m qore.infrastructure.trader_lab.first_cohort_multi_pair_walk_forward "
            "PATH1 PATH2 PATH3 PATH4 PATH5 PATH6"
        )
        return 2
    try:
        payload = run_multi_pair_walk_forward(tuple(Path(item) for item in arguments))
    except FirstCohortBacktestError as error:
        print(f"first-cohort multi-pair walk-forward failed: {error}", file=sys.stderr)
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
