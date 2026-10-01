from __future__ import annotations

import hashlib
import json

import pytest

from qore.infrastructure.cibo_arch_a_phase22_pre_outcome import (
    CANONICAL_STORE_PATHS,
    CANONICAL_TRADER_IDS,
    evaluate_phase22_pre_outcome_provenance,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def _manifest() -> dict:
    payload = {
        "schema": "qore.cibo.phase22.execution-manifest.v2",
        "candidate_id": "CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2",
        "source_receipt_sha256": _sha("source"),
        "pre_holdout_source_receipt_sha256": _sha("pre"),
        "phase21_policy_freeze_sha256": _sha("phase21"),
        "calibration_freeze_sha256": _sha("calibration"),
        "provider_core_freeze_sha256": _sha("provider"),
        "candidate_code_sha": "a" * 40,
        "candidate_parameter_sha256": _sha("parameters"),
        "qualification_plan_sha256": _sha("plan"),
        "parity_manifest_sha256": _sha("parity"),
        "trader_bindings": [
            {
                "trader_id": trader_id,
                "methodology_git_sha": "b" * 40,
                "replay_engine_sha256": _sha("engine-" + trader_id),
                "parameter_sha256": _sha("param-" + trader_id),
                "parity_artifact_ref": "artifact:" + trader_id,
                "parity_artifact_digest": _sha("parity-" + trader_id),
            }
            for trader_id in CANONICAL_TRADER_IDS
        ],
        "fresh_outcomes_executed": False,
        "productive_authority": False,
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    payload["manifest_sha256"] = "sha256:" + hashlib.sha256(raw).hexdigest()
    return payload


def _stores() -> dict:
    names = (
        "HOLDOUT_FORWARD_EVIDENCE",
        "HOLDOUT_POLICY",
        "EXECUTED_RISK",
        "CMA_SETTLEMENT",
        "T20_RELEASE",
    )
    return {
        "schema": "qore.cibo.phase22.store-contract.v1",
        "root": "phase22-v2-stores",
        "stores": [
            {
                "name": name,
                "relative_path": path,
                "schema": name,
                "role": name,
                "empty_sha256": _sha(name),
            }
            for name, path in zip(names, CANONICAL_STORE_PATHS)
        ],
        "store_reuse_allowed": False,
        "fresh_outcomes_executed": False,
        "productive_authority": False,
    }


def _guard(manifest: dict, *, ready: bool) -> dict:
    blockers = [] if ready else [
        "REALIZED_EXECUTION_ECONOMICS_REQUIRED_BEFORE_PHASE22_HOLDOUT",
        "SYNTHETIC_EXECUTION_EVIDENCE_FORBIDDEN",
    ]
    return {
        "status": "READY" if ready else "BLOCKED",
        "execution_manifest_sha256": manifest["manifest_sha256"],
        "store_paths": list(CANONICAL_STORE_PATHS),
        "blockers": blockers,
        "fresh_outcomes_already_emitted": False,
        "authorized_to_emit_first_fresh_outcome": ready,
        "productive_authority": False,
    }


def test_a_records_blocked_preflight_without_calling_it_ready() -> None:
    manifest = _manifest()
    receipt = evaluate_phase22_pre_outcome_provenance(
        execution_manifest=manifest,
        store_contract=_stores(),
        one_shot_guard=_guard(manifest, ready=False),
    )
    assert receipt.one_shot_status == "BLOCKED"
    assert receipt.ready_for_fresh_execution is False
    assert receipt.fresh_outcomes_already_emitted is False


def test_a_accepts_ready_preflight_only_with_zero_blockers() -> None:
    manifest = _manifest()
    receipt = evaluate_phase22_pre_outcome_provenance(
        execution_manifest=manifest,
        store_contract=_stores(),
        one_shot_guard=_guard(manifest, ready=True),
    )
    assert receipt.ready_for_fresh_execution is True
    assert receipt.guard_blockers == ()


def test_a_rejects_consumed_preflight() -> None:
    manifest = _manifest()
    guard = _guard(manifest, ready=False)
    guard["status"] = "CONSUMED"
    guard["fresh_outcomes_already_emitted"] = True
    with pytest.raises(CiboCapitalManagementError, match="already consumed"):
        evaluate_phase22_pre_outcome_provenance(
            execution_manifest=manifest,
            store_contract=_stores(),
            one_shot_guard=guard,
        )
