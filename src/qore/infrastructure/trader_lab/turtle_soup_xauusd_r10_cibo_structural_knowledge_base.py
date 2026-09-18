"""Evidence-bound structural knowledge base for Turtle Soup XAUUSD.

This module is the research memory used by the R10 Journey Intelligence layer.
It records what consumed evidence has established, what is only a clue, and
what remains unresolved. It deliberately does not convert historical outcomes
into a score, probability, order, or capital authorization.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

IDENTITY = "TURTLE_SOUP_XAUUSD_R10_CIBO_STRUCTURAL_KNOWLEDGE_BASE_V1"


class KnowledgeStrength(StrEnum):
    ESTABLISHED_STRUCTURAL_NEGATIVE = "ESTABLISHED_STRUCTURAL_NEGATIVE"
    ESTABLISHED_DIAGNOSTIC = "ESTABLISHED_DIAGNOSTIC"
    STABLE_CLUE_NOT_RULE = "STABLE_CLUE_NOT_RULE"
    INSUFFICIENT_STANDALONE = "INSUFFICIENT_STANDALONE"
    CONFLICTED = "CONFLICTED"
    UNRESOLVED = "UNRESOLVED"


class OperatingUse(StrEnum):
    STRUCTURAL_ABSTENTION_ALLOWED = "STRUCTURAL_ABSTENTION_ALLOWED"
    REASONING_CONTEXT_ONLY = "REASONING_CONTEXT_ONLY"
    NO_OPERATING_USE = "NO_OPERATING_USE"


@dataclass(frozen=True)
class EvidenceRef:
    code: str
    run_id: int
    artifact_id: int
    digest: str


@dataclass(frozen=True)
class StructuralKnowledgeClaim:
    code: str
    subject: str
    statement: str
    strength: KnowledgeStrength
    operating_use: OperatingUse
    evidence: tuple[EvidenceRef, ...]
    limitations: tuple[str, ...] = ()


R9_CAUSAL = EvidenceRef(
    code="R9_CAUSAL_BREAK_DISCRIMINATOR",
    run_id=35274286150,
    artifact_id=10518674739,
    digest="sha256:a445b550a09e75050bc7bc11764c7f72db51d74485df14427e87022d1c765254",
)
R9_PATH = EvidenceRef(
    code="R9_JOURNEY_DIVERGENCE_FORENSICS",
    run_id=35275016846,
    artifact_id=10520147121,
    digest="sha256:813d0a6ee79aa16d45ef0d872b3905773e1800a5fcf32b207473a7b8751a9054",
)
R9_LIQUIDITY = EvidenceRef(
    code="R9_LIQUIDITY_SIGNIFICANCE_FORENSICS",
    run_id=35275461733,
    artifact_id=10520471534,
    digest="sha256:aba7a747488487c7bee744ba04783d64f14dce65b167b6b7cd97af15dfdd61a2",
)
R9_CISD = EvidenceRef(
    code="R9_CISD_SEQUENCE_FORENSICS",
    run_id=35275903599,
    artifact_id=10520337279,
    digest="sha256:b623b7cd9a895c631d0a63633f94c64760d2400c6e58e1fc89a83097bc2e448f",
)
R10_PS = EvidenceRef(
    code="R10_PROTECTED_SWING_CAUSALITY_FORENSICS",
    run_id=35280108784,
    artifact_id=10521797296,
    digest="sha256:d42df4bb01f761853ccce0245f91659a65ba7b5ea66e2758f9b436f04218f110",
)
R10_INTELLIGENCE = EvidenceRef(
    code="R10_JOURNEY_INTELLIGENCE_CONTRACT",
    run_id=35279661372,
    artifact_id=10521449973,
    digest="sha256:84f1bb1962a2009f9f5cbb29fec59ea6098662d61f3c4fbed3c910522bdcade5",
)


R10_MEMORY_ATLAS = EvidenceRef(
    code="R10_CAUSAL_MEMORY_TRANSFER_ATLAS",
    run_id=35280678425,
    artifact_id=10522826606,
    digest="sha256:c5ca6976877e53ceb797cc81e6a1e12e94b8d38ae4fd38b4a55e91f3d67baeaa",
)

R11_RECOGNITION = EvidenceRef(
    code="R11_SITUATION_RECOGNITION_ENGINE_AUDIT",
    run_id=35282212625,
    artifact_id=10522679602,
    digest="sha256:d78081b2aab8a2d3d85e34e49a5f2134dfc90221cd5a5abf0df2fa7fd8f3e134",
)
R11_POSITIVE_CANDIDATE = EvidenceRef(
    code="R11_BREAK_A_POSITIVE_VALIDITY_CANDIDATE_CONTRACT",
    run_id=35282466639,
    artifact_id=10523105269,
    digest="sha256:cfcfdfad5f7907c85f9355b3710ade97c3b16883d86628b0003b6cf925938a1c",
)

CLAIMS = (
    StructuralKnowledgeClaim(
        code="K01_ROBUST_INVALID_DEEP_RAID_LATE_CISD",
        subject="journey_validity",
        statement=(
            "Deep raid >25%-50%, fast reclaim <=5m, CISD progress >75%, and "
            "protected risk >50%-100% source range is a repeatedly negative "
            "structural mechanism across early, transition, and recent consumed evidence."
        ),
        strength=KnowledgeStrength.ESTABLISHED_STRUCTURAL_NEGATIVE,
        operating_use=OperatingUse.STRUCTURAL_ABSTENTION_ALLOWED,
        evidence=(R9_CAUSAL,),
        limitations=(
            "applies only to the exact documented conjunction",
            "does not imply that SHORT, H1, H4, or any session is globally invalid",
        ),
    ),
    StructuralKnowledgeClaim(
        code="K02_BREAK_A_B_FAILURE_IS_UPSTREAM",
        subject="journey_failure_location",
        statement=(
            "Most recent BREAK A and BREAK B failures are invalidated before "
            "touching any active DOL, locating the dominant failure upstream "
            "of selected-target hierarchy."
        ),
        strength=KnowledgeStrength.ESTABLISHED_DIAGNOSTIC,
        operating_use=OperatingUse.REASONING_CONTEXT_ONLY,
        evidence=(R9_PATH,),
        limitations=(
            "post-entry path is a forensic label only",
            "must never be used as contemporaneous operating input",
        ),
    ),
    StructuralKnowledgeClaim(
        code="K03_LIQUIDITY_SIGNIFICANCE_IS_MECHANISM_SPECIFIC",
        subject="liquidity_significance",
        statement=(
            "Liquidity significance contains useful clues, especially for BREAK A, "
            "but no single universal C1/liquidity scalar explains both BREAK A and BREAK B."
        ),
        strength=KnowledgeStrength.INSUFFICIENT_STANDALONE,
        operating_use=OperatingUse.REASONING_CONTEXT_ONLY,
        evidence=(R9_LIQUIDITY,),
    ),
    StructuralKnowledgeClaim(
        code="K04_CISD_SEQUENCE_IS_NOT_STANDALONE_BRAIN",
        subject="cisd_quality",
        statement=(
            "Pre-entry CISD sequence features show weak or inconsistent standalone "
            "separation between DOL-capable journeys and pre-DOL invalidations."
        ),
        strength=KnowledgeStrength.INSUFFICIENT_STANDALONE,
        operating_use=OperatingUse.REASONING_CONTEXT_ONLY,
        evidence=(R9_CISD,),
    ),
    StructuralKnowledgeClaim(
        code="K05_BREAK_A_OPPOSING_SERIES_LENGTH_CLUE",
        subject="protected_swing_causality",
        statement=(
            "Within BREAK A, DOL-capable journeys show a consistently longer opposing "
            "series around the Protected Swing than pre-DOL invalidations across "
            "2016-20, 2021-23, and 2024-26."
        ),
        strength=KnowledgeStrength.STABLE_CLUE_NOT_RULE,
        operating_use=OperatingUse.REASONING_CONTEXT_ONLY,
        evidence=(R10_PS,),
        limitations=(
            "distributional separation is moderate, not decisive",
            "must not be thresholded into an entry rule from consumed data",
        ),
    ),
    StructuralKnowledgeClaim(
        code="K06_PROTECTED_SWING_NOT_UNIVERSAL_DISCRIMINATOR",
        subject="protected_swing_causality",
        statement=(
            "Protected Swing geometry by itself does not provide a stable universal "
            "discriminator for BREAK A and BREAK B; BREAK B lacks the BREAK A signature."
        ),
        strength=KnowledgeStrength.INSUFFICIENT_STANDALONE,
        operating_use=OperatingUse.REASONING_CONTEXT_ONLY,
        evidence=(R10_PS,),
    ),
    StructuralKnowledgeClaim(
        code="K07_BREAK_A_B_REMAIN_CONFLICTED",
        subject="journey_validity",
        statement=(
            "BREAK A and BREAK B were historically viable and recently degraded; "
            "they remain conflicted rather than proven structurally invalid."
        ),
        strength=KnowledgeStrength.CONFLICTED,
        operating_use=OperatingUse.NO_OPERATING_USE,
        evidence=(R9_CAUSAL, R9_PATH, R9_LIQUIDITY, R9_CISD, R10_PS),
        limitations=(
            "no date/year rule is permitted",
            "no retrospective blacklist is justified",
        ),
    ),
    StructuralKnowledgeClaim(
        code="K09_BREAK_A_MULTICHANNEL_TRANSFER_CLUE",
        subject="multi_channel_interaction",
        statement=(
            "For BREAK A, the frozen early-history conjunction of stronger C1 directional wick "
            "and lower post-reclaim re-violation retained a positive association with touching "
            "active DOL across 2016-20, 2021-23, and 2024-26 without recalibration."
        ),
        strength=KnowledgeStrength.STABLE_CLUE_NOT_RULE,
        operating_use=OperatingUse.REASONING_CONTEXT_ONLY,
        evidence=(R10_MEMORY_ATLAS,),
        limitations=(
            "true-conjunction samples are small: 16 early, 8 transition, 6 recent",
            "anchors were learned on consumed early history and are diagnostic only",
            "transfer success is not trade permission and must not open the fresh holdout",
        ),
    ),
    StructuralKnowledgeClaim(
        code="K10_BREAK_B_RAID_PS_TRANSFER_CLUE",
        subject="multi_channel_interaction",
        statement=(
            "For BREAK B, relative raid depth to C1 combined with Protected Swing candle range "
            "kept a positive but modest structural-capacity association across all three consumed "
            "temporal partitions without recalibration."
        ),
        strength=KnowledgeStrength.STABLE_CLUE_NOT_RULE,
        operating_use=OperatingUse.REASONING_CONTEXT_ONLY,
        evidence=(R10_MEMORY_ATLAS,),
        limitations=(
            "separation is materially weaker than the BREAK A multi-channel clue",
            "the relation remains research context, not a positive entry contract",
        ),
    ),
    StructuralKnowledgeClaim(
        code="K11_BREAK_B_CISD_EXPANSION_NOT_STABLE",
        subject="multi_channel_interaction",
        statement=(
            "BREAK B CISD confirmation-range evidence did not transfer consistently: "
            "the early-history relation reversed in the 2021-23 transition partition, "
            "including pre-registered interaction pairs."
        ),
        strength=KnowledgeStrength.INSUFFICIENT_STANDALONE,
        operating_use=OperatingUse.REASONING_CONTEXT_ONLY,
        evidence=(R10_MEMORY_ATLAS,),
        limitations=(
            "do not encode CISD expansion magnitude as a universal BREAK B permission rule",
        ),
    ),
    StructuralKnowledgeClaim(
        code="K12_R11_EXACT_SITUATION_RECOGNITION_BOUND",
        subject="situation_recognition",
        statement=(
            "R11 reproduces the exact evidence populations before applying continuous "
            "context: 273 robust-invalid cases, 151 BREAK A cases, and 88 BREAK B cases."
        ),
        strength=KnowledgeStrength.ESTABLISHED_DIAGNOSTIC,
        operating_use=OperatingUse.REASONING_CONTEXT_ONLY,
        evidence=(R11_RECOGNITION,),
        limitations=(
            "recognition accuracy is evidence-binding accuracy, not profitability",
            "all audited outcomes remain consumed research evidence",
        ),
    ),
    StructuralKnowledgeClaim(
        code="K13_BREAK_A_POSITIVE_VALIDITY_CANDIDATE_FROZEN",
        subject="positive_entry_validity",
        statement=(
            "Exact BREAK A plus the transferred C1 directional-wick and defended-reclaim "
            "conjunction is frozen as a research structural-validity candidate: 31 situations "
            "recognized pre-entry, 30 binary-auditable, and 21 of 30 reached at least one active DOL."
        ),
        strength=KnowledgeStrength.STABLE_CLUE_NOT_RULE,
        operating_use=OperatingUse.NO_OPERATING_USE,
        evidence=(R11_RECOGNITION, R11_POSITIVE_CANDIDATE),
        limitations=(
            "the candidate predicts journey capacity, not profit or selected-target success",
            "sample support is limited and entirely consumed",
            "independent validation is required before any positive operating contract",
        ),
    ),
    StructuralKnowledgeClaim(
        code="K08_POSITIVE_VALIDITY_NOT_YET_PROVEN",
        subject="positive_entry_validity",
        statement=(
            "Consumed evidence does not yet define a frozen positive structural "
            "validity contract sufficient to authorize entry."
        ),
        strength=KnowledgeStrength.UNRESOLVED,
        operating_use=OperatingUse.NO_OPERATING_USE,
        evidence=(R10_INTELLIGENCE, R10_PS),
        limitations=(
            "unknown must not be converted into permission",
            "fresh holdout remains closed until a positive validity contract is frozen",
        ),
    ),
)


def claims_for_subject(subject: str) -> tuple[StructuralKnowledgeClaim, ...]:
    return tuple(claim for claim in CLAIMS if claim.subject == subject)


def claim_by_code(code: str) -> StructuralKnowledgeClaim:
    matches = tuple(claim for claim in CLAIMS if claim.code == code)
    if len(matches) != 1:
        raise KeyError(code)
    return matches[0]


def knowledge_manifest() -> dict[str, Any]:
    return {
        "schema": "qore.turtle_soup_xauusd_r10.cibo_structural_knowledge_base.v1",
        "identity": IDENTITY,
        "purpose": (
            "Persistent evidence-bound memory for CIBO Journey Intelligence. "
            "Claims distinguish established negatives, diagnostics, clues, conflicts, "
            "and unresolved questions without historical-return scoring."
        ),
        "claims": [asdict(claim) for claim in CLAIMS],
        "reasoning_contract": {
            "historical_return_score": False,
            "automatic_probability_of_trade_success": False,
            "automatic_threshold_search": False,
            "year_or_date_operating_rule": False,
            "post_entry_label_allowed_as_live_input": False,
            "positive_permission_requires_separate_frozen_validity_contract": True,
            "unknown_means_permission": False,
        },
        "governance": {
            "candidate_promoted": False,
            "fresh_holdout_consumed": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def write_manifest(path: Path) -> dict[str, Any]:
    payload = cast(dict[str, Any], _jsonable(knowledge_manifest()))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload
