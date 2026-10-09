"""CIBO Soberano Native MAX -> four economic motors -> physical QDLE (P0 SHADOW).

The upstream CIBO instruction explicitly owns lane, direction, geometry and
working capital. Native MAX's causal sensor observation can tighten its risk
request, but NEVER substitutes for a sovereign instruction, signed treasury,
broker specification or provider risk authority. No orders, deals, fills,
OPEN fees or settlements are created here.

Single source of truth for the Native MAX cognitive cap used by both the
universal 3368 historical manager and the direct sovereign QDLE route.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, InvalidOperation

from qore.infrastructure.cibo_p0_native_cognitive_management import (
    native_sensor_management_plan,
)
from qore.infrastructure.cibo_native_mode_authority import SOURCE as NATIVE_RUNTIME_PRODUCER
from qore.infrastructure.cibo_sovereign_integration import (
    PreparedShadowDecision,
    ShadowFundingOutcome,
    prepare_shadow_economic_decision,
    record_shadow_qdle_result,
)
from qore.infrastructure.cibo_trade_ops_director import TradeOpsState
from qore.infrastructure.cibo_four_motor_policy import FourMotorObservation
from qore.infrastructure.qdle_cibo_authority import CiboEconomicInstruction
from qore.infrastructure.qore_dynamic_lot_engine import QDLE, QDLEIntent

_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
_MAX_NAV_FRACTION = Decimal("0.05")


class CiboSovereignQdleBridgeError(ValueError):
    """Untrusted/mismatched cognitive or economic inputs. No silent signal drop."""


def _risk_fraction(plan: dict) -> Decimal:
    if (not isinstance(plan, dict)
        or plan.get("native_disposition_used_for_policy") is not False
        or plan.get("producer") not in (
            NATIVE_RUNTIME_PRODUCER,
            "P0_DETERMINISTIC_SENSOR_DERIVED_RESEARCH_ADAPTER_NOT_NATIVE_BROKER_AUTHORIZATION",
        )):
        raise CiboSovereignQdleBridgeError("Native MAX causal research plan required")
    try:
        fraction = Decimal(str(plan["requested_risk_fraction_of_current_qore_nav"]))
    except (InvalidOperation, KeyError, TypeError, ValueError) as exc:
        raise CiboSovereignQdleBridgeError("invalid Native MAX risk fraction") from exc
    if not fraction.is_finite() or not Decimal(0) < fraction <= _MAX_NAV_FRACTION:
        raise CiboSovereignQdleBridgeError("Native MAX risk fraction violates QORE 5pct")
    return fraction


def apply_native_qdle_risk_cap(
    *, intent: QDLEIntent, qore_nav_usd: Decimal, native_plan: dict,
) -> QDLEIntent:
    """Couple Native MAX to executable physical lot calculations, not labels.

    Never increase a pre-existing CIBO/four-motor/source capacity; QDLE still
    enforces its entire physical risk+fees+margin+broker grid.
    """
    if not isinstance(intent, QDLEIntent):
        raise CiboSovereignQdleBridgeError("typed QDLE intent required")
    if (not isinstance(qore_nav_usd, Decimal) or not qore_nav_usd.is_finite()
        or qore_nav_usd < 0):
        raise CiboSovereignQdleBridgeError("reconciled nonnegative QORE NAV required")
    maximum = qore_nav_usd * _risk_fraction(native_plan)
    return replace(
        intent,
        requested_risk_usd=min(intent.requested_risk_usd, maximum),
        sizing_cap_usd=min(intent.sizing_cap_usd, maximum),
        cibo_compound_cap_usd=min(intent.cibo_compound_cap_usd, maximum),
    )


def bind_native_max_receipt(
    *, native_receipt: dict, cibo: CiboEconomicInstruction,
    observation: FourMotorObservation,
) -> dict:
    """Authenticate *structural/causal* constraints of a predecision research row.

    A digest on this row is provenance, not proof of a signed Native
    or LIVE CIBO order. Caller MUST have externally checked source sealing.
    """
    if not isinstance(native_receipt, dict):
        raise CiboSovereignQdleBridgeError("Native MAX receipt required")
    if (native_receipt.get("signal_fingerprint") != cibo.signal_id
        or native_receipt.get("trader_id") != cibo.trader_id
        or cibo.signal_id != observation.request_id
        or cibo.trader_id != observation.trader_id):
        raise CiboSovereignQdleBridgeError("Native MAX CIBO/Trader identity mismatch")
    if (native_receipt.get("native_maximum_intelligence") is not True
        or native_receipt.get("full_semantics_consumed") is not True
        or native_receipt.get("outcome_used_for_predecision") is not False
        or native_receipt.get("external_ai_call_count") != 0
        or not isinstance(native_receipt.get("semantic_digest"), str)
        or not _SHA.fullmatch(native_receipt["semantic_digest"])):
        raise CiboSovereignQdleBridgeError("Native MAX causal and digest provenance missing")
    try:
        decided_at = datetime.fromisoformat(native_receipt["decided_at"])
    except (TypeError, KeyError, ValueError) as exc:
        raise CiboSovereignQdleBridgeError("Native MAX chronology missing") from exc
    if (decided_at.tzinfo is None or decided_at.utcoffset() is None
        or decided_at > observation.observed_at
        or decided_at > cibo.issued_at):
        raise CiboSovereignQdleBridgeError("future or naive cognitive decision forbidden")
    return native_sensor_management_plan(native_receipt)


@dataclass(frozen=True, slots=True)
class SovereignNativeQdleShadowOutcome:
    """CIBO-owned decision + QDLE physical reservation; NOT a broker fill."""

    prepared: PreparedShadowDecision
    funding: ShadowFundingOutcome
    native_mode: str
    native_semantic_digest: str
    native_risk_request_usd: Decimal
    native_exit_policy_shadow: dict
    cognitive_risk_reaches_physical_qdle: bool = True
    real_mt5_fill_proven: bool = False
    live_authorized: bool = False


def administer_native_sovereign_qdle_shadow(
    *, state: TradeOpsState, native_receipt: dict,
    cibo: CiboEconomicInstruction, observation: FourMotorObservation,
    qdle: QDLE, event_id: str, at: datetime,
    broker_min_lot: Decimal, broker_lot_step: Decimal,
) -> SovereignNativeQdleShadowOutcome:
    """Execute CIBO -> 4 motors -> QDLE -> CIBO receipt, strictly paper.

    CIBO supplies economic instruction/lane. Native cognition modulates
    requested risk. QDLE is the sole lot/margin/roundtrip-cost calculator.
    No alternate broker-order path or synthetic settlement is permitted.
    """
    if not isinstance(qdle, QDLE):
        raise CiboSovereignQdleBridgeError("physical QDLE engine required")
    if not isinstance(cibo, CiboEconomicInstruction) or not isinstance(
        observation, FourMotorObservation
    ):
        raise CiboSovereignQdleBridgeError("sovereign CIBO instruction and four motor evidence required")
    # Legacy Trader CONTROL settlements are never sovereign managed cashflows.
    # Do not let their losses activate Compound's three-settlement haircut.
    if any(flow.event_id.startswith((
        "TRADER_CONTROL_ONLY:", "REPLAY_SETTLED:", "REPLAY_PRIOR_CASHBOOK:"
    )) for flow in observation.reconciled_cashflows):
        raise CiboSovereignQdleBridgeError(
            "Trader CONTROL cashflow forbidden in CIBO sovereign managed NAV"
        )
    plan = bind_native_max_receipt(
        native_receipt=native_receipt, cibo=cibo, observation=observation,
    )
    fraction = _risk_fraction(plan)
    # QORE NAV belongs to the economic epoch, not an old Trader control result.
    requested = min(cibo.authorized_all_in_risk_usd, observation.qore_nav_usd * fraction)
    bounded_cibo = replace(cibo, authorized_all_in_risk_usd=requested)
    prepared = prepare_shadow_economic_decision(
        state=state, cibo=bounded_cibo, observation=observation,
    )
    prepared = replace(prepared, intent=apply_native_qdle_risk_cap(
        intent=prepared.intent, qore_nav_usd=observation.qore_nav_usd,
        native_plan=plan,
    ))
    if not isinstance(at, datetime) or at.tzinfo is None or at.utcoffset() is None:
        raise CiboSovereignQdleBridgeError("timezone-aware QDLE epoch required")
    if at != observation.observed_at:
        raise CiboSovereignQdleBridgeError("QDLE valuation epoch must match CIBO observation")
    # All validation completed before the only side-effect: QDLE reservation.
    quote = qdle.reserve_for_trader(prepared.intent, now=at)
    outcome = record_shadow_qdle_result(
        prepared=prepared, result=quote,
        broker_min_lot=broker_min_lot, broker_lot_step=broker_lot_step,
        event_id=event_id, event_at=at,
    )
    return SovereignNativeQdleShadowOutcome(
        prepared=prepared, funding=outcome,
        native_mode=str(plan["mode"]),
        native_semantic_digest=native_receipt["semantic_digest"],
        native_risk_request_usd=requested,
        native_exit_policy_shadow=dict(plan["exit_policy_SHADOW"]),
    )
