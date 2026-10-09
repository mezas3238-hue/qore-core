#!/usr/bin/env python3
"""CEO-authorized OFFLINE 3368 experimental comparison: never certify proxy PnL.

Compares existing sovereign Native MAX CIBO and QDLE four-motor research results
by the same sealed signal IDs. DOES NOT pretend these are one shared ledger.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path


def audit(manifest: dict, native: dict, qdle: dict) -> dict:
    opportunities = manifest["opportunities"]
    source_ids = [row["signal_fingerprint"] for row in opportunities]
    if len(source_ids) != 3368 or len(set(source_ids)) != 3368:
        raise ValueError("source must have precisely 3368 unique sealed IDs")
    decisions = native["decision_receipts"]
    native_by_id = {str(x["signal_fingerprint"]): x for x in decisions}
    qdle_by_id = {str(x["signal_fingerprint"]): x for x in qdle["decisions"]}
    if (len(native_by_id) != len(decisions) or len(qdle_by_id) != 3368
        or set(native_by_id) != set(source_ids)
        or set(qdle_by_id) != set(source_ids)):
        raise ValueError("MISSING_DUPLICATED_OR_FOREIGN_SIGNAL: no fake coverage")
    if qdle.get("real_fundednext_fills") != 0 or qdle.get("certified") is not False:
        raise ValueError("experiment cannot claim authenticated fills/certification")
    if native.get("governance", {}).get("certification_claimed") is not False:
        raise ValueError("native ceiling must remain research-only")
    if qdle.get("economic_motor_mode") != "independent_four_motors":
        raise ValueError("all four motors must participate in experimental arm")
    if (qdle["research_financed_proposals"]
        + qdle["research_unfundable_or_invalid"] != 3368):
        raise ValueError("missing unfinanced opportunity accounting")
    if (qdle.get("intratrade_drawdown_measured") is not False
        or qdle.get("physical_broker_MT5_probe_used") is not False):
        raise ValueError("provider MTM observations cannot be invented")
    n_authorized = {sid for sid, x in native_by_id.items()
                    if Decimal(str(x["authorized_volume"])) > 0}
    q_financed = {sid for sid, x in qdle_by_id.items()
                  if Decimal(str(x.get("lots", "0"))) > 0}
    pairs = Counter()
    discrepancies = []
    for sid in source_ids:
        n = native_by_id[sid]
        q = qdle_by_id[sid]
        label = ("NATIVE_APPROVED" if sid in n_authorized else "NATIVE_NO_APPROVAL",
                 "QDLE_RESEARCH_FINANCED" if sid in q_financed else "QDLE_UNFUNDABLE")
        pairs["|".join(label)] += 1
        if len(discrepancies) < 40 and (sid in n_authorized) != (sid in q_financed):
            discrepancies.append({
                "signal_id": sid,
                "trader": n["trader_id"],
                "native_risk_decision": n.get("risk_decision"),
                "native_authorized_volume": n.get("authorized_volume"),
                "native_authorized_stop_risk_usd": n.get("authorized_stop_risk_usd"),
                "qdle_lots_research": q.get("lots"),
                "qdle_reason": q.get("reason", q.get("status")),
            })
    return {
        "schema": "qore.cibo.ceo.experimental-offline-replay-audit.v1",
        "authorization": "CEO_EXPERIMENTAL_REPLAY_ONLY",
        "source_signal_count": 3368,
        "paired_unique_signal_count": len(source_ids),
        "native_cibo_authorized_count": len(n_authorized),
        "qdle_four_motor_financed_hypotheses": len(q_financed),
        "overlap_native_authorized_and_qdle_financed": len(n_authorized & q_financed),
        "contingency_table_by_signal": dict(pairs),
        "mismatch_examples_first_40": discrepancies,
        "native_ceiling_research_capital_usd": native.get("ending_capital_usd"),
        "qdle_independent_proxy_qore_capital_usd": qdle.get("qore_ending_capital_usd"),
        "qdle_independent_proxy_dd_closed_pct": qdle.get("max_closed_equity_drawdown_pct"),
        "qdle_independent_proxy_profit_factor": qdle.get("profit_factor_proxy"),
        "qdle_proxy_open_commissions_usd": qdle.get("opening_commission_paid_proxy_usd"),
        "qdle_proxy_close_commissions_usd": qdle.get("closing_commission_paid_proxy_usd"),
        "qdle_proxy_total_roundtrip_commissions_usd": qdle.get("roundtrip_total_commission_committed_proxy_usd"),
        "native_and_qdle_pnl_are_not_economically_comparable": True,
        "same_cibo_strategy_and_qdle_actual_joint_execution": False,
        "cibo_source_lane_declared_by_native_receipts": all(
            "source_lane" in native_by_id[sid] for sid in n_authorized),
        "cibo_managed_exit_declared_by_native_receipts": all(
            "managed_exit_at" in native_by_id[sid] for sid in n_authorized),
        "cibo_4_votes_broker_signed": False,
        "real_mt5_fills": 0,
        "financial_certification": "REJECTED_NOT_REQUESTED_BY_EXPERIMENT",
        "research_certification_gates_are_nonblocking": [
            "Legacy Stack Quarantine", "Zero Open Work", "Phase20 Fresh OOS",
            "FINAL_INTEGRATED_CIBO_EXAM", "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
        ],
        "integrity_and_finance_gates_remain_enforced": [
            "sealed_3368_unique_ids", "no_fake_fills", "causal_replay_own_source",
            "qore_5pct_dynamic_risk", "physical_grid_min", "four_distinct_votes",
            "broker_fee_research_sensitivity_not_actual_commission",
            "per_signal_nonfinanciable_not_silently_dropped",
        ],
        "remaining_joint_replay_blockers": [
            "native decision receipts do not expose complete authenticated CIBO source allocation/Bank/Cushion",
            "native CIBO-managed exits and positions not emitted per trade for QDLE",
            "provider historical broker quote/margin/actual fees/deals absent",
            "native capital and QDLE research NAV timelines are NOT shared",
            "certification gates still RED where current evidence fails",
        ],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--native", type=Path, required=True)
    p.add_argument("--qdle", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = audit(*(json.loads(x.read_text(encoding="utf-8"))
                     for x in (a.manifest, a.native, a.qdle)))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    print("CEO_EXPERIMENTAL_REPLAY_3368", json.dumps({
        k: v for k, v in result.items() if k not in (
            "mismatch_examples_first_40", "remaining_joint_replay_blockers",
            "integrity_and_finance_gates_remain_enforced",
            "research_certification_gates_are_nonblocking",
        )}, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
