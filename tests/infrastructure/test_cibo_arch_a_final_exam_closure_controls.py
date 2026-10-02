from __future__ import annotations

import importlib.util
from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
from pathlib import Path

import pytest

from qore.infrastructure.cibo_arch_a_final_exam_closure_controls import (
    build_architect_a_final_exam_closure_controls,
    build_scientific_closure_41_final_exam_controls,
)
from qore.infrastructure.cibo_arch_a_internal_readiness import (
    _COMPOUND_P8_REQUIRED_PROVEN_IDS,
    ArchitectAPhase22V2CompoundClosureReceipt,
    ArchitectAPhase22V2ScientificClosureReceipt,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

_FIXTURE_PATH = Path(__file__).with_name("test_cibo_ce2i_final_certification.py")
_SPEC = importlib.util.spec_from_file_location("_final_cert_fixture_controls", _FIXTURE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_FIXTURE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_FIXTURE)

_CLOSURE_FIXTURE_PATH = Path(__file__).with_name(
    "test_cibo_scientific_closure_41.py"
)
_CLOSURE_SPEC = importlib.util.spec_from_file_location(
    "_closure41_fixture_controls",
    _CLOSURE_FIXTURE_PATH,
)
assert _CLOSURE_SPEC is not None and _CLOSURE_SPEC.loader is not None
_CLOSURE_FIXTURE = importlib.util.module_from_spec(_CLOSURE_SPEC)
_CLOSURE_SPEC.loader.exec_module(_CLOSURE_FIXTURE)


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode("utf-8")).hexdigest()


def _closures():
    scientific = ArchitectAPhase22V2ScientificClosureReceipt(
        phase22_manifest_sha256=_sha("manifest"),
        closure_batch_sha256=_sha("batch"),
        completed_ids=("T04",),
        falsified_ids=("GEN-C12",),
        scientific_closure_terminal=True,
        blockers=(),
    )
    compound = ArchitectAPhase22V2CompoundClosureReceipt(
        phase22_manifest_sha256=_sha("manifest"),
        closure_batch_sha256=_sha("batch"),
        genc1_evidence_sha256=_sha("genc1"),
        required_proven_ids=_COMPOUND_P8_REQUIRED_PROVEN_IDS,
        missing_or_nonproven_ids=(),
        compound_closure_terminal=True,
        blockers=(),
    )
    return scientific, compound


def test_arch_a_builds_bound_p7_p8_controls_post_phase22() -> None:
    phase21 = _FIXTURE._phase21_manifest()
    phase22 = _FIXTURE._receipt(phase21_sha=phase21.manifest_sha256())
    scientific, compound = _closures()
    observed = phase22.qualified_at + timedelta(minutes=1)

    p7, p8 = build_architect_a_final_exam_closure_controls(
        integrated_git_sha="a" * 40,
        phase22_receipt=phase22,
        scientific_closure=scientific,
        compound_closure=compound,
        observed_at=observed,
    )

    assert p7.receipt_id == "P7_SCIENTIFIC_CLOSURE"
    assert p8.receipt_id == "P8_COMPOUND_CLOSURE"
    assert (
        p7.phase22_qualification_artifact_sha256
        == phase22.qualification_artifact_sha256
    )
    assert p7.policy_identity_sha256 == phase22.candidate_parameter_sha256
    assert p8.integrated_git_sha == "a" * 40


def test_arch_a_closure_controls_require_post_phase22_time() -> None:
    phase21 = _FIXTURE._phase21_manifest()
    phase22 = _FIXTURE._receipt(phase21_sha=phase21.manifest_sha256())
    scientific, compound = _closures()

    with pytest.raises(
        CiboCapitalManagementError,
        match="must be post-Phase22 qualification",
    ):
        build_architect_a_final_exam_closure_controls(
            integrated_git_sha="a" * 40,
            phase22_receipt=phase22,
            scientific_closure=scientific,
            compound_closure=compound,
            observed_at=phase22.qualified_at,
        )


def test_arch_a_closure_controls_reject_cross_batch_lineage() -> None:
    phase21 = _FIXTURE._phase21_manifest()
    phase22 = _FIXTURE._receipt(phase21_sha=phase21.manifest_sha256())
    scientific, compound = _closures()
    compound = replace(compound, closure_batch_sha256=_sha("other-batch"))

    with pytest.raises(CiboCapitalManagementError, match="closure lineage drift"):
        build_architect_a_final_exam_closure_controls(
            integrated_git_sha="a" * 40,
            phase22_receipt=phase22,
            scientific_closure=scientific,
            compound_closure=compound,
            observed_at=phase22.qualified_at + timedelta(minutes=1),
        )


def test_arch_a_closure_controls_reject_nonproven_compound() -> None:
    phase21 = _FIXTURE._phase21_manifest()
    phase22 = _FIXTURE._receipt(phase21_sha=phase21.manifest_sha256())
    scientific, compound = _closures()
    compound = replace(
        compound,
        missing_or_nonproven_ids=("GEN-C9",),
        compound_closure_terminal=False,
        blockers=("GEN-C9_NOT_PROVEN",),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="P8 Compound closure is not proven",
    ):
        build_architect_a_final_exam_closure_controls(
            integrated_git_sha="a" * 40,
            phase22_receipt=phase22,
            scientific_closure=scientific,
            compound_closure=compound,
            observed_at=phase22.qualified_at + timedelta(minutes=1),
        )


def test_closure41_p7_p8_accept_terminal_scientific_falsification() -> None:
    phase21 = _FIXTURE._phase21_manifest()
    phase22 = _FIXTURE._receipt(phase21_sha=phase21.manifest_sha256())
    package = _CLOSURE_FIXTURE._package(fail_id="ADVERSARIAL_STRESS")

    p7, p8 = build_scientific_closure_41_final_exam_controls(
        integrated_git_sha="a" * 40,
        phase22_receipt=phase22,
        closure_package=package,
        observed_at=phase22.qualified_at + timedelta(minutes=1),
    )

    assert p7.producer_gate_id == "CIBO_SCIENTIFIC_CLOSURE_41_V1"
    assert p8.producer_gate_id == "CIBO_CAPITAL_COMPOUND_CLOSURE_13_V1"
    assert p7.receipt_id == "P7_SCIENTIFIC_CLOSURE"
    assert p8.receipt_id == "P8_COMPOUND_CLOSURE"
    p8_payload = json.loads(p8.source_artifact_json)
    assert p8_payload["falsified_ids"] == ["ADVERSARIAL_STRESS"]
    assert p8_payload["capital_compound_closure_terminal"] is True
