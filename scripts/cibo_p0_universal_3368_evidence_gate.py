#!/usr/bin/env python3
"""P0 acceptance gate for the 3,368-signal CIBO/QDLE Trader Lab.

This is a fail-closed *evidence coverage* gate, not proof that a digest belongs
to a real Native MAX episode, that motor votes are independent, or that fills
are economically correct. Those require their own causal, crypto and physical
integration tests. In particular, do not paper over missing evidence by
synthesizing receipts from the legacy replay's mode/lot columns.
No broker/VPS access and no order_send.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

EXPECTED_SIGNALS = 3368
MOTORS = ("SIZING", "CIBO_COMPOUND", "ADAPTIVE_LEVERAGE",
          "PORTFOLIO_COMPOUND")
EXECUTION_STATES = {
    "PAPER_FILLED", "PAPER_PARTIALLY_FILLED", "PAPER_UNFILLED",
    "PAPER_UNFUNDABLE", "PAPER_OPEN", "PAPER_SETTLED",
    "INCOMPLETE_EVIDENCE", "INCOMPLETE_PRICE_PATH",
    "NO_EXECUTABLE_ENTRY", "CIBO_ZERO_RISK",
}
SHA_PREFIX = "sha256:"


def _aware_at(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    return dt if dt.tzinfo is not None and dt.utcoffset() is not None else None


def _digest(value: object) -> bool:
    return (isinstance(value, str) and value.startswith(SHA_PREFIX)
            and len(value) == 71
            and all(c in "0123456789abcdef" for c in value[7:]))


def _nonnegative(value: object) -> bool:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return False
    return amount.is_finite() and amount >= 0


def audit_universal_3368(manifest: dict, report: dict) -> dict:
    """Return an objective per-stage missing-evidence report, never a faux PASS.

    The gate requires one genuinely *new-formatted* event envelope for each
    stage. A present payload is only a prerequisite: independent test suites
    must establish authentic cognitive invocation and physical ledger safety.
    """
    opportunities = manifest.get("opportunities", [])
    rows = report.get("signal_decisions", [])
    defects: dict[str, list[str]] = defaultdict(list)

    if not isinstance(opportunities, list) or not isinstance(rows, list):
        return {"status": "FAIL", "reason": "malformed input arrays"}
    inputs = [r.get("signal_fingerprint") if isinstance(r, dict) else None
              for r in opportunities]
    outputs = [r.get("signal_fingerprint") if isinstance(r, dict) else None
               for r in rows]
    if len(inputs) != EXPECTED_SIGNALS or len(set(inputs)) != EXPECTED_SIGNALS or None in inputs:
        defects["source_cardinality"].append("input")
    if len(outputs) != EXPECTED_SIGNALS or len(set(outputs)) != EXPECTED_SIGNALS or None in outputs:
        defects["replay_cardinality"].append("output")
    if set(inputs) != set(outputs):
        defects["source_identity"].append("mismatched fingerprint sets")
    for row in rows:
        if not isinstance(row, dict):
            defects["malformed_rows"].append("non-object")
            continue
        sid = row.get("signal_fingerprint")
        if not isinstance(sid, str) or not sid:
            continue
        as_of = _aware_at(row.get("qdle_at"))
        if as_of is None:
            defects["missing_causal_clock"].append(sid)
            continue
        episode = row.get("cibo_native_episode")
        if not (isinstance(episode, dict)
                and _digest(episode.get("episode_digest"))
                and _aware_at(episode.get("observed_up_to"))
                and _aware_at(episode["observed_up_to"]) <= as_of):
            defects["cibo_episode"].append(sid)
        decision = row.get("cibo_management_decision")
        if not (isinstance(decision, dict)
                and _digest(decision.get("decision_digest"))
                and _aware_at(decision.get("decided_at"))
                and _aware_at(decision["decided_at"]) <= as_of
                and _nonnegative(decision.get("desired_risk_fraction"))
                and Decimal(str(decision["desired_risk_fraction"])) <= Decimal("0.05")
                and isinstance(decision.get("management_intent"), str)
                and bool(decision["management_intent"].strip())):
            defects["cibo_management_decision"].append(sid)
        motors = row.get("four_motor_receipts")
        if not isinstance(motors, dict) or set(motors) != set(MOTORS):
            defects["four_fresh_motor_votes"].append(sid)
        else:
            for name in MOTORS:
                vote = motors[name]
                if not (isinstance(vote, dict)
                        and vote.get("producer") == name
                        and vote.get("request_id") == sid
                        and _digest(vote.get("source_event_sha256"))
                        and _aware_at(vote.get("observed_at"))
                        and _aware_at(vote["observed_at"]) <= as_of
                        and type(vote.get("account_sequence")) is int
                        and vote["account_sequence"] > 0):
                    defects["four_fresh_motor_votes"].append(sid)
                    break
        qdle = row.get("qdle_physical_assessment")
        if not (isinstance(qdle, dict)
                and qdle.get("request_id") == sid
                and isinstance(qdle.get("state"), str) and qdle["state"]
                and _nonnegative(qdle.get("lots"))
                and type(qdle.get("account_sequence")) is int
                and qdle["account_sequence"] > 0
                and isinstance(qdle.get("binding_limits"), list)):
            defects["qdle_physical_assessment"].append(sid)
        outcome = row.get("execution_outcome")
        if not (isinstance(outcome, dict)
                and outcome.get("paper_status") in EXECUTION_STATES
                and outcome.get("request_id") == sid):
            defects["execution_outcome"].append(sid)
        # This checks a critical consistency, even when another stage is absent.
        if isinstance(outcome, dict) and isinstance(qdle, dict):
            lots = qdle.get("lots")
            if (_nonnegative(lots)
                    and Decimal(str(lots)) == 0
                    and outcome.get("paper_status") in
                    {"PAPER_FILLED", "PAPER_PARTIALLY_FILLED",
                     "PAPER_OPEN", "PAPER_SETTLED"}):
                defects["paper_fill_without_qdle_lot"].append(sid)
    defects = dict(defects)
    return {
        "schema": "qore.cibo.p0.universal-3368-evidence-gate.v1",
        "status": "FAIL" if defects else "PASS_EVIDENCE_SHAPE_ONLY",
        "source_signals": len(inputs),
        "output_signals": len(outputs),
        "unique_output_signals": len(set(outputs)),
        "defect_counts": {key: len(value) for key, value in sorted(defects.items())},
        "defect_examples": {key: value[:5] for key, value in sorted(defects.items())},
        "scope": "PAPER GitHub Trader Lab only",
        "certifies_native_cognition": False,
        "certifies_independent_motor_decisions": False,
        "certifies_broker_physics_or_profitability": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit_universal_3368(
        json.loads(args.manifest.read_text()),
        json.loads(args.replay.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("CIBO_P0_EVIDENCE_GATE", json.dumps(result, sort_keys=True), flush=True)
    return 0 if result["status"] == "PASS_EVIDENCE_SHAPE_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
