from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from qore.governance.mission04_closure import (
    Mission04ClosureEvidenceRef,
    Mission04ClosureReadiness,
    Mission04ClosureReadinessStatus,
    Mission04ClosureValidationError,
    Mission04Delivery,
    Mission04DeliveryClosureRecord,
    build_mission04_closure_readiness,
)
from qore.kernel.result import Failure, Success


def _completed_record(delivery: Mission04Delivery) -> Mission04DeliveryClosureRecord:
    return Mission04DeliveryClosureRecord(
        delivery=delivery,
        completed=True,
        evidence_refs=(
            Mission04ClosureEvidenceRef(f"github:mission04/{delivery.value}"),
        ),
    )


def _complete_records() -> tuple[Mission04DeliveryClosureRecord, ...]:
    return tuple(_completed_record(delivery) for delivery in Mission04Delivery)


def test_complete_delivery_matrix_is_ready_but_cannot_self_close_or_activate() -> None:
    result = build_mission04_closure_readiness(_complete_records())

    assert isinstance(result, Success)
    readiness = result.value
    assert readiness.status is Mission04ClosureReadinessStatus.READY
    assert readiness.closure_attempt_permitted
    assert readiness.missing_deliveries == ()
    assert readiness.blocker_codes == ()
    assert not readiness.mission_closed
    assert not readiness.external_control_plane_activation_authorized
    assert not readiness.production_authorized
    assert not readiness.mission03_operationally_closed
    assert not readiness.mission05_opened


def test_incomplete_sequential_prefix_is_blocked_with_deterministic_reasons() -> None:
    deliveries = tuple(Mission04Delivery)
    records = tuple(_completed_record(delivery) for delivery in deliveries[:8]) + tuple(
        Mission04DeliveryClosureRecord(delivery=delivery, completed=False)
        for delivery in deliveries[8:]
    )

    result = build_mission04_closure_readiness(records)

    assert isinstance(result, Success)
    readiness = result.value
    assert readiness.status is Mission04ClosureReadinessStatus.BLOCKED
    assert not readiness.closure_attempt_permitted
    assert readiness.missing_deliveries == deliveries[8:]
    assert readiness.blocker_codes == tuple(
        f"{delivery.value}.not-completed" for delivery in deliveries[8:]
    )


def test_gap_in_delivery_sequence_is_rejected_fail_closed() -> None:
    records = list(_complete_records())
    missing = Mission04Delivery.REQUEST_GUARD
    index = tuple(Mission04Delivery).index(missing)
    records[index] = Mission04DeliveryClosureRecord(delivery=missing, completed=False)

    with pytest.raises(Mission04ClosureValidationError):
        Mission04ClosureReadiness(tuple(records))


def test_builder_rejects_duplicate_or_incomplete_matrix() -> None:
    records = _complete_records()
    duplicate = records[:-1] + (records[0],)

    duplicate_result = build_mission04_closure_readiness(duplicate)
    incomplete_result = build_mission04_closure_readiness(records[:-1])

    assert isinstance(duplicate_result, Failure)
    assert isinstance(incomplete_result, Failure)


def test_completed_flag_is_strict_bool_and_evidence_binding_is_exact() -> None:
    delivery = Mission04Delivery.AUDIT_EVIDENCE
    with pytest.raises(Mission04ClosureValidationError):
        Mission04DeliveryClosureRecord(
            delivery=delivery,
            completed=cast(bool, 1),
            evidence_refs=(Mission04ClosureEvidenceRef("github:pr/163"),),
        )
    with pytest.raises(Mission04ClosureValidationError):
        Mission04DeliveryClosureRecord(delivery=delivery, completed=True)
    with pytest.raises(Mission04ClosureValidationError):
        Mission04DeliveryClosureRecord(
            delivery=delivery,
            completed=False,
            evidence_refs=(Mission04ClosureEvidenceRef("github:pr/163"),),
        )


def test_evidence_refs_are_secret_free_unique_and_deterministic() -> None:
    with pytest.raises(Mission04ClosureValidationError):
        Mission04ClosureEvidenceRef("github:token/private")
    with pytest.raises(Mission04ClosureValidationError):
        Mission04ClosureEvidenceRef("GitHub PR 163")

    ref_a = Mission04ClosureEvidenceRef("github:ci/544")
    ref_b = Mission04ClosureEvidenceRef("github:pr/163")
    record = Mission04DeliveryClosureRecord(
        delivery=Mission04Delivery.AUDIT_EVIDENCE,
        completed=True,
        evidence_refs=(ref_b, ref_a),
    )
    assert record.evidence_refs == (ref_a, ref_b)

    with pytest.raises(Mission04ClosureValidationError):
        Mission04DeliveryClosureRecord(
            delivery=Mission04Delivery.AUDIT_EVIDENCE,
            completed=True,
            evidence_refs=(ref_a, ref_a),
        )


def test_readiness_is_immutable_deterministic_and_public_payload_remains_closed() -> None:
    result = build_mission04_closure_readiness(_complete_records())
    assert isinstance(result, Success)
    readiness = result.value

    assert readiness.logical_values() == readiness.logical_values()
    payload = readiness.public_payload()
    assert payload["mission"] == "mission-04"
    assert payload["scope"] == "offline-provider-independent-control-plane"
    assert payload["readiness_status"] == "ready"
    assert payload["closure_attempt_permitted"] is True
    assert payload["mission_closed"] is False
    assert payload["external_control_plane_activation_authorized"] is False
    assert payload["production_authorized"] is False
    assert payload["mission03_operationally_closed"] is False
    assert payload["mission05_opened"] is False
    assert readiness.to_json() == readiness.to_json()
    rendered = readiness.to_json().lower()
    for forbidden in ("password", "bearer ", "client_secret", "token="):
        assert forbidden not in rendered

    with pytest.raises(FrozenInstanceError):
        readiness.__setattr__("deliveries", ())
