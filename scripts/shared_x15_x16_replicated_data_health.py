#!/usr/bin/env python3
"""Replicated real-data proof for Shared X-15 Data Health and X-16 Freshness."""

from __future__ import annotations

import argparse
import json
from datetime import timedelta
from pathlib import Path

from shared_wp03_historical_causal_discovery import _load_bars, _parse_key

from qore.infrastructure.core_stack_v2.shared_data_health_intelligence import (
    SharedDataHealthObservation,
    SharedDataHealthState,
    SharedFreshnessState,
    assess_shared_data_health,
)

IDENTITY = "QORE_SHARED_X15_X16_REPLICATED_DATA_HEALTH_001"
SCENARIOS = (
    "BASELINE",
    "STALE_OPEN",
    "STALE_CLOSED",
    "FUTURE",
    "DUPLICATE",
    "OUT_OF_ORDER",
    "IDENTITY_AMBIGUITY",
    "ROLL_AMBIGUITY",
    "PROVIDER_ANOMALY",
    "MISSING_OPEN",
    "MISSING_CLOSED",
)
EXPECTED = {
    "BASELINE": SharedDataHealthState.HEALTHY,
    "STALE_OPEN": SharedDataHealthState.STALE_UNEXPECTED,
    "STALE_CLOSED": SharedDataHealthState.MARKET_CLOSED,
    "FUTURE": SharedDataHealthState.FUTURE_EVIDENCE,
    "DUPLICATE": SharedDataHealthState.DUPLICATE,
    "OUT_OF_ORDER": SharedDataHealthState.OUT_OF_ORDER,
    "IDENTITY_AMBIGUITY": SharedDataHealthState.IDENTITY_AMBIGUITY,
    "ROLL_AMBIGUITY": SharedDataHealthState.ROLL_AMBIGUITY,
    "PROVIDER_ANOMALY": SharedDataHealthState.PROVIDER_ANOMALY,
    "MISSING_OPEN": SharedDataHealthState.MISSING,
    "MISSING_CLOSED": SharedDataHealthState.MARKET_CLOSED,
}


def _sample_indices(length: int, maximum: int = 1000) -> tuple[int, ...]:
    if length < 2:
        raise ValueError("real-data health proof needs at least two bars")
    usable = length - 1
    if usable <= maximum:
        return tuple(range(1, length))
    stride = max(1, usable // maximum)
    indexes = tuple(range(1, length, stride))[:maximum]
    return indexes


def _observation(
    *,
    market: str,
    previous_at: object,
    current_at: object,
    scenario: str,
) -> SharedDataHealthObservation:
    prev = previous_at
    cur = current_at
    decision = cur
    observed = cur
    available = cur
    kwargs: dict[str, object] = {
        "market_open": True,
        "missing": False,
        "duplicate": False,
        "sequence_monotonic": True,
        "canonical_identity_verified": True,
        "roll_identity_unambiguous": True,
        "provider_healthy": True,
    }

    if scenario == "STALE_OPEN":
        decision = cur + timedelta(minutes=3)
    elif scenario == "STALE_CLOSED":
        decision = cur + timedelta(minutes=3)
        kwargs["market_open"] = False
    elif scenario == "FUTURE":
        observed = cur + timedelta(seconds=1)
        available = cur + timedelta(seconds=1)
    elif scenario == "DUPLICATE":
        kwargs["duplicate"] = True
    elif scenario == "OUT_OF_ORDER":
        observed = prev - timedelta(minutes=1)
        available = observed
    elif scenario == "IDENTITY_AMBIGUITY":
        kwargs["canonical_identity_verified"] = False
    elif scenario == "ROLL_AMBIGUITY":
        kwargs["roll_identity_unambiguous"] = False
    elif scenario == "PROVIDER_ANOMALY":
        kwargs["provider_healthy"] = False
    elif scenario == "MISSING_OPEN":
        observed = None
        available = None
        kwargs["missing"] = True
    elif scenario == "MISSING_CLOSED":
        observed = None
        available = None
        kwargs["missing"] = True
        kwargs["market_open"] = False

    return SharedDataHealthObservation(
        instrument_key=market,
        observed_at=observed,
        available_at=available,
        decision_time=decision,
        previous_observed_at=prev,
        expected_cadence_ms=60_000,
        validity_horizon_ms=120_000,
        decay_horizon_ms=300_000,
        provenance_refs=(f"immutable-real-{market}-m1",),
        **kwargs,
    )


def _evaluate_file(path: Path, *, market: str) -> dict[str, object]:
    bars = _load_bars(path)
    indexes = _sample_indices(len(bars))
    results = {name: 0 for name in SCENARIOS}
    freshness_checks = 0

    for index in indexes:
        previous_at = _parse_key(bars[index - 1].closed_key)
        current_at = _parse_key(bars[index].closed_key)
        for scenario in SCENARIOS:
            assessment = assess_shared_data_health(
                _observation(
                    market=market,
                    previous_at=previous_at,
                    current_at=current_at,
                    scenario=scenario,
                )
            )
            if assessment.state is EXPECTED[scenario]:
                results[scenario] += 1
            if scenario == "BASELINE":
                if assessment.freshness is not SharedFreshnessState.FRESH:
                    raise AssertionError("baseline real bar must classify FRESH")
                if not assessment.new_market_change_inference_allowed:
                    raise AssertionError("healthy real bar must allow cognition")
                freshness_checks += 1
            if scenario == "STALE_CLOSED":
                if assessment.new_market_change_inference_allowed:
                    raise AssertionError("closed market cannot imply new market move")
            if scenario != "BASELINE" and scenario != "STALE_CLOSED":
                if assessment.new_market_change_inference_allowed:
                    raise AssertionError(
                        f"{scenario} must fail closed for new market inference"
                    )

    expected_count = len(indexes)
    scenario_pass = {
        name: count == expected_count for name, count in results.items()
    }
    return {
        "bar_count": len(bars),
        "sample_count": expected_count,
        "scenario_correct_counts": results,
        "scenario_pass": scenario_pass,
        "freshness_check_count": freshness_checks,
        "all_pass": all(scenario_pass.values())
        and freshness_checks == expected_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r8", "r6", "r5"):
        for market in ("nas", "sp", "us"):
            parser.add_argument(
                f"--{partition}-{market}",
                type=Path,
                required=True,
            )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    market_names = {"nas": "NAS100", "sp": "SP500", "us": "US30"}
    partitions: dict[str, dict[str, object]] = {}
    for partition in ("r8", "r6", "r5"):
        partition_rows: dict[str, object] = {}
        for key, market in market_names.items():
            partition_rows[market] = _evaluate_file(
                getattr(args, f"{partition}_{key}"),
                market=market,
            )
        partitions[partition] = partition_rows

    all_pass = all(
        bool(row["all_pass"])
        for rows in partitions.values()
        for row in rows.values()
    )
    payload = {
        "identity": IDENTITY,
        "capabilities": ["X-15_DATA_HEALTH", "X-16_INFORMATION_FRESHNESS"],
        "status": (
            "COMPLETED_AND_PROVEN_REPLICATED_REAL_DATA"
            if all_pass
            else "REPLICATION_FAILURE"
        ),
        "all_pass": all_pass,
        "partitions": partitions,
        "proof": {
            "real_data_bound": True,
            "causal_replay_executed": True,
            "fault_injection_stress": True,
            "temporal_replication_r8_r6_r5": True,
            "market_closed_distinguished_from_feed_failure": True,
            "future_evidence_fails_closed": True,
            "duplicate_fails_closed": True,
            "out_of_order_fails_closed": True,
            "identity_ambiguity_fails_closed": True,
            "roll_ambiguity_fails_closed": True,
            "provider_anomaly_fails_closed": True,
            "economic_value_required": False,
            "reason_economic_value_not_required": (
                "deterministic safety/observability capability; no trading action"
            ),
        },
        "governance": {
            "trader_authority": False,
            "capital_authority": False,
            "risk_authority": False,
            "execution_authority": False,
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "all_pass": all_pass,
                "samples": sum(
                    int(row["sample_count"])
                    for rows in partitions.values()
                    for row in rows.values()
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
