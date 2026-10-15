#!/usr/bin/env python3
"""VT31 methodology/cognition Ultra Fast batch, borrowing Trader Lab's fork pattern.

Preload authenticated NAS100 M1 and original 775-day TTrades census ONCE,
then fork two bounded read-only M3/M4/M5 source witnesses. Compare full
canonical SHA256 of every cognitive case against the original scalar
reference. No performance, orders, fills, stop, sizing, or cert minting.
"""
from __future__ import annotations

import argparse
import copy
import importlib
import json
import multiprocessing as mp
import os
import time
from hashlib import sha256
from pathlib import Path
from typing import Any

from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    M1_TOTAL,
    MARKET_SHA,
    collect_hours,
    hash_file,
    market_rows,
    run_census,
)

PREREG = "c2473687ccdf0989cd721818bd2e61073ee3e583"
SCHEMA = "VT31_METHOD_COG_TRADER_LAB_SHARED_SOURCE_ULTRAFAST_PARITY_V1"
SOURCES = {
    "M3_WAIT_V2": (
        "scripts.vt31_m3_ttrades_cog_wait_v2_20261015",
        "audit_483_real_first_returns",
        "frozen_first_returns",
    ),
    "M4_FAMILY": (
        "scripts.vt31_m4_source_family_cognitive_witness_20261015",
        "audit_483",
        "frozen_M3_first_return_cases",
    ),
    "M5_CAUSATIVE_SWING": (
        "scripts.vt31_m5_swing_causation_witness_20261015",
        "audit_483",
        "cases_frozen",
    ),
    "M4_M5_AUTHOR_COMPONENTS": (
        "scripts.vt31_m4_m5_author_semantics_bridge_20261015",
        "audit_frozen_cases",
        "frozen_real_M1_cases",
    ),
}
FROZEN_STATES = {
    "MSS_ATTESTED_CONTEXT_ONLY": 128,
    "FIRST_RETURN_NO_QORE_MSS": 483,
    "SWEEP_NO_RETURN": 92,
    "NO_SWEEP": 65,
    "INCOMPLETE_M1_HOURS": 6,
    "REJECTED_SOURCE": 1,
}
_GROUPS: dict | None = None
_CENSUS: dict | None = None


def canonical_sha256(data: dict[str, Any]) -> str:
    """Hash FULL result, including every day and timestamp, not just counts."""
    return sha256(json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")).hexdigest()


def frozen_census_copy(requested_groups: dict) -> dict:
    """Never allow one fork task to corrupt or mutate source census."""
    if requested_groups is not _GROUPS or _CENSUS is None:
        raise ValueError("UNAUTHENTICATED_OR_UNSHARED_CENSUS_SOURCE")
    return copy.deepcopy(_CENSUS)


def _call(key: str, groups: dict, *, reuse_census: bool) -> dict[str, Any]:
    """The imported original script is never edited; inject read-only cache
    exclusively in a temporary child process with a try/finally restore.
    """
    if key not in SOURCES:
        raise ValueError("UNKNOWN_COGNITIVE_GATE")
    module_name, func_name, case_key = SOURCES[key]
    module = importlib.import_module(module_name)
    producer = getattr(module, func_name)
    original = module.run_census
    if reuse_census:
        module.run_census = frozen_census_copy
    try:
        result = producer(groups)
    finally:
        module.run_census = original
    if (
        not isinstance(result, dict) or result.get(case_key) != 483
        or result.get("trader_certified", False) is not False
    ):
        raise AssertionError(f"NON_FROZEN_OR_FALSE_CERTIFIED_COG_GATE:{key}")
    return result


def _fork_gate(key: str) -> dict[str, object]:
    """Linux fork inherits already-validated tuples copy-on-write."""
    if _GROUPS is None or _CENSUS is None:
        raise ValueError("ULTRAFAST_PRELOAD_NOT_PRESENT")
    start = time.monotonic()
    result = _call(key, _GROUPS, reuse_census=True)
    return {
        "gate": key,
        "full_cognitive_casebook_sha256": canonical_sha256(result),
        "cognitive_case_count": 483,
        "duration_s": round(time.monotonic()-start, 6),
        "worker_pid_present": os.getpid() > 0,
    }


def run_replay_batch(
    market: Path, *, parity: bool, workers: int = 2,
) -> dict[str, object]:
    global _GROUPS, _CENSUS  # noqa: PLW0603
    if workers not in (1, 2):
        raise ValueError("BOUNDED_FORK_WORKERS_MUST_BE_1_OR_2")
    if hash_file(market) != MARKET_SHA:
        raise ValueError("ORIGINAL_3Y_M1_SHA256_NOT_MATCH")
    load_start = time.monotonic()
    groups, count = collect_hours(market_rows(market))
    if count != M1_TOTAL:
        raise AssertionError("ORIGINAL_M1_COUNT_DRIFT")
    census = run_census(groups)
    if census["observed_days_total"] != 775 or census["state_counts"] != FROZEN_STATES:
        raise AssertionError("FROZEN_775_TTRADES_SOURCE_CENSUS_CHANGED")
    source_load_s = time.monotonic()-load_start
    _GROUPS, _CENSUS = groups, census

    baseline: dict[str, dict[str, object]] = {}
    scalar_duration = 0.0
    if parity:
        for key in SOURCES:
            start = time.monotonic()
            result = _call(key, groups, reuse_census=False)
            elapsed = time.monotonic()-start
            scalar_duration += elapsed
            baseline[key] = {
                "full_cognitive_casebook_sha256": canonical_sha256(result),
                "duration_s": round(elapsed, 6),
            }

    batch_start = time.monotonic()
    # Exactly the Trader Lab design: preloaded immutable parent state,
    # forked workers with copy-on-write source, zero intermediary raw dumps.
    context = mp.get_context("fork")
    with context.Pool(processes=workers, maxtasksperchild=2) as pool:
        results = pool.map(_fork_gate, tuple(SOURCES))
    batch_duration = time.monotonic()-batch_start
    keys = {x["gate"] for x in results}
    if keys != set(SOURCES) or len(results) != len(SOURCES):
        raise AssertionError("ULTRAFAST_WORKER_MISSING_OR_DUPLICATE")
    if parity:
        for x in results:
            expected = baseline[x["gate"]]["full_cognitive_casebook_sha256"]
            if x["full_cognitive_casebook_sha256"] != expected:
                raise AssertionError(f"SCALAR_ULTRAFAST_COGNITIVE_PARITY_BROKEN:{x['gate']}")

    return {
        "schema": SCHEMA,
        "pre_code_prereg_commit": PREREG,
        "original_market_sha256": MARKET_SHA,
        "original_market_M1_total": count,
        "original_days": 775,
        "frozen_first_return_contexts": 483,
        "source_data_development_already_seen_not_oos": True,
        "acceleration_architecture": (
            "TRADER_LAB_ULTRAFAST_PRELOAD_ONCE_FORK_COPY_ON_WRITE"
        ),
        "external_reference": "https://github.com/mezas3238-hue/qore-core/pull/730",
        "qore_research_reference": "https://github.com/mezas3238-hue/qore-core/pull/908",
        "bounded_fork_workers": workers,
        "all_full_casebook_sha256_scalar_match": bool(parity),
        "scalar_reference": baseline if parity else None,
        "ultrafast_gate_records": results,
        "timings_wall_seconds_not_market_metrics": {
            "source_load_and_single_census": round(source_load_s, 6),
            "scalar_gate_total_excluding_load": (
                round(scalar_duration, 6) if parity else None
            ),
            "ultrafast_batch_excluding_load": round(batch_duration, 6),
            "speedup_scalar_gate_total_divided_by_batch": (
                round(scalar_duration/batch_duration, 4)
                if parity and batch_duration > 0 else None
            ),
        },
        "m3_m4_m5_author_method_certified": False,
        "m3_m4_m5_cognition_certified": False,
        "external_m6_dual_signatures_verified": False,
        "trader_certified": False,
        "economic_metrics_calculated": False,
        "vt31_sizing_calculated": False,
        "orders_ack_fills": 0,
        "live_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, choices=(1, 2), default=2)
    parser.add_argument("--parity", action="store_true")
    args = parser.parse_args()
    report = run_replay_batch(
        args.market, parity=args.parity, workers=args.workers,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(
        report, indent=2, sort_keys=True,
    )+"\n", encoding="utf-8")
    print(json.dumps({
        "source_M1": report["original_market_M1_total"],
        "days": report["original_days"],
        "cognitive_cases": report["frozen_first_return_contexts"],
        "full_casebook_scalar_ultrafast_parity": (
            report["all_full_casebook_sha256_scalar_match"]
        ),
        "gate_hashes": {
            row["gate"]: row["full_cognitive_casebook_sha256"]
            for row in report["ultrafast_gate_records"]
        },
        "actual_wall_timings": report["timings_wall_seconds_not_market_metrics"],
        "trader_certified": False,
        "economic_metrics_calculated": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
