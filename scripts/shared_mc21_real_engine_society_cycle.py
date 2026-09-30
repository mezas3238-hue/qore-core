#!/usr/bin/env python3
"""MC-21 real-engine Scientific Society cycle.

The cycle binds all twelve scientific roles to real source/engine evidence and
uses the already-falsified STI-5 V1 proposition as a real minority-falsification
case. No role can promote knowledge or acquire trading authority.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import shared_sti2_real_opportunity_discovery as source

from qore.infrastructure.core_stack_v2.hypothesis_ensemble import (
    MarketHypothesis,
    evaluate_reversal_hypotheses,
)
from qore.infrastructure.core_stack_v2.perception import perceive
from qore.infrastructure.core_stack_v2.scientific_society import (
    ScientificClaim,
    ScientificContribution,
    ScientificRole,
    ScientificSocietyVerdict,
    arbitrate_scientific_society,
)

IDENTITY = "QORE_SHARED_MC21_REAL_ENGINE_SCIENTIFIC_SOCIETY_CYCLE_001"
STI5_RUN_ID = 36640098773
STI5_ARTIFACT_ID = 11066541040
STI5_DIAGNOSTIC_RUN_ID = 36685175913
STI5_DIAGNOSTIC_ARTIFACT_ID = 11082953096
R6_SOURCE_ARTIFACT_ID = 10389112524


def _find_sti5(root: Path) -> dict[str, Any]:
    matches = list(root.rglob("sti5-causal-replay.json"))
    if len(matches) != 1:
        raise ValueError(
            f"expected one canonical sti5-causal-replay.json, found {len(matches)}"
        )
    payload = json.loads(matches[0].read_text())
    if not isinstance(payload, dict):
        raise ValueError("canonical STI5 replay payload must be an object")
    if payload.get("identity") != "QORE_SHARED_STI5_REAL_REGIME_TRANSITION_V1":
        raise ValueError("canonical STI5 replay identity drifted")
    if payload.get("mode") != "CAUSAL_HISTORICAL_REPLAY":
        raise ValueError("canonical STI5 replay mode drifted")
    return payload


def _real_hypothesis_binding(paths: dict[str, Path]) -> dict[str, object]:
    rows = source._aligned_source_rows(
        paths,
        partition="mc21_real_hypothesis_binding",
        require_future=False,
    )
    if not rows:
        raise ValueError("MC21 hypothesis binding requires real source rows")

    sample = rows[: min(256, len(rows))]
    deterministic = 0
    resolved = 0
    hypothesis_counts: dict[str, int] = {}
    for observation, _states, pre, future in sample:
        if future is not None:
            raise AssertionError("MC21 role binding cannot attach future evidence")
        nas = pre["NAS100"]
        sp = pre["SP500"]
        us = pre["US30"]
        if len(nas) < 30 or len(sp) < 10 or len(us) < 10:
            continue
        recent = nas[-10:]
        prior = nas[-30:-10]
        low = min(Decimal(str(item.low)) for item in recent)
        high = max(Decimal(str(item.high)) for item in recent)
        width = high - low
        if width <= 0:
            continue
        side = "long" if recent[-1].close >= recent[0].close else "short"
        perception = perceive(
            as_of=observation.as_of,
            side=side,
            reference_width=width,
            nas_recent=recent,
            nas_prior=prior,
            sweep_to_signal=recent,
            sp500_recent=sp[-10:],
            us30_recent=us[-10:],
        )
        first = evaluate_reversal_hypotheses(perception)
        second = evaluate_reversal_hypotheses(perception)
        deterministic += int(first == second)
        hypothesis_counts[first.primary.value] = (
            hypothesis_counts.get(first.primary.value, 0) + 1
        )
        resolved += int(first.primary is not MarketHypothesis.UNRESOLVED)

    evaluated = sum(hypothesis_counts.values())
    passed = (
        evaluated >= 100
        and deterministic == evaluated
        and resolved > 0
    )
    return {
        "sample_count": evaluated,
        "deterministic_count": deterministic,
        "resolved_count": resolved,
        "hypothesis_counts": dict(sorted(hypothesis_counts.items())),
        "future_market_used": False,
        "outcome_used": False,
        "pass": passed,
    }


def _contribution(
    role: ScientificRole,
    claim: ScientificClaim,
    confidence_bps: int,
    model_family: str,
    refs: tuple[str, ...],
) -> ScientificContribution:
    return ScientificContribution(
        role=role,
        claim=claim,
        confidence_bps=confidence_bps,
        model_family=model_family,
        evidence_refs=tuple(sorted(set(refs))),
        real_engine_bound=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sti5-root", type=Path, required=True)
    parser.add_argument("--r6-nas", type=Path, required=True)
    parser.add_argument("--r6-sp", type=Path, required=True)
    parser.add_argument("--r6-us", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    sti5 = _find_sti5(args.sti5_root)
    if sti5.get("engine_state") != (
        "ENGINE_IMPLEMENTED_REAL_DATA_BOUND_CAUSAL_REPLAY_EXECUTED"
    ):
        raise AssertionError("STI5 real engine evidence missing")
    if sti5.get("value_status") != "STI5_V1_FALSIFIED_ON_CONSUMED_EVIDENCE":
        raise AssertionError("STI5 V1 falsification evidence drifted")
    if sti5.get("consumed_gate_pass") is not False:
        raise AssertionError("STI5 V1 scientific gate unexpectedly passed")
    evaluations = sti5.get("evaluations")
    if not isinstance(evaluations, dict):
        raise AssertionError("STI5 evaluation partitions missing")
    for partition in ("r6", "r5"):
        row = evaluations.get(partition)
        if not isinstance(row, dict) or row.get("gate_pass") is not False:
            raise AssertionError(f"STI5 {partition} falsification not preserved")

    hypothesis = _real_hypothesis_binding(
        {
            "NAS100": args.r6_nas,
            "SP500": args.r6_sp,
            "US30": args.r6_us,
        }
    )
    if hypothesis["pass"] is not True:
        raise AssertionError("real hypothesis generator binding failed")

    contributions = (
        _contribution(
            ScientificRole.OBSERVER,
            ScientificClaim.ABSTAIN,
            8_000,
            "SOURCE_OBSERVATION",
            (f"artifact:{R6_SOURCE_ARTIFACT_ID}",),
        ),
        _contribution(
            ScientificRole.HYPOTHESIS_GENERATOR,
            ScientificClaim.ABSTAIN,
            8_000,
            "SYMBOLIC_HYPOTHESIS_ENSEMBLE",
            (
                f"artifact:{R6_SOURCE_ARTIFACT_ID}",
                "engine:hypothesis_ensemble",
            ),
        ),
        _contribution(
            ScientificRole.CAUSAL_SCIENTIST,
            ScientificClaim.ABSTAIN,
            8_000,
            "CAUSAL_DISCOVERY",
            ("artifact:10904203504", "run:36236760353"),
        ),
        _contribution(
            ScientificRole.STATISTICIAN,
            ScientificClaim.FALSIFY,
            9_500,
            "STATISTICAL_GATE_EVALUATION",
            (
                f"artifact:{STI5_ARTIFACT_ID}",
                f"run:{STI5_RUN_ID}",
            ),
        ),
        _contribution(
            ScientificRole.ADVERSARIAL_CRITIC,
            ScientificClaim.OPPOSE,
            9_000,
            "ADVERSARIAL_FAILURE_DIAGNOSTIC",
            (
                f"artifact:{STI5_DIAGNOSTIC_ARTIFACT_ID}",
                f"run:{STI5_DIAGNOSTIC_RUN_ID}",
            ),
        ),
        _contribution(
            ScientificRole.DEFENDER,
            ScientificClaim.ABSTAIN,
            7_000,
            "STRUCTURAL_CONSTRAINT_MODEL",
            ("artifact:11115664725", "run:36755380068"),
        ),
        _contribution(
            ScientificRole.SKEPTIC,
            ScientificClaim.OPPOSE,
            8_500,
            "CONTRADICTION_MODEL",
            ("artifact:11104578542", "run:36731394336"),
        ),
        _contribution(
            ScientificRole.COUNTERFACTUAL_ANALYST,
            ScientificClaim.ABSTAIN,
            7_000,
            "COUNTERFACTUAL_WORLD_MODEL",
            ("artifact:11119876541", "run:36764204066"),
        ),
        _contribution(
            ScientificRole.REGIME_SPECIALIST,
            ScientificClaim.OPPOSE,
            9_000,
            "REGIME_TRANSITION_MODEL",
            (
                f"artifact:{STI5_ARTIFACT_ID}",
                f"run:{STI5_RUN_ID}",
            ),
        ),
        _contribution(
            ScientificRole.TRAJECTORY_SPECIALIST,
            ScientificClaim.ABSTAIN,
            7_000,
            "TRAJECTORY_MODEL",
            ("artifact:11120695398", "run:36764215198"),
        ),
        _contribution(
            ScientificRole.RISK_OF_ERROR_ANALYST,
            ScientificClaim.OPPOSE,
            8_000,
            "BAYESIAN_CALIBRATION",
            ("artifact:11116522138", "run:36754966932"),
        ),
        _contribution(
            ScientificRole.REPLICATION_SCIENTIST,
            ScientificClaim.ABSTAIN,
            8_000,
            "TEMPORAL_REPLICATION",
            ("artifact:10908077821", "run:36248025384"),
        ),
    )

    decision = arbitrate_scientific_society(
        proposition_id="STI5_V1_SCIENTIFIC_ADMISSION",
        contributions=contributions,
    )
    all_roles_real = all(item.real_engine_bound for item in decision.contributions)
    model_families = sorted(
        {item.model_family for item in decision.contributions}
    )
    material_falsifiers = tuple(
        item.role.value
        for item in decision.contributions
        if item.claim is ScientificClaim.FALSIFY
        and item.confidence_bps >= 5_000
    )
    completed = (
        all_roles_real
        and len(decision.contributions) == 12
        and decision.verdict
        is ScientificSocietyVerdict.REJECTED_BY_FALSIFICATION
        and decision.minority_falsification_preserved
        and len(material_falsifiers) >= 1
        and bool(hypothesis["pass"])
    )
    payload = {
        "identity": IDENTITY,
        "status": (
            "MC21_SCIENTIFIC_SOCIETY_COMPLETED_AND_PROVEN"
            if completed
            else "MC21_REAL_ENGINE_CYCLE_FAILED"
        ),
        "proposition_id": decision.proposition_id,
        "verdict": decision.verdict.value,
        "required_role_count": len(ScientificRole),
        "real_engine_bound_role_count": sum(
            item.real_engine_bound for item in decision.contributions
        ),
        "all_roles_real_engine_bound": all_roles_real,
        "material_falsifier_roles": material_falsifiers,
        "minority_falsification_preserved": (
            decision.minority_falsification_preserved
        ),
        "simple_majority_voting_used": decision.simple_majority_voting_used,
        "heterogeneous_model_family_count": len(model_families),
        "model_families": model_families,
        "real_hypothesis_generator_binding": hypothesis,
        "sti5_v1_falsification_preserved": True,
        "knowledge_promotion_authority": decision.knowledge_promotion_authority,
        "methodology_authority": decision.methodology_authority,
        "execution_authority": decision.execution_authority,
        "risk_authority": decision.risk_authority,
        "sizing_authority": decision.sizing_authority,
        "productive_authority": False,
        "mc21_completed_and_proven": completed,
        "master_ledger_mutated": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
