"""Terminal disposition law for Architect-2 CE2I T02.

T02 has two frozen evidence gates:
1. fresh structural-stop precision on explicit terminal-reason evidence;
2. provider-bound economic ablation.

Missing population remains non-terminal.  A sufficiently populated structural
exam that fails the frozen rule is terminal falsification.  A structurally
valid population advances to the economic ablation; 4/4 economic PASS completes
T02 and any economic fold failure falsifies it.

No result grants runtime authority or mutates the canonical ledger.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_arch2_t02_economic_ablation import (
    T02EconomicAblationResult,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_t02_structural_oos import (
    T02ForwardStructuralAudit,
)

COMPLETED = "COMPLETED_AND_PROVEN"
FALSIFIED = "FALSIFIED_AND_CLOSED"
WAITING_STRUCTURAL = "WAITING_ON_AUTHORITATIVE_FORWARD_LIFECYCLE"
WAITING_ABLATION = "WAITING_ON_PROVIDER_BOUND_ECONOMIC_ABLATION"


@dataclass(frozen=True, slots=True)
class T02TerminalDispositionAssessment:
    structural_population_sufficient: bool
    structural_precision_passed: bool
    economic_ablation_present: bool
    economic_ablation_passed: bool | None
    terminal_ready: bool
    recommendation: str | None
    waiting_reason: str | None
    canonical_ledger_modified: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.economic_ablation_present != (
            self.economic_ablation_passed is not None
        ):
            raise CiboCapitalManagementError(
                "T02 terminal assessment ablation presence drift"
            )
        if self.terminal_ready:
            if self.recommendation not in {COMPLETED, FALSIFIED}:
                raise CiboCapitalManagementError(
                    "T02 terminal assessment terminal disposition invalid"
                )
            if self.waiting_reason is not None:
                raise CiboCapitalManagementError(
                    "T02 terminal assessment terminal result cannot wait"
                )
        else:
            if self.recommendation is not None:
                raise CiboCapitalManagementError(
                    "T02 non-terminal assessment cannot recommend terminal state"
                )
            if self.waiting_reason not in {
                WAITING_STRUCTURAL,
                WAITING_ABLATION,
            }:
                raise CiboCapitalManagementError(
                    "T02 non-terminal assessment waiting reason invalid"
                )
        if self.canonical_ledger_modified or self.productive_authority:
            raise CiboCapitalManagementError(
                "T02 terminal assessment exceeded Architect-2 authority"
            )


def assess_t02_terminal_disposition(
    *,
    structural: T02ForwardStructuralAudit,
    economic: T02EconomicAblationResult | None,
) -> T02TerminalDispositionAssessment:
    if not isinstance(structural, T02ForwardStructuralAudit):
        raise CiboCapitalManagementError(
            "T02 terminal assessment requires canonical structural audit"
        )
    if economic is not None and not isinstance(economic, T02EconomicAblationResult):
        raise CiboCapitalManagementError(
            "T02 terminal assessment requires canonical economic ablation"
        )

    population_sufficient = bool(structural.lineages) and all(
        item.minimum_sample_met and item.provider_binding_complete
        for item in structural.lineages
    )

    if not population_sufficient:
        if economic is not None:
            raise CiboCapitalManagementError(
                "T02 economic ablation cannot precede sufficient structural population"
            )
        return T02TerminalDispositionAssessment(
            structural_population_sufficient=False,
            structural_precision_passed=False,
            economic_ablation_present=False,
            economic_ablation_passed=None,
            terminal_ready=False,
            recommendation=None,
            waiting_reason=WAITING_STRUCTURAL,
        )

    if not structural.fresh_structural_precision_demonstrated:
        if economic is not None:
            raise CiboCapitalManagementError(
                "T02 failed structural gate cannot consume economic ablation"
            )
        return T02TerminalDispositionAssessment(
            structural_population_sufficient=True,
            structural_precision_passed=False,
            economic_ablation_present=False,
            economic_ablation_passed=None,
            terminal_ready=True,
            recommendation=FALSIFIED,
            waiting_reason=None,
        )

    if economic is None:
        return T02TerminalDispositionAssessment(
            structural_population_sufficient=True,
            structural_precision_passed=True,
            economic_ablation_present=False,
            economic_ablation_passed=None,
            terminal_ready=False,
            recommendation=None,
            waiting_reason=WAITING_ABLATION,
        )

    passed = economic.provider_bound_economic_value_proven
    return T02TerminalDispositionAssessment(
        structural_population_sufficient=True,
        structural_precision_passed=True,
        economic_ablation_present=True,
        economic_ablation_passed=passed,
        terminal_ready=True,
        recommendation=COMPLETED if passed else FALSIFIED,
        waiting_reason=None,
    )
