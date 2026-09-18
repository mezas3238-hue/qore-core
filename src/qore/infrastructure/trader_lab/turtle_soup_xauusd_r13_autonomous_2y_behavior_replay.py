"""R13 autonomous 2Y behavior replay for Turtle Soup XAUUSD.

Purpose
-------
Observe what the trader does when allowed to operate its full methodology over
two complete recent years of already-consumed XAUUSD evidence.

This is NOT a 31-candidate replay. Every causal Turtle Soup setup in
[2024-09-17, 2026-09-17) is presented to the trader.

Autonomy policy
---------------
* CIBO/R3 chooses among causally available entry/target routes.
* Protected Swing remains the exact structural stop.
* Active DOL remains the structural target.
* R11 situation intelligence is evaluated before execution.
* Only KNOWN_INVALID causes intelligence-driven abstention.
* CONFLICTED, UNKNOWN and STRUCTURALLY_VALID_CANDIDATE remain executable.
* Natural no-route, no-fill and single-position constraints remain part of
  market behavior, not external performance filters.
* No date/year is used as a trading feature; dates only define this audit
  window and diagnostic grouping.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any, cast

from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r3_causal_regime_forensics as causal,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r3_cibo_journey as r3,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r3_cibo_journey_binding_repair as binding_repair,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r5_regime_journey_validity_forensics as r5,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r9_causal_break_discriminator as r9,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r9_cisd_sequence_forensics as cisd,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r9_liquidity_significance_forensics as liquidity,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r10_protected_swing_causality_forensics as ps,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r11_situation_recognition_engine as intelligence,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r11_situation_recognition_lab as recognition_lab,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    SourceCandle,
    build_daily,
    build_h1,
    build_h4,
)

IDENTITY = "TURTLE_SOUP_XAUUSD_R13_AUTONOMOUS_2Y_BEHAVIOR_REPLAY_V1"
EVAL_OPEN = datetime(2024, 9, 17, tzinfo=UTC)
EVAL_CLOSE = datetime(2026, 9, 17, tzinfo=UTC)
WINDOW_LABEL = "2024-09-17_2026-09-17"
EVIDENCE_STATUS = (
    "CONSUMED_2Y_AUTONOMOUS_BEHAVIOR_REPLAY_NOT_FRESH_HOLDOUT"
)

EXECUTABLE_STATES = {
    intelligence.SituationState.STRUCTURALLY_VALID_CANDIDATE,
    intelligence.SituationState.CONFLICTED,
    intelligence.SituationState.UNKNOWN,
}
TARGET_EXIT_REASONS = {"TARGET", "GAP_TARGET_CAPPED"}
STOP_EXIT_REASONS = {"STOP", "GAP_STOP", "STOP_FIRST"}


def _decimal_summary(values: Sequence[Decimal]) -> dict[str, Any]:
    if not values:
        return {
            "n": 0,
            "min": None,
            "median": None,
            "mean": None,
            "max": None,
        }
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "min": str(ordered[0]),
        "median": str(median(ordered)),
        "mean": str(sum(ordered, Decimal(0)) / Decimal(len(ordered))),
        "max": str(ordered[-1]),
    }


def _duration_minutes(start: datetime, end: datetime) -> Decimal:
    return Decimal(str((end - start).total_seconds())) / Decimal(60)


def _trade_geometry(trade: r3.RoutedTrade) -> dict[str, Any]:
    risk_price = abs(trade.entry - trade.stop)
    reward_price = abs(trade.target - trade.entry)
    rr = None if risk_price <= 0 else reward_price / risk_price
    stop_entry_fraction = (
        None if trade.entry == 0 else risk_price / abs(trade.entry)
    )
    target_entry_fraction = (
        None if trade.entry == 0 else reward_price / abs(trade.entry)
    )
    return {
        "risk_price": risk_price,
        "reward_price": reward_price,
        "initial_rr": rr,
        "stop_entry_fraction": stop_entry_fraction,
        "target_entry_fraction": target_entry_fraction,
        "duration_minutes": _duration_minutes(trade.entry_at, trade.exit_at),
    }


def _prepare_recognition_context(
    evidence: Any,
) -> dict[str, Any]:
    h1 = build_h1(evidence.bars)
    h4 = build_h4(evidence.bars)
    daily = build_daily(h4)
    frames: dict[str, Sequence[SourceCandle]] = {"H1": h1, "H4": h4}
    frame_indexes = {
        timeframe: {
            candle.opened_at: index for index, candle in enumerate(candles)
        }
        for timeframe, candles in frames.items()
    }
    frame_by_open = {
        timeframe: {candle.opened_at: candle for candle in candles}
        for timeframe, candles in frames.items()
    }
    h1_opens = tuple(candle.opened_at for candle in h1)
    h4_opens = tuple(candle.opened_at for candle in h4)
    d1_opens = tuple(candle.opened_at for candle in daily)
    d1_regime = r5._aggregate(evidence.bars, "D1")
    h4_regime = r5._aggregate(evidence.bars, "H4")
    return {
        "h1": h1,
        "h4": h4,
        "daily": daily,
        "frames": frames,
        "frame_indexes": frame_indexes,
        "frame_by_open": frame_by_open,
        "h1_opens": h1_opens,
        "h4_opens": h4_opens,
        "d1_opens": d1_opens,
        "d1_regime": d1_regime,
        "h4_regime": h4_regime,
    }


def _assess(
    *,
    setup: r3.Setup,
    trade: r3.RoutedTrade,
    evidence: Any,
    opens: Sequence[datetime],
    episodes: dict[str, list[r3.TargetCandidate]],
    ctx: dict[str, Any],
) -> tuple[intelligence.SituationAssessment, dict[str, Any]]:
    base = causal._record(setup, trade, evidence.bars, opens)
    base.update(
        r5._regime_features(
            base,
            ctx["d1_regime"],
            ctx["h4_regime"],
        )
    )

    timeframe = setup.context.timeframe
    c1 = ctx["frame_by_open"][timeframe].get(
        setup.context.signal.c1_opened_at
    )
    if c1 is None:
        raise ValueError("R13 missing C1 for recognition")

    target_rows = episodes.get(trade.episode_id)
    if not target_rows:
        raise ValueError("R13 missing target episode for recognition")

    prior20 = r9._mean_prior_source_range(
        ctx["frames"][timeframe],
        ctx["frame_indexes"][timeframe],
        setup.source.opened_at,
    )

    row: dict[str, Any] = dict(base)
    row["timeframe"] = timeframe
    row["side"] = setup.context.signal.side.value
    row.update(
        r9._continuous_record(
            setup,
            trade,
            c1,
            prior20,
            ctx["h1"],
            ctx["h1_opens"],
            ctx["h4"],
            ctx["h4_opens"],
            ctx["d1_regime"],
            ctx["h4_regime"],
            target_rows,
        )
    )
    row.update(
        liquidity._features(
            setup,
            c1,
            ctx["frames"],
            ctx["frame_indexes"],
            ctx["h1"],
            ctx["h4"],
            ctx["daily"],
            ctx["h4_opens"],
            ctx["d1_opens"],
        )
    )
    row.update(cisd._sequence_features(setup, c1))
    row.update(ps._ps_features(setup, trade))

    assessment = intelligence.assess_situation(
        recognition_lab._build_observation(row)
    )
    return assessment, row


def _stat(trades: Sequence[r3.RoutedTrade], attr: str) -> dict[str, Any]:
    return r3._stat(trades, attr)


def _group_stats(
    executed: Sequence[dict[str, Any]],
    key: str,
) -> dict[str, Any]:
    grouped: dict[str, list[r3.RoutedTrade]] = defaultdict(list)
    for item in executed:
        grouped[str(item[key])].append(item["trade"])
    return {
        name: {
            "primary_005r": _stat(rows, "primary_net_r"),
            "stress_010r": _stat(rows, "stress_net_r"),
            "gross": _stat(rows, "gross_r"),
        }
        for name, rows in sorted(grouped.items())
    }


def _year_stats(executed: Sequence[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[r3.RoutedTrade]] = defaultdict(list)
    for item in executed:
        grouped[str(item["trade"].entry_at.year)].append(item["trade"])
    return {
        year: {
            "primary_005r": _stat(rows, "primary_net_r"),
            "stress_010r": _stat(rows, "stress_net_r"),
            "gross": _stat(rows, "gross_r"),
        }
        for year, rows in sorted(grouped.items())
    }


def _json_trade(
    trade: r3.RoutedTrade,
    *,
    assessment: intelligence.SituationAssessment,
    row: dict[str, Any],
) -> dict[str, Any]:
    raw = asdict(trade)
    converted = {
        key: (
            value.isoformat()
            if isinstance(value, datetime)
            else str(value)
            if isinstance(value, Decimal)
            else value
        )
        for key, value in raw.items()
    }
    geometry = _trade_geometry(trade)
    converted.update(
        {
            "intelligence_state": assessment.state.value,
            "intelligence_mechanism": assessment.mechanism_code,
            "intelligence_evidence_grade": assessment.evidence_grade.value,
            "knowledge_claim_codes": list(assessment.knowledge_claim_codes),
            "initial_rr": (
                None
                if geometry["initial_rr"] is None
                else str(geometry["initial_rr"])
            ),
            "risk_price": str(geometry["risk_price"]),
            "reward_price": str(geometry["reward_price"]),
            "stop_entry_fraction": (
                None
                if geometry["stop_entry_fraction"] is None
                else str(geometry["stop_entry_fraction"])
            ),
            "target_entry_fraction": (
                None
                if geometry["target_entry_fraction"] is None
                else str(geometry["target_entry_fraction"])
            ),
            "duration_minutes": str(geometry["duration_minutes"]),
            "raid_depth_source_fraction": str(
                row["raid_depth_source_fraction"]
            ),
            "cisd_progress_exact": str(row["cisd_progress_exact"]),
            "protected_risk_source_fraction": str(
                row["protected_risk_source_fraction_exact"]
            ),
        }
    )
    return converted


def run(
    source_root: Path,
    target_root: Path,
    output: Path,
) -> dict[str, Any]:
    evidence, provenance = r3.journey.load_raw_m5(source_root)
    if evidence.symbol != r3.SYMBOL:
        raise ValueError("R13 expected XAUUSD")
    if int(provenance["retained_bars"]) != 707716:
        raise ValueError("R13 unexpected retained bar count")

    episodes, source_index = binding_repair._load_targets_fail_closed(target_root)

    original_open, original_close = r3.r1.EVAL_OPEN, r3.r1.EVAL_CLOSE
    try:
        r3.r1.EVAL_OPEN = r3.EVAL_OPEN
        r3.r1.EVAL_CLOSE = r3.EVAL_CLOSE
        setups, funnel = r3._build_setups(evidence)
    finally:
        r3.r1.EVAL_OPEN, r3.r1.EVAL_CLOSE = original_open, original_close

    opens = tuple(bar.opened_at for bar in evidence.bars)
    all_rows: list[
        tuple[
            r3.Setup,
            dict[
                tuple[str, str],
                tuple[Decimal | None, r3.RoutedTrade | None, str],
            ],
        ]
    ] = []
    unmatched = 0

    for setup in setups:
        signal = setup.context.signal
        episode_id = source_index.get(
            (
                signal.cisd_at,
                signal.side.value,
                setup.context.timeframe,
                signal.target,
            )
        )
        if episode_id is None:
            unmatched += 1
            continue
        outcomes = {
            action: r3._simulate(
                setup,
                episodes[episode_id],
                evidence,
                opens,
                action,
            )
            for action in r3.ACTIONS
        }
        all_rows.append((setup, outcomes))

    router = r3._fit_router(all_rows)
    recognition_context = _prepare_recognition_context(evidence)

    eval_rows = [
        (setup, outcomes)
        for setup, outcomes in all_rows
        if EVAL_OPEN <= setup.context.signal.entry_at < EVAL_CLOSE
    ]

    decisions: list[dict[str, Any]] = []
    executed: list[dict[str, Any]] = []
    decision_counts: Counter[str] = Counter()
    state_counts: Counter[str] = Counter()
    route_counts: Counter[str] = Counter()
    entry_mode_counts: Counter[str] = Counter()
    target_route_counts: Counter[str] = Counter()
    exit_reason_counts: Counter[str] = Counter()

    busy_until = EVAL_OPEN

    for setup, outcomes in eval_rows:
        action, outcome = r3._choose(setup, outcomes, router)
        if action is None or outcome is None:
            decision_counts["ABSTAIN_NO_CAUSALLY_AVAILABLE_ROUTE"] += 1
            decisions.append(
                {
                    "setup_at": setup.context.signal.entry_at.isoformat(),
                    "decision": "ABSTAIN_NO_CAUSALLY_AVAILABLE_ROUTE",
                    "intelligence_state": None,
                }
            )
            continue

        route_counts["|".join(action)] += 1
        _value, trade, reason = outcome
        if trade is None:
            decision = f"ABSTAIN_{reason}"
            decision_counts[decision] += 1
            decisions.append(
                {
                    "setup_at": setup.context.signal.entry_at.isoformat(),
                    "decision": decision,
                    "intelligence_state": None,
                    "route": "|".join(action),
                }
            )
            continue

        assessment, recognition_row = _assess(
            setup=setup,
            trade=trade,
            evidence=evidence,
            opens=opens,
            episodes=episodes,
            ctx=recognition_context,
        )
        state_counts[assessment.state.value] += 1

        if assessment.state is intelligence.SituationState.KNOWN_INVALID:
            decision_counts["ABSTAIN_KNOWN_INVALID"] += 1
            decisions.append(
                {
                    "setup_at": setup.context.signal.entry_at.isoformat(),
                    "entry_at": trade.entry_at.isoformat(),
                    "decision": "ABSTAIN_KNOWN_INVALID",
                    "intelligence_state": assessment.state.value,
                    "mechanism": assessment.mechanism_code,
                    "route": "|".join(action),
                }
            )
            continue

        if assessment.state not in EXECUTABLE_STATES:
            raise ValueError(
                f"R13 unexpected non-executable state: {assessment.state}"
            )

        if trade.entry_at < busy_until:
            decision_counts["ABSTAIN_SINGLE_POSITION_BUSY"] += 1
            decisions.append(
                {
                    "setup_at": setup.context.signal.entry_at.isoformat(),
                    "entry_at": trade.entry_at.isoformat(),
                    "decision": "ABSTAIN_SINGLE_POSITION_BUSY",
                    "intelligence_state": assessment.state.value,
                    "mechanism": assessment.mechanism_code,
                    "route": "|".join(action),
                }
            )
            continue

        decision_counts["EXECUTE"] += 1
        entry_mode_counts[trade.entry_mode] += 1
        target_route_counts[trade.target_route] += 1
        exit_reason_counts[trade.exit_reason] += 1
        busy_until = trade.exit_at

        executed.append(
            {
                "trade": trade,
                "intelligence_state": assessment.state.value,
                "intelligence_mechanism": assessment.mechanism_code,
                "assessment": assessment,
                "recognition_row": recognition_row,
            }
        )
        decisions.append(
            {
                "setup_at": setup.context.signal.entry_at.isoformat(),
                "entry_at": trade.entry_at.isoformat(),
                "decision": "EXECUTE",
                "intelligence_state": assessment.state.value,
                "mechanism": assessment.mechanism_code,
                "route": "|".join(action),
                "episode_id": trade.episode_id,
            }
        )

    trades = [item["trade"] for item in executed]
    geometries = [_trade_geometry(trade) for trade in trades]

    target_hits = sum(
        1 for trade in trades if trade.exit_reason in TARGET_EXIT_REASONS
    )
    stop_hits = sum(
        1 for trade in trades if trade.exit_reason in STOP_EXIT_REASONS
    )
    time_exits = sum(1 for trade in trades if trade.exit_reason == "TIME_24H")

    payload = {
        "schema": "qore.turtle_soup_xauusd_r13.autonomous_2y_behavior.v1",
        "identity": IDENTITY,
        "symbol": r3.SYMBOL,
        "evidence_status": EVIDENCE_STATUS,
        "window": {
            "open": EVAL_OPEN.isoformat(),
            "close": EVAL_CLOSE.isoformat(),
            "label": WINDOW_LABEL,
            "duration_years": 2,
        },
        "reproduction": {
            "retained_bars": provenance["retained_bars"],
            "setup_pool_10y": len(setups),
            "matched_rows_10y": len(all_rows),
            "unmatched_10y": unmatched,
            "ambiguous_source_opposite_keys_fail_closed": binding_repair._LAST_AMBIGUOUS_KEYS,
            "setups_presented_2y": len(eval_rows),
        },
        "autonomy_contract": {
            "all_causal_setups_in_window_presented": True,
            "restricted_to_r11_31_candidates": False,
            "restricted_to_positive_state": False,
            "known_invalid_internal_abstention": True,
            "conflicted_remains_executable": True,
            "unknown_remains_executable": True,
            "structurally_valid_candidate_remains_executable": True,
            "entry_router": (
                "R3_CIBO_CAUSAL_ROUTE_SELECTION_NO_POSITIVE_SCORE_TRADE_GATE"
            ),
            "stop": "CAUSAL_CISD_PROTECTED_SWING_EXACT_NO_OFFSET",
            "target": "ACTIVE_UNTOUCHED_CIBO_DOL_KNOWN_AT_DECISION",
            "single_position_constraint": True,
            "max_lifetime": "24H",
            "calendar_year_used_as_trade_feature": False,
            "post_entry_data_used_for_decision": False,
            "ambiguous_source_bindings_fail_closed": True,
            "fresh_holdout_used": False,
        },
        "behavior": {
            "decision_counts": dict(decision_counts),
            "intelligence_state_counts_on_filled_candidates": dict(state_counts),
            "route_counts": dict(route_counts),
            "entry_mode_counts_executed": dict(entry_mode_counts),
            "target_route_counts_executed": dict(target_route_counts),
            "exit_reason_counts": dict(exit_reason_counts),
            "executed_trades": len(trades),
            "target_hits": target_hits,
            "stop_hits": stop_hits,
            "time_24h_exits": time_exits,
            "target_hit_fraction": (
                None
                if not trades
                else str(Decimal(target_hits) / Decimal(len(trades)))
            ),
            "stop_hit_fraction": (
                None
                if not trades
                else str(Decimal(stop_hits) / Decimal(len(trades)))
            ),
        },
        "economics": {
            "gross": _stat(trades, "gross_r"),
            "primary_005r": _stat(trades, "primary_net_r"),
            "stress_010r": _stat(trades, "stress_net_r"),
        },
        "geometry": {
            "initial_rr": _decimal_summary(
                [
                    cast(Decimal, item["initial_rr"])
                    for item in geometries
                    if item["initial_rr"] is not None
                ]
            ),
            "risk_price": _decimal_summary(
                [cast(Decimal, item["risk_price"]) for item in geometries]
            ),
            "reward_price": _decimal_summary(
                [cast(Decimal, item["reward_price"]) for item in geometries]
            ),
            "stop_entry_fraction": _decimal_summary(
                [
                    cast(Decimal, item["stop_entry_fraction"])
                    for item in geometries
                    if item["stop_entry_fraction"] is not None
                ]
            ),
            "target_entry_fraction": _decimal_summary(
                [
                    cast(Decimal, item["target_entry_fraction"])
                    for item in geometries
                    if item["target_entry_fraction"] is not None
                ]
            ),
            "duration_minutes": _decimal_summary(
                [
                    cast(Decimal, item["duration_minutes"])
                    for item in geometries
                ]
            ),
        },
        "by_intelligence_state": _group_stats(
            executed, "intelligence_state"
        ),
        "by_intelligence_mechanism": _group_stats(
            executed, "intelligence_mechanism"
        ),
        "by_side": {
            side: {
                "primary_005r": _stat(
                    [item["trade"] for item in executed if item["trade"].side == side],
                    "primary_net_r",
                ),
                "stress_010r": _stat(
                    [item["trade"] for item in executed if item["trade"].side == side],
                    "stress_net_r",
                ),
            }
            for side in sorted({item["trade"].side for item in executed})
        },
        "by_source_timeframe": {
            timeframe: {
                "primary_005r": _stat(
                    [
                        item["trade"]
                        for item in executed
                        if item["trade"].source_timeframe == timeframe
                    ],
                    "primary_net_r",
                ),
                "stress_010r": _stat(
                    [
                        item["trade"]
                        for item in executed
                        if item["trade"].source_timeframe == timeframe
                    ],
                    "stress_net_r",
                ),
            }
            for timeframe in sorted(
                {item["trade"].source_timeframe for item in executed}
            )
        },
        "by_target_route": {
            route: {
                "primary_005r": _stat(
                    [
                        item["trade"]
                        for item in executed
                        if item["trade"].target_route == route
                    ],
                    "primary_net_r",
                ),
                "stress_010r": _stat(
                    [
                        item["trade"]
                        for item in executed
                        if item["trade"].target_route == route
                    ],
                    "stress_net_r",
                ),
            }
            for route in sorted(
                {item["trade"].target_route for item in executed}
            )
        },
        "by_entry_mode": {
            mode: {
                "primary_005r": _stat(
                    [
                        item["trade"]
                        for item in executed
                        if item["trade"].entry_mode == mode
                    ],
                    "primary_net_r",
                ),
                "stress_010r": _stat(
                    [
                        item["trade"]
                        for item in executed
                        if item["trade"].entry_mode == mode
                    ],
                    "stress_net_r",
                ),
            }
            for mode in sorted({item["trade"].entry_mode for item in executed})
        },
        "by_year_diagnostic": _year_stats(executed),
        "funnel_10y_setup_reproduction": funnel,
        "governance": {
            "research_only": True,
            "fresh_holdout_consumed": False,
            "candidate_promoted": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "autonomous-2y-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "autonomous-2y-trades.json").write_text(
        json.dumps(
            [
                _json_trade(
                    item["trade"],
                    assessment=item["assessment"],
                    row=item["recognition_row"],
                )
                for item in executed
            ],
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    (output / "autonomous-2y-decisions.json").write_text(
        json.dumps(decisions, indent=2, sort_keys=True) + "\n"
    )
    (output / "router.json").write_text(
        json.dumps(router, indent=2, sort_keys=True) + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module SOURCE_ROOT TARGET_ROOT OUTPUT_DIR")
    payload = run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
