"""Shadow classification of behavior-lab cases for CIBO CMA Phase 7."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_cma_behavior_binding import (
    economic_floor_from_behavior_case,
)
from qore.infrastructure.ctrader_demo_live_behavior_lab import LiveBehaviorCaseReport


class CmaShadowFloorStatus(StrEnum):
    BASE_RECOVERED = "BASE_RECOVERED"
    BASE_NOT_RECOVERED = "BASE_NOT_RECOVERED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True, slots=True)
class CmaShadowFloorObservation:
    case_id: str
    trader: str
    status: CmaShadowFloorStatus
    net_economic_floor_usd: Decimal | None
    base_capital_at_risk_usd: Decimal | None
    self_financing_capacity_usd: Decimal | None
    reason: str


def classify_behavior_case(
    report: LiveBehaviorCaseReport,
) -> CmaShadowFloorObservation:
    """Classify historical evidence without granting runtime capital authority."""

    trader = report.trader or "UNKNOWN"
    closed_settled = "CTRADER_DEMO_EXIT_SETTLEMENT" in report.settlement_events
    if not closed_settled:
        return CmaShadowFloorObservation(
            case_id=report.case_id,
            trader=trader,
            status=CmaShadowFloorStatus.INSUFFICIENT_EVIDENCE,
            net_economic_floor_usd=None,
            base_capital_at_risk_usd=None,
            self_financing_capacity_usd=None,
            reason=(
                "open/non-final case lacks authoritative real-time reconciliation; "
                "historical estimates remain observational"
            ),
        )

    result = economic_floor_from_behavior_case(
        report,
        position_open=False,
        broker_position_reconciled=True,
        protection_reconciled=True,
        mutation_outcome_unknown=False,
    )
    if not result.evidence_sufficient:
        return CmaShadowFloorObservation(
            case_id=report.case_id,
            trader=trader,
            status=CmaShadowFloorStatus.INSUFFICIENT_EVIDENCE,
            net_economic_floor_usd=None,
            base_capital_at_risk_usd=None,
            self_financing_capacity_usd=None,
            reason=result.reason,
        )

    if result.base_recovered:
        status = CmaShadowFloorStatus.BASE_RECOVERED
    else:
        status = CmaShadowFloorStatus.BASE_NOT_RECOVERED
    return CmaShadowFloorObservation(
        case_id=report.case_id,
        trader=trader,
        status=status,
        net_economic_floor_usd=result.net_economic_floor_usd,
        base_capital_at_risk_usd=result.base_capital_at_risk_usd,
        self_financing_capacity_usd=result.proven_self_financing_capacity_usd,
        reason=result.reason,
    )
