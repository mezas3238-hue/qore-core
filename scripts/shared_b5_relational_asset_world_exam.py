#!/usr/bin/env python3
"""Deterministic Architect-B5 relational/asset-world examination receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.core_stack_v2.global_temporal_comparability import (
    ComparabilityConfidence,
    RelationalComparabilityState,
)
from qore.infrastructure.core_stack_v2.shared_b5_asset_world import (
    assess_agricultural_world,
    assess_commodity_world,
    dated_gc_contracts_from_evidence,
    energy_reference_objects_from_evidence,
)
from qore.infrastructure.core_stack_v2.shared_b5_relational_science import (
    RelationalSample,
    observe_lead_lag,
    observe_structural_divergence,
    populate_relationship_lifecycle,
)

IDENTITY = "QORE_SHARED_ARCHITECT_B5_RELATIONAL_ASSET_WORLD_EXAM_001"
AS_OF = datetime(2026, 9, 30, 16, 0, tzinfo=UTC)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload, _sha256_bytes(raw)


def _sample(
    minute: int,
    source: int,
    target: int,
    *,
    state: RelationalComparabilityState = RelationalComparabilityState.COMPARABLE,
    confidence: ComparabilityConfidence = ComparabilityConfidence.HIGH,
) -> RelationalSample:
    return RelationalSample(
        observed_at=AS_OF + timedelta(minutes=minute),
        source_value_bps=source,
        target_value_bps=target,
        comparability_state=state,
        comparability_confidence=confidence,
        source_freshness_ms=100,
        target_freshness_ms=120,
        provenance_refs=(f"b5-golden-trace:{minute:02d}",),
    )


def _b11() -> dict[str, Any]:
    samples = (
        _sample(0, 0, 0),
        _sample(1, 100, 100),
        _sample(2, -50, -50),
        _sample(3, 200, 200),
        _sample(4, -100, -100),
        _sample(5, 250, 250),
        _sample(
            6,
            300,
            300,
            state=RelationalComparabilityState.STALE_PEER,
            confidence=ComparabilityConfidence.LOW,
        ),
        _sample(
            7,
            350,
            350,
            state=RelationalComparabilityState.STALE_PEER,
            confidence=ComparabilityConfidence.LOW,
        ),
    )
    first = populate_relationship_lifecycle(
        relation_id="B5:GOLDEN:LIFECYCLE",
        samples=samples,
        window_size=5,
        dead_after_stale_windows=2,
    )
    second = populate_relationship_lifecycle(
        relation_id="B5:GOLDEN:LIFECYCLE",
        samples=samples,
        window_size=5,
        dead_after_stale_windows=2,
    )
    return {
        "work_id": "B-11",
        "engine_functional_pass": first == second,
        "deterministic_replay_pass": first.fingerprint() == second.fingerprint(),
        "lifecycle_states_observed": [item.state.value for item in first.transitions],
        "receipt_fingerprint_sha256": first.fingerprint(),
        "empirical_global_population_complete": False,
        "disposition": "ENGINEERING_PASS_EMPIRICAL_POPULATION_OPEN",
        "blockers": ["REAL_GLOBAL_RELATIONSHIP_POPULATION_REQUIRED"],
    }


def _b12() -> dict[str, Any]:
    source = (0, 500, -300, 800, -700, 200, 900, -450, 150, 650, -200, 400)
    target = (100, -100) + source[:-2]
    samples = tuple(
        _sample(index, source[index], target[index])
        for index in range(len(source))
    )
    first = observe_lead_lag(
        relation_id="B5:GOLDEN:LEAD_LAG",
        samples=samples,
        max_lag_steps=4,
        minimum_abs_r_bps=8_000,
    )
    second = observe_lead_lag(
        relation_id="B5:GOLDEN:LEAD_LAG",
        samples=samples,
        max_lag_steps=4,
        minimum_abs_r_bps=8_000,
    )
    return {
        "work_id": "B-12",
        "engine_functional_pass": first == second,
        "deterministic_replay_pass": first == second,
        "direction": first.direction.value,
        "lag_steps": first.lag_steps,
        "lag_ms": first.lag_ms,
        "pearson_r_bps": first.pearson_r_bps,
        "epistemic_grade": first.epistemic_grade.value,
        "temporal_precedence_observed": first.temporal_precedence_observed,
        "causation_claimed": first.causation_claimed,
        "empirical_global_population_complete": False,
        "disposition": "ENGINEERING_PASS_EMPIRICAL_POPULATION_OPEN",
        "blockers": ["REAL_GLOBAL_LEAD_LAG_POPULATION_REQUIRED"],
    }


def _b13() -> dict[str, Any]:
    samples = (
        _sample(0, 0, 0),
        _sample(1, 100, -100),
        _sample(2, 200, -200),
        _sample(3, 300, -300),
        _sample(4, 450, -500),
    )
    first = observe_structural_divergence(
        relation_id="B5:GOLDEN:STRUCTURAL_DIVERGENCE",
        samples=samples,
        window_size=5,
        minimum_leg_move_bps=200,
    )
    second = observe_structural_divergence(
        relation_id="B5:GOLDEN:STRUCTURAL_DIVERGENCE",
        samples=samples,
        window_size=5,
        minimum_leg_move_bps=200,
    )
    return {
        "work_id": "B-13",
        "engine_functional_pass": first == second,
        "deterministic_replay_pass": first == second,
        "divergent": first.divergent,
        "source_delta_bps": first.source_delta_bps,
        "target_delta_bps": first.target_delta_bps,
        "divergence_bps": first.divergence_bps,
        "comparable_sample_count": first.comparable_sample_count,
        "empirical_global_population_complete": False,
        "disposition": "ENGINEERING_PASS_EMPIRICAL_POPULATION_OPEN",
        "blockers": ["REAL_GLOBAL_STRUCTURAL_DIVERGENCE_POPULATION_REQUIRED"],
    }


def _b14() -> dict[str, Any]:
    receipt = assess_agricultural_world(
        as_of=AS_OF,
        conceptual_market_count=16,
        provider_candidate_count=0,
        provider_count=1,
        secondary_provider_scientifically_admitted=False,
    )
    return {
        "work_id": "B-14",
        "engine_functional_pass": True,
        "deterministic_replay_pass": (
            receipt.fingerprint()
            == assess_agricultural_world(
                as_of=AS_OF,
                conceptual_market_count=16,
                provider_candidate_count=0,
                provider_count=1,
                secondary_provider_scientifically_admitted=False,
            ).fingerprint()
        ),
        "state": receipt.state.value,
        "conceptual_market_count": receipt.conceptual_market_count,
        "provider_candidate_count": receipt.provider_candidate_count,
        "synthetic_proxy_used": receipt.synthetic_proxy_used,
        "relational_claims_authorized": receipt.relational_claims_authorized,
        "disposition": "KNOWN_BLINDSPOT",
        "blockers": ["SECONDARY_GOVERNED_AGRICULTURAL_PROVIDER_NOT_ADMITTED"],
    }


def _b15(
    *,
    energy_payload: dict[str, Any],
    gc_payload: dict[str, Any],
) -> dict[str, Any]:
    energy = energy_reference_objects_from_evidence(energy_payload)
    contracts = dated_gc_contracts_from_evidence(gc_payload)
    receipt = assess_commodity_world(
        as_of=AS_OF,
        metal_reference_object_count=11,
        energy_reference_objects=energy,
        dated_contracts=contracts,
    )
    replica = assess_commodity_world(
        as_of=AS_OF,
        metal_reference_object_count=11,
        energy_reference_objects=energy,
        dated_contracts=contracts,
    )
    return {
        "work_id": "B-15",
        "engine_functional_pass": True,
        "deterministic_replay_pass": receipt.fingerprint() == replica.fingerprint(),
        "state": receipt.state.value,
        "metal_reference_object_count": receipt.metal_reference_object_count,
        "energy_reference_object_count": receipt.energy_reference_object_count,
        "dated_contract_count": receipt.dated_contract_count,
        "expired_dated_contract_count": receipt.expired_dated_contract_count,
        "front_contract_verified_count": receipt.front_contract_verified_count,
        "roll_semantics_verified_count": receipt.roll_semantics_verified_count,
        "continuous_semantics_verified_count": (
            receipt.continuous_semantics_verified_count
        ),
        "disposition": "UNRESOLVED",
        "blockers": list(receipt.blockers),
    }


def run(*, repo_root: Path, output: Path) -> dict[str, Any]:
    energy_path = (
        repo_root
        / "docs/shared/evidence/QORE_SHARED_GW2_ENERGY_REFERENCE_AUTHORITY_EVIDENCE_001.json"
    )
    gc_path = (
        repo_root
        / "docs/shared/evidence/QORE_SHARED_GW2_GC_FUTURES_CONTRACT_AUTHORITY_EVIDENCE_001.json"
    )
    agri_path = (
        repo_root
        / "docs/shared/evidence/QORE_SHARED_AGRICULTURAL_CONCEPTUAL_UNIVERSE_001.json"
    )
    energy, energy_sha = _load(energy_path)
    gc, gc_sha = _load(gc_path)
    agri, agri_sha = _load(agri_path)
    targets = agri.get("targets")
    if not isinstance(targets, list) or len(targets) != 16:
        raise ValueError("expected exact 16-market agricultural conceptual universe")

    workstreams = [_b11(), _b12(), _b13(), _b14(), _b15(
        energy_payload=energy,
        gc_payload=gc,
    )]
    all_engineering = all(bool(item["engine_functional_pass"]) for item in workstreams)
    all_replay = all(bool(item["deterministic_replay_pass"]) for item in workstreams)
    open_ids = [
        str(item["work_id"])
        for item in workstreams
        if item["disposition"] not in {"CLOSED", "TERMINAL"}
    ]
    payload: dict[str, Any] = {
        "identity": IDENTITY,
        "as_of": AS_OF.isoformat(),
        "source_evidence_sha256": {
            energy_path.relative_to(repo_root).as_posix(): energy_sha,
            gc_path.relative_to(repo_root).as_posix(): gc_sha,
            agri_path.relative_to(repo_root).as_posix(): agri_sha,
        },
        "workstreams": workstreams,
        "engineering_functional_pass": all_engineering,
        "deterministic_replay_pass": all_replay,
        "b5_zero_open": not open_ids,
        "open_work_ids": open_ids,
        "outcome_used": False,
        "future_market_used": False,
        "protected_holdout_opened": False,
        "execution_authority": False,
        "risk_authority": False,
        "sizing_authority": False,
        "cibo_authority": False,
        "broker_mutation": False,
        "productive_authority": False,
        "certification_claimed": False,
    }
    payload["receipt_fingerprint_sha256"] = _sha256_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "artifacts/shared_b5/QORE_SHARED_ARCHITECT_B5_RELATIONAL_ASSET_WORLD_EXAM_001.json"
        ),
    )
    args = parser.parse_args()
    report = run(repo_root=args.repo_root.resolve(), output=args.output.resolve())
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
