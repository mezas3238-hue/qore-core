"""Build CIBO Maximum Capability Frontier and Economic Efficiency telemetry."""

from __future__ import annotations

import argparse
import hashlib
import json
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.cibo_maximum_capability_frontier import (
    FULL_LIFECYCLE_FEATURES,
    POLICY_ID,
    CausalFrontierOpportunity,
    EpochOption,
    LifecycleFeature,
    PositionLifecycleResult,
    cognitive_multiplier_cap,
    optimize_epoch_multipliers,
)
from qore.infrastructure.cibo_position_lifecycle import (
    CiboLifecycleFeature,
    CiboPositionLifecycleInput,
    run_cibo_position_lifecycle,
)
from qore.infrastructure.trader_lab.cibo_market_atlas_journey_extractor_v1 import (
    load_raw_m5,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Bar

SYMBOLS = (
    "AUDJPY",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "XAUUSD",
    "NAS100",
)
INITIAL_CAPITAL = Decimal("60")


@dataclass(slots=True)
class _OpenExposure:
    signal: str
    trader: str
    initial_risk: Decimal
    initial_margin: Decimal
    lifecycle: PositionLifecycleResult
    next_event: int = 0
    risk_fraction: Decimal = Decimal(1)
    margin_fraction: Decimal = Decimal(1)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _dec(value: object) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError(f"non-finite Decimal: {value!r}")
    return result


def _dt(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def _fmt(value: Decimal) -> str:
    return format(value, "f")


def _source_roots(values: list[str]) -> dict[str, Path]:
    parsed: dict[str, Path] = {}
    for value in values:
        symbol, sep, raw = value.partition("=")
        if not sep or symbol not in SYMBOLS or not raw:
            raise ValueError(
                "source root must be one supported SYMBOL=PATH"
            )
        if symbol in parsed:
            raise ValueError(
                f"duplicate source root: {symbol}"
            )
        parsed[symbol] = Path(raw)
    if set(parsed) != set(SYMBOLS):
        raise ValueError(
            "maximum capability frontier requires exact six symbol corpora"
        )
    return parsed


def _provider_cost_per_volume(
    row: dict[str, Any],
) -> Decimal:
    state = row.get("market_predecision_state")
    if not isinstance(state, dict):
        raise ValueError(
            "market predecision state missing"
        )
    obs = state.get("provider_observation")
    if not isinstance(obs, dict):
        raise ValueError("provider observation missing")
    ask = _dec(obs["ask"])
    bid = _dec(obs["bid"])
    tick_size = _dec(obs["tick_size"])
    tick_value = _dec(obs["tick_value"])
    commission = _dec(
        obs.get("commission_per_volume_usd", "0")
    )
    slippage = _dec(
        obs.get(
            "slippage_reserve_per_volume_usd",
            "0",
        )
    )
    if (
        tick_size <= 0
        or tick_value <= 0
        or ask < bid
    ):
        raise ValueError(
            "provider economics invalid"
        )
    spread_cost = (
        (ask - bid) / tick_size
    ) * tick_value
    return spread_cost + commission + slippage


def _base_volume(
    opportunity: dict[str, Any],
) -> Decimal:
    minimum = _dec(
        opportunity["minimum_volume"]
    )
    step = _dec(
        opportunity["volume_step"]
    )
    minimum_steps = int(
        opportunity["minimum_execution_steps"]
    )
    raw = minimum * Decimal(minimum_steps)
    return (
        raw / step
    ).to_integral_value(
        rounding=ROUND_CEILING
    ) * step


def _opportunities(
    trace: dict[str, Any],
) -> tuple[
    dict[str, CausalFrontierOpportunity],
    dict[str, str],
    dict[str, tuple[str, ...]],
    dict[str, str],
]:
    rows = trace.get("opportunities")
    if not isinstance(rows, list) or not rows:
        raise ValueError(
            "decision trace opportunities missing"
        )
    opportunities: dict[
        str, CausalFrontierOpportunity
    ] = {}
    epoch_by_signal: dict[str, str] = {}
    cognitive_codes: dict[
        str, tuple[str, ...]
    ] = {}
    cognitive_reasons: dict[
        str, str
    ] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(
                "decision trace row invalid"
            )
        signal = str(
            row["signal_fingerprint"]
        )
        if signal in opportunities:
            raise ValueError(
                "duplicate frontier signal"
            )
        raw_opportunity = row.get(
            "trader_opportunity"
        )
        expectation = row.get("expectation")
        evaluation = row.get(
            "evaluation_outcome"
        )
        context = row.get("context_quality")
        cognitive = row.get(
            "cognitive_orchestration"
        )
        if (
            not isinstance(
                raw_opportunity, dict
            )
            or not isinstance(
                expectation, dict
            )
            or not isinstance(
                evaluation, dict
            )
            or not isinstance(
                context, dict
            )
            or not isinstance(
                cognitive, dict
            )
        ):
            raise ValueError(
                "frontier row is missing causal/evaluation surfaces"
            )
        if (
            evaluation.get(
                "not_available_to_predecision"
            )
            is not True
        ):
            raise ValueError(
                "evaluation outcome boundary missing"
            )
        if (
            evaluation.get(
                "used_for_decision"
            )
            is not False
        ):
            raise ValueError(
                "frontier rejects evaluation outcome in decision"
            )
        cap, consumed, reason = (
            cognitive_multiplier_cap(
                cognitive
            )
        )
        base_volume = _base_volume(
            raw_opportunity
        )
        opportunities[
            signal
        ] = CausalFrontierOpportunity(
            signal_fingerprint=signal,
            trader_id=str(
                row["trader_id"]
            ),
            qore_symbol=str(
                row["qore_symbol"]
            ),
            decision_at=_dt(
                row["market_decision_at"]
            ),
            entry_at=_dt(
                evaluation["entry_at"]
            ),
            horizon_at=_dt(
                evaluation["exit_at"]
            ),
            side=str(
                raw_opportunity["side"]
            ),
            entry_price=_dec(
                raw_opportunity[
                    "intended_entry"
                ]
            ),
            structural_stop=_dec(
                raw_opportunity[
                    "stop_loss"
                ]
            ),
            technical_target=_dec(
                raw_opportunity[
                    "take_profit"
                ]
            ),
            base_volume=base_volume,
            volume_step=_dec(
                raw_opportunity[
                    "volume_step"
                ]
            ),
            maximum_volume=_dec(
                raw_opportunity[
                    "maximum_volume"
                ]
            ),
            stop_risk_per_volume_usd=_dec(
                raw_opportunity[
                    "stop_loss_per_volume"
                ]
            ),
            margin_per_volume_usd=_dec(
                raw_opportunity[
                    "margin_per_volume"
                ]
            ),
            provider_cost_per_volume_usd=(
                _provider_cost_per_volume(
                    row
                )
            ),
            expected_net_value_usd=_dec(
                expectation[
                    "expected_net_value_usd"
                ]
            ),
            expected_capital_minutes=max(
                Decimal(1),
                _dec(
                    expectation[
                        "expected_capital_minutes"
                    ]
                ),
            ),
            context_allowed=(
                str(
                    context.get(
                        "disposition"
                    )
                )
                == "ALLOW"
            ),
            cognitive_multiplier_cap=cap,
            fallback_gross_r=_dec(
                evaluation[
                    "gross_structural_outcome_r"
                ]
            ),
        )
        epoch_by_signal[
            signal
        ] = str(
            row["decision_epoch_id"]
        )
        cognitive_codes[
            signal
        ] = consumed
        cognitive_reasons[
            signal
        ] = reason
    return (
        opportunities,
        epoch_by_signal,
        cognitive_codes,
        cognitive_reasons,
    )


def _bars_by_symbol(
    source_roots: dict[str, Path],
) -> dict[str, tuple[Bar, ...]]:
    result: dict[
        str, tuple[Bar, ...]
    ] = {}
    for symbol in SYMBOLS:
        evidence, _provenance = (
            load_raw_m5(
                source_roots[symbol]
            )
        )
        if evidence.symbol != symbol:
            raise ValueError(
                f"{symbol}: Market Atlas identity drift"
            )
        result[
            symbol
        ] = evidence.bars
    return result


def _lifecycle_map(
    opportunities: dict[
        str, CausalFrontierOpportunity
    ],
    bars: dict[
        str, tuple[Bar, ...]
    ],
    *,
    features: frozenset[
        LifecycleFeature
    ],
) -> dict[
    str, PositionLifecycleResult
]:
    bounds = {
        symbol: (
            tuple(
                item.opened_at
                for item in series
            ),
            tuple(
                item.closed_at
                for item in series
            ),
        )
        for symbol, series
        in bars.items()
    }
    result: dict[
        str, PositionLifecycleResult
    ] = {}
    for (
        signal,
        opportunity,
    ) in opportunities.items():
        series = bars[
            opportunity.qore_symbol
        ]
        opened, closed = bounds[
            opportunity.qore_symbol
        ]
        start = bisect_left(
            opened,
            opportunity.entry_at,
        )
        end = bisect_right(
            closed,
            opportunity.horizon_at,
        )
        segment = (
            series[start:end]
            if start < end
            else ()
        )
        result[
            signal
        ] = simulate_position_lifecycle(
            opportunity,
            segment,
            features=features,
        )
    return result


def _max_drawdown(
    events: list[
        tuple[datetime, Decimal]
    ],
) -> Decimal:
    capital = INITIAL_CAPITAL
    peak = capital
    maximum = Decimal(0)
    for _time, pnl in sorted(
        events,
        key=lambda item: item[0],
    ):
        capital += pnl
        peak = max(peak, capital)
        maximum = max(
            maximum,
            peak - capital,
        )
    return maximum


def _run_frontier(
    *,
    opportunities: dict[
        str, CausalFrontierOpportunity
    ],
    epoch_by_signal: dict[
        str, str
    ],
    lifecycle: dict[
        str, PositionLifecycleResult
    ],
    cognitive_enabled: bool = True,
    fixed_multiplier: int | None = None,
    portfolio_competition: bool = True,
    compound_enabled: bool = True,
) -> dict[str, Any]:
    signals_by_epoch: dict[
        str, list[str]
    ] = defaultdict(list)
    epoch_times: dict[
        str, datetime
    ] = {}
    for (
        signal,
        epoch,
    ) in epoch_by_signal.items():
        signals_by_epoch[
            epoch
        ].append(signal)
        at = opportunities[
            signal
        ].decision_at
        if (
            epoch in epoch_times
            and epoch_times[
                epoch
            ]
            != at
        ):
            raise ValueError(
                "epoch decision-time drift"
            )
        epoch_times[
            epoch
        ] = at

    ordered_epochs = sorted(
        epoch_times,
        key=lambda key: (
            epoch_times[key],
            key,
        ),
    )
    realized = INITIAL_CAPITAL
    peak = INITIAL_CAPITAL
    max_dd = Decimal(0)
    active: dict[
        str, _OpenExposure
    ] = {}
    pnl_events: list[
        tuple[datetime, Decimal]
    ] = []
    selected_rows: list[
        dict[str, Any]
    ] = []
    by_trader: defaultdict[
        str, Decimal
    ] = defaultdict(Decimal)
    leverage = Counter()
    costs = Decimal(0)
    rejected_capacity = 0

    def book(
        at: datetime,
        trader: str,
        pnl: Decimal,
    ) -> None:
        nonlocal realized
        nonlocal peak
        nonlocal max_dd
        realized += pnl
        by_trader[
            trader
        ] += pnl
        pnl_events.append(
            (at, pnl)
        )
        peak = max(
            peak, realized
        )
        max_dd = max(
            max_dd,
            peak - realized,
        )

    def advance(
        clock: datetime,
    ) -> None:
        while True:
            due: list[
                tuple[
                    datetime,
                    str,
                ]
            ] = []
            for (
                signal,
                exposure,
            ) in active.items():
                if (
                    exposure.next_event
                    >= len(
                        exposure.lifecycle.events
                    )
                ):
                    continue
                event = (
                    exposure.lifecycle.events[
                        exposure.next_event
                    ]
                )
                if (
                    event.occurred_at
                    <= clock
                ):
                    due.append(
                        (
                            event.occurred_at,
                            signal,
                        )
                    )
            if not due:
                break
            (
                at,
                signal,
            ) = min(
                due,
                key=lambda item: (
                    item[0],
                    item[1],
                ),
            )
            exposure = active[
                signal
            ]
            event = (
                exposure.lifecycle.events[
                    exposure.next_event
                ]
            )
            pnl = (
                event.realized_r_delta
                * exposure.initial_risk
            )
            if pnl:
                book(
                    at,
                    exposure.trader,
                    pnl,
                )
            exposure.risk_fraction = (
                event.risk_fraction_remaining
            )
            exposure.margin_fraction = (
                event.margin_fraction_remaining
            )
            exposure.next_event += 1
            if (
                event.remaining_volume_fraction
                == 0
            ):
                active.pop(signal)

    for epoch in ordered_epochs:
        clock = epoch_times[
            epoch
        ]
        advance(clock)
        capacity_capital = (
            realized
            if compound_enabled
            else min(
                realized,
                INITIAL_CAPITAL,
            )
        )
        if capacity_capital <= 0:
            break
        open_risk = sum(
            (
                item.initial_risk
                * item.risk_fraction
                for item in active.values()
            ),
            Decimal(0),
        )
        open_margin = sum(
            (
                item.initial_margin
                * item.margin_fraction
                for item in active.values()
            ),
            Decimal(0),
        )
        risk_headroom = max(
            Decimal(0),
            capacity_capital
            - open_risk,
        )
        margin_headroom = max(
            Decimal(0),
            capacity_capital
            - open_margin,
        )

        epoch_signals = sorted(
            signals_by_epoch[
                epoch
            ]
        )
        epoch_opps = [
            opportunities[
                signal
            ]
            for signal
            in epoch_signals
        ]
        options: list[
            EpochOption
        ] = []
        for opportunity in epoch_opps:
            cap = (
                opportunity.provider_multiplier_cap
            )
            if not (
                opportunity.context_allowed
            ):
                cap = 0
            if cognitive_enabled:
                cap = min(
                    cap,
                    opportunity.cognitive_multiplier_cap,
                )
            options.append(
                EpochOption(
                    signal_fingerprint=(
                        opportunity.signal_fingerprint
                    ),
                    multiplier_cap=cap,
                    expected_net_value_usd=(
                        opportunity.expected_net_value_usd
                    ),
                    expected_capital_minutes=(
                        opportunity.expected_capital_minutes
                    ),
                    risk_per_multiplier_usd=(
                        opportunity.base_stop_risk_usd
                    ),
                    margin_per_multiplier_usd=(
                        opportunity.base_margin_usd
                    ),
                )
            )
        multipliers = (
            optimize_epoch_multipliers(
                options,
                risk_headroom_usd=(
                    risk_headroom
                ),
                margin_headroom_usd=(
                    margin_headroom
                ),
                fixed_multiplier=(
                    fixed_multiplier
                ),
                portfolio_competition=(
                    portfolio_competition
                ),
            )
        )
        for (
            opportunity,
            multiplier,
        ) in zip(
            epoch_opps,
            multipliers,
            strict=True,
        ):
            if multiplier <= 0:
                continue
            risk = (
                opportunity.base_stop_risk_usd
                * Decimal(multiplier)
            )
            margin = (
                opportunity.base_margin_usd
                * Decimal(multiplier)
            )
            if (
                risk > risk_headroom
                or margin > margin_headroom
            ):
                rejected_capacity += 1
                continue
            volume = (
                opportunity.base_volume
                * Decimal(multiplier)
            )
            cost = (
                opportunity.provider_cost_per_volume_usd
                * volume
            )
            costs += cost
            book(
                clock,
                opportunity.trader_id,
                -cost,
            )
            risk_headroom -= risk
            margin_headroom -= margin
            active[
                opportunity.signal_fingerprint
            ] = _OpenExposure(
                signal=(
                    opportunity.signal_fingerprint
                ),
                trader=opportunity.trader_id,
                initial_risk=risk,
                initial_margin=margin,
                lifecycle=lifecycle[
                    opportunity.signal_fingerprint
                ],
            )
            leverage[
                str(multiplier)
            ] += 1
            selected_rows.append(
                {
                    "signal_fingerprint": (
                        opportunity.signal_fingerprint
                    ),
                    "trader_id": (
                        opportunity.trader_id
                    ),
                    "qore_symbol": (
                        opportunity.qore_symbol
                    ),
                    "decision_at": (
                        opportunity.decision_at.isoformat()
                    ),
                    "multiplier": multiplier,
                    "expected_net_value_usd": (
                        _fmt(
                            opportunity.expected_net_value_usd
                        )
                    ),
                    "expected_capital_minutes": (
                        _fmt(
                            opportunity.expected_capital_minutes
                        )
                    ),
                    "initial_stop_risk_usd": (
                        _fmt(risk)
                    ),
                    "initial_margin_usd": (
                        _fmt(margin)
                    ),
                    "provider_cost_usd": (
                        _fmt(cost)
                    ),
                    "cognitive_multiplier_cap": (
                        opportunity.cognitive_multiplier_cap
                    ),
                    "position_lifecycle_data_available": (
                        lifecycle[
                            opportunity.signal_fingerprint
                        ].data_available
                    ),
                }
            )

    if active:
        final_clock = max(
            item.lifecycle.events[
                -1
            ].occurred_at
            for item in active.values()
        )
        advance(final_clock)

    if active:
        raise ValueError(
            "frontier left open exposures after final advance"
        )
    return {
        "ending_capital_usd": (
            _fmt(realized)
        ),
        "net_pnl_usd": (
            _fmt(
                realized
                - INITIAL_CAPITAL
            )
        ),
        "max_realized_drawdown_usd": (
            _fmt(max_dd)
        ),
        "survival": realized > 0,
        "selected_count": (
            len(selected_rows)
        ),
        "provider_cost_usd": (
            _fmt(costs)
        ),
        "leverage_distribution": (
            dict(
                sorted(
                    leverage.items()
                )
            )
        ),
        "per_trader_pnl_usd": {
            key: _fmt(value)
            for (
                key,
                value,
            ) in sorted(
                by_trader.items()
            )
        },
        "capacity_rejections": (
            rejected_capacity
        ),
        "selected": selected_rows,
        "outcome_used_for_decision": False,
        "future_market_used_for_decision": False,
        "qore_risk_bypassed": False,
    }


def _actual_events(
    trace: dict[str, Any],
    dynamic_portfolio: dict[
        str, Any
    ],
) -> list[
    tuple[datetime, Decimal]
]:
    events: list[
        tuple[datetime, Decimal]
    ] = []
    for row in trace[
        "opportunities"
    ]:
        settlement = row.get(
            "settlement"
        )
        if isinstance(
            settlement, dict
        ):
            events.append(
                (
                    _dt(
                        settlement[
                            "capital_released_at"
                        ]
                    ),
                    _dec(
                        settlement[
                            "realized_net_pnl_usd"
                        ]
                    ),
                )
            )
    for row in dynamic_portfolio.get(
        "trades", []
    ):
        if isinstance(row, dict):
            events.append(
                (
                    _dt(
                        row[
                            "exit_at"
                        ]
                    ),
                    _dec(
                        row[
                            "incremental_realized_pnl_usd"
                        ]
                    ),
                )
            )
    return events


def _idle_capital_metrics(
    trace: dict[str, Any],
) -> dict[str, Any]:
    by_epoch: dict[
        str, list[
            dict[str, Any]
        ]
    ] = defaultdict(list)
    for row in trace[
        "opportunities"
    ]:
        by_epoch[
            str(
                row[
                    "decision_epoch_id"
                ]
            )
        ].append(row)
    ordered = sorted(
        by_epoch,
        key=lambda key: _dt(
            by_epoch[key][0][
                "market_decision_at"
            ]
        ),
    )
    weighted_idle = Decimal(0)
    weighted_margin_idle = Decimal(0)
    weight_total = Decimal(0)
    simple: list[
        Decimal
    ] = []
    simple_margin: list[
        Decimal
    ] = []
    for (
        index,
        epoch,
    ) in enumerate(
        ordered
    ):
        rows = by_epoch[
            epoch
        ]
        at = _dt(
            rows[0][
                "market_decision_at"
            ]
        )
        if (
            index + 1
            < len(ordered)
        ):
            nxt = _dt(
                by_epoch[
                    ordered[index + 1]
                ][0][
                    "market_decision_at"
                ]
            )
            minutes = max(
                Decimal(1),
                Decimal(
                    str(
                        (
                            nxt - at
                        ).total_seconds()
                    )
                )
                / Decimal(60),
            )
        else:
            minutes = Decimal(1)
        state = rows[
            0
        ][
            "market_predecision_state"
        ]
        risk_headroom = _dec(
            state[
                "hard_risk_headroom_usd"
            ]
        )
        margin_headroom = _dec(
            state[
                "margin_headroom_usd"
            ]
        )
        selected_risk = sum(
            (
                _dec(
                    row[
                        "cma"
                    ][
                        "requested_stop_risk_usd"
                    ]
                )
                for row in rows
                if (
                    row[
                        "allocation"
                    ][
                        "selected_by_cibo_policy"
                    ]
                    and row[
                        "cma"
                    ][
                        "requested_stop_risk_usd"
                    ]
                    is not None
                )
            ),
            Decimal(0),
        )
        selected_margin = sum(
            (
                _dec(
                    row[
                        "qore_risk"
                    ].get(
                        "authorized_margin_usd",
                        "0",
                    )
                )
                for row in rows
                if row[
                    "allocation"
                ][
                    "selected_by_cibo_policy"
                ]
            ),
            Decimal(0),
        )
        risk_idle = (
            Decimal(0)
            if risk_headroom <= 0
            else (
                max(
                    Decimal(0),
                    risk_headroom
                    - selected_risk,
                )
                / risk_headroom
            )
        )
        margin_idle = (
            Decimal(0)
            if margin_headroom <= 0
            else (
                max(
                    Decimal(0),
                    margin_headroom
                    - selected_margin,
                )
                / margin_headroom
            )
        )
        simple.append(
            risk_idle
        )
        simple_margin.append(
            margin_idle
        )
        weighted_idle += (
            risk_idle * minutes
        )
        weighted_margin_idle += (
            margin_idle
            * minutes
        )
        weight_total += minutes
    return {
        "risk_headroom_idle_pct_simple": (
            _fmt(
                (
                    sum(
                        simple,
                        Decimal(0),
                    )
                    / Decimal(
                        len(simple)
                    )
                )
                * Decimal(100)
            )
        ),
        "risk_headroom_idle_pct_time_weighted": (
            _fmt(
                (
                    weighted_idle
                    / weight_total
                )
                * Decimal(100)
            )
        ),
        "margin_headroom_idle_pct_simple": (
            _fmt(
                (
                    sum(
                        simple_margin,
                        Decimal(0),
                    )
                    / Decimal(
                        len(
                            simple_margin
                        )
                    )
                )
                * Decimal(100)
            )
        ),
        "margin_headroom_idle_pct_time_weighted": (
            _fmt(
                (
                    weighted_margin_idle
                    / weight_total
                )
                * Decimal(100)
            )
        ),
        "epoch_count": len(ordered),
    }


def _opportunity_miss_metrics(
    trace: dict[str, Any],
) -> dict[str, Any]:
    missed = []
    later_losers = []
    for row in trace[
        "opportunities"
    ]:
        ev = _dec(
            row[
                "expectation"
            ][
                "expected_net_value_usd"
            ]
        )
        selected = bool(
            row[
                "allocation"
            ][
                "selected_by_cibo_policy"
            ]
        )
        context = row[
            "context_quality"
        ]
        if (
            ev > 0
            and not selected
        ):
            missed.append(
                (
                    ev,
                    str(
                        context.get(
                            "disposition"
                        )
                    ),
                )
            )
        settlement = row.get(
            "settlement"
        )
        if (
            selected
            and isinstance(
                settlement,
                dict,
            )
        ):
            pnl = _dec(
                settlement[
                    "realized_net_pnl_usd"
                ]
            )
            if pnl < 0:
                later_losers.append(
                    (
                        _dec(
                            row[
                                "qore_risk"
                            ][
                                "authorized_stop_risk_usd"
                            ]
                        ),
                        pnl,
                        ev,
                    )
                )
    return {
        "positive_expectancy_missed_count": (
            len(missed)
        ),
        "positive_expectancy_missed_expected_value_usd": (
            _fmt(
                sum(
                    (
                        item[0]
                        for item
                        in missed
                    ),
                    Decimal(0),
                )
            )
        ),
        "positive_expectancy_missed_context_vetoed_count": (
            sum(
                item[1]
                != "ALLOW"
                for item
                in missed
            )
        ),
        "positive_expectancy_missed_after_context_allow_count": (
            sum(
                item[1]
                == "ALLOW"
                for item
                in missed
            )
        ),
        "later_loser_count": (
            len(
                later_losers
            )
        ),
        "later_loser_authorized_risk_usd": (
            _fmt(
                sum(
                    (
                        item[0]
                        for item
                        in later_losers
                    ),
                    Decimal(0),
                )
            )
        ),
        "later_loser_realized_loss_usd": (
            _fmt(
                sum(
                    (
                        -item[1]
                        for item
                        in later_losers
                    ),
                    Decimal(0),
                )
            )
        ),
        "later_loser_predecision_expected_value_usd": (
            _fmt(
                sum(
                    (
                        item[2]
                        for item
                        in later_losers
                    ),
                    Decimal(0),
                )
            )
        ),
        "outcome_used_for_decision": False,
    }


def _quantile(
    values: list[Decimal],
    q: Decimal,
) -> Decimal:
    if not values:
        return Decimal(0)
    ordered = sorted(values)
    position = (
        q
        * Decimal(
            len(ordered) - 1
        )
    )
    lo = int(position)
    hi = min(
        lo + 1,
        len(ordered) - 1,
    )
    frac = position - Decimal(lo)
    return (
        ordered[lo]
        + (
            ordered[hi]
            - ordered[lo]
        )
        * frac
    )


def _release_velocity(
    trace: dict[str, Any],
) -> dict[str, Any]:
    deployments = sorted(
        _dt(
            row[
                "settlement"
            ][
                "capital_deployed_at"
            ]
        )
        for row in trace[
            "opportunities"
        ]
        if isinstance(
            row.get(
                "settlement"
            ),
            dict,
        )
    )
    releases = sorted(
        _dt(
            row[
                "settlement"
            ][
                "capital_released_at"
            ]
        )
        for row in trace[
            "opportunities"
        ]
        if isinstance(
            row.get(
                "settlement"
            ),
            dict,
        )
    )
    latencies: list[
        Decimal
    ] = []
    for release in releases:
        nxt = next(
            (
                item
                for item
                in deployments
                if item > release
            ),
            None,
        )
        if nxt is None:
            continue
        latencies.append(
            Decimal(
                str(
                    (
                        nxt
                        - release
                    ).total_seconds()
                )
            )
            / Decimal(60)
        )
    return {
        "release_to_next_deploy_observations": (
            len(latencies)
        ),
        "release_to_next_deploy_median_minutes": (
            _fmt(
                Decimal(
                    str(
                        median(
                            latencies
                        )
                    )
                )
                if latencies
                else Decimal(0)
            )
        ),
        "release_to_next_deploy_p90_minutes": (
            _fmt(
                _quantile(
                    latencies,
                    Decimal(
                        "0.90"
                    ),
                )
            )
        ),
    }


def _function_attribution(
    *,
    cognitive_value: Decimal,
    lifecycle_value: Decimal,
    compound_value: Decimal,
    portfolio_value: Decimal,
    leverage_value: Decimal,
) -> list[dict[str, Any]]:
    rows = []
    cognitive_controls = {
        "CF02",
        "CF06",
        "CF07",
        "CF10",
        "CF12",
    }
    for index in range(
        1, 20
    ):
        code = (
            f"CF{index:02d}"
        )
        if (
            code
            in cognitive_controls
        ):
            rows.append(
                {
                    "function_code": code,
                    "block": (
                        "COGNITIVE_ECONOMIC_ACTUATION"
                    ),
                    "attribution": (
                        "SHARED_BLOCK_VALUE"
                    ),
                    "block_value_usd": (
                        _fmt(
                            cognitive_value
                        )
                    ),
                    "unique_value_identified": False,
                }
            )
        else:
            rows.append(
                {
                    "function_code": code,
                    "block": (
                        "COGNITIVE"
                    ),
                    "attribution": (
                        "NO_SEPARABLE_DIRECT_CAPITAL_CONTROL_YET"
                    ),
                    "block_value_usd": None,
                    "unique_value_identified": False,
                }
            )
    for index in range(
        1, 21
    ):
        code = (
            f"T{index:02d}"
        )
        if code == "T06":
            block = (
                "COMPOUND_REDEPLOYMENT"
            )
            value = (
                compound_value
            )
        elif code == "T11":
            block = (
                "ADAPTIVE_LEVERAGE"
            )
            value = (
                leverage_value
            )
        elif code == "T14":
            block = (
                "POSITION_LIFECYCLE"
            )
            value = (
                lifecycle_value
            )
        elif code in {
            "T05",
            "T19",
            "T20",
        }:
            block = (
                "CAPITAL_VELOCITY"
            )
            value = (
                compound_value
            )
        else:
            block = "CE2I"
            value = None
        rows.append(
            {
                "function_code": code,
                "block": block,
                "attribution": (
                    "SHARED_BLOCK_VALUE"
                    if value is not None
                    else (
                        "OBSERVED_NOT_UNIQUELY_SEPARABLE"
                    )
                ),
                "block_value_usd": (
                    None
                    if value is None
                    else _fmt(value)
                ),
                "unique_value_identified": False,
            }
        )
    for index in range(
        1, 15
    ):
        code = (
            f"GEN-C{index}"
        )
        rows.append(
            {
                "function_code": code,
                "block": (
                    "CAPITAL_SCIENCE_COMPOUND_PORTFOLIO"
                ),
                "attribution": (
                    "SHARED_BLOCK_VALUE"
                ),
                "block_value_usd": (
                    _fmt(
                        portfolio_value
                    )
                ),
                "unique_value_identified": False,
            }
        )
    if len(rows) != 53:
        raise ValueError(
            "function attribution must cover exact 53 functions"
        )
    return rows


def main() -> int:
    parser = (
        argparse.ArgumentParser()
    )
    parser.add_argument(
        "--decision-trace",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--three-lane",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--source-root",
        action="append",
        required=True,
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )
    args = parser.parse_args()

    trace = _load(
        args.decision_trace
    )
    three_lane = _load(
        args.three_lane
    )
    roots = _source_roots(
        args.source_root
    )
    bars = _bars_by_symbol(
        roots
    )
    (
        opportunities,
        epoch_by_signal,
        cognitive_codes,
        cognitive_reasons,
    ) = _opportunities(
        trace
    )

    variants: dict[
        str,
        frozenset[
            LifecycleFeature
        ],
    ] = {
        "FULL": (
            FULL_LIFECYCLE_FEATURES
        ),
        "NONE": frozenset(),
    }
    for feature in LifecycleFeature:
        variants[
            f"WITHOUT_{feature.value}"
        ] = frozenset(
            item
            for item
            in FULL_LIFECYCLE_FEATURES
            if item is not feature
        )

    lifecycle_maps = {
        name: _lifecycle_map(
            opportunities,
            bars,
            features=features,
        )
        for (
            name,
            features,
        ) in variants.items()
    }

    full = _run_frontier(
        opportunities=opportunities,
        epoch_by_signal=epoch_by_signal,
        lifecycle=(
            lifecycle_maps["FULL"]
        ),
    )
    no_cognition = _run_frontier(
        opportunities=opportunities,
        epoch_by_signal=epoch_by_signal,
        lifecycle=(
            lifecycle_maps["FULL"]
        ),
        cognitive_enabled=False,
    )
    fixed_1x = _run_frontier(
        opportunities=opportunities,
        epoch_by_signal=epoch_by_signal,
        lifecycle=(
            lifecycle_maps["FULL"]
        ),
        fixed_multiplier=1,
    )
    no_competition = _run_frontier(
        opportunities=opportunities,
        epoch_by_signal=epoch_by_signal,
        lifecycle=(
            lifecycle_maps["FULL"]
        ),
        portfolio_competition=False,
    )
    no_compound = _run_frontier(
        opportunities=opportunities,
        epoch_by_signal=epoch_by_signal,
        lifecycle=(
            lifecycle_maps["FULL"]
        ),
        compound_enabled=False,
    )
    no_lifecycle = _run_frontier(
        opportunities=opportunities,
        epoch_by_signal=epoch_by_signal,
        lifecycle=(
            lifecycle_maps["NONE"]
        ),
    )
    lifecycle_ablations = {
        feature.value: (
            _run_frontier(
                opportunities=(
                    opportunities
                ),
                epoch_by_signal=(
                    epoch_by_signal
                ),
                lifecycle=(
                    lifecycle_maps[
                        f"WITHOUT_{feature.value}"
                    ]
                ),
            )
        )
        for feature
        in LifecycleFeature
    }

    dynamic_local = three_lane[
        "all_trader_cibo_compound_dynamic"
    ]
    dynamic_portfolio = three_lane[
        "all_trader_cibo_compound_portfolio_dynamic"
    ]
    core = three_lane[
        "all_trader_cibo_core"
    ]
    actual_ending = _dec(
        dynamic_portfolio[
            "ending_capital_usd"
        ]
    )
    actual_profit = (
        actual_ending
        - INITIAL_CAPITAL
    )
    frontier_ending = _dec(
        full[
            "ending_capital_usd"
        ]
    )
    frontier_profit = (
        frontier_ending
        - INITIAL_CAPITAL
    )
    capture_ratio = (
        None
        if frontier_profit <= 0
        else (
            actual_profit
            / frontier_profit
        )
    )
    actual_events = (
        _actual_events(
            trace,
            dynamic_portfolio,
        )
    )
    actual_dd = _max_drawdown(
        actual_events
    )

    t14_rows = (
        dynamic_portfolio.get(
            "t14_derisk_decisions",
            [],
        )
    )
    t14_released_risk = sum(
        (
            _dec(
                row[
                    "released_stop_risk_usd"
                ]
            )
            for row
            in t14_rows
            if isinstance(
                row, dict
            )
        ),
        Decimal(0),
    )
    t14_released_margin = sum(
        (
            _dec(
                row[
                    "released_margin_usd"
                ]
            )
            for row
            in t14_rows
            if isinstance(
                row, dict
            )
        ),
        Decimal(0),
    )
    t14_changed = sum(
        (
            isinstance(
                row, dict
            )
            and str(
                row.get(
                    "action"
                )
            )
            in {
                "REDUCE",
                "RELEASE_ALL",
            }
        )
        for row
        in t14_rows
    )

    cognitive_value = (
        frontier_ending
        - _dec(
            no_cognition[
                "ending_capital_usd"
            ]
        )
    )
    lifecycle_value = (
        frontier_ending
        - _dec(
            no_lifecycle[
                "ending_capital_usd"
            ]
        )
    )
    compound_value = (
        frontier_ending
        - _dec(
            no_compound[
                "ending_capital_usd"
            ]
        )
    )
    portfolio_value = (
        frontier_ending
        - _dec(
            no_competition[
                "ending_capital_usd"
            ]
        )
    )
    leverage_value = (
        frontier_ending
        - _dec(
            fixed_1x[
                "ending_capital_usd"
            ]
        )
    )

    function_attribution = (
        _function_attribution(
            cognitive_value=(
                cognitive_value
            ),
            lifecycle_value=(
                lifecycle_value
            ),
            compound_value=(
                compound_value
            ),
            portfolio_value=(
                portfolio_value
            ),
            leverage_value=(
                leverage_value
            ),
        )
    )

    payload = {
        "schema": (
            "qore.cibo.maximum-capability-frontier.v1"
        ),
        "policy_id": POLICY_ID,
        "research_group_id": (
            three_lane.get(
                "research_group_id"
            )
        ),
        "objective": (
            "maximize causally expected economic value per capital-minute "
            "under risk, margin, cognition, portfolio competition and "
            "0x..4x constraints"
        ),
        "actual_cibo": {
            "ending_capital_usd": (
                _fmt(
                    actual_ending
                )
            ),
            "net_pnl_usd": (
                _fmt(
                    actual_profit
                )
            ),
            "max_realized_drawdown_usd": (
                _fmt(
                    actual_dd
                )
            ),
        },
        "causal_frontier": full,
        "capture": {
            "frontier_gap_usd": (
                _fmt(
                    frontier_ending
                    - actual_ending
                )
            ),
            "profit_capture_ratio": (
                None
                if capture_ratio
                is None
                else _fmt(
                    capture_ratio
                )
            ),
            "profit_capture_pct": (
                None
                if capture_ratio
                is None
                else _fmt(
                    capture_ratio
                    * Decimal(100)
                )
            ),
        },
        "economic_efficiency": {
            "idle_deployable_capital": (
                _idle_capital_metrics(
                    trace
                )
            ),
            "opportunity_capture": (
                _opportunity_miss_metrics(
                    trace
                )
            ),
            "capital_velocity": (
                _release_velocity(
                    trace
                )
            ),
            "compound_incremental_over_core_usd": (
                _fmt(
                    _dec(
                        dynamic_local[
                            "ending_capital_usd"
                        ]
                    )
                    - _dec(
                        core[
                            "ending_capital_usd"
                        ]
                    )
                )
            ),
            "compound_portfolio_incremental_over_compound_usd": (
                _fmt(
                    actual_ending
                    - _dec(
                        dynamic_local[
                            "ending_capital_usd"
                        ]
                    )
                )
            ),
            "actual_dynamic_leverage_distribution": (
                dict(
                    sorted(
                        Counter(
                            str(
                                row.get(
                                    "effective_multiplier"
                                )
                            )
                            for row
                            in dynamic_portfolio.get(
                                "leverage_decisions",
                                [],
                            )
                            if isinstance(
                                row, dict
                            )
                        ).items()
                    )
                )
            ),
            "actual_dynamic_leverage_reason_distribution": (
                dict(
                    Counter(
                        str(
                            row.get(
                                "reason"
                            )
                        )
                        for row
                        in dynamic_portfolio.get(
                            "leverage_decisions",
                            [],
                        )
                        if isinstance(
                            row, dict
                        )
                    ).most_common()
                )
            ),
            "t14_pre_settlement_release": {
                "decision_count": (
                    len(
                        t14_rows
                    )
                ),
                "changed_count": (
                    t14_changed
                ),
                "released_stop_risk_usd": (
                    _fmt(
                        t14_released_risk
                    )
                ),
                "released_margin_usd": (
                    _fmt(
                        t14_released_margin
                    )
                ),
            },
        },
        "block_ablations": {
            "cognitive_economic_actuation_value_usd": (
                _fmt(
                    cognitive_value
                )
            ),
            "position_lifecycle_value_usd": (
                _fmt(
                    lifecycle_value
                )
            ),
            "capital_compound_value_usd": (
                _fmt(
                    compound_value
                )
            ),
            "portfolio_competition_value_usd": (
                _fmt(
                    portfolio_value
                )
            ),
            "adaptive_leverage_value_vs_1x_usd": (
                _fmt(
                    leverage_value
                )
            ),
            "without_cognition": (
                no_cognition
            ),
            "without_position_lifecycle": (
                no_lifecycle
            ),
            "without_compound": (
                no_compound
            ),
            "without_portfolio_competition": (
                no_competition
            ),
            "fixed_1x": (
                fixed_1x
            ),
        },
        "position_lifecycle_ablations": {
            feature.value: {
                "ending_capital_without_feature_usd": (
                    lifecycle_ablations[
                        feature.value
                    ][
                        "ending_capital_usd"
                    ]
                ),
                "marginal_value_usd": (
                    _fmt(
                        frontier_ending
                        - _dec(
                            lifecycle_ablations[
                                feature.value
                            ][
                                "ending_capital_usd"
                            ]
                        )
                    )
                ),
            }
            for feature
            in LifecycleFeature
        },
        "position_lifecycle_coverage": {
            "candidate_count": (
                len(
                    opportunities
                )
            ),
            "m5_path_available_count": (
                sum(
                    item.data_available
                    for item
                    in lifecycle_maps[
                        "FULL"
                    ].values()
                )
            ),
            "fallback_original_settlement_count": (
                sum(
                    not item.data_available
                    for item
                    in lifecycle_maps[
                        "FULL"
                    ].values()
                )
            ),
            "symbols": list(
                SYMBOLS
            ),
        },
        "cognitive_economic_actuation": {
            "consumed_control_functions": [
                "CF02",
                "CF06",
                "CF07",
                "CF10",
                "CF12",
            ],
            "all_19_faculties_required_for_valid_orchestration": True,
            "per_signal_cognitive_multiplier_cap": {
                signal: (
                    opportunities[
                        signal
                    ].cognitive_multiplier_cap
                )
                for signal
                in sorted(
                    opportunities
                )
            },
            "per_signal_consumed_codes": {
                signal: list(
                    cognitive_codes[
                        signal
                    ]
                )
                for signal
                in sorted(
                    cognitive_codes
                )
            },
            "per_signal_reason": {
                signal: (
                    cognitive_reasons[
                        signal
                    ]
                )
                for signal
                in sorted(
                    cognitive_reasons
                )
            },
        },
        "function_economic_attribution": (
            function_attribution
        ),
        "function_attribution_summary": {
            "function_count": (
                len(
                    function_attribution
                )
            ),
            "unique_function_values_identified": (
                sum(
                    bool(
                        row[
                            "unique_value_identified"
                        ]
                    )
                    for row
                    in function_attribution
                )
            ),
            "shared_block_attribution_count": (
                sum(
                    row[
                        "attribution"
                    ]
                    == "SHARED_BLOCK_VALUE"
                    for row
                    in function_attribution
                )
            ),
            "unseparated_attribution_count": (
                sum(
                    row[
                        "attribution"
                    ]
                    != "SHARED_BLOCK_VALUE"
                    for row
                    in function_attribution
                )
            ),
        },
        "governance": {
            "decision_inputs_predecision_only": True,
            "evaluation_outcomes_not_available_to_decision": True,
            "closed_m5_path_consumed_sequentially_after_entry": True,
            "same_bar_ambiguity_ordering": (
                "CONSERVATIVE_STOP_FIRST"
            ),
            "outcome_aware_tuning": False,
            "trader_logic_changed": False,
            "broker_mutation": False,
            "live": False,
            "production": False,
            "real_capital": False,
            "certification_claimed": False,
        },
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    payload[
        "fingerprint"
    ] = (
        "sha256:"
        + hashlib.sha256(
            raw
        ).hexdigest()
    )
    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    args.output.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "group_id": (
                    payload[
                        "research_group_id"
                    ]
                ),
                "actual_ending_capital_usd": (
                    payload[
                        "actual_cibo"
                    ][
                        "ending_capital_usd"
                    ]
                ),
                "frontier_ending_capital_usd": (
                    full[
                        "ending_capital_usd"
                    ]
                ),
                "frontier_gap_usd": (
                    payload[
                        "capture"
                    ][
                        "frontier_gap_usd"
                    ]
                ),
                "profit_capture_pct": (
                    payload[
                        "capture"
                    ][
                        "profit_capture_pct"
                    ]
                ),
                "m5_path_available_count": (
                    payload[
                        "position_lifecycle_coverage"
                    ][
                        "m5_path_available_count"
                    ]
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
