"""Read-only native semantic observations for CF01-CF19.

These observations are the intelligence plane, not the authority plane.
They are derived exclusively from causal predecision inputs already admitted to
CIBO and are available even when a formal CF result correctly fails closed for
lack of an external Trader Lab / Market / Economic / Risk authority receipt.

They cannot authorize capital, sizing, Risk, execution, broker mutation, LIVE,
Production, or real capital.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_regime_selector import CiboCapitalRegimeState


def _context(opportunity: TraderOpportunityEnvelope) -> dict[str, str]:
    result = dict(opportunity.decision_context)
    if len(result) != len(opportunity.decision_context):
        raise CiboCapitalManagementError(
            "native faculty semantics decision_context duplicate key"
        )
    return result


def _reward_r(opportunity: TraderOpportunityEnvelope) -> str | None:
    if opportunity.side == "long":
        risk = opportunity.intended_entry - opportunity.stop_loss
        reward = opportunity.take_profit - opportunity.intended_entry
    else:
        risk = opportunity.stop_loss - opportunity.intended_entry
        reward = opportunity.intended_entry - opportunity.take_profit
    if risk <= 0:
        return None
    return format(reward / risk, "f")


def _opportunity_row(
    opportunity: TraderOpportunityEnvelope,
) -> dict[str, object]:
    context = _context(opportunity)
    return {
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
        "margin_per_volume": format(opportunity.margin_per_volume, "f"),
        "minimum_volume": format(opportunity.minimum_volume, "f"),
        "maximum_volume": format(opportunity.maximum_volume, "f"),
        "minimum_execution_steps": opportunity.minimum_execution_steps,
        "planned_reward_r": _reward_r(opportunity),
        "perception_key_count": len(context),
        "native_perception_complete": (
            context.get("cibo_native_perception_complete")
        ),
        "native_perception_version": (
            context.get("cibo_native_perception_version")
        ),
        "context_quality_disposition": context.get(
            "cibo_context_quality_disposition"
        ),
        "expectation_basis": context.get("cibo_expectation_basis"),
        "expected_value_usd": context.get("cibo_expected_value_usd"),
        "expected_net_utility_usd": context.get(
            "cibo_expected_net_utility_usd"
        ),
        "expected_capital_minutes": context.get(
            "cibo_expected_capital_minutes"
        ),
        "decision_context": [
            [key, value] for key, value in sorted(context.items())
        ],
    }


def _regime(regime_state: CiboCapitalRegimeState) -> dict[str, object]:
    return {
        "liquidity": regime_state.liquidity.value,
        "volatility": regime_state.volatility.value,
        "correlation": regime_state.correlation.value,
        "provider_condition": regime_state.provider_condition.value,
        "risk_utilization": format(regime_state.risk_utilization, "f"),
        "margin_utilization": format(regime_state.margin_utilization, "f"),
        "drawdown_utilization": format(
            regime_state.drawdown_utilization,
            "f",
        ),
        "opportunity_count": regime_state.opportunity_count,
        "position_path_adverse": regime_state.position_path_adverse,
        "evidence_stale": regime_state.evidence_stale,
    }


def _digest(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_native_faculty_research_semantics(
    *,
    function_code: str,
    decision_at: datetime,
    opportunities: tuple[TraderOpportunityEnvelope, ...],
    regime_state: CiboCapitalRegimeState,
) -> dict[str, object]:
    """Return deterministic, causal, authority-free semantics for one CF."""

    if function_code not in {
        f"CF{index:02d}" for index in range(1, 20)
    }:
        raise CiboCapitalManagementError(
            "native faculty semantics function code invalid"
        )
    if decision_at.tzinfo is None or decision_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "native faculty semantics decision_at must be timezone-aware"
        )
    if (
        not isinstance(opportunities, tuple)
        or not opportunities
        or any(
            not isinstance(item, TraderOpportunityEnvelope)
            for item in opportunities
        )
    ):
        raise CiboCapitalManagementError(
            "native faculty semantics requires canonical opportunities"
        )
    if not isinstance(regime_state, CiboCapitalRegimeState):
        raise CiboCapitalManagementError(
            "native faculty semantics requires canonical regime"
        )
    if regime_state.opportunity_count != len(opportunities):
        raise CiboCapitalManagementError(
            "native faculty semantics opportunity count drift"
        )

    rows = tuple(
        _opportunity_row(item)
        for item in sorted(
            opportunities,
            key=lambda item: item.signal_fingerprint,
        )
    )
    regime = _regime(regime_state)
    traders = tuple(sorted({str(row["trader_id"]) for row in rows}))
    symbols = tuple(sorted({str(row["qore_symbol"]) for row in rows}))
    providers = tuple(sorted({str(row["provider_symbol"]) for row in rows}))
    context_key_counts = tuple(
        (str(row["signal_fingerprint"]), int(row["perception_key_count"]))
        for row in rows
    )

    if function_code == "CF01":
        semantics: object = {
            "financial_world_state": regime,
            "symbols": symbols,
        }
    elif function_code == "CF02":
        semantics = {
            "market_intelligence_surface": rows,
            "regime": regime,
        }
    elif function_code == "CF03":
        semantics = {
            "trader_surface": traders,
            "opportunity_count": len(rows),
            "context_key_counts": context_key_counts,
        }
    elif function_code == "CF04":
        semantics = {
            "trader_capability_observation": tuple(
                {
                    "trader_id": row["trader_id"],
                    "perception_key_count": row["perception_key_count"],
                    "native_perception_complete": row[
                        "native_perception_complete"
                    ],
                    "native_perception_version": row[
                        "native_perception_version"
                    ],
                }
                for row in rows
            ),
        }
    elif function_code == "CF05":
        semantics = {
            "opportunity_geometry": tuple(
                {
                    "signal_fingerprint": row["signal_fingerprint"],
                    "trader_id": row["trader_id"],
                    "symbol": row["qore_symbol"],
                    "side": row["side"],
                    "planned_reward_r": row["planned_reward_r"],
                    "stop_loss_per_volume": row["stop_loss_per_volume"],
                    "margin_per_volume": row["margin_per_volume"],
                }
                for row in rows
            )
        }
    elif function_code == "CF06":
        semantics = {
            "portfolio_state": {
                "traders": traders,
                "symbols": symbols,
                "correlation": regime["correlation"],
                "risk_utilization": regime["risk_utilization"],
                "margin_utilization": regime["margin_utilization"],
                "drawdown_utilization": regime["drawdown_utilization"],
                "opportunity_count": len(rows),
            }
        }
    elif function_code == "CF07":
        semantics = {
            "economic_state": {
                "provider_condition": regime["provider_condition"],
                "providers": providers,
                "unit_economics": tuple(
                    {
                        "signal_fingerprint": row["signal_fingerprint"],
                        "stop_loss_per_volume": row[
                            "stop_loss_per_volume"
                        ],
                        "margin_per_volume": row["margin_per_volume"],
                        "planned_reward_r": row["planned_reward_r"],
                        "minimum_volume": row["minimum_volume"],
                        "maximum_volume": row["maximum_volume"],
                        "expectation_basis": row["expectation_basis"],
                        "expected_value_usd": row["expected_value_usd"],
                        "expected_net_utility_usd": row[
                            "expected_net_utility_usd"
                        ],
                        "expected_capital_minutes": row[
                            "expected_capital_minutes"
                        ],
                    }
                    for row in rows
                ),
            }
        }
    elif function_code == "CF08":
        semantics = {
            "temporal_boundary": "PREDECISION",
            "outcome_available": False,
        }
    elif function_code == "CF09":
        semantics = {
            "failure_intelligence_predecision": {
                "evidence_stale": regime["evidence_stale"],
                "provider_condition": regime["provider_condition"],
                "position_path_adverse": regime[
                    "position_path_adverse"
                ],
                "context_key_counts": context_key_counts,
            }
        }
    elif function_code == "CF10":
        semantics = {
            "quantitative_state": {
                "opportunity_count": len(rows),
                "risk_utilization": regime["risk_utilization"],
                "margin_utilization": regime["margin_utilization"],
                "drawdown_utilization": regime["drawdown_utilization"],
                "planned_reward_r": tuple(
                    (
                        row["signal_fingerprint"],
                        row["planned_reward_r"],
                    )
                    for row in rows
                ),
            }
        }
    elif function_code == "CF11":
        semantics = {
            "research_state": {
                "authority_evidence_required": True,
                "perception_key_counts": context_key_counts,
                "outcome_available": False,
            }
        }
    elif function_code == "CF12":
        semantics = {
            "risk_aware_state": {
                "qore_risk_authority": "external-sovereign",
                "risk_utilization": regime["risk_utilization"],
                "margin_utilization": regime["margin_utilization"],
                "drawdown_utilization": regime["drawdown_utilization"],
                "provider_condition": regime["provider_condition"],
            }
        }
    elif function_code == "CF13":
        semantics = {
            "core_health_state": {
                "causal_predecision": True,
                "broker_mutation": False,
                "outcome_used": False,
                "evidence_stale": regime["evidence_stale"],
                "context_key_counts": context_key_counts,
            }
        }
    elif function_code == "CF14":
        semantics = {
            "executive_plan_state": {
                "objective": "evaluate-opportunity-and-capital",
                "opportunity_fingerprints": tuple(
                    row["signal_fingerprint"] for row in rows
                ),
                "qore_risk_pending": True,
            }
        }
    elif function_code == "CF15":
        semantics = {
            "executive_context": {
                "decision_at": decision_at.isoformat(),
                "regime": regime,
                "opportunities": rows,
            }
        }
    elif function_code == "CF16":
        semantics = {
            "trader_voice_surface": tuple(
                {
                    "trader_id": row["trader_id"],
                    "signal_fingerprint": row["signal_fingerprint"],
                    "symbol": row["qore_symbol"],
                    "decision_context": row["decision_context"],
                }
                for row in rows
            )
        }
    elif function_code == "CF17":
        journal = {
            "decision_at": decision_at.isoformat(),
            "regime": regime,
            "signals": tuple(
                row["signal_fingerprint"] for row in rows
            ),
            "alternatives": (
                "evaluate-capital",
                "defer",
                "abstain",
            ),
            "outcome_available": False,
        }
        semantics = {
            "decision_journal_predecision": journal,
            "journal_sha256": _digest(journal),
        }
    elif function_code == "CF18":
        semantics = {
            "temporal_boundary": "PREDECISION",
            "self_evaluation_available": False,
        }
    else:
        semantics = {
            "temporal_boundary": "PREDECISION",
            "learning_available": False,
            "current_outcome_consumed": False,
        }

    envelope = {
        "schema": "qore.cibo.native-faculty-research-semantics.v1",
        "function_code": function_code,
        "decision_at": decision_at.isoformat(),
        "research_read_only": True,
        "causal_predecision_only": True,
        "memory_is_evidence_not_authority": True,
        "economic_authority": False,
        "sizing_authority": False,
        "risk_authority": False,
        "execution_authority": False,
        "broker_authority": False,
        "outcome_used": False,
        "semantics": semantics,
    }
    envelope["semantic_sha256"] = _digest(envelope)
    return envelope
