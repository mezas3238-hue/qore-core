"""Causal economics adapter for CIBO single-account ceiling discovery.

This module converts resealed manifest rows into the exact predecision economic
surface consumed by the sovereign ceiling state. It never reads settlement
outcomes and fails closed on future/outcome/PnL leakage.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal, localcontext
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_single_account_ceiling_state import (
    CiboCeilingOpportunityEvidence,
)
from qore.infrastructure.cibo_single_account_manifest_integrity import (
    validate_single_account_manifest_sha256,
)

_EXPECTATION_BASES = {
    "FROZEN_HISTORICAL_PRIOR",
    "CAUSAL_MODEL_FORECAST",
    "CURRENT_STATE_FORECAST",
}


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CiboCapitalManagementError(f"{name} must be a mapping")
    return value


def _decimal(value: object, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as error:
        raise CiboCapitalManagementError(f"{name} must be Decimal-compatible") from error
    if not result.is_finite():
        raise CiboCapitalManagementError(f"{name} must be finite")
    return result


def _datetime(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise CiboCapitalManagementError(f"{name} must be string")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise CiboCapitalManagementError(f"{name} must be timezone-aware")
    return result


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _decision_context(payload: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    raw = payload.get("decision_context", ())
    if isinstance(raw, Mapping):
        return tuple(sorted((str(key), str(value)) for key, value in raw.items()))
    if not isinstance(raw, (list, tuple)):
        raise CiboCapitalManagementError("decision_context must be pairs or mapping")
    result: list[tuple[str, str]] = []
    for item in raw:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise CiboCapitalManagementError("decision_context entry must be key/value pair")
        result.append((str(item[0]), str(item[1])))
    return tuple(result)


def _cognitive_economic_context(
    row: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> tuple[tuple[str, str], ...]:
    base = dict(_decision_context(payload))
    if len(base) != len(_decision_context(payload)):
        raise CiboCapitalManagementError(
            "decision_context contains duplicate keys"
        )

    expectation = _mapping(row.get("expectation"), "expectation")
    context_quality = _mapping(
        row.get("context_quality"),
        "context_quality",
    )
    disposition = context_quality.get("disposition")
    basis = expectation.get("basis")
    expected_value = expectation.get("expected_net_value_usd")
    expected_minutes = expectation.get("expected_capital_minutes")
    if not isinstance(disposition, str) or not disposition:
        raise CiboCapitalManagementError(
            "cognitive context quality disposition is required"
        )
    if not isinstance(basis, str) or not basis:
        raise CiboCapitalManagementError(
            "cognitive expectation basis is required"
        )
    if expected_value is None or not str(expected_value):
        raise CiboCapitalManagementError(
            "cognitive expected value is required"
        )
    if expected_minutes is None or not str(expected_minutes):
        raise CiboCapitalManagementError(
            "cognitive expected capital minutes are required"
        )
    raw_rules = context_quality.get("matched_rule_ids", ())
    if not isinstance(raw_rules, (list, tuple)):
        raise CiboCapitalManagementError(
            "cognitive context quality rules must be a sequence"
        )
    rule_value = ",".join(str(item) for item in raw_rules) or "none"
    minimum_volume = _decimal(
        payload.get("minimum_volume"),
        "minimum_volume",
    )
    uncertainty_penalty = _decimal(
        expectation.get("uncertainty_penalty_usd", "0"),
        "uncertainty_penalty_usd",
    )
    provider_cost_per_volume = (
        manifest_row_provider_cost_per_volume_usd(row)
    )
    with localcontext() as context:
        context.prec = 100
        expected_net_utility = (
            _decimal(expected_value, "expected_net_value_usd")
            - provider_cost_per_volume * minimum_volume
            - uncertainty_penalty
        )
    additions = {
        "cibo_context_quality_disposition": disposition,
        "cibo_context_quality_rules": rule_value,
        "cibo_expectation_basis": basis,
        "cibo_expected_value_usd": str(expected_value),
        "cibo_expected_net_utility_usd": format(
            expected_net_utility,
            "f",
        ),
        "cibo_expected_capital_minutes": str(expected_minutes),
    }
    overlap = set(base).intersection(additions)
    if overlap:
        raise CiboCapitalManagementError(
            "decision_context collides with CIBO economic context: "
            + ",".join(sorted(overlap))
        )
    base.update(additions)
    return tuple(sorted(base.items()))


def _opportunity(row: Mapping[str, Any]) -> TraderOpportunityEnvelope:
    payload = _mapping(row.get("trader_opportunity"), "trader_opportunity")
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage(str(row["trader_id"])),
        signal_fingerprint=str(row["signal_fingerprint"]),
        qore_symbol=str(row["qore_symbol"]),
        provider_symbol=str(payload.get("provider_symbol") or row["qore_symbol"]),
        side=str(payload["side"]),
        entry_type=str(payload.get("entry_type", "market")),
        intended_entry=_decimal(payload["intended_entry"], "intended_entry"),
        stop_loss=_decimal(payload["stop_loss"], "stop_loss"),
        take_profit=_decimal(payload["take_profit"], "take_profit"),
        stop_loss_per_volume=_decimal(
            payload["stop_loss_per_volume"],
            "stop_loss_per_volume",
        ),
        margin_per_volume=_decimal(payload["margin_per_volume"], "margin_per_volume"),
        volume_step=_decimal(payload["volume_step"], "volume_step"),
        minimum_volume=_decimal(payload["minimum_volume"], "minimum_volume"),
        maximum_volume=_decimal(payload["maximum_volume"], "maximum_volume"),
        minimum_execution_steps=int(payload.get("minimum_execution_steps", 1)),
        decision_context=_cognitive_economic_context(row, payload),
    )


def manifest_row_provider_cost_per_volume_usd(
    row: Mapping[str, Any],
) -> Decimal:
    state = _mapping(row.get("market_predecision_state"), "market_predecision_state")
    observation = _mapping(state.get("provider_observation"), "provider_observation")
    ask = _decimal(observation["ask"], "provider ask")
    bid = _decimal(observation["bid"], "provider bid")
    tick_size = _decimal(observation["tick_size"], "provider tick_size")
    tick_value = _decimal(observation["tick_value"], "provider tick_value")
    commission = _decimal(
        observation.get("commission_per_volume_usd", "0"),
        "provider commission",
    )
    slippage = _decimal(
        observation.get("slippage_reserve_per_volume_usd", "0"),
        "provider slippage reserve",
    )
    if tick_size <= 0 or tick_value <= 0 or ask < bid or commission < 0 or slippage < 0:
        raise CiboCapitalManagementError("provider economics invalid")
    return ((ask - bid) / tick_size) * tick_value + commission + slippage


def manifest_row_to_ceiling_opportunity_evidence(
    row: Mapping[str, Any],
) -> CiboCeilingOpportunityEvidence:
    """Convert one manifest row without consulting settlement outcome."""

    decision_at = _datetime(row.get("market_decision_at"), "market_decision_at")
    expectation = _mapping(row.get("expectation"), "expectation")
    context = _mapping(row.get("context_quality"), "context_quality")

    evidence_id = expectation.get("evidence_id")
    if not isinstance(evidence_id, str) or not evidence_id:
        raise CiboCapitalManagementError("expectation evidence_id is required")
    expectation_as_of = _datetime(expectation.get("as_of"), "expectation as_of")
    if expectation_as_of > decision_at:
        raise CiboCapitalManagementError("expectation cannot postdate decision")
    if expectation.get("basis") not in _EXPECTATION_BASES:
        raise CiboCapitalManagementError("expectation basis is not canonical")
    for name in (
        "future_market_used",
        "outcome_used",
        "pnl_used",
        "post_entry_path_used",
        "sizing_authority",
        "risk_authority",
        "order_authority",
        "execution_authority",
    ):
        if expectation.get(name) is not False:
            raise CiboCapitalManagementError(
                f"expectation governance flag must be false: {name}"
            )

    if context.get("causal_predecision") is not True:
        raise CiboCapitalManagementError("context quality must be causal predecision")
    for name in (
        "identity_predicate_used",
        "outcome_used",
        "sizing_authority",
        "risk_authority",
        "execution_authority",
        "broker_mutation",
        "certification_claimed",
    ):
        if context.get(name) is not False:
            raise CiboCapitalManagementError(
                f"context-quality governance flag must be false: {name}"
            )
    disposition = context.get("disposition")
    if disposition not in {"ALLOW", "ABSTAIN"}:
        raise CiboCapitalManagementError("context-quality disposition is invalid")

    uncertainty_penalty = _decimal(
        expectation.get("uncertainty_penalty_usd", "0"),
        "uncertainty_penalty_usd",
    )
    if uncertainty_penalty < 0:
        raise CiboCapitalManagementError("uncertainty penalty cannot be negative")

    return CiboCeilingOpportunityEvidence(
        opportunity=_opportunity(row),
        expected_net_value_usd=_decimal(
            expectation["expected_net_value_usd"],
            "expected_net_value_usd",
        ),
        expected_capital_minutes=_decimal(
            expectation["expected_capital_minutes"],
            "expected_capital_minutes",
        ),
        provider_cost_per_volume_usd=manifest_row_provider_cost_per_volume_usd(row),
        expectation_evidence_sha256=_canonical_sha256(expectation),
        expectation_basis=CausalExpectationBasis(
            str(expectation["basis"])
        ),
        context_allowed=disposition == "ALLOW",
        provider_viable=True,
        capital_source_eligible=True,
        uncertainty_penalty_usd=uncertainty_penalty,
    )


def manifest_to_ceiling_opportunity_evidence(
    manifest: Mapping[str, Any],
) -> tuple[CiboCeilingOpportunityEvidence, ...]:
    """Validate the manifest seal and convert every causal opportunity row."""

    validate_single_account_manifest_sha256(manifest)
    rows = manifest.get("opportunities")
    if not isinstance(rows, list) or not rows:
        raise CiboCapitalManagementError("single-account manifest has no opportunities")
    return tuple(
        manifest_row_to_ceiling_opportunity_evidence(_mapping(row, "manifest row"))
        for row in rows
    )
