"""R15 CIBO-first market brain for Turtle Soup XAUUSD.

Research-only architecture candidate over consumed evidence.

The key architectural change is causal ownership:
market -> CIBO context -> entry posture -> fill -> R11 structural assessment
-> DOL selection -> execution.

R3's learned PnL route score is NOT used. The brain reasons from structural
context available at the decision/fill time:
- Turtle Soup exact C2/CISD anatomy;
- session and weekday memory;
- FVG / exact equal liquidity context;
- raid, reclaim, CISD, Protected Swing and source-candle geometry;
- D1/H4 trend, efficiency, range expansion/compression and range location;
- the complete active CIBO DOL ladder known at fill.

Weekday/session and association-only CIBO memories are recorded as knowledge
context but are not hard operating filters. No PnL score, probability of
profit, year switch, post-entry feature, or fresh holdout is used.
"""
from __future__ import annotations

import bisect
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r13_autonomous_2y_behavior_replay as prior,
)
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r3_cibo_journey_binding_repair as repair,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r5_regime_journey_validity_forensics as r5,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r11_situation_recognition_engine as r11,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Side

IDENTITY = "TURTLE_SOUP_XAUUSD_R15_CIBO_FIRST_MARKET_BRAIN_V1"
EVAL_OPEN = datetime(2024, 9, 17, tzinfo=UTC)
EVAL_CLOSE = datetime(2026, 9, 17, tzinfo=UTC)

TARGET_EXIT_REASONS = {"TARGET", "GAP_TARGET_CAPPED"}
STOP_EXIT_REASONS = {"STOP", "GAP_STOP", "STOP_FIRST"}


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _candidate_route(row: r3.TargetCandidate) -> str:
    if row.kind == "SOURCE_OPPOSITE_BOUNDARY":
        return "SOURCE_OPPOSITE"
    if row.kind == "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY":
        return f"PRIOR_{row.timeframe}"
    if row.kind == "ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY":
        return f"SWING_{row.timeframe}"
    raise ValueError(f"unsupported CIBO target kind: {row.kind}")


def _all_active_targets(
    rows: Sequence[r3.TargetCandidate],
    *,
    at: datetime,
    side: Side,
    anchor: Decimal,
) -> list[r3.TargetCandidate]:
    active: list[r3.TargetCandidate] = []
    for row in rows:
        if row.known_at > at:
            continue
        if row.touch_at is not None and row.touch_at < at:
            continue
        ahead = row.level > anchor if side is Side.LONG else row.level < anchor
        if ahead:
            active.append(row)
    active.sort(key=lambda item: (abs(item.level - anchor), item.known_at, item.level))
    return active


def _distinct_target_ladder(
    rows: Sequence[r3.TargetCandidate],
    *,
    anchor: Decimal,
) -> list[r3.TargetCandidate]:
    result: list[r3.TargetCandidate] = []
    seen: set[Decimal] = set()
    for row in rows:
        distance = abs(row.level - anchor)
        if distance in seen:
            continue
        seen.add(distance)
        result.append(row)
    return result


def _with_trade(state: str) -> bool:
    return state.endswith("_with_trade")


def _against_trade(state: str) -> bool:
    return state.endswith("_against_trade")


def _persistent_with_trade(state: str) -> bool:
    return state == "persistent_with_trade"


def _market_posture(regime: dict[str, str]) -> str:
    d1 = regime["d1_trend_state_20"]
    h4 = regime["h4_trend_state_20"]
    d1_range = regime["d1_range_5v20"]
    h4_range = regime["h4_range_3v20"]

    both_compressed = (
        d1_range == "compressed<=0.75"
        and h4_range == "compressed<=0.75"
    )
    if _against_trade(d1) and _against_trade(h4):
        return "OPPOSED_TREND"
    if both_compressed or d1 == "choppy" or h4 == "choppy":
        return "RANGE_OR_COMPRESSION"
    if _with_trade(d1) and _with_trade(h4):
        if _persistent_with_trade(d1) or _persistent_with_trade(h4):
            return "EXPANSION_WITH_TRADE"
        return "DIRECTIONAL_WITH_TRADE"
    return "MIXED_CONTEXT"


def _entry_mode(setup: r3.Setup, posture: str) -> str:
    if posture in {"OPPOSED_TREND", "RANGE_OR_COMPRESSION"}:
        return "CISD_THRESHOLD_RETEST"
    if setup.context.cisd_progress_bucket == "q4:>0.75":
        return "CISD_THRESHOLD_RETEST"
    return "NEXT_SOURCE_OPEN"


def _target_index(posture: str, regime: dict[str, str]) -> int:
    if posture != "EXPANSION_WITH_TRADE":
        return 0
    if (
        regime["d1_range_5v20"] == "compressed<=0.75"
        or regime["h4_range_3v20"] == "compressed<=0.75"
    ):
        return 0
    # One-step extension only. No arbitrary fixed-R target is created.
    return 1


def _provisional_trade(
    setup: r3.Setup,
    *,
    entry_mode: str,
    entry_at: datetime,
    entry: Decimal,
    target: r3.TargetCandidate,
) -> r3.RoutedTrade:
    return r3.RoutedTrade(
        source_timeframe=setup.context.timeframe,
        side=setup.context.signal.side.value,
        entry_mode=entry_mode,
        target_route=_candidate_route(target),
        episode_id=target.episode_id,
        entry_at=entry_at,
        exit_at=entry_at,
        entry=entry,
        stop=setup.context.signal.protected_swing,
        target=target.level,
        target_kind=target.kind,
        target_timeframe=target.timeframe,
        gross_r=Decimal(0),
        primary_net_r=Decimal(0),
        stress_net_r=Decimal(0),
        exit_reason="PRE_ENTRY_REASONING",
        session_bucket=setup.context.signal.session_bucket,
        prior_body_alignment=setup.context.signal.prior_body_alignment,
    )


def _simulate_selected(
    setup: r3.Setup,
    *,
    entry_mode: str,
    entry_at: datetime,
    entry: Decimal,
    target_row: r3.TargetCandidate,
    evidence: Any,
    opens: Sequence[datetime],
) -> r3.RoutedTrade | None:
    side = setup.context.signal.side
    stop = setup.context.signal.protected_swing
    risk = entry - stop if side is Side.LONG else stop - entry
    reward = target_row.level - entry if side is Side.LONG else entry - target_row.level
    if risk <= 0 or reward <= 0:
        return None

    left = bisect.bisect_left(opens, entry_at)
    right = bisect.bisect_left(
        opens,
        min(entry_at + timedelta(hours=24), r3.EVAL_CLOSE),
    )
    path = evidence.bars[left:right]
    if not path:
        return None

    exit_at = path[-1].closed_at
    exit_price = path[-1].close
    reason = "TIME_24H"
    gross = (
        (exit_price - entry) / risk
        if side is Side.LONG
        else (entry - exit_price) / risk
    )

    for bar in path:
        if side is Side.LONG:
            if bar.open <= stop:
                exit_at, exit_price, reason, gross = (
                    bar.opened_at,
                    bar.open,
                    "GAP_STOP",
                    (bar.open - entry) / risk,
                )
                break
            if bar.open >= target_row.level:
                exit_at, exit_price, reason, gross = (
                    bar.opened_at,
                    target_row.level,
                    "GAP_TARGET_CAPPED",
                    reward / risk,
                )
                break
            stop_touch = bar.low <= stop
            target_touch = bar.high >= target_row.level
        else:
            if bar.open >= stop:
                exit_at, exit_price, reason, gross = (
                    bar.opened_at,
                    bar.open,
                    "GAP_STOP",
                    (entry - bar.open) / risk,
                )
                break
            if bar.open <= target_row.level:
                exit_at, exit_price, reason, gross = (
                    bar.opened_at,
                    target_row.level,
                    "GAP_TARGET_CAPPED",
                    reward / risk,
                )
                break
            stop_touch = bar.high >= stop
            target_touch = bar.low <= target_row.level

        if stop_touch and target_touch:
            exit_at, exit_price, reason, gross = (
                bar.closed_at,
                stop,
                "STOP_FIRST",
                Decimal(-1),
            )
            break
        if stop_touch:
            exit_at, exit_price, reason, gross = (
                bar.closed_at,
                stop,
                "STOP",
                Decimal(-1),
            )
            break
        if target_touch:
            exit_at, exit_price, reason, gross = (
                bar.closed_at,
                target_row.level,
                "TARGET",
                reward / risk,
            )
            break

    return r3.RoutedTrade(
        source_timeframe=setup.context.timeframe,
        side=side.value,
        entry_mode=entry_mode,
        target_route=_candidate_route(target_row),
        episode_id=target_row.episode_id,
        entry_at=entry_at,
        exit_at=exit_at,
        entry=entry,
        stop=stop,
        target=target_row.level,
        target_kind=target_row.kind,
        target_timeframe=target_row.timeframe,
        gross_r=gross,
        primary_net_r=gross - r3.PRIMARY_FRICTION_R,
        stress_net_r=gross - r3.STRESS_FRICTION_R,
        exit_reason=reason,
        session_bucket=setup.context.signal.session_bucket,
        prior_body_alignment=setup.context.signal.prior_body_alignment,
    )


def _stats(trades: Sequence[r3.RoutedTrade], attr: str = "primary_net_r") -> dict[str, Any]:
    return r3._stat(trades, attr)


def _group(
    executed: Sequence[dict[str, Any]],
    key: str,
) -> dict[str, Any]:
    grouped: dict[str, list[r3.RoutedTrade]] = defaultdict(list)
    for item in executed:
        grouped[str(item[key])].append(item["trade"])
    return {
        name: {
            "primary_005r": _stats(rows),
            "stress_010r": _stats(rows, "stress_net_r"),
            "gross": _stats(rows, "gross_r"),
        }
        for name, rows in sorted(grouped.items())
    }


def _json_trade(item: dict[str, Any]) -> dict[str, Any]:
    trade: r3.RoutedTrade = item["trade"]
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
    converted.update(
        {
            "brain_posture": item["brain_posture"],
            "intelligence_state": item["intelligence_state"],
            "intelligence_mechanism": item["intelligence_mechanism"],
            "target_ladder_rank": item["target_ladder_rank"],
            "weekday": item["weekday"],
            "session": item["session"],
            "fvg_before_entry": item["fvg_before_entry"],
            "exact_equal_liquidity": item["exact_equal_liquidity"],
            "d1_trend_state_20": item["regime"]["d1_trend_state_20"],
            "h4_trend_state_20": item["regime"]["h4_trend_state_20"],
            "d1_range_5v20": item["regime"]["d1_range_5v20"],
            "h4_range_3v20": item["regime"]["h4_range_3v20"],
            "d1_location_20": item["regime"]["d1_location_20"],
            "h4_location_20": item["regime"]["h4_location_20"],
        }
    )
    return converted


def run(source_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    evidence, provenance = r3.journey.load_raw_m5(source_root)
    if evidence.symbol != "XAUUSD" or int(provenance["retained_bars"]) != 707716:
        raise ValueError("unexpected XAUUSD source corpus")

    episodes, source_index = repair._load_targets_fail_closed(target_root)

    original_open, original_close = r3.r1.EVAL_OPEN, r3.r1.EVAL_CLOSE
    try:
        r3.r1.EVAL_OPEN, r3.r1.EVAL_CLOSE = r3.EVAL_OPEN, r3.EVAL_CLOSE
        setups, funnel = r3._build_setups(evidence)
    finally:
        r3.r1.EVAL_OPEN, r3.r1.EVAL_CLOSE = original_open, original_close

    opens = tuple(bar.opened_at for bar in evidence.bars)
    recognition_ctx = prior._prepare_recognition_context(evidence)
    d1 = recognition_ctx["d1_regime"]
    h4 = recognition_ctx["h4_regime"]

    decisions: list[dict[str, Any]] = []
    executed: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    state_counts: Counter[str] = Counter()
    posture_counts: Counter[str] = Counter()
    entry_counts: Counter[str] = Counter()
    target_rank_counts: Counter[str] = Counter()
    target_route_counts: Counter[str] = Counter()

    busy_until = EVAL_OPEN
    presented = 0
    matched = 0

    for setup in setups:
        signal = setup.context.signal
        if not (EVAL_OPEN <= signal.entry_at < EVAL_CLOSE):
            continue
        presented += 1

        episode_id = source_index.get(
            (
                signal.cisd_at,
                signal.side.value,
                setup.context.timeframe,
                signal.target,
            )
        )
        if episode_id is None:
            counts["ABSTAIN_NO_CAUSAL_CIBO_EPISODE"] += 1
            continue
        matched += 1
        target_rows = episodes[episode_id]

        regime = r5._regime_features(
            {"entry_at": signal.entry_at.isoformat(), "side": signal.side.value},
            d1,
            h4,
        )
        posture = _market_posture(regime)
        posture_counts[posture] += 1
        entry_mode = _entry_mode(setup, posture)
        entry_counts[entry_mode] += 1

        fill = r3._entry(setup, evidence, opens, entry_mode)
        if fill is None:
            counts["ABSTAIN_NO_FILL_OR_INVALIDATED_BEFORE_FILL"] += 1
            continue
        entry_at, entry = fill

        active = _all_active_targets(
            target_rows,
            at=entry_at,
            side=signal.side,
            anchor=entry,
        )
        ladder = _distinct_target_ladder(active, anchor=entry)
        if not ladder:
            counts["ABSTAIN_NO_ACTIVE_DOL_AT_FILL"] += 1
            continue

        provisional = _provisional_trade(
            setup,
            entry_mode=entry_mode,
            entry_at=entry_at,
            entry=entry,
            target=ladder[0],
        )
        assessment, _row = prior._assess(
            setup=setup,
            trade=provisional,
            evidence=evidence,
            opens=opens,
            episodes=episodes,
            ctx=recognition_ctx,
        )
        state_counts[assessment.state.value] += 1

        if assessment.state is r11.SituationState.KNOWN_INVALID:
            counts["ABSTAIN_KNOWN_INVALID"] += 1
            continue
        if assessment.state is r11.SituationState.CONFLICTED:
            counts["ABSTAIN_CONFLICTED"] += 1
            continue

        target_index = min(_target_index(posture, regime), len(ladder) - 1)
        target = ladder[target_index]
        target_rank_counts[str(target_index + 1)] += 1

        trade = _simulate_selected(
            setup,
            entry_mode=entry_mode,
            entry_at=entry_at,
            entry=entry,
            target_row=target,
            evidence=evidence,
            opens=opens,
        )
        if trade is None:
            counts["ABSTAIN_INVALID_EXECUTION_GEOMETRY"] += 1
            continue

        if trade.entry_at < busy_until:
            counts["ABSTAIN_SINGLE_POSITION_BUSY"] += 1
            continue

        busy_until = trade.exit_at
        counts["EXECUTE"] += 1
        target_route_counts[trade.target_route] += 1
        item = {
            "trade": trade,
            "brain_posture": posture,
            "intelligence_state": assessment.state.value,
            "intelligence_mechanism": assessment.mechanism_code,
            "target_ladder_rank": target_index + 1,
            "weekday": setup.context.weekday,
            "session": setup.context.session,
            "fvg_before_entry": setup.context.fvg_before_entry,
            "exact_equal_liquidity": setup.context.exact_equal_liquidity,
            "regime": regime,
        }
        executed.append(item)
        decisions.append(
            {
                "setup_at": signal.entry_at.isoformat(),
                "entry_at": trade.entry_at.isoformat(),
                "decision": "EXECUTE",
                "brain_posture": posture,
                "entry_mode": entry_mode,
                "intelligence_state": assessment.state.value,
                "target_ladder_rank": target_index + 1,
                "target_route": trade.target_route,
                "weekday": setup.context.weekday,
                "session": setup.context.session,
            }
        )

    trades = [item["trade"] for item in executed]
    target_hits = sum(1 for trade in trades if trade.exit_reason in TARGET_EXIT_REASONS)
    stop_hits = sum(1 for trade in trades if trade.exit_reason in STOP_EXIT_REASONS)

    payload = {
        "schema": "qore.turtle_soup_xauusd_r15.cibo_first_market_brain.v1",
        "identity": IDENTITY,
        "symbol": "XAUUSD",
        "window": {
            "open": EVAL_OPEN.isoformat(),
            "close": EVAL_CLOSE.isoformat(),
            "duration_years": 2,
        },
        "knowledge_sources": {
            "cibo_xauusd_market_intelligence_identity": (
                "CIBO_XAUUSD_MARKET_INTELLIGENCE_DOSSIER_V1"
            ),
            "cibo_market_journey_identity": (
                "CIBO_MARKET_JOURNEY_LAYER_V1"
            ),
            "target_destination_identity": r3.TARGET_IDENTITY,
            "r11_situation_engine_identity": r11.IDENTITY,
            "r14_upstream_capacity_evidence": (
                "TURTLE_SOUP_XAUUSD_R14_UPSTREAM_JOURNEY_CAPACITY_GEOMETRY_FORENSICS_V1"
            ),
        },
        "brain_contract": {
            "r3_pnl_router_used": False,
            "market_context_before_entry": True,
            "r11_assessed_before_execution": True,
            "known_invalid_respected": True,
            "conflicted_respected": True,
            "unknown_can_be_resolved_by_market_brain_context": True,
            "protected_swing_is_structural_stop": True,
            "fixed_r_target_used": False,
            "active_cibo_dol_ladder_used": True,
            "target_extension_max_one_ladder_step": True,
            "target_extension_requires_with_trade_regime": True,
            "weekday_known_but_not_hard_filter": True,
            "session_known_but_not_hard_filter": True,
            "fvg_known_but_not_hard_filter": True,
            "equal_liquidity_known_but_not_hard_filter": True,
            "pnl_score_used": False,
            "probability_of_profit_used": False,
            "year_as_trade_feature": False,
            "post_entry_information_used_for_decision": False,
            "fresh_holdout_used": False,
        },
        "reproduction": {
            "retained_bars": int(provenance["retained_bars"]),
            "setup_pool_10y": len(setups),
            "setups_presented_2y": presented,
            "causal_episode_matched_2y": matched,
            "ambiguous_target_bindings_fail_closed": repair._LAST_AMBIGUOUS_KEYS,
        },
        "behavior": {
            "decision_counts": dict(counts),
            "intelligence_state_counts": dict(state_counts),
            "brain_posture_counts": dict(posture_counts),
            "entry_mode_counts": dict(entry_counts),
            "target_ladder_rank_counts": dict(target_rank_counts),
            "target_route_counts": dict(target_route_counts),
            "executed_trades": len(trades),
            "target_hits": target_hits,
            "stop_hits": stop_hits,
        },
        "economics": {
            "gross": _stats(trades, "gross_r"),
            "primary_005r": _stats(trades),
            "stress_010r": _stats(trades, "stress_net_r"),
        },
        "by_brain_posture": _group(executed, "brain_posture"),
        "by_intelligence_state": _group(executed, "intelligence_state"),
        "by_target_ladder_rank": _group(executed, "target_ladder_rank"),
        "by_weekday_diagnostic": _group(executed, "weekday"),
        "by_session_diagnostic": _group(executed, "session"),
        "funnel_10y": funnel,
        "governance": {
            "research_only": True,
            "consumed_evidence_characterization": True,
            "fresh_holdout_consumed": False,
            "no_rule_promoted": True,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "r15-market-brain-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "r15-market-brain-trades.json").write_text(
        json.dumps([_json_trade(item) for item in executed], indent=2, sort_keys=True)
        + "\n"
    )
    (output / "r15-market-brain-decisions.json").write_text(
        json.dumps(decisions, indent=2, sort_keys=True) + "\n"
    )
    return payload


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module SOURCE_ROOT TARGET_ROOT OUTPUT_DIR")
    print(
        json.dumps(
            run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
