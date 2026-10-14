"""Independent QORE alpha-discovery triage from PREVIOUSLY CLOSED signed artifacts.

ZERO new prices, quotes, returns, trading hypotheses, p-values, selection or
re-optimization. Read exactly H-TOM-1, E3 Native and H-COT-2 final witnesses.
Three distinct failure mechanisms: absent robust gross, low effective N,
and lack of executable net prices/cost contract. Evidence-only inference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

TOM_RUN = 38502188181
TOM_SHA = "be77998d185165ff0d2cce320d015981c8a8c631"
TOM_PREREG = "358d2d0e9691a95bbd9c121ea62b0075c2182975"
E3_RUN = 38262585848
E3_SHA = "845a7e351c1641025a6131271ae3ada37ebf37f1"
CFTC_RUN = 38495515717
CFTC_PREREG = "1cca3399514125ba11ae446a059e09382c605d40"
MARKETS = ("SP500", "US30", "NAS100")
CFTC_MARKETS = ("WTI", "NG")


class EvidenceError(ValueError):
    """Reject missing, forged, unverified or inconsistent prior outcomes."""


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise EvidenceError("MISSING_EXACT_SIGNED_RESULT:" + path.name)
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_sha_file(root: Path, filename: str, ledger: str) -> Path:
    """Verify precisely the prior original code's SHA256SUMS manifest."""
    digest_file = root / ledger
    if not digest_file.is_file():
        raise EvidenceError("MISSING_SHA_LEDGER_" + ledger)
    entries: dict[str, str] = {}
    for line in digest_file.read_text(encoding="utf-8").splitlines():
        fragments = line.split()
        if len(fragments) != 2 or len(fragments[0]) != 64:
            raise EvidenceError("MALFORMED_SHA_LINE")
        sha, name = fragments
        if name in entries or "/" in name or "\\" in name or name.startswith("."):
            raise EvidenceError("UNSAFE_OR_DUPLICATE_LEDGER_PATH")
        if any(c not in "0123456789abcdef" for c in sha):
            raise EvidenceError("INVALID_SHA_CHARACTER")
        entries[name] = sha
    if filename not in entries:
        raise EvidenceError("MISSING_TARGET_FROM_SHA_LEDGER")
    for name, sha in entries.items():
        if not (root / name).is_file() or _sha256(root / name) != sha:
            raise EvidenceError("SIGNED_ARTIFACT_CHANGED_" + name)
    return root / filename


def _check_receipt(document: dict[str, Any]) -> None:
    recorded = document.get("receipt_sha256")
    data = {key: val for key, val in document.items() if key != "receipt_sha256"}
    serialized = json.dumps(
        data, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    if recorded != hashlib.sha256(serialized.encode()).hexdigest():
        raise EvidenceError("PRIOR_EXAM_RECEIPT_SHA256_MISMATCH")


def _check_e3(root: Path) -> dict[str, Any]:
    file = _verify_sha_file(
        root,
        "qore-native-e3-seven-method-block-shrinkage-posthoc.json",
        "OUTPUT_SHA256SUMS.txt",
    )
    if (root / "exact-E3-code-head-sha.txt").read_text().strip() != E3_SHA:
        raise EvidenceError("E3_ORIGINAL_CODE_SHA_CHANGED")
    doc = _read_json(file)
    if (
        doc.get("identity") != "QORE_NATIVE_E3_POSTHOC_SEVEN_METHOD_MULTIWEEK_SHRINKAGE_V1"
        or doc.get("source_33_signed_market_witnesses") != 33
        or doc.get("source_7_methods_per_market") != 7
        or doc.get("total_cells_source") != 231
        or doc.get("source_e1_code_head") !=
        "dfe78f115957a40f4188c30e78bd7f88c2ce6c42"
        or doc.get("original_2024_plus_OHLC_unopened") is not True
        or doc.get("traders_certified") != 0
    ):
        raise EvidenceError("E3_SOURCE_OR_OOS_CONTRACT_CHANGED")
    cohort = doc.get("cross_period_seven_method_descriptive_screen")
    if not isinstance(cohort, list) or len(cohort) != 7:
        raise EvidenceError("E3_NOT_SEVEN_METHOD_FAMILY")
    if len({x["method_id"] for x in cohort}) != 7:
        raise EvidenceError("DUPLICATE_E3_METHOD")
    if any(
        x["positive_gross_and_delta_both_periods_all_L"] is True
        or x["BH_q_below_10pct_both_periods_all_L"] is True
        for x in cohort
    ):
        raise EvidenceError("E3_PRIOR_CLOSURE_CONTRADICTS_ORIGINAL_CLAIM")
    return {
        "family": "QORE_NATIVE_E3_SEVEN_METHODS_33_MARKETS",
        "source_run_id": E3_RUN,
        "data_integrity": "PRIOR_ORIGINAL_ACTIONS_SHA_SUMS_VERIFIED",
        "unique_methods": 7,
        "source_market_method_cells": 231,
        "positive_gross_and_delta_both_periods_all_block_sensitivities": sum(
            x["positive_gross_and_delta_both_periods_all_L"] is True
            for x in cohort
        ),
        "positive_bh_fdr10_both_periods_all_blocks": sum(
            x["BH_q_below_10pct_both_periods_all_L"] is True for x in cohort
        ),
        "decision": "CLOSED_GROSS_NOT_ROBUST_AND_REPLICATED",
        "causal_2024_plus_holdout_unopened": True,
        "economic_net_trading_certified": False,
    }


def _check_tom(root: Path) -> dict[str, Any]:
    path = _verify_sha_file(
        root, "qore-tom-final-three-index.json", "SHA256SUMS.txt"
    )
    original_sha = (root / "exact-code-head-sha.txt").read_text().strip()
    if original_sha != TOM_SHA:
        raise EvidenceError("TOM_ORIGINAL_CODE_SHA_CHANGED")
    d = _read_json(path)
    _check_receipt(d)
    if (
        d.get("prereg_sha") != TOM_PREREG
        or d.get("verdict") != "NO_SUPPORT_UNDER_PREREG"
        or d.get("next_action") != "CLOSE_H_TOM_1_NO_PARAMETER_SEARCH"
        or d.get("holdout_2024_09_17_plus_consumed") is not False
        or d.get("broker_historical_net_executed") is not False
        or d.get("edge_certified") is not False
        or d.get("traders_certified") != 0
        or set(d.get("symbols", {})) != set(MARKETS)
    ):
        raise EvidenceError("TOM_PRIOR_SCIENTIFIC_CLOSURE_CHANGED")
    scores: dict[str, dict[str, float | int | bool]] = {}
    for symbol in MARKETS:
        witness = d["symbols"][symbol]
        if (
            witness.get("source_all_11_years_SHA_verified") is not True
            or witness.get("prices_post_2024_09_17_read") is not False
            or witness.get("historical_bidask_net_calculated") is not False
        ):
            raise EvidenceError("TOM_HISTORICAL_SOURCE_OR_NET_STATUS_CHANGED")
        dev, diag = witness["dev"], witness["diag"]
        if (
            dev["months"] != 70 or diag["months"] != 23
            or dev["adequate_months"] is not True
            or diag["adequate_months"] is not True
        ):
            raise EvidenceError("TOM_MONTH_COVERAGE_CHANGED")
        for window in (dev, diag):
            gross = window["gross_TOM_mean_bps"]
            control = window["gross_midmonth_control_mean_bps"]
            excess = window["paired_excess_mean_bps"]
            if (
                not isinstance(gross, (int, float))
                or abs((gross - control) - excess) > 1e-8
            ):
                raise EvidenceError("TOM_PAIRS_NOT_ARITHMETICALLY_CONSISTENT")
            if any(
                abs(window["gross_TOM_after_hypothetical_RT_cost_bps"][str(cost)]
                    - (gross - cost)) > 1e-8
                for cost in (5, 10, 20)
            ):
                raise EvidenceError("TOM_COST_STRESS_ARITHMETIC_DRIFT")
        gross_diag = float(diag["gross_TOM_mean_bps"])
        scores[symbol] = {
            "dev_months": dev["months"],
            "diag_months": diag["months"],
            "dev_TOM_gross_bps": float(dev["gross_TOM_mean_bps"]),
            "diag_TOM_gross_bps": gross_diag,
            "dev_paired_excess_bps": float(dev["paired_excess_mean_bps"]),
            "diag_paired_excess_bps": float(diag["paired_excess_mean_bps"]),
            "dev_delta_bootstrap_lower_95_bps": float(dev["bootstrap_lower_excess_bps"]),
            "diag_delta_bootstrap_lower_95_bps": float(diag["bootstrap_lower_excess_bps"]),
            "diag_absolute_gross_positive_before_costs": gross_diag > 0,
            "diag_possible_positive_mean_after_nonnegative_cost": gross_diag > 0,
        }
    if not all(scores[s]["diag_TOM_gross_bps"] < 0 for s in MARKETS):
        raise EvidenceError("POSTMORTEM_ASSERTION_ALL_THREE_GROSS_NEGATIVE_FALSE")
    if not (
        d["symbols"]["SP500"]["dev"]["verdict"] == "NO_SUPPORT"
        and d["symbols"]["SP500"]["diag"]["verdict"] == "NO_SUPPORT"
        and d["symbols"]["US30"]["diag"]["verdict"] == "NO_SUPPORT"
    ):
        raise EvidenceError("TOM_PRIOR_ORIGINAL_GATES_CHANGED")
    return {
        "family": "H_TOM_1_LONG_ONLY_US_INDICES",
        "source_run_id": TOM_RUN,
        "data_integrity": "PRIOR_ORIGINAL_ACTIONS_SHA_SUMS_AND_LOGICAL_RECEIPT_VERIFIED",
        "gross_per_market": scores,
        "three_of_three_diag_absolute_gross_negative": True,
        "best_case_net_cost_floor_bps": 0,
        "claim_scope": (
            "EXACT_TOM_PRECOMMITTED_LONG_ONLY_REFERENCE_STRATEGY_ONLY;"
            "ASSUMES_NONNEGATIVE_ALL_IN_EXECUTION_AND_FINANCING_COST;"
            "NOT_A_REFUTATION_OF_ALL_INDEX_ALPHA"
        ),
        "decision": "CLOSED_UNPROFITABLE_AVERAGE_GROSS_IN_DIAGNOSTIC",
        "net_trading_certified": False,
    }


def _check_cftc(root: Path) -> dict[str, Any]:
    raw = _read_json(root / "cftc_extreme_z2_final_exam.json")
    _check_receipt(raw)
    if (
        raw.get("prereg_commit") != CFTC_PREREG
        or raw.get("final_scientific_verdict") != "CLOSED_INCONCLUSIVE_LOW_POWER"
        or raw.get("holdout_2022_2024_opened") is not False
        or raw.get("native_futures_execution_data_available") is not False
        or raw.get("profit_factor_or_net_pnl_calculated") is not False
        or raw.get("trader_certified") is not False
        or set(raw.get("roots", {})) != set(CFTC_MARKETS)
    ):
        raise EvidenceError("CFTC_ORIGINAL_CLOSURE_CHANGED")
    observations: dict[str, Any] = {}
    for root in CFTC_MARKETS:
        line = raw["roots"][root]
        observations[root] = {}
        for window in ("dev", "diag"):
            view = line[window]
            if (
                view.get("decision") !=
                "INCONCLUSIVE_INSUFFICIENT_INDEPENDENT_EXTREMES"
                or view.get("exact_one_sided_p") is not None
                or view.get("accuracy") is not None
                or view["n_independent_events"] >= view["minimum_events"]
            ):
                raise EvidenceError("CFTC_EFFECT_SIZE_OR_POWER_WAS_REINTERPRETED")
            observations[root][window] = {
                "independent_effective_episodes": view["n_independent_events"],
                "minimum_needed_under_original_prereg": view["minimum_events"],
                "underpowered": True,
            }
    return {
        "family": "H_COT_2_EXTREME_POSITION_REVERSION",
        "source_run_id": CFTC_RUN,
        "data_integrity": "ORIGINAL_RECEIPT_VERIFIED",
        "power_splits": observations,
        "decision": "CLOSED_INCONCLUSIVE_INSUFFICIENT_INDEPENDENT_EVENTS",
        "trading_edge_refuted_universally": False,
        "economic_net_trading_certified": False,
    }


def review(tom: Path, e3: Path, cftc: Path) -> dict[str, Any]:
    first = _check_tom(tom)
    second = _check_e3(e3)
    third = _check_cftc(cftc)
    return {
        "schema": "qore.alpha-discovery.postmortem-three-closed-exams.v1",
        "study_kind": "REUSABLE_EVIDENCE_TRIAGE_NOT_A_NEW_HYPOTHESIS",
        "studies": [first, second, third],
        "executed_economic_gross_evidence": {
            "separate_mechanisms_audited": 2,
            "tom_primary_and_all_replicates_diag_gross_nonpositive": True,
            "native_e3_robust_positive_methods": 0,
        },
        "blocked_due_to_underpowered_events": [
            "H_COT_2_EXTREME_POSITION_REVERSION"
        ],
        "not_equivalent_failure_modes": True,
        "economic_next_step": (
            "FREEZE_SPONTANEOUS_HYPOTHESIS_ROUNDS;"
            "NEW_TEST_REQUIRES_IDENTIFIABLE_RISK_TRANSFER_OR_FLOW_MECHANISM,"
            "PREDECLARED_EXCLUSIVE_PRICE_SOURCE_AND_REALISTIC_COST_CEILING,"
            "EFFECTIVE_SAMPLE_POWER_AND_TRULY_FRESH_OOS"
        ),
        "result_is_certification": False,
        "all_existing_holdouts_respected": True,
        "future_trading_outcomes_read": False,
        "new_market_prices_downloaded": False,
        "historical_broker_net_calculated": False,
        "new_traders_certified": 0,
        "real_capital_or_live_authorized": False,
        "market_data_spend_usd": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tom_original")
    parser.add_argument("e3_original")
    parser.add_argument("cftc_original")
    parser.add_argument("destination")
    args = parser.parse_args()
    result = review(
        Path(args.tom_original), Path(args.e3_original), Path(args.cftc_original)
    )
    packed = json.dumps(
        result, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    result["receipt_sha256"] = hashlib.sha256(packed.encode()).hexdigest()
    file = Path(args.destination)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    for item in result["studies"]:
        print("ALPHA_PROGRAM_REVIEW", item["family"], item["decision"])
    print("ALPHA_PROGRAM_NEXT_STEP", result["economic_next_step"])
    print("ALPHA_PROGRAM_RECEIPT", result["receipt_sha256"])
    print("NO_NEW_PRICE_OUTCOMES_NO_TRADERS_NO_LIVE")


if __name__ == "__main__":
    main()
