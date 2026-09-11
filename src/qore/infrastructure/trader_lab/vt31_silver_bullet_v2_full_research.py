"""Full Trader Lab research evidence for source-bound VT-31 Silver Bullet V2.

The module packages chronological IS/OOS, characterization, stress, Monte Carlo,
failure analysis, Story Forensics, and hypothesis governance from the frozen
NAS100 source-bound implementation. It grants no DEMO/LIVE/Risk authority.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab.vt31_silver_bullet_v2_backtest import (
    Vt31SilverBulletV2BacktestError,
)

_SCHEMA = "qore.trader_lab.vt31_silver_bullet_v2_full_research.v1"
_BACKTEST_SCHEMA = "qore.trader_lab.vt31_silver_bullet_v2_backtest.v1"
_MARKET_SCHEMA = "qore.ctrader_demo.vt31_silver_bullet_v2_m1_evidence.v1"
_SYMBOL = "NAS100"
_METHODOLOGY = "silver-bullet-am-nq-v2"
_MIN_TERMINAL_SAMPLE = 20
_STRESS_HAIRCUTS_R = (Decimal("0.05"), Decimal("0.10"))
_BOOTSTRAP_BLOCK = 3
_BOOTSTRAP_COUNT = 5000
_BOOTSTRAP_SEED = 310_2026
_BOOTSTRAP_DOMAIN = b"qore-research-circular-block-bootstrap-v1"


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
    entry_model: str
    breakeven_armed_at: datetime | None


@dataclass(frozen=True, slots=True)
class _Metrics:
    sample_size: int
    expectancy_r: Decimal
    win_rate: Decimal
    population_variance_r: Decimal
    max_drawdown_r: Decimal
    target_count: int
    stop_count: int
    breakeven_count: int

    def payload(self) -> dict[str, object]:
        return {
            "sample_size": self.sample_size,
            "expectancy_r": format(self.expectancy_r, "f"),
            "win_rate": format(self.win_rate, "f"),
            "population_variance_r": format(self.population_variance_r, "f"),
            "max_drawdown_r": format(self.max_drawdown_r, "f"),
            "target_count": self.target_count,
            "stop_count": self.stop_count,
            "breakeven_count": self.breakeven_count,
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


def _optional_timestamp(value: object, *, field_name: str) -> datetime | None:
    return None if value is None else _timestamp(value, field_name=field_name)


def _decimal(value: object, *, field_name: str) -> Decimal:
    raw = _text(value, field_name=field_name)
    try:
        result = Decimal(raw)
    except InvalidOperation as error:
        raise Vt31SilverBulletV2FullResearchError(
            f"{field_name} must be decimal text"
        ) from error
    if not result.is_finite():
        raise Vt31SilverBulletV2FullResearchError(f"{field_name} must be finite")
    return result


def _optional_decimal(value: object, *, field_name: str) -> Decimal | None:
    return None if value is None else _decimal(value, field_name=field_name)


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
    ordered = tuple(sorted(result, key=lambda item: item.opened_at))
    if len(ordered) < 2 or tuple(result) != ordered:
        raise Vt31SilverBulletV2FullResearchError(
            "M1 evidence must contain chronological bars"
        )
    return ordered


def _trades(backtest: dict[str, object]) -> tuple[_Trade, ...]:
    rows = _array(backtest.get("trades"), field_name="backtest trades")
    allowed = {"target", "stop", "breakeven", "gap_censored", "data_end_censored"}
    result: list[_Trade] = []
    for index, raw in enumerate(rows):
        row = _object(raw, field_name=f"trade[{index}]")
        side = _text(row.get("side"), field_name="trade side")
        if side not in {"long", "short"}:
            raise Vt31SilverBulletV2FullResearchError(
                "trade side must be canonical long/short"
            )
        outcome = _text(row.get("outcome"), field_name="trade outcome")
        if outcome not in allowed:
            raise Vt31SilverBulletV2FullResearchError("unsupported trade outcome")
        r_multiple = _optional_decimal(row.get("r_multiple"), field_name="r_multiple")
        if outcome in {"target", "stop", "breakeven"} and r_multiple is None:
            raise Vt31SilverBulletV2FullResearchError(
                "terminal trade must retain R multiple"
            )
        if outcome == "breakeven" and r_multiple != Decimal(0):
            raise Vt31SilverBulletV2FullResearchError("breakeven must equal zero R")
        entry_model_raw = row.get("entry_model")
        entry_model = (
            entry_model_raw
            if type(entry_model_raw) is str and entry_model_raw
            else "historical-fixture-unspecified"
        )
        result.append(
            _Trade(
                signal_at=_timestamp(row.get("signal_at"), field_name="signal_at"),
                filled_at=_timestamp(row.get("filled_at"), field_name="filled_at"),
                resolved_at=_optional_timestamp(
                    row.get("resolved_at"), field_name="resolved_at"
                ),
                side=side,
                entry_price=_decimal(row.get("entry_price"), field_name="entry_price"),
                stop_loss=_decimal(row.get("stop_loss"), field_name="stop_loss"),
                take_profit=_decimal(row.get("take_profit"), field_name="take_profit"),
                outcome=outcome,
                r_multiple=r_multiple,
                entry_model=entry_model,
                breakeven_armed_at=_optional_timestamp(
                    row.get("breakeven_armed_at"), field_name="breakeven_armed_at"
                ),
            )
        )
    return tuple(sorted(result, key=lambda item: (item.signal_at, item.filled_at)))


def _validate_contracts(
    market: dict[str, object],
    backtest: dict[str, object],
) -> tuple[str, tuple[_Bar, ...], tuple[_Trade, ...]]:
    if _text(market.get("schema"), field_name="market schema") != _MARKET_SCHEMA:
        raise Vt31SilverBulletV2FullResearchError("unexpected market evidence schema")
    if _text(backtest.get("schema"), field_name="backtest schema") != _BACKTEST_SCHEMA:
        raise Vt31SilverBulletV2FullResearchError("unexpected backtest schema")
    for payload, label in ((market, "market"), (backtest, "backtest")):
        if _text(payload.get("environment"), field_name=f"{label} environment") != "demo":
            raise Vt31SilverBulletV2FullResearchError("research evidence must be DEMO")
        if not _strict_bool(payload.get("read_only"), field_name=f"{label} read_only"):
            raise Vt31SilverBulletV2FullResearchError(
                "research evidence must be read-only"
            )
    if _strict_bool(market.get("account_is_live"), field_name="account_is_live"):
        raise Vt31SilverBulletV2FullResearchError("LIVE evidence is prohibited")
    required_days = _strict_int(
        market.get("required_coverage_days"), field_name="required_coverage_days"
    )
    if required_days < 730:
        raise Vt31SilverBulletV2FullResearchError(
            "at least 730 required days are mandatory"
        )
    if _text(
        market.get("source_authorized_market"), field_name="source_authorized_market"
    ) != _SYMBOL:
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
        raise Vt31SilverBulletV2FullResearchError(
            "filled_count must reconcile to retained trades"
        )
    return market_sha, _bars(market), trades


def _terminal_values(
    trades: tuple[_Trade, ...],
    *,
    haircut: Decimal = Decimal(0),
) -> tuple[Decimal, ...]:
    return tuple(
        trade.r_multiple - haircut
        for trade in trades
        if trade.r_multiple is not None
    )


def _max_drawdown(values: tuple[Decimal, ...]) -> Decimal:
    equity = Decimal(0)
    peak = Decimal(0)
    maximum = Decimal(0)
    for value in values:
        equity += value
        peak = max(peak, equity)
        maximum = max(maximum, peak - equity)
    return maximum


def _metrics(
    trades: tuple[_Trade, ...],
    *,
    haircut: Decimal = Decimal(0),
) -> _Metrics:
    values = _terminal_values(trades, haircut=haircut)
    if not values:
        return _Metrics(0, Decimal(0), Decimal(0), Decimal(0), Decimal(0), 0, 0, 0)
    size = Decimal(len(values))
    expectancy = sum(values, Decimal(0)) / size
    variance = sum(((value - expectancy) ** 2 for value in values), Decimal(0)) / size
    terminal = tuple(item for item in trades if item.r_multiple is not None)
    targets = sum(item.outcome == "target" for item in terminal)
    stops = sum(item.outcome == "stop" for item in terminal)
    breakevens = sum(item.outcome == "breakeven" for item in terminal)
    return _Metrics(
        sample_size=len(values),
        expectancy_r=expectancy,
        win_rate=Decimal(targets) / size,
        population_variance_r=variance,
        max_drawdown_r=_max_drawdown(values),
        target_count=targets,
        stop_count=stops,
        breakeven_count=breakevens,
    )


def _screen_pass(metrics: _Metrics) -> bool:
    return metrics.sample_size >= _MIN_TERMINAL_SAMPLE and metrics.expectancy_r >= 0


def _bootstrap_start(*, replicate: int, draw: int, sample_size: int) -> int:
    payload = (
        _BOOTSTRAP_DOMAIN
        + b":"
        + str(_BOOTSTRAP_SEED).encode("ascii")
        + b":"
        + str(replicate).encode("ascii")
        + b":"
        + str(draw).encode("ascii")
    )
    return int.from_bytes(sha256(payload).digest(), "big") % sample_size


def _bootstrap(values: tuple[Decimal, ...]) -> dict[str, object]:
    policy: dict[str, object] = {
        "algorithm": "qore-circular-block-bootstrap-v1",
        "block_length": _BOOTSTRAP_BLOCK,
        "simulation_count": _BOOTSTRAP_COUNT,
        "seed": _BOOTSTRAP_SEED,
        "lower_quantile_bps": 500,
        "upper_quantile_bps": 9500,
        "qualification_rule": f"sample_size>={_MIN_TERMINAL_SAMPLE} and lower_mean_r>=0",
    }
    if len(values) < _BOOTSTRAP_BLOCK:
        return {
            "status": "insufficient_sample",
            "sample_size": len(values),
            "policy": policy,
        }
    means: list[Decimal] = []
    sample_size = len(values)
    blocks_per_replicate = (
        sample_size + _BOOTSTRAP_BLOCK - 1
    ) // _BOOTSTRAP_BLOCK
    for replicate in range(_BOOTSTRAP_COUNT):
        draw_values: list[Decimal] = []
        for draw in range(blocks_per_replicate):
            start = _bootstrap_start(
                replicate=replicate,
                draw=draw,
                sample_size=sample_size,
            )
            for offset in range(_BOOTSTRAP_BLOCK):
                draw_values.append(values[(start + offset) % sample_size])
                if len(draw_values) == sample_size:
                    break
            if len(draw_values) == sample_size:
                break
        means.append(sum(draw_values, Decimal(0)) / Decimal(sample_size))
    means.sort()
    lower = means[int((len(means) - 1) * 0.05)]
    upper = means[int((len(means) - 1) * 0.95)]
    status = (
        "qualified"
        if sample_size >= _MIN_TERMINAL_SAMPLE and lower >= 0
        else "not_qualified"
    )
    return {
        "status": status,
        "sample_size": sample_size,
        "lower_mean_r": format(lower, "f"),
        "upper_mean_r": format(upper, "f"),
        "policy": policy,
    }


def _story(trade: _Trade, bars: tuple[_Bar, ...]) -> dict[str, object]:
    end = trade.resolved_at if trade.resolved_at is not None else trade.filled_at
    path = tuple(item for item in bars if trade.filled_at <= item.closed_at <= end)
    risk = abs(trade.entry_price - trade.stop_loss)
    if risk == 0:
        mfe = Decimal(0)
        mae = Decimal(0)
    elif trade.side == "long":
        mfe = max((item.high - trade.entry_price for item in path), default=Decimal(0)) / risk
        mae = max((trade.entry_price - item.low for item in path), default=Decimal(0)) / risk
    else:
        mfe = max((trade.entry_price - item.low for item in path), default=Decimal(0)) / risk
        mae = max((item.high - trade.entry_price for item in path), default=Decimal(0)) / risk
    return {
        "decision_time": {
            "signal_at": trade.signal_at.isoformat(timespec="microseconds"),
            "side": trade.side,
            "entry_price": format(trade.entry_price, "f"),
            "stop_loss": format(trade.stop_loss, "f"),
            "take_profit": format(trade.take_profit, "f"),
            "entry_model": trade.entry_model,
        },
        "entry": {"filled_at": trade.filled_at.isoformat(timespec="microseconds")},
        "management": {
            "source_rule": "3R-to-breakeven",
            "breakeven_armed_at": (
                trade.breakeven_armed_at.isoformat(timespec="microseconds")
                if trade.breakeven_armed_at is not None
                else None
            ),
        },
        "post_outcome_oracle_descriptive_only": {
            "resolved_at": (
                trade.resolved_at.isoformat(timespec="microseconds")
                if trade.resolved_at is not None
                else None
            ),
            "outcome": trade.outcome,
            "r_multiple": (
                format(trade.r_multiple, "f") if trade.r_multiple is not None else None
            ),
            "mfe_r": format(max(mfe, Decimal(0)), "f"),
            "mae_r": format(max(mae, Decimal(0)), "f"),
        },
    }


def build_vt31_silver_bullet_v2_full_research_payloads(
    market: dict[str, object],
    backtest: dict[str, object],
) -> dict[str, dict[str, object]]:
    """Build deterministic Trader Lab research evidence without authority promotion."""

    software_sha, bars, trades = _validate_contracts(market, backtest)
    split_index = max(1, int(len(bars) * 0.70))
    split_at = bars[split_index].opened_at if split_index < len(bars) else bars[-1].opened_at
    in_sample = tuple(item for item in trades if item.signal_at < split_at)
    oos = tuple(item for item in trades if item.signal_at >= split_at)
    in_metrics = _metrics(in_sample)
    oos_metrics = _metrics(oos)
    governance: dict[str, object] = {
        "state": "consumed_for_research",
        "consumed_holdout_cannot_certify_modified_strategy": True,
        "post_change_reuse_as_independent_holdout_prohibited": True,
        "new_previously_unseen_holdout_required_after_any_hypothesis_change": True,
        "demo_eligible_authority": False,
    }
    walk_forward: dict[str, object] = {
        "schema": "qore.trader_lab.vt31_silver_bullet_v2_walk_forward.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": software_sha,
        "symbol": _SYMBOL,
        "configuration_selection": "source_frozen_no_parameter_search",
        "in_sample_fraction": "0.70",
        "oos_fraction": "0.30",
        "split_at": split_at.isoformat(timespec="microseconds"),
        "in_sample": in_metrics.payload(),
        "oos": oos_metrics.payload(),
        "in_sample_pass": _screen_pass(in_metrics),
        "oos_pass": _screen_pass(oos_metrics),
        "holdout_governance": governance,
    }
    setup_count = _strict_int(backtest.get("setup_count"), field_name="setup_count")
    filled_count = _strict_int(backtest.get("filled_count"), field_name="filled_count")
    unfilled = _strict_int(
        backtest.get("unfilled_setup_count"), field_name="unfilled_setup_count"
    )
    characterization: dict[str, object] = {
        "schema": "qore.trader_lab.vt31_silver_bullet_v2_characterization.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": software_sha,
        "symbol": _SYMBOL,
        "decision_funnel": {
            "decision_days": _strict_int(
                backtest.get("decision_days"), field_name="decision_days"
            ),
            "setup_count": setup_count,
            "filled_count": filled_count,
            "unfilled_setup_count": unfilled,
            "pending_gap_count": _strict_int(
                backtest.get("pending_gap_count"), field_name="pending_gap_count"
            ),
            "abstain_evaluation_counts": backtest.get("abstain_evaluation_counts", {}),
            "session_abstain_counts": backtest.get("session_abstain_counts", {}),
        },
        "all_terminal": _metrics(trades).payload(),
        "long": _metrics(tuple(item for item in trades if item.side == "long")).payload(),
        "short": _metrics(tuple(item for item in trades if item.side == "short")).payload(),
        "entry_model_counts": dict(sorted(Counter(item.entry_model for item in trades).items())),
        "breakeven_management": {
            "source_rule": "3R-to-breakeven",
            "armed_trade_count": sum(item.breakeven_armed_at is not None for item in trades),
            "breakeven_exit_count": sum(item.outcome == "breakeven" for item in trades),
        },
        "parameter_sensitivity": {
            "status": "not_applicable",
            "reason": "source-frozen methodology has no optimization sweep",
        },
        "holdout_governance": governance,
    }
    stress_rows: list[dict[str, object]] = []
    stress_pass = oos_metrics.sample_size >= _MIN_TERMINAL_SAMPLE
    for haircut in _STRESS_HAIRCUTS_R:
        metrics = _metrics(oos, haircut=haircut)
        passed = _screen_pass(metrics)
        stress_pass = stress_pass and passed
        stress_rows.append(
            {
                "haircut_r": format(haircut, "f"),
                "metrics": metrics.payload(),
                "pass": passed,
            }
        )
    stress: dict[str, object] = {
        "schema": "qore.trader_lab.vt31_silver_bullet_v2_stress.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": software_sha,
        "symbol": _SYMBOL,
        "scenarios": stress_rows,
        "stress_pass": stress_pass,
        "governed_stage_authority": False,
        "holdout_governance": governance,
    }
    monte_carlo: dict[str, object] = {
        "schema": "qore.trader_lab.vt31_silver_bullet_v2_monte_carlo.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": software_sha,
        "symbol": _SYMBOL,
        "source": "chronological_oos_terminal_R_sequence",
        **_bootstrap(_terminal_values(oos)),
        "governed_stage_authority": False,
        "holdout_governance": governance,
    }
    stories = [_story(item, bars) for item in trades]
    story_forensics: dict[str, object] = {
        "schema": "qore.trader_lab.vt31_silver_bullet_v2_story_forensics.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": software_sha,
        "symbol": _SYMBOL,
        "methodology": _METHODOLOGY,
        "trade_story_count": len(stories),
        "stories": stories,
        "holdout_governance": governance,
    }
    long_oos = _metrics(tuple(item for item in oos if item.side == "long"))
    short_oos = _metrics(tuple(item for item in oos if item.side == "short"))
    labels: list[str] = []
    if not _screen_pass(oos_metrics):
        labels.append("oos_generalization_failure")
    if not stress_pass:
        labels.append("stress_fragility")
    if monte_carlo.get("status") != "qualified":
        labels.append("monte_carlo_lower_envelope_not_positive")
    if (
        long_oos.sample_size > 0
        and short_oos.sample_size > 0
        and (long_oos.expectancy_r >= 0) != (short_oos.expectancy_r >= 0)
    ):
        labels.append("directional_asymmetry")
    if setup_count and Decimal(unfilled) / Decimal(setup_count) > Decimal("0.25"):
        labels.append("elevated_unfilled_setup_rate")
    if not labels:
        labels.append("no_failure_rule_triggered_research_only")
    failure_analysis: dict[str, object] = {
        "schema": "qore.trader_lab.vt31_silver_bullet_v2_failure_analysis.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": software_sha,
        "symbol": _SYMBOL,
        "observations": labels,
        "oos": oos_metrics.payload(),
        "long_oos": long_oos.payload(),
        "short_oos": short_oos.payload(),
        "stress_pass": stress_pass,
        "monte_carlo_status": monte_carlo.get("status"),
        "causality_claimed": False,
        "holdout_governance": governance,
    }
    hypothesis_register: dict[str, object] = {
        "schema": "qore.trader_lab.vt31_silver_bullet_v2_hypothesis_register.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": software_sha,
        "symbol": _SYMBOL,
        "methodology_frozen": True,
        "observed_failure_labels": labels,
        "candidate_hypotheses": [
            {
                "id": "vt31-v2-entry-model-discretion",
                "enabled_for_modification": False,
                "mechanism_to_investigate": (
                    "source-discretionary breaker/order-block/FVG selection"
                ),
                "falsification_requirement": (
                    "pre-register selection policy and use fresh unseen holdout"
                ),
            },
            {
                "id": "vt31-v2-directional-asymmetry",
                "enabled_for_modification": False,
                "triggered": "directional_asymmetry" in labels,
                "mechanism_to_investigate": (
                    "long/short geometry and post-raid structure behavior"
                ),
                "falsification_requirement": (
                    "pre-register any change and evaluate on fresh unseen holdout"
                ),
            },
        ],
        "holdout_governance": governance,
    }
    summary: dict[str, object] = {
        "schema": _SCHEMA,
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "software_sha": software_sha,
        "symbol": _SYMBOL,
        "trader_code": "vt-31",
        "trader_version": "v2",
        "methodology": _METHODOLOGY,
        "methodology_version": "v2.1-source-complete",
        "walk_forward_in_sample_pass": walk_forward["in_sample_pass"],
        "walk_forward_oos_pass": walk_forward["oos_pass"],
        "stress_pass": stress_pass,
        "monte_carlo_status": monte_carlo.get("status"),
        "story_forensics_complete": len(stories) == len(trades),
        "failure_labels": labels,
        "demo_eligible": False,
        "promotion_blocker": (
            "fresh unseen holdout and governed authority chain remain required"
        ),
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
    payloads = build_vt31_silver_bullet_v2_full_research_payloads(
        _load_json(market_path, field_name="market evidence"),
        _load_json(backtest_path, field_name="backtest evidence"),
    )
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