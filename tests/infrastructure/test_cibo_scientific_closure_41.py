from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_scientific_closure_41 import (
    CONSUMED_INVALID_V4_HOLDOUT_ID,
    SOURCE_UNAVAILABLE_V5_HOLDOUT_ID,
    CANONICAL_POLICY_IDENTITY,
    CANONICAL_PROVIDER_IDENTITY,
    COMPLETED,
    FALSIFIED,
    FINAL_EXAM_IDS,
    FRESH_OOS_ID,
    OPEN_PREIMAGE,
    PRE_CLOSURE_OPEN_IDS,
    SCIENTIFIC_CLOSURE_41_IDS,
    SCIENTIFIC_CLOSURE_EXTERNAL_IDS,
    ScientificClosure41Evidence,
    apply_scientific_closure_41_to_ledger_copy,
    build_scientific_closure_41_package,
    validate_scientific_closure_41_preimage,
)

LEDGER_PATH = Path("docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json")
SUCCESSOR_HOLDOUT_ID = "CIBO_USD60_6M_HOLDOUT_2013-10-19_2014-04-19_V6"


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode("utf-8")).hexdigest()


def _evidence(
    workstream_id: str,
    *,
    status: str = "PASS",
    manifest: str | None = None,
    policy_identity: str = CANONICAL_POLICY_IDENTITY,
    provider_identity: str = CANONICAL_PROVIDER_IDENTITY,
    holdout_id: str = SUCCESSOR_HOLDOUT_ID,
    causal_lineage: str | None = None,
    evidence_sha256s: tuple[str, ...] | None = None,
    synthetic: bool = False,
    future_leakage: bool = False,
    outcome_aware: bool = False,
    integrity_result: str = "PASS",
) -> ScientificClosure41Evidence:
    return ScientificClosure41Evidence(
        workstream_id=workstream_id,
        previous_disposition=(
            OPEN_PREIMAGE
            if workstream_id == FRESH_OOS_ID
            else "EXTERNAL_DEPENDENCY_BLOCKED"
        ),
        scientific_hypothesis=f"Frozen hypothesis for {workstream_id}",
        evidence_refs=(f"artifact://{workstream_id}",),
        evidence_sha256s=(
            (_sha(f"evidence:{workstream_id}"),)
            if evidence_sha256s is None
            else evidence_sha256s
        ),
        population_identity=f"phase22-v6:{workstream_id}",
        policy_identity=policy_identity,
        provider_identity=provider_identity,
        causal_lineage=causal_lineage or _sha(f"lineage:{workstream_id}"),
        economic_result="PASS" if status == "PASS" else "FAIL",
        stress_result="PASS",
        temporal_replication_result="PASS",
        integrity_result=integrity_result,
        source_gate_status=status,
        terminal_reason=f"Frozen gate result for {workstream_id}",
        evaluated_at=datetime(2026, 10, 2, 12, 0, tzinfo=UTC),
        phase22_manifest_sha256=manifest or _sha("phase22-manifest"),
        holdout_id=holdout_id,
        evidence_origin="CANONICAL_GATE_RECEIPT",
        synthetic_evidence_used=synthetic,
        future_leakage_detected=future_leakage,
        outcome_aware_evidence=outcome_aware,
    )


def _package(
    *,
    fail_id: str | None = None,
):
    manifest = _sha("phase22-manifest")
    evidence = tuple(
        _evidence(
            workstream_id,
            status="FAIL" if workstream_id == fail_id else "PASS",
            manifest=manifest,
        )
        for workstream_id in SCIENTIFIC_CLOSURE_41_IDS
    )
    return build_scientific_closure_41_package(
        phase22_manifest_sha256=manifest,
        evidence=evidence,
    )


def _ledger() -> dict[str, object]:
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def test_exact_41_workstream_ownership_matches_current_ledger() -> None:
    summary = validate_scientific_closure_41_preimage(_ledger())

    assert len(SCIENTIFIC_CLOSURE_41_IDS) == 41
    assert len(set(SCIENTIFIC_CLOSURE_41_IDS)) == 41
    assert len(SCIENTIFIC_CLOSURE_EXTERNAL_IDS) == 40
    assert summary["external_dependency_blocked"] == 40
    assert summary["fresh_oos_open"] is True
    assert tuple(summary["open_workstream_ids"]) == PRE_CLOSURE_OPEN_IDS
    assert tuple(summary["open_exam_ids"]) == FINAL_EXAM_IDS


def test_package_rejects_missing_workstream() -> None:
    manifest = _sha("phase22-manifest")
    evidence = tuple(
        _evidence(item, manifest=manifest)
        for item in SCIENTIFIC_CLOSURE_41_IDS[:-1]
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="exact ownership mismatch",
    ):
        build_scientific_closure_41_package(
            phase22_manifest_sha256=manifest,
            evidence=evidence,
        )


def test_out_of_scope_workstream_is_rejected() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="outside exact ownership",
    ):
        _evidence("T03")


def test_synthetic_evidence_cannot_close_real_workstream() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="contaminated evidence",
    ):
        _evidence("T02", synthetic=True)


def test_missing_digest_fails_closed() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="digests required",
    ):
        _evidence("T02", evidence_sha256s=())


def test_incorrect_lineage_fails_closed() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="causal lineage",
    ):
        _evidence("T02", causal_lineage="not-a-digest")


def test_provider_identity_drift_fails_closed() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="provider identity drift",
    ):
        _evidence("T02", provider_identity="other-provider")


def test_policy_identity_drift_fails_closed() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="policy identity drift",
    ):
        _evidence("T02", policy_identity=_sha("other-policy"))


def test_holdout_mismatch_fails_closed() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="versioned fresh holdout id",
    ):
        _evidence(
            "T02",
            holdout_id="CIBO_USD60_6M_HOLDOUT_2017H1_BURNED",
        )


@pytest.mark.parametrize(
    "holdout_id",
    [CONSUMED_INVALID_V4_HOLDOUT_ID, SOURCE_UNAVAILABLE_V5_HOLDOUT_ID],
)
def test_known_noncertifiable_holdouts_fail_closed(holdout_id: str) -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="explicitly non-certifiable",
    ):
        _evidence("T02", holdout_id=holdout_id)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"future_leakage": True}, "contaminated evidence"),
        ({"outcome_aware": True}, "contaminated evidence"),
    ],
)
def test_future_or_outcome_aware_evidence_fails_closed(
    kwargs: dict[str, bool],
    message: str,
) -> None:
    with pytest.raises(CiboCapitalManagementError, match=message):
        _evidence("T02", **kwargs)


def test_valid_pass_maps_only_to_completed_and_proven() -> None:
    evidence = _evidence("T02", status="PASS")

    assert evidence.terminal_disposition == COMPLETED
    assert evidence.productive_authority is False
    assert evidence.live_authorized is False
    assert evidence.real_capital_authorized is False


def test_valid_scientific_fail_maps_to_falsified_and_closed() -> None:
    evidence = _evidence("T02", status="FAIL")

    assert evidence.terminal_disposition == FALSIFIED


@pytest.mark.parametrize("status", ["NOT_READY", "INVALID"])
def test_not_ready_or_invalid_cannot_be_terminal(status: str) -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="NOT_READY/INVALID",
    ):
        _evidence("T02", status=status)



def test_package_accepts_one_successor_holdout_and_rejects_cross_holdout_mix() -> None:
    manifest = _sha("phase22-successor-manifest")
    successor = "CIBO_USD60_6M_HOLDOUT_2013-10-19_2014-04-19_V6"
    evidence = tuple(
        _evidence(workstream_id, manifest=manifest, holdout_id=successor)
        for workstream_id in SCIENTIFIC_CLOSURE_41_IDS
    )
    package = build_scientific_closure_41_package(
        phase22_manifest_sha256=manifest,
        evidence=evidence,
    )
    assert package.holdout_id == successor

    mixed = (*evidence[:-1], _evidence(
        SCIENTIFIC_CLOSURE_41_IDS[-1],
        manifest=manifest,
        holdout_id="CIBO_USD60_6M_HOLDOUT_2013-04-19_2013-10-19_V7",
    ))
    with pytest.raises(
        CiboCapitalManagementError,
        match="multiple fresh holdouts",
    ):
        build_scientific_closure_41_package(
            phase22_manifest_sha256=manifest,
            evidence=mixed,
        )

def test_package_accepts_terminal_falsification_without_rescue() -> None:
    package = _package(fail_id="GEN-C12")

    assert package.falsified_ids == ("GEN-C12",)
    assert len(package.completed_ids) == 40
    assert package.certification_claimed is False
    assert package.productive_authority is False


def test_transition_modifies_only_exact_41_and_leaves_exams_open() -> None:
    ledger = _ledger()
    before = json.loads(json.dumps(ledger))
    package = _package(fail_id="GEN-C12")

    updated, receipt = apply_scientific_closure_41_to_ledger_copy(
        ledger=ledger,
        package=package,
    )

    rows = {
        row["id"]: row
        for row in updated["workstreams"]
        if row.get("mandatory") is True
    }
    before_rows = {
        row["id"]: row
        for row in before["workstreams"]
        if row.get("mandatory") is True
    }

    for workstream_id in SCIENTIFIC_CLOSURE_41_IDS:
        assert rows[workstream_id]["terminal_disposition"] in {
            COMPLETED,
            FALSIFIED,
        }

    for workstream_id in (
        "T03",
        "T16",
        "T17",
        "PROVIDER_ECONOMICS",
        "FORWARD_QUALIFICATION",
    ):
        assert rows[workstream_id] == before_rows[workstream_id]

    assert receipt.residual_external_ids == ()
    assert receipt.open_exam_ids == FINAL_EXAM_IDS
    assert rows["FINAL_INTEGRATED_CIBO_EXAM"].get(
        "terminal_disposition"
    ) in {None, ""}
    assert rows["WORLD_CUP_MAXIMUM_CAPABILITY_EXAM"].get(
        "terminal_disposition"
    ) in {None, ""}
    assert receipt.certification_claimed is False
    assert receipt.canonical_ledger_modified is False
    assert receipt.productive_authority is False
    assert receipt.live_authorized is False
    assert receipt.real_capital_authorized is False


def test_transition_rejects_reopened_or_preterminal_target() -> None:
    ledger = _ledger()
    for row in ledger["workstreams"]:
        if row.get("id") == "T02":
            row["terminal_disposition"] = "COMPLETED_AND_PROVEN"
            break

    with pytest.raises(
        CiboCapitalManagementError,
        match="external surface is not exact",
    ):
        apply_scientific_closure_41_to_ledger_copy(
            ledger=ledger,
            package=_package(),
        )


def test_legitimate_integrity_failure_can_be_terminal_falsification() -> None:
    evidence = _evidence(
        "T02",
        status="FAIL",
        integrity_result="FAIL",
    )

    assert evidence.terminal_disposition == FALSIFIED


def test_integrity_failure_can_never_hide_under_pass() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="PASS cannot hide failed dimensions",
    ):
        _evidence(
            "T02",
            status="PASS",
            integrity_result="FAIL",
        )
