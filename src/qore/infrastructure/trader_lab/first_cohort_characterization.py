"""Deep, read-only behavioral characterization for the first DEMO cohort.

This module turns a long-horizon Trader Lab run into a methodology dossier. It
replays the exact production evaluator on every eligible closed execution bar
and records the complete decision funnel, abstention causes, setup geometry,
fill behavior, realized outcomes, close-path excursions, time-to-fill/exit and
past-only market-regime descriptors.

The characterization is descriptive research evidence. It never changes a
Trader, ranks a configuration, grants execution authority or treats the OOS it
reads as reusable independent evidence after a hypothesis is derived from it.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import cast

from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.trader_lab.first_cohort_backtest import (
    FirstCohortBacktestError,
    FirstCohortBacktestTrade,
    _EXECUTION_PERIOD,
    _PERIOD_SECONDS,
    _h4_context,
    _history,
    _load,
    _model_trade,
)
from qore.infrastructure.trader_lab.first_cohort_walk_forward import (
    _ConfiguredEvaluator,
    _fingerprint,
    _parameters,
)
from qore.infrastructure.traders.contracts import (
    DemoTradingDecision,
    DemoTradingSetupSide,
)
from qore.infrastructure.traders.evaluators import (
    Vt01NyPrecisionCore,
    Vt08Crt4hAmd,
    Vt09TurtleSoup,
    Vt17QtScalper,
    Vt31SilverBullet,
    cohort_evaluators,
)
from qore.infrastructure.traders.instrument_binding import (
    DemoTradingEvaluatorBoundary,
    build_instrument_bound_demo_trading_input,
    evaluate_instrument_bound_demo_trader,
)
from qore.kernel.result import Failure

_SCHEMA = "qore.trader_lab.first_cohort_characterization.v1"
_WALK_SCHEMA = "qore.trader_lab.first_cohort_walk_forward.v2"
_CODES = ("vt-01", "vt-08", "vt-09", "vt-17", "vt-31")
_TREND_LOOKBACK = 20
_VOLATILITY_RECENT = 10
_VOLATILITY_BASELINE = 40


class FirstCohortCharacterizationError(FirstCohortBacktestError):
    __slots__ = ()


def _object(value: object, *, field_name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise FirstCohortCharacterizationError(f"{field_name} must be a JSON object")
    return cast(dict[str, object], value)


def _array(value: object, *, field_name: str) -> list[object]:
    if type(value) is not list:
        raise FirstCohortCharacterizationError(f"{field_name} must be a JSON array")
    return cast(list[object], value)


def _text(value: object, *, field_name: str) -> str:
    if type(value) is not str or not value:
        raise FirstCohortCharacterizationError(f"{field_name} must be a non-empty string")
    return value


def _strict_int(value: object, *, field_name: str) -> int:
    if type(value) is not int:
        raise FirstCohortCharacterizationError(f"{field_name} must be an int")
    return value


def _read_json(path: Path, *, field_name: str) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FirstCohortCharacterizationError(f"cannot read {field_name}") from error
    return _object(decoded, field_name=field_name)


def _mean(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal(0)
    return sum(values, Decimal(0)) / Decimal(len(values))


def _summary(values: list[Decimal]) -> dict[str, object]:
    if not values:
        return {
            "count": 0,
            "mean": "0",
            "minimum": "0",
            "maximum": "0",
            "population_variance": "0",
        }
    mean = _mean(values)
    variance = sum(((value - mean) ** 2 for value in values), Decimal(0)) / Decimal(
        len(values)
    )
    return {
        "count": len(values),
        "mean": format(mean, "f"),
        "minimum": format(min(values), "f"),
        "maximum": format(max(values), "f"),
        "population_variance": format(variance, "f"),
    }


def _return_metrics(values: list[Decimal]) -> dict[str, object]:
    summary = _summary(values)
    summary["win_rate"] = (
        format(Decimal(sum(value > 0 for value in values)) / Decimal(len(values)), "f")
        if values
        else "0"
    )
    return summary


def _max_losing_streak(values: list[Decimal]) -> int:
    longest = 0
    current = 0
    for value in values:
        if value <= 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


@dataclass(slots=True)
class _Bucket:
    setup_count: int = 0
    filled_count: int = 0
    returns: list[Decimal] = field(default_factory=list)

    def record(self, trade: FirstCohortBacktestTrade | None) -> None:
        self.setup_count += 1
        if trade is not None:
            self.filled_count += 1
            self.returns.append(trade.return_rate)

    def payload(self) -> dict[str, object]:
        return {
            "setup_count": self.setup_count,
            "filled_count": self.filled_count,
            "unfilled_count": self.setup_count - self.filled_count,
            "fill_rate": (
                format(Decimal(self.filled_count) / Decimal(self.setup_count), "f")
                if self.setup_count
                else "0"
            ),
            "outcomes": _return_metrics(self.returns),
        }


def _close_values(history: tuple[OhlcSnapshot, ...]) -> list[Decimal]:
    return [Decimal(str(item.close)) for item in history]


def _trend_regime(history: tuple[OhlcSnapshot, ...]) -> str:
    if len(history) < _TREND_LOOKBACK:
        return "insufficient-history"
    closes = _close_values(history[-_TREND_LOOKBACK:])
    path = sum(
        (abs(current - previous) for previous, current in zip(closes, closes[1:], strict=True)),
        Decimal(0),
    )
    if path == 0:
        return "range"
    efficiency = abs(closes[-1] - closes[0]) / path
    if efficiency >= Decimal("0.60"):
        return "trend"
    if efficiency <= Decimal("0.30"):
        return "range"
    return "mixed"


def _normalized_ranges(history: tuple[OhlcSnapshot, ...]) -> list[Decimal]:
    values: list[Decimal] = []
    for bar in history:
        close = Decimal(str(bar.close))
        if close <= 0:
            continue
        values.append((Decimal(str(bar.high)) - Decimal(str(bar.low))) / close)
    return values


def _volatility_regime(history: tuple[OhlcSnapshot, ...]) -> str:
    required = _VOLATILITY_RECENT + _VOLATILITY_BASELINE
    if len(history) < required:
        return "insufficient-history"
    ranges = _normalized_ranges(history[-required:])
    if len(ranges) < required:
        return "insufficient-history"
    baseline = _mean(ranges[:_VOLATILITY_BASELINE])
    recent = _mean(ranges[-_VOLATILITY_RECENT:])
    if baseline <= 0:
        return "normal"
    ratio = recent / baseline
    if ratio >= Decimal("1.50"):
        return "high"
    if ratio <= Decimal("0.67"):
        return "low"
    return "normal"


def _close_excursions(
    trade: FirstCohortBacktestTrade,
    execution: tuple[OhlcSnapshot, ...],
    closed_index: dict[object, int],
) -> tuple[Decimal, Decimal]:
    fill_index = closed_index.get(trade.filled_at)
    exit_index = closed_index.get(trade.exited_at)
    if fill_index is None or exit_index is None or exit_index < fill_index:
        return Decimal(0), Decimal(0)
    closes = [Decimal(str(item.close)) for item in execution[fill_index : exit_index + 1]]
    if not closes:
        return Decimal(0), Decimal(0)
    entry = trade.entry_price
    if trade.side is DemoTradingSetupSide.LONG:
        favorable = max((value - entry for value in closes), default=Decimal(0)) / entry
        adverse = max((entry - value for value in closes), default=Decimal(0)) / entry
    else:
        favorable = max((entry - value for value in closes), default=Decimal(0)) / entry
        adverse = max((value - entry for value in closes), default=Decimal(0)) / entry
    return max(favorable, Decimal(0)), max(adverse, Decimal(0))


def _evaluator_from_selected(
    trader_code: str,
    selected: dict[str, object],
) -> _ConfiguredEvaluator:
    parameters = _object(selected.get("parameters"), field_name="selected parameters")
    if trader_code == "vt-01":
        return cast(
            _ConfiguredEvaluator,
            Vt01NyPrecisionCore(
                sweep_strength=_strict_int(
                    parameters.get("sweep_strength"), field_name="sweep_strength"
                )
            ),
        )
    if trader_code == "vt-08":
        return cast(
            _ConfiguredEvaluator,
            Vt08Crt4hAmd(
                range_length=_strict_int(
                    parameters.get("range_length"), field_name="range_length"
                )
            ),
        )
    if trader_code == "vt-09":
        return cast(
            _ConfiguredEvaluator,
            Vt09TurtleSoup(
                swing_strength=_strict_int(
                    parameters.get("swing_strength"), field_name="swing_strength"
                )
            ),
        )
    if trader_code == "vt-17":
        if parameters:
            raise FirstCohortCharacterizationError("VT-17 selected parameters must be empty")
        return cast(_ConfiguredEvaluator, Vt17QtScalper())
    if trader_code == "vt-31":
        return cast(
            _ConfiguredEvaluator,
            Vt31SilverBullet(
                sweep_strength=_strict_int(
                    parameters.get("sweep_strength"), field_name="sweep_strength"
                )
            ),
        )
    raise FirstCohortCharacterizationError("unknown first-cohort Trader code")


def _profile_payload(
    *,
    label: str,
    evaluator: _ConfiguredEvaluator,
    trader_code: str,
    series: dict[str, tuple[OhlcSnapshot, ...]],
) -> dict[str, object]:
    execution = series[_EXECUTION_PERIOD[trader_code]]
    period_seconds = _PERIOD_SECONDS[_EXECUTION_PERIOD[trader_code]]
    closed_index: dict[object, int] = {
        bar.closed_at: index for index, bar in enumerate(execution)
    }
    decision_counts: Counter[str] = Counter()
    abstain_reasons: Counter[str] = Counter()
    side_counts: Counter[str] = Counter()
    setup_reasons: Counter[str] = Counter()
    exit_reasons: Counter[str] = Counter()
    context_unavailable = 0
    evaluation_failures = 0
    setup_count = 0
    filled_count = 0
    returns: list[Decimal] = []
    risk_fractions: list[Decimal] = []
    reward_fractions: list[Decimal] = []
    reward_risk_multiples: list[Decimal] = []
    entry_offsets: list[Decimal] = []
    bars_to_fill: list[Decimal] = []
    bars_to_exit: list[Decimal] = []
    close_mfe: list[Decimal] = []
    close_mae: list[Decimal] = []
    trend_buckets: dict[str, _Bucket] = {}
    volatility_buckets: dict[str, _Bucket] = {}
    hour_buckets: dict[str, _Bucket] = {}
    weekday_buckets: dict[str, _Bucket] = {}
    quartile_buckets: dict[str, _Bucket] = {}

    for index in range(len(execution) - 1):
        signal_bar = execution[index]
        as_of = signal_bar.closed_at
        history = _history(execution, index)
        context = _h4_context(series["H4"], as_of=as_of) if trader_code == "vt-08" else ()
        if trader_code == "vt-08" and not context:
            context_unavailable += 1
            continue
        bound = build_instrument_bound_demo_trading_input(
            execution_evidence=history,
            context_evidence=context,
            as_of=as_of,
        )
        evaluated = evaluate_instrument_bound_demo_trader(
            cast(DemoTradingEvaluatorBoundary, evaluator), bound
        )
        if isinstance(evaluated, Failure):
            evaluation_failures += 1
            continue
        output = evaluated.value.trader_output
        decision_counts[output.decision.value] += 1
        if output.decision is DemoTradingDecision.ABSTAIN:
            if output.abstain_reason is not None:
                abstain_reasons[output.abstain_reason.value] += 1
            continue
        if output.setup is None:
            raise FirstCohortCharacterizationError("SETUP decision is missing setup geometry")
        setup = output.setup
        setup_count += 1
        side_counts[setup.side.value] += 1
        setup_reasons[setup.entry_reason] += 1
        entry = setup.entry_price
        risk = abs(entry - setup.invalidation_price)
        reward = abs(setup.take_profit_price - entry)
        risk_fractions.append(risk / entry)
        reward_fractions.append(reward / entry)
        if risk > 0:
            reward_risk_multiples.append(reward / risk)
        entry_offsets.append(abs(entry - Decimal(str(signal_bar.close))) / entry)

        trade, _consumed = _model_trade(
            trader_code=trader_code,
            series=execution,
            signal_index=index,
            side=setup.side,
            entry=entry,
            stop=setup.invalidation_price,
            target=setup.take_profit_price,
        )
        if trade is not None:
            filled_count += 1
            returns.append(trade.return_rate)
            exit_reasons[trade.exit_reason] += 1
            bars_to_fill.append(
                Decimal(str((trade.filled_at - as_of).total_seconds() / period_seconds))
            )
            bars_to_exit.append(
                Decimal(
                    str(
                        (trade.exited_at - trade.filled_at).total_seconds()
                        / period_seconds
                    )
                )
            )
            favorable, adverse = _close_excursions(trade, execution, closed_index)
            close_mfe.append(favorable)
            close_mae.append(adverse)

        trend = _trend_regime(history)
        volatility = _volatility_regime(history)
        hour = f"{as_of.hour:02d}"
        weekday = str(as_of.weekday())
        quartile = f"q{min(4, (index * 4) // max(1, len(execution)) + 1)}"
        for buckets, key in (
            (trend_buckets, trend),
            (volatility_buckets, volatility),
            (hour_buckets, hour),
            (weekday_buckets, weekday),
            (quartile_buckets, quartile),
        ):
            buckets.setdefault(key, _Bucket()).record(trade)

    evaluated_count = sum(decision_counts.values())
    return {
        "profile": label,
        "config_fingerprint": _fingerprint(evaluator),
        "parameters": dict(_parameters(evaluator)),
        "execution_period": _EXECUTION_PERIOD[trader_code],
        "execution_bar_count": len(execution),
        "evaluated_bar_count": evaluated_count,
        "context_unavailable_count": context_unavailable,
        "evaluation_failure_count": evaluation_failures,
        "decision_counts": dict(sorted(decision_counts.items())),
        "abstain_reason_counts": dict(sorted(abstain_reasons.items())),
        "setup_count": setup_count,
        "filled_setup_count": filled_count,
        "unfilled_setup_count": setup_count - filled_count,
        "fill_rate": (
            format(Decimal(filled_count) / Decimal(setup_count), "f")
            if setup_count
            else "0"
        ),
        "side_counts": dict(sorted(side_counts.items())),
        "setup_reason_counts": dict(sorted(setup_reasons.items())),
        "exit_reason_counts": dict(sorted(exit_reasons.items())),
        "outcomes": _return_metrics(returns),
        "max_losing_streak": _max_losing_streak(returns),
        "geometry": {
            "risk_fraction": _summary(risk_fractions),
            "reward_fraction": _summary(reward_fractions),
            "reward_risk_multiple": _summary(reward_risk_multiples),
            "entry_offset_from_signal_close_fraction": _summary(entry_offsets),
        },
        "timing": {
            "bars_to_fill": _summary(bars_to_fill),
            "bars_from_fill_to_exit": _summary(bars_to_exit),
        },
        "close_path_excursions": {
            "max_favorable_excursion_fraction": _summary(close_mfe),
            "max_adverse_excursion_fraction": _summary(close_mae),
            "measurement": "closed-bar-path; no intrabar ordering inferred",
        },
        "by_trend_regime": {
            key: bucket.payload() for key, bucket in sorted(trend_buckets.items())
        },
        "by_volatility_regime": {
            key: bucket.payload() for key, bucket in sorted(volatility_buckets.items())
        },
        "by_signal_hour_utc": {
            key: bucket.payload() for key, bucket in sorted(hour_buckets.items())
        },
        "by_signal_weekday_utc": {
            key: bucket.payload() for key, bucket in sorted(weekday_buckets.items())
        },
        "by_chronological_quartile": {
            key: bucket.payload() for key, bucket in sorted(quartile_buckets.items())
        },
    }


def run_characterization(market_path: Path, walk_forward_path: Path) -> dict[str, object]:
    """Build a deep methodology dossier from exact long-horizon research evidence."""
    series, account_fingerprint, symbol, checked_at = _load(market_path)
    walk = _read_json(walk_forward_path, field_name="walk-forward evidence")
    if _text(walk.get("schema"), field_name="walk-forward schema") != _WALK_SCHEMA:
        raise FirstCohortCharacterizationError("characterization requires walk-forward v2")
    if _text(walk.get("environment"), field_name="walk-forward environment") != "demo":
        raise FirstCohortCharacterizationError("walk-forward evidence must be DEMO")
    if _text(walk.get("symbol"), field_name="walk-forward symbol") != symbol:
        raise FirstCohortCharacterizationError("market and walk-forward symbols differ")
    if (
        _text(walk.get("account_fingerprint"), field_name="walk-forward fingerprint")
        != account_fingerprint
    ):
        raise FirstCohortCharacterizationError("market and walk-forward accounts differ")

    walk_rows = _array(walk.get("results"), field_name="walk-forward results")
    walk_by_code: dict[str, dict[str, object]] = {}
    for item in walk_rows:
        row = _object(item, field_name="walk-forward result")
        code = _text(row.get("trader_code"), field_name="trader_code")
        walk_by_code[code] = row
    if tuple(walk_by_code) != _CODES:
        raise FirstCohortCharacterizationError("walk-forward cohort identity/order changed")

    defaults = cohort_evaluators()
    if tuple(item.trader_code for item in defaults) != _CODES:
        raise FirstCohortCharacterizationError("production cohort identity/order changed")

    results: list[dict[str, object]] = []
    for trader_code, default in zip(_CODES, defaults, strict=True):
        default_evaluator = cast(_ConfiguredEvaluator, default)
        profiles = [
            _profile_payload(
                label="production-default",
                evaluator=default_evaluator,
                trader_code=trader_code,
                series=series,
            )
        ]
        selected_value = walk_by_code[trader_code].get("selected")
        if selected_value is not None:
            selected = _object(selected_value, field_name="selected configuration")
            selected_evaluator = _evaluator_from_selected(trader_code, selected)
            if _fingerprint(selected_evaluator) != _fingerprint(default_evaluator):
                profiles.append(
                    _profile_payload(
                        label="walk-forward-selected",
                        evaluator=selected_evaluator,
                        trader_code=trader_code,
                        series=series,
                    )
                )
        results.append({"trader_code": trader_code, "profiles": profiles})

    return {
        "schema": _SCHEMA,
        "environment": "demo",
        "read_only": True,
        "symbol": symbol,
        "account_fingerprint": account_fingerprint,
        "checked_at": checked_at.isoformat(),
        "methodology": {
            "decision_funnel": True,
            "abstention_causes": True,
            "setup_geometry": True,
            "independent_setup_fill_outcomes": True,
            "close_path_excursions": True,
            "past_only_regime_descriptors": True,
            "parameter_surface_source": "walk-forward-v2",
        },
        "holdout_governance": {
            "analysis_reads_oos": True,
            "post_change_reuse_as_independent_holdout_prohibited": True,
            "fresh_unseen_holdout_required_after_methodology_change": True,
        },
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 2:
        print(
            "usage: python -m qore.infrastructure.trader_lab.first_cohort_characterization "
            "MARKET_EVIDENCE WALK_FORWARD",
            file=sys.stderr,
        )
        return 2
    try:
        payload = run_characterization(Path(arguments[0]), Path(arguments[1]))
    except FirstCohortBacktestError as error:
        print(f"first-cohort characterization failed: {error}", file=sys.stderr)
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
