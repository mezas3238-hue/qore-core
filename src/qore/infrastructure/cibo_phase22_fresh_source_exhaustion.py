"""Canonical external-dependency proof for Phase22 fresh-source exhaustion."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_holdout_registry import (
    CONFIRMED_CIBO_BURNS,
    CiboHoldoutCandidate,
    CiboHoldoutCandidateStatus,
    candidate_is_burn_clean_for_all_lineages,
)

V5_RECEIPT_PATH = Path(
    "docs/research/CIBO-PHASE22-V5-SOURCE-UNAVAILABLE-RECEIPT.json"
)
V6_RECEIPT_PATH = Path(
    "docs/research/CIBO-PHASE22-V6-SOURCE-UNAVAILABLE-RECEIPT.json"
)
ARCHIVED_SOURCE_PATH = Path(
    "docs/research/CIBO-PHASE22-NAS100-ARCHIVED-SOURCE-EXHAUSTION-V1.json"
)
OBSERVED_AT = datetime(2026, 10, 4, 2, 21, 27, tzinfo=UTC)
EARLIEST_FUTURE_START = datetime(2026, 9, 17, tzinfo=UTC)
EARLIEST_FUTURE_END = datetime(2027, 3, 17, tzinfo=UTC)
FUTURE_CANDIDATE_ID = (
    "CIBO_USD60_6M_FORWARD_HOLDOUT_2026-09-17_2027-03-17_V7"
)


@dataclass(frozen=True, slots=True)
class FreshSourceExhaustionReceipt:
    observed_at: datetime
    historical_source_exhausted: bool
    archived_nas100_alternative_found: bool
    latest_confirmed_burn_end: datetime
    earliest_future_candidate: CiboHoldoutCandidate
    future_window_complete_at_observation: bool
    outcome_data_used_for_selection: bool = False
    trader_logic_executed: bool = False
    broker_mutation: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise CiboCapitalManagementError("fresh exhaustion observation must be aware")
        if not self.historical_source_exhausted:
            raise CiboCapitalManagementError("historical source exhaustion not proven")
        if self.archived_nas100_alternative_found:
            raise CiboCapitalManagementError("archived NAS100 alternative contradicts exhaustion")
        if self.latest_confirmed_burn_end != EARLIEST_FUTURE_START:
            raise CiboCapitalManagementError("latest burn boundary drift")
        candidate = self.earliest_future_candidate
        if (
            candidate.candidate_id != FUTURE_CANDIDATE_ID
            or candidate.start_at != EARLIEST_FUTURE_START
            or candidate.end_exclusive_at != EARLIEST_FUTURE_END
            or candidate.status is not CiboHoldoutCandidateStatus.SEALED_UNTOUCHED
            or candidate.outcome_data_inspected_at_selection
            or candidate.source_validation_complete
        ):
            raise CiboCapitalManagementError("future candidate governance drift")
        if not candidate_is_burn_clean_for_all_lineages(candidate):
            raise CiboCapitalManagementError("future candidate overlaps confirmed burn")
        if self.future_window_complete_at_observation:
            raise CiboCapitalManagementError("future window falsely marked complete")
        if self.observed_at >= candidate.end_exclusive_at:
            raise CiboCapitalManagementError("observation unexpectedly postdates future window")
        if any(
            (
                self.outcome_data_used_for_selection,
                self.trader_logic_executed,
                self.broker_mutation,
                self.productive_authority,
            )
        ):
            raise CiboCapitalManagementError("fresh exhaustion governance contamination")


def _load(path: Path) -> dict[str, object]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise CiboCapitalManagementError(f"receipt must be object: {path}")
    return raw


def build_fresh_source_exhaustion_receipt(
    repo_root: Path = Path("."),
) -> FreshSourceExhaustionReceipt:
    v5 = _load(repo_root / V5_RECEIPT_PATH)
    v6 = _load(repo_root / V6_RECEIPT_PATH)
    archived = _load(repo_root / ARCHIVED_SOURCE_PATH)

    if (
        v5.get("candidate_id")
        != "CIBO_USD60_6M_HOLDOUT_2014-04-19_2014-10-19_V5"
        or v5.get("source_available") is not False
        or int(v5.get("available_surface_count", -1)) != 8
        or v5.get("outcomes_inspected") is not False
        or v5.get("claim_committed") is not False
    ):
        raise CiboCapitalManagementError("V5 source-unavailable receipt drift")
    if (
        v6.get("candidate_id")
        != "CIBO_USD60_6M_HOLDOUT_2013-10-19_2014-04-19_V6"
        or v6.get("source_available") is not False
        or int(v6.get("available_surface_count", -1)) != 8
        or v6.get("outcomes_inspected") is not False
        or v6.get("claim_committed") is not False
    ):
        raise CiboCapitalManagementError("V6 source-unavailable receipt drift")
    if (
        archived.get("include_archived_symbols") is not True
        or archived.get("matching_symbol_count") != 1
        or archived.get("conclusion")
        != "NO_ARCHIVED_NAS100_EQUIVALENT_WITH_PRE_V4_HISTORY"
        or archived.get("outcomes_inspected") is not False
        or archived.get("broker_mutation") is not False
    ):
        raise CiboCapitalManagementError("archived NAS100 exhaustion receipt drift")

    latest_burn_end = max(item.end_exclusive_at for item in CONFIRMED_CIBO_BURNS)
    future = CiboHoldoutCandidate(
        candidate_id=FUTURE_CANDIDATE_ID,
        start_at=latest_burn_end,
        end_exclusive_at=EARLIEST_FUTURE_END,
        status=CiboHoldoutCandidateStatus.SEALED_UNTOUCHED,
        selection_rule=(
            "earliest exact six-calendar-month interval starting at the latest "
            "confirmed burn end after historical source exhaustion was proven; "
            "selected without reading future outcomes"
        ),
        outcome_data_inspected_at_selection=False,
        source_validation_complete=False,
    )
    return FreshSourceExhaustionReceipt(
        observed_at=OBSERVED_AT,
        historical_source_exhausted=True,
        archived_nas100_alternative_found=False,
        latest_confirmed_burn_end=latest_burn_end,
        earliest_future_candidate=future,
        future_window_complete_at_observation=False,
    )


def payload(repo_root: Path = Path(".")) -> dict[str, object]:
    receipt = build_fresh_source_exhaustion_receipt(repo_root)
    candidate = receipt.earliest_future_candidate
    return {
        "schema": "qore.cibo.phase22.fresh-source-exhaustion.v1",
        "observed_at": receipt.observed_at.isoformat(),
        "historical_source_exhausted": True,
        "archived_nas100_alternative_found": False,
        "latest_confirmed_burn_end": receipt.latest_confirmed_burn_end.isoformat(),
        "earliest_future_candidate": {
            "candidate_id": candidate.candidate_id,
            "start": candidate.start_at.isoformat(),
            "end_exclusive": candidate.end_exclusive_at.isoformat(),
            "status": candidate.status.value,
            "selection_rule": candidate.selection_rule,
        },
        "future_window_complete_at_observation": False,
        "external_dependency": (
            "WAIT_FOR_FORWARD_BURN_CLEAN_WINDOW_TO_COMPLETE_2027-03-17"
        ),
        "outcome_data_used_for_selection": False,
        "trader_logic_executed": False,
        "broker_mutation": False,
        "productive_authority": False,
    }
