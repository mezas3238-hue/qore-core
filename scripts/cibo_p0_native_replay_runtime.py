"""Reconstruct genuine CF01-CF19 -> Native MAX episodes at causal PAPER epochs.

This does not validate historical fills or create MT5 authorization. It uses the
same predecision Trader envelope and CE2I semantics as the canonical MAX
preflight, but injects the current research-account cash and open risk state.
Previous native quote decisions/mode/stop/exit labels are never loaded here.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from cibo_single_account_native_max_intelligence_preflight import (
    _opportunity, _regime,
)
from qore.infrastructure.cibo_native_maximum_intelligence import (
    run_native_maximum_intelligence,
)
from qore.infrastructure.cibo_native_mode_authority import (
    issue_native_sovereign_mode_instruction,
)
from qore.infrastructure.cibo_sovereign_function_consultation import (
    consult_cibo_economic_faculties,
)


class NativeReplayReconstructionError(ValueError):
    pass


def reconstruct_native_max_at_epoch(
    *,
    original: dict, decision_at: datetime,
    qore_cash_usd: Decimal, peak_cash_usd: Decimal,
    open_stop_risk_usd: Decimal, broker_margin_held_usd: Decimal,
    open_positions: int, broker_cash_usd: Decimal,
) -> tuple[object, dict]:
    """Genuine Native MAX inference, not a historical Native mode receipt.

    A failed reconstruction must be counted as a cognitive failure and never
    replaced with the archived mode. The original Trader context must already
    be sealed predecision, since future outcome fields are forbidden by MAX.
    """
    if decision_at.tzinfo is None or decision_at.utcoffset() is None:
        raise NativeReplayReconstructionError("decision epoch must be aware")
    source_at = datetime.fromisoformat(original["market_decision_at"])
    if source_at > decision_at:
        raise NativeReplayReconstructionError("future Trader context at earlier replay epoch")
    if any(not x.is_finite() or x < 0 for x in (
        qore_cash_usd, peak_cash_usd, open_stop_risk_usd,
        broker_margin_held_usd, broker_cash_usd,
    )):
        raise NativeReplayReconstructionError("invalid or negative causal account state")
    if open_positions < 0:
        raise NativeReplayReconstructionError("negative open position count")
    opportunity = _opportunity(original)
    values = dict(opportunity.decision_context)
    for key in (
        "qore_cash_usd_at_observation",
        "qore_peak_cash_usd_at_observation",
        "open_stop_risk_usd_at_observation",
        "broker_margin_held_usd_at_observation",
        "broker_cash_usd_at_observation",
        "open_positions_at_observation",
    ):
        if key in values:
            raise NativeReplayReconstructionError("account observation collides with sealed Trader context")
    values.update({
        "qore_cash_usd_at_observation": str(qore_cash_usd),
        "qore_peak_cash_usd_at_observation": str(peak_cash_usd),
        "open_stop_risk_usd_at_observation": str(open_stop_risk_usd),
        "broker_margin_held_usd_at_observation": str(broker_margin_held_usd),
        "broker_cash_usd_at_observation": str(broker_cash_usd),
        "open_positions_at_observation": str(open_positions),
    })
    opportunity=replace(opportunity,decision_context=tuple(sorted(values.items())))
    regime=_regime(original,opportunity_count=1)
    risk_utilization = min(Decimal("1"),open_stop_risk_usd / max(Decimal("0.00000001"), qore_cash_usd))
    margin_utilization = min(Decimal("1"),broker_margin_held_usd / max(Decimal("0.00000001"), broker_cash_usd))
    drawdown = ((peak_cash_usd-qore_cash_usd)/peak_cash_usd
                if peak_cash_usd > 0 and peak_cash_usd >= qore_cash_usd
                else Decimal("0"))
    regime=replace(
        regime, risk_utilization=risk_utilization,
        margin_utilization=margin_utilization,
        drawdown_utilization=min(Decimal("1"),drawdown),
    )
    consultation=consult_cibo_economic_faculties(
        decision_at=decision_at,
        opportunities=(opportunity,),
        regime_state=regime,
    )
    result=run_native_maximum_intelligence(
        consultation=consultation,
        opportunities=(opportunity,),
        target=opportunity,
        regime_state=regime,
    )
    instruction=issue_native_sovereign_mode_instruction(
        episode=result.cognitive_episode,
        signal_fingerprint=opportunity.signal_fingerprint,
        trader_id=opportunity.trader_id.value,
        decided_at=decision_at,
        semantic_digest=result.semantic_digest,
    )
    if not result.native_only or result.external_ai_call_count:
        raise NativeReplayReconstructionError("Native MAX runtime integrity failure")
    return instruction, {
        "recomputed_native_max": True,
        "cf01_cf19_consultation_id": consultation.consultation_id,
        "native_semantic_digest": result.semantic_digest,
        "native_decision_digest": instruction.decision_digest,
        "native_decided_at": decision_at.isoformat(),
        "native_faculties_applicable": result.applicable_faculty_count,
        "native_faculties_successful": result.successful_faculty_count,
        "native_faculties_blocked": list(result.blocked_function_codes),
        "account_cash_at_decision_usd": str(qore_cash_usd),
        "account_held_stop_risk_usd": str(open_stop_risk_usd),
        "account_broker_margin_held_usd": str(broker_margin_held_usd),
        "account_active_positions": open_positions,
        "native_regime_risk_utilization": str(risk_utilization),
        "native_regime_drawdown_utilization": str(drawdown),
        "native_mode": instruction.mode,
        "native_calibration_confidence": instruction.calibration_confidence,
        "native_abstention_required": instruction.abstention_required,
        "native_calibration_note": str(result.cognitive_episode.calibration.note),
        "native_calibration_kind": str(result.cognitive_episode.calibration.kind),
        "native_reasoning_route": result.cognitive_episode.reasoning_routing.decision.value,
        "native_metacognitive_evidence_sufficiency": (
            result.cognitive_episode.metacognitive_audit.evidence_sufficiency.value
        ),
        "native_decision_gate_codes": list(result.cognitive_episode.decision_gate_codes),
        "native_cognitive_not_authentic_broker_exec": True,
        "native_exit_policy_is_static_template": True,
    }
