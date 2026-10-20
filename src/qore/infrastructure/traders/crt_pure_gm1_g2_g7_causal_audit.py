"""Causal G2 reference-conflict and G7 rearm audit for VT08 CRT (research-only).

QORE proposed rules under owner-authorized three-source synthesis: NOT signed
source methodology, NOT production strategy, NOT a trade/entry signal. The
frozen V1/V2/V3 generators and price outcomes are intentionally untouched.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)

_SHA256 = re.compile(r"^[a-f0-9]{64}$")


class CrtGm1CausalVerdict(StrEnum):
    WAIT = "WAIT"
    ABSTAIN = "ABSTAIN"
    PROVISIONAL = "PROVISIONAL"


@dataclass(frozen=True, slots=True)
class CrtGm1Reference:
    """Immutable point-in-time source identity; no price-outcome or PnL fields."""

    market: CrtPureMarket
    reference_id: str
    parent_id: str
    direction: CrtPureCandidateDirection
    closed_at: datetime
    discovered_at: datetime
    evidence_sha256: str

    def __post_init__(self) -> None:
        if not self.reference_id or not self.parent_id:
            raise ValueError("G2 reference and parent identity required")
        _require_aware(self.closed_at)
        _require_aware(self.discovered_at)
        if self.closed_at > self.discovered_at:
            raise ValueError("G2 reference cannot be discovered before close")
        if not _SHA256.fullmatch(self.evidence_sha256):
            raise ValueError("G2 source evidence must have SHA256 provenance")


@dataclass(frozen=True, slots=True)
class CrtGm1G2Assessment:
    verdict: CrtGm1CausalVerdict
    reasons: tuple[str, ...]
    selected_reference_id: str | None
    candidates_considered: int
    grants_execution_authority: bool = False
    grants_capital_authority: bool = False


def _require_aware(t: datetime) -> None:
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("G-M1 causal timestamps must be timezone-aware")


def audit_g2_reference_conflicts(
    *,
    market: CrtPureMarket,
    parent_id: str,
    decision_at: datetime,
    references: tuple[CrtGm1Reference, ...],
    inventory_complete: bool,
) -> CrtGm1G2Assessment:
    """No learned ranking. Ambiguity => ABSTAIN, incomplete census => WAIT.

    Only a unique closed, discovered, SHA-bound reference can be provisionally
    selected. inventory_complete is a RESEARCH CLAIM, not independent evidence
    of coverage and never authorizes execution.
    """
    _require_aware(decision_at)
    if not parent_id:
        raise ValueError("G2 parent identity missing")
    if any(r.market != market for r in references):
        raise ValueError("cross-market reference not admissible")
    if any(r.parent_id != parent_id for r in references):
        raise ValueError("cross-parent reference not admissible")
    if len({r.reference_id for r in references}) != len(references):
        raise ValueError("duplicate reference identity")
    if any(r.closed_at > decision_at or r.discovered_at > decision_at for r in references):
        raise ValueError("future reference cannot enter decision prefix")
    if not inventory_complete:
        return CrtGm1G2Assessment(
            CrtGm1CausalVerdict.WAIT,
            ("REFERENCE_INVENTORY_INCOMPLETE", "NO_PNL_PRIORITY_FALLBACK"),
            None, len(references),
        )
    if not references:
        return CrtGm1G2Assessment(
            CrtGm1CausalVerdict.WAIT,
            ("NO_SOURCE_REFERENCE_OBSERVED",), None, 0,
        )
    if len(references) > 1:
        return CrtGm1G2Assessment(
            CrtGm1CausalVerdict.ABSTAIN,
            ("MULTIPLE_REFERENCE_PRIORITY_NOT_ADJUDICATED", "NO_RETROSPECTIVE_SELECTION"),
            None, len(references),
        )
    return CrtGm1G2Assessment(
        CrtGm1CausalVerdict.PROVISIONAL,
        ("UNIQUE_CAUSAL_REFERENCE_ONLY", "G_M1_APPROVAL_STILL_REQUIRED"),
        references[0].reference_id,
        1,
    )


@dataclass(frozen=True, slots=True)
class CrtGm1SourceEvent:
    """One source event and hypothesis, with explicitly recorded generation."""

    market: CrtPureMarket
    parent_id: str
    source_event_id: str
    hypothesis_id: str
    event_generation: int
    observed_at: datetime
    decision_at: datetime
    terminal_observed_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.parent_id or not self.source_event_id or not self.hypothesis_id:
            raise ValueError("G7 parent/source/hypothesis identity missing")
        if self.event_generation < 1:
            raise ValueError("G7 generation must be positive")
        _require_aware(self.observed_at)
        _require_aware(self.decision_at)
        if self.observed_at > self.decision_at:
            raise ValueError("G7 source cannot be observed after decision")
        if self.terminal_observed_at is not None:
            _require_aware(self.terminal_observed_at)
            if self.terminal_observed_at < self.decision_at:
                raise ValueError("G7 terminal observation predates decision")


@dataclass(frozen=True, slots=True)
class CrtGm1G7Assessment:
    verdict: CrtGm1CausalVerdict
    reasons: tuple[str, ...]
    event_generation: int
    grants_rearm_authority: bool = False
    grants_execution_authority: bool = False
    grants_capital_authority: bool = False


def audit_g7_rearm(
    *,
    proposal: CrtGm1SourceEvent,
    observed_history: tuple[CrtGm1SourceEvent, ...],
) -> CrtGm1G7Assessment:
    """Retired parent/source/hypothesis cannot be reused to chase a result.

    History must be a causal, complete-for-claim ledger; this pure audit
    cannot prove external custody. A fresh event can be PROVISIONAL only,
    never authorized re-entry, execution or capital.
    """
    if any(x.market != proposal.market for x in observed_history):
        raise ValueError("cross-market G7 history must be isolated")
    if len({x.source_event_id for x in observed_history}) != len(observed_history):
        raise ValueError("duplicate G7 source identity in history")
    if len({x.hypothesis_id for x in observed_history}) != len(observed_history):
        raise ValueError("duplicate G7 hypothesis identity in history")
    if len({x.parent_id for x in observed_history}) != len(observed_history):
        raise ValueError("duplicate G7 parent event in history")
    if any(x.decision_at >= proposal.decision_at for x in observed_history):
        raise ValueError("noncausal G7 history includes decision or future")
    if any(
        a.decision_at >= b.decision_at
        or a.event_generation >= b.event_generation
        for a, b in zip(observed_history, observed_history[1:], strict=False)
    ):
        raise ValueError("G7 history is not chronologically monotonic")
    if not observed_history:
        return CrtGm1G7Assessment(
            CrtGm1CausalVerdict.PROVISIONAL,
            ("FIRST_CAUSAL_SOURCE_EVENT", "NO_REENTRY_CERTIFICATE"),
            proposal.event_generation,
        )
    if any(x.parent_id == proposal.parent_id for x in observed_history):
        return CrtGm1G7Assessment(
            CrtGm1CausalVerdict.ABSTAIN,
            ("H4_PARENT_ALREADY_USED", "NO_SAME_PARENT_FALLBACK"),
            proposal.event_generation,
        )
    if any(
        x.source_event_id == proposal.source_event_id
        or x.hypothesis_id == proposal.hypothesis_id
        for x in observed_history
    ):
        return CrtGm1G7Assessment(
            CrtGm1CausalVerdict.ABSTAIN,
            ("SOURCE_OR_HYPOTHESIS_REPLAY",),
            proposal.event_generation,
        )
    last = observed_history[-1]
    if proposal.event_generation <= last.event_generation:
        return CrtGm1G7Assessment(
            CrtGm1CausalVerdict.ABSTAIN,
            ("NONMONOTONIC_EVENT_GENERATION",),
            proposal.event_generation,
        )
    if proposal.observed_at <= last.decision_at:
        return CrtGm1G7Assessment(
            CrtGm1CausalVerdict.ABSTAIN,
            ("SOURCE_EVENT_NOT_NEW_AFTER_PRIOR_DECISION",),
            proposal.event_generation,
        )
    if any(
        prior.terminal_observed_at is not None
        and prior.terminal_observed_at > proposal.decision_at
        for prior in observed_history
    ):
        raise ValueError("future terminal evidence not admissible to G7 prefix")
    if any(
        prior.terminal_observed_at is None
        or prior.terminal_observed_at >= proposal.observed_at
        for prior in observed_history
    ):
        return CrtGm1G7Assessment(
            CrtGm1CausalVerdict.WAIT,
            ("PRIOR_THESIS_NOT_TERMINAL_BEFORE_NEW_SOURCE",),
            proposal.event_generation,
        )
    return CrtGm1G7Assessment(
        CrtGm1CausalVerdict.PROVISIONAL,
        ("NEW_PARENT_AND_SOURCE_CAUSALLY_OBSERVED", "G_M1_APPROVAL_STILL_REQUIRED"),
        proposal.event_generation,
    )
