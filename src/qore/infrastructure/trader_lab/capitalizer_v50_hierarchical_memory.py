"""V50.1 hierarchical cognitive-memory representation contract.

This module is architecture-only. It does not evaluate outcomes or decide trades.

The V50 development atlas exposed a representation defect: SYMBOL and SESSION were stored both
as context and as evidence tokens, allowing memory to learn coarse conclusions such as
"SESSION=LONDON is negative". V50.1 separates:

- context identity: symbol, session, market/session scope;
- causal evidence: freshness, execution timing, geometry, destination, trigger/basis,
  new-causal-event state, target availability and portfolio slot state;
- derived dispositions: metadata only, never independent causal evidence.

No threshold or admission policy is defined here.
"""

from __future__ import annotations

from dataclasses import dataclass

IDENTITY = "QORE_CAPITALIZER_V50_1_HIERARCHICAL_MEMORY_REPRESENTATION"

_CONTEXT_PREFIXES = ("SYMBOL=", "SESSION=")
_DERIVED_PREFIXES = ("STRUCTURAL_DISPOSITION=",)


@dataclass(frozen=True, slots=True)
class V501MemoryRepresentation:
    identity: str
    symbol: str
    session: str
    context_tokens: tuple[str, ...]
    evidence_tokens: tuple[str, ...]
    derived_tokens: tuple[str, ...]
    outcome_visible: bool = False
    admission_decision_made: bool = False
    rule_promotion_allowed: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("unexpected V50.1 memory representation identity")
        if not self.symbol or not self.session:
            raise ValueError("V50.1 memory context requires symbol/session")
        if self.outcome_visible:
            raise ValueError("V50.1 representation cannot see outcome")
        if self.admission_decision_made:
            raise ValueError("V50.1 representation is not an admission policy")
        if self.rule_promotion_allowed:
            raise ValueError("V50.1 representation cannot self-promote")
        if any(
            token.startswith(_CONTEXT_PREFIXES)
            for token in self.evidence_tokens
        ):
            raise ValueError("identity/context token leaked into causal evidence")
        if any(
            token.startswith(_DERIVED_PREFIXES)
            for token in self.evidence_tokens
        ):
            raise ValueError("derived disposition leaked into causal evidence")


def separate_memory_representation(
    *,
    symbol: str,
    session: str,
    tokens: tuple[str, ...],
) -> V501MemoryRepresentation:
    """Separate context, causal evidence and derived metadata deterministically."""

    context: list[str] = []
    evidence: list[str] = []
    derived: list[str] = []
    for token in tokens:
        if token.startswith(_CONTEXT_PREFIXES):
            context.append(token)
        elif token.startswith(_DERIVED_PREFIXES):
            derived.append(token)
        else:
            evidence.append(token)

    canonical_context = tuple(sorted(set(context)))
    canonical_evidence = tuple(sorted(set(evidence)))
    canonical_derived = tuple(sorted(set(derived)))
    return V501MemoryRepresentation(
        identity=IDENTITY,
        symbol=symbol,
        session=session,
        context_tokens=canonical_context,
        evidence_tokens=canonical_evidence,
        derived_tokens=canonical_derived,
    )
