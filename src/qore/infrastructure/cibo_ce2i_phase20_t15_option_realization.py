"""Forward realization audit for CE2I T15 known capital options.

A known option is useful evidence only if it can be linked, without hindsight,
from its sealed pre-decision identity to a later forward candidate at the
declared decision step. This audit measures that maturation population. It does
not claim that reservation caused the later opportunity to remain executable,
and it never promotes T15 by itself.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)


@dataclass(frozen=True, slots=True)
class Phase20T15OptionRealization:
    known_option_instances: int
    signal_bound_option_instances: int
    matured_option_instances: int
    materialized_candidate_instances: int
    reconciled_materialized_outcomes: int
    expired_before_materialization: int
    unresolved_matured_options: int
    distinct_origin_epochs: int
    stream_bound: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "known_option_instances",
            "signal_bound_option_instances",
            "matured_option_instances",
            "materialized_candidate_instances",
            "reconciled_materialized_outcomes",
            "expired_before_materialization",
            "unresolved_matured_options",
            "distinct_origin_epochs",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T15 {name} must be non-negative int"
                )
        if self.signal_bound_option_instances > self.known_option_instances:
            raise CiboCapitalManagementError(
                "Phase20 T15 signal-bound options exceed known options"
            )
        if self.matured_option_instances > self.signal_bound_option_instances:
            raise CiboCapitalManagementError(
                "Phase20 T15 matured options exceed signal-bound options"
            )
        if self.materialized_candidate_instances > self.matured_option_instances:
            raise CiboCapitalManagementError(
                "Phase20 T15 materialized options exceed matured options"
            )
        if (
            self.reconciled_materialized_outcomes
            > self.materialized_candidate_instances
        ):
            raise CiboCapitalManagementError(
                "Phase20 T15 reconciled outcomes exceed materialized options"
            )
        if (
            self.expired_before_materialization
            + self.unresolved_matured_options
            + self.materialized_candidate_instances
            > self.matured_option_instances
        ):
            raise CiboCapitalManagementError(
                "Phase20 T15 matured option accounting drift"
            )
        if self.stream_bound and self.signal_bound_option_instances == 0:
            raise CiboCapitalManagementError(
                "Phase20 T15 bound stream requires signal-bound options"
            )
        if not self.stream_bound and not self.blockers:
            raise CiboCapitalManagementError(
                "Phase20 T15 unbound stream must name blockers"
            )


@dataclass(frozen=True, slots=True)
class _KnownOption:
    origin_sha256: str
    origin_epoch_id: str
    origin_decision_at: datetime
    signal_fingerprint: str
    decision_step: int
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class _ForwardCandidate:
    decision_sha256: str
    decision_at: datetime
    current_step: int
    signal_fingerprint: str


def assess_phase20_t15_option_realization(
    evidence_book: VersionedPhase20ForwardEvidenceBook,
) -> Phase20T15OptionRealization:
    """Track pre-decision known options into later fresh forward candidates."""

    if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
        raise CiboCapitalManagementError(
            "Phase20 T15 realization requires canonical forward book"
        )

    options: list[_KnownOption] = []
    candidates: list[_ForwardCandidate] = []
    origin_epochs: set[str] = set()
    total_known = 0
    signal_bound = 0

    for decision in sorted(
        evidence_book.decisions,
        key=lambda item: (item.decision_at, item.evidence_sha256),
    ):
        if not _usable(decision):
            continue
        payload = _payload(decision)
        current_step = _int_field(payload, "current_step")
        raw_candidates = payload.get("candidates")
        if not isinstance(raw_candidates, list):
            raise CiboCapitalManagementError(
                "Phase20 T15 candidate evidence must be list"
            )
        for row in raw_candidates:
            signal = _candidate_signal(row)
            candidates.append(
                _ForwardCandidate(
                    decision_sha256=decision.evidence_sha256,
                    decision_at=decision.decision_at,
                    current_step=current_step,
                    signal_fingerprint=signal,
                )
            )

        raw_options = payload.get("known_options")
        if not isinstance(raw_options, list):
            raise CiboCapitalManagementError(
                "Phase20 T15 known_options must be list"
            )
        if raw_options:
            origin_epochs.add(decision.decision_epoch_id)
        total_known += len(raw_options)
        for row in raw_options:
            parsed = _parse_known_option(
                row=row,
                decision=decision,
            )
            if parsed is None:
                continue
            signal_bound += 1
            options.append(parsed)

    outcomes = {
        (
            item.decision_evidence_sha256,
            item.signal_fingerprint,
        ): item
        for item in evidence_book.outcomes
    }

    latest_decision_at = max(
        (
            item.decision_at
            for item in evidence_book.decisions
            if _usable(item)
        ),
        default=None,
    )
    matured = 0
    materialized = 0
    reconciled = 0
    expired = 0
    unresolved = 0

    for option in options:
        step_has_elapsed = any(
            candidate.current_step >= option.decision_step
            and candidate.decision_at > option.origin_decision_at
            for candidate in candidates
        )
        expiry_has_elapsed = (
            option.expires_at is not None
            and latest_decision_at is not None
            and latest_decision_at >= option.expires_at
        )
        if not step_has_elapsed and not expiry_has_elapsed:
            continue
        matured += 1

        matches = tuple(
            candidate
            for candidate in candidates
            if (
                candidate.decision_at > option.origin_decision_at
                and candidate.current_step == option.decision_step
                and candidate.signal_fingerprint
                == option.signal_fingerprint
                and (
                    option.expires_at is None
                    or candidate.decision_at < option.expires_at
                )
            )
        )
        if matches:
            materialized += 1
            if any(
                (
                    match.decision_sha256,
                    match.signal_fingerprint,
                )
                in outcomes
                for match in matches
            ):
                reconciled += 1
            continue
        if expiry_has_elapsed:
            expired += 1
        else:
            unresolved += 1

    blockers: list[str] = []
    if total_known == 0:
        blockers.append("NO_FORWARD_KNOWN_OPTION_INSTANCES")
    if signal_bound == 0:
        blockers.append("NO_SIGNAL_BOUND_KNOWN_OPTIONS")
    if matured == 0:
        blockers.append("NO_MATURED_KNOWN_OPTION_INSTANCES")
    if materialized == 0:
        blockers.append("NO_KNOWN_OPTION_MATERIALIZED_AS_FUTURE_CANDIDATE")
    blockers.append("COUNTERFACTUAL_RESERVATION_CAUSAL_EFFECT_NOT_IDENTIFIED")
    blockers.append("FRESH_OOS_OPTIONALITY_UTILITY_ANALYSIS_REQUIRED")

    return Phase20T15OptionRealization(
        known_option_instances=total_known,
        signal_bound_option_instances=signal_bound,
        matured_option_instances=matured,
        materialized_candidate_instances=materialized,
        reconciled_materialized_outcomes=reconciled,
        expired_before_materialization=expired,
        unresolved_matured_options=unresolved,
        distinct_origin_epochs=len(origin_epochs),
        stream_bound=signal_bound > 0,
        blockers=tuple(blockers),
    )


def _usable(decision: Phase20ForwardDecisionSeal) -> bool:
    if decision.decision_at < FROZEN_PHASE20D_QUALIFICATION_PLAN.frozen_at:
        return False
    if decision.sealed_at is None:
        return False
    if (
        decision.seal_deadline_at is not None
        and not decision.sealed_within_deadline
    ):
        return False
    return _payload(decision).get("evidence_kind") == "FORWARD_OBSERVED"


def _payload(decision: Phase20ForwardDecisionSeal) -> dict[str, object]:
    try:
        payload = json.loads(decision.canonical_payload_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "Phase20 T15 decision payload is invalid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "Phase20 T15 decision payload must be object"
        )
    return payload


def _parse_known_option(
    *,
    row: object,
    decision: Phase20ForwardDecisionSeal,
) -> _KnownOption | None:
    if not isinstance(row, dict):
        raise CiboCapitalManagementError(
            "Phase20 T15 known option row must be object"
        )
    option = row.get("option")
    if not isinstance(option, dict):
        raise CiboCapitalManagementError(
            "Phase20 T15 known option payload must be object"
        )
    opportunity_id = option.get("opportunity_id")
    if not isinstance(opportunity_id, str) or not opportunity_id:
        raise CiboCapitalManagementError(
            "Phase20 T15 opportunity_id must be non-empty string"
        )
    signal = _signal_from_opportunity_id(opportunity_id)
    if signal is None:
        return None
    decision_step = option.get("decision_step")
    if (
        not isinstance(decision_step, int)
        or isinstance(decision_step, bool)
        or decision_step < 0
    ):
        raise CiboCapitalManagementError(
            "Phase20 T15 option decision_step must be non-negative int"
        )
    known_as_of = _datetime_field(row, "known_as_of")
    if known_as_of > decision.decision_at:
        raise CiboCapitalManagementError(
            "Phase20 T15 known option postdates origin decision"
        )
    if row.get("active_at_decision") is not True:
        raise CiboCapitalManagementError(
            "Phase20 T15 option must be active at origin decision"
        )
    expires_at = _optional_datetime_field(row, "expires_at")
    cancelled_at = _optional_datetime_field(row, "cancelled_at")
    if cancelled_at is not None and cancelled_at <= decision.decision_at:
        raise CiboCapitalManagementError(
            "Phase20 T15 cancelled option cannot be origin evidence"
        )
    return _KnownOption(
        origin_sha256=decision.evidence_sha256,
        origin_epoch_id=decision.decision_epoch_id,
        origin_decision_at=decision.decision_at,
        signal_fingerprint=signal,
        decision_step=decision_step,
        expires_at=expires_at,
    )


def _candidate_signal(row: object) -> str:
    if not isinstance(row, dict):
        raise CiboCapitalManagementError(
            "Phase20 T15 candidate row must be object"
        )
    candidate = row.get("candidate")
    if not isinstance(candidate, dict):
        raise CiboCapitalManagementError(
            "Phase20 T15 candidate payload must be object"
        )
    signal = candidate.get("signal_fingerprint")
    if not isinstance(signal, str) or not signal:
        raise CiboCapitalManagementError(
            "Phase20 T15 candidate signal must be non-empty string"
        )
    return signal


def _signal_from_opportunity_id(opportunity_id: str) -> str | None:
    prefix = "known-option:"
    if not opportunity_id.startswith(prefix):
        return None
    remainder = opportunity_id[len(prefix):]
    trader, separator, signal = remainder.partition(":")
    if not separator or not trader or not signal:
        raise CiboCapitalManagementError(
            "Phase20 T15 signal-bound opportunity_id is malformed"
        )
    return signal


def _int_field(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
    ):
        raise CiboCapitalManagementError(
            f"Phase20 T15 {key} must be non-negative int"
        )
    return value


def _datetime_field(row: dict[str, object], key: str) -> datetime:
    raw = row.get(key)
    if not isinstance(raw, str):
        raise CiboCapitalManagementError(
            f"Phase20 T15 {key} must be ISO datetime string"
        )
    value = datetime.fromisoformat(raw)
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"Phase20 T15 {key} must be timezone-aware"
        )
    return value


def _optional_datetime_field(
    row: dict[str, object],
    key: str,
) -> datetime | None:
    raw = row.get(key)
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise CiboCapitalManagementError(
            f"Phase20 T15 {key} must be ISO datetime/null"
        )
    value = datetime.fromisoformat(raw)
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"Phase20 T15 {key} must be timezone-aware"
        )
    return value
