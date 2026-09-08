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
    _EXECUTION_PERIOD,
    _PERIOD_SECONDS,
    FirstCohortBacktestError,
    FirstCohortBacktestTrade,
    _h4_context,
    _history,
    _load,
    _model_trade,
)
from qore.infrastructure.trader_lab.first_cohort_walk_forward import (
    _ConfiguredEvaluator,
    _fingerprint,
    _grids,
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
_METHODOLOGY_COMPONENTS: dict[str, dict[str, object]] = {
    "vt-01": {
        "ordered_components": [
            "ny-session",
            "swing-and-liquidity-sweep",
            "false-break",
            "fvg-confirmation",
            "fvg-midpoint-entry",
            "swept-level-invalidation",
            "two-r-target",
        ],
        "observable_abstentions": ["no-session", "no-sweep"],
        "resolution_limit": (
            "production evaluator intentionally coalesces swing, false-break, FVG, and "
            "geometry rejection into no-sweep"
        ),
    },
    "vt-08": {
        "ordered_components": [
            "h4-context",
            "h4-accumulation-manipulation-distribution",
            "structural-bias",
            "m5-fvg-confirmation",
            "manipulation-extreme-invalidation",
            "opposite-h4-range-target",
        ],
        "observable_abstentions": ["no-structure", "no-fvg"],
    },
    "vt-09": {
        "ordered_components": [
            "swing-construction",
            "turtle-soup-false-break",
            "reversal-entry",
            "swing-extreme-invalidation",
            "two-r-target",
        ],
        "observable_abstentions": ["insufficient-evidence", "no-false-break"],
    },
    "vt-17": {
        "ordered_components": [
            "ny-session",
            "ninety-minute-cycle",
            "cycle-range-sweep",
            "reversal-entry",
            "cycle-extreme-invalidation",
            "two-r-target",
        ],
        "observable_abstentions": ["no-session", "no-cycle", "no-sweep"],
    },
    "vt-31": {
        "ordered_components": [
            "silver-bullet-window",
            "swing-and-liquidity-sweep",
            "false-break",
            "fvg-confirmation",
            "fvg-midpoint-entry",
            "swept-level-invalidation",
            "two-r-target",
        ],
        "observable_abstentions": ["window-closed", "no-sweep"],
        "resolution_limit": (
            "production evaluator intentionally coalesces swing, false-break, FVG, and "
            "geometry rejection into no-sweep"
        ),
    },
}


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


def _strict_bool(value: object, *, field_name: str) -> bool:
    if type(value) is not bool:
        raise FirstCohortCharacterizationError(f"{field_name} must be bool")
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
    mfe: list[Decimal] = field(default_factory=list)
    mae: list[Decimal] = field(default_factory=list)
    exits: Counter[str] = field(default_factory=Counter)

    def record(
        self,
        trade: FirstCohortBacktestTrade | None,
        *,
        mfe: Decimal = Decimal(0),
        mae: Decimal = Decimal(0),
    ) -> None:
        self.setup_count += 1
        if trade is not None:
            self.filled_count += 1
            self.returns.append(trade.return_rate)
            self.mfe.append(mfe)
            self.mae.append(mae)
            self.exits[trade.exit_reason] += 1

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
            "exit_reason_counts": dict(sorted(self.exits.items())),
            "close_path_mfe_fraction": _summary(self.mfe),
            "close_path_mae_fraction": _summary(self.mae),
        }


def _close_values(history: tuple[OhlcSnapshot, ...]) -> list[Decimal]:
    return [Decimal(str(item.close)) for item in history]


def _trend_regime(history: tuple[OhlcSnapshot, ...]) -> str:
    if len(history) < _TREND_LOOKBACK:
        return "insufficient-history"
    closes = _close_values(history[-_TREND_LOOKBACK:])
    path = sum(
        (
            abs(current - previous)
            for previous, current in zip(closes, closes[1:], strict=False)
        ),
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


def _evaluator_from_configuration(
    trader_code: str,
    configuration: dict[str, object],
) -> _ConfiguredEvaluator:
    parameters = _object(
        configuration.get("parameters"), field_name="configuration parameters"
    )
    if trader_code == "vt-01":
        if set(parameters) != {"sweep_strength"}:
            raise FirstCohortCharacterizationError("VT-01 parameters changed")
        return cast(
            _ConfiguredEvaluator,
            Vt01NyPrecisionCore(
                sweep_strength=_strict_int(
                    parameters.get("sweep_strength"), field_name="sweep_strength"
                )
            ),
        )
    if trader_code == "vt-08":
        if set(parameters) != {"range_length"}:
            raise FirstCohortCharacterizationError("VT-08 parameters changed")
        return cast(
            _ConfiguredEvaluator,
            Vt08Crt4hAmd(
                range_length=_strict_int(
                    parameters.get("range_length"), field_name="range_length"
                )
            ),
        )
    if trader_code == "vt-09":
        if set(parameters) != {"swing_strength"}:
            raise FirstCohortCharacterizationError("VT-09 parameters changed")
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
        if set(parameters) != {"sweep_strength"}:
            raise FirstCohortCharacterizationError("VT-31 parameters changed")
        return cast(
            _ConfiguredEvaluator,
            Vt31SilverBullet(
                sweep_strength=_strict_int(
                    parameters.get("sweep_strength"), field_name="sweep_strength"
                )
            ),
        )
    raise FirstCohortCharacterizationError("unknown first-cohort Trader code")


def _methodology_payload(evaluator: _ConfiguredEvaluator) -> dict[str, object]:
    if not isinstance(
        evaluator,
        (Vt01NyPrecisionCore, Vt08Crt4hAmd, Vt09TurtleSoup, Vt17QtScalper, Vt31SilverBullet),
    ):
        raise FirstCohortCharacterizationError("unsupported first-cohort evaluator")
    methodology_id, methodology_version, methodology_fingerprint = evaluator.methodology()
    return {
        "trader_version": evaluator.version,
        "methodology_id": methodology_id.value,
        "methodology_version": methodology_version.value,
        "methodology_fingerprint": methodology_fingerprint.value,
        "timeframe": evaluator.timeframe,
        "session": evaluator.session,
    }


def _profile_payload(
    *,
    label: str,
    evaluator: _ConfiguredEvaluator,
    trader_code: str,
    series: dict[str, tuple[OhlcSnapshot, ...]],
    selected_by_in_sample: bool,
    walk_forward_assessment: dict[str, object],
) -> dict[str, object]:
    execution = series[_EXECUTION_PERIOD[trader_code]]
    period_seconds = _PERIOD_SECONDS[_EXECUTION_PERIOD[trader_code]]
    closed_index: dict[object, int] = {
        bar.closed_at: index for index, bar in enumerate(execution)
    }
    decision_counts: Counter[str] = Counter()
    abstain_reasons: Counter[str] = Counter()
    evaluation_failure_reasons: Counter[str] = Counter()
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
    risk_normalized_mfe: list[Decimal] = []
    risk_normalized_mae: list[Decimal] = []
    mfe_before_stop: list[Decimal] = []
    mae_before_target: list[Decimal] = []
    setup_records: list[dict[str, object]] = []
    trend_buckets: dict[str, _Bucket] = {}
    volatility_buckets: dict[str, _Bucket] = {}
    hour_buckets: dict[str, _Bucket] = {}
    weekday_buckets: dict[str, _Bucket] = {}
    quartile_buckets: dict[str, _Bucket] = {}
    month_buckets: dict[str, _Bucket] = {}
    year_buckets: dict[str, _Bucket] = {}
    session_buckets: dict[str, _Bucket] = {}
    side_buckets: dict[str, _Bucket] = {}

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
            evaluation_failure_reasons[type(evaluated.error).__name__] += 1
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

        trend = _trend_regime(history)
        volatility = _volatility_regime(history)
        hour = f"{as_of.hour:02d}"
        weekday = str(as_of.weekday())
        quartile = f"q{min(4, (index * 4) // max(1, len(execution)) + 1)}"
        month = f"{as_of.month:02d}"
        year = str(as_of.year)
        session = output.session

        trade, _consumed = _model_trade(
            trader_code=trader_code,
            series=execution,
            signal_index=index,
            side=setup.side,
            entry=entry,
            stop=setup.invalidation_price,
            target=setup.take_profit_price,
        )
        favorable = Decimal(0)
        adverse = Decimal(0)
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
            risk_fraction = risk / entry
            if risk_fraction > 0:
                risk_normalized_mfe.append(favorable / risk_fraction)
                risk_normalized_mae.append(adverse / risk_fraction)
            if trade.exit_reason == "stop":
                mfe_before_stop.append(favorable)
            if trade.exit_reason == "target":
                mae_before_target.append(adverse)

        setup_records.append(
            {
                "signal_at": as_of.isoformat(),
                "side": setup.side.value,
                "entry_price": format(entry, "f"),
                "signal_close": format(Decimal(str(signal_bar.close)), "f"),
                "entry_offset_from_signal_close_fraction": format(
                    abs(entry - Decimal(str(signal_bar.close))) / entry, "f"
                ),
                "stop_distance": format(risk, "f"),
                "target_distance": format(reward, "f"),
                "risk_fraction": format(risk / entry, "f"),
                "reward_fraction": format(reward / entry, "f"),
                "reward_risk_multiple": format(reward / risk, "f"),
                "setup_reason": setup.entry_reason,
                "timeframe": output.timeframe,
                "session": session,
                "trend_regime": trend,
                "volatility_regime": volatility,
                "filled": trade is not None,
                "fill_at": None if trade is None else trade.filled_at.isoformat(),
                "exit_at": None if trade is None else trade.exited_at.isoformat(),
                "exit_reason": None if trade is None else trade.exit_reason,
                "return_rate": None if trade is None else format(trade.return_rate, "f"),
                "close_path_mfe_fraction": format(favorable, "f"),
                "close_path_mae_fraction": format(adverse, "f"),
            }
        )
        for buckets, key in (
            (trend_buckets, trend),
            (volatility_buckets, volatility),
            (hour_buckets, hour),
            (weekday_buckets, weekday),
            (quartile_buckets, quartile),
            (month_buckets, month),
            (year_buckets, year),
            (session_buckets, session),
            (side_buckets, setup.side.value),
        ):
            buckets.setdefault(key, _Bucket()).record(
                trade, mfe=favorable, mae=adverse
            )

    evaluated_count = sum(decision_counts.values())
    opportunity_count = max(0, len(execution) - 1)
    return {
        "profile": label,
        "selected_by_in_sample_only": selected_by_in_sample,
        "config_fingerprint": _fingerprint(evaluator),
        "parameters": dict(_parameters(evaluator)),
        "methodology_identity": _methodology_payload(evaluator),
        "walk_forward_assessment": walk_forward_assessment,
        "execution_period": _EXECUTION_PERIOD[trader_code],
        "execution_bar_count": len(execution),
        "decision_opportunity_count": opportunity_count,
        "evaluable_bar_count": opportunity_count - context_unavailable,
        "evaluated_bar_count": evaluated_count,
        "context_unavailable_count": context_unavailable,
        "evaluation_failure_count": evaluation_failures,
        "evaluation_failure_reason_counts": dict(
            sorted(evaluation_failure_reasons.items())
        ),
        "decision_counts": dict(sorted(decision_counts.items())),
        "abstain_reason_counts": dict(sorted(abstain_reasons.items())),
        "decision_funnel": {
            "execution_bars": len(execution),
            "decision_opportunities": opportunity_count,
            "context_unavailable": context_unavailable,
            "evaluable_bars": opportunity_count - context_unavailable,
            "evaluation_failures": evaluation_failures,
            "abstain": decision_counts.get(DemoTradingDecision.ABSTAIN.value, 0),
            "setup": setup_count,
            "filled": filled_count,
            "winner": sum(value > 0 for value in returns),
        },
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
        "execution_model_diagnostics": {
            "policy_id": "limit-3bar-fill-24bar-hold-stop-first-v1",
            "setups_exposed_to_limit_fill": setup_count,
            "unfilled_within_three_bars": setup_count - filled_count,
            "filled_within_three_bars": filled_count,
            "maximum_hold_exit_count": exit_reasons.get("time_exit", 0),
            "gap_exit_count": exit_reasons.get("gap_exit", 0),
            "stop_exit_count": exit_reasons.get("stop", 0),
            "target_exit_count": exit_reasons.get("target", 0),
            "causal_alternative_requires_versioned_experiment": True,
        },
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
            "mfe_before_stop_fraction": _summary(mfe_before_stop),
            "mae_before_target_fraction": _summary(mae_before_target),
            "risk_normalized_mfe": _summary(risk_normalized_mfe),
            "risk_normalized_mae": _summary(risk_normalized_mae),
            "measurement": "closed-bar-path; no intrabar ordering inferred",
            "same_bar_stop_target_policy": "stop-first-conservative",
        },
        "setups": setup_records,
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
        "by_calendar_month": {
            key: bucket.payload() for key, bucket in sorted(month_buckets.items())
        },
        "by_calendar_year": {
            key: bucket.payload() for key, bucket in sorted(year_buckets.items())
        },
        "by_session": {
            key: bucket.payload() for key, bucket in sorted(session_buckets.items())
        },
        "by_side": {
            key: bucket.payload() for key, bucket in sorted(side_buckets.items())
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
        if code in walk_by_code:
            raise FirstCohortCharacterizationError("duplicate walk-forward Trader")
        walk_by_code[code] = row
    if tuple(walk_by_code) != _CODES:
        raise FirstCohortCharacterizationError("walk-forward cohort identity/order changed")

    defaults = cohort_evaluators()
    if tuple(item.trader_code for item in defaults) != _CODES:
        raise FirstCohortCharacterizationError("production cohort identity/order changed")

    results: list[dict[str, object]] = []
    for trader_code, default in zip(_CODES, defaults, strict=True):
        default_evaluator = cast(_ConfiguredEvaluator, default)
        walk_row = walk_by_code[trader_code]
        assessment_values = _array(
            walk_row.get("assessments"), field_name="configuration assessments"
        )
        assessed_count = _strict_int(
            walk_row.get("assessed_configurations"),
            field_name="assessed_configurations",
        )
        if len(assessment_values) != assessed_count or not assessment_values:
            raise FirstCohortCharacterizationError(
                "configuration assessment count changed"
            )
        selected_value = walk_row.get("selected")
        selected_fingerprint = None
        if selected_value is not None:
            selected = _object(selected_value, field_name="selected configuration")
            selected_fingerprint = _text(
                selected.get("config_fingerprint"),
                field_name="selected config_fingerprint",
            )
            if not _strict_bool(
                selected.get("in_sample_pass"), field_name="selected in_sample_pass"
            ):
                raise FirstCohortCharacterizationError(
                    "selected configuration must pass in-sample"
                )

        profiles: list[dict[str, object]] = []
        seen_fingerprints: set[str] = set()
        ordered_fingerprints: list[str] = []
        default_seen = False
        for assessment_value in assessment_values:
            assessment = _object(
                assessment_value, field_name="configuration assessment"
            )
            evaluator = _evaluator_from_configuration(trader_code, assessment)
            fingerprint = _fingerprint(evaluator)
            declared_fingerprint = _text(
                assessment.get("config_fingerprint"),
                field_name="assessment config_fingerprint",
            )
            if fingerprint != declared_fingerprint:
                raise FirstCohortCharacterizationError(
                    "configuration fingerprint does not match parameters"
                )
            if fingerprint in seen_fingerprints:
                raise FirstCohortCharacterizationError(
                    "duplicate configuration assessment"
                )
            seen_fingerprints.add(fingerprint)
            ordered_fingerprints.append(fingerprint)
            is_default = fingerprint == _fingerprint(default_evaluator)
            default_seen = default_seen or is_default
            profiles.append(
                _profile_payload(
                    label=("production-default" if is_default else "parameter-grid"),
                    evaluator=evaluator,
                    trader_code=trader_code,
                    series=series,
                    selected_by_in_sample=fingerprint == selected_fingerprint,
                    walk_forward_assessment=assessment,
                )
            )
        if not default_seen:
            raise FirstCohortCharacterizationError(
                "walk-forward surface omitted production default"
            )
        expected_fingerprints = tuple(
            _fingerprint(item) for item in _grids()[trader_code]
        )
        if tuple(ordered_fingerprints) != expected_fingerprints:
            raise FirstCohortCharacterizationError(
                "walk-forward surface does not match source-controlled grid"
            )
        if selected_fingerprint is not None and selected_fingerprint not in seen_fingerprints:
            raise FirstCohortCharacterizationError(
                "selected configuration is absent from assessment surface"
            )
        results.append(
            {
                "trader_code": trader_code,
                "methodology_component_map": _METHODOLOGY_COMPONENTS[trader_code],
                "profiles": profiles,
            }
        )

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
            "all_assessed_configurations_characterized": True,
            "trend_regime_policy": {
                "policy_id": "close-efficiency-20-v1",
                "lookback_closed_bars": _TREND_LOOKBACK,
                "trend_min_efficiency": "0.60",
                "range_max_efficiency": "0.30",
                "past_only": True,
            },
            "volatility_regime_policy": {
                "policy_id": "normalized-range-ratio-40-10-v1",
                "baseline_closed_bars": _VOLATILITY_BASELINE,
                "recent_closed_bars": _VOLATILITY_RECENT,
                "high_min_ratio": "1.50",
                "low_max_ratio": "0.67",
                "past_only": True,
            },
            "execution_model": {
                "policy_id": "limit-3bar-fill-24bar-hold-stop-first-v1",
                "limit_fill_horizon_bars": 3,
                "maximum_hold_bars": 24,
                "same_bar_ordering": "stop-first-conservative",
                "alternative_model_applied": False,
            },
        },
        "holdout_governance": {
            "state": "consumed_for_research",
            "analysis_reads_oos": True,
            "post_change_reuse_as_independent_holdout_prohibited": True,
            "fresh_unseen_holdout_required_after_methodology_change": True,
            "source_symbol": symbol,
            "source_account_fingerprint": account_fingerprint,
            "source_checked_at": checked_at.isoformat(),
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
