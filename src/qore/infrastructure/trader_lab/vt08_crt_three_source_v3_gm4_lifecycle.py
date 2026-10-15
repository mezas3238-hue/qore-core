"""G-M4 V3 source -> cognition -> locked router -> price-only lifecycle.

PRE-REGISTERED: docs/research/VT08_CRT_THREE_SOURCE_V3_GM4_CAUSAL_LIFECYCLE_PREREG_2026-10-15.md.
A price touched level is not a trade, fill, PnL, or broker order.
CIBO/Risk retains ALL capital and volume authority; VT08 does no sizing.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar
from qore.infrastructure.trader_lab.vt08_crt_pure_original_atlas_reader import (
    load_atlas_vt08_m5,
)
from qore.infrastructure.trader_lab.vt08_crt_three_source_v3_confirmed_h4_census import (
    POLICY_ID,
    full_utc_h4_v3_census,
)
from qore.infrastructure.trader_lab.vt08_crt_three_source_v3_gm3_cognitive_replay import (
    ALLOWED_SOURCE_FIELDS,
    audit_v3_positive_cognition,
)
from qore.infrastructure.trader_lab.vt08_crt_three_source_v3_price_lifecycle import (
    evaluate_frozen_v3_price_lifecycle,
)
from qore.infrastructure.traders.crt_pure_cognitive_contract import (
    CrtPureHypothesisStage,
)
from qore.infrastructure.traders.crt_pure_cognitive_state import transition_hypothesis
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodological_certification import (
    present_vt08_gm5_status,
)
from qore.infrastructure.traders.crt_pure_three_source_methodology import (
    current_three_source_methodology,
)

SCHEMA = "qore.vt08.crt_three_source.v3.gm4_integrated_research_only.v1"
M5 = timedelta(minutes=5)
H4 = timedelta(hours=4)
SOURCE_STAGES = (
    CrtPureHypothesisStage.OBSERVED_EVENT,
    CrtPureHypothesisStage.HYPOTHESIS_FORMING,
    CrtPureHypothesisStage.AWAITING_CONFIRMATION,
    CrtPureHypothesisStage.CONFIRMED,
)
INVALIDATION_PATHS = frozenset((
    "INVALIDATION_FIRST",
    "INVALIDATION_FIRST_AMBIGUOUS_SAME_M5",
))
KNOWN_FINAL_PATHS = frozenset((
    *INVALIDATION_PATHS,
    "DESTINATION_FIRST",
    "EXPIRED_WITHOUT_TOUCH",
    "EXPIRED_AT_C3_CLOSE_NO_POST_DECISION_WINDOW",
))
UNKNOWN_PATHS = frozenset((
    "UNKNOWN_MISSING_ENTRY_OPEN_PRICE",
    "UNKNOWN_ENTRY_ALREADY_BEYOND_BARRIER",
    "UNKNOWN_MISSING_M5_BEFORE_TERMINAL",
    "UNKNOWN_BARRIER_GEOMETRY_INVALID",
))

COGNITION_FIELDS = frozenset((
    "schema", "policy_id", "market", "source_event_id",
    "decision_clock_utc", "causal_source_event_detected",
    "causal_confirmation_recognized", "direction", "cognitive_action",
    "metacognitive_readiness", "adversarial_verdict", "reason_why",
    "methodology_GM1_pass", "cognition_GM3_pass",
    "source_authority_claimed", "no_sizing", "no_broker_order",
    "no_live_or_demo", "not_fresh_holdout",
))
POST_DECISION_FIELDS = frozenset((
    "schema", "policy_id", "market", "source_event_id",
    "c3_H4_opened_at_utc", "decision_clock_utc", "year_utc",
    "source_direction", "source_m15_invalidating_extreme_relative",
    "fixed_parent_h4_target_twice_relative", "price_path_outcome",
    "first_hit_opened_at_utc", "observed_m5_after_decision",
    "not_a_trade", "no_PnL_or_sizing", "not_fresh_OOS",
))


def reconcile_v3_gm4_case(
    source: dict[str, Any],
    cognition: dict[str, Any],
    post_decision: dict[str, Any],
) -> dict[str, Any]:
    """Match three separately rebuilt ledgers; do NOT peek for initial decision."""
    if set(source) - ALLOWED_SOURCE_FIELDS:
        raise ValueError("unexpected future/sizing fields in source")
    if set(cognition) - COGNITION_FIELDS:
        raise ValueError("unexpected future/sizing fields in cognition")
    if set(post_decision) - POST_DECISION_FIELDS:
        raise ValueError("unexpected future/sizing fields in post-decision path")
    if source["policy_id"] != POLICY_ID:
        raise ValueError("source policy identity mismatch")
    if cognition["policy_id"] != POLICY_ID or post_decision["policy_id"] != POLICY_ID:
        raise ValueError("cognition/path source policy mismatch")
    if source["conceptual_state"] != "CONCEPTUAL_CANDIDATE_V3":
        raise ValueError("non-confirmed V3 cannot enter G-M4 source lifecycle")
    if (
        source["source_authority_adjudicated"] is not False
        or source["independent_method_review_complete"] is not False
        or source["not_a_trade"] is not True
        or source["no_sizing_or_capital_authority"] is not True
    ):
        raise ValueError("source falsely claims approval, orders, or capital")
    if (
        cognition["cognitive_action"] != "ABSTAIN"
        or cognition["source_authority_claimed"] is not False
        or cognition["no_sizing"] is not True
        or cognition["no_broker_order"] is not True
        or cognition["cognition_GM3_pass"] is not False
        or cognition["methodology_GM1_pass"] is not False
        or cognition["causal_confirmation_recognized"] is not True
        or "CRT_SOURCE_STRATEGY_NOT_CLOSED" not in cognition["reason_why"]
    ):
        raise ValueError("cognition does not preserve source-open fail-closed")
    if (
        post_decision["not_a_trade"] is not True
        or post_decision["no_PnL_or_sizing"] is not True
        or post_decision["not_fresh_OOS"] is not True
    ):
        raise ValueError("post-decision evidence claims trades/sizing/OOS")
    event_id = source["source_event_id"]
    market = source["market"]
    if CrtPureMarket(market) not in (CrtPureMarket.AUDUSD, CrtPureMarket.USDJPY):
        raise ValueError("BTCUSD is frozen")
    clock = source["decision_clock_utc"]
    c3_start_s = source["c3_H4_opened_at_utc"]
    if not all((
        cognition["source_event_id"] == event_id,
        post_decision["source_event_id"] == event_id,
        cognition["market"] == market,
        post_decision["market"] == market,
        cognition["decision_clock_utc"] == clock,
        post_decision["decision_clock_utc"] == clock,
        cognition["direction"] == source["parent_direction"],
        post_decision["source_direction"] == source["parent_direction"],
        post_decision["c3_H4_opened_at_utc"] == c3_start_s,
    )):
        raise ValueError("source/cognition/path case identity or causal clock mismatch")
    decision = datetime.fromisoformat(clock)
    c3_start = datetime.fromisoformat(c3_start_s)
    if (
        decision.tzinfo is None or c3_start.tzinfo is None
        or not c3_start < decision < c3_start + H4
    ):
        raise ValueError("invalid V3 causal decision in parent H4 C3")
    if current_three_source_methodology().methodology_closed:
        raise ValueError("not a research-only unapproved three-source state")
    gm5 = present_vt08_gm5_status()
    if gm5.certificate_issued or gm5.broker_order_authorized or gm5.volume_authorized:
        raise ValueError("cannot simulate route through approved G-M5 or capital")
    if "THREE_SOURCE_RULE_OPEN:entry_confirmation" not in gm5.blockers:
        raise ValueError("current router has lost three-source entry source blocker")

    stages = [SOURCE_STAGES[0]]
    for stage in SOURCE_STAGES[1:]:
        stages.append(transition_hypothesis(stages[-1], stage))
    if stages[-1] is not CrtPureHypothesisStage.CONFIRMED:
        raise ValueError("missing real confirmed causal stage")

    outcome = post_decision["price_path_outcome"]
    hit_clock = post_decision["first_hit_opened_at_utc"]
    current_stage: CrtPureHypothesisStage = stages[-1]
    observed_at: str | None = None
    terminal = False
    if outcome in INVALIDATION_PATHS or outcome == "DESTINATION_FIRST":
        if not isinstance(hit_clock, str):
            raise ValueError("known first-touch requires real original M5 open time")
        opened = datetime.fromisoformat(hit_clock)
        closed = opened + M5
        if (
            opened.tzinfo is None
            or opened.astimezone(UTC) < decision.astimezone(UTC)
            or closed.astimezone(UTC) > (c3_start + H4).astimezone(UTC)
        ):
            raise ValueError("post-decision M5 hit was not causally observable")
        observed_at = closed.isoformat()
        if outcome in INVALIDATION_PATHS:
            current_stage = transition_hypothesis(
                current_stage, CrtPureHypothesisStage.THESIS_INVALIDATED
            )
            stages.append(current_stage)
        current_stage = transition_hypothesis(
            current_stage, CrtPureHypothesisStage.THESIS_KILLED
        )
        stages.append(current_stage)
        terminal = True
    elif outcome in KNOWN_FINAL_PATHS:
        if hit_clock is not None:
            raise ValueError("expired price path cannot have a fabricated price hit")
        current_stage = transition_hypothesis(
            current_stage, CrtPureHypothesisStage.THESIS_KILLED
        )
        stages.append(current_stage)
        terminal = True
        observed_at = (c3_start + H4).isoformat()
    elif outcome in UNKNOWN_PATHS:
        if hit_clock is not None:
            raise ValueError("unknown path may not invent an observed terminal price")
        # The research record CANNOT infer a terminal market observation from a
        # corrupted or missing M5 prefix, even if wall-clock time has passed.
        terminal = False
    else:
        raise ValueError("unexpected price-only lifecycle status")

    return {
        "schema": SCHEMA,
        "source_policy_id": POLICY_ID,
        "source_event_id": event_id,
        "market": market,
        "source_decision_clock_utc": clock,
        "initial_cognitive_action": cognition["cognitive_action"],
        "initial_cognitive_why": tuple(cognition["reason_why"]),
        "initial_confirmation_recognized": True,
        "gm5_router_blocked_at_decision": True,
        "parent_c3_utc": c3_start_s,
        "price_path_outcome_only_post_decision": outcome,
        "terminal_observed_at_utc": observed_at,
        "terminal_observation_proven": terminal,
        "stage_path": tuple(stage.value for stage in stages),
        "last_causal_stage": current_stage.value,
        "no_resurrection_or_rearm": True,
        "not_a_trade": True,
        "no_capital_or_volume_authority": True,
        "no_PnL_or_sizing": True,
        "not_fresh_OOS": True,
        "G_M4_PASS": False,
        "G_M5_ISSUED": False,
        "GLOBAL_CERTIFIED": False,
    }


def replay_v3_gm4(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    source, all_source = full_utc_h4_v3_census(market, bars)
    _, price_rows = evaluate_frozen_v3_price_lifecycle(market, bars)
    source_rows = tuple(
        s for s in all_source
        if s["conceptual_state"] == "CONCEPTUAL_CANDIDATE_V3"
    )
    if len(source_rows) != len(price_rows):
        raise ValueError("frozen source/price count mismatch")
    indexed_price = {r["source_event_id"]: r for r in price_rows}
    if len(indexed_price) != len(price_rows):
        raise ValueError("duplicate post-decision source ID")
    if {r["source_event_id"] for r in source_rows} != set(indexed_price):
        raise ValueError("source/price IDs do not match")
    out: list[dict[str, Any]] = []
    for raw_source in source_rows:
        cognition = audit_v3_positive_cognition(raw_source)
        output = reconcile_v3_gm4_case(
            raw_source, cognition, indexed_price[raw_source["source_event_id"]]
        )
        out.append(output)
    if not out and source["state_counts"].get("CONCEPTUAL_CANDIDATE_V3", 0):
        raise ValueError("missing G-M4 source cases")
    states = Counter(row["price_path_outcome_only_post_decision"] for row in out)
    summary = {
        "schema": SCHEMA,
        "source_policy_id": POLICY_ID,
        "market": market.value,
        "real_atlas_M5": len(bars),
        "H4_contexts": source["complete_h4_c1_c2_contexts"],
        "v3_confirmed_source_count": len(source_rows),
        "v3_cognition_recognized": len(out),
        "v3_gm4_cases_reconciled": len(out),
        "cognitive_action_ABSTAIN": sum(
            r["initial_cognitive_action"] == "ABSTAIN" for r in out
        ),
        "terminal_proven": sum(r["terminal_observation_proven"] for r in out),
        "terminal_unknown": sum(not r["terminal_observation_proven"] for r in out),
        "price_outcomes_post_decision_only": dict(sorted(states.items())),
        "all_initial_routers_blocked": all(
            r["gm5_router_blocked_at_decision"] for r in out
        ),
        "G_M1_PASS": False,
        "G_M2_PASS": False,
        "G_M3_PASS": False,
        "G_M4_PASS": False,
        "G_M5_ISSUED": False,
        "GLOBAL_CERTIFIED": False,
        "no_sizing": True,
        "no_PnL_or_broker_fills": True,
        "not_fresh_OOS": True,
    }
    return summary, tuple(out)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("market", choices=("AUDUSD", "USDJPY"))
    p.add_argument("atlas_root", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    market = CrtPureMarket(args.market)
    bars, provenance = load_atlas_vt08_m5(market, args.atlas_root)
    summary, ledger = replay_v3_gm4(market, bars)
    summary["original_source_provenance"] = provenance
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "v3-gm4-causal-lifecycle-summary.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n"
    )
    with (args.output / "v3-gm4-causal-lifecycle-ledger.jsonl").open("w") as f:
        for row in ledger:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({
        k: v for k, v in summary.items() if k != "original_source_provenance"
    }, sort_keys=True))


if __name__ == "__main__":
    main()
