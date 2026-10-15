"""V3 confirmed real CRT source -> autonomous QORE cognitive cognition audit.

Positive geometric evidence is recognized, but unadjudicated three-source
methodology must fail closed. This is G-M3 research, NOT G-M3 PASS, fills,
sizing, broker execution, numerical confidence, or economic certification.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta
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
from qore.infrastructure.traders.crt_pure_cognitive_contract import (
    CrtPureAttentionState,
    CrtPureHypothesisStage,
    CrtPureKnowledgeState,
    CrtPureReasoningAction,
)
from qore.infrastructure.traders.crt_pure_cognitive_state import (
    CrtPureCausalObservation,
    CrtPureSituationModel,
    reason,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_three_source_methodology import (
    current_three_source_methodology,
)

SCHEMA = "qore.vt08.crt_three_source.v3.gm3_cognitive_positive_replay.v1"
ALLOWED_SOURCE_FIELDS = frozenset((
    "schema", "policy_id", "market", "source_event_id",
    "c3_H4_opened_at_utc", "year_utc", "parent_direction",
    "decision_clock_utc", "m15_confirmed_triples_checked",
    "opposing_micro_patterns",
    "structural_invalidation_price_if_candidate",
    "conceptual_state", "why", "source_authority_adjudicated",
    "independent_method_review_complete", "not_a_trade",
    "no_sizing_or_capital_authority",
    "prior_dev_sample_not_fresh_holdout",
))


def audit_v3_positive_cognition(row: dict[str, Any]) -> dict[str, Any]:
    if set(row).difference(ALLOWED_SOURCE_FIELDS):
        raise ValueError("unknown or future/sizing columns in V3 source observation")
    if row["policy_id"] != POLICY_ID:
        raise ValueError("V3 source policy mismatch")
    if row["conceptual_state"] != "CONCEPTUAL_CANDIDATE_V3":
        raise ValueError("G-M3 positive audit expects confirmed V3 hypothesis")
    if (
        row["source_authority_adjudicated"] is not False
        or row["independent_method_review_complete"] is not False
        or row["not_a_trade"] is not True
        or row["no_sizing_or_capital_authority"] is not True
    ):
        raise ValueError("G-M3 source cannot forge review/trading authorization")
    market = CrtPureMarket(row["market"])
    if market is CrtPureMarket.BTCUSD:
        raise ValueError("BTCUSD frozen")
    parent_start = datetime.fromisoformat(row["c3_H4_opened_at_utc"])
    observed_at = datetime.fromisoformat(row["decision_clock_utc"])
    if (
        parent_start.tzinfo is None or observed_at.tzinfo is None
        or not parent_start < observed_at < parent_start + timedelta(hours=4)
        or (observed_at - parent_start).total_seconds() % 900
    ):
        raise ValueError("V3 confirmation must close causally within H4 C3")
    if not row["source_event_id"]:
        raise ValueError("V3 source event needs causal stable identity")
    owner_policy = current_three_source_methodology()
    if owner_policy.methodology_closed:
        raise ValueError("this research-only safety audit requires G-M1 OPEN")
    current = CrtPureSituationModel(
        market=market,
        observed_at=observed_at,
        hypothesis_id=f"V3:{row['source_event_id']}",
        source_event_id=row["source_event_id"],
        event_generation=1,
        attention_state=CrtPureAttentionState.DECISION,
        hypothesis_stage=CrtPureHypothesisStage.CONFIRMED,
        data_integrity_ok=True,
        strategy_identity_ready=False,
        source_event_present=True,
        confirmation_complete=True,
        destination_context_known=True,
        destination_available=True,
        execution_data_fresh=True,
        knowledge_state=CrtPureKnowledgeState.PARTIAL,
        uncertainties=("THREE_SOURCE_V3_RULES_NOT_INDEPENDENTLY_ADJUDICATED",),
        market_context_tokens=(
            "V3_THIRD_CANDLE_RECOGNIZED",
            "SOURCE_INSPIRED_QORE_ENGINEERING_UNAPPROVED",
        ),
        observations=(
            CrtPureCausalObservation(
                name="H4_C2_PARENT_BIAS_SOURCE_CLOSED",
                observed_at=parent_start,
                value_token=str(row["parent_direction"]),
            ),
            CrtPureCausalObservation(
                name="M15_THIRD_BODY_CONFIRMATION_CLOSED",
                observed_at=observed_at,
                value_token="TRUE_AT_M15_CLOSE",
            ),
            CrtPureCausalObservation(
                name="H4_C1_DOL_NOT_CONSUMED_BEFORE_DECISION",
                observed_at=observed_at,
                value_token="TRUE_AT_M15_CLOSE",
            ),
        ),
    )
    decision = reason(current)
    if decision.action is not CrtPureReasoningAction.ABSTAIN:
        raise ValueError("unapproved V3 source was falsely promoted to execution")
    if "CRT_CONFIRMATION_COMPLETE" not in decision.supporting_evidence:
        raise ValueError("cognition did not recognize positive M15 confirmation")
    if "CRT_SOURCE_STRATEGY_NOT_CLOSED" not in decision.auditable_why:
        raise ValueError("cognition lacked explicit independent-source blocker")
    return {
        "schema": SCHEMA,
        "policy_id": POLICY_ID,
        "market": market.value,
        "source_event_id": row["source_event_id"],
        "decision_clock_utc": observed_at.isoformat(),
        "causal_source_event_detected": True,
        "causal_confirmation_recognized": True,
        "direction": row["parent_direction"],
        "cognitive_action": decision.action.value,
        "metacognitive_readiness": decision.metacognitive_readiness.value,
        "adversarial_verdict": decision.adversarial_verdict.value,
        "reason_why": decision.auditable_why,
        "methodology_GM1_pass": False,
        "cognition_GM3_pass": False,
        "source_authority_claimed": False,
        "no_sizing": True,
        "no_broker_order": True,
        "no_live_or_demo": True,
        "not_fresh_holdout": True,
    }


def replay_v3_gm3(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    census, events = full_utc_h4_v3_census(market, bars)
    eligible = tuple(
        r for r in events
        if r["conceptual_state"] == "CONCEPTUAL_CANDIDATE_V3"
    )
    results = tuple(audit_v3_positive_cognition(e) for e in eligible)
    if len(results) != census["state_counts"].get("CONCEPTUAL_CANDIDATE_V3", 0):
        raise ValueError("all V3 positive source events must be audited")
    if len({r["source_event_id"] for r in results}) != len(results):
        raise ValueError("duplicate V3 event in cognitive audit")
    counts = Counter(row["cognitive_action"] for row in results)
    manifest = {
        "schema": SCHEMA,
        "market": market.value,
        "policy_id": POLICY_ID,
        "original_M5": len(bars),
        "H4_contexts": census["complete_h4_c1_c2_contexts"],
        "V3_conceptual_sources": len(eligible),
        "G_M3_positives_recognized": len(results),
        "cognitive_actions": dict(sorted(counts.items())),
        "all_causal_confirmations_recognized": all(
            row["causal_confirmation_recognized"] for row in results
        ),
        "independent_author_review_exists": False,
        "G_M1_PASS": False,
        "G_M2_PASS": False,
        "G_M3_PASS": False,
        "G_M4_PASS": False,
        "G_M5_CERTIFIED": False,
        "GLOBAL_CERTIFIED": False,
        "no_sizing": True,
        "no_PnL_or_fills": True,
        "not_fresh_OOS": True,
    }
    return manifest, results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("market", choices=("AUDUSD", "USDJPY"))
    ap.add_argument("atlas_root", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()
    market = CrtPureMarket(args.market)
    bars, prov = load_atlas_vt08_m5(market, args.atlas_root)
    manifest, ledger = replay_v3_gm3(market, bars)
    manifest["original_atlas_provenance"] = prov
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "v3-gm3-cognitive-summary.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "v3-gm3-cognitive-ledger.jsonl").open("w") as f:
        for row in ledger:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({
        k: v for k, v in manifest.items() if k != "original_atlas_provenance"
    }, sort_keys=True))


if __name__ == "__main__":
    main()
