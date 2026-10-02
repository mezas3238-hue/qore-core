"""Pre-outcome governance for the Phase22 V5 successor fresh cycle.

V4 is durably consumed/invalid and may never be rerun. V5 is selected
mechanically as the immediately preceding exact six-calendar-month block.
This module does not read market data, inspect outcomes, change Trader policy,
or grant fresh execution.
"""

from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_holdout_registry import (
    CiboHoldoutCandidate,
    CiboHoldoutCandidateStatus,
    candidate_is_burn_clean_for_all_lineages,
)

CONSUMED_V4_CANDIDATE_ID = (
    "CIBO_USD60_6M_HOLDOUT_2014-10-19_2015-04-19_V4"
)
V5_CANDIDATE_ID = (
    "CIBO_USD60_6M_HOLDOUT_2014-04-19_2014-10-19_V5"
)
V4_START_AT = datetime(2014, 10, 19, tzinfo=UTC)

PHASE22_V5_CANDIDATE = CiboHoldoutCandidate(
    candidate_id=V5_CANDIDATE_ID,
    start_at=datetime(2014, 4, 19, tzinfo=UTC),
    end_exclusive_at=V4_START_AT,
    status=CiboHoldoutCandidateStatus.SOURCE_VALIDATION_PENDING,
    selection_rule=(
        "immediately preceding exact six-calendar-month block ending at the "
        "V4 start boundary; selected mechanically after V4 was durably "
        "consumed/invalid without using V4 lane outcomes or inspecting V5 "
        "outcomes"
    ),
    outcome_data_inspected_at_selection=False,
    source_validation_complete=False,
)


def assert_phase22_v5_pre_outcome_governance() -> None:
    candidate = PHASE22_V5_CANDIDATE
    if candidate.end_exclusive_at != V4_START_AT:
        raise CiboCapitalManagementError("V5 candidate is not adjacent to V4")
    if candidate.outcome_data_inspected_at_selection:
        raise CiboCapitalManagementError("V5 selection is outcome-contaminated")
    if not candidate_is_burn_clean_for_all_lineages(candidate):
        raise CiboCapitalManagementError("V5 candidate overlaps confirmed burn")


def phase22_v5_governance_payload() -> dict[str, object]:
    assert_phase22_v5_pre_outcome_governance()
    candidate = PHASE22_V5_CANDIDATE
    return {
        "schema": "qore.cibo.phase22.v5-pre-outcome-governance.v1",
        "consumed_v4_candidate_id": CONSUMED_V4_CANDIDATE_ID,
        "v4_rerun_authorized": False,
        "candidate_id": candidate.candidate_id,
        "window": {
            "start": candidate.start_at.isoformat(),
            "end_exclusive": candidate.end_exclusive_at.isoformat(),
        },
        "selection_rule": candidate.selection_rule,
        "selection_outcomes_inspected": False,
        "v4_lane_outcomes_used_for_selection": False,
        "policy_retuning_authorized": False,
        "methodology_change_authorized": False,
        "source_validation_complete": False,
        "fresh_execution_authorized": False,
        "second_v4_execution_authorized": False,
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
        "merge_authorized": False,
        "productive_authority": False,
    }


assert_phase22_v5_pre_outcome_governance()
