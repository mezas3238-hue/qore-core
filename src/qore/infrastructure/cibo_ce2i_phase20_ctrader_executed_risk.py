"""cTrader DEMO adapter for exact Phase20 executed structural risk.

The adapter accepts only a MATCHED fill reconciliation for one canonical CIBO
request. It converts provider exposure units back to source volume and adjusts
the frozen stop-risk-per-volume by the actual weighted fill-to-stop distance.

Partial/diverged/missing fills are intentionally ineligible for Phase20D
economic qualification.
"""

from __future__ import annotations

import json
from decimal import Decimal
from hashlib import sha256

from qore.infrastructure.account_wide_risk import CiboRiskRequest
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_outcome_reconciliation import (
    Phase20ExecutedRiskEvidence,
)
from qore.infrastructure.ctrader_demo_allocation_only import (
    CTraderDemoBrokerContract,
)
from qore.infrastructure.ctrader_demo_execution_contracts import (
    CTraderDemoFillObservation,
    CTraderDemoFillReconciliation,
    CTraderDemoFillReconciliationStatus,
)


def build_ctrader_phase20_executed_risk(
    *,
    decision_evidence_sha256: str,
    position_id: int,
    authorized_source_volume: Decimal,
    request: CiboRiskRequest,
    contract: CTraderDemoBrokerContract,
    fills: tuple[CTraderDemoFillObservation, ...],
    reconciliation: CTraderDemoFillReconciliation,
) -> Phase20ExecutedRiskEvidence:
    """Build a reconciled structural-risk denominator from actual fills."""

    if (
        not isinstance(position_id, int)
        or isinstance(position_id, bool)
        or position_id <= 0
    ):
        raise CiboCapitalManagementError(
            "Phase20D executed risk requires reconciled positive position_id"
        )
    if (
        not isinstance(authorized_source_volume, Decimal)
        or not authorized_source_volume.is_finite()
        or authorized_source_volume <= 0
    ):
        raise CiboCapitalManagementError(
            "Phase20D executed risk requires positive authorized source volume"
        )
    if not isinstance(request, CiboRiskRequest):
        raise CiboCapitalManagementError(
            "Phase20D executed risk requires canonical CiboRiskRequest"
        )
    if not isinstance(contract, CTraderDemoBrokerContract):
        raise CiboCapitalManagementError(
            "Phase20D executed risk requires cTrader broker contract"
        )
    if not isinstance(reconciliation, CTraderDemoFillReconciliation):
        raise CiboCapitalManagementError(
            "Phase20D executed risk requires fill reconciliation"
        )
    if reconciliation.status is not CTraderDemoFillReconciliationStatus.MATCHED:
        raise CiboCapitalManagementError(
            "Phase20D executed risk requires MATCHED fill reconciliation"
        )
    if not fills:
        raise CiboCapitalManagementError(
            "Phase20D executed risk requires provider fills"
        )
    if contract.qore_symbol != request.qore_symbol:
        raise CiboCapitalManagementError(
            "Phase20D executed risk broker/request symbol mismatch"
        )
    if authorized_source_volume > request.requested_volume:
        raise CiboCapitalManagementError(
            "Phase20D authorized source volume cannot exceed CIBO request"
        )
    if authorized_source_volume < request.minimum_volume:
        raise CiboCapitalManagementError(
            "Phase20D authorized source volume cannot be below provider minimum"
        )
    step_units = authorized_source_volume / request.volume_step
    if step_units != step_units.to_integral_value():
        raise CiboCapitalManagementError(
            "Phase20D authorized source volume must align to volume step"
        )

    expected_provider_quantity = (
        authorized_source_volume * contract.source_contract_size_units
    )
    if reconciliation.requested_quantity != expected_provider_quantity:
        raise CiboCapitalManagementError(
            "Phase20D fill reconciliation requested quantity drift"
        )
    if reconciliation.filled_quantity != expected_provider_quantity:
        raise CiboCapitalManagementError(
            "Phase20D fill reconciliation must fully match requested quantity"
        )

    receipt_ids = {item.receipt_id for item in fills}
    idempotency_keys = {item.idempotency_key for item in fills}
    provider_refs = {item.provider_order_ref for item in fills}
    instruments = {item.instrument.value for item in fills}
    sides = {item.side.value for item in fills}
    if any(
        len(values) != 1
        for values in (
            receipt_ids,
            idempotency_keys,
            provider_refs,
            instruments,
            sides,
        )
    ):
        raise CiboCapitalManagementError(
            "Phase20D fills do not represent one execution identity"
        )
    if instruments != {request.qore_symbol}:
        raise CiboCapitalManagementError(
            "Phase20D fill instrument does not match CIBO request"
        )
    expected_side = "BUY" if request.side == "long" else "SELL"
    if {item.upper() for item in sides} != {expected_side}:
        raise CiboCapitalManagementError(
            "Phase20D fill side does not match CIBO request"
        )

    ordered = tuple(
        sorted(
            fills,
            key=lambda item: (
                item.provider_timestamp,
                item.fill_ref,
            ),
        )
    )
    if ordered[-1].cumulative_quantity != reconciliation.filled_quantity:
        raise CiboCapitalManagementError(
            "Phase20D terminal fill cumulative quantity mismatch"
        )
    if not ordered[-1].is_complete:
        raise CiboCapitalManagementError(
            "Phase20D terminal fill must be marked complete"
        )
    cumulative = sum(
        (item.fill_quantity for item in ordered),
        Decimal(0),
    )
    if cumulative != reconciliation.filled_quantity:
        raise CiboCapitalManagementError(
            "Phase20D fill quantities do not reconcile to terminal quantity"
        )

    weighted_price = (
        sum(
            (
                item.fill_price * item.fill_quantity
                for item in ordered
            ),
            Decimal(0),
        )
        / cumulative
    )
    intended_distance = abs(request.intended_entry - request.stop_loss)
    executed_distance = abs(weighted_price - request.stop_loss)
    if intended_distance <= 0 or executed_distance <= 0:
        raise CiboCapitalManagementError(
            "Phase20D executed risk has invalid stop distance"
        )
    if request.side == "long" and weighted_price <= request.stop_loss:
        raise CiboCapitalManagementError(
            "Phase20D long fill crossed structural stop"
        )
    if request.side == "short" and weighted_price >= request.stop_loss:
        raise CiboCapitalManagementError(
            "Phase20D short fill crossed structural stop"
        )

    filled_source_volume = (
        reconciliation.filled_quantity
        / contract.source_contract_size_units
    )
    executed_risk_per_volume = (
        request.stop_loss_per_volume
        * executed_distance
        / intended_distance
    )
    executed_initial_risk = (
        filled_source_volume * executed_risk_per_volume
    )
    if executed_initial_risk <= 0 or not executed_initial_risk.is_finite():
        raise CiboCapitalManagementError(
            "Phase20D executed initial risk is invalid"
        )

    payload = {
        "decision_evidence_sha256": decision_evidence_sha256,
        "signal_fingerprint": request.signal_fingerprint,
        "request_id": request.request_id,
        "qore_symbol": request.qore_symbol,
        "provider_order_ref": ordered[-1].provider_order_ref,
        "fill_refs": [item.fill_ref for item in ordered],
        "weighted_fill_price": format(weighted_price, "f"),
        "filled_provider_quantity": format(
            reconciliation.filled_quantity,
            "f",
        ),
        "authorized_source_volume": format(
            authorized_source_volume,
            "f",
        ),
        "filled_source_volume": format(filled_source_volume, "f"),
        "executed_initial_stop_risk_usd": format(
            executed_initial_risk,
            "f",
        ),
        "capital_deployed_at": ordered[-1].provider_timestamp.isoformat(),
        "reconciled_at": reconciliation.reconciled_at.isoformat(),
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return Phase20ExecutedRiskEvidence(
        evidence_id=f"phase20d-executed-risk:{sha256(raw).hexdigest()}",
        decision_evidence_sha256=decision_evidence_sha256,
        signal_fingerprint=request.signal_fingerprint,
        qore_symbol=request.qore_symbol,
        provider_order_ref=ordered[-1].provider_order_ref,
        side=request.side,
        position_id=position_id,
        authorized_source_volume=authorized_source_volume,
        filled_source_volume=filled_source_volume,
        weighted_fill_price=weighted_price,
        intended_entry_price=request.intended_entry,
        structural_stop_price=request.stop_loss,
        stop_risk_per_volume_at_intended_entry_usd=(
            request.stop_loss_per_volume
        ),
        executed_initial_stop_risk_usd=executed_initial_risk,
        observed_at=reconciliation.reconciled_at,
        fill_evidence_refs=tuple(item.fill_ref for item in ordered),
        fill_reconciled=True,
        mutation_outcome_known=True,
        capital_deployed_at=ordered[-1].provider_timestamp,
    )
