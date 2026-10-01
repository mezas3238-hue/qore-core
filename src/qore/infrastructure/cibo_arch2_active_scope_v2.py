"""Non-overlapping active scope for CIBO Architect 2 after the A1/A2 split.

This contract supersedes the earlier broad 43-workstream helper frontier for
new work. Historical files remain immutable evidence of the previous checkpoint.

Architect 2 now advances only unresolved external/B-side scientific fronts.
Architect A1, Architect A2 and the Integrator retain exclusive ownership of
their respective surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass


ARCHITECT_A1_OWNERSHIP = (
    "T04",
    "T06",
    "T07",
    "T08",
    "T09",
    "T10",
    "T12",
    "T13",
    "T14",
    "T15",
    "T18",
    "GEN-C2",
    "GEN-C3",
    "GEN-C4",
    "GEN-C5",
    "GEN-C6",
    "GEN-C7",
    "TEMPORAL_REPLICATION",
)

ARCHITECT_A2_OWNERSHIP = (
    "GEN-C8",
    "GEN-C9",
    "GEN-C10",
    "GEN-C11",
    "GEN-C12",
    "GEN-C13",
    "GEN-C14",
    "COMPOUND_ENGINE",
    "COMPOUND_PORTFOLIO",
    "INTERNAL_CAPITAL_MARKET",
    "CAPITAL_GENERATIONS",
    "PROTECTED_BASE_CAPITAL",
    "PROFIT_PROTECTION",
    "PATH_DEPENDENT_MONTE_CARLO",
    "ADVERSARIAL_STRESS",
    "CAPITAL_AMPLIFICATION",
    "AS_IS_ECONOMIC_BASELINE",
)

ARCHITECT2_ACTIVE_OWNERSHIP = (
    "T02",
    "T03",
    "T11",
    "T16",
    "T20",
    "PROVIDER_ECONOMICS",
    "FORWARD_QUALIFICATION",
    "FRESH_OOS",
)

INTEGRATOR_RESERVED_SURFACES = (
    "CANONICAL_MASTER_LEDGER",
    "PHASE22_ONE_SHOT_CONSUMPTION",
    "PHASE22_FINAL_EXECUTION",
    "USD60_GOVERNED_EXAM",
    "INTEGRATED_CAPITAL_TRUTH",
    "FINAL_INTEGRATED_CIBO_EXAM",
    "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
    "STRICT_ZERO_OPEN",
    "CERTIFICATION_SEAL",
)


@dataclass(frozen=True, slots=True)
class Architect2ActiveScope:
    workstreams: tuple[str, ...]
    architect_a1_ownership: tuple[str, ...]
    architect_a2_ownership: tuple[str, ...]
    integrator_reserved_surfaces: tuple[str, ...]
    canonical_ledger_mutation_allowed: bool = False
    phase22_consumption_allowed: bool = False
    merge_authority: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if len(self.workstreams) != len(set(self.workstreams)):
            raise ValueError("Architect-2 active workstreams must be unique")
        if set(self.workstreams) & set(self.architect_a1_ownership):
            raise ValueError("Architect-2 scope overlaps Architect A1")
        if set(self.workstreams) & set(self.architect_a2_ownership):
            raise ValueError("Architect-2 scope overlaps Architect A2")
        if any(
            (
                self.canonical_ledger_mutation_allowed,
                self.phase22_consumption_allowed,
                self.merge_authority,
                self.productive_authority,
            )
        ):
            raise ValueError("Architect-2 active scope exceeded authority boundary")


ARCHITECT2_ACTIVE_SCOPE = Architect2ActiveScope(
    workstreams=ARCHITECT2_ACTIVE_OWNERSHIP,
    architect_a1_ownership=ARCHITECT_A1_OWNERSHIP,
    architect_a2_ownership=ARCHITECT_A2_OWNERSHIP,
    integrator_reserved_surfaces=INTEGRATOR_RESERVED_SURFACES,
)
