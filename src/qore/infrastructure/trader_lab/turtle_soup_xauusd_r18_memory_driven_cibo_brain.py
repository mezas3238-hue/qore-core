"""R18 memory-driven CIBO market brain for Turtle Soup XAUUSD.

Research-only consumed-evidence policy characterization.

R18 uses structural knowledge established by R16/R17 rather than PnL:
- NEXT_SOURCE_OPEN is the canonical entry because generic retest rarely recovers
  journey capacity and often destroys it across all temporal partitions.
- Protected Swing remains the exact stop. If the Protected Swing risk is
  structurally too compressed relative to the source candle (pre-existing R2
  q1/q2 buckets), the trader abstains instead of widening the stop.
- Rank 1 of the distinct active CIBO DOL ladder is the normal destination.
- Rank 2 is considered only for two named structural capacity pathways
  (late-confirmation capacity or H4 compression-release), only during Asia or
  London, and never on Friday. This is a journey-depth decision, not a PnL rule.
- R11 KNOWN_INVALID and CONFLICTED directives are respected before execution.

No learned return score, profit probability, year switch, post-entry input,
arbitrary fixed-R target, or fresh holdout is used.
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
from typing import Any

from qore.infrastructure.trader_lab import (
    cibo_market_atlas_journey_extractor_v1 as journey,
)
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r1 as r1
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r13_autonomous_2y_behavior_replay as recognition,
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
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r15_cibo_first_market_brain as r15,
)

IDENTITY = "TURTLE_SOUP_XAUUSD_R18_MEMORY_DRIVEN_CIBO_BRAIN_V1"
EVAL_OPEN = datetime(2024, 9, 17, tzinfo=UTC)
EVAL_CLOSE = datetime(2026, 9, 17, tzinfo=UTC)

LOW_CAPACITY_RISK_BUCKETS = frozenset({"q1:<=0.25", "q2:<=0.50"})
STRUCTURALLY_ADEQUATE_RISK_BUCKETS = frozenset(
    {"q3:<=1.0", "q4:<=2.0", "q5:>2.0"}
)
SOURCE_RANGE_Q2_PLUS = frozenset(
    {"q2:<=1.0", "q3:<=1.5", "q4:<=2.0", "q5:>2.0"}
)
SOURCE_RANGE_Q3_PLUS = frozenset(
    {"q3:<=1.5", "q4:<=2.0", "q5:>2.0"}
)
EXTENSION_SESSIONS = frozenset({"asia", "london"})


def _late_confirmation_capacity(setup: r3.Setup) -> bool:
    return bool(
        setup.context.cisd_progress_bucket == "q4:>0.75"
        and setup.context.fvg_before_entry == "yes"
        and setup.context.protected_risk_range_bucket
        in STRUCTURALLY_ADEQUATE_RISK_BUCKETS
        and setup.context.source_range_state_bucket in SOURCE_RANGE_Q2_PLUS
    )


def _compression_release_capacity(
    setup: r3.Setup,
    regime: dict[str, str],
) -> bool:
    return bool(
        regime["h4_range_3v20"] == "compressed<=0.75"
        and setup.context.fvg_before_entry == "yes"
        and setup.context.protected_risk_range_bucket
        in STRUCTURALLY_ADEQUATE_RISK_BUCKETS
        and setup.context.source_range_state_bucket in SOURCE_RANGE_Q3_PLUS
    )


def _displacement_context(setup: r3.Setup) -> bool:
    return bool(
        setup.context.fvg_before_entry == "yes"
        and setup.context.reclaim_latency_bucket
        in {"16-30m", "31-60m", "61-120m"}
        and setup.context.protected_risk_range_bucket
        in STRUCTURALLY_ADEQUATE_RISK_BUCKETS
    )


def _target_depth_decision(
    *,
    setup: r3.Setup,
    regime: dict[str, str],
    ladder_size: int,
) -> tuple[int, str]:
    late = _late_confirmation_capacity(setup)
    compression = _compression_release_capacity(setup, regime)
    session_support = setup.context.session in EXTENSION_SESSIONS
    friday = setup.context.weekday == "Friday"

    if (
        ladder_size >= 2
        and session_support
        and not friday
        and (late or compression)
    ):
        if late and compression:
            return 2, "RANK2_LATE_CONFIRMATION_AND_COMPRESSION_RELEASE"
        if late:
            return 2, "RANK2_LATE_CONFIRMATION_CAPACITY"
        return 2, "RANK2_COMPRESSION_RELEASE_CAPACITY"

    if friday and (late or compression):
        return 1, "RANK1_FRIDAY_DEPTH_CONSERVATIVE"
    if not session_support and (late or compression):
        return 1, "RANK1_SESSION_DEPTH_CONSERVATIVE"
    if _displacement_context(setup):
        return 1, "RANK1_DISPLACEMENT_SUPPORTED"
    return 1, "RANK1_BASE_STRUCTURAL_DESTINATION"


def _stats(
    trades: Sequence[r3.RoutedTrade],
    attr: str = "primary_net_r",
) -> dict[str, Any]:
    return r3._stat(trades, attr)


def _group(
    executed: Sequence[dict[str, Any]],
    key: str,
) -> dict[str, Any]:
    groups: dict[str, list[r3.RoutedTrade]] = defaultdict(list)
    for item in executed:
        groups[str(item[key])].append(item["trade"])
    return {
        name: {
            "primary_005r": _stats(rows),
            "stress_010r": _stats(rows, "stress_net_r"),
            "gross": _stats(rows, "gross_r"),
        }
        for name, rows in sorted(groups.items())
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
            "brain_reason": item["brain_reason"],
            "target_ladder_rank": item["target_ladder_rank"],
            "intelligence_state": item["intelligence_state"],
            "intelligence_mechanism": item["intelligence_mechanism"],
            "brain_posture": item["brain_posture"],
            "weekday": item["weekday"],
            "session": item["session"],
            "fvg_before_entry": item["fvg_before_entry"],
            "exact_equal_liquidity": item["exact_equal_liquidity"],
            "protected_risk_range_bucket": item[
                "protected_risk_range_bucket"
            ],
            "source_range_state_bucket": item[
                "source_range_state_bucket"
            ],
            "cisd_progress_bucket": item["cisd_progress_bucket"],
            "reclaim_latency_bucket": item["reclaim_latency_bucket"],
            "d1_trend_state_20": item["regime"]["d1_trend_state_20"],
            "h4_trend_state_20": item["regime"]["h4_trend_state_20"],
            "d1_range_5v20": item["regime"]["d1_range_5v20"],
            "h4_range_3v20": item["regime"]["h4_range_3v20"],
        }
    )
    return converted


def run(
    source_root: Path,
    target_root: Path,
    output: Path,
) -> dict[str, Any]:
    evidence, provenance = journey.load_raw_m5(source_root)
    if evidence.symbol != r3.SYMBOL or int(provenance["retained_bars"]) != 707716:
        raise ValueError("unexpected XAUUSD corpus")

    episodes, source_index = repair._load_targets_fail_closed(target_root)

    original_open, original_close = r1.EVAL_OPEN, r1.EVAL_CLOSE
    try:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = r3.EVAL_OPEN, r3.EVAL_CLOSE
        setups, funnel = r3._build_setups(evidence)
    finally:
        r1.EVAL_OPEN, r1.EVAL_CLOSE = original_open, original_close

    opens = tuple(bar.opened_at for bar in evidence.bars)
    recognition_ctx = recognition._prepare_recognition_context(evidence)
    d1 = recognition_ctx["d1_regime"]
    h4 = recognition_ctx["h4_regime"]

    decisions: list[dict[str, Any]] = []
    executed: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    state_counts: Counter[str] = Counter()
    rank_counts: Counter[str] = Counter()
    route_counts: Counter[str] = Counter()

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

        fill = r3._entry(
            setup,
            evidence,
            opens,
            "NEXT_SOURCE_OPEN",
        )
        if fill is None:
            counts["ABSTAIN_NO_IMMEDIATE_FILL"] += 1
            continue
        entry_at, entry = fill

        target_rows = episodes[episode_id]
        active = r15._all_active_targets(
            target_rows,
            at=entry_at,
            side=signal.side,
            anchor=entry,
        )
        ladder = r15._distinct_target_ladder(active, anchor=entry)
        if not ladder:
            counts["ABSTAIN_NO_ACTIVE_DOL"] += 1
            continue

        regime = r5._regime_features(
            {"entry_at": entry_at.isoformat(), "side": signal.side.value},
            d1,
            h4,
        )
        posture = r15._market_posture(regime)

        provisional = r15._provisional_trade(
            setup,
            entry_mode="NEXT_SOURCE_OPEN",
            entry_at=entry_at,
            entry=entry,
            target=ladder[0],
        )
        assessment, _recognition_row = recognition._assess(
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

        if (
            setup.context.protected_risk_range_bucket
            in LOW_CAPACITY_RISK_BUCKETS
        ):
            counts["ABSTAIN_LOW_CAPACITY_PROTECTED_SWING"] += 1
            continue

        rank, reason = _target_depth_decision(
            setup=setup,
            regime=regime,
            ladder_size=len(ladder),
        )
        target = ladder[rank - 1]

        trade = r15._simulate_selected(
            setup,
            entry_mode="NEXT_SOURCE_OPEN",
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
        reasons[reason] += 1
        rank_counts[str(rank)] += 1
        route_counts[trade.target_route] += 1

        item = {
            "trade": trade,
            "brain_reason": reason,
            "target_ladder_rank": rank,
            "intelligence_state": assessment.state.value,
            "intelligence_mechanism": assessment.mechanism_code,
            "brain_posture": posture,
            "weekday": setup.context.weekday,
            "session": setup.context.session,
            "fvg_before_entry": setup.context.fvg_before_entry,
            "exact_equal_liquidity": setup.context.exact_equal_liquidity,
            "protected_risk_range_bucket": (
                setup.context.protected_risk_range_bucket
            ),
            "source_range_state_bucket": (
                setup.context.source_range_state_bucket
            ),
            "cisd_progress_bucket": setup.context.cisd_progress_bucket,
            "reclaim_latency_bucket": setup.context.reclaim_latency_bucket,
            "regime": regime,
        }
        executed.append(item)
        decisions.append(
            {
                "setup_at": signal.entry_at.isoformat(),
                "entry_at": entry_at.isoformat(),
                "decision": "EXECUTE",
                "brain_reason": reason,
                "target_ladder_rank": rank,
                "target_route": trade.target_route,
                "intelligence_state": assessment.state.value,
                "brain_posture": posture,
                "weekday": setup.context.weekday,
                "session": setup.context.session,
            }
        )

    trades = [item["trade"] for item in executed]

    payload = {
        "schema": "qore.turtle_soup_xauusd_r18.memory_driven_cibo_brain.v1",
        "identity": IDENTITY,
        "window": {
            "open": EVAL_OPEN.isoformat(),
            "close": EVAL_CLOSE.isoformat(),
            "duration_years": 2,
        },
        "knowledge_sources": {
            "r11_situation_engine": r11.IDENTITY,
            "r16_structural_decision_forensics": (
                "TURTLE_SOUP_XAUUSD_R16_STRUCTURAL_DECISION_FORENSICS_V1"
            ),
            "r17_journey_capacity_memory": (
                "TURTLE_SOUP_XAUUSD_R17_CIBO_JOURNEY_CAPACITY_MEMORY_V1"
            ),
        },
        "brain_contract": {
            "r3_pnl_router_used": False,
            "entry_mode": "NEXT_SOURCE_OPEN",
            "generic_retest_used": False,
            "protected_swing_exact_stop": True,
            "low_capacity_stop_is_widened": False,
            "low_capacity_stop_causes_abstention": True,
            "known_invalid_respected": True,
            "conflicted_respected": True,
            "target_is_active_cibo_dol": True,
            "normal_target_rank": 1,
            "maximum_target_rank": 2,
            "rank2_requires_named_structural_capacity_path": True,
            "rank2_requires_asia_or_london": True,
            "rank2_forbidden_on_friday": True,
            "weekday_controls_entry_permission": False,
            "session_controls_entry_permission": False,
            "pnl_score_used": False,
            "profit_probability_used": False,
            "year_as_trade_feature": False,
            "post_entry_information_used_for_decision": False,
            "fresh_holdout_used": False,
        },
        "reproduction": {
            "retained_bars": int(provenance["retained_bars"]),
            "setups": len(setups),
            "setups_presented_2y": presented,
            "causal_episode_matched_2y": matched,
            "ambiguous_bindings_fail_closed": repair._LAST_AMBIGUOUS_KEYS,
        },
        "behavior": {
            "decision_counts": dict(counts),
            "brain_reason_counts": dict(reasons),
            "intelligence_state_counts": dict(state_counts),
            "target_ladder_rank_counts": dict(rank_counts),
            "target_route_counts": dict(route_counts),
            "executed_trades": len(trades),
        },
        "economics": {
            "gross": _stats(trades, "gross_r"),
            "primary_005r": _stats(trades, "primary_net_r"),
            "stress_010r": _stats(trades, "stress_net_r"),
        },
        "by_brain_reason": _group(executed, "brain_reason"),
        "by_target_ladder_rank": _group(executed, "target_ladder_rank"),
        "by_session_diagnostic": _group(executed, "session"),
        "by_weekday_diagnostic": _group(executed, "weekday"),
        "by_brain_posture_diagnostic": _group(executed, "brain_posture"),
        "governance": {
            "research_only": True,
            "consumed_evidence_characterization": True,
            "fresh_holdout_consumed": False,
            "brain_promoted": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
        "funnel": funnel,
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "r18-memory-brain-report.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    (output / "r18-memory-brain-trades.json").write_text(
        json.dumps([_json_trade(item) for item in executed], indent=2, sort_keys=True)
        + "\n"
    )
    (output / "r18-memory-brain-decisions.json").write_text(
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
