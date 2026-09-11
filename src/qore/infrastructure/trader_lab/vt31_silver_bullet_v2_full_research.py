"""Full Trader Lab research evidence adapter for source-bound VT-31 V2.

This module connects the NAS100-only Silver Bullet V2 reconstruction to the
research evidence families already used by QORE Trader Lab without mutating V1
or manufacturing promotion authority.

The methodology is frozen: there is no parameter search.  A chronological
70/30 split is retained so the last 30% is evaluated as OOS research evidence,
but that OOS is explicitly marked consumed after this run and cannot certify a
modified strategy.  Stress and Monte Carlo outputs are descriptive research
screens only.  They do not satisfy governed STRESS/MONTE_CARLO lifecycle gates
or grant DEMO/LIVE/Risk/execution authority.

Monte Carlo deliberately reuses QORE's canonical deterministic circular-block
bootstrap primitives from ``research_block_bootstrap`` and QORE's nearest-rank
quantile rule from ``research_resampling_envelope``.  No alternate RNG or
post-hoc resampling engine is introduced here.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from qore.infrastructure.research_block_bootstrap import (
    ResearchBlockBootstrapPolicy,
    _draw_start,
    _mean,
)
from qore.infrastructure.research_resampling_envelope import (
    ResearchResamplingEnvelopePolicy,
    _nearest_rank,
)
from qore.infrastructure.trader_lab.vt31_silver_bullet_v2_backtest import (
    Vt31SilverBulletV2BacktestError,
)

_SCHEMA = "qore.trader_lab.vt31_silver_bullet_v2_full_research.v1"
_BACKTEST_SCHEMA = "qore.trader_lab.vt31_silver_bullet_v2_backtest.v1"
_EVIDENCE_SCHEMA = "qore.ctrader_demo.vt31_silver_bullet_v2_m1_evidence.v1"
_SYMBOL = "NAS100"
_METHODOLOGY = "silver-bullet-am-nq-v2"
_MIN_TERMINAL_SAMPLE = 20
_STRESS_HAIRCUTS_R = (Decimal("0.05"), Decimal("0.10"))
_BOOTSTRAP_POLICY = ResearchBlockBootstrapPolicy(
    block_length=3,
    resample_count=5000,
    seed=310_2026,
)
_ENVELOPE_POLICY = ResearchResamplingEnvelopePolicy(
    lower_quantile_bps=500,
    upper_quantile_bps=9500,
)
_NY = ZoneInfo("America/New_York")


class Vt31SilverBulletV2FullResearchError(Vt31SilverBulletV2BacktestError):
    """Full VT-31 V2 Trader Lab research packaging failed closed."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class _Bar:
    opened_at: datetime
    closed_at: datetime
    high: Decimal
    low: Decimal


@dataclass(frozen=True, slots=True)
class _Trade:
    signal_at: datetime
    filled_at: datetime
    resolved_at: datetime | None
    side: str
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    outcome: str
    r_multiple: Decimal | None


@dataclass(frozen=True, slots=True)
class _Metrics:
    sample_size: int
    expectancy_r: Decimal
    win_rate: Decimal
    population_variance_r: Decimal
    max_drawdown_r: Decimal
    target_count: int
    stop_count: int

    def payload(self) -> dict[str, object]:
        return {
            "sample_size": self.sample_size,
            "expectancy_r": format(self.expectancy_r, "f"),
            "win_rate": format(self.win_rate, "f"),
            "population_variance_r": format(self.population_variance_r, "f"),
            "max_drawdown_r": format(self.max_drawdown_r, "f"),
            "target_count": self.target_count,
            "stop_count": self.stop_count,
        }


def _object(value: object, *, field_name: str) -> dict[str, object]:
    if type(value) is not dict or any(type(key) is not str for key in value):
        raise Vt31SilverBulletV2FullResearchError(f"{field_name} must be an object")
    return cast(dict[str, object], value)


def _array(value: object, *, field_name: str) -> list[object]:
    if type(value) is not list:
        raise Vt31SilverBulletV2FullResearchError(f"{field_name} must be an array")
    return cast(list[object], value)


def _text(value: object, *, field_name: str) -> str:
    if type(value) is not str or not value:
        raise Vt31SilverBulletV2FullResearchError(
            f"{field_name} must be a non-empty string"
        )
    return value


def _strict_int(value: object, *, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise Vt31SilverBulletV2FullResearchError(
            f"{field_name} must be a non-negative int"
        )
    return value


def _strict_bool(value: object, *, field_name: str) -> bool:
    if type(value) is not bool:
        raise Vt31SilverBulletV2FullResearchError(f"{field_name} must be bool")
    return value


def _timestamp(value: object, *, field_name: str) -> datetime:
    raw = _text(value, field_name=field_name)
    try:
        result = datetime.fromisoformat(raw)
    except ValueError as error:
        raise Vt31SilverBulletV2FullResearchError(
            f"{field_name} must be RFC3339"
        ) from error
    if result.tzinfo is None or result.utcoffset() is None:
        raise Vt31SilverBulletV2FullResearchError(
            f"{field_name} must be timezone-aware"
        )
    return result.astimezone(UTC)


def _decimal(value: object, *, field_name: str) -> Decimal:
    if type(value) is not str or not value:
        raise Vt31SilverBulletV2FullResearchError(
            f"{field_name} must be decimal text"
        )
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        raise Vt31SilverBulletV2FullResearchError(
            f"{field_name} must be decimal text"
        ) from error
    if not result.is_finite():
        raise Vt31SilverBulletV2FullResearchError(f"{field_name} must be finite")
    return result


def _optional_decimal(value: object, *, field_name: str) -> Decimal | None:
    if value is None:
        return None
    return _decimal(value, field_name=field_name)


def _max_drawdown(values: tuple[Decimal, ...]) -> Decimal:
    equity = Decimal(0)
    peak = Decimal(0)
    maximum = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        maximum = max(maximum, peak - equity)
    return maximum


def _metrics(trades: tuple[_Trade, ...], *, haircut: Decimal = Decimal(0)) -> _Metrics:
    terminal = tuple(item for item in trades if item.r_multiple is not None)
    values = tuple(cast(Decimal, item.r_multiple) - haircut for item in terminal)
    if not values:
        return _Metrics(0, Decimal(0), Decimal(0), Decimal(0), Decimal(0), 0, 0)
    size = Decimal(len(values))
    expectancy = sum(values, Decimal(0)) / size
    variance = sum(((value - expectancy) ** 2 for value in values), Decimal(0)) / size
    targets = sum(item.outcome == "target" for item in terminal)
    stops = sum(item.outcome == "stop" for item in terminal)
    return _Metrics(
        sample_size=len(values),
        expectancy_r=expectancy,
        win_rate=Decimal(targets) / size,
        population_variance_r=variance,
        max_drawdown_r=_max_drawdown(values),
        target_count=targets,
        stop_count=stops,
    )


def _screen_pass(metrics: _Metrics) -> bool:
    """Frozen R-unit research screen for source-bound asymmetric payoff methods."""

    return metrics.sample_size >= _MIN_TERMINAL_SAMPLE and metrics.expectancy_r >= 0


def _load_json(path: Path, *, field_name: str) -> dict[str, object]:
    try:
        decoded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise Vt31SilverBulletV2FullResearchError(
            f"cannot read {field_name}"
        ) from error
    return _object(decoded, field_name=field_name)


def _bars(market: dict[str, object]) -> tuple[_Bar, ...]:
    periods = _object(market.get("periods"), field_name="market periods")
    if set(periods) != {"M1"}:
        raise Vt31SilverBulletV2FullResearchError(
            "VT-31 V2 full research requires M1-only evidence"
        )
    rows = _array(periods.get("M1"), field_name="market M1")
    result: list[_Bar] = []
    for index, raw in enumerate(rows):
        row = _object(raw, field_name=f"M1[{index}]")
        result.append(
            _Bar(
                opened_at=_timestamp(row.get("opened_at"), field_name="bar opened_at"),
                closed_at=_timestamp(row.get("closed_at"), field_name="bar closed_at"),
                high=_decimal(row.get("high"), field_name="bar high"),
                low=_decimal(row.get("low"), field_name="bar low"),
            )
        )
    if len(result) < 2:
        raise Vt31SilverBulletV2FullResearchError("M1 evidence is too small")
    ordered = tuple(sorted(result, key=lambda item: item.opened_at))
    if tuple(result) != ordered:
        raise Vt31SilverBulletV2FullResearchError("M1 evidence must be chronological")
    return ordered


def _trades(backtest: dict[str, object]) -> tuple[_Trade, ...]:
    rows = _array(backtest.get("trades"), field_name="backtest trades")
    result: list[_Trade] = []
    for index, raw in enumerate(rows):
        row = _object(raw, field_name=f"trade[{index}]")
        side = _text(row.get("side"), field_name="trade side")
        if side not in {"long", "short"}:
            raise Vt31SilverBulletV2FullResearchError(
                "trade side must be canonical long/short"
            )
        outcome = _text(row.get("outcome"), field_name="trade outcome")
        if outcome not in {"target", "stop", "gap_censored", "data_end_censored"}:
            raise Vt31SilverBulletV2FullResearchError("unsupported trade outcome")
        result.append(
            _Trade(
                signal_at=_timestamp(row.get("signal_at"), field_name="signal_at"),
                filled_at=_timestamp(row.get("filled_at"), field_name="filled_at"),
                resolved_at=(
                    _timestamp(row.get("resolved_at"), field_name="resolved_at")
                    if row.get("resolved_at") is not None
                    else None
                ),
                side=side,
                entry_price=_decimal(row.get("entry_price"), field_name="entry_price"),
                stop_loss=_decimal(row.get("stop_loss"), field_name="stop_loss"),
                take_profit=_decimal(row.get("take_profit"), field_name="take_profit"),
                outcome=outcome,
                r_multiple=_optional_decimal(row.get("r_multiple"), field_name="r_multiple"),
            )
        )
    return tuple(sorted(result, key=lambda item: (item.signal_at, item.filled_at)))


def _validate_contracts(
    market: dict[str, object],
    backtest: dict[str, object],
) -> tuple[str, tuple[_Bar, ...], tuple[_Trade, ...]]:
    if _text(market.get("schema"), field_name="market schema") != _EVIDENCE_SCHEMA:
        raise Vt31SilverBulletV2FullResearchError("unexpected market evidence schema")
    if _text(backtest.get("schema"), field_name="backtest schema") != _BACKTEST_SCHEMA:
        raise Vt31SilverBulletV2FullResearchError("unexpected backtest schema")
    for payload, name in ((market, "market"), (backtest, "backtest")):
        if _text(payload.get("environment"), field_name=f"{name} environment") != "demo":
            raise Vt31SilverBulletV2FullResearchError("research evidence must be DEMO")
        if not _strict_bool(payload.get("read_only"), field_name=f"{name} read_only"):
            raise Vt31SilverBulletV2FullResearchError("research evidence must be read-only")
    if _strict_bool(market.get("account_is_live"), field_name="account_is_live"):
        raise Vt31SilverBulletV2FullResearchError("LIVE evidence is prohibited")
    if _strict_int(
        market.get("required_coverage_days"), field_name="required_coverage_days"
    ) < 730:
        raise Vt31SilverBulletV2FullResearchError("at least 730 required days are mandatory")
    source_market = _text(
        market.get("source_authorized_market"), field_name="source_authorized_market"
    )
    if source_market != _SYMBOL:
        raise Vt31SilverBulletV2FullResearchError("source contract requires NAS100")
    symbol = _object(market.get("symbol"), field_name="market symbol")
    if _text(symbol.get("symbol_name"), field_name="symbol_name") != _SYMBOL:
        raise Vt31SilverBulletV2FullResearchError("canonical market must be NAS100")
    if _text(backtest.get("symbol"), field_name="backtest symbol") != _SYMBOL:
        raise Vt31SilverBulletV2FullResearchError("backtest must be NAS100")
    if _text(backtest.get("methodology"), field_name="methodology") != _METHODOLOGY:
        raise Vt31SilverBulletV2FullResearchError("unexpected VT-31 V2 methodology")
    market_sha = _text(market.get("software_sha"), field_name="market software_sha")
    backtest_sha = _text(backtest.get("software_sha"), field_name="backtest software_sha")
    if market_sha != backtest_sha or re.fullmatch(r"[0-9a-f]{40}", market_sha) is None:
        raise Vt31SilverBulletV2FullResearchError(
            "market/backtest software SHA must match exactly"
        )
    trades = _trades(backtest)
    if len(trades) != _strict_int(backtest.get("filled_count"), field_name="filled_count"):
        raise Vt31SilverBulletV2FullResearchError("filled_count must reconcile to trades")
    return market_sha, _bars(market), trades


def _bootstrap(values: tuple[Decimal, ...]) -> dict[str, object]:
    if len(values) < _BOOTSTRAP_POLICY.block_length:
        return {
            "status": "insufficient_sample",
            "sample_size": len(values),
            "policy": {
                "algorithm": "qore-circular-block-bootstrap-v1",
                "block_length": _BOOTSTRAP_POLICY.block_length,
                "simulation_count": _BOOTSTRAP_POLICY.resample_count,
                "seed": _BOOTSTRAP_POLICY.seed,
                "lower_quantile_bps": _ENVELOPE_POLICY.lower_quantile_bps,
                "upper_quantile_bps": _ENVELOPE_POLICY.upper_quantile_bps,
            },
        }
    sample_size = len(values)
    blocks_per_replicate = (
        sample_size + _BOOTSTRAP_POLICY.block_length - 1
    ) // _BOOTSTRAP_POLICY.block_length
    means: list[Decimal] = []
    for replicate in range(_BOOTSTRAP_POLICY.resample_count):
        resampled: list[Decimal] = []
        for draw in range(blocks_per_replicate):
            start = _draw_start(
                seed=_BOOTSTRAP_POLICY.seed,
                replicate=replicate,
                draw=draw,
                sample_size=sample_size,
            )
            for offset in range(_BOOTSTRAP_POLICY.block_length):
                resampled.append(values[(start + offset) % sample_size])
                if len(resampled) == sample_size:
                    break
            if len(resampled) == sample_size:
                break
        means.append(_mean(tuple(resampled)))
    ordered = tuple(sorted(means))
    lower = _nearest_rank(ordered, _ENVELOPE_POLICY.lower_quantile_bps)
    median = _nearest_rank(ordered, 5000)
    upper = _nearest_rank(ordered, _ENVELOPE_POLICY.upper_quantile_bps)
    source_mean = _mean(values)
    status = (
        "qualified"
        if sample_size >= _MIN_TERMINAL_SAMPLE and lower >= 0
        else "threshold_violation"
    )
    return {
        "status": status,
        "sample_size": sample_size,
        "source_mean_r": format(source_mean, "f"),
        "lower_mean_r": format(lower, "f"),
        "median_mean_r": format(median, "f"),
        "upper_mean_r": format(upper, "f"),
        "contains_zero": lower <= 0 <= upper,
        "policy": {
            "algorithm": "qore-circular-block-bootstrap-v1",
            "block_length": _BOOTSTRAP_POLICY.block_length,
            "simulation_count": _BOOTSTRAP_POLICY.resample_count,
            "seed": _BOOTSTRAP_POLICY.seed,
            "lower_quantile_bps": _ENVELOPE_POLICY.lower_quantile_bps,
            "upper_quantile_bps": _ENVELOPE_POLICY.upper_quantile_bps,
            "qualification_rule": (
                f"sample_size>={_MIN_TERMINAL_SAMPLE} and lower_mean_r>=0"
            ),
        },
    }


def _path_payload(trade: _Trade, bars: tuple[_Bar, ...]) -> dict[str, object]:
    risk = abs(trade.entry_price - trade.stop_loss)
    if risk <= 0:
        raise Vt31SilverBulletV2FullResearchError("trade risk distance must be positive")
    end = trade.resolved_at or bars[-1].closed_at
    path = tuple(
        bar for bar in bars if trade.filled_at <= bar.closed_at <= end
    )
    if path:
        highest = max(item.high for item in path)
        lowest = min(item.low for item in path)
        if trade.side == "long":
            mfe = (highest - trade.entry_price) / risk
            mae = (trade.entry_price - lowest) / risk
        else:
            mfe = (trade.entry_price - lowest) / risk
            mae = (highest - trade.entry_price) / risk
    else:
        mfe = Decimal(0)
        mae = Decimal(0)
    reward_to_risk = abs(trade.take_profit - trade.entry_price) / risk
    signal_ny = trade.signal_at.astimezone(_NY)
    return {
        "signal_at": trade.signal_at.isoformat(timespec="microseconds"),
        "filled_at": trade.filled_at.isoformat(timespec="microseconds"),
        "resolved_at": (
            trade.resolved_at.isoformat(timespec="microseconds")
            if trade.resolved_at is not None
            else None
        ),
        "side": trade.side,
        "outcome": trade.outcome,
        "r_multiple": format(trade.r_multiple, "f") if trade.r_multiple is not None else None,
        "entry_price": format(trade.entry_price, "f"),
        "stop_loss": format(trade.stop_loss, "f"),
        "take_profit": format(trade.take_profit, "f"),
        "reward_to_risk": format(reward_to_risk, "f"),
        "bars_signal_to_fill": int((trade.filled_at - trade.signal_at).total_seconds() // 60),
        "bars_fill_to_resolution": (
            int((trade.resolved_at - trade.filled_at).total_seconds() // 60)
            if trade.resolved_at is not None
            else None
        ),
        "mfe_r": format(mfe, "f"),
        "mae_r": format(mae, "f"),
        "new_york_date": signal_ny.date().isoformat(),
        "new_york_minute": signal_ny.strftime("%H:%M"),
        "weekday": signal_ny.strftime("%A").lower(),
    }


def _temporal_metrics(trades: tuple[_Trade, ...]) -> dict[str, object]:
    by_year: dict[str, list[_Trade]] = defaultdict(list)
    by_month: dict[str, list[_Trade]] = defaultdict(list)
    by_weekday: dict[str, list[_Trade]] = defaultdict(list)
    for trade in trades:
        local = trade.signal_at.astimezone(_NY)
        by_year[str(local.year)].append(trade)
        by_month[local.strftime("%Y-%m")].append(trade)
        by_weekday[local.strftime("%A").lower()].append(trade)

    def payload(groups: dict[str, list[_Trade]]) -> dict[str, object]:
        return {
            key: _metrics(tuple(value)).payload()
            for key, value in sorted(groups.items())
        }

    return {
        "by_year": payload(by_year),
        "by_month": payload(by_month),
        "by_weekday": payload(by_weekday),
    }


def _side_metrics(trades: tuple[_Trade, ...]) -> dict[str, object]:
    return {
        side: _metrics(tuple(item for item in trades if item.side == side)).payload()
        for side in ("long", "short")
    }


def _holdout_governance(split_at: datetime) -> dict[str, object]:
    return {
        "state": "consumed_for_research",
        "split_at": split_at.isoformat(timespec="microseconds"),
        "consumed_holdout_cannot_certify_modified_strategy": True,
        "post_change_reuse_as_independent_holdout_prohibited": True,
        "new_previously_unseen_holdout_required_after_any_hypothesis_change": True,
        "demo_eligible_authority": False,
    }


def build_vt31_silver_bullet_v2_full_research_payloads(
    market: dict[str, object],
    backtest: dict[str, object],
) -> dict[str, dict[str, object]]:
    """Build all research artifacts from exact broker evidence + canonical backtest."""

    software_sha, bars, trades = _validate_contracts(market, backtest)
    split_index = (len(bars) * 7) // 10
    if split_index <= 0 or split_index >= len(bars):
        raise Vt31SilverBulletV2FullResearchError("market evidence is too small for 70/30 split")
    split_at = bars[split_index].opened_at
    train = tuple(item for item in trades if item.signal_at < split_at)
    oos = tuple(item for item in trades if item.signal_at >= split_at)
    train_metrics = _metrics(train)
    oos_metrics = _metrics(oos)
    governance = _holdout_governance(split_at)

    walk_forward = {
        "schema": "qore.trader_lab.vt31_silver_bullet_v2_walk_forward.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": software_sha,
        "symbol": _SYMBOL,
        "trader_code": "vt-31",
        "trader_version": "v2",
        "methodology": _METHODOLOGY,
        "configuration_selection": "source_frozen_no_parameter_search",
        "split_at": split_at.isoformat(timespec="microseconds"),
        "in_sample_fraction": "0.70",
        "oos_fraction": "0.30",
        "policy": {
            "unit": "R",
            "min_terminal_sample_size": _MIN_TERMINAL_SAMPLE,
            "min_expectancy_r": "0",
            "win_rate_is_not_a_standalone_gate": True,
            "reason": "source method has asymmetric reward/risk geometry",
        },
        "in_sample": train_metrics.payload(),
        "in_sample_pass": _screen_pass(train_metrics),
        "oos": oos_metrics.payload(),
        "oos_pass": _screen_pass(oos_metrics),
        "selected_configuration": (
            "silver-bullet-am-nq-v2" if _screen_pass(train_metrics) else None
        ),
        "holdout_governance": governance,
    }

    side_all = _side_metrics(trades)
    side_oos = _side_metrics(oos)
    characterization = {
        "schema": "qore.trader_lab.vt31_silver_bullet_v2_characterization.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": software_sha,
        "symbol": _SYMBOL,
        "decision_funnel": {
            "decision_days": _strict_int(backtest.get("decision_days"), field_name="decision_days"),
            "setup_count": _strict_int(backtest.get("setup_count"), field_name="setup_count"),
            "filled_count": _strict_int(backtest.get("filled_count"), field_name="filled_count"),
            "unfilled_setup_count": _strict_int(
                backtest.get("unfilled_setup_count"), field_name="unfilled_setup_count"
            ),
            "pending_gap_count": _strict_int(
                backtest.get("pending_gap_count"), field_name="pending_gap_count"
            ),
            "terminal_sample_size": sum(item.r_multiple is not None for item in trades),
            "censored_filled_count": sum(item.r_multiple is None for item in trades),
        },
        "all_history": _metrics(trades).payload(),
        "in_sample": train_metrics.payload(),
        "oos": oos_metrics.payload(),
        "by_side_all_history": side_all,
        "by_side_oos": side_oos,
        "temporal": _temporal_metrics(trades),
        "parameter_sensitivity": {
            "status": "not_applicable",
            "reason": "source-bound V2 exposes no optimization parameter",
        },
        "holdout_governance": governance,
    }

    stress_haircuts = []
    for haircut in _STRESS_HAIRCUTS_R:
        stressed = _metrics(oos, haircut=haircut)
        stress_haircuts.append(
            {
                "haircut_r_per_terminal_trade": format(haircut, "f"),
                "metrics": stressed.payload(),
                "pass": _screen_pass(stressed),
            }
        )
    terminal_oos = tuple(item for item in oos if item.r_multiple is not None)
    midpoint = len(terminal_oos) // 2
    first_half = _metrics(terminal_oos[:midpoint])
    second_half = _metrics(terminal_oos[midpoint:])
    subwindow_pass = (
        first_half.sample_size >= max(5, _MIN_TERMINAL_SAMPLE // 2)
        and second_half.sample_size >= max(5, _MIN_TERMINAL_SAMPLE // 2)
        and first_half.expectancy_r >= 0
        and second_half.expectancy_r >= 0
    )
    stress_pass = (
        _screen_pass(oos_metrics)
        and all(bool(item["pass"]) for item in stress_haircuts)
        and subwindow_pass
    )
    stress = {
        "schema": "qore.trader_lab.vt31_silver_bullet_v2_stress.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": software_sha,
        "symbol": _SYMBOL,
        "families": {
            "normalized_r_haircut": stress_haircuts,
            "oos_start_subwindow": {
                "first_half": first_half.payload(),
                "second_half": second_half.payload(),
                "pass": subwindow_pass,
            },
            "parameter_neighborhood": {
                "status": "not_applicable",
                "reason": "no source-authorized optimization parameter exists",
            },
        },
        "stress_pass": stress_pass,
        "governed_stage_authority": False,
        "holdout_governance": governance,
    }

    oos_values = tuple(
        cast(Decimal, item.r_multiple)
        for item in terminal_oos
        if item.r_multiple is not None
    )
    monte_carlo = {
        "schema": "qore.trader_lab.vt31_silver_bullet_v2_monte_carlo.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": software_sha,
        "symbol": _SYMBOL,
        "source": "chronological_oos_terminal_R_sequence",
        **_bootstrap(oos_values),
        "governed_stage_authority": False,
        "holdout_governance": governance,
    }

    paths = [_path_payload(item, bars) for item in trades]
    story_forensics = {
        "schema": "qore.trader_lab.vt31_silver_bullet_v2_story_forensics.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": software_sha,
        "symbol": _SYMBOL,
        "methodology": _METHODOLOGY,
        "trade_story_count": len(paths),
        "stories": paths,
        "holdout_governance": governance,
    }

    long_oos = _metrics(tuple(item for item in oos if item.side == "long"))
    short_oos = _metrics(tuple(item for item in oos if item.side == "short"))
    observations: list[str] = []
    if not _screen_pass(oos_metrics):
        observations.append("oos_generalization_failure")
    if not stress_pass:
        observations.append("stress_fragility")
    if str(monte_carlo.get("status")) != "qualified":
        observations.append("monte_carlo_lower_envelope_not_positive")
    if (
        long_oos.sample_size > 0
        and short_oos.sample_size > 0
        and (long_oos.expectancy_r >= 0) != (short_oos.expectancy_r >= 0)
    ):
        observations.append("directional_asymmetry")
    setup_count = _strict_int(backtest.get("setup_count"), field_name="setup_count")
    unfilled = _strict_int(
        backtest.get("unfilled_setup_count"), field_name="unfilled_setup_count"
    )
    if setup_count and Decimal(unfilled) / Decimal(setup_count) > Decimal("0.25"):
        observations.append("elevated_unfilled_setup_rate")
    if not observations:
        observations.append("no_failure_rule_triggered_research_only")

    failure_analysis = {
        "schema": "qore.trader_lab.vt31_silver_bullet_v2_failure_analysis.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": software_sha,
        "symbol": _SYMBOL,
        "observations": observations,
        "oos": oos_metrics.payload(),
        "long_oos": long_oos.payload(),
        "short_oos": short_oos.payload(),
        "stress_pass": stress_pass,
        "monte_carlo_status": monte_carlo.get("status"),
        "causality_claimed": False,
        "holdout_governance": governance,
    }

    hypothesis_register = {
        "schema": "qore.trader_lab.vt31_silver_bullet_v2_hypothesis_register.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": software_sha,
        "symbol": _SYMBOL,
        "methodology_frozen": True,
        "observed_failure_labels": observations,
        "candidate_hypotheses": [
            {
                "id": "vt31-v2-directional-asymmetry",
                "enabled_for_modification": False,
                "triggered": "directional_asymmetry" in observations,
                "mechanism_to_investigate": (
                    "long/short setup geometry and post-raid structure behavior"
                ),
                "falsification_requirement": (
                    "pre-register any change and evaluate on a fresh unseen holdout"
                ),
            },
            {
                "id": "vt31-v2-oos-regime-dependence",
                "enabled_for_modification": False,
                "triggered": "oos_generalization_failure" in observations,
                "mechanism_to_investigate": (
                    "temporal/regime concentration of terminal R outcomes"
                ),
                "falsification_requirement": (
                    "do not reuse consumed 30% OOS as independent certification"
                ),
            },
        ],
        "holdout_governance": governance,
    }

    summary = {
        "schema": _SCHEMA,
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": software_sha,
        "symbol": _SYMBOL,
        "trader_code": "vt-31",
        "trader_version": "v2",
        "methodology": _METHODOLOGY,
        "walk_forward_in_sample_pass": walk_forward["in_sample_pass"],
        "walk_forward_oos_pass": walk_forward["oos_pass"],
        "stress_pass": stress_pass,
        "monte_carlo_status": monte_carlo.get("status"),
        "story_forensics_complete": len(paths) == len(trades),
        "failure_labels": observations,
        "demo_eligible": False,
        "promotion_blocker": "fresh unseen holdout and governed authority chain remain required",
        "holdout_governance": governance,
    }

    return {
        "walk-forward.json": walk_forward,
        "characterization.json": characterization,
        "stress.json": stress,
        "monte-carlo.json": monte_carlo,
        "failure-analysis.json": failure_analysis,
        "story-forensics.json": story_forensics,
        "hypothesis-register.json": hypothesis_register,
        "research-summary.json": summary,
    }


def run_vt31_silver_bullet_v2_full_research(
    market_path: Path,
    backtest_path: Path,
    output_directory: Path,
) -> dict[str, object]:
    market = _load_json(market_path, field_name="market evidence")
    backtest = _load_json(backtest_path, field_name="backtest evidence")
    payloads = build_vt31_silver_bullet_v2_full_research_payloads(market, backtest)
    output_directory.mkdir(parents=True, exist_ok=True)
    for filename, payload in payloads.items():
        (output_directory / filename).write_text(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )
    return payloads["research-summary.json"]


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 3:
        print(
            "usage: python -m qore.infrastructure.trader_lab."
            "vt31_silver_bullet_v2_full_research MARKET BACKTEST OUTPUT_DIR",
            file=sys.stderr,
        )
        return 2
    try:
        summary = run_vt31_silver_bullet_v2_full_research(
            Path(arguments[0]),
            Path(arguments[1]),
            Path(arguments[2]),
        )
    except Vt31SilverBulletV2FullResearchError as error:
        print(f"VT-31 V2 full research failed: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            summary,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
