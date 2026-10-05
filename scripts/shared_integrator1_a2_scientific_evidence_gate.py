#!/usr/bin/env python3
"""Fail-closed scientific evidence gate for Shared Integrator 1 A2 lane.

This gate does not create scientific evidence and does not relax any producer
gate. It only prevents an A1+A2 integration package from being represented as
scientifically closed when the required sealed MC23/MC24/MC25/WP11 evidence is
absent from the exact target SHA.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

IDENTITY = "QORE_SHARED_INTEGRATOR_1_A2_SCIENTIFIC_EVIDENCE_GATE_001"

MC23_CANDIDATE_001_ID = "QORE_SHARED_MC23_VALIDATED_NOVEL_REGIME_ADAPTATION_001"
MC23_CANDIDATE_002_ID = "QORE_SHARED_MC23_CANDIDATE_002_ROUTED_SECOND_ORDER_001"
MC23_CANDIDATE_001_FALSIFIED_STATUS = (
    "MC23_VALIDATED_REAL_NOVEL_REGIME_ADAPTATION_"
    "FALSIFIED_AND_CLOSED_FOR_THIS_MECHANISM"
)
MC23_CANDIDATE_002_FALSIFIED_STATUS = (
    "MC23_CANDIDATE_002_FALSIFIED_ON_REPLICATION_D"
)
MC23_CANDIDATE_003_PREREGISTRATION_SCHEMA = (
    "QORE_SHARED_MC23_VALIDATED_NOVEL_REGIME_ADAPTATION_PREREGISTRATION_003"
)
MC24_ID = "QORE_SHARED_MC24_VALIDATED_ADAPTATION_HALF_LIFE_001"
MC25_LINEAGE_ID = "QORE_SHARED_MC25_WP04_V3B_LINEAGE_INTEGRITY_STRESS_001"
MC25_PERFORMANCE_ID = "QORE_SHARED_MC25_WP04_V3B_PERFORMANCE_STRESS_001"
WP11_ID = "QORE_SHARED_WP11_EXACT_BLOCKER_AUDIT_002"


def _load_rows(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    if not root.is_dir():
        raise ValueError(f"evidence directory missing: {root}")
    rows: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(root.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"{path} must contain a JSON object")
        rows.append((path, payload))
    return rows


def _identity_rows(
    rows: list[tuple[Path, dict[str, Any]]],
    identity: str,
) -> list[tuple[Path, dict[str, Any]]]:
    return [(path, row) for path, row in rows if row.get("identity") == identity]


def _has(
    rows: list[tuple[Path, dict[str, Any]]],
    identity: str,
    predicate,
) -> bool:
    return any(predicate(row) for _path, row in _identity_rows(rows, identity))


def _safe_governance(row: dict[str, Any]) -> bool:
    forbidden_true = (
        "productive_authority",
        "protected_certification_holdout_opened",
        "master_ledger_mutated",
        "broker_mutation",
        "live",
        "real_capital_used",
    )
    return not any(row.get(key) is True for key in forbidden_true)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=Path("docs/shared/evidence"),
    )
    parser.add_argument(
        "--runtime-evidence-dir",
        type=Path,
        action="append",
        default=[],
        help="Additional same-run evidence directories (for example result/).",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows = _load_rows(args.evidence_dir)
    for runtime_dir in args.runtime_evidence_dir:
        if runtime_dir.exists():
            rows.extend(_load_rows(runtime_dir))
    blockers: list[str] = []

    candidate_001_terminal_falsified = any(
        row.get("schema")
        == "QORE_SHARED_A2_MC23_CANDIDATE_001_FALSIFICATION_001"
        and row.get("status") == MC23_CANDIDATE_001_FALSIFIED_STATUS
        and row.get("governance", {}).get("candidate_001_terminal") is True
        and row.get("governance", {}).get(
            "candidate_001_may_not_be_retried_for_pass"
        )
        is True
        and _safe_governance(row)
        for _path, row in rows
    )
    candidate_002_terminal_falsified = any(
        row.get("schema")
        == "QORE_SHARED_A2_MC23_CANDIDATE_002_FALSIFICATION_001"
        and row.get("status") == MC23_CANDIDATE_002_FALSIFIED_STATUS
        and row.get("governance", {}).get("candidate_002_terminal") is True
        and row.get("governance", {}).get("retry_for_pass_forbidden") is True
        and row.get("replication_e", {}).get("evaluated") is False
        and _safe_governance(row)
        for _path, row in rows
    )

    candidate_003_preregistered = any(
        row.get("schema") == MC23_CANDIDATE_003_PREREGISTRATION_SCHEMA
        and row.get("validation", {}).get("partition")
        == "REPLACEMENT_ONE_SHOT_HOLDOUT_E"
        and row.get("validation", {}).get("one_shot") is True
        and row.get("development", {}).get("no_E_information_allowed") is True
        and row.get("governance", {}).get("shared_lab_required") is True
        and row.get("governance", {}).get(
            "holdout_E_mc23_targets_not_read_before_freeze"
        )
        is True
        and row.get("governance", {}).get("outcome_aware_tuning_on_E") is False
        and row.get("governance", {}).get("protected_final_holdout_opened") is False
        and _safe_governance(row)
        for _path, row in rows
    )

    candidate_002_row = next(
        (
            row
            for _path, row in rows
            if row.get("identity") == MC23_CANDIDATE_002_ID
            and row.get("status")
            == "MC23_CANDIDATE_002_VALIDATED_AND_INDEPENDENTLY_REPLICATED_PASS"
            and row.get("real_novel_regime_validated_adaptation") is True
            and row.get("mc23_completed_and_proven") is True
            and row.get("candidate_001_reused") is False
            and row.get("r5_used_as_candidate_002_validation") is False
            and row.get("validation_d_refit") is False
            and row.get("replication_e_refit") is False
            and row.get("gate_retuning") is False
            and row.get("outcome_aware_tuning") is False
            and _safe_governance(row)
        ),
        None,
    )
    candidate_002_pass = candidate_002_row is not None
    candidate_002_fingerprint = (
        None
        if candidate_002_row is None
        else candidate_002_row.get("candidate_fingerprint")
    )
    legacy_mc23_pass = any(
        row.get("identity") == MC23_CANDIDATE_001_ID
        and row.get("real_novel_regime_validated_adaptation") is True
        and row.get("mc23_completed_and_proven") is True
        and _safe_governance(row)
        for _path, row in rows
    )
    if candidate_002_terminal_falsified:
        mc23_pass = False
        blockers.append(
            "MC23_CANDIDATE_003_IMPLEMENTATION_AND_ONE_SHOT_E_VALIDATION"
            if candidate_003_preregistered
            else "MC23_NEW_PREREGISTERED_MECHANISM_REQUIRED"
        )
    else:
        mc23_pass = (
            candidate_002_pass
            if candidate_001_terminal_falsified
            else legacy_mc23_pass
        )
        if not mc23_pass:
            blockers.append(
                "MC23_CANDIDATE_002_VALIDATED_AND_INDEPENDENTLY_REPLICATED"
                if candidate_001_terminal_falsified
                else "MC23_VALIDATED_REAL_NOVEL_REGIME_ADAPTATION"
            )

    mc24_pass = (not candidate_002_terminal_falsified) and _has(
        rows,
        MC24_ID,
        lambda row: (
            row.get("mc23_real_regime_adaptation_bound") is True
            and row.get("empirical_half_life_validated") is True
            and row.get("retained_knowledge_non_degradation_pass") is True
            and row.get("mc24_completed_and_proven") is True
            and (
                not candidate_001_terminal_falsified
                or (
                    candidate_002_fingerprint is not None
                    and row.get("mc23_candidate_identity")
                    == MC23_CANDIDATE_002_ID
                    and row.get("mc23_candidate_fingerprint")
                    == candidate_002_fingerprint
                )
            )
            and _safe_governance(row)
        ),
    )
    if not mc24_pass:
        blockers.append(
            "MC24_BLOCKED_UNTIL_NEW_MC23_MECHANISM"
            if candidate_002_terminal_falsified
            else (
                "MC24_CANDIDATE_002_BOUND_EMPIRICAL_KNOWLEDGE_HALF_LIFE"
                if candidate_001_terminal_falsified
                else "MC24_EMPIRICAL_KNOWLEDGE_HALF_LIFE"
            )
        )

    lineage_pass = mc24_pass and _has(
        rows,
        MC25_LINEAGE_ID,
        lambda row: (
            row.get("lineage_integrity_stress_pass") is True
            and row.get("promotion_allowed") is False
            and _safe_governance(row)
        ),
    )
    if not lineage_pass:
        blockers.append("MC25_LINEAGE_INTEGRITY_STRESS")

    performance_pass = lineage_pass and _has(
        rows,
        MC25_PERFORMANCE_ID,
        lambda row: (
            row.get("performance_stress_bound") is True
            and row.get("performance_stress_pass") is True
            and row.get("threshold_retuning") is False
            and row.get("target_aware_stress_selection") is False
            and _safe_governance(row)
        ),
    )
    if not performance_pass:
        blockers.append("MC25_SAME_LINEAGE_PERFORMANCE_STRESS")

    formal_stress_pass = performance_pass and any(
        row.get("formal_stress_stage_completed") is True
        and _safe_governance(row)
        for _path, row in rows
    )
    shadow_pass = formal_stress_pass and any(
        row.get("shadow_stage_bound") is True
        and _safe_governance(row)
        for _path, row in rows
    )
    certification_pass = shadow_pass and any(
        row.get("certification_stage_bound") is True
        and _safe_governance(row)
        for _path, row in rows
    )
    promotion_pass = certification_pass and any(
        row.get("promotion_allowed") is True
        and row.get("mc25_completed_and_proven") is True
        and _safe_governance(row)
        for _path, row in rows
    )
    lifecycle_pass = all(
        (
            formal_stress_pass,
            shadow_pass,
            certification_pass,
            promotion_pass,
        )
    )
    if not formal_stress_pass:
        blockers.append("MC25_FORMAL_STRESS_STAGE")
    if not shadow_pass:
        blockers.append("MC25_SAME_LINEAGE_SHADOW")
    if not certification_pass:
        blockers.append("MC25_CERTIFICATION")
    if not promotion_pass:
        blockers.append("MC25_GOVERNED_PROMOTION")

    wp11_pass = lifecycle_pass and _has(
        rows,
        WP11_ID,
        lambda row: (
            row.get("status")
            == "WP11_GOVERNED_SELF_IMPROVEMENT_COMPLETED_AND_PROVEN"
            and row.get("zero_open_work") is True
            and row.get("wp11_completed_and_proven") is True
            and int(row.get("blocker_count", -1)) == 0
            and _safe_governance(row)
        ),
    )
    if not wp11_pass:
        blockers.append("WP11_EXACT_TERMINAL_RECONCILIATION")

    blockers = sorted(set(blockers))
    passed = not blockers
    payload = {
        "identity": IDENTITY,
        "status": (
            "I1_A2_SCIENTIFIC_EVIDENCE_GATE_PASS"
            if passed
            else "I1_A2_SCIENTIFIC_EVIDENCE_GATE_BLOCKED"
        ),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "mc23_candidate_001_terminal_falsified": candidate_001_terminal_falsified,
        "mc23_candidate_001_retry_for_pass_allowed": (False if candidate_001_terminal_falsified else None),
        "mc23_candidate_002_terminal_falsified": candidate_002_terminal_falsified,
        "mc23_candidate_002_retry_for_pass_allowed": (False if candidate_002_terminal_falsified else None),
        "mc23_candidate_003_preregistered": candidate_003_preregistered,
        "mc23_candidate_002_scientific_pass": candidate_002_pass and not candidate_002_terminal_falsified,
        "mc23_candidate_002_fingerprint": candidate_002_fingerprint,
        "mc24_bound_to_active_mc23_candidate": mc24_pass,
        "mc23_scientific_pass": mc23_pass,
        "mc23_active_candidate": (
            (
                "MC23_CANDIDATE_003_PREREGISTERED"
                if candidate_003_preregistered
                else "NONE_NEW_PREREGISTERED_MECHANISM_REQUIRED"
            )
            if candidate_002_terminal_falsified
            else (
                "MC23_CANDIDATE_002"
                if candidate_001_terminal_falsified
                else "MC23_CANDIDATE_001"
            )
        ),
        "mc23_candidate_001_terminal_falsification_preserved": True,
        "mc24_scientific_pass": mc24_pass,
        "mc25_lineage_pass": lineage_pass,
        "mc25_performance_pass": performance_pass,
        "mc25_formal_stress_pass": formal_stress_pass,
        "mc25_shadow_pass": shadow_pass,
        "mc25_certification_pass": certification_pass,
        "mc25_promotion_pass": promotion_pass,
        "mc25_full_lifecycle_pass": lifecycle_pass,
        "wp11_terminal_pass": wp11_pass,
        "producer_thresholds_modified": False,
        "scientific_evidence_created_by_gate": False,
        "productive_authority": False,
        "master_ledger_mutated": False,
        "protected_certification_holdout_opened": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    raise SystemExit(0 if passed else 2)


if __name__ == "__main__":
    main()
