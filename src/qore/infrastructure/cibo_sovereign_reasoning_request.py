"""Bind sovereign CF01-CF19 semantics into the existing CIBO reasoning runtime.

This adapter does not decide capital and does not invent a new intelligence
policy. It converts the complete causal faculty consultation into one
CiboReasoningRequest consumed by the already-existing CIBO reasoning engine /
Executive Brain path.

Memory remains context/evidence only. No outcome, sizing, Risk, execution,
broker, LIVE, production, or real-capital authority is introduced here.
"""

from __future__ import annotations

import json
from uuid import NAMESPACE_URL, uuid5

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_reasoning_runtime import CiboReasoningRequest
from qore.infrastructure.cibo_sovereign_function_consultation import (
    CiboEconomicConsultationReceipt,
)
from qore.modules.cibo.cognitive_contracts import CiboCognitiveEvidenceRef


_MAX_REASONING_PROMPT_CHARS = 60_000


def build_sovereign_reasoning_request(
    *,
    consultation: CiboEconomicConsultationReceipt,
    opportunity: TraderOpportunityEnvelope,
) -> CiboReasoningRequest:
    """Create one evidence-bound MAX-capability reasoning request.

    The request carries the exact full semantic CF01-CF19 outputs plus the
    opportunity's complete causal decision_context. The downstream reasoning
    engine remains responsible for inference and directive selection.
    """

    if not isinstance(consultation, CiboEconomicConsultationReceipt):
        raise CiboCapitalManagementError(
            "sovereign reasoning requires canonical faculty consultation"
        )
    if not isinstance(opportunity, TraderOpportunityEnvelope):
        raise CiboCapitalManagementError(
            "sovereign reasoning requires canonical Trader opportunity"
        )
    if consultation.outcome_used or consultation.broker_mutation:
        raise CiboCapitalManagementError(
            "sovereign reasoning cannot consume contaminated consultation"
        )
    if (
        opportunity.signal_fingerprint
        not in consultation.opportunity_fingerprints
    ):
        raise CiboCapitalManagementError(
            "sovereign reasoning target is absent from shared consultation"
        )
    if consultation.opportunity_fingerprints.count(
        opportunity.signal_fingerprint
    ) != 1:
        raise CiboCapitalManagementError(
            "sovereign reasoning target must appear exactly once"
        )

    faculty_semantics = []
    for receipt in consultation.faculty_receipts:
        native = receipt.output_payload.get("native_engine_output")
        if not isinstance(native, dict):
            raise CiboCapitalManagementError(
                "sovereign reasoning native semantic output missing"
            )
        semantic = (
            native.get("result_semantics")
            if "result_semantics" in native
            else native.get("result_value")
        )
        if receipt.output_payload.get("native_engine_called"):
            if native.get("semantic_transport") != "FULL_CANONICAL_READ_ONLY":
                raise CiboCapitalManagementError(
                    "sovereign reasoning requires full semantic transport"
                )
            if semantic is None:
                raise CiboCapitalManagementError(
                    "sovereign reasoning applicable faculty lacks semantics"
                )

        faculty_semantics.append(
            {
                "function_code": receipt.function_code,
                "faculty": receipt.faculty.value,
                "native_engine_name": receipt.output_payload[
                    "native_engine_name"
                ],
                "native_engine_status": receipt.output_payload[
                    "native_engine_status"
                ],
                "semantic_output": semantic,
                "evidence_status": receipt.output_payload.get(
                    "evidence_status"
                ),
                "contribution_code": receipt.output_payload.get(
                    "contribution_code"
                ),
            }
        )

    shared_context = None
    for receipt in consultation.faculty_receipts:
        candidate_context = receipt.input_payload.get(
            "high_intelligence_context"
        )
        if candidate_context is None:
            continue
        if shared_context is None:
            shared_context = candidate_context
        elif candidate_context != shared_context:
            raise CiboCapitalManagementError(
                "sovereign reasoning shared opportunity context drift"
            )
    if (
        not isinstance(shared_context, (tuple, list))
        or not shared_context
    ):
        raise CiboCapitalManagementError(
            "sovereign reasoning requires shared high-intelligence context"
        )

    prompt_payload = {
        "mission": "single-account-seven-trader-maximum-capability",
        "instruction": (
            "Reason from current causal state and faculty semantics. "
            "Memory is evidence, never authority. Decide whether this "
            "opportunity deserves capital, should defer, or should abstain. "
            "Do not infer from future outcome and do not choose broker order "
            "details. Preserve uncertainty explicitly."
        ),
        "shared_account_opportunity_surface": {
            "opportunity_count": len(
                consultation.opportunity_fingerprints
            ),
            "opportunity_fingerprints": list(
                consultation.opportunity_fingerprints
            ),
            "high_intelligence_context": shared_context,
        },
        "target_opportunity": {
            "signal_fingerprint": opportunity.signal_fingerprint,
            "trader_id": opportunity.trader_id.value,
            "qore_symbol": opportunity.qore_symbol,
            "provider_symbol": opportunity.provider_symbol,
            "side": opportunity.side,
            "entry_type": opportunity.entry_type,
            "intended_entry": format(opportunity.intended_entry, "f"),
            "stop_loss": format(opportunity.stop_loss, "f"),
            "take_profit": format(opportunity.take_profit, "f"),
            "stop_loss_per_volume": format(
                opportunity.stop_loss_per_volume,
                "f",
            ),
            "margin_per_volume": format(
                opportunity.margin_per_volume,
                "f",
            ),
            "minimum_volume": format(opportunity.minimum_volume, "f"),
            "maximum_volume": format(opportunity.maximum_volume, "f"),
            "minimum_execution_steps": opportunity.minimum_execution_steps,
            "decision_context": [
                [key, value] for key, value in opportunity.decision_context
            ],
        },
        "consultation": {
            "consultation_id": consultation.consultation_id,
            "coordination_disposition": (
                consultation.coordination_disposition
            ),
            "coordination_request_code": (
                consultation.coordination_request_code
            ),
            "mission_disposition": consultation.mission_disposition,
            "faculty_semantics": faculty_semantics,
        },
        "authority": {
            "memory_authority": False,
            "economic_authority": False,
            "sizing_authority": False,
            "risk_authority": False,
            "execution_authority": False,
            "broker_authority": False,
        },
    }
    prompt = json.dumps(
        prompt_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    if len(prompt) > _MAX_REASONING_PROMPT_CHARS:
        raise CiboCapitalManagementError(
            "sovereign reasoning prompt exceeds bounded causal payload"
        )

    consultation_digest = consultation.consultation_id.removeprefix(
        "sha256:"
    )
    evidence_refs = (
        CiboCognitiveEvidenceRef(
            "cibo:consultation:" + consultation_digest
        ),
        CiboCognitiveEvidenceRef(
            "cibo:opportunity:" + opportunity.signal_fingerprint
        ),
    )
    request_id = uuid5(
        NAMESPACE_URL,
        (
            "qore:cibo:single-account-maxcap:"
            + consultation.consultation_id
            + ":"
            + opportunity.signal_fingerprint
        ),
    )

    return CiboReasoningRequest(
        request_id=request_id,
        subject_code="single-account-maxcap",
        asked_at=consultation.decision_at,
        prompt=prompt,
        evidence_refs=evidence_refs,
        observations=(
            "causal-predecision",
            "full-cf01-cf19-consulted",
            "memory-evidence-not-authority",
            "qore-risk-sovereign",
            "single-account-seven-trader",
        ),
        memory_refs=(),
    )
