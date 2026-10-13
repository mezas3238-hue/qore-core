"""Causal, source-linked Model #1 witness for qualitative VT08 CRT PURE research.

This bridges already-closed candle geometry to cognition without choosing an old
level, claiming an original-author hierarchy, or authorizing any trading.
It checks internal chronology/geometry, NOT authenticity of the upstream feed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from qore.infrastructure.traders.crt_pure_cognitive_contract import (
    CrtPureAttentionState,
    CrtPureHypothesisStage,
    CrtPureKnowledgeState,
)
from qore.infrastructure.traders.crt_pure_cognitive_state import (
    CrtPureCausalObservation,
    CrtPureSituationModel,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_model1 import (
    MODEL1_EXECUTION_TIMEFRAME_SECONDS,
    CrtPureModel1Bar,
    CrtPureModel1Confirmation,
    CrtPureModel1ReferenceKind,
    CrtPureModel1State,
    assess_model1_confirmation,
    detect_model1_candidate,
)


@dataclass(frozen=True, slots=True)
class CrtPureModel1CausalWitness:
    """A research witness for one known M15 source, not a level-selection verdict.

    reference_known_at is upstream-provided provenance: the witness only proves
    chronological consistency, not that the old level was originally selected
    correctly by RomeoTPT rules or that market OHLC was independently verified.
    """

    market: CrtPureMarket
    parent_crt_id: str
    parent_c3_opened_at: datetime
    parent_c3_closed_at: datetime
    reference_bar: CrtPureModel1Bar
    reference_known_at: datetime
    eligible_reference_ids: tuple[str, ...]
    confirmation: CrtPureModel1Confirmation
    observed_at: datetime

    def __post_init__(self) -> None:
        if not self.parent_crt_id.strip():
            raise ValueError("Model #1 witness requires parent CRT identity")
        for label, value in (
            ("parent C3 open", self.parent_c3_opened_at),
            ("parent C3 close", self.parent_c3_closed_at),
            ("reference known", self.reference_known_at),
            ("observed", self.observed_at),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"Model #1 {label} requires timezone-aware timestamp")
        if self.parent_c3_closed_at - self.parent_c3_opened_at != timedelta(
            hours=4
        ):
            raise ValueError("Model #1 parent C3 must be one H4 candle")

        candidate = self.confirmation.candidate
        source = candidate.source_candle
        confirm_bar = self.confirmation.confirming_candle
        reference = candidate.reference
        m15 = timedelta(seconds=MODEL1_EXECUTION_TIMEFRAME_SECONDS)

        if not self.eligible_reference_ids or len(set(self.eligible_reference_ids)) != len(
            self.eligible_reference_ids
        ):
            raise ValueError("Model #1 reference witness IDs must be nonempty and unique")
        if any(not ref_id.strip() for ref_id in self.eligible_reference_ids):
            raise ValueError("Model #1 witness reference IDs cannot be blank")
        if reference.evidence_id not in self.eligible_reference_ids:
            raise ValueError("Model #1 selected reference absent from witness group")
        if not (self.parent_c3_opened_at <= source.opened_at < self.parent_c3_closed_at):
            raise ValueError("Model #1 source must open within parent C3")
        if source.opened_at + m15 > confirm_bar.opened_at:
            raise ValueError("Model #1 confirmation must start after source M15 closes")
        if not (
            self.parent_c3_opened_at <= confirm_bar.opened_at
            and self.confirmation.decision_at <= self.parent_c3_closed_at
        ):
            raise ValueError("Model #1 confirmation must be known within parent C3")
        if self.reference_bar.opened_at + m15 > self.reference_known_at:
            raise ValueError("Model #1 old level cannot be known before origin candle closes")
        if self.reference_known_at > source.opened_at:
            raise ValueError("Model #1 old level was not known before source opens")
        if self.reference_bar.opened_at >= source.opened_at:
            raise ValueError("Model #1 old level must originate before source")
        expected_reference_price = (
            self.reference_bar.high_price
            if reference.kind is CrtPureModel1ReferenceKind.OLD_HIGH
            else self.reference_bar.low_price
        )
        if reference.price != expected_reference_price:
            raise ValueError("Model #1 reference price disagrees with origin candle")
        reconstructed = detect_model1_candidate(
            reference=reference, candle=source
        )
        if reconstructed != candidate:
            raise ValueError("Model #1 witness source candle does not satisfy Model #1")
        reconstructed_confirmation = assess_model1_confirmation(
            candidate=candidate, candle=confirm_bar
        )
        if reconstructed_confirmation != self.confirmation:
            raise ValueError("Model #1 witness confirmation does not match body close")
        if self.observed_at < self.confirmation.decision_at:
            raise ValueError("Model #1 witness cannot observe confirmation before close")

    @property
    def source_event_id(self) -> str:
        """Same M15 candle + direction is one event despite several old levels."""
        candidate = self.confirmation.candidate
        return (
            f"{self.market.value}:{self.parent_crt_id}:"
            f"{candidate.source_candle.opened_at.isoformat()}:"
            f"{candidate.direction.value}"
        )


def build_model1_cognitive_situation(
    witness: CrtPureModel1CausalWitness,
    *,
    data_integrity_ok: bool,
    strategy_identity_ready: bool,
    destination_context_known: bool,
    destination_available: bool,
    execution_data_fresh: bool,
) -> CrtPureSituationModel:
    """Pass time-anchored Model #1 evidence to cognition, fail-open never.

    All external integrity/readiness/destination flags must be supplied by their
    respective owners. Source selection is still ambiguous in the primary
    corpus; a witness must NOT elevate partial knowledge to KNOWN.
    """
    candidate = witness.confirmation.candidate
    source_known_at = candidate.source_candle.opened_at + timedelta(
        seconds=MODEL1_EXECUTION_TIMEFRAME_SECONDS
    )
    observations = (
        CrtPureCausalObservation(
            name="MODEL1_REFERENCE_ORIGIN",
            observed_at=witness.reference_known_at,
            value_token=(
                f"{candidate.reference.evidence_id}:"
                f"{candidate.reference.kind.value}:{candidate.reference.price}:"
                f"{witness.reference_bar.opened_at.isoformat()}"
            ),
        ),
        CrtPureCausalObservation(
            name="MODEL1_ELIGIBLE_REFERENCE_SET",
            observed_at=source_known_at,
            value_token="|".join(witness.eligible_reference_ids),
        ),
        CrtPureCausalObservation(
            name="MODEL1_SOURCE_BAR_CLOSE",
            observed_at=source_known_at,
            value_token=candidate.source_candle.opened_at.isoformat(),
        ),
        CrtPureCausalObservation(
            name="MODEL1_CONFIRMING_BODY_CLOSE",
            observed_at=witness.confirmation.decision_at,
            value_token=(
                f"{witness.confirmation.confirming_candle.opened_at.isoformat()}:"
                f"{witness.confirmation.state.value}"
            ),
        ),
    )
    confirmed = witness.confirmation.state is CrtPureModel1State.CONFIRMED
    return CrtPureSituationModel(
        market=witness.market,
        observed_at=witness.observed_at,
        hypothesis_id=witness.source_event_id,
        source_event_id=witness.source_event_id,
        event_generation=1,
        attention_state=CrtPureAttentionState.DECISION,
        hypothesis_stage=(
            CrtPureHypothesisStage.CONFIRMED
            if confirmed
            else CrtPureHypothesisStage.AWAITING_CONFIRMATION
        ),
        data_integrity_ok=data_integrity_ok,
        strategy_identity_ready=strategy_identity_ready,
        source_event_present=True,
        confirmation_complete=confirmed,
        destination_context_known=destination_context_known,
        destination_available=destination_available,
        execution_data_fresh=execution_data_fresh,
        # Multi-level and single-level selection alike remain source-ambiguous.
        knowledge_state=CrtPureKnowledgeState.PARTIAL,
        uncertainties=(
            "MODEL_1_REFERENCE_SELECTION_AMBIGUOUS",
            "MODEL_1_REFERENCE_ELIGIBILITY_IS_UPSTREAM_ATTESTED",
        ),
        market_context_tokens=(
            "MODEL1_SOURCE_WITNESS_RESEARCH_ONLY",
            f"MODEL1_PARENT_CRT:{witness.parent_crt_id}",
        ),
        observations=observations,
    )
