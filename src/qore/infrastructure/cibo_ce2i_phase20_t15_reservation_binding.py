"""Bind CE2I T15 known options to the sealed Phase20I MPC reserve.

T15 realization evidence alone does not prove that capital was actually
reserved for an option. This audit joins each fresh FORWARD_OBSERVED origin
decision to its immutable policy record and verifies:

- every known option inside the frozen horizon appears in considered_option_ids;
- every representative option is one of those considered options;
- the sealed reserve geometry matches the representative minimum risk/margin;
- recovery/halt preserves the complete sealed headroom; and
- the policy-record SHA matches its canonical JSON bytes.

No future option materialization or outcome magnitude is used. Complete binding
proves provenance of the reservation only, not its counterfactual causal effect
or economic utility.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_policy_store import (
    VersionedPhase20ForwardPolicyBook,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)

_FULL_RESERVE_POSTURES = {"RECOVERY", "HALT_NEW_CAPITAL"}


@dataclass(frozen=True, slots=True)
class Phase20T15ReservationBinding:
    origin_epochs_with_known_options: int
    known_option_instances: int
    in_horizon_option_instances: int
    considered_option_instances: int
    representative_option_instances: int
    policy_bound_origin_epochs: int
    geometry_verified_origin_epochs: int
    nonzero_reserve_origin_epochs: int
    completely_bound_origin_epochs: int
    missing_policy_origin_epochs: int
    considered_set_mismatch_epochs: int
    reserve_geometry_mismatch_epochs: int
    reservation_binding_complete: bool
    future_materialization_used: bool
    outcome_magnitudes_read: bool
    counterfactual_reservation_effect_identified: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "origin_epochs_with_known_options",
            "known_option_instances",
            "in_horizon_option_instances",
            "considered_option_instances",
            "representative_option_instances",
            "policy_bound_origin_epochs",
            "geometry_verified_origin_epochs",
            "nonzero_reserve_origin_epochs",
            "completely_bound_origin_epochs",
            "missing_policy_origin_epochs",
            "considered_set_mismatch_epochs",
            "reserve_geometry_mismatch_epochs",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T15 binding {name} must be non-negative int"
                )
        for name in (
            "reservation_binding_complete",
            "future_materialization_used",
            "outcome_magnitudes_read",
            "counterfactual_reservation_effect_identified",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"Phase20 T15 binding {name} must be bool"
                )
        if self.future_materialization_used or self.outcome_magnitudes_read:
            raise CiboCapitalManagementError(
                "Phase20 T15 reservation binding must remain pre-outcome"
            )
        if self.counterfactual_reservation_effect_identified:
            raise CiboCapitalManagementError(
                "Phase20 T15 binding cannot identify counterfactual effect"
            )
        if self.reservation_binding_complete != (
            self.origin_epochs_with_known_options > 0
            and self.completely_bound_origin_epochs
            == self.origin_epochs_with_known_options
        ):
            raise CiboCapitalManagementError(
                "Phase20 T15 reservation binding completion drift"
            )


@dataclass(frozen=True, slots=True)
class _Option:
    opportunity_id: str
    decision_step: int
    minimum_stop_risk_usd: Decimal
    minimum_margin_usd: Decimal


def assess_phase20_t15_reservation_binding(
    *,
    evidence_book: VersionedPhase20ForwardEvidenceBook,
    policy_book: VersionedPhase20ForwardPolicyBook,
) -> Phase20T15ReservationBinding:
    """Verify option→MPC reservation provenance without reading outcomes."""

    if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
        raise CiboCapitalManagementError(
            "Phase20 T15 binding requires canonical forward evidence book"
        )
    if not isinstance(policy_book, VersionedPhase20ForwardPolicyBook):
        raise CiboCapitalManagementError(
            "Phase20 T15 binding requires canonical policy book"
        )

    policies = {
        item.evidence_sha256: item for item in policy_book.decisions
    }
    origins = 0
    known_count = 0
    in_horizon_count = 0
    considered_count = 0
    representative_count = 0
    policy_bound = 0
    geometry_verified = 0
    nonzero_reserve = 0
    completely_bound = 0
    missing_policy = 0
    set_mismatch = 0
    geometry_mismatch = 0

    for decision in sorted(
        evidence_book.decisions,
        key=lambda item: (item.decision_at, item.evidence_sha256),
    ):
        if not _usable(decision):
            continue
        payload = _payload(decision)
        options = _options(payload)
        if not options:
            continue
        origins += 1
        known_count += len(options)
        current_step = _int_field(payload, "current_step")
        horizon_steps = _positive_int_field(payload, "horizon_steps")
        horizon_end = current_step + horizon_steps
        in_horizon = tuple(
            item
            for item in options
            if current_step < item.decision_step <= horizon_end
        )
        in_horizon_count += len(in_horizon)
        expected_ids = {item.opportunity_id for item in in_horizon}

        policy = policies.get(decision.evidence_sha256)
        if policy is None:
            missing_policy += 1
            continue
        _verify_policy_sha(policy.policy_record_sha256, policy.canonical_record_json)
        record = _json_object(
            policy.canonical_record_json,
            "Phase20 T15 canonical policy record",
        )
        if record.get("evidence_sha256") != decision.evidence_sha256:
            raise CiboCapitalManagementError(
                "Phase20 T15 policy/evidence SHA binding mismatch"
            )
        mpc = record.get("mpc_plan")
        if not isinstance(mpc, dict):
            raise CiboCapitalManagementError(
                "Phase20 T15 policy record lacks canonical MPC plan"
            )
        policy_bound += 1

        considered = _string_list(mpc, "considered_option_ids")
        representatives = _string_list(mpc, "representative_option_ids")
        considered_count += len(considered)
        representative_count += len(representatives)

        sets_match = set(considered) == expected_ids
        if not sets_match:
            set_mismatch += 1
        if not set(representatives).issubset(set(considered)):
            raise CiboCapitalManagementError(
                "Phase20 T15 representative option escaped considered set"
            )

        reserve_risk = _decimal_field(mpc, "reserve_stop_risk_usd")
        reserve_margin = _decimal_field(mpc, "reserve_margin_usd")
        if reserve_risk > 0 or reserve_margin > 0:
            nonzero_reserve += 1

        geometry_ok = _reservation_geometry_matches(
            payload=payload,
            mpc=mpc,
            options=options,
            representatives=representatives,
            considered=considered,
        )
        if geometry_ok:
            geometry_verified += 1
        else:
            geometry_mismatch += 1

        if sets_match and geometry_ok:
            completely_bound += 1

    complete = origins > 0 and completely_bound == origins
    blockers: list[str] = []
    if origins == 0:
        blockers.append("NO_FORWARD_T15_KNOWN_OPTION_ORIGIN_EPOCHS")
    if missing_policy > 0:
        blockers.append("T15_KNOWN_OPTION_ORIGIN_MISSING_POLICY_RECORD")
    if set_mismatch > 0:
        blockers.append("T15_MPC_CONSIDERED_OPTION_SET_MISMATCH")
    if geometry_mismatch > 0:
        blockers.append("T15_MPC_RESERVATION_GEOMETRY_MISMATCH")
    if in_horizon_count > 0 and nonzero_reserve == 0:
        blockers.append("T15_NO_NONZERO_RESERVE_FOR_IN_HORIZON_OPTIONS")
    blockers.extend(
        (
            "COUNTERFACTUAL_RESERVATION_CAUSAL_EFFECT_NOT_IDENTIFIED",
            "FRESH_OOS_OPTIONALITY_UTILITY_ANALYSIS_REQUIRED",
        )
    )

    return Phase20T15ReservationBinding(
        origin_epochs_with_known_options=origins,
        known_option_instances=known_count,
        in_horizon_option_instances=in_horizon_count,
        considered_option_instances=considered_count,
        representative_option_instances=representative_count,
        policy_bound_origin_epochs=policy_bound,
        geometry_verified_origin_epochs=geometry_verified,
        nonzero_reserve_origin_epochs=nonzero_reserve,
        completely_bound_origin_epochs=completely_bound,
        missing_policy_origin_epochs=missing_policy,
        considered_set_mismatch_epochs=set_mismatch,
        reserve_geometry_mismatch_epochs=geometry_mismatch,
        reservation_binding_complete=complete,
        future_materialization_used=False,
        outcome_magnitudes_read=False,
        counterfactual_reservation_effect_identified=False,
        blockers=tuple(blockers),
    )


def _reservation_geometry_matches(
    *,
    payload: dict[str, object],
    mpc: dict[str, object],
    options: tuple[_Option, ...],
    representatives: tuple[str, ...],
    considered: tuple[str, ...],
) -> bool:
    reserve_risk = _decimal_field(mpc, "reserve_stop_risk_usd")
    reserve_margin = _decimal_field(mpc, "reserve_margin_usd")
    headroom_risk = _decimal_field(payload, "hard_risk_headroom_usd")
    headroom_margin = _decimal_field(payload, "margin_headroom_usd")
    posture = mpc.get("posture")
    if not isinstance(posture, str):
        return False

    if posture in _FULL_RESERVE_POSTURES:
        return (
            reserve_risk == headroom_risk
            and reserve_margin == headroom_margin
        )
    if not considered:
        return reserve_risk == 0 and reserve_margin == 0
    if not representatives:
        return False

    by_id = {item.opportunity_id: item for item in options}
    try:
        reps = tuple(by_id[item] for item in representatives)
    except KeyError:
        return False
    expected_risk = min(
        headroom_risk,
        max(item.minimum_stop_risk_usd for item in reps),
    )
    expected_margin = min(
        headroom_margin,
        max(item.minimum_margin_usd for item in reps),
    )
    steps = tuple(item.decision_step for item in reps)
    considered_steps = {
        by_id[item].decision_step
        for item in considered
        if item in by_id
    }
    return (
        len(steps) == len(set(steps))
        and set(steps) == considered_steps
        and reserve_risk == expected_risk
        and reserve_margin == expected_margin
    )


def _options(payload: dict[str, object]) -> tuple[_Option, ...]:
    rows = payload.get("known_options")
    if not isinstance(rows, list):
        raise CiboCapitalManagementError(
            "Phase20 T15 binding known_options must be list"
        )
    result: list[_Option] = []
    ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise CiboCapitalManagementError(
                "Phase20 T15 binding option row must be object"
            )
        option = row.get("option")
        if not isinstance(option, dict):
            raise CiboCapitalManagementError(
                "Phase20 T15 binding option payload must be object"
            )
        option_id = option.get("opportunity_id")
        if not isinstance(option_id, str) or not option_id:
            raise CiboCapitalManagementError(
                "Phase20 T15 binding option id is required"
            )
        if option_id in ids:
            raise CiboCapitalManagementError(
                "Phase20 T15 binding option ids must be unique"
            )
        ids.add(option_id)
        result.append(
            _Option(
                opportunity_id=option_id,
                decision_step=_int_field(option, "decision_step"),
                minimum_stop_risk_usd=_decimal_field(
                    option,
                    "minimum_stop_risk_usd",
                ),
                minimum_margin_usd=_decimal_field(
                    option,
                    "minimum_margin_usd",
                ),
            )
        )
    return tuple(result)


def _verify_policy_sha(expected: str, canonical_json: str) -> None:
    actual = "sha256:" + hashlib.sha256(canonical_json.encode()).hexdigest()
    if actual != expected:
        raise CiboCapitalManagementError(
            "Phase20 T15 policy record SHA does not match canonical JSON"
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
    return _json_object(
        decision.canonical_payload_json,
        "Phase20 T15 decision payload",
    )


def _json_object(value: str, name: str) -> dict[str, object]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(f"{name} invalid JSON") from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(f"{name} must be object")
    return payload


def _string_list(
    payload: dict[str, object],
    key: str,
) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise CiboCapitalManagementError(
            f"Phase20 T15 {key} must be non-empty string list"
        )
    result = tuple(value)
    if len(result) != len(set(result)):
        raise CiboCapitalManagementError(
            f"Phase20 T15 {key} must contain unique ids"
        )
    return result


def _decimal_field(
    payload: dict[str, object],
    key: str,
) -> Decimal:
    raw = payload.get(key)
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError) as error:
        raise CiboCapitalManagementError(
            f"Phase20 T15 {key} must be Decimal-compatible"
        ) from error
    if not value.is_finite() or value < 0:
        raise CiboCapitalManagementError(
            f"Phase20 T15 {key} must be finite non-negative"
        )
    return value


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


def _positive_int_field(payload: dict[str, object], key: str) -> int:
    value = _int_field(payload, key)
    if value <= 0:
        raise CiboCapitalManagementError(
            f"Phase20 T15 {key} must be positive"
        )
    return value
