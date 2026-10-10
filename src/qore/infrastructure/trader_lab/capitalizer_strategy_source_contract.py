"""Source-bound methodology contract for QORE Capitalizer research.

This is a provenance and rule-family contract, not evidence that the strategy has edge.
Exact economic promotion remains governed by QORE Research/Trader Lab.

The contract deliberately separates:
- source-supported concepts,
- QORE's deterministic operationalization of those concepts,
- economic validation.

No source claim or operational rule may be silently rewritten after outcome inspection.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from re import fullmatch

CAPITALIZER_SOURCE_CONTRACT_ID = "QORE_CAPITALIZER_SOURCE_CONTRACT_V1"


class CapitalizerSourceAuthority(StrEnum):
    PRIMARY = "PRIMARY"
    SECONDARY_STRUCTURED = "SECONDARY_STRUCTURED"


class CapitalizerRuleProvenance(StrEnum):
    SOURCE_SUPPORTED = "SOURCE_SUPPORTED"
    QORE_OPERATIONALIZATION = "QORE_OPERATIONALIZATION"


@dataclass(frozen=True, slots=True)
class CapitalizerSourceReference:
    source_id: str
    authority: CapitalizerSourceAuthority
    title: str
    locator: str

    def __post_init__(self) -> None:
        if fullmatch(r"[A-Z0-9][A-Z0-9_\-]{2,79}", self.source_id) is None:
            raise ValueError("source_id must be canonical uppercase token")
        if not self.title or not self.locator:
            raise ValueError("source title/locator must be non-empty")


@dataclass(frozen=True, slots=True)
class CapitalizerSourceRule:
    rule_id: str
    provenance: CapitalizerRuleProvenance
    statement: str
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if fullmatch(r"[A-Z0-9][A-Z0-9_\-]{2,79}", self.rule_id) is None:
            raise ValueError("rule_id must be canonical uppercase token")
        if not self.statement:
            raise ValueError("rule statement must be non-empty")
        if self.provenance is CapitalizerRuleProvenance.SOURCE_SUPPORTED and not self.source_ids:
            raise ValueError("source-supported rule requires at least one source id")
        if self.provenance is CapitalizerRuleProvenance.QORE_OPERATIONALIZATION and self.source_ids:
            raise ValueError("QORE operationalization must not masquerade as a sourced rule")
        if self.source_ids != tuple(sorted(set(self.source_ids))):
            raise ValueError("source_ids must be unique canonical order")


@dataclass(frozen=True, slots=True)
class CapitalizerSourceContract:
    contract_id: str
    sources: tuple[CapitalizerSourceReference, ...]
    rules: tuple[CapitalizerSourceRule, ...]
    runtime_mutation_allowed: bool = False
    economic_edge_claimed: bool = False

    def __post_init__(self) -> None:
        if self.contract_id != CAPITALIZER_SOURCE_CONTRACT_ID:
            raise ValueError("Capitalizer source contract identity is frozen")
        if self.runtime_mutation_allowed:
            raise ValueError("source contract cannot self-mutate at runtime")
        if self.economic_edge_claimed:
            raise ValueError("source contract cannot claim economic edge")

        source_ids = tuple(source.source_id for source in self.sources)
        if source_ids != tuple(sorted(set(source_ids))):
            raise ValueError("sources must use unique canonical source_id order")
        available = set(source_ids)
        rule_ids = tuple(rule.rule_id for rule in self.rules)
        if rule_ids != tuple(sorted(set(rule_ids))):
            raise ValueError("rules must use unique canonical rule_id order")
        for rule in self.rules:
            missing = set(rule.source_ids) - available
            if missing:
                raise ValueError(f"rule references missing sources: {sorted(missing)}")


CAPITALIZER_SOURCES: tuple[CapitalizerSourceReference, ...] = (
    CapitalizerSourceReference(
        source_id="ICT_ASIAN_KILLZONE",
        authority=CapitalizerSourceAuthority.PRIMARY,
        title="ICT Forex - The ICT Asian Killzone",
        locator="youtube:ley5HZs4bUM",
    ),
    CapitalizerSourceReference(
        source_id="ICT_HIGH_PROBABILITY_SCALPING",
        authority=CapitalizerSourceAuthority.PRIMARY,
        title="ICT - Mastering High Probability Scalping",
        locator="youtube:uE-aaP16nOw",
    ),
    CapitalizerSourceReference(
        source_id="ICT_LONDON_KILLZONE",
        authority=CapitalizerSourceAuthority.PRIMARY,
        title="ICT Forex - The ICT London Killzone",
        locator="youtube:G8OEsUAoIWE",
    ),
    CapitalizerSourceReference(
        source_id="ICT_NEW_YORK_KILLZONE",
        authority=CapitalizerSourceAuthority.PRIMARY,
        title="ICT Forex - The ICT New York Killzone",
        locator="youtube:plNN9n7nrxc",
    ),
    CapitalizerSourceReference(
        source_id="TTRADES_FAILURE_TO_MANIPULATE",
        authority=CapitalizerSourceAuthority.SECONDARY_STRUCTURED,
        title="TTrades - Failure to Manipulate",
        locator="ttrades:failure-to-manipulate",
    ),
    CapitalizerSourceReference(
        source_id="TTRADES_SCALPING_MODEL",
        authority=CapitalizerSourceAuthority.SECONDARY_STRUCTURED,
        title="TTrades Scalping Model",
        locator="youtube:eywpZT3z6GQ",
    ),
)


CAPITALIZER_SOURCE_RULES: tuple[CapitalizerSourceRule, ...] = (
    CapitalizerSourceRule(
        rule_id="CONTEXT_PRECEDES_ENTRY",
        provenance=CapitalizerRuleProvenance.SOURCE_SUPPORTED,
        statement="Scalp execution is contextual rather than an isolated lower-timeframe signal.",
        source_ids=("ICT_HIGH_PROBABILITY_SCALPING", "TTRADES_SCALPING_MODEL"),
    ),
    CapitalizerSourceRule(
        rule_id="FAILURE_CAN_RECLASSIFY_TRANSITION",
        provenance=CapitalizerRuleProvenance.SOURCE_SUPPORTED,
        statement=(
            "Failure of the expected manipulation/reversal can carry continuation information."
        ),
        source_ids=("TTRADES_FAILURE_TO_MANIPULATE",),
    ),
    CapitalizerSourceRule(
        rule_id="LIQUIDITY_EVENT_PRECEDES_MICRO_DECISION",
        provenance=CapitalizerRuleProvenance.SOURCE_SUPPORTED,
        statement="A liquidity/break interaction is interpreted before lower-timeframe execution.",
        source_ids=("ICT_HIGH_PROBABILITY_SCALPING", "TTRADES_FAILURE_TO_MANIPULATE"),
    ),
    CapitalizerSourceRule(
        rule_id="QORE_ACCEPTANCE_REJECTION_STATE_MACHINE",
        provenance=CapitalizerRuleProvenance.QORE_OPERATIONALIZATION,
        statement=(
            "QORE operationalizes post-event behavior as deterministic acceptance/rejection "
            "states before continuation/reversal classification."
        ),
        source_ids=(),
    ),
    CapitalizerSourceRule(
        rule_id="QORE_MAX_THREE_EXECUTIONS_PER_SESSION",
        provenance=CapitalizerRuleProvenance.QORE_OPERATIONALIZATION,
        statement=(
            "At most three executed opportunities are permitted per session; this is a QORE "
            "capitalization constraint, not a claim attributed to ICT or TTrades."
        ),
        source_ids=(),
    ),
    CapitalizerSourceRule(
        rule_id="SESSION_CONTEXT_IS_EXPLICIT",
        provenance=CapitalizerRuleProvenance.SOURCE_SUPPORTED,
        statement="Asia, London and New York are explicit contextual regimes for intraday study.",
        source_ids=(
            "ICT_ASIAN_KILLZONE",
            "ICT_LONDON_KILLZONE",
            "ICT_NEW_YORK_KILLZONE",
        ),
    ),
)


FROZEN_CAPITALIZER_SOURCE_CONTRACT = CapitalizerSourceContract(
    contract_id=CAPITALIZER_SOURCE_CONTRACT_ID,
    sources=CAPITALIZER_SOURCES,
    rules=CAPITALIZER_SOURCE_RULES,
)
