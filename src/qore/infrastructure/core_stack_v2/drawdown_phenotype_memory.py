"""Authority-free universal drawdown phenotype memory for Shared Core V2.

This module stores causal phenotype knowledge learned from CLOSED historical
episodes and lets runtime perception ask whether the current causal signature
resembles a known form.

It deliberately does NOT decide whether to enter, exit, resize, trail, mutate a
stop, mutate a target, or allocate capital. A match is knowledge, not authority.

Current-episode outcomes, runtime PnL, future market path, sizing and risk budget
are not inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DrawdownPhenotypeComposition(StrEnum):
    PURE_LOSS = "PURE_LOSS"
    LOSS_DOMINANT = "LOSS_DOMINANT"
    MIXED_BALANCED = "MIXED_BALANCED"
    WINNER_DOMINANT = "WINNER_DOMINANT"


class DrawdownPhenotypeRecognition(StrEnum):
    UNKNOWN = "UNKNOWN"
    KNOWN_PURE_LOSS = "KNOWN_PURE_LOSS"
    KNOWN_LOSS_BIASED = "KNOWN_LOSS_BIASED"
    KNOWN_AMBIGUOUS = "KNOWN_AMBIGUOUS"
    KNOWN_WINNER_OVERLAP = "KNOWN_WINNER_OVERLAP"


@dataclass(frozen=True, slots=True)
class DrawdownPhenotype:
    """Closed-evidence phenotype retained by Shared knowledge memory."""

    view: str
    signature: str
    composition: DrawdownPhenotypeComposition
    historical_sample: int
    historical_losses: int
    historical_winners: int
    fold_presence: str
    temporal_stability: str

    def __post_init__(self) -> None:
        if not self.view or not self.signature:
            raise ValueError("phenotype identity must be non-empty")
        if self.historical_sample < 0:
            raise ValueError("historical_sample cannot be negative")
        if self.historical_losses < 0 or self.historical_winners < 0:
            raise ValueError("historical outcome counts cannot be negative")
        if self.historical_losses + self.historical_winners > self.historical_sample:
            raise ValueError("historical outcomes cannot exceed sample")
        if not self.fold_presence or not self.temporal_stability:
            raise ValueError("phenotype stability metadata must be non-empty")

        expected = _composition(
            self.historical_losses,
            self.historical_winners,
        )
        if self.composition is not expected:
            raise ValueError(
                "phenotype composition must agree with closed historical counts"
            )

    @property
    def key(self) -> tuple[str, str]:
        return (self.view, self.signature)


@dataclass(frozen=True, slots=True)
class DrawdownPhenotypeQuery:
    """Causal resident signatures visible at the current decision timestamp."""

    signatures: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if self.signatures != tuple(sorted(self.signatures)):
            raise ValueError("query signatures must be canonical")
        if len({view for view, _ in self.signatures}) != len(self.signatures):
            raise ValueError("query views must be unique")
        if any(not view or not signature for view, signature in self.signatures):
            raise ValueError("query signature fields must be non-empty")


@dataclass(frozen=True, slots=True)
class DrawdownPhenotypeAssessment:
    """Knowledge-only phenotype assessment. Carries no trading authority."""

    recognition: DrawdownPhenotypeRecognition
    matched: tuple[DrawdownPhenotype, ...]
    matched_compositions: tuple[DrawdownPhenotypeComposition, ...]
    known_views: tuple[str, ...]
    unknown_views: tuple[str, ...]
    pure_loss_matches: int
    loss_dominant_matches: int
    ambiguous_matches: int
    winner_dominant_matches: int
    confidence_bps: int
    order_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    execution_authority: bool = False
    stop_authority: bool = False
    target_authority: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.confidence_bps <= 10_000:
            raise ValueError("confidence_bps must be within 0..10000")
        if (
            self.order_authority
            or self.risk_authority
            or self.sizing_authority
            or self.execution_authority
            or self.stop_authority
            or self.target_authority
        ):
            raise ValueError("drawdown phenotype memory cannot carry trade authority")


def _composition(
    losses: int,
    winners: int,
) -> DrawdownPhenotypeComposition:
    if losses > 0 and winners == 0:
        return DrawdownPhenotypeComposition.PURE_LOSS
    if losses > winners:
        return DrawdownPhenotypeComposition.LOSS_DOMINANT
    if losses == winners:
        return DrawdownPhenotypeComposition.MIXED_BALANCED
    return DrawdownPhenotypeComposition.WINNER_DOMINANT


def _recognition(
    compositions: tuple[DrawdownPhenotypeComposition, ...],
) -> DrawdownPhenotypeRecognition:
    if not compositions:
        return DrawdownPhenotypeRecognition.UNKNOWN
    unique = set(compositions)
    if unique == {DrawdownPhenotypeComposition.PURE_LOSS}:
        return DrawdownPhenotypeRecognition.KNOWN_PURE_LOSS
    if unique <= {
        DrawdownPhenotypeComposition.PURE_LOSS,
        DrawdownPhenotypeComposition.LOSS_DOMINANT,
    }:
        return DrawdownPhenotypeRecognition.KNOWN_LOSS_BIASED
    if DrawdownPhenotypeComposition.WINNER_DOMINANT in unique:
        return DrawdownPhenotypeRecognition.KNOWN_WINNER_OVERLAP
    return DrawdownPhenotypeRecognition.KNOWN_AMBIGUOUS


class UniversalDrawdownPhenotypeMemory:
    """Deterministic registry of closed historical phenotype knowledge."""

    def __init__(
        self,
        phenotypes: tuple[DrawdownPhenotype, ...],
    ) -> None:
        ordered = tuple(sorted(phenotypes, key=lambda item: item.key))
        if len({item.key for item in ordered}) != len(ordered):
            raise ValueError("duplicate drawdown phenotype")
        self._phenotypes = ordered
        self._by_key = {item.key: item for item in ordered}

    @property
    def phenotype_count(self) -> int:
        return len(self._phenotypes)

    def assess(
        self,
        query: DrawdownPhenotypeQuery,
    ) -> DrawdownPhenotypeAssessment:
        matched = tuple(
            self._by_key[(view, signature)]
            for view, signature in query.signatures
            if (view, signature) in self._by_key
        )
        matched = tuple(sorted(matched, key=lambda item: item.key))

        known_views = tuple(item.view for item in matched)
        known_set = set(known_views)
        unknown_views = tuple(
            view
            for view, _ in query.signatures
            if view not in known_set
        )
        compositions = tuple(item.composition for item in matched)

        pure = sum(
            item.composition is DrawdownPhenotypeComposition.PURE_LOSS
            for item in matched
        )
        loss_dominant = sum(
            item.composition is DrawdownPhenotypeComposition.LOSS_DOMINANT
            for item in matched
        )
        ambiguous = sum(
            item.composition is DrawdownPhenotypeComposition.MIXED_BALANCED
            for item in matched
        )
        winner_dominant = sum(
            item.composition is DrawdownPhenotypeComposition.WINNER_DOMINANT
            for item in matched
        )

        # Confidence is coverage of the resident causal views, not confidence
        # that a trade will lose. Outcome probability is intentionally absent.
        confidence = (
            0
            if not query.signatures
            else int(
                min(
                    10_000,
                    (len(matched) * 10_000) // len(query.signatures),
                )
            )
        )

        return DrawdownPhenotypeAssessment(
            recognition=_recognition(compositions),
            matched=matched,
            matched_compositions=compositions,
            known_views=known_views,
            unknown_views=unknown_views,
            pure_loss_matches=pure,
            loss_dominant_matches=loss_dominant,
            ambiguous_matches=ambiguous,
            winner_dominant_matches=winner_dominant,
            confidence_bps=confidence,
        )
