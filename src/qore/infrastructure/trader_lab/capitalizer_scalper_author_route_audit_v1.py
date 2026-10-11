"""Auditable source-route taxonomy for the QORE Capitalizer scalper.

Research/audit metadata only. This does not create signals, deny otherwise valid
trades, change timeframes, size positions, or promote a certification result.

Primary author: TTrades. ICT claims need a separate first-party timestamp ledger.
The distinction between a generic scalp practiced in a session and the author's
session-specific profile must never be erased.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_high_frequency_identity_v49 import (
    V49_HIGH_FREQUENCY_SCALPER_IDENTITY,
)

IDENTITY = "QORE_CAPITALIZER_SCALPER_AUTHOR_ROUTE_AUDIT_V1"
SOURCE_BASE = "https://ttrades.com/"


class AuthorRoute(StrEnum):
    GENERIC_SCALPING = "GENERIC_SCALPING"
    ASIA_POSITIONAL = "ASIA_POSITIONAL"
    ASIA_H4_M15_FRACTAL = "ASIA_H4_M15_FRACTAL"
    LONDON_DAILY_H4_M15 = "LONDON_DAILY_H4_M15"
    NEW_YORK_MANIPULATION = "NEW_YORK_MANIPULATION"
    FAILURE_TO_MANIPULATE = "FAILURE_TO_MANIPULATE"


class FidelityVerdict(StrEnum):
    PARTIAL_GENERIC_ALIGNMENT = "PARTIAL_GENERIC_ALIGNMENT"
    CONFLICT_LITERAL_SESSION_ROUTE = "CONFLICT_LITERAL_SESSION_ROUTE"
    UNRESOLVED_ROUTE_EXECUTION = "UNRESOLVED_ROUTE_EXECUTION"


@dataclass(frozen=True, slots=True)
class AuthorSourceRoute:
    route: AuthorRoute
    session: str
    author: str
    primary_url: str
    source_section: str
    source_timeframe_roles: tuple[str, ...]
    mandatory_source_concepts: tuple[str, ...]
    source_alternatives: tuple[str, ...] = ()
    illustrative_behaviors: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.author != "TTrades":
            raise ValueError("TTrades source routes must be attributed to TTrades")
        if not self.primary_url.startswith(SOURCE_BASE):
            raise ValueError("TTrades source route requires a first-party page")
        if not self.source_section or not self.mandatory_source_concepts:
            raise ValueError("source route must identify sections and concepts")


SOURCES: tuple[AuthorSourceRoute, ...] = (
    AuthorSourceRoute(
        route=AuthorRoute.GENERIC_SCALPING,
        session="GENERIC",
        author="TTrades",
        primary_url=SOURCE_BASE + "ttrades-scalping-model-simple-day-trading-strategy/",
        source_section=(
            "The Core Concept; Establishing Hourly Bias; "
            "Finding the Fifteen Minute Swing Point; Entry"
        ),
        source_timeframe_roles=(
            "DAILY_CONTEXT", "H1_BIAS", "M15_SWING", "M1_EXECUTION"
        ),
        mandatory_source_concepts=(
            "HOURLY_BIAS", "M15_SWING", "M1_EXECUTION", "STRUCTURAL_STOP_HTF_TARGET"
        ),
        # The generic article lists examples of continuation behavior; it does
        # not declare each item a standalone, sufficient entry-model alternative.
        illustrative_behaviors=("FVG_INTERACTION", "CISD", "PROTECTED_SWING_FORMATION"),
    ),
    AuthorSourceRoute(
        route=AuthorRoute.ASIA_POSITIONAL,
        session="ASIA",
        author="TTrades",
        primary_url=SOURCE_BASE + "how-to-trade-asia-using-the-ttrades-fractal-model/",
        source_section="Option One: Positional Entries in Asia",
        source_timeframe_roles=(
            "DAILY_HTF_BIAS", "PREEXISTING_HTF_PROTECTED_SWING", "POSITIONAL_ENTRY"
        ),
        mandatory_source_concepts=("HTF_BIAS", "PREEXISTING_PROTECTED_SWING"),
    ),
    AuthorSourceRoute(
        route=AuthorRoute.ASIA_H4_M15_FRACTAL,
        session="ASIA",
        author="TTrades",
        primary_url=SOURCE_BASE + "how-to-trade-asia-using-the-ttrades-fractal-model/",
        source_section="Option Two: The 4-Hour and 15-Minute Fractal Model",
        source_timeframe_roles=("DAILY_HTF_BIAS", "H4_CANDLE2", "M15_CISD_ENTRY"),
        mandatory_source_concepts=("HTF_BIAS", "H4_CANDLE2_CLOSURE", "M15_PROTECTED_SWING"),
    ),
    AuthorSourceRoute(
        route=AuthorRoute.LONDON_DAILY_H4_M15,
        session="LONDON",
        author="TTrades",
        primary_url=SOURCE_BASE + "how-to-trade-london-using-ttrades-fractal-model/",
        source_section=(
            "Start With A Daily Bias; Use The 4 Hour Candle; "
            "Confirm The Swing On The 15 Minute"
        ),
        source_timeframe_roles=("DAILY_BIAS_WICK", "H4_WICK_SWING", "M15_CISD_PROTECTED_SWING"),
        mandatory_source_concepts=("DAILY_BIAS", "H4_WICK_FORMATION", "M15_PROTECTED_SWING"),
    ),
    AuthorSourceRoute(
        route=AuthorRoute.NEW_YORK_MANIPULATION,
        session="NEW_YORK",
        author="TTrades",
        primary_url=SOURCE_BASE + "daily-profile-understanding-the-new-york-manipulation/",
        source_section="What is the New York Manipulation Profile?; How to Recognize It on Charts",
        source_timeframe_roles=("LONDON_RANGE_CONTEXT", "NY_SWEEP", "NY_CISD", "EXPANSION"),
        mandatory_source_concepts=("LONDON_RANGE_CONTEXT", "LIQUIDITY_SWEEP", "CISD"),
        source_alternatives=("FVG_ENTRY", "OB_ENTRY", "OTHER_EXPLICIT_ENTRY_MODEL"),
    ),
    AuthorSourceRoute(
        route=AuthorRoute.FAILURE_TO_MANIPULATE,
        session="CONTEXTUAL",
        author="TTrades",
        primary_url=SOURCE_BASE + "how-to-trade-breakouts-failure-to-manipulate/",
        source_section=(
            "The Reversal Has To Actually Form; Trade The Continuation; "
            "Pair It With Higher Time Frame Bias"
        ),
        source_timeframe_roles=("HTF_BIAS", "FAILED_REVERSAL", "LTF_CONTINUATION"),
        mandatory_source_concepts=(
            "HIGH_LOW_TAKEN", "REVERSAL_NOT_CONFIRMED", "HTF_ALIGNED_CONTINUATION"
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class SourceRouteDifferential:
    identity: str
    route: AuthorRoute
    verdict: FidelityVerdict
    primary_url: str
    source_section: str
    source_roles: tuple[str, ...]
    qore_decision_roles: tuple[str, ...]
    reason_codes: tuple[str, ...]
    label_as_literal_author_route: bool = False
    alters_source_admission: bool = False
    author_fidelity_certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY or not self.reason_codes:
            raise ValueError("source audit requires identity and evidence reasons")
        if self.label_as_literal_author_route or self.alters_source_admission:
            raise ValueError("source-route taxonomy has no authority to rewrite source strategy")
        if self.author_fidelity_certified:
            raise ValueError("route differential cannot certify unverified methodology")


def audit_frozen_v49_route_claims() -> tuple[SourceRouteDifferential, ...]:
    """Compare frozen V49 identity against published models, not actual replay callers.

    This is deliberately a *route-claim* audit. Source-engine wiring and exact
    rule-level provenance are separate proof obligations.
    """

    identity = V49_HIGH_FREQUENCY_SCALPER_IDENTITY
    layers = tuple(layer.timeframe.value for layer in identity.layers)
    if layers != ("H1", "M15", "M1"):
        raise ValueError("source-route audit requires the actual frozen V49 identity")
    if identity.daily_decision_layer_allowed or identity.h4_decision_layer_allowed:
        raise ValueError("V49 source-route audit cannot secretly change timeframes")

    rows: list[SourceRouteDifferential] = []
    reasons: tuple[str, ...]
    for source in SOURCES:
        if source.route is AuthorRoute.GENERIC_SCALPING:
            verdict = FidelityVerdict.PARTIAL_GENERIC_ALIGNMENT
            reasons = ("H1_M15_M1_SOURCE_CORE_ALIGNED", "DAILY_BROADER_CONTEXT_NOT_USED_BY_QORE")
        elif source.route in {
            AuthorRoute.ASIA_POSITIONAL,
            AuthorRoute.ASIA_H4_M15_FRACTAL,
            AuthorRoute.LONDON_DAILY_H4_M15,
        }:
            verdict = FidelityVerdict.CONFLICT_LITERAL_SESSION_ROUTE
            reasons = ("AUTHOR_SESSION_ROUTE_HAS_DIFFERENT_HTF_OR_ENTRY_LAYERS",)
        else:
            verdict = FidelityVerdict.UNRESOLVED_ROUTE_EXECUTION
            reasons = ("SOURCE_ROUTE_SPECIFIC_CALL_CHAIN_NOT_YET_PROVED",)

        rows.append(
            SourceRouteDifferential(
                identity=IDENTITY,
                route=source.route,
                verdict=verdict,
                primary_url=source.primary_url,
                source_section=source.source_section,
                source_roles=source.source_timeframe_roles,
                qore_decision_roles=layers,
                reason_codes=reasons,
            )
        )
    return tuple(rows)
