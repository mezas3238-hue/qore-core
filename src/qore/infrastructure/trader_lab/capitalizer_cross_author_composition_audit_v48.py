"""V48 cross-author composition audit for Capitalizer.

Individual provenance does not prove conjunction provenance. A rule supported by ICT and a
different rule supported by TTrades may both be valid facts while the requirement to satisfy
both simultaneously remains a QORE synthesis.

V48 therefore distinguishes SOURCE_REQUIREMENT from QORE_COMPOSITION.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

IDENTITY = "QORE_CAPITALIZER_V48_CROSS_AUTHOR_COMPOSITION_AUDIT"


class V48CompositionAuthority(StrEnum):
    AUTHOR_EXPLICIT = "AUTHOR_EXPLICIT"
    AUTHOR_STRONGLY_IMPLIED = "AUTHOR_STRONGLY_IMPLIED"
    QORE_SYNTHESIS = "QORE_SYNTHESIS"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True, slots=True)
class V48CompositionClaim:
    claim_id: str
    authority: V48CompositionAuthority
    statement: str
    source_families: tuple[str, ...]
    may_be_universal_hard_gate: bool

    def __post_init__(self) -> None:
        if not self.claim_id or self.claim_id != self.claim_id.upper():
            raise ValueError("claim_id must be non-empty uppercase")
        if not self.statement or not self.source_families:
            raise ValueError("composition claim requires statement and source families")
        if (
            self.authority in {
                V48CompositionAuthority.QORE_SYNTHESIS,
                V48CompositionAuthority.UNRESOLVED,
            }
            and self.may_be_universal_hard_gate
        ):
            raise ValueError("QORE synthesis/unresolved composition cannot be source-mandatory")


CLAIMS: tuple[V48CompositionClaim, ...] = (
    V48CompositionClaim(
        claim_id="ICT_2022_LIQUIDITY_MSS_DISPLACEMENT_FVG_SEQUENCE",
        authority=V48CompositionAuthority.AUTHOR_EXPLICIT,
        statement=(
            "The retained ICT 2022 source family supports a liquidity-run, structure-shift/"
            "displacement and fair-value-gap execution sequence within that ICT model family."
        ),
        source_families=("ICT_2022",),
        may_be_universal_hard_gate=False,
    ),
    V48CompositionClaim(
        claim_id="TTRADES_FRACTAL_CISD_PROTECTED_SWING_SEQUENCE",
        authority=V48CompositionAuthority.AUTHOR_EXPLICIT,
        statement=(
            "TTrades supports higher-timeframe context followed by lower-timeframe CISD/"
            "protected-swing continuation within its fractal model family."
        ),
        source_families=("TTRADES_FRACTAL",),
        may_be_universal_hard_gate=False,
    ),
    V48CompositionClaim(
        claim_id="EVERY_TRADE_MUST_PASS_FULL_ICT_AND_FULL_TTRADES",
        authority=V48CompositionAuthority.QORE_SYNTHESIS,
        statement=(
            "The requirement that every Capitalizer candidate simultaneously satisfy the full "
            "ICT execution inventory and the full TTrades refinement inventory is a QORE "
            "composition. V48 has not found an author source that declares this conjunction."
        ),
        source_families=("ICT_2022", "TTRADES_FRACTAL", "QORE"),
        may_be_universal_hard_gate=False,
    ),
    V48CompositionClaim(
        claim_id="M1_MSS_FVG_OB_ALL_REQUIRED_AFTER_TTRADES_CONFIRMATION",
        authority=V48CompositionAuthority.QORE_SYNTHESIS,
        statement=(
            "The mandatory M1 MSS AND FVG AND Order Block triad layered after TTrades "
            "confirmation is not established as a universal author requirement by the V48 "
            "source pack; TTrades presents multiple execution techniques and entry models."
        ),
        source_families=("TTRADES", "QORE"),
        may_be_universal_hard_gate=False,
    ),
    V48CompositionClaim(
        claim_id="SESSION_SPECIFIC_ROUTE_SELECTION",
        authority=V48CompositionAuthority.AUTHOR_EXPLICIT,
        statement=(
            "TTrades source material distinguishes session/timeframe structures and, for Asia, "
            "explicitly offers positional OR 4H/15M execution routes."
        ),
        source_families=("TTRADES",),
        may_be_universal_hard_gate=False,
    ),
)


@dataclass(frozen=True, slots=True)
class V48CrossAuthorCompositionAudit:
    identity: str = IDENTITY
    claims: tuple[V48CompositionClaim, ...] = CLAIMS
    conjunction_requires_own_provenance: bool = True
    qore_synthesis_may_masquerade_as_author_rule: bool = False
    fresh_holdout_authorized: bool = False
    economics_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V48 composition audit identity is frozen")
        claim_ids = tuple(claim.claim_id for claim in self.claims)
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("composition claim IDs must be unique")
        if not self.conjunction_requires_own_provenance:
            raise ValueError("V48 requires provenance for the conjunction itself")
        if self.qore_synthesis_may_masquerade_as_author_rule:
            raise ValueError("QORE synthesis cannot masquerade as author methodology")
        if self.fresh_holdout_authorized or self.economics_authorized:
            raise ValueError("composition audit is pre-economic")


V48_CROSS_AUTHOR_COMPOSITION_AUDIT = V48CrossAuthorCompositionAudit()
