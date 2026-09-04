"""CIBO Cognitive multi-scenario mental simulation substrate (CA strengthening 3.2).

Typed, immutable, replay-safe scenario families (base / adverse / extreme /
regime-change) that model plausible alternatives WITHOUT treating simulations as
facts. Hypothetical state is separated from observed fact, scenarios bind to
observed world-model snapshots by exact ``(id, fingerprint)``, alternatives are
comparable or the scenario abstains, uncertainty is explicit, and no fabricated
probability is ever manufactured. Scenario output is advisory cognition only.

Laws honoured: hypothetical != observed; no hidden clock/RNG; deterministic
ordering + self-fingerprints; exact runtime types; secret-bearing strings fail
closed; no global mutable state; no authority transfer.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from re import compile
from uuid import UUID

from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveError,
    CiboCognitiveFingerprint,
    CiboCognitiveValidationError,
    contains_secret_material,
    fingerprint_material,
    require_exact_str,
)
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveValidationError as CiboContractsValidationError,
)
from qore.modules.cibo.cognitive_contracts import CiboUncertainty

_CODE_RE = r"[a-z][a-z0-9._-]*"
_VERSION_RE = r"[0-9A-Za-z._-]{1,128}"


class ScenarioError(CiboCognitiveError):
    """Base error for the CIBO cognitive scenario substrate."""

    __slots__ = ()


class ScenarioValidationError(ScenarioError, CiboCognitiveValidationError):
    """A scenario violates a deterministic simulation-integrity invariant."""

    __slots__ = ()


class ScenarioFamily(StrEnum):
    """Required scenario families."""

    BASE = "base"
    ADVERSE = "adverse"
    EXTREME = "extreme"
    REGIME_CHANGE = "regime-change"


class ScenarioFactKind(StrEnum):
    """Separates observed fact from hypothetical state."""

    OBSERVED = "observed"
    HYPOTHETICAL = "hypothetical"


def _validate_code(value: object, *, field: str) -> str:
    text = require_exact_str(value, field=field)
    if compile(_CODE_RE).fullmatch(text) is None:
        raise ScenarioValidationError(
            f"{field} must use canonical lowercase code syntax"
        )
    if contains_secret_material(text):
        raise ScenarioValidationError(f"{field} must not carry secret-bearing material")
    return text


def _validate_version(value: object, *, field: str) -> str:
    text = require_exact_str(value, field=field)
    if compile(_VERSION_RE).fullmatch(text) is None:
        raise ScenarioValidationError(
            f"{field} must be a non-blank token of letters, digits, dot, underscore or hyphen"
        )
    if contains_secret_material(text):
        raise ScenarioValidationError(f"{field} must not carry secret-bearing material")
    return text


def _canonical_codes(values: tuple[str, ...], *, field: str) -> tuple[str, ...]:
    if type(values) is not tuple or any(type(v) is not str for v in values):
        raise ScenarioValidationError(f"{field} must be an immutable tuple of strings")
    normalized = tuple(_validate_code(v, field=field) for v in values)
    if len(set(normalized)) != len(normalized):
        raise ScenarioValidationError(f"{field} must not contain duplicates")
    return tuple(sorted(normalized))


@dataclass(frozen=True, slots=True)
class ScenarioAssumption:
    """One typed scenario assumption, observed or hypothetical."""

    code: str
    fact_kind: ScenarioFactKind

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        object.__setattr__(self, "code", _validate_code(self.code, field="assumption"))
        if type(self.fact_kind) is not ScenarioFactKind:
            raise ScenarioValidationError(
                "assumption fact kind must be a ScenarioFactKind"
            )

    def logical_values(self) -> tuple[str, str]:
        return (self.code, self.fact_kind.value)

    def sort_key(self) -> tuple[str, str]:
        return (self.code, self.fact_kind.value)


@dataclass(frozen=True, slots=True)
class ScenarioAlternative:
    """One comparable hypothetical alternative (never observed fact)."""

    alternative_id: UUID
    action_code: str
    outcome_code: str

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.alternative_id) is not UUID:
            raise ScenarioValidationError("alternative id must be a UUID")
        object.__setattr__(
            self, "action_code", _validate_code(self.action_code, field="alternative action")
        )
        object.__setattr__(
            self, "outcome_code", _validate_code(self.outcome_code, field="alternative outcome")
        )

    def logical_values(self) -> tuple[object, ...]:
        return (str(self.alternative_id), self.action_code, self.outcome_code)

    def sort_key(self) -> tuple[object, ...]:
        return (self.action_code, self.outcome_code, str(self.alternative_id))


def _canonical_assumptions(
    values: tuple[ScenarioAssumption, ...], *, field: str
) -> tuple[ScenarioAssumption, ...]:
    if type(values) is not tuple or any(type(v) is not ScenarioAssumption for v in values):
        raise ScenarioValidationError(
            f"{field} must be an immutable tuple of ScenarioAssumption"
        )
    for assumption in values:
        assumption.revalidate()
    if len({a.code for a in values}) != len(values):
        raise ScenarioValidationError(f"{field} must not contain duplicate codes")
    return tuple(sorted(values, key=lambda a: a.sort_key()))


def _canonical_alternatives(
    values: tuple[ScenarioAlternative, ...], *, field: str
) -> tuple[ScenarioAlternative, ...]:
    if type(values) is not tuple or any(type(v) is not ScenarioAlternative for v in values):
        raise ScenarioValidationError(
            f"{field} must be an immutable tuple of ScenarioAlternative"
        )
    for alternative in values:
        alternative.revalidate()
    if len({a.alternative_id for a in values}) != len(values):
        raise ScenarioValidationError(f"{field} must not contain duplicate ids")
    return tuple(sorted(values, key=lambda a: a.sort_key()))


@dataclass(frozen=True, slots=True)
class Scenario:
    """One immutable, replay-safe cognitive scenario."""

    scenario_id: UUID
    family: ScenarioFamily
    version: str
    assumptions: tuple[ScenarioAssumption, ...]
    world_snapshot_id: UUID | None
    world_fingerprint: CiboCognitiveFingerprint | None
    alternatives: tuple[ScenarioAlternative, ...]
    abstained: bool
    uncertainty: CiboUncertainty
    limitations: tuple[str, ...]
    supersedes: UUID | None
    fingerprint: CiboCognitiveFingerprint

    def __post_init__(self) -> None:
        self.revalidate()

    def revalidate(self) -> None:
        if type(self.scenario_id) is not UUID:
            raise ScenarioValidationError("scenario id must be a UUID")
        if type(self.family) is not ScenarioFamily:
            raise ScenarioValidationError("scenario family must be a ScenarioFamily")
        object.__setattr__(
            self, "version", _validate_version(self.version, field="scenario version")
        )
        object.__setattr__(
            self, "assumptions", _canonical_assumptions(self.assumptions, field="assumptions")
        )
        if self.world_snapshot_id is not None and type(self.world_snapshot_id) is not UUID:
            raise ScenarioValidationError("world snapshot id must be a UUID or None")
        if self.world_fingerprint is not None:
            if type(self.world_fingerprint) is not CiboCognitiveFingerprint:
                raise ScenarioValidationError(
                    "world fingerprint must be a CiboCognitiveFingerprint or None"
                )
            self.world_fingerprint.revalidate()
        if (self.world_snapshot_id is None) != (self.world_fingerprint is None):
            raise ScenarioValidationError(
                "world snapshot id and fingerprint must be bound together"
            )
        # Every observed assumption must be bound to an observed world snapshot.
        if any(a.fact_kind is ScenarioFactKind.OBSERVED for a in self.assumptions):
            if self.world_snapshot_id is None:
                raise ScenarioValidationError(
                    "an observed assumption requires a bound world snapshot"
                )
        object.__setattr__(
            self,
            "alternatives",
            _canonical_alternatives(self.alternatives, field="alternatives"),
        )
        if type(self.abstained) is not bool:
            raise ScenarioValidationError("abstained must be an exact bool")
        if self.abstained and self.alternatives:
            raise ScenarioValidationError(
                "an abstained scenario must not carry alternatives"
            )
        if type(self.uncertainty) is not CiboUncertainty:
            raise ScenarioValidationError("scenario requires CiboUncertainty")
        try:
            self.uncertainty.revalidate()
        except CiboContractsValidationError as error:
            raise ScenarioValidationError(
                "scenario uncertainty failed revalidation"
            ) from error
        object.__setattr__(
            self, "limitations", _canonical_codes(self.limitations, field="limitations")
        )
        if self.supersedes is not None and type(self.supersedes) is not UUID:
            raise ScenarioValidationError("scenario supersedes must be a UUID or None")
        if self.supersedes == self.scenario_id:
            raise ScenarioValidationError("a scenario must not supersede itself")
        if type(self.fingerprint) is not CiboCognitiveFingerprint:
            raise ScenarioValidationError(
                "scenario fingerprint must be a CiboCognitiveFingerprint"
            )
        self.fingerprint.revalidate()
        if self.fingerprint != fingerprint_material(self.logical_values()):
            raise ScenarioValidationError(
                "scenario fingerprint does not match its canonical content"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.scenario_id),
            self.family.value,
            self.version,
            tuple(a.logical_values() for a in self.assumptions),
            None if self.world_snapshot_id is None else str(self.world_snapshot_id),
            None if self.world_fingerprint is None else self.world_fingerprint.value,
            tuple(a.logical_values() for a in self.alternatives),
            self.abstained,
            self.uncertainty.logical_values(),
            self.limitations,
            None if self.supersedes is None else str(self.supersedes),
        )


def build_scenario(
    *,
    scenario_id: UUID,
    family: ScenarioFamily,
    version: str,
    assumptions: Sequence[ScenarioAssumption] = (),
    world_snapshot_id: UUID | None = None,
    world_fingerprint: CiboCognitiveFingerprint | None = None,
    alternatives: Sequence[ScenarioAlternative] = (),
    abstained: bool = False,
    uncertainty: CiboUncertainty,
    limitations: Sequence[str] = (),
    supersedes: UUID | None = None,
) -> Scenario:
    """Build a validated, canonically ordered, fingerprinted scenario."""
    if not isinstance(assumptions, Sequence):
        raise ScenarioValidationError("assumptions must be a sequence")
    if not isinstance(alternatives, Sequence):
        raise ScenarioValidationError("alternatives must be a sequence")
    if not isinstance(limitations, Sequence):
        raise ScenarioValidationError("limitations must be a sequence")
    # Canonicalize every semantically-unordered sequence BEFORE deriving the
    # fingerprint, so any permutation of the same semantic input produces the
    # same canonical state and fingerprint (constructor == revalidate).
    canonical_assumptions = _canonical_assumptions(tuple(assumptions), field="assumptions")
    canonical_alternatives = _canonical_alternatives(tuple(alternatives), field="alternatives")
    canonical_limitations = _canonical_codes(tuple(limitations), field="limitations")
    return Scenario(
        scenario_id=scenario_id,
        family=family,
        version=version,
        assumptions=canonical_assumptions,
        world_snapshot_id=world_snapshot_id,
        world_fingerprint=world_fingerprint,
        alternatives=canonical_alternatives,
        abstained=abstained,
        uncertainty=uncertainty,
        limitations=canonical_limitations,
        supersedes=supersedes,
        fingerprint=fingerprint_material(
            _scenario_material(
                scenario_id,
                family,
                version,
                canonical_assumptions,
                world_snapshot_id,
                world_fingerprint,
                canonical_alternatives,
                abstained,
                uncertainty,
                canonical_limitations,
                supersedes,
            )
        ),
    )


def _scenario_material(
    scenario_id: UUID,
    family: ScenarioFamily,
    version: str,
    assumptions: tuple[ScenarioAssumption, ...],
    world_snapshot_id: UUID | None,
    world_fingerprint: CiboCognitiveFingerprint | None,
    alternatives: tuple[ScenarioAlternative, ...],
    abstained: bool,
    uncertainty: CiboUncertainty,
    limitations: tuple[str, ...],
    supersedes: UUID | None,
) -> tuple[object, ...]:
    return (
        str(scenario_id),
        family.value,
        version,
        tuple(a.logical_values() for a in assumptions),
        None if world_snapshot_id is None else str(world_snapshot_id),
        None if world_fingerprint is None else world_fingerprint.value,
        tuple(a.logical_values() for a in alternatives),
        abstained,
        uncertainty.logical_values(),
        limitations,
        None if supersedes is None else str(supersedes),
    )


def assert_scenario_lineage_acyclic(scenarios: Sequence[Scenario]) -> None:
    """Raise if the ``supersedes`` graph among scenarios contains a cycle."""
    if not isinstance(scenarios, Sequence):
        raise ScenarioValidationError("scenarios must be a sequence")
    by_id: dict[UUID, Scenario] = {}
    for scenario in scenarios:
        if type(scenario) is not Scenario:
            raise ScenarioValidationError("scenarios must contain only Scenario values")
        scenario.revalidate()
        if scenario.scenario_id in by_id:
            raise ScenarioValidationError("scenarios must have unique ids")
        by_id[scenario.scenario_id] = scenario

    visiting: set[UUID] = set()
    visited: set[UUID] = set()

    def visit(node: UUID) -> None:
        if node in visiting:
            raise ScenarioValidationError("scenario supersession lineage must be acyclic")
        if node in visited:
            return
        visiting.add(node)
        supersedes = by_id[node].supersedes
        if supersedes is not None and supersedes in by_id:
            visit(supersedes)
        visiting.remove(node)
        visited.add(node)

    for scenario_id in by_id:
        visit(scenario_id)


__all__ = [
    "Scenario",
    "ScenarioAlternative",
    "ScenarioAssumption",
    "ScenarioError",
    "ScenarioFactKind",
    "ScenarioFamily",
    "ScenarioValidationError",
    "assert_scenario_lineage_acyclic",
    "build_scenario",
]
