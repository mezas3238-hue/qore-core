from __future__ import annotations

import importlib.util
from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
from pathlib import Path

import pytest

from qore.infrastructure.cibo_arch_a_final_source_truth_control import (
    FinalSourceTruthManifest,
    build_final_source_truth_control,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

_FIXTURE_PATH = Path(__file__).with_name("test_cibo_ce2i_final_certification.py")
_SPEC = importlib.util.spec_from_file_location("_final_cert_fixture_p1", _FIXTURE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_FIXTURE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_FIXTURE)


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode("utf-8")).hexdigest()


def _manifest() -> FinalSourceTruthManifest:
    return FinalSourceTruthManifest(
        schema="qore.cibo.final-source-truth-manifest.v2",
        integrated_git_sha="a" * 40,
        architect_a_head_sha="b" * 40,
        architect_b_head_sha="c" * 40,
        phase22_handoff_manifest_sha256=_sha("phase22-handoff"),
        mandatory_count=64,
        terminal_count=62,
        open_ids=(
            "FINAL_INTEGRATED_CIBO_EXAM",
            "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
        ),
        file_sha256s=tuple(
            (role, _sha(role))
            for role in (
                "master_ledger",
                "source_truth_reconciliation",
                "final_integrated_exam_protocol",
                "world_cup_exam_protocol",
                "certification_sequence",
                "architect_a_science",
                "architect_b_phase22",
            )
        ),
        unaccounted_files=(),
        certification_critical_external_blockers=(),
        stale_current_state_claims=(),
    )


def test_p1_source_truth_binds_two_heads_phase22_and_64_62_2() -> None:
    phase21 = _FIXTURE._phase21_manifest()
    phase22 = _FIXTURE._receipt(phase21_sha=phase21.manifest_sha256())
    manifest = _manifest()
    receipt = build_final_source_truth_control(
        manifest=manifest,
        phase22_receipt=phase22,
        observed_at=phase22.qualified_at + timedelta(minutes=1),
    )
    assert receipt.receipt_id == "P1_SOURCE_OF_TRUTH_RECONCILED"
    assert receipt.integrated_git_sha == manifest.integrated_git_sha
    assert (
        receipt.phase22_qualification_artifact_sha256
        == phase22.qualification_artifact_sha256
    )
    assert manifest.fingerprint().startswith("sha256:")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("unaccounted_files", ("x.py",), "unaccounted files"),
        (
            "certification_critical_external_blockers",
            ("T09",),
            "certification-critical external blockers",
        ),
        (
            "stale_current_state_claims",
            ("2017H1_ACTIVE",),
            "stale current-state claims",
        ),
    ),
)
def test_p1_source_truth_fails_closed_on_unreconciled_state(
    field: str,
    value: tuple[str, ...],
    message: str,
) -> None:
    phase21 = _FIXTURE._phase21_manifest()
    phase22 = _FIXTURE._receipt(phase21_sha=phase21.manifest_sha256())
    manifest = replace(_manifest(), **{field: value})
    with pytest.raises(CiboCapitalManagementError, match=message):
        build_final_source_truth_control(
            manifest=manifest,
            phase22_receipt=phase22,
            observed_at=phase22.qualified_at + timedelta(minutes=1),
        )


def test_p1_source_truth_rejects_wrong_topology() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="exact 64/62 pre-exam topology",
    ):
        replace(_manifest(), terminal_count=63)


def test_p1_source_truth_must_be_post_phase22() -> None:
    phase21 = _FIXTURE._phase21_manifest()
    phase22 = _FIXTURE._receipt(phase21_sha=phase21.manifest_sha256())
    with pytest.raises(
        CiboCapitalManagementError,
        match="must be post-Phase22 qualification",
    ):
        build_final_source_truth_control(
            manifest=_manifest(),
            phase22_receipt=phase22,
            observed_at=phase22.qualified_at,
        )
