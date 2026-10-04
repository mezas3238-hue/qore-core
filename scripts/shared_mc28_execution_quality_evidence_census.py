#!/usr/bin/env python3
"""Census sealed DEMO evidence for MC28 execution-quality deterioration."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

IDENTITY = "QORE_SHARED_MC28_EXECUTION_QUALITY_EVIDENCE_CENSUS_001"
EXPECTED_SCHEMA = "qore.cibo.ctrader_demo.empirical_slippage.v1"
MIN_ATTEMPTS_PER_WINDOW = 30
MIN_FILLS_PER_WINDOW = 20


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("sealed execution evidence must contain an object")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = _load(args.evidence)
    if payload.get("schema") != EXPECTED_SCHEMA:
        raise AssertionError("unexpected sealed DEMO execution schema")
    if payload.get("environment") != "demo":
        raise AssertionError("execution evidence must be cTrader DEMO")
    if payload.get("read_only") is not True:
        raise AssertionError("evidence census requires read-only source collection")
    if payload.get("broker_mutation_performed") is not False:
        raise AssertionError("evidence census cannot consume mutation-producing collection")

    observations = payload.get("observations")
    if not isinstance(observations, list):
        raise AssertionError("sealed DEMO observations missing")

    by_instrument = Counter(
        str(row.get("qore_symbol", ""))
        for row in observations
        if isinstance(row, dict) and row.get("qore_symbol")
    )
    real_fill_count = len(observations)
    provider_fill_evidence_found = real_fill_count > 0 and all(
        isinstance(row, dict)
        and row.get("fill_price") is not None
        and row.get("evidence_ref")
        and row.get("execution_at")
        for row in observations
    )
    rejection_population_found = any(
        isinstance(row, dict)
        and str(row.get("outcome", "")).upper() == "REJECTED"
        for row in observations
    )
    executable_bid_ask_found = bool(observations) and all(
        isinstance(row, dict)
        and row.get("quote_bid") is not None
        and row.get("quote_ask") is not None
        for row in observations
    )
    explicit_window_labels_found = bool(observations) and all(
        isinstance(row, dict)
        and str(row.get("window", "")).upper() in {"BASELINE", "RECENT"}
        for row in observations
    )
    baseline_window_present = any(
        isinstance(row, dict)
        and str(row.get("window", "")).upper() == "BASELINE"
        for row in observations
    )
    recent_window_present = any(
        isinstance(row, dict)
        and str(row.get("window", "")).upper() == "RECENT"
        for row in observations
    )
    per_instrument_fill_minimum_met = bool(by_instrument) and all(
        count >= MIN_FILLS_PER_WINDOW for count in by_instrument.values()
    )
    attempt_population_observable = any(
        isinstance(row, dict) and row.get("attempt_id") is not None
        for row in observations
    )

    reasons: list[str] = []
    if not provider_fill_evidence_found:
        reasons.append("NO_PROVIDER_ORIGINATED_FILL_EVIDENCE")
    if not rejection_population_found:
        reasons.append("NO_PROVIDER_REJECTION_POPULATION")
    if not executable_bid_ask_found:
        reasons.append("NO_PRE_SUBMIT_EXECUTABLE_BID_ASK")
    if not explicit_window_labels_found or not (
        baseline_window_present and recent_window_present
    ):
        reasons.append("NO_BASELINE_RECENT_WINDOW_SPLIT")
    if not per_instrument_fill_minimum_met:
        reasons.append("PER_INSTRUMENT_FILL_POPULATION_BELOW_20_PER_WINDOW")
    if not attempt_population_observable:
        reasons.append("ATTEMPT_POPULATION_30_PER_WINDOW_NOT_OBSERVABLE")

    result = {
        "identity": IDENTITY,
        "status": "INSUFFICIENT_REAL_DEMO_EXECUTION_EVIDENCE",
        "scientific_disposition": "INSUFFICIENT",
        "source_schema": payload.get("schema"),
        "source_run_id": "36927602692",
        "source_artifact_id": 11194039517,
        "source_read_only": True,
        "source_broker_mutation_performed": False,
        "real_fill_observation_count": real_fill_count,
        "per_instrument_fill_counts": dict(sorted(by_instrument.items())),
        "provider_fill_evidence_found": provider_fill_evidence_found,
        "provider_rejection_population_found": rejection_population_found,
        "pre_submit_executable_bid_ask_found": executable_bid_ask_found,
        "baseline_recent_window_split_found": (
            baseline_window_present and recent_window_present
        ),
        "per_instrument_minimum_fills_per_window": MIN_FILLS_PER_WINDOW,
        "minimum_attempts_per_window": MIN_ATTEMPTS_PER_WINDOW,
        "per_instrument_fill_minimum_met": per_instrument_fill_minimum_met,
        "attempt_population_observable": attempt_population_observable,
        "reason_codes": reasons,
        "execution_quality_completed_and_proven": False,
        "new_order_submission_for_this_diagnostic": False,
        "broker_mutation": False,
        "order_authority": False,
        "risk_authority": False,
        "sizing_authority": False,
        "capital_authority": False,
        "master_ledger_mutated": False,
        "protected_holdout_opened": False,
        "next_gate": (
            "WAIT_FOR_EXISTING_SEALED_REAL_DEMO_BASELINE_RECENT_ATTEMPT_FILL_"
            "REJECTION_POPULATION"
        ),
    }
    if result["scientific_disposition"] != "INSUFFICIENT":
        raise AssertionError("census must remain fail-closed")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
