"""Pre-registered QORE synthesis of THREE CRT sources, strictly research-only.

Specification: docs/research/VT08_CRT_3_FUENTES_QORE_V1_PREREG_2026-10-15.md
The strategy is invented/engineered by QORE with 3-source CRT context; it is
NOT a claim that Romeo, SpeculatorFL, or TraderFlameseN authored this exact
algorithm. It may not enter an order, assign risk/lotage, or certify itself.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_gm3_real_case_safety import (
    audit_blind_case,
)

SCHEMA = "qore.vt08.crt_three_source_candidate_v1.development_only.v1"
POLICY_ID = "VT08_CRT_THREE_SOURCE_QORE_V1"


def _direction(c1: dict[str, Any], c2: dict[str, Any]) -> str | None:
    """One-side HTF/M15 price purge and close *strictly* inside old range."""
    lo1, hi1 = c1["low_relative"], c1["high_relative"]
    close2 = c2["close_relative"]
    if not lo1 < close2 < hi1:
        return None
    if c2["low_relative"] < lo1 and c2["high_relative"] <= hi1:
        return "BULLISH"
    if c2["high_relative"] > hi1 and c2["low_relative"] >= lo1:
        return "BEARISH"
    return None


def evaluate_three_source_case(case: dict[str, Any]) -> dict[str, Any]:
    """Hypothesize one H4 C1 -> H4 C2 -> M15 C1/C2 source-neutral sequence."""
    audit_blind_case(case)  # causality, closed H4/M15, no C3 future and no sizing
    h4c1 = case["parent_H4_C1_ohlc"]
    h4c2 = case["parent_H4_C2_ohlc"]
    m15 = case["M15_observed_prefix_through_C2"]
    if len(m15) != 2:
        raise ValueError("V1 prereg requires exactly the first TWO closed M15 bars")
    m1, m2 = m15
    h4_dir = _direction(h4c1, h4c2)
    m15_dir = _direction(m1, m2)
    status, reason = "ABSTAIN", "H4_ONE_SIDE_SWEEP_AND_RECLAIM_ABSENT"
    if h4_dir:
        if not m15_dir:
            status, reason = "WAIT", "M15_CONFIRMATION_ABSENT_OR_AMBIGUOUS"
        elif m15_dir != h4_dir:
            status, reason = "ABSTAIN", "M15_OPPOSES_H4_PARENT"
        elif (
            (h4_dir == "BULLISH" and 2 * m2["close_relative"] <=
             m1["high_relative"] + m1["low_relative"])
            or (h4_dir == "BEARISH" and 2 * m2["close_relative"] >=
                m1["high_relative"] + m1["low_relative"])
        ):
            status, reason = "WAIT", "M15_CLOSE_NOT_ON_FAVORABLE_SIDE_OF_MIDPOINT"
        elif (
            (h4_dir == "BULLISH" and 2 * m2["close_relative"] >=
             h4c1["high_relative"] + h4c1["low_relative"])
            or (h4_dir == "BEARISH" and 2 * m2["close_relative"] <=
                h4c1["high_relative"] + h4c1["low_relative"])
        ):
            status, reason = "ABSTAIN", "H4_MIDPOINT_DOL_ALREADY_CONSUMED"
        else:
            status, reason = (
                "CONCEPTUAL_CANDIDATE", "QORE_V1_H4_PURGE_M15_RECLAIM_TARGET_AHEAD"
            )
    return {
        "schema": SCHEMA,
        "case_id": case["case_id"],
        "market": case["market"],
        "decision_clock_utc": case["decision_clock_utc"],
        "policy_id": POLICY_ID,
        "source_policy": "THREE_SOURCE_QORE_ENGINEERING_UNAPPROVED",
        "htf_direction_from_closed_candles": h4_dir,
        "ltf_direction_from_closed_candles": m15_dir,
        "conceptual_state": status,
        "why": reason,
        "h4_reference": "H4_C1_PREVIOUS_CLOSED_RANGE_QORE_POLICY",
        "h4_target_midpoint_double_relative": (
            h4c1["low_relative"] + h4c1["high_relative"]
        ),
        "invalidating_m15_extreme_relative": (
            m2["low_relative"] if h4_dir == "BULLISH"
            else m2["high_relative"] if h4_dir == "BEARISH" else None
        ),
        "not_trading_signal": True,
        "not_certified": True,
        "no_broker_authority": True,
        "no_capital_or_volume_authority": True,
        "no_sizing_used": True,
        "fresh_holdout": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("blind_casebook", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    cases = [
        json.loads(line) for line in args.blind_casebook.read_text().splitlines()
        if line.strip()
    ]
    out = [evaluate_three_source_case(case) for case in cases]
    if not out or len({c["case_id"] for c in out}) != len(out):
        raise ValueError("empty or duplicated real case cohort")
    counts = Counter(row["conceptual_state"] for row in out)
    manifest = {
        "schema": SCHEMA,
        "policy_id": POLICY_ID,
        "cases": len(out),
        "states": dict(sorted(counts.items())),
        "not_a_fresh_holdout": True,
        "no_profit_loss_calculated": True,
        "no_sizing_or_broker_order": True,
        "model_authority_adjudication_complete": False,
        "GM1_PASS": False,
        "GM2_PASS": False,
        "GM3_PASS": False,
        "GM4_PASS": False,
        "GM5_ISSUED": False,
        "GLOBAL_CERTIFIED": False,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "three-source-qore-v1-summary.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    )
    with (args.output / "three-source-qore-v1-dev-ledger.jsonl").open("w") as f:
        for row in out:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
