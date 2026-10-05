"""Canonical high-intelligence causal context for CIBO.

This module exposes the complete TraderOpportunityEnvelope predecision state to
CIBO cognition. Memory/context remain read-only evidence: this module grants no
sizing, capital, Risk, execution, broker, LIVE, or production authority.
"""

from __future__ import annotations

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)


def build_high_intelligence_context(
    opportunities: tuple[TraderOpportunityEnvelope, ...],
) -> tuple[dict[str, object], ...]:
    """Return deterministic full causal context for admitted opportunities."""

    if (
        not isinstance(opportunities, tuple)
        or not opportunities
        or any(
            not isinstance(item, TraderOpportunityEnvelope)
            for item in opportunities
        )
    ):
        raise CiboCapitalManagementError(
            "high-intelligence context requires canonical opportunities"
        )

    fingerprints = tuple(
        item.signal_fingerprint for item in opportunities
    )
    if len(fingerprints) != len(set(fingerprints)):
        raise CiboCapitalManagementError(
            "high-intelligence context opportunity fingerprints must be unique"
        )

    return tuple(
        {
            "signal_fingerprint": item.signal_fingerprint,
            "trader_id": item.trader_id.value,
            "qore_symbol": item.qore_symbol,
            "provider_symbol": item.provider_symbol,
            "side": item.side,
            "entry_type": item.entry_type,
            "intended_entry": str(item.intended_entry),
            "stop_loss": str(item.stop_loss),
            "take_profit": str(item.take_profit),
            "stop_loss_per_volume": str(item.stop_loss_per_volume),
            "margin_per_volume": str(item.margin_per_volume),
            "volume_step": str(item.volume_step),
            "minimum_volume": str(item.minimum_volume),
            "maximum_volume": str(item.maximum_volume),
            "minimum_execution_steps": item.minimum_execution_steps,
            "decision_context": [list(pair) for pair in item.decision_context],
        }
        for item in sorted(
            opportunities,
            key=lambda candidate: candidate.signal_fingerprint,
        )
    )
