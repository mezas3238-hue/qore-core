"""Pre-outcome governance for the Phase22 V6 source candidate.

V5 was never executed: its read-only source probe proved that the exact 10/10
surface is unavailable because NAS100/USTEC has no M1 or M5 bars at the V5
opening boundary. V6 is selected mechanically as the immediately preceding
exact six-calendar-month block. No V5 outcomes exist or are used.
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

SOURCE_UNAVAILABLE_V5_CANDIDATE_ID = (
    "CIBO_USD60_6M_HOLDOUT_2014-04-19_2014-10-19_V5"
)
V6_CANDIDATE_ID = (
    "CIBO_USD60_6M_HOLDOUT_2013-10-19_2014-04-19_V6"
)
V5_START_AT = datetime(2014, 4, 19, tzinfo=UTC)

PHASE22_V6_CANDIDATE = CiboHoldoutCandidate(
    candidate_id=V6_CANDIDATE_ID,
    start_at=datetime(2013, 10, 19, tzinfo=UTC),
    end_exclusive_at=V5_START_AT,
    status=CiboHoldoutCandidateStatus.SOURCE_VALIDATION_PENDING,
    selection_rule=(
        "immediately preceding exact six-calendar-month block ending at the "
        "V5 start boundary; selected mechanically after V5 read-only source "
        "availability failed 10/10 without Trader execution or outcome access"
    ),
    outcome_data_inspected_at_selection=False,
    source_validation_complete=False,
)


def assert_phase22_v6_pre_outcome_governance() -> None:
    candidate = PHASE22_V6_CANDIDATE
    if candidate.end_exclusive_at != V5_START_AT:
        raise CiboCapitalManagementError("V6 candidate is not adjacent to V5")
    if candidate.outcome_data_inspected_at_selection:
        raise CiboCapitalManagementError("V6 selection is outcome-contaminated")
    if not candidate_is_burn_clean_for_all_lineages(candidate):
        raise CiboCapitalManagementError("V6 candidate overlaps confirmed burn")


def phase22_v6_governance_payload() -> dict[str, object]:
    assert_phase22_v6_pre_outcome_governance()
    candidate = PHASE22_V6_CANDIDATE
    return {
        "schema": "qore.cibo.phase22.v6-pre-outcome-governance.v1",
        "source_unavailable_v5_candidate_id": SOURCE_UNAVAILABLE_V5_CANDIDATE_ID,
        "v5_fresh_execution_occurred": False,
        "candidate_id": candidate.candidate_id,
        "window": {
            "start": candidate.start_at.isoformat(),
            "end_exclusive": candidate.end_exclusive_at.isoformat(),
        },
        "selection_rule": candidate.selection_rule,
        "selection_outcomes_inspected": False,
        "v5_outcomes_exist": False,
        "policy_retuning_authorized": False,
        "methodology_change_authorized": False,
        "source_validation_complete": False,
        "fresh_execution_authorized": False,
        "broker_mutation_authorized": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
        "merge_authorized": False,
        "productive_authority": False,
    }


assert_phase22_v6_pre_outcome_governance()
