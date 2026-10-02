"""Assemble Phase22 V4 lane payloads after the durable Git claim."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_consumption_ledger import (
    Phase22ExecutionConsumptionReceipt,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    CANONICAL_PHASE22_TRADER_IDS,
)
from qore.infrastructure.cibo_phase22_v4_execution_manifest import (
    build_phase22_v4_execution_manifest,
)
from qore.infrastructure.cibo_phase22_v4_fresh_batch import (
    Phase22V4FreshOpportunityBatch,
    build_phase22_v4_fresh_batch,
)
from qore.infrastructure.cibo_phase22_v4_fresh_evidence import (
    TURTLE_SURFACE,
    native_trader_evidence,
    turtle_trader_evidence,
)
from qore.infrastructure.cibo_phase22_v4_governance import V4_CANDIDATE_ID


def assert_v4_claim(receipt: Phase22ExecutionConsumptionReceipt) -> None:
    manifest = build_phase22_v4_execution_manifest()
    if (
        not receipt.claim_committed
        or receipt.outcomes_emitted
        or receipt.candidate_id != V4_CANDIDATE_ID
        or receipt.execution_manifest_sha256 != manifest.fingerprint()
    ):
        raise CiboCapitalManagementError("V4 durable claim state invalid")


def assemble_phase22_v4_fresh_batch(
    *,
    vt08_payload: Mapping[str, object],
    turtle_rows: Mapping[str, Sequence[Mapping[str, object]]],
    vt31_payload: Mapping[str, object],
    lane_artifact_sha256s: Mapping[str, str],
    consumption_claim: Phase22ExecutionConsumptionReceipt,
) -> Phase22V4FreshOpportunityBatch:
    assert_v4_claim(consumption_claim)
    expected = set(CANONICAL_PHASE22_TRADER_IDS)
    if set(lane_artifact_sha256s) != expected:
        raise CiboCapitalManagementError("V4 lane artifact surface drift")
    turtle_ids = {item[0] for item in TURTLE_SURFACE}
    if set(turtle_rows) != turtle_ids:
        raise CiboCapitalManagementError("V4 Turtle surface drift")

    by_id = {
        "VT08_FOREX": native_trader_evidence(
            trader_id="VT08_FOREX",
            payload=vt08_payload,
            lane_artifact_sha256=lane_artifact_sha256s["VT08_FOREX"],
        ),
        "VT31_NAS100": native_trader_evidence(
            trader_id="VT31_NAS100",
            payload=vt31_payload,
            lane_artifact_sha256=lane_artifact_sha256s["VT31_NAS100"],
        ),
    }
    for trader_id, _symbol in TURTLE_SURFACE:
        by_id[trader_id] = turtle_trader_evidence(
            trader_id=trader_id,
            rows=turtle_rows[trader_id],
            lane_artifact_sha256=lane_artifact_sha256s[trader_id],
        )
    traders = tuple(by_id[item] for item in CANONICAL_PHASE22_TRADER_IDS)
    return build_phase22_v4_fresh_batch(traders)
