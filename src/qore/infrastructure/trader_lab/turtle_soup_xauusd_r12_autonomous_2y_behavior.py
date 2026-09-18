"""R12: autonomous two-year behaviour replay for the intelligent XAUUSD trader.

Research-only consumed-evidence experiment. Every causally routable Turtle Soup
setup remains simulation-eligible unless R11 recognizes the exact established
KNOWN_INVALID anatomy. CONFLICTED, UNKNOWN and STRUCTURALLY_VALID_CANDIDATE
remain eligible for this behaviour experiment; that is not live permission.

The sequence is recomputed before the single-position constraint, so an
intelligence abstention can free capital for a later setup.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import cibo_market_atlas_journey_extractor_v1 as journey
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r1 as r1
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_causal_regime_forensics as causal
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey_binding_repair as repair
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r5_regime_journey_validity_forensics as r5
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r9_causal_break_discriminator as r9
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r9_cisd_sequence_forensics as cisd
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r9_liquidity_significance_forensics as liquidity
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r10_protected_swing_causality_forensics as ps
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r11_situation_recognition_engine as r11
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r11_situation_recognition_lab as r11lab
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import SourceCandle, build_daily, build_h1, build_h4

IDENTITY = "TURTLE_SOUP_XAUUSD_R12_AUTONOMOUS_2Y_BEHAVIOR_V2"
OPEN = datetime(2024, 9, 17, tzinfo=UTC)
CLOSE = datetime(2026, 9, 17, tzinfo=UTC)


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _max_losing_streak(values: Sequence[Decimal]) -> int:
    best = current = 0
    for value in values:
        if value < 0:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def _stats(rows: list[dict[str, Any]], extra_friction_r: Decimal = Decimal(0)) -> dict[str, Any]:
    rs = [_d(row["primary_net_r"]) - extra_friction_r for row in rows]
    gross = [_d(row["gross_r"]) for row in rows]
    if not rs:
        return {"trades": 0}
    wins = sum(x > 0 for x in rs)
    losses = sum(x < 0 for x in rs)
    total = sum(rs, Decimal(0))
    peak = equity = dd = Decimal(0)
    for value in rs:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    gp = sum((x for x in rs if x > 0), Decimal(0))
    gl = -sum((x for x in rs if x < 0), Decimal(0))
    stop_dist = [abs(_d(row["entry"]) - _d(row["stop"])) for row in rows]
    target_dist = [abs(_d(row["target"]) - _d(row["entry"])) for row in rows]
    planned_rr = [t / s for t, s in zip(target_dist, stop_dist, strict=True) if s > 0]
    durations: list[Decimal] = []
    for row in rows:
        if row.get("entry_at") is None or row.get("exit_at") is None:
            continue
        delta = datetime.fromisoformat(str(row["exit_at"])) - datetime.fromisoformat(str(row["entry_at"]))
        durations.append(Decimal(str(delta.total_seconds())) / Decimal(60))
    target_exits = sum(1 for row in rows if "TARGET" in str(row.get("exit_reason", "")).upper())
    stop_exits = sum(1 for row in rows if "STOP" in str(row.get("exit_reason", "")).upper())
    return {
        "trades": len(rows),
        "wins": wins,
        "losses": losses,
        "flats": len(rows) - wins - losses,
        "win_rate": str(Decimal(wins) / Decimal(len(rows))),
        "total_primary_r": str(total),
        "mean_primary_r": str(total / Decimal(len(rows))),
        "profit_factor": None if gl == 0 else str(gp / gl),
        "max_drawdown_r": str(dd),
        "max_losing_streak": _max_losing_streak(rs),
        "gross_total_r": str(sum(gross, Decimal(0))),
        "target_exits": target_exits,
        "stop_exits": stop_exits,
        "other_exits": len(rows) - target_exits - stop_exits,
        "target_exit_rate": str(Decimal(target_exits) / Decimal(len(rows))),
        "stop_exit_rate": str(Decimal(stop_exits) / Decimal(len(rows))),
        "median_stop_price_distance": str(sorted(stop_dist)[len(stop_dist) // 2]),
        "median_target_price_distance": str(sorted(target_dist)[len(target_dist) // 2]),
        "median_planned_rr": None if not planned_rr else str(sorted(planned_rr)[len(planned_rr) // 2]),
        "median_duration_minutes": None if not durations else str(sorted(durations)[len(durations) // 2]),
    }


def _pack(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "primary_0p05R": _stats(rows),
        "stress_0p10R": _stats(rows, Decimal("0.05")),
        "stress_0p15R": _stats(rows, Decimal("0.10")),
    }


def _group(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(row)
    return {name: _pack(items) for name, items in sorted(groups.items())}


def _in_window(at: datetime) -> bool:
    return OPEN <= at < CLOSE


def _recognition_context(evidence: Any) -> dict[str, Any]:
    h1 = build_h1(evidence.bars)
    h4 = build_h4(evidence.bars)
    daily = build_daily(h4)
    frames: dict[str, Sequence[SourceCandle]] = {"H1": h1, "H4": h4}
    return {
        "frames": frames,
        "frame_indexes": {tf: {c.opened_at: i for i, c in enumerate(cs)} for tf, cs in frames.items()},
        "frame_by_open": {tf: {c.opened_at: c for c in cs} for tf, cs in frames.items()},
        "h1": h1,
        "h4": h4,
        "daily": daily,
        "h1_opens": tuple(c.opened_at for c in h1),
        "h4_opens": tuple(c.opened_at for c in h4),
        "d1_opens": tuple(c.opened_at for c in daily),
        "d1_regime": r5._aggregate(evidence.bars, "D1"),
        "h4_regime": r5._aggregate(evidence.bars, "H4"),
    }


def _assess(
    setup: r3.Setup,
    trade: r3.RoutedTrade,
    target_rows: Sequence[r3.TargetCandidate],
    evidence: Any,
    opens: Sequence[datetime],
    rc: dict[str, Any],
) -> tuple[r11.SituationAssessment, dict[str, Any]]:
    base = causal._record(setup, trade, evidence.bars, opens)
    base.update(r5._regime_features(base, rc["d1_regime"], rc["h4_regime"]))
    timeframe = setup.context.timeframe
    c1 = rc["frame_by_open"][timeframe].get(setup.context.signal.c1_opened_at)
    if c1 is None:
        raise ValueError("R12 autonomous replay missing C1")
    prior20 = r9._mean_prior_source_range(rc["frames"][timeframe], rc["frame_indexes"][timeframe], setup.source.opened_at)
    row: dict[str, Any] = dict(base)
    row["timeframe"] = timeframe
    row["side"] = setup.context.signal.side.value
    row.update(r9._continuous_record(
        setup, trade, c1, prior20,
        rc["h1"], rc["h1_opens"], rc["h4"], rc["h4_opens"],
        rc["d1_regime"], rc["h4_regime"], target_rows,
    ))
    row.update(liquidity._features(
        setup, c1, rc["frames"], rc["frame_indexes"],
        rc["h1"], rc["h4"], rc["daily"], rc["h4_opens"], rc["d1_opens"],
    ))
    row.update(cisd._sequence_features(setup, c1))
    row.update(ps._ps_features(setup, trade))
    assessment = r11.assess_situation(r11lab._build_observation(row))
    return assessment, row


def _policy(assessment: r11.SituationAssessment) -> tuple[bool, str]:
    if assessment.state is r11.SituationState.KNOWN_INVALID:
        return False, "ABSTAIN_INTELLIGENCE_KNOWN_INVALID"
    if assessment.state is r11.SituationState.STRUCTURALLY_VALID_CANDIDATE:
        return True, "OPERATE_RESEARCH_VALID_CANDIDATE"
    if assessment.state is r11.SituationState.CONFLICTED:
        return True, "OPERATE_CONFLICT_RECORDED"
    return True, "OPERATE_UNKNOWN_OBSERVATION_MODE"


def _json_trade(trade: r3.RoutedTrade) -> dict[str, Any]:
    return causal._json_trade(trade)


def run(source_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(source_root)
    if evidence.symbol != r3.SYMBOL or int(provenance["retained_bars"]) != 707716:
        raise ValueError("unexpected XAUUSD 10Y corpus")

    episodes, source_index = repair._load_targets_fail_closed(target_root)
    original_open, original_close = r1.EVAL_OPEN, r1.EVAL_CLOSE
    try:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = r3.EVAL_OPEN, r3.EVAL_CLOSE
        setups, funnel = r3._build_setups(evidence)
    finally:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = original_open, original_close
    opens = tuple(bar.opened_at for bar in evidence.bars)

    routed: list[tuple[
        r3.Setup,
        Sequence[r3.TargetCandidate],
        dict[tuple[str, str], tuple[Decimal | None, r3.RoutedTrade | None, str]],
    ]] = []
    unmatched = 0
    for setup in setups:
        signal = setup.context.signal
        episode_id = source_index.get((signal.cisd_at, signal.side.value, setup.context.timeframe, signal.target))
        if episode_id is None:
            unmatched += 1
            continue
        target_rows = episodes[episode_id]
        outcomes = {action: r3._simulate(setup, target_rows, evidence, opens, action) for action in r3.ACTIONS}
        routed.append((setup, target_rows, outcomes))

    router = r3._fit_router([(setup, outcomes) for setup, _targets, outcomes in routed])

    baseline_selected: list[r3.RoutedTrade] = []
    baseline_busy_until = r3.EVAL_OPEN
    for setup, _target_rows, outcomes in routed:
        _action, outcome = r3._choose(setup, outcomes, router)
        if outcome is None:
            continue
        _value, trade, _reason = outcome
        if trade is None or trade.entry_at < baseline_busy_until:
            continue
        baseline_selected.append(trade)
        baseline_busy_until = trade.exit_at
    if len(baseline_selected) != 5885:
        raise ValueError(f"canonical R3 reproduction drift: {len(baseline_selected)} != 5885")

    rc = _recognition_context(evidence)
    executed: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    assessments: Counter[str] = Counter()
    intelligence_abstentions: Counter[str] = Counter()
    natural_abstentions: Counter[str] = Counter()
    route_counts: Counter[str] = Counter()
    busy_until = r3.EVAL_OPEN
    window_setup_count = 0
    window_assessed_fill_count = 0

    for setup, routed_targets, outcomes in routed:
        signal = setup.context.signal
        signal_in_window = _in_window(signal.entry_at)
        if signal_in_window:
            window_setup_count += 1

        action, outcome = r3._choose(setup, outcomes, router)
        if action is None or outcome is None:
            if signal_in_window:
                natural_abstentions["NO_CAUSALLY_AVAILABLE_ROUTE"] += 1
            continue
        route_name = "|".join(action)
        _value, trade, reason = outcome
        if trade is None:
            if signal_in_window:
                natural_abstentions[reason] += 1
            continue

        assessment, feature_row = _assess(setup, trade, routed_targets, evidence, opens, rc)
        if signal_in_window:
            assessments[assessment.state.value] += 1
            window_assessed_fill_count += 1

        eligible, behavior = _policy(assessment)
        decision = behavior
        if not eligible:
            if signal_in_window:
                intelligence_abstentions[assessment.mechanism_code] += 1
        elif trade.entry_at < busy_until:
            decision = "ABSTAIN_SINGLE_POSITION_BUSY"
            if signal_in_window:
                natural_abstentions["SINGLE_POSITION_BUSY"] += 1
        else:
            trade_row = _json_trade(trade)
            trade_row.update({
                "r11_state": assessment.state.value,
                "r11_mechanism": assessment.mechanism_code,
                "r11_engine_directive": assessment.directive.value,
                "research_behavior_decision": behavior,
                "selected_route": route_name,
                "structural_rr": feature_row.get("structural_rr"),
            })
            executed.append(trade_row)
            busy_until = trade.exit_at
            if _in_window(trade.entry_at):
                route_counts[route_name] += 1

        if signal_in_window:
            decisions.append({
                "signal_at": signal.entry_at.isoformat(),
                "trade_entry_at": trade.entry_at.isoformat(),
                "trade_exit_at": trade.exit_at.isoformat(),
                "side": trade.side,
                "source_timeframe": trade.source_timeframe,
                "entry_mode": trade.entry_mode,
                "target_route": trade.target_route,
                "entry": str(trade.entry),
                "stop": str(trade.stop),
                "target": str(trade.target),
                "planned_rr": feature_row.get("structural_rr"),
                "r11_state": assessment.state.value,
                "r11_mechanism": assessment.mechanism_code,
                "r11_engine_directive": assessment.directive.value,
                "research_behavior_decision": decision,
            })

    intelligent_2y = [row for row in executed if _in_window(datetime.fromisoformat(str(row["entry_at"])))]
    baseline_2y = [_json_trade(trade) for trade in baseline_selected if _in_window(trade.entry_at)]

    payload = {
        "schema": "qore.turtle_soup_xauusd_r12.autonomous_2y_behavior.v2",
        "identity": IDENTITY,
        "window": {"open": OPEN.isoformat(), "close": CLOSE.isoformat(), "years": 2},
        "evidence_status": "CONSUMED_2Y_AUTONOMOUS_INTELLIGENCE_BEHAVIOR_NOT_FRESH_HOLDOUT",
        "reproduction": {
            "retained_bars": int(provenance["retained_bars"]),
            "setups": len(setups),
            "routed_rows": len(routed),
            "unmatched": unmatched,
            "ambiguous_source_opposite_keys": repair._LAST_AMBIGUOUS_KEYS,
            "canonical_r3_trades": len(baseline_selected),
        },
        "freedom_contract": {
            "restricted_to_r11_positive_candidates": False,
            "known_invalid_is_only_r11_hard_abstention": True,
            "conflicted_simulation_eligible": True,
            "unknown_simulation_eligible": True,
            "structurally_valid_candidate_simulation_eligible": True,
            "simulation_eligibility_is_live_operating_permission": False,
            "external_side_filter": False,
            "external_timeframe_filter": False,
            "external_session_filter": False,
            "calendar_year_used_as_operating_rule": False,
            "pnl_used_as_operating_filter": False,
            "entry_owner": "R3_CIBO_JOURNEY_ROUTER",
            "stop_owner": "CAUSAL_CISD_PROTECTED_SWING",
            "target_owner": "R3_ACTIVE_CIBO_DOL_ROUTER",
            "single_position_constraint": True,
            "sequential_replay_recomputed_after_intelligence_abstention": True,
        },
        "two_year_behavior": {
            "setup_signals": window_setup_count,
            "assessed_fill_opportunities": window_assessed_fill_count,
            "executed_trades": len(intelligent_2y),
            "r11_state_assessments": dict(assessments),
            "executed_by_r11_state": dict(Counter(str(row["r11_state"]) for row in intelligent_2y)),
            "intelligence_abstentions": dict(intelligence_abstentions),
            "natural_abstentions": dict(natural_abstentions),
            "route_counts": dict(route_counts),
            "performance": _pack(intelligent_2y),
            "by_r11_state": _group(intelligent_2y, "r11_state"),
            "by_r11_mechanism": _group(intelligent_2y, "r11_mechanism"),
            "by_side": _group(intelligent_2y, "side"),
            "by_source_timeframe": _group(intelligent_2y, "source_timeframe"),
            "by_entry_mode": _group(intelligent_2y, "entry_mode"),
            "by_target_route": _group(intelligent_2y, "target_route"),
            "by_session": _group(intelligent_2y, "session_bucket"),
            "by_exit_reason": dict(Counter(row["exit_reason"] for row in intelligent_2y)),
        },
        "canonical_r3_same_window": {
            "executed_trades": len(baseline_2y),
            "performance": _pack(baseline_2y),
        },
        "comparison": {
            "trade_count_delta_vs_r3": len(intelligent_2y) - len(baseline_2y),
            "primary_total_r_delta_vs_r3": str(
                sum((_d(row["primary_net_r"]) for row in intelligent_2y), Decimal(0))
                - sum((_d(row["primary_net_r"]) for row in baseline_2y), Decimal(0))
            ),
            "note": "Difference includes sequential capital-release effects after intelligence abstentions, not post-hoc filtering.",
        },
        "funnel": funnel,
        "governance": {
            "research_behavior_replay_only": True,
            "fresh_holdout_consumed": False,
            "positive_candidate_promoted": False,
            "conflicted_promoted": False,
            "unknown_promoted": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "r12-autonomous-2y-report.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    (output / "r12-autonomous-2y-trades.json").write_text(json.dumps(intelligent_2y, indent=2, sort_keys=True) + "\n")
    (output / "r12-autonomous-2y-decisions.json").write_text(json.dumps(decisions, indent=2, sort_keys=True) + "\n")
    (output / "r12-canonical-r3-2y-trades.json").write_text(json.dumps(baseline_2y, indent=2, sort_keys=True) + "\n")
    return payload


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module SOURCE_ROOT TARGET_ROOT OUTPUT_DIR")
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])), sort_keys=True))


if __name__ == "__main__":
    main()
