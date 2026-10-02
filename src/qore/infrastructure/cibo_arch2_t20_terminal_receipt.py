"""Terminal receipt law for Architect-2 CE2I T20.

The underlying qualifier already enforces the frozen Phase20D population,
coverage, fold, lineage and exact capacity-reconciliation requirements.  This
module exposes the result as an Integrator-ready terminal recommendation without
mutating the canonical ledger.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_arch2_t20_forward_release_qualification import (
    TERMINAL_RECOMMENDATION,
    WAITING_RECOMMENDATION,
    T20ForwardReleaseQualification,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


@dataclass(frozen=True, slots=True)
class T20TerminalReceipt:
    candidate_rows: int
    complete_release_lifecycles: int
    release_coverage: str
    terminal_ready: bool
    recommendation: str | None
    waiting_reason: str | None
    canonical_ledger_modified: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.candidate_rows < 0 or self.complete_release_lifecycles < 0:
            raise CiboCapitalManagementError(
                "T20 terminal receipt counts invalid"
            )
        if self.terminal_ready:
            if self.recommendation != TERMINAL_RECOMMENDATION:
                raise CiboCapitalManagementError(
                    "T20 terminal receipt disposition drift"
                )
            if self.waiting_reason is not None:
                raise CiboCapitalManagementError(
                    "T20 terminal receipt cannot be terminal and waiting"
                )
        else:
            if self.recommendation is not None:
                raise CiboCapitalManagementError(
                    "T20 non-terminal receipt cannot recommend terminal state"
                )
            if self.waiting_reason != WAITING_RECOMMENDATION:
                raise CiboCapitalManagementError(
                    "T20 terminal receipt waiting reason drift"
                )
        if self.canonical_ledger_modified or self.productive_authority:
            raise CiboCapitalManagementError(
                "T20 terminal receipt exceeded Architect-2 authority"
            )


def build_t20_terminal_receipt(
    qualification: T20ForwardReleaseQualification,
) -> T20TerminalReceipt:
    if not isinstance(qualification, T20ForwardReleaseQualification):
        raise CiboCapitalManagementError(
            "T20 terminal receipt requires canonical qualification"
        )
    ready = qualification.empirical_t20_ready
    return T20TerminalReceipt(
        candidate_rows=qualification.manifest_candidate_rows,
        complete_release_lifecycles=qualification.complete_release_lifecycles,
        release_coverage=format(qualification.release_coverage, "f"),
        terminal_ready=ready,
        recommendation=TERMINAL_RECOMMENDATION if ready else None,
        waiting_reason=None if ready else WAITING_RECOMMENDATION,
        canonical_ledger_modified=False,
        productive_authority=False,
    )
