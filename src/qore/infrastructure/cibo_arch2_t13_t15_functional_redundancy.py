"""Architect-2 functional redundancy probe for CE2I T13/T15.

This probe consumes real Trader-Lab decision traces and answers one narrow
question: in the observed integrated composition, did T13/T15 receive any
causal state capable of changing the allocator envelope, and did they actually
change it?

It does not modify capital policy, sizing, QORE Risk, execution, or outcomes.
"""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal, InvalidOperation
from typing import Any


def _dec(value: object) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"non-decimal value: {value!r}") from exc
    if not result.is_finite():
        raise ValueError(f"non-finite decimal: {value!r}")
    return result


def _walk(value: object) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def _receipts(trace: dict[str, Any], code: str) -> list[dict[str, Any]]:
    opportunities = trace.get("opportunities")
    if not isinstance(opportunities, list) or not opportunities:
        raise ValueError("decision trace opportunities missing")
    result: list[dict[str, Any]] = []
    for opportunity in opportunities:
        if not isinstance(opportunity, dict):
            continue
        ce2i = opportunity.get("ce2i")
        for row in _walk(ce2i):
            if row.get("tool_code") == code:
                result.append(row)
    return result


def _zero_effect(receipt: dict[str, Any]) -> bool:
    output = receipt.get("output_payload")
    if not isinstance(output, dict):
        return False
    return (
        receipt.get("decision_changed") is False
        and receipt.get("economic_effect_observable") is False
        and _dec(output.get("reserve_stop_risk_usd", 0)) == 0
        and _dec(output.get("reserve_margin_usd", 0)) == 0
    )


def _base_receipt_health(receipt: dict[str, Any]) -> bool:
    return (
        receipt.get("native_engine_called") is True
        and receipt.get("outcome_used") is False
        and receipt.get("broker_mutation") is False
        and receipt.get("downstream_consumer") == "phase20h-allocator-budget"
        and receipt.get("status") == "APPLIED"
    )


def analyze_t13_t15_redundancy(trace: dict[str, Any]) -> dict[str, Any]:
    t13 = _receipts(trace, "T13")
    t15 = _receipts(trace, "T15")
    if not t13 or not t15:
        raise ValueError("T13/T15 runtime receipts are required")

    t13_zero_input = all(
        isinstance(row.get("input_payload"), dict)
        and _dec(row["input_payload"].get("hard_risk_headroom_usd", 0)) == 0
        and _dec(row["input_payload"].get("margin_headroom_usd", 0)) == 0
        for row in t13
    )
    t13_recovery_only = all(
        isinstance(row.get("input_payload"), dict)
        and row["input_payload"].get("drawdown_posture") == "RECOVERY"
        for row in t13
    )
    t13_zero_effect = all(_zero_effect(row) for row in t13)
    t13_health = all(_base_receipt_health(row) for row in t13)

    t15_known_options_empty = all(
        isinstance(row.get("input_payload"), dict)
        and not row["input_payload"].get("known_options")
        for row in t15
    )
    t15_identity_envelope = all(
        isinstance(row.get("input_payload"), dict)
        and isinstance(row.get("output_payload"), dict)
        and _dec(row["output_payload"].get("reserve_stop_risk_usd", 0)) == 0
        and _dec(row["output_payload"].get("reserve_margin_usd", 0)) == 0
        and _dec(row["output_payload"].get("deployable_stop_risk_usd", 0))
        == _dec(row["input_payload"].get("hard_risk_headroom_usd", 0))
        and _dec(row["output_payload"].get("deployable_margin_usd", 0))
        == _dec(row["input_payload"].get("margin_headroom_usd", 0))
        for row in t15
    )
    t15_zero_effect = all(_zero_effect(row) for row in t15)
    t15_health = all(_base_receipt_health(row) for row in t15)

    t13_no_measurable = (
        t13_health
        and t13_recovery_only
        and t13_zero_input
        and t13_zero_effect
    )
    t15_no_measurable = (
        t15_health
        and t15_known_options_empty
        and t15_identity_envelope
        and t15_zero_effect
    )

    return {
        "schema": "qore.cibo.arch2-t13-t15-functional-redundancy.v1",
        "group_id": trace.get("group_id"),
        "T13": {
            "receipt_count": len(t13),
            "native_consumer_chain_healthy": t13_health,
            "recovery_only": t13_recovery_only,
            "all_input_headroom_zero": t13_zero_input,
            "all_incremental_effect_zero": t13_zero_effect,
            "classification": (
                "NO_MEASURABLE_EFFECT" if t13_no_measurable else "UNPROVEN"
            ),
            "reason": (
                "T13 receives no deployable headroom in every observed recovery "
                "receipt, so its incremental reserve action is identically zero "
                "in the current integrated composition."
            ),
        },
        "T15": {
            "receipt_count": len(t15),
            "native_consumer_chain_healthy": t15_health,
            "all_known_options_empty": t15_known_options_empty,
            "all_outputs_identity_envelope": t15_identity_envelope,
            "all_incremental_effect_zero": t15_zero_effect,
            "classification": (
                "NO_MEASURABLE_EFFECT" if t15_no_measurable else "UNPROVEN"
            ),
            "reason": (
                "T15 receives no known option in every observed receipt and "
                "returns the allocator envelope unchanged, so its incremental "
                "effect is zero in the current integrated composition."
            ),
        },
        "functional_seam_closed": t13_no_measurable and t15_no_measurable,
        "scope": "CURRENT_REPLAY_COMPOSITION_ONLY",
        "economic_promotion_claimed": False,
        "outcome_aware_tuning": False,
        "authority_mutated": False,
    }
