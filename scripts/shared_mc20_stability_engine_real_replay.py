#!/usr/bin/env python3
"""Real source-only replay for MC-20 Stability Engine."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import shared_sti2_real_opportunity_discovery as source

from qore.infrastructure.core_stack_v2.stability_engine import (
    StabilityDomain,
    StabilityEvidence,
    StabilityState,
    build_stability_snapshot,
)

IDENTITY = "QORE_SHARED_MC20_STABILITY_ENGINE_REAL_REPLAY_001"


def _mean(*values: int) -> int:
    return sum(values) // len(values)


def _evidence(observation) -> tuple[StabilityEvidence, ...]:
    market_degradation = _mean(
        observation.structural_fragility_bps,
        observation.leader_divergence_bps,
        observation.regime_transition_bps,
    )
    market_stability = _mean(
        observation.data_integrity_bps,
        observation.leader_confirmation_bps,
        10_000 - observation.regime_transition_bps,
    )
    market_recovery = _mean(
        observation.acceptance_bps,
        observation.momentum_persistence_bps,
        observation.leader_confirmation_bps,
    )
    market_dislocation = _mean(
        observation.anomaly_bps,
        observation.liquidity_vacuum_bps,
        observation.regime_transition_bps,
    )

    cognition_degradation = _mean(
        10_000 - observation.data_integrity_bps,
        observation.anomaly_bps,
        observation.leader_divergence_bps,
    )
    cognition_stability = 10_000 - cognition_degradation
    cognition_recovery = _mean(
        observation.acceptance_bps,
        observation.leader_confirmation_bps,
    )

    systemic_degradation = _mean(
        observation.structural_fragility_bps,
        observation.anomaly_bps,
        observation.leader_divergence_bps,
    )
    systemic_stability = 10_000 - systemic_degradation
    systemic_recovery = _mean(
        observation.acceptance_bps,
        observation.momentum_persistence_bps,
    )

    refs = tuple(sorted(observation.provenance_refs))
    return (
        StabilityEvidence(
            domain=StabilityDomain.MARKET,
            evidence_available=True,
            stability_bps=market_stability,
            degradation_bps=market_degradation,
            recovery_bps=market_recovery,
            dislocation_bps=market_dislocation,
            evidence_refs=refs,
        ),
        StabilityEvidence(
            domain=StabilityDomain.QORE_CORE,
            evidence_available=False,
            stability_bps=0,
            degradation_bps=0,
            recovery_bps=0,
            dislocation_bps=0,
            evidence_refs=("mc20:qore-core-telemetry-unbound",),
        ),
        StabilityEvidence(
            domain=StabilityDomain.PROVIDER_BROKER,
            evidence_available=False,
            stability_bps=0,
            degradation_bps=0,
            recovery_bps=0,
            dislocation_bps=0,
            evidence_refs=("mc20:provider-broker-telemetry-unbound",),
        ),
        StabilityEvidence(
            domain=StabilityDomain.COGNITION,
            evidence_available=True,
            stability_bps=cognition_stability,
            degradation_bps=cognition_degradation,
            recovery_bps=cognition_recovery,
            dislocation_bps=observation.anomaly_bps,
            evidence_refs=refs,
        ),
        StabilityEvidence(
            domain=StabilityDomain.SYSTEMIC_STRESS,
            evidence_available=True,
            stability_bps=systemic_stability,
            degradation_bps=systemic_degradation,
            recovery_bps=systemic_recovery,
            dislocation_bps=systemic_degradation,
            evidence_refs=refs,
        ),
    )


def _partition(paths: dict[str, Path], partition: str) -> dict[str, object]:
    rows = source._aligned_source_rows(
        paths,
        partition=partition,
        require_future=False,
    )
    deterministic = 0
    channel_counts = {
        domain.value: Counter() for domain in StabilityDomain
    }
    for observation, _states, _pre, future in rows:
        if future is not None:
            raise AssertionError("MC20 source replay cannot attach future evidence")
        first = build_stability_snapshot(_evidence(observation))
        second = build_stability_snapshot(_evidence(observation))
        deterministic += int(first.fingerprint() == second.fingerprint())
        for item in first.channels:
            channel_counts[item.domain.value][item.state.value] += 1

    passed = bool(rows) and deterministic == len(rows)
    return {
        "partition": partition,
        "observation_count": len(rows),
        "deterministic_count": deterministic,
        "state_counts": {
            domain: dict(sorted(counter.items()))
            for domain, counter in sorted(channel_counts.items())
        },
        "qore_core_unknown_count": channel_counts[
            StabilityDomain.QORE_CORE.value
        ][StabilityState.UNKNOWN.value],
        "provider_broker_unknown_count": channel_counts[
            StabilityDomain.PROVIDER_BROKER.value
        ][StabilityState.UNKNOWN.value],
        "pass": passed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r6", "r5"):
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    def paths(name: str) -> dict[str, Path]:
        return {
            "NAS100": getattr(args, f"{name}_nas"),
            "SP500": getattr(args, f"{name}_sp"),
            "US30": getattr(args, f"{name}_us"),
        }

    results = {
        name: _partition(paths(name), f"mc20_{name}")
        for name in ("r6", "r5")
    }
    passed = all(bool(item["pass"]) for item in results.values())
    payload = {
        "identity": IDENTITY,
        "status": (
            "MC20_STABILITY_ENGINE_MARKET_COGNITION_SYSTEMIC_REAL_BOUND_PASS"
            if passed
            else "MC20_STABILITY_ENGINE_REAL_BOUND_FAIL"
        ),
        "results": results,
        "domains_distinct": True,
        "market_price_used_as_core_health_proxy": False,
        "market_price_used_as_provider_health_proxy": False,
        "qore_core_operational_telemetry_bound": False,
        "provider_broker_operational_telemetry_bound": False,
        "states_are_trading_commands": False,
        "dependency": "B_AND_RUNTIME_OPERATIONAL_TELEMETRY_BINDING",
        "mc20_completed_and_proven": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
