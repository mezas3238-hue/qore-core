"""Fail-closed terminalization for the frozen Architect-2 T11 contract.

T11 has two necessary scientific components after provider execution/slippage
calibration:
1. provider-bound market-impact model validation;
2. fresh-OOS validation of the frozen gross-edge prior.

A necessary component that is empirically falsified terminally falsifies T11.
Missing evidence never becomes falsification.  Only when both necessary
components are present and validated may T11 be recommended
COMPLETED_AND_PROVEN.

This module has no ledger, broker, sizing or productive authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_arch2_t11_gross_edge_oos import (
    T11GrossEdgeFreshOOSResult,
)
from qore.infrastructure.cibo_arch2_t11_market_impact_evaluator import (
    T11MarketImpactEvaluation,
)
from qore.infrastructure.cibo_arch2_t11_market_impact_terminal_receipt import (
    T11MarketImpactTerminalReceipt,
)

COMPLETED = "COMPLETED_AND_PROVEN"
FALSIFIED = "FALSIFIED_AND_CLOSED"
WAITING = "WAITING_ON_REQUIRED_EVIDENCE"


@dataclass(frozen=True, slots=True)
class T11TerminalRecommendation:
    recommendation: str
    market_impact_evidence_present: bool
    market_impact_model_ready: bool | None
    gross_edge_evidence_present: bool
    gross_edge_fresh_oos_validated: bool | None
    unresolved_requirements: tuple[str, ...]
    falsification_reasons: tuple[str, ...]
    canonical_ledger_modified: bool = False
    phase22_v2_consumed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.recommendation not in {COMPLETED, FALSIFIED, WAITING}:
            raise ValueError("T11 terminal recommendation invalid")
        if (
            self.canonical_ledger_modified
            or self.phase22_v2_consumed
            or self.productive_authority
        ):
            raise ValueError("T11 terminalizer exceeded Architect-2 authority")
        if self.market_impact_evidence_present != (
            self.market_impact_model_ready is not None
        ):
            raise ValueError("T11 market-impact presence/result drift")
        if self.gross_edge_evidence_present != (
            self.gross_edge_fresh_oos_validated is not None
        ):
            raise ValueError("T11 gross-edge presence/result drift")

        any_falsified = (
            self.market_impact_model_ready is False
            or self.gross_edge_fresh_oos_validated is False
        )
        both_proven = (
            self.market_impact_model_ready is True
            and self.gross_edge_fresh_oos_validated is True
        )
        expected = FALSIFIED if any_falsified else COMPLETED if both_proven else WAITING
        if self.recommendation != expected:
            raise ValueError("T11 terminal recommendation/result drift")

        if self.recommendation == COMPLETED and (
            self.unresolved_requirements or self.falsification_reasons
        ):
            raise ValueError("completed T11 cannot retain blockers/falsification")
        if self.recommendation == FALSIFIED and not self.falsification_reasons:
            raise ValueError("falsified T11 requires explicit reason")
        if self.recommendation == WAITING and not self.unresolved_requirements:
            raise ValueError("waiting T11 requires unresolved evidence")


def terminalize_t11(
    *,
    market_impact: T11MarketImpactEvaluation | None,
    gross_edge: T11GrossEdgeFreshOOSResult | None,
) -> T11TerminalRecommendation:
    unresolved: list[str] = []
    falsified: list[str] = []

    impact_ready: bool | None = None
    if market_impact is None:
        unresolved.append("REAL_PROVIDER_BOUND_MARKET_IMPACT_MODEL_REQUIRED")
    else:
        impact_ready = market_impact.market_impact_model_ready
        if not impact_ready:
            falsified.append(
                "FROZEN_PROVIDER_BOUND_MARKET_IMPACT_MODEL_FAILED_4_OF_4_VALIDATION"
            )

    gross_ready: bool | None = None
    if gross_edge is None:
        unresolved.append("REAL_CALIBRATED_FRESH_OOS_GROSS_EDGE_MODEL_REQUIRED")
    else:
        gross_ready = gross_edge.fresh_oos_validated
        if not gross_ready:
            falsified.append(
                "FROZEN_TRAIN_GROSS_EDGE_PRIOR_FAILED_FRESH_OOS_4_OF_4_VALIDATION"
            )

    if falsified:
        recommendation = FALSIFIED
        # Once a necessary frozen component is falsified, absent evidence for the
        # other component is no longer required to establish terminal falsification.
        unresolved = []
    elif impact_ready is True and gross_ready is True:
        recommendation = COMPLETED
        unresolved = []
    else:
        recommendation = WAITING

    return T11TerminalRecommendation(
        recommendation=recommendation,
        market_impact_evidence_present=market_impact is not None,
        market_impact_model_ready=impact_ready,
        gross_edge_evidence_present=gross_edge is not None,
        gross_edge_fresh_oos_validated=gross_ready,
        unresolved_requirements=tuple(unresolved),
        falsification_reasons=tuple(falsified),
        canonical_ledger_modified=False,
        phase22_v2_consumed=False,
        productive_authority=False,
    )


def terminalize_t11_from_receipt(
    *,
    market_impact_receipt: T11MarketImpactTerminalReceipt | None,
    gross_edge: T11GrossEdgeFreshOOSResult | None,
) -> T11TerminalRecommendation:
    """Terminalize T11 from the immutable sealed market-impact receipt.

    This is the Integrator-facing path. It never re-evaluates broker rows or
    changes the frozen market-impact decision.
    """

    unresolved: list[str] = []
    falsified: list[str] = []

    impact_ready: bool | None = None
    if market_impact_receipt is None:
        unresolved.append("REAL_PROVIDER_BOUND_MARKET_IMPACT_MODEL_REQUIRED")
    else:
        if not isinstance(
            market_impact_receipt,
            T11MarketImpactTerminalReceipt,
        ):
            raise ValueError("T11 market-impact terminal receipt type invalid")
        impact_ready = market_impact_receipt.market_impact_model_ready
        if not impact_ready:
            falsified.append(
                "FROZEN_PROVIDER_BOUND_MARKET_IMPACT_MODEL_FAILED_4_OF_4_VALIDATION"
            )

    gross_ready: bool | None = None
    if gross_edge is None:
        unresolved.append("REAL_CALIBRATED_FRESH_OOS_GROSS_EDGE_MODEL_REQUIRED")
    else:
        gross_ready = gross_edge.fresh_oos_validated
        if not gross_ready:
            falsified.append(
                "FROZEN_TRAIN_GROSS_EDGE_PRIOR_FAILED_FRESH_OOS_4_OF_4_VALIDATION"
            )

    if falsified:
        recommendation = FALSIFIED
        unresolved = []
    elif impact_ready is True and gross_ready is True:
        recommendation = COMPLETED
        unresolved = []
    else:
        recommendation = WAITING

    return T11TerminalRecommendation(
        recommendation=recommendation,
        market_impact_evidence_present=market_impact_receipt is not None,
        market_impact_model_ready=impact_ready,
        gross_edge_evidence_present=gross_edge is not None,
        gross_edge_fresh_oos_validated=gross_ready,
        unresolved_requirements=tuple(unresolved),
        falsification_reasons=tuple(falsified),
        canonical_ledger_modified=False,
        phase22_v2_consumed=False,
        productive_authority=False,
    )
