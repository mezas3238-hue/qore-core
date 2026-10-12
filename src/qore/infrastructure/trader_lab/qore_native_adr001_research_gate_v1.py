"""Validate QORE Native ADR001 research-stop ledger, no broker or price access.

A governance test: asserts statements and closure conditions are internally
consistent. It does not create evidence of net returns, causal edges, or
independent re-verification of original GitHub Actions artifacts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

IDENTITY = "QORE_NATIVE_ADR001_RESEARCH_STOP_LEDGER_V1"
EXPECTED_IDS = (
    ("H4_GROSS01_EURUSD", 822, 38203530559),
    ("H4_GROSS02_XAUUSD", 825, 38204480486),
    ("NY_OPEN_DRIVE03_NAS100", 827, 38205479893),
    ("GROSS04_ALL33_SWEEP_RECLAIM", 830, 38208073921),
)
G0_SHA = "1291d5c2efb4e51c2698ea25ad420a01a213dc405b5070c37efbce4131606b85"


def validate(data: dict[str, Any]) -> dict[str, Any]:
    """Reject any claim of independent repeated edges, 33 futures or LIVE."""
    if (
        data.get("identity") != IDENTITY
        or data.get("decision") != "PIVOT_TO_EXOGENOUS_FORCED_INDEX_FLOW_FEASIBILITY"
        or data.get("legacy_price_pattern_family") != "CLOSED_NO_SUPPORT_FOR_TESTED_IMPLEMENTATIONS"
        or data.get("g0_source_status") != "33_OF_33_M5_SHA_VERIFIED"
        or data.get("g0_source_bars") != 24377420
        or data.get("g0_original_markets") != 12
        or data.get("g0_new_markets") != 21
        or data.get("preregistered_native_attempts") != 4
        or data.get("completed_no_support") != 4
        or data.get("native_traders_certified") != 0
        or data.get("no_new_price_pattern_backtests_without_new_adr") is not True
        or data.get("no_future_prices_or_holdout_reopened") is not True
        or data.get("net_economics_authorized") is not False
        or data.get("historical_bidask_broker_cost_verified") is not False
        or data.get("news_asof_operational_compliance") is not False
        or data.get("production_untouched") is not True
    ):
        raise ValueError("Native closure requires exactly four NO_SUPPORT attempts and no live authorization")
    g0 = data.get("source_g0", {})
    if g0 != {"pr":829, "actions_run":38207337960, "manifest_sha256":G0_SHA}:
        raise ValueError("G0 original signed 33-source provenance drift")
    rows = data.get("tests")
    if not isinstance(rows, list) or len(rows) != 4:
        raise ValueError("QORE Native four prereg runs required")
    for expected, row in zip(EXPECTED_IDS, rows, strict=True):
        name, pr, run = expected
        if (
            row.get("code") != name
            or row.get("pr") != pr
            or row.get("actions_run") != run
            or row.get("result") != "NO_SUPPORT"
            or row.get("estimated_real_net") != "NOT_MEASURED"
            or not isinstance(row.get("prereg_sha"), str)
            or len(row["prereg_sha"]) != 40
            or not isinstance(row.get("dev_n"), int)
            or row["dev_n"] <= 0
            or not isinstance(row.get("diag_n"), int)
            or row["diag_n"] <= 0
        ):
            raise ValueError("Native historical prereg outcomes mutated or missing")
        for suffix in ("dev", "diag"):
            ci = row.get(f"{suffix}_CI_delta_bps")
            estimate = row.get(f"{suffix}_delta_bps")
            if not isinstance(ci, list) or len(ci) != 2 or not all(type(x) in (float, int) for x in ci):
                raise ValueError("CI bounds of paired delta required, not CI of absolute gross")
            if not ci[0] <= 0 <= ci[1]:
                raise ValueError("Native NO_SUPPORT intervals must include zero")
            if type(estimate) not in (int, float) or not ci[0] <= estimate <= ci[1]:
                raise ValueError("Paired point estimate inconsistent with signed CI")
    if (
        data.get("related_prior_work_without_native_prereg_verification") != ["RESET", "DRIVE"]
        or data.get("independence_correction") != "GROSS04_SYNCHRONIZED_WHOLE_UTC_WEEK_BLOCK_BOOTSTRAP"
        or data.get("factor_equivalent_count") != "NOT_ESTIMATED"
        or data.get("effective_sample_size") != "NOT_ESTIMATED"
        or data.get("proposed_new_research_gate") != "E0_INDEX_RECONSTITUTION_METADATA_POINT_IN_TIME_ONLY"
        or data.get("expected_e0_outcomes") != [
            "DATA_READY_FOR_PREREG", "SOURCE_BLOCKED", "STRUCTURAL_MECHANISM_NOT_TESTABLE"
        ]
        or data.get("futures_alternative") != "F0_FEASIBILITY_ONLY_H3_NOT_REOPENED"
    ):
        raise ValueError("no fictional effective N, known-as-of proof, or futures rescue allowed")
    return {
        "status": "ADR001_RESEARCH_CLASS_CLOSED_STRUCTURAL_E0_ONLY",
        "g0_market_sources": data["g0_original_markets"] + data["g0_new_markets"],
        "prereg_NO_SUPPORT": len(rows),
        "structural_price_outcomes_tested": 0,
        "certified_traders": 0,
        "net_or_live_authorized": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("ledger", type=Path)
    args = p.parse_args()
    print(json.dumps(validate(json.loads(args.ledger.read_text(encoding="utf-8"))),
                     sort_keys=True))


if __name__ == "__main__":
    main()
