from __future__ import annotations

from qore.infrastructure.cibo_arch2_forward_qualification_reconciliation import (
    FORWARD_RECOMMENDATION,
    FRESH_OOS_LOCAL_STATE,
    build_arch2_forward_qualification_reconciliation,
)


def test_forward_qualification_is_superseded_but_fresh_oos_waits_for_integrator() -> None:
    state = build_arch2_forward_qualification_reconciliation()

    assert state.forward_qualification_recommendation == FORWARD_RECOMMENDATION
    assert state.forward_qualification_recommendation == (
        "SUPERSEDED_WITH_PROVEN_LINEAGE"
    )
    assert state.old_qualification_plan_bound_as_superseded is True
    assert state.old_qualification_plan_sha_bound is True
    assert state.provider_execution_plane_ready is True
    assert state.dual_evidence_activation_ready is True
    assert state.frozen_before_holdout_outcomes is True
    assert state.historical_fill_fabrication_forbidden is True

    assert state.fresh_oos_local_state == FRESH_OOS_LOCAL_STATE
    assert state.fresh_oos_local_state == "WAITING_ON_INTEGRATOR_RECEIPT"
    assert state.fresh_oos_remaining_requirement == (
        "PHASE22_V2_FRESH_OUTCOME_RECEIPT_REQUIRED"
    )
    assert state.phase22_v2_consumed is False
    assert state.terminal_disposition_assigned is False
    assert state.productive_authority is False
