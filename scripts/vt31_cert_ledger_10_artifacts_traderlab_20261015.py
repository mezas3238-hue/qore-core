#!/usr/bin/env python3
"""Qualitative VT31 cert ledger: 8 source cases + 2 native TraderLab cases.

Conjunctive original methodology/cognition verdict is unchanged; extra
chrono-parity evidence does NOT confer author fidelity or human role signing.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.vt31_qualitative_method_cog_certificate_decision_20261015 import (
    G3_BLOB,
    _read_inputs,
    adjudicate_qualitative_certification,
)

PREREG = "8b3e0e17ce4011ae6bfff5ef46fb3242834cd617"
EXTRA = {
    "short12": (
        "11976412423",
        "VT31_G3_TRADERLAB_NATIVE_32X_QUALITATIVE_PARITY.json",
    ),
    "both24": (
        "11979797382",
        "VT31_TRADERLAB_NATIVE_32X_G3_COG_BIDIRECTIONAL_24_CASES.json",
    ),
}


def certify_extra_cognitive_parity(
    original: dict[str, Any],
    short12: dict[str, Any],
    both24: dict[str, Any],
) -> dict[str, Any]:
    """Recognize original-Cog parity only after exact causal semantic checks."""
    if (
        short12["cog_original_sha"]["git_blob_sha1"] != G3_BLOB
        or both24["original_g3_code_sha"]["git_blob_sha1"] != G3_BLOB
    ):
        raise ValueError("TRADERLAB_COG_G3_ORIGINAL_BLOB_MISMATCH")
    if (
        not short12["actual_native_trader_lab_schedule_used"]
        or not short12["all_trace_parity"]
        or short12["native_l3_real_candidate_qualified"]
        or short12["methodology_certified"]
        or short12["cognition_certified"]
        or len(short12["cases"]) != 12
    ):
        raise ValueError("TRADERLAB_12_CASE_SOURCE_PARITY_NOT_REPRODUCED")
    for case in short12["cases"]:
        if (
            case["normal_1x"] != case["traderlab_simulated_32x"]
            or case["native_schedule_acceleration_factor"] != 32
            or not case["parity_by_canonical_trace_and_source_sha256"]
            or case["real_traderlab_candidate_L3_certified"]
            or case["normal_1x"]["cog_original_traces"][0]["action"] != "WAIT"
        ):
            raise ValueError("TRADERLAB_12_CASE_COG_QUALITATIVE_DRIFT")
    if (
        not both24["native_traderlab_schedule_used"]
        or not both24["all_24_parity"]
        or both24["qualified_real_vt31_L3"]
        or both24["methodology_certified"]
        or both24["cognition_certified"]
        or both24["observed_CPU_speedup_32x"]
        or len(both24["cases"]) != 24
        or len({x["identity"] for x in both24["cases"]}) != 24
    ):
        raise ValueError("TRADERLAB_24_CASE_BIDIRECTIONAL_PARITY_NOT_REPRODUCED")

    sides = {"LONG": 0, "SHORT": 0}
    waits = 0
    sessions: set[str] = set()
    months: set[int] = set()
    for case in both24["cases"]:
        sides[case["side"]] += 1
        sessions.add(case["session"])
        months.add(case["month"])
        if (
            not case["ff_canonical_source_and_trace_identical"]
            or not case["ff_all_m1_closed_at_preserved"]
            or case["ff_acceleration_factor_simulated"] != 32
            or case["elapsed_normal_us"] != 32 * case["elapsed_simulated_ff_us"]
            or case["qualified_vt31_trader_lab_L3"]
            or case["certified_author_method"]
            or case["certified_cognition"]
            or case["orders"] != 0 or case["trader_sizing"] != 0
        ):
            raise ValueError("TRADERLAB_24_CASE_SOURCE_OR_COG_TRACE_DRIFT")
        first, last = case["original_cog_trace_before_and_after"]
        if first["action"] != "WAIT" or first["trade_authorized"]:
            raise ValueError("TRADERLAB_24_CASE_LOOKAHEAD_OR_AUTHORIZATION")
        if case["counterfactual_change_only_last_close"]:
            waits += 1
            if last["action"] != "WAIT":
                raise ValueError("TRADERLAB_24_CASE_INVALID_MSS_NOT_ABSTAINED")
        elif (
            last["action"] != case["side"]
            or last["target"] != ("150" if case["side"] == "LONG" else "80")
            or last["structure_level"] != (
                "134" if case["side"] == "LONG" else "96"
            )
        ):
            raise ValueError("TRADERLAB_24_CASE_ACTUAL_METHOD_TESIS_MUTATED")
    if (
        sides != {"LONG": 12, "SHORT": 12}
        or waits != 12
        or sessions != {"VT31_LONDON", "VT31_NY_AM", "VT31_NY_PM"}
        or months != {1, 7}
    ):
        raise ValueError("TRADERLAB_BIDIRECTIONAL_SESSION_DST_COUNTS_DRIFT")

    # Preserve all missing original requirements, do not award a cert.
    if (
        original["methodology"]["decision"] != "PENDIENTE"
        or original["cognition"]["decision"] != "PENDIENTE"
        or original["overall_method_cognitive_certified"]
    ):
        raise ValueError("ORIGINAL_METHOD_COG_REQUIREMENTS_ILLEGITIMATELY_PROMOTED")
    previous_gaps = tuple(original["cognition"]["missing_necessary_conditions"])
    previous_method_gaps = tuple(
        original["methodology"]["missing_necessary_conditions"]
    )
    original["cognition"]["conditions"][
        "COG_original_native_traderlab_1x_32x_full_semantic_parity"
    ] = True
    original["cognitive_acceleration_evidence"] = {
        "native_traderlab_schedule_32x_simulated": True,
        "real_CPU_speedup_proven": False,
        "original_G3_short_cases": 12,
        "original_G3_bidirectional_cases": 24,
        "long_cases": 12, "short_cases": 12, "wait_cases": 12,
        "all_closed_M1_asof_and_trace_hashes_equal": True,
        "real_traderlab_L3_certified": False,
        "economic_performance_used": False,
    }
    if (
        tuple(original["cognition"]["missing_necessary_conditions"])
        != previous_gaps
        or tuple(original["methodology"]["missing_necessary_conditions"])
        != previous_method_gaps
    ):
        raise ValueError("COGNITIVE_PARITY_EVIDENCE_CHANGED_CERT_REQUIRED_GAPS")
    original["prereg_added_lab_10_archive_commit"] = PREREG
    original["all_verified_artifact_count"] = 10
    original["methodology"]["decision"] = "PENDIENTE"
    original["cognition"]["decision"] = "PENDIENTE"
    original["overall_method_cognitive_certified"] = False
    return original


def run(root: Path) -> dict[str, Any]:
    raw = _read_inputs(root)
    prior = adjudicate_qualitative_certification(raw)
    additional = {}
    for name, (aid, filename) in EXTRA.items():
        file = root / aid / filename
        if not file.is_file():
            raise ValueError(f"MISSING_TRADERLAB_COG_IMMUTABLE_ARTIFACT:{name}")
        additional[name] = json.loads(file.read_text())
    return certify_extra_cognitive_parity(
        prior, additional["short12"], additional["both24"],
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--evidence-root", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    result = run(args.evidence_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "archives": result["all_verified_artifact_count"],
        "methodology": result["methodology"]["decision"],
        "cognition": result["cognition"]["decision"],
        "cognitive_lab_parity": result["cognitive_acceleration_evidence"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
