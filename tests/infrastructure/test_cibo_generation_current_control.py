from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_generation_current_control import (
    CIBO_CURRENT_CONTROL_ID,
    seal_current_generation_control,
)

T0 = datetime(2026, 9, 30, 0, 15, tzinfo=UTC)
SHA = "sha256:" + "a" * 64


def _seal(**overrides):
    values = {
        "git_sha": "1" * 40,
        "sealed_at": T0,
        "trader_surface_sha256": SHA,
        "provider_capability_snapshot_sha256": SHA,
        "capital_state_snapshot_sha256": SHA,
        "capital_utilization_snapshot_sha256": SHA,
        "workflow_evidence_sha256": SHA,
        "world_cup_mission_sha256": SHA,
        "world_cup_gap_matrix_sha256": SHA,
        "all_required_ci_green": True,
        "holdout_2017h1_untouched": True,
    }
    values.update(overrides)
    return seal_current_generation_control(**values)


def test_current_control_seals_exact_research_generation() -> None:
    manifest = _seal()

    assert manifest.control_id == CIBO_CURRENT_CONTROL_ID
    assert manifest.all_required_ci_green is True
    assert manifest.holdout_2017h1_untouched is True
    assert manifest.phase20_v3_mutated is False
    assert manifest.outcome_data_used_to_select_control is False
    assert manifest.runtime_authority is False
    assert manifest.risk_authority is False
    assert manifest.execution_authority is False
    assert manifest.live_authority is False
    assert manifest.real_capital_authority is False
    assert manifest.merge_authority is False
    assert manifest.fingerprint().startswith("sha256:")


def test_current_control_rejects_non_green_ci() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="cannot seal while required CI is not green",
    ):
        _seal(all_required_ci_green=False)


def test_current_control_rejects_opened_holdout() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="requires untouched 2017H1 holdout",
    ):
        _seal(holdout_2017h1_untouched=False)


def test_current_control_rejects_noncanonical_snapshot_digest() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="must be canonical SHA-256",
    ):
        _seal(capital_utilization_snapshot_sha256="not-a-digest")


def test_current_control_cannot_gain_authority_after_seal() -> None:
    manifest = _seal()

    with pytest.raises(
        CiboCompoundCapitalError,
        match="grants no productive authority",
    ):
        replace(manifest, live_authority=True)


def test_current_control_cannot_relabel_mutated_v3() -> None:
    manifest = _seal()

    with pytest.raises(
        CiboCompoundCapitalError,
        match="cannot seal mutated Phase20 V3",
    ):
        replace(manifest, phase20_v3_mutated=True)


def test_current_control_cannot_be_selected_after_outcome_inspection() -> None:
    manifest = _seal()

    with pytest.raises(
        CiboCompoundCapitalError,
        match="cannot be selected from outcome inspection",
    ):
        replace(manifest, outcome_data_used_to_select_control=True)
