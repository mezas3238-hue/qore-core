"""Terminal scientific disposition logic for Architect-2 CE2I T11.

The decision order is frozen before the provider experiment completes:
1. A falsified required nonlinear market-impact model falsifies T11.
2. If market impact survives, a supplied fresh-OOS gross-edge result must also
   survive; a falsified gross-edge model falsifies T11.
3. Only when both required nonlinear inputs survive may Architect-2 recommend
   COMPLETED_AND_PROVEN.
4. Missing gross-edge evidence after market-impact PASS remains nonterminal.

This module never edits the canonical ledger and grants no productive authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.cibo_arch2_t11_gross_edge_oos import (
    T11GrossEdgeFreshOOSResult,
)
from qore.infrastructure.cibo_arch2_t11_market_impact_evaluator import (
    T11MarketImpactEvaluation,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


class T11TerminalRecommendation(StrEnum):
    COMPLETED_AND_PROVEN = "COMPLETED_AND_PROVEN"
    FALSIFIED_AND_CLOSED = "FALSIFIED_AND_CLOSED"
    WAITING_ON_GROSS_EDGE_FRESH_OOS = "WAITING_ON_GROSS_EDGE_FRESH_OOS"


@dataclass(frozen=True, slots=True)
class T11TerminalDispositionAssessment:
    recommendation: T11TerminalRecommendation
    market_impact_ready: bool
    gross_edge_evidence_present: bool
    gross_edge_ready: bool | None
    blocking_requirement: str | None
    canonical_ledger_modified: bool = False
    phase22_v2_consumed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.recommendation is T11TerminalRecommendation.COMPLETED_AND_PROVEN:
            if not (
                self.market_impact_ready
                and self.gross_edge_evidence_present
                and self.gross_edge_ready is True
                and self.blocking_requirement is None
            ):
                raise CiboCapitalManagementError(
                    "T11 completed recommendation evidence drift"
                )
        elif self.recommendation is T11TerminalRecommendation.FALSIFIED_AND_CLOSED:
            if self.market_impact_ready and self.gross_edge_ready is not False:
                raise CiboCapitalManagementError(
                    "T11 falsification requires a falsified mandatory input"
                )
            if self.blocking_requirement is not None:
                raise CiboCapitalManagementError(
                    "T11 terminal falsification cannot retain blocker"
                )
        else:
            if (
                not self.market_impact_ready
                or self.gross_edge_evidence_present
                or self.gross_edge_ready is not None
                or self.blocking_requirement
                != "FRESH_OOS_GROSS_EDGE_VALIDATION_REQUIRED"
            ):
                raise CiboCapitalManagementError(
                    "T11 waiting recommendation state drift"
                )
        if (
            self.canonical_ledger_modified
            or self.phase22_v2_consumed
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "T11 terminal assessment exceeded Architect-2 authority"
            )


def assess_t11_terminal_disposition(
    *,
    market_impact: T11MarketImpactEvaluation,
    gross_edge: T11GrossEdgeFreshOOSResult | None,
) -> T11TerminalDispositionAssessment:
    if not isinstance(market_impact, T11MarketImpactEvaluation):
        raise CiboCapitalManagementError(
            "T11 terminal assessment requires canonical market-impact evaluation"
        )
    if gross_edge is not None and not isinstance(
        gross_edge,
        T11GrossEdgeFreshOOSResult,
    ):
        raise CiboCapitalManagementError(
            "T11 terminal assessment gross-edge evidence invalid"
        )

    if not market_impact.market_impact_model_ready:
        return T11TerminalDispositionAssessment(
            recommendation=T11TerminalRecommendation.FALSIFIED_AND_CLOSED,
            market_impact_ready=False,
            gross_edge_evidence_present=gross_edge is not None,
            gross_edge_ready=(
                None if gross_edge is None else gross_edge.fresh_oos_validated
            ),
            blocking_requirement=None,
        )

    if gross_edge is None:
        return T11TerminalDispositionAssessment(
            recommendation=T11TerminalRecommendation.WAITING_ON_GROSS_EDGE_FRESH_OOS,
            market_impact_ready=True,
            gross_edge_evidence_present=False,
            gross_edge_ready=None,
            blocking_requirement="FRESH_OOS_GROSS_EDGE_VALIDATION_REQUIRED",
        )

    if not gross_edge.fresh_oos_validated:
        return T11TerminalDispositionAssessment(
            recommendation=T11TerminalRecommendation.FALSIFIED_AND_CLOSED,
            market_impact_ready=True,
            gross_edge_evidence_present=True,
            gross_edge_ready=False,
            blocking_requirement=None,
        )

    return T11TerminalDispositionAssessment(
        recommendation=T11TerminalRecommendation.COMPLETED_AND_PROVEN,
        market_impact_ready=True,
        gross_edge_evidence_present=True,
        gross_edge_ready=True,
        blocking_requirement=None,
    )
