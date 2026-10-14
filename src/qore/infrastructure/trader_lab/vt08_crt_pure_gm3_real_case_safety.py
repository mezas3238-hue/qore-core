"""G-M3 safety replay of G-M2 blinded REAL market cases.

This is not a new CRT detector or a certification witness. It checks whether
existing cognitive reasoning fails closed on actual past market prefixes when
Model #1 source-reference selection remains unresolved. No PnL and NO sizing.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

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
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)
from qore.infrastructure.traders.crt_pure_r2_entry_router import (
    CrtPureR2EntryState,
    assess_model1_certification_entry_family,
)
from qore.infrastructure.traders.crt_pure_strategy_identity_memory import (
    model1_source_ready,
    unresolved_model1_source_concepts,
)

SCHEMA = "qore.vt08.crt_pure.gm3_real_case_source_safety.v1"
M15 = timedelta(minutes=15)


def audit_blind_case(case: dict[str, Any]) -> dict[str, Any]:
    """Consume PRE-C2 snapshots exclusively. Refuse embedded future C3."""
    if case.get("is_execution_authorized") is not False:
        raise ValueError("must be research-only")
    if case.get("future_C3_withheld_from_blind_file") is not True:
        raise ValueError("must provide future-free blinded prefix")
    if any("reveal" in key.lower() or "future_C3_ohlc" in key for key in case):
        raise ValueError("sealed future must not enter G-M3 review")
    market = CrtPureMarket(case["market"])
    if market is CrtPureMarket.BTCUSD:
        raise ValueError("BTCUSD frozen")
    clock = datetime.fromisoformat(case["decision_clock_utc"])
    if clock.tzinfo is None:
        raise ValueError("decision clock requires timezone")
    candles = case["M15_observed_prefix_through_C2"]
    if len(candles) < 2:
        raise ValueError("missing closed C1/C2 evidence")
    observations: list[CrtPureCausalObservation] = []
    previous: datetime | None = None
    for bar in candles:
        opened = datetime.fromisoformat(bar["opened_at_utc"])
        if opened.tzinfo is None or opened + M15 > clock:
            raise ValueError("future/partial M15 in purported blinded prefix")
        if previous is not None and opened - previous != M15:
            raise ValueError("noncontiguous M15 sequence")
        previous = opened
        for key in ("open_relative", "high_relative", "low_relative", "close_relative"):
            if not isinstance(bar[key], int):
                raise ValueError("non-integer original Atlas relative OHLC")
        if not bar["low_relative"] <= min(bar["open_relative"], bar["close_relative"]):
            raise ValueError("invalid M15 OHLC low")
        if not max(bar["open_relative"], bar["close_relative"]) <= bar["high_relative"]:
            raise ValueError("invalid M15 OHLC high")
        observations.append(
            CrtPureCausalObservation(
                name="CLOSED_M15_OHLC",
                observed_at=opened + M15,
                value_token=json.dumps(
                    (
                        bar["open_relative"], bar["high_relative"],
                        bar["low_relative"], bar["close_relative"]
                    ), separators=(",", ":")
                ),
            )
        )
    if previous is None or previous + M15 != clock:
        raise ValueError("last M15 not closed at decision clock")
    if case["reference_level_selection"] != "UNRESOLVED_BY_PRIMARY_SOURCE":
        raise ValueError("case unexpectedly claims closed reference")
    if case["author_model1_equivalence"] != "NOT_ADJUDICATED":
        raise ValueError("case unexpectedly promoted source")
    blockers = tuple(x.value for x in unresolved_model1_source_concepts())
    if not blockers or model1_source_ready():
        raise ValueError("safety audit designed for genuine open-source gate only")
    situation = CrtPureSituationModel(
        market=market,
        observed_at=clock,
        hypothesis_id="GM3_CASE:" + case["case_id"],
        source_event_id="UNADJUDICATED_MODEL1:" + case["case_id"],
        event_generation=1,
        attention_state=CrtPureAttentionState.WATCH,
        hypothesis_stage=CrtPureHypothesisStage.HYPOTHESIS_FORMING,
        data_integrity_ok=True,
        strategy_identity_ready=False,
        source_event_present=False,
        confirmation_complete=False,
        destination_context_known=False,
        destination_available=False,
        execution_data_fresh=True,
        knowledge_state=CrtPureKnowledgeState.PARTIAL,
        uncertainties=(
            "MODEL1_REFERENCE_SELECTION_SOURCE_OPEN",
            "C2_OBSERVATION_IS_NOT_MODEL1_CONFIRMATION",
            "DOL_SOURCE_NOT_ADJUDICATED",
        ),
        observations=tuple(observations),
    )
    decision = reason(situation)
    if decision.action is not CrtPureReasoningAction.ABSTAIN:
        raise ValueError("unresolved Model #1 was incorrectly promoted")
    if decision.grants_capital_authority:
        raise ValueError("cognitive output must never grant capital authority")
    # No source-authenticated Model #1 candidate exists in the blind casebook.
    # Integrate the real H4 context with the source-aware G-M4 certification
    # router; this audits the missing-source barrier, not a full E2E execution.
    router = assess_model1_certification_entry_family(
        parent_direction=CrtPureCandidateDirection(
            case["parent_H4_direction_context"]
        ),
        confirmation=None,
    )
    if (
        router.action is not CrtPureReasoningAction.WAIT
        or router.state is not CrtPureR2EntryState.UNRESOLVED
        or router.grants_capital_authority
        or router.grants_execution_authority
    ):
        raise ValueError("G-M4 router bypassed unresolved Model #1 source")
    return {
        "schema": SCHEMA,
        "case_id": case["case_id"],
        "market": market.value,
        "decision_clock_utc": clock.isoformat(),
        "M15_closed_prefix": len(candles),
        "unresolved_source_concepts": blockers,
        "reason_action": decision.action.value,
        "reason_why": decision.auditable_why,
        "certification_router_action": router.action.value,
        "certification_router_state": router.state.value,
        "certification_router_why": router.why,
        "G_M4_missing_source_router_safety_checked": True,
        "G_M3_source_fidelity_certified": False,
        "G_M3_safety_fail_closed_checked": True,
        "no_profit_loss_or_sizing_used": True,
        "no_trade": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("blind_jsonl", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rows = [
        audit_blind_case(json.loads(line))
        for line in args.blind_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows or len({r["case_id"] for r in rows}) != len(rows):
        raise ValueError("missing or duplicate real cases")
    stats = Counter(row["reason_action"] for row in rows)
    manifest = {
        "schema": SCHEMA,
        "cases": len(rows),
        "actions": dict(sorted(stats.items())),
        "methodological_GM3_certified": False,
        "source_only_safety_barrier_checked": True,
        "G_M4_unresolved_source_router_actions": dict(
            sorted(Counter(row["certification_router_action"] for row in rows).items())
        ),
        "G_M4_missing_source_router_safety_checked": True,
        "full_cognitive_reconciliation_completed": False,
        "GM4_end_to_end_certified": False,
        "GM5_certified": False,
        "global_certified": False,
        "sizing_or_broker_orders": False,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "gm3-real-safety-summary.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (args.output / "gm3-real-safety-ledger.jsonl").open(
        "w", encoding="utf-8"
    ) as file:
        for row in rows:
            file.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
