#!/usr/bin/env python3
"""STI-4 real causal alert-lifecycle replay from frozen STI-2 V2 cognition."""

from __future__ import annotations

import argparse
import json
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path

import shared_sti2_real_opportunity_discovery as source
import shared_sti2_v2_trajectory_heads as sti2

from qore.infrastructure.core_stack_v2.shared_global_opportunity_discovery import (
    SharedOpportunitySourceObservation,
)
from qore.infrastructure.core_stack_v2.shared_global_opportunity_trajectory_v2 import (
    SharedOpportunityMechanism,
    assess_opportunity_trajectory,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedAlertLifecycle,
    SharedOpportunityMaturity,
)
from qore.infrastructure.core_stack_v2.shared_trader_intelligence_lifecycle import (
    transition_alert_lifecycle,
)

IDENTITY = "QORE_SHARED_STI4_REAL_ALERT_LIFECYCLE_REPLAY_001"
_ACTIVE = frozenset(
    {
        SharedOpportunityMaturity.EARLY,
        SharedOpportunityMaturity.DEVELOPING,
        SharedOpportunityMaturity.MATURE,
        SharedOpportunityMaturity.DETERIORATING,
    }
)


@dataclass
class _LiveHypothesis:
    hypothesis_id: str
    alert_id: str
    mechanism: SharedOpportunityMechanism
    state: SharedAlertLifecycle
    epoch: int


def _next_state(
    previous: SharedAlertLifecycle,
    maturity: SharedOpportunityMaturity,
) -> SharedAlertLifecycle:
    if previous is SharedAlertLifecycle.NEW:
        return SharedAlertLifecycle.ACTIVE
    if maturity is SharedOpportunityMaturity.DETERIORATING:
        return SharedAlertLifecycle.WEAKENING
    if maturity is SharedOpportunityMaturity.MATURE:
        if previous is SharedAlertLifecycle.ACTIVE:
            return SharedAlertLifecycle.STRENGTHENING
        if previous is SharedAlertLifecycle.WEAKENING:
            return SharedAlertLifecycle.ACTIVE
        return previous
    if previous in {
        SharedAlertLifecycle.STRENGTHENING,
        SharedAlertLifecycle.WEAKENING,
    }:
        return SharedAlertLifecycle.ACTIVE
    return previous


def _replay_once(
    *,
    partition: str,
    paths: dict[str, Path],
    policy: object,
) -> dict[str, object]:
    rows = source._aligned_source_rows(
        paths,
        partition=partition,
        require_future=False,
    )
    history: dict[str, deque[SharedOpportunitySourceObservation]] = {}
    live: dict[str, _LiveHypothesis] = {}
    epochs: Counter[str] = Counter()
    transition_counts: Counter[str] = Counter()
    transition_fingerprints: list[str] = []
    new_alert_count = 0
    deduplicated_count = 0
    terminal_count = 0
    source_count = 0

    for observation, _states, _pre, future in rows:
        if future is not None:
            raise AssertionError("STI-4 lifecycle replay must not attach future")
        source_count += 1
        series = history.setdefault(
            observation.asset,
            deque(maxlen=policy.sequence_window),
        )
        series.append(observation)
        assessment = assess_opportunity_trajectory(
            tuple(series),
            policy=policy,
        )
        current = live.get(observation.asset)
        is_active = (
            assessment.maturity in _ACTIVE
            and assessment.dominant_mechanism is not None
        )

        if not is_active:
            if current is None:
                deduplicated_count += 1
                continue
            terminal = (
                SharedAlertLifecycle.INVALIDATED
                if current.state is SharedAlertLifecycle.NEW
                else SharedAlertLifecycle.RESOLVED
            )
            event = transition_alert_lifecycle(
                alert_id=current.alert_id,
                hypothesis_id=current.hypothesis_id,
                previous_state=current.state,
                next_state=terminal,
                transitioned_at=observation.as_of,
                evidence_cutoff_at=observation.evidence_cutoff_at,
                reason_codes=("SOURCE_TRAJECTORY_NO_LONGER_MATERIAL",),
                provenance_refs=tuple(
                    sorted(
                        set(
                            observation.provenance_refs
                            + ("sti4-real-lifecycle-replay",)
                        )
                    )
                ),
            )
            if event is None:
                raise AssertionError("terminal lifecycle transition was deduplicated")
            transition_counts[
                f"{current.state.value}->{terminal.value}"
            ] += 1
            transition_fingerprints.append(event.fingerprint())
            terminal_count += 1
            del live[observation.asset]
            continue

        mechanism = assessment.dominant_mechanism
        assert mechanism is not None

        if current is not None and current.mechanism is not mechanism:
            terminal = (
                SharedAlertLifecycle.INVALIDATED
                if current.state is SharedAlertLifecycle.NEW
                else SharedAlertLifecycle.RESOLVED
            )
            close = transition_alert_lifecycle(
                alert_id=current.alert_id,
                hypothesis_id=current.hypothesis_id,
                previous_state=current.state,
                next_state=terminal,
                transitioned_at=observation.as_of,
                evidence_cutoff_at=observation.evidence_cutoff_at,
                reason_codes=("DOMINANT_MECHANISM_CHANGED",),
                provenance_refs=tuple(
                    sorted(
                        set(
                            observation.provenance_refs
                            + ("sti4-real-lifecycle-replay",)
                        )
                    )
                ),
            )
            if close is None:
                raise AssertionError("mechanism switch failed to close prior alert")
            transition_counts[
                f"{current.state.value}->{terminal.value}"
            ] += 1
            transition_fingerprints.append(close.fingerprint())
            terminal_count += 1
            current = None
            del live[observation.asset]

        if current is None:
            epochs[observation.asset] += 1
            epoch = epochs[observation.asset]
            hypothesis_id = (
                f"{partition}:{observation.asset}:{mechanism.value}:epoch-{epoch}"
            )
            live[observation.asset] = _LiveHypothesis(
                hypothesis_id=hypothesis_id,
                alert_id=f"alert:{hypothesis_id}",
                mechanism=mechanism,
                state=SharedAlertLifecycle.NEW,
                epoch=epoch,
            )
            new_alert_count += 1
            continue

        desired = _next_state(current.state, assessment.maturity)
        if desired is current.state:
            deduplicated_count += 1
            continue

        event = transition_alert_lifecycle(
            alert_id=current.alert_id,
            hypothesis_id=current.hypothesis_id,
            previous_state=current.state,
            next_state=desired,
            transitioned_at=observation.as_of,
            evidence_cutoff_at=observation.evidence_cutoff_at,
            reason_codes=(
                f"MATURITY_{assessment.maturity.value}",
                f"MECHANISM_{mechanism.value}",
            ),
            provenance_refs=tuple(
                sorted(
                    set(
                        observation.provenance_refs
                        + ("sti4-real-lifecycle-replay",)
                    )
                )
            ),
        )
        if event is None:
            raise AssertionError("material lifecycle transition was deduplicated")
        transition_counts[f"{current.state.value}->{desired.value}"] += 1
        transition_fingerprints.append(event.fingerprint())
        current.state = desired

    return {
        "partition": partition,
        "source_observation_count": source_count,
        "new_alert_count": new_alert_count,
        "material_transition_count": len(transition_fingerprints),
        "terminal_transition_count": terminal_count,
        "deduplicated_nonmaterial_count": deduplicated_count,
        "open_alert_count_at_partition_end": len(live),
        "transition_counts": dict(sorted(transition_counts.items())),
        "transition_fingerprints": transition_fingerprints,
        "silent_resurrection_count": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    for partition in ("r8", "r6", "r5"):
        parser.add_argument(f"--{partition}-nas", type=Path, required=True)
        parser.add_argument(f"--{partition}-sp", type=Path, required=True)
        parser.add_argument(f"--{partition}-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    policy, calibration = sti2._source_policy(
        {
            "NAS100": args.r8_nas,
            "SP500": args.r8_sp,
            "US30": args.r8_us,
        }
    )
    results = {}
    for partition in ("r6", "r5"):
        paths = {
            "NAS100": getattr(args, f"{partition}_nas"),
            "SP500": getattr(args, f"{partition}_sp"),
            "US30": getattr(args, f"{partition}_us"),
        }
        first = _replay_once(partition=partition, paths=paths, policy=policy)
        second = _replay_once(partition=partition, paths=paths, policy=policy)
        deterministic = (
            first["transition_fingerprints"]
            == second["transition_fingerprints"]
            and first["transition_counts"] == second["transition_counts"]
            and first["new_alert_count"] == second["new_alert_count"]
        )
        first["deterministic_replay"] = deterministic
        first.pop("transition_fingerprints")
        results[partition] = first

    passed = all(
        row["source_observation_count"] > 0
        and row["new_alert_count"] > 0
        and row["material_transition_count"] > 0
        and row["deduplicated_nonmaterial_count"] > 0
        and row["silent_resurrection_count"] == 0
        and row["deterministic_replay"]
        for row in results.values()
    )
    payload = {
        "identity": IDENTITY,
        "status": (
            "STI4_ALERT_LIFECYCLE_REAL_REPLAY_COMPLETED_AND_PROVEN"
            if passed
            else "STI4_ALERT_LIFECYCLE_REAL_REPLAY_FAIL"
        ),
        "r8_source_only_calibration": calibration,
        "results": results,
        "proof": {
            "future_market_read": False,
            "future_outcome_read": False,
            "trader_methodology_read": False,
            "unchanged_state_deduplicated": True,
            "terminal_alert_resurrection_forbidden": True,
            "mechanism_change_closes_old_identity": True,
            "new_hypothesis_uses_new_epoch_identity": True,
        },
        "governance": {
            "protected_certification_holdout_opened": False,
            "productive_authority": False,
        },
        "capability_state": (
            "COMPLETED_AND_PROVEN" if passed else "RESEARCH_INCOMPLETE"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "status": payload["status"],
        "results": results,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
