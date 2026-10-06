"""Phase22-native reservation counterfactual lineage for CE2I T15.

The active certification holdout is a historical replay. Existing Phase20 T15
reservation audits intentionally accept only FORWARD_OBSERVED evidence and
therefore cannot be reused by rewriting historical decisions or fabricating
provider identifiers. This module consumes the canonical Phase22 historical
replay book read-only and proves reservation provenance plus later option
materialization lineage.

It does not claim that reservation caused the later economic result. That
counterfactual effect still requires the frozen T15 control/treatment utility
gate and strict temporal replication.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    Phase20ForwardPolicyDecisionSeal,
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_phase22_historical_replay_settlement import (
    Phase22HistoricalReplayOutcomeSeal,
    VersionedPhase22HistoricalReplayEvidenceBook,
)

GATE_ID = "CIBO_T15_RESERVATION_COUNTERFACTUAL_LINEAGE_V1"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class T15ReservationCounterfactualLineageReport:
    gate_id: str
    candidate_id: str
    source_population_sha256: str
    policy_population_sha256: str
    amendment_sha256: str
    origin_epochs_with_known_options: int
    known_option_instances: int
    policy_bound_origin_epochs: int
    nonzero_reserve_origin_epochs: int
    matured_option_instances: int
    materialized_candidate_instances: int
    reconciled_materialized_outcomes: int
    lineage_complete: bool
    lineage_blockers: tuple[str, ...]
    counterfactual_effect_identified: bool = False
    future_identity_used_to_set_reserve: bool = False
    future_outcome_used_to_set_reserve: bool = False
    historical_broker_ids_required: bool = False
    productive_authority: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False

    def __post_init__(self) -> None:
        if self.gate_id != GATE_ID:
            raise CiboCapitalManagementError(
                "T15 reservation lineage gate identity drift"
            )
        if not self.candidate_id:
            raise CiboCapitalManagementError(
                "T15 reservation lineage candidate identity required"
            )
        for name in (
            "source_population_sha256",
            "policy_population_sha256",
            "amendment_sha256",
        ):
            _sha(getattr(self, name), name)
        for name in (
            "origin_epochs_with_known_options",
            "known_option_instances",
            "policy_bound_origin_epochs",
            "nonzero_reserve_origin_epochs",
            "matured_option_instances",
            "materialized_candidate_instances",
            "reconciled_materialized_outcomes",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"T15 reservation lineage {name} must be non-negative int"
                )
        if self.policy_bound_origin_epochs > self.origin_epochs_with_known_options:
            raise CiboCapitalManagementError(
                "T15 reservation lineage policy-bound count drift"
            )
        if self.nonzero_reserve_origin_epochs > self.policy_bound_origin_epochs:
            raise CiboCapitalManagementError(
                "T15 reservation lineage reserve count drift"
            )
        if self.materialized_candidate_instances > self.matured_option_instances:
            raise CiboCapitalManagementError(
                "T15 reservation lineage materialized count drift"
            )
        if (
            self.reconciled_materialized_outcomes
            > self.materialized_candidate_instances
        ):
            raise CiboCapitalManagementError(
                "T15 reservation lineage outcome count drift"
            )
        if self.lineage_complete != (not self.lineage_blockers):
            raise CiboCapitalManagementError(
                "T15 reservation lineage completion/blocker drift"
            )
        prohibited = (
            self.counterfactual_effect_identified,
            self.future_identity_used_to_set_reserve,
            self.future_outcome_used_to_set_reserve,
            self.historical_broker_ids_required,
            self.productive_authority,
            self.live_authorized,
            self.real_capital_authorized,
        )
        if any(prohibited):
            raise CiboCapitalManagementError(
                "T15 reservation lineage governance contamination"
            )

    @property
    def scientific_blockers(self) -> tuple[str, ...]:
        return self.lineage_blockers + (
            "COUNTERFACTUAL_RESERVATION_CAUSAL_EFFECT_NOT_IDENTIFIED",
            "T15_CAUSAL_UTILITY_AND_WF1_WF4_REPLICATION_REQUIRED",
        )

    def fingerprint(self) -> str:
        raw = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class _KnownOption:
    origin_sha256: str
    origin_decision_at: datetime
    opportunity_id: str
    signal_fingerprint: str
    decision_step: int
    expires_at: datetime | None


def assess_t15_reservation_counterfactual_lineage(
    *,
    evidence_book: VersionedPhase22HistoricalReplayEvidenceBook,
    policy_book: VersionedPhase20ForwardPolicyBook,
) -> T15ReservationCounterfactualLineageReport:
    """Bind predecision reservation to later Phase22 historical replay evidence."""

    if not isinstance(
        evidence_book,
        VersionedPhase22HistoricalReplayEvidenceBook,
    ):
        raise CiboCapitalManagementError(
            "T15 reservation lineage requires canonical Phase22 replay book"
        )
    if not isinstance(policy_book, VersionedPhase20ForwardPolicyBook):
        raise CiboCapitalManagementError(
            "T15 reservation lineage requires canonical policy book"
        )
    if not evidence_book.decisions:
        raise CiboCapitalManagementError(
            "T15 reservation lineage requires replay decisions"
        )

    candidates = {item.candidate_id for item in evidence_book.decisions}
    if len(candidates) != 1:
        raise CiboCapitalManagementError(
            "T15 reservation lineage candidate drift"
        )
    candidate_id = next(iter(candidates))

    policies = {
        item.evidence_sha256: item
        for item in policy_book.decisions
    }
    outcomes = {
        (item.decision_evidence_sha256, item.signal_fingerprint): item
        for item in evidence_book.outcomes
    }

    origins = 0
    known_count = 0
    policy_bound = 0
    nonzero_reserve = 0
    policy_mismatch = 0
    missing_policy = 0
    options: list[_KnownOption] = []

    ordered_decisions = tuple(
        sorted(
            evidence_book.decisions,
            key=lambda item: (item.decision_at, item.evidence_sha256),
        )
    )

    for decision in ordered_decisions:
        payload = _payload(decision.canonical_payload_json)
        current_step = _int_field(payload, "current_step")
        horizon_steps = _int_field(payload, "horizon_steps")
        raw_options = payload.get("known_options")
        if not isinstance(raw_options, list):
            raise CiboCapitalManagementError(
                "T15 reservation lineage known_options must be list"
            )
        parsed = tuple(
            _parse_known_option(
                row=row,
                decision_sha256=decision.evidence_sha256,
                decision_at=decision.decision_at,
            )
            for row in raw_options
        )
        active = tuple(item for item in parsed if item is not None)
        if not active:
            continue

        origins += 1
        known_count += len(active)
        options.extend(active)
        expected_ids = {
            item.opportunity_id
            for item in active
            if current_step < item.decision_step <= current_step + horizon_steps
        }

        policy = policies.get(decision.evidence_sha256)
        if policy is None:
            missing_policy += 1
            continue
        record = _policy_record(policy)
        mpc = record.get("mpc_plan")
        if not isinstance(mpc, dict):
            raise CiboCapitalManagementError(
                "T15 reservation lineage policy lacks MPC plan"
            )
        considered = _string_set(mpc, "considered_option_ids")
        if considered != expected_ids:
            policy_mismatch += 1
            continue

        reserve_risk = _decimal_field(mpc, "reserve_stop_risk_usd")
        reserve_margin = _decimal_field(mpc, "reserve_margin_usd")
        if reserve_risk < 0 or reserve_margin < 0:
            raise CiboCapitalManagementError(
                "T15 reservation lineage reserve cannot be negative"
            )
        policy_bound += 1
        if expected_ids and (reserve_risk > 0 or reserve_margin > 0):
            nonzero_reserve += 1

    matured = 0
    materialized = 0
    reconciled = 0
    for option in options:
        future = tuple(
            item
            for item in ordered_decisions
            if item.decision_at > option.origin_decision_at
        )
        future_steps = tuple(
            _int_field(_payload(item.canonical_payload_json), "current_step")
            for item in future
        )
        expiry_elapsed = (
            option.expires_at is not None
            and bool(future)
            and future[-1].decision_at >= option.expires_at
        )
        if (
            not any(step >= option.decision_step for step in future_steps)
            and not expiry_elapsed
        ):
            continue
        matured += 1

        matches = tuple(
            item
            for item in future
            if (
                _int_field(
                    _payload(item.canonical_payload_json),
                    "current_step",
                )
                == option.decision_step
                and option.signal_fingerprint in item.signal_fingerprints
                and (
                    option.expires_at is None
                    or item.decision_at < option.expires_at
                )
            )
        )
        if not matches:
            continue
        materialized += 1
        if any(
            (item.evidence_sha256, option.signal_fingerprint) in outcomes
            for item in matches
        ):
            reconciled += 1

    blockers: list[str] = []
    if origins == 0:
        blockers.append("NO_T15_KNOWN_OPTION_ORIGIN_EPOCHS")
    if missing_policy:
        blockers.append("T15_ORIGIN_MISSING_POLICY_RECORD")
    if policy_mismatch:
        blockers.append("T15_CONSIDERED_OPTION_SET_MISMATCH")
    if origins and policy_bound != origins:
        blockers.append("T15_RESERVATION_POLICY_BINDING_INCOMPLETE")
    if origins and nonzero_reserve != origins:
        blockers.append("T15_NONZERO_RESERVATION_NOT_PROVEN_FOR_ALL_ORIGINS")
    if known_count and matured == 0:
        blockers.append("T15_KNOWN_OPTIONS_NOT_YET_MATURED")
    if matured and materialized == 0:
        blockers.append("T15_MATURED_OPTIONS_NOT_MATERIALIZED")
    if materialized and reconciled != materialized:
        blockers.append("T15_MATERIALIZED_OPTION_OUTCOME_RECONCILIATION_INCOMPLETE")

    return T15ReservationCounterfactualLineageReport(
        gate_id=GATE_ID,
        candidate_id=candidate_id,
        source_population_sha256=_source_population_sha256(evidence_book),
        policy_population_sha256=_policy_population_sha256(policy_book),
        amendment_sha256=evidence_book.amendment_sha256,
        origin_epochs_with_known_options=origins,
        known_option_instances=known_count,
        policy_bound_origin_epochs=policy_bound,
        nonzero_reserve_origin_epochs=nonzero_reserve,
        matured_option_instances=matured,
        materialized_candidate_instances=materialized,
        reconciled_materialized_outcomes=reconciled,
        lineage_complete=not blockers,
        lineage_blockers=tuple(blockers),
    )


def _source_population_sha256(
    book: VersionedPhase22HistoricalReplayEvidenceBook,
) -> str:
    payload = {
        "generation": book.generation,
        "amendment_sha256": book.amendment_sha256,
        "decisions": [item.evidence_sha256 for item in book.decisions],
        "outcomes": [item.fingerprint() for item in book.outcomes],
    }
    return _digest(payload)


def _policy_population_sha256(
    book: VersionedPhase20ForwardPolicyBook,
) -> str:
    payload = {
        "generation": book.generation,
        "policies": [
            {
                "evidence_sha256": item.evidence_sha256,
                "policy_record_sha256": item.policy_record_sha256,
            }
            for item in book.decisions
        ],
    }
    return _digest(payload)


def _digest(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _payload(raw: str) -> dict[str, object]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "T15 reservation lineage decision payload invalid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "T15 reservation lineage decision payload must be object"
        )
    if payload.get("evidence_kind") != "HISTORICAL_REPLAY_OBSERVED":
        raise CiboCapitalManagementError(
            "T15 reservation lineage requires historical replay evidence kind"
        )
    return payload


def _policy_record(
    policy: Phase20ForwardPolicyDecisionSeal,
) -> dict[str, object]:
    expected = "sha256:" + hashlib.sha256(
        policy.canonical_record_json.encode("utf-8")
    ).hexdigest()
    if expected != policy.policy_record_sha256:
        raise CiboCapitalManagementError(
            "T15 reservation lineage policy digest drift"
        )
    try:
        record = json.loads(policy.canonical_record_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "T15 reservation lineage policy record invalid JSON"
        ) from error
    if not isinstance(record, dict):
        raise CiboCapitalManagementError(
            "T15 reservation lineage policy record must be object"
        )
    if record.get("evidence_sha256") != policy.evidence_sha256:
        raise CiboCapitalManagementError(
            "T15 reservation lineage policy/evidence binding drift"
        )
    return record


def _parse_known_option(
    *,
    row: object,
    decision_sha256: str,
    decision_at: datetime,
) -> _KnownOption | None:
    if not isinstance(row, dict):
        raise CiboCapitalManagementError(
            "T15 reservation lineage known-option row must be object"
        )
    option = row.get("option")
    if not isinstance(option, dict):
        raise CiboCapitalManagementError(
            "T15 reservation lineage option payload must be object"
        )
    opportunity_id = option.get("opportunity_id")
    if not isinstance(opportunity_id, str) or not opportunity_id:
        raise CiboCapitalManagementError(
            "T15 reservation lineage opportunity id required"
        )
    signal = _signal_from_opportunity_id(opportunity_id)
    if signal is None:
        return None
    decision_step = _int_field(option, "decision_step")
    known_as_of = _datetime_field(row, "known_as_of")
    if known_as_of > decision_at:
        raise CiboCapitalManagementError(
            "T15 reservation lineage known option postdates reservation decision"
        )
    if row.get("active_at_decision") is not True:
        raise CiboCapitalManagementError(
            "T15 reservation lineage option must be active at decision"
        )
    cancelled_at = _optional_datetime_field(row, "cancelled_at")
    if cancelled_at is not None and cancelled_at <= decision_at:
        raise CiboCapitalManagementError(
            "T15 reservation lineage cancelled option cannot drive reserve"
        )
    expires_at = _optional_datetime_field(row, "expires_at")
    return _KnownOption(
        origin_sha256=decision_sha256,
        origin_decision_at=decision_at,
        opportunity_id=opportunity_id,
        signal_fingerprint=signal,
        decision_step=decision_step,
        expires_at=expires_at,
    )


def _signal_from_opportunity_id(value: str) -> str | None:
    prefix = "known-option:"
    if not value.startswith(prefix):
        return None
    remainder = value[len(prefix):]
    trader, separator, signal = remainder.partition(":")
    if not separator or not trader or not signal:
        raise CiboCapitalManagementError(
            "T15 reservation lineage signal-bound opportunity id malformed"
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
            f"T15 reservation lineage {key} must be non-negative int"
        )
    return value


def _decimal_field(payload: dict[str, object], key: str) -> Decimal:
    raw = payload.get(key)
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError) as error:
        raise CiboCapitalManagementError(
            f"T15 reservation lineage {key} must be Decimal-compatible"
        ) from error
    if not value.is_finite():
        raise CiboCapitalManagementError(
            f"T15 reservation lineage {key} must be finite"
        )
    return value


def _string_set(payload: dict[str, object], key: str) -> set[str]:
    raw = payload.get(key)
    if (
        not isinstance(raw, list)
        or any(not isinstance(item, str) or not item for item in raw)
        or len(raw) != len(set(raw))
    ):
        raise CiboCapitalManagementError(
            f"T15 reservation lineage {key} must be unique strings"
        )
    return set(raw)


def _datetime_field(payload: dict[str, object], key: str) -> datetime:
    raw = payload.get(key)
    if not isinstance(raw, str):
        raise CiboCapitalManagementError(
            f"T15 reservation lineage {key} must be ISO datetime"
        )
    try:
        value = datetime.fromisoformat(raw)
    except ValueError as error:
        raise CiboCapitalManagementError(
            f"T15 reservation lineage {key} invalid datetime"
        ) from error
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"T15 reservation lineage {key} must be timezone-aware"
        )
    return value


def _optional_datetime_field(
    payload: dict[str, object],
    key: str,
) -> datetime | None:
    raw = payload.get(key)
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise CiboCapitalManagementError(
            f"T15 reservation lineage {key} must be ISO datetime or null"
        )
    try:
        value = datetime.fromisoformat(raw)
    except ValueError as error:
        raise CiboCapitalManagementError(
            f"T15 reservation lineage {key} invalid datetime"
        ) from error
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"T15 reservation lineage {key} must be timezone-aware"
        )
    return value


def _sha(value: str, field_name: str) -> None:
    if _SHA256_RE.fullmatch(value) is None:
        raise CiboCapitalManagementError(
            f"T15 reservation lineage {field_name} invalid"
        )


def _outcome_identity(
    outcome: Phase22HistoricalReplayOutcomeSeal,
) -> tuple[str, str]:
    return outcome.decision_evidence_sha256, outcome.signal_fingerprint
