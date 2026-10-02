from __future__ import annotations

from dataclasses import replace

import pytest

from qore.infrastructure.cibo_a1_phase22_external_execution_preflight import (
    CANDIDATE_CODE_SHA,
    CANDIDATE_ID,
    CANDIDATE_PARAMETER_SHA256,
    EXECUTION_MANIFEST_SHA256,
    GITHUB_ARTIFACT_DIGEST,
    GITHUB_ARTIFACT_ID,
    INTEGRATOR_HEAD_SHA,
    frozen_a1_phase22_external_execution_preflight,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
)


def test_external_phase22_preflight_pins_verified_artifact_identity() -> None:
    receipt = frozen_a1_phase22_external_execution_preflight()

    assert receipt.integrator_head_sha == INTEGRATOR_HEAD_SHA
    assert receipt.github_artifact_id == GITHUB_ARTIFACT_ID
    assert receipt.github_artifact_digest == GITHUB_ARTIFACT_DIGEST
    assert receipt.execution_manifest_sha256 == EXECUTION_MANIFEST_SHA256
    assert receipt.candidate_id == CANDIDATE_ID
    assert receipt.candidate_code_sha == CANDIDATE_CODE_SHA
    assert receipt.candidate_parameter_sha256 == CANDIDATE_PARAMETER_SHA256
    assert receipt.trader_ids == tuple(
        item.value for item in PHASE19_REQUIRED_TRADERS
    )
    assert receipt.preflight_status == "READY"
    assert receipt.authorized_to_emit_first_fresh_outcome is True


def test_external_phase22_preflight_projects_canonical_execution_identity() -> None:
    receipt = frozen_a1_phase22_external_execution_preflight()
    identity = receipt.execution_identity()

    assert identity.execution_manifest_sha256 == EXECUTION_MANIFEST_SHA256
    assert identity.candidate_code_sha == CANDIDATE_CODE_SHA
    assert identity.candidate_parameter_sha256 == CANDIDATE_PARAMETER_SHA256
    assert identity.fresh_outcomes_executed is False


def test_external_phase22_preflight_cannot_masquerade_as_outcome_evidence() -> None:
    receipt = frozen_a1_phase22_external_execution_preflight()

    with pytest.raises(
        CiboCapitalManagementError,
        match="cannot claim executed/outcome authority",
    ):
        replace(receipt, scientific_outcome_evidence=True)


def test_external_phase22_preflight_cannot_claim_fresh_outcomes() -> None:
    receipt = frozen_a1_phase22_external_execution_preflight()

    with pytest.raises(
        CiboCapitalManagementError,
        match="cannot claim executed/outcome authority",
    ):
        replace(receipt, fresh_outcomes_already_emitted=True)
