"""cTrader DEMO observer for authoritative T20 capital-release evidence.

The observer is strictly read-only. It converts already-recorded Risk,
execution, settlement and broker-deal facts into T20 release evidence. Missing
or ambiguous lifecycle facts fail closed; a position close alone is never
accepted as proof of released capacity.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from qore.infrastructure.cibo_ce2i_phase20_outcome_reconciliation import (
    Phase20ExecutedRiskEvidence,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardOutcomeSeal,
)
from qore.infrastructure.cibo_cma_settlement_ledger import CmaSettlementState
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_t20_capital_release_evidence import (
    T20CapitalAuthorizationEvidence,
    T20CapitalReleaseEvidence,
    T20CapitalReleaseSlice,
    build_t20_capital_release_evidence,
)
from qore.infrastructure.ctrader_demo_free_position_service import DemoDeal
from qore.infrastructure.ctrader_demo_trade_registry import (
    DemoTradeRegistryEntry,
)


def build_ctrader_demo_t20_release_evidence(
    *,
    entry: DemoTradeRegistryEntry,
    executed_risk: Phase20ExecutedRiskEvidence,
    outcome: Phase20ForwardOutcomeSeal,
    settlement: CmaSettlementState,
    broker_deals: tuple[DemoDeal, ...],
    broker_open_position_ids: frozenset[int],
    risk_reservation_released: bool,
) -> T20CapitalReleaseEvidence:
    """Build one T20 receipt only from a fully reconciled provider lifecycle."""

    if not isinstance(entry, DemoTradeRegistryEntry):
        raise CiboCompoundCapitalError(
            "T20 DEMO observer requires canonical registry entry"
        )
    if not isinstance(executed_risk, Phase20ExecutedRiskEvidence):
        raise CiboCompoundCapitalError(
            "T20 DEMO observer requires executed-risk evidence"
        )
    if not isinstance(outcome, Phase20ForwardOutcomeSeal):
        raise CiboCompoundCapitalError(
            "T20 DEMO observer requires forward outcome seal"
        )
    if not isinstance(settlement, CmaSettlementState):
        raise CiboCompoundCapitalError(
            "T20 DEMO observer requires settlement state"
        )
    if type(risk_reservation_released) is not bool:
        raise CiboCompoundCapitalError(
            "T20 DEMO observer Risk release flag must be bool"
        )
    if not risk_reservation_released:
        raise CiboCompoundCapitalError(
            "T20 DEMO observer requires reconciled QORE Risk shadow release"
        )
    if entry.position_id is None or entry.position_id <= 0:
        raise CiboCompoundCapitalError(
            "T20 DEMO observer requires bound broker position"
        )
    if entry.position_id in broker_open_position_ids:
        raise CiboCompoundCapitalError(
            "T20 DEMO observer refuses still-open broker position"
        )
    if entry.closed_at is None:
        raise CiboCompoundCapitalError(
            "T20 DEMO observer requires authoritative broker close timestamp"
        )
    if not settlement.position_closed:
        raise CiboCompoundCapitalError(
            "T20 DEMO observer requires terminal CMA settlement"
        )
    if (
        executed_risk.signal_fingerprint != entry.signal_fingerprint
        or executed_risk.position_id != entry.position_id
        or outcome.signal_fingerprint != entry.signal_fingerprint
        or outcome.position_id != entry.position_id
        or settlement.signal_fingerprint != entry.signal_fingerprint
        or settlement.position_id != entry.position_id
    ):
        raise CiboCompoundCapitalError(
            "T20 DEMO observer lifecycle identity drift"
        )

    required = {
        "requested_at": entry.requested_at,
        "margin_per_volume": entry.margin_per_volume,
        "risk_authorization_id": entry.risk_authorization_id,
        "risk_authorization_fingerprint": (
            entry.risk_authorization_fingerprint
        ),
        "risk_decision": entry.risk_decision,
        "risk_authorized_at": entry.risk_authorized_at,
        "risk_authorized_margin_usd": entry.risk_authorized_margin_usd,
        "risk_authorized_stop_risk_usd": (
            entry.risk_authorized_stop_risk_usd
        ),
        "authorized_source_volume": entry.authorized_source_volume,
        "source_contract_size_units": entry.source_contract_size_units,
    }
    missing = tuple(
        name for name, value in required.items() if value is None
    )
    if missing:
        raise CiboCompoundCapitalError(
            "T20 DEMO observer registry lineage incomplete: "
            + ",".join(missing)
        )
    if entry.risk_decision not in {"ALLOW", "REDUCE"}:
        raise CiboCompoundCapitalError(
            "T20 DEMO observer requires ALLOW/REDUCE Risk disposition"
        )
    if executed_risk.capital_deployed_at is None:
        raise CiboCompoundCapitalError(
            "T20 DEMO observer requires exact capital deployment timestamp"
        )

    try:
        requested_at = datetime.fromisoformat(str(entry.requested_at))
        risk_authorized_at = datetime.fromisoformat(
            str(entry.risk_authorized_at)
        )
        closed_at = datetime.fromisoformat(entry.closed_at)
        requested_volume = Decimal(entry.requested_volume)
        margin_per_volume = Decimal(str(entry.margin_per_volume))
        requested_stop_risk = Decimal(entry.requested_stop_risk)
        authorized_volume = Decimal(str(entry.authorized_source_volume))
        risk_authorized_margin = Decimal(
            str(entry.risk_authorized_margin_usd)
        )
        risk_authorized_stop = Decimal(
            str(entry.risk_authorized_stop_risk_usd)
        )
        source_contract_size = Decimal(
            str(entry.source_contract_size_units)
        )
    except (InvalidOperation, ValueError) as error:
        raise CiboCompoundCapitalError(
            "T20 DEMO observer registry economics invalid"
        ) from error

    expected_close_units = (
        executed_risk.filled_source_volume * source_contract_size
    )
    if expected_close_units <= 0:
        raise CiboCompoundCapitalError(
            "T20 DEMO observer executed quantity must be positive"
        )

    settlement_ids = tuple(item.deal_id for item in settlement.records)
    closing = tuple(
        sorted(
            (
                item
                for item in broker_deals
                if (
                    item.position_id == entry.position_id
                    and item.is_closing
                    and item.deal_id in settlement_ids
                )
            ),
            key=lambda item: (item.executed_at, item.deal_id),
        )
    )
    if not closing:
        raise CiboCompoundCapitalError(
            "T20 DEMO observer requires provider closing deals"
        )
    if len({item.deal_id for item in closing}) != len(closing):
        raise CiboCompoundCapitalError(
            "T20 DEMO observer duplicate provider closing deal"
        )
    total_closed_units = sum(
        (item.filled_units for item in closing),
        Decimal(0),
    )
    if total_closed_units != expected_close_units:
        raise CiboCompoundCapitalError(
            "T20 DEMO observer closing volume does not reconcile to fill"
        )
    if closing[-1].executed_at != closed_at:
        raise CiboCompoundCapitalError(
            "T20 DEMO observer terminal deal/registry timestamp drift"
        )
    if (
        outcome.capital_released_at is None
        or outcome.capital_released_at != closed_at
    ):
        raise CiboCompoundCapitalError(
            "T20 DEMO observer outcome release timestamp drift"
        )

    requested_margin = requested_volume * margin_per_volume
    execution_margin = (
        risk_authorized_margin
        * executed_risk.filled_source_volume
        / authorized_volume
    )
    authorization = T20CapitalAuthorizationEvidence(
        evidence_id=(
            "t20-auth:"
            f"{entry.signal_fingerprint}:{entry.position_id}"
        ),
        decision_evidence_sha256=executed_risk.decision_evidence_sha256,
        signal_fingerprint=entry.signal_fingerprint,
        position_id=entry.position_id,
        requested_at=requested_at,
        requested_margin_usd=requested_margin,
        requested_stop_risk_usd=requested_stop_risk,
        risk_decision_id=str(entry.risk_authorization_id),
        risk_disposition=str(entry.risk_decision),
        risk_authorized_at=risk_authorized_at,
        risk_authorized_margin_usd=risk_authorized_margin,
        risk_authorized_stop_risk_usd=risk_authorized_stop,
        execution_evidence_id=executed_risk.evidence_id,
        execution_realized_at=executed_risk.observed_at,
        execution_realized_margin_usd=execution_margin,
        execution_realized_stop_risk_usd=(
            executed_risk.executed_initial_stop_risk_usd
        ),
        capacity_deployed_at=executed_risk.capital_deployed_at,
        source_refs=(
            f"risk:{entry.risk_authorization_id}",
            f"execution:{executed_risk.evidence_id}",
            f"registry:{entry.client_order_id}",
        ),
    )

    releases: list[T20CapitalReleaseSlice] = []
    allocated_stop = Decimal(0)
    allocated_margin = Decimal(0)
    for index, deal in enumerate(closing):
        terminal = index == len(closing) - 1
        if terminal:
            released_stop = (
                executed_risk.executed_initial_stop_risk_usd
                - allocated_stop
            )
            released_margin = execution_margin - allocated_margin
        else:
            fraction = deal.filled_units / expected_close_units
            released_stop = (
                executed_risk.executed_initial_stop_risk_usd
                * fraction
            )
            released_margin = execution_margin * fraction
            allocated_stop += released_stop
            allocated_margin += released_margin
        releases.append(
            T20CapitalReleaseSlice(
                settlement_deal_id=deal.deal_id,
                released_at=deal.executed_at,
                released_stop_risk_capacity_usd=released_stop,
                released_margin_capacity_usd=released_margin,
                source_ref=f"ctrader-demo-deal:{deal.deal_id}",
                terminal=terminal,
            )
        )

    evidence_id = (
        "t20-release:"
        f"{entry.signal_fingerprint}:{entry.position_id}"
    )
    source_refs = tuple(
        dict.fromkeys(
            (
                f"registry:{entry.client_order_id}",
                f"risk:{entry.risk_authorization_id}",
                f"risk-fingerprint:{entry.risk_authorization_fingerprint}",
                f"execution:{executed_risk.evidence_id}",
                f"outcome:{outcome.evidence_id}",
                *(
                    f"settlement-deal:{item.deal_id}"
                    for item in closing
                ),
            )
        )
    )
    return build_t20_capital_release_evidence(
        evidence_id=evidence_id,
        authorization=authorization,
        outcome=outcome,
        settlement=settlement,
        releases=tuple(releases),
        observed_at=outcome.observed_at,
        source_refs=source_refs,
    )
