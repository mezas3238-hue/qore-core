"""Per-Trader observation replay for conditional market-state analytics."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from typing import TextIO, cast

from qore.infrastructure.market_data import OhlcSnapshot
from qore.infrastructure.trader_lab.conditional_market_state_features import (
    event_fingerprint,
    forward_path_evaluation,
    market_state,
    trade_excursions,
)
from qore.infrastructure.trader_lab.conditional_market_state_surfaces import (
    STANDARD_SURFACES,
    StreamingSurface,
)
from qore.infrastructure.trader_lab.first_cohort_backtest import (
    _EXECUTION_PERIOD,
    _PERIOD_SECONDS,
    FirstCohortBacktestError,
    FirstCohortBacktestTrade,
    _h4_context,
    _history,
    _model_trade,
)
from qore.infrastructure.trader_lab.first_cohort_characterization import (
    _methodology_payload,
)
from qore.infrastructure.trader_lab.first_cohort_walk_forward import (
    _ConfiguredEvaluator,
    _fingerprint,
    _parameters,
)
from qore.infrastructure.traders.contracts import DemoTradingDecision
from qore.infrastructure.traders.instrument_binding import (
    DemoTradingEvaluatorBoundary,
    build_instrument_bound_demo_trading_input,
    evaluate_instrument_bound_demo_trader,
)
from qore.kernel.result import Failure


class ConditionalMarketStateObservationError(FirstCohortBacktestError):
    __slots__ = ()


def _outcome_payload(
    *,
    trade: FirstCohortBacktestTrade | None,
    execution: tuple[OhlcSnapshot, ...],
    signal_index: int,
    closed_index: dict[datetime, int],
    risk_fraction: Decimal | None,
) -> dict[str, object]:
    forward = forward_path_evaluation(execution, signal_index)
    if trade is None:
        return {
            "trade_filled": False,
            "trade_return_rate": None,
            "exit_reason": None,
            "mae_fraction": None,
            "mfe_fraction": None,
            "risk_normalized_mae": None,
            "risk_normalized_mfe": None,
            "bars_to_fill": None,
            "holding_bars": None,
            "post_decision_oracle_only": True,
            "forward_path": forward,
        }
    mfe, mae = trade_excursions(trade, execution, closed_index)
    normalized_mfe = None
    normalized_mae = None
    if risk_fraction is not None and risk_fraction > 0:
        normalized_mfe = format(mfe / risk_fraction, "f")
        normalized_mae = format(mae / risk_fraction, "f")
    period_seconds = Decimal(_PERIOD_SECONDS[_EXECUTION_PERIOD[trade.trader_code]])
    bars_to_fill = Decimal(
        str((trade.filled_at - trade.signal_at).total_seconds())
    ) / period_seconds
    holding_bars = Decimal(
        str((trade.exited_at - trade.filled_at).total_seconds())
    ) / period_seconds
    return {
        "trade_filled": True,
        "trade_return_rate": format(trade.return_rate, "f"),
        "exit_reason": trade.exit_reason,
        "filled_at": trade.filled_at.astimezone(UTC).isoformat(),
        "exited_at": trade.exited_at.astimezone(UTC).isoformat(),
        "mae_fraction": format(mae, "f"),
        "mfe_fraction": format(mfe, "f"),
        "risk_normalized_mae": normalized_mae,
        "risk_normalized_mfe": normalized_mfe,
        "bars_to_fill": format(bars_to_fill, "f"),
        "holding_bars": format(holding_bars, "f"),
        "post_decision_oracle_only": True,
        "forward_path": forward,
    }


def analyze_trader(
    evaluator: DemoTradingEvaluatorBoundary,
    *,
    trader_code: str,
    symbol: str,
    software_sha: str,
    series: dict[str, tuple[OhlcSnapshot, ...]],
    observation_writer: TextIO | None,
) -> dict[str, object]:
    execution_period = _EXECUTION_PERIOD[trader_code]
    execution = series[execution_period]
    closed_index = {bar.closed_at: index for index, bar in enumerate(execution)}
    surfaces = {
        dimensions: StreamingSurface(dimensions) for dimensions in STANDARD_SURFACES
    }
    decision_counts: Counter[str] = Counter()
    context_unavailable = 0
    observation_count = 0
    observation_hasher = hashlib.sha256()
    abstention_forward_up_count = 0
    abstention_forward_down_count = 0
    abstention_large_move_count = 0
    stopped_after_positive_mfe_count = 0
    stopped_after_one_r_mfe_count = 0

    def _record_observation(observation: dict[str, object]) -> None:
        nonlocal observation_count
        nonlocal abstention_forward_up_count, abstention_forward_down_count
        nonlocal abstention_large_move_count
        nonlocal stopped_after_positive_mfe_count, stopped_after_one_r_mfe_count
        canonical = json.dumps(
            observation,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        encoded = (canonical + "\n").encode()
        observation_hasher.update(encoded)
        observation_count += 1
        if observation_writer is not None:
            observation_writer.write(canonical)
            observation_writer.write("\n")
        decision = cast(dict[str, object], observation["decision"])
        status = str(decision["status"])
        decision_counts[status] += 1
        outcome = cast(dict[str, object], observation["outcome_evaluation"])
        if status == DemoTradingDecision.ABSTAIN.value:
            forward = cast(dict[str, object], outcome["forward_path"])
            up = Decimal(str(forward["max_up_fraction"]))
            down = Decimal(str(forward["max_down_fraction"]))
            if up > 0:
                abstention_forward_up_count += 1
            if down > 0:
                abstention_forward_down_count += 1
            state = cast(dict[str, object], observation["decision_time_state"])
            reference_raw = state.get("recent_realized_range_fraction")
            if isinstance(reference_raw, str):
                reference = Decimal(reference_raw)
                if reference > 0 and max(up, down) >= reference * Decimal(2):
                    abstention_large_move_count += 1
        if outcome.get("trade_filled") is True and outcome.get("exit_reason") == "stop":
            mfe_raw = outcome.get("mfe_fraction")
            risk_raw = decision.get("risk_fraction")
            if isinstance(mfe_raw, str) and Decimal(mfe_raw) > 0:
                stopped_after_positive_mfe_count += 1
                if isinstance(risk_raw, str) and Decimal(risk_raw) > 0:
                    if Decimal(mfe_raw) >= Decimal(risk_raw):
                        stopped_after_one_r_mfe_count += 1
        for surface in surfaces.values():
            surface.record(observation)

    for index in range(len(execution) - 1):
        as_of = execution[index].closed_at
        history = _history(execution, index)
        h4_context = _h4_context(series["H4"], as_of=as_of)
        state = market_state(
            history,
            context_history=h4_context,
            as_of=as_of,
            execution_period=execution_period,
        )
        event_id = event_fingerprint(
            trader_code=trader_code,
            symbol=symbol,
            software_sha=software_sha,
            decision_at=as_of,
            execution_period=execution_period,
        )
        context = h4_context if trader_code == "vt-08" else ()
        if trader_code == "vt-08" and not context:
            context_unavailable += 1
            _record_observation(
                {
                    "event_fingerprint": event_id,
                    "trader_code": trader_code,
                    "market": symbol,
                    "decision_time_state": state,
                    "decision": {
                        "status": "context_unavailable",
                        "abstain_reason": None,
                        "side": None,
                        "setup_reason": None,
                    },
                    "outcome_evaluation": _outcome_payload(
                        trade=None,
                        execution=execution,
                        signal_index=index,
                        closed_index=closed_index,
                        risk_fraction=None,
                    ),
                }
            )
            continue

        bound = build_instrument_bound_demo_trading_input(
            execution_evidence=history,
            context_evidence=context,
            as_of=as_of,
        )
        evaluated = evaluate_instrument_bound_demo_trader(evaluator, bound)
        if isinstance(evaluated, Failure):
            _record_observation(
                {
                    "event_fingerprint": event_id,
                    "trader_code": trader_code,
                    "market": symbol,
                    "decision_time_state": state,
                    "decision": {
                        "status": "evaluation_failure",
                        "failure_type": type(evaluated.error).__name__,
                        "abstain_reason": None,
                        "side": None,
                        "setup_reason": None,
                    },
                    "outcome_evaluation": _outcome_payload(
                        trade=None,
                        execution=execution,
                        signal_index=index,
                        closed_index=closed_index,
                        risk_fraction=None,
                    ),
                }
            )
            continue

        output = evaluated.value.trader_output
        if output.decision is DemoTradingDecision.ABSTAIN:
            _record_observation(
                {
                    "event_fingerprint": event_id,
                    "trader_code": trader_code,
                    "market": symbol,
                    "decision_time_state": state,
                    "decision": {
                        "status": output.decision.value,
                        "abstain_reason": (
                            None
                            if output.abstain_reason is None
                            else output.abstain_reason.value
                        ),
                        "side": None,
                        "setup_reason": None,
                        "trader_session": output.session,
                        "trader_timeframe": output.timeframe,
                    },
                    "outcome_evaluation": _outcome_payload(
                        trade=None,
                        execution=execution,
                        signal_index=index,
                        closed_index=closed_index,
                        risk_fraction=None,
                    ),
                }
            )
            continue

        setup = output.setup
        if setup is None:
            raise ConditionalMarketStateObservationError(
                "SETUP decision is missing setup geometry"
            )
        entry = setup.entry_price
        risk_distance = abs(entry - setup.invalidation_price)
        reward_distance = abs(setup.take_profit_price - entry)
        risk_fraction = risk_distance / entry
        reward_risk_multiple = (
            None if risk_distance <= 0 else reward_distance / risk_distance
        )
        trade, _consumed = _model_trade(
            trader_code=trader_code,
            series=execution,
            signal_index=index,
            side=setup.side,
            entry=entry,
            stop=setup.invalidation_price,
            target=setup.take_profit_price,
        )
        _record_observation(
            {
                "event_fingerprint": event_id,
                "trader_code": trader_code,
                "market": symbol,
                "decision_time_state": state,
                "decision": {
                    "status": output.decision.value,
                    "abstain_reason": None,
                    "side": setup.side.value,
                    "setup_reason": setup.entry_reason,
                    "trader_session": output.session,
                    "trader_timeframe": output.timeframe,
                    "entry_price": format(entry, "f"),
                    "stop_loss": format(setup.invalidation_price, "f"),
                    "take_profit": format(setup.take_profit_price, "f"),
                    "risk_fraction": format(risk_fraction, "f"),
                    "reward_risk_multiple": (
                        None
                        if reward_risk_multiple is None
                        else format(reward_risk_multiple, "f")
                    ),
                },
                "outcome_evaluation": _outcome_payload(
                    trade=trade,
                    execution=execution,
                    signal_index=index,
                    closed_index=closed_index,
                    risk_fraction=risk_fraction,
                ),
            }
        )

    surface_payloads = {
        "|".join(dimensions): surface.payload()
        for dimensions, surface in surfaces.items()
    }
    edge_state_index: dict[str, list[dict[str, object]]] = {
        "FAVORABLE_EXPLORATORY": [],
        "ADVERSE_EXPLORATORY": [],
        "MIXED_UNCERTAIN": [],
        "INSUFFICIENT_EVIDENCE": [],
    }
    for surface_name, surface_payload in surface_payloads.items():
        cells = cast(list[dict[str, object]], surface_payload["cells"])
        for cell in cells:
            evidence_state = str(cell["evidence_state"])
            edge_state_index[evidence_state].append(
                {
                    "surface": surface_name,
                    "conditions": cell["conditions"],
                    "opportunity_count": cell["opportunity_count"],
                    "filled_count": cell["filled_count"],
                    "outcomes": cell["outcomes"],
                }
            )

    return {
        "trader_code": trader_code,
        "trader_version": cast(_ConfiguredEvaluator, evaluator).version,
        "config_fingerprint": _fingerprint(cast(_ConfiguredEvaluator, evaluator)),
        "parameters": dict(_parameters(cast(_ConfiguredEvaluator, evaluator))),
        "methodology_identity": _methodology_payload(
            cast(_ConfiguredEvaluator, evaluator)
        ),
        "execution_period": execution_period,
        "decision_opportunity_count": max(0, len(execution) - 1),
        "context_unavailable_count": context_unavailable,
        "decision_counts": dict(sorted(decision_counts.items())),
        "post_decision_diagnostics": {
            "oracle_only": True,
            "abstention_with_any_forward_up_move_count": abstention_forward_up_count,
            "abstention_with_any_forward_down_move_count": (
                abstention_forward_down_count
            ),
            "abstention_with_ge_2x_recent_range_move_count": (
                abstention_large_move_count
            ),
            "stopped_after_positive_mfe_count": stopped_after_positive_mfe_count,
            "stopped_after_at_least_one_r_mfe_count": stopped_after_one_r_mfe_count,
            "trailing_or_exit_policy_not_applied": True,
        },
        "observation_stream": {
            "format": "canonical-json-lines-v1",
            "row_count": observation_count,
            "sha256": observation_hasher.hexdigest(),
            "separate_artifact_supported": True,
        },
        "conditional_surfaces": surface_payloads,
        "edge_state_index": edge_state_index,
        "surface_policy": {
            "standard_surfaces": [list(item) for item in STANDARD_SURFACES],
            "all_labels_exploratory": True,
            "fresh_holdout_required_for_promotion": True,
            "combinatorial_mining_does_not_certify": True,
        },
    }
