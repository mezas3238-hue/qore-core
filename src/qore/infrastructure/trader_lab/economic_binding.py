"""Instrument-bound economic evidence for the first DEMO Trader cohort.

The generic Trader Lab economic-reference seam predates the first cTrader DEMO
vertical and binds research-run lineage but not the execution instrument.  The
first cohort has a stronger invariant: the economic observation, every retained
performance observation, and the frozen Trader manifest must all use the exact
same canonical instrument.

This module derives a v2 self-authenticating ECONOMIC_EVALUATION reference from
the complete return observation and the frozen instrument.  It is deliberately
narrow to the first-cohort execution boundary and does not grant Risk, CIBO,
execution, Production, or real-capital authority.
"""

from __future__ import annotations

from hashlib import sha256

from qore.infrastructure.market_data import Instrument
from qore.infrastructure.research_economic_evidence import (
    ResearchGrossEconomicResult,
    ResearchNetEconomicResult,
    ResearchReturnObservation,
)
from qore.infrastructure.research_performance_statistics import (
    ResearchPerformanceStatisticsSnapshot,
)
from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateBinding,
    TraderLabValidationError,
)
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceDigest,
    TraderLabEvidenceKind,
    TraderLabEvidenceReference,
    _canonical_bytes,
    _make_self_authenticating_reference,
    validate_trader_lab_evidence_reference,
)

INSTRUMENT_BOUND_ECONOMIC_SCHEMA = "research.economic-return.instrument-bound.v2"


def _candidate_instrument(candidate: TraderLabCandidateBinding) -> Instrument:
    if not isinstance(candidate, TraderLabCandidateBinding):
        raise TraderLabValidationError(
            "instrument-bound economics require TraderLabCandidateBinding"
        )
    candidate.__post_init__()
    values = tuple(
        parameter.value
        for parameter in candidate.strategy_binding.manifest.parameters
        if parameter.name == "trader.instrument"
    )
    if len(values) != 1 or type(values[0]) is not str:
        raise TraderLabValidationError(
            "instrument-bound economics require one frozen trader.instrument"
        )
    return Instrument(values[0])


def research_return_instrument(
    observation: ResearchReturnObservation,
) -> Instrument:
    """Return the exact canonical instrument carried by one economic return."""

    if not isinstance(observation, ResearchReturnObservation):
        raise TraderLabValidationError(
            "instrument-bound economics require ResearchReturnObservation"
        )
    observation.__post_init__()
    source = observation.source_result
    gross: ResearchGrossEconomicResult
    if isinstance(source, ResearchNetEconomicResult):
        source.gross_result.__post_init__()
        source.__post_init__()
        gross = source.gross_result
    elif isinstance(source, ResearchGrossEconomicResult):
        source.__post_init__()
        gross = source
    else:
        raise TraderLabValidationError(
            "economic return source must be a canonical research economic result"
        )
    return Instrument(gross.instrument.value)


def reference_instrument_bound_research_economic(
    candidate: TraderLabCandidateBinding,
    observation: ResearchReturnObservation,
) -> TraderLabEvidenceReference:
    """Mint the canonical first-cohort economic reference with instrument binding."""

    frozen_instrument = _candidate_instrument(candidate)
    if not isinstance(observation, ResearchReturnObservation):
        raise TraderLabValidationError(
            "instrument-bound economic reference requires ResearchReturnObservation"
        )
    observation.__post_init__()
    if observation.run != candidate.strategy_binding.run:
        raise TraderLabValidationError(
            "instrument-bound economics must use the exact candidate research run"
        )
    observed_instrument = research_return_instrument(observation)
    if observed_instrument != frozen_instrument:
        raise TraderLabValidationError(
            "economic observation instrument does not match frozen Trader instrument"
        )
    lineage = candidate.strategy_binding.binding_fingerprint.value
    digest = TraderLabEvidenceDigest(
        sha256(
            _canonical_bytes(
                {
                    "schema": "qore.trader_lab.reference.economic_return.instrument.v2",
                    "candidate_fingerprint": candidate.fingerprint.value,
                    "strategy_binding_fingerprint": lineage,
                    "instrument": frozen_instrument.symbol,
                    "observation": list(observation.logical_values()),
                }
            )
        ).hexdigest()
    )
    return _make_self_authenticating_reference(
        kind=TraderLabEvidenceKind.ECONOMIC_EVALUATION,
        reference_id=observation.observation_id.value,
        content_digest=digest,
        schema_version=INSTRUMENT_BOUND_ECONOMIC_SCHEMA,
        strategy_binding_fingerprint=lineage,
    )


def validate_first_cohort_economic_binding(
    candidate: TraderLabCandidateBinding,
    performance: ResearchPerformanceStatisticsSnapshot,
    economic_evidence: TraderLabEvidenceReference,
) -> None:
    """Deep-revalidate one cohort's economics against its exact frozen instrument."""

    frozen_instrument = _candidate_instrument(candidate)
    if not isinstance(performance, ResearchPerformanceStatisticsSnapshot):
        raise TraderLabValidationError(
            "instrument-bound economics require ResearchPerformanceStatisticsSnapshot"
        )
    performance.__post_init__()
    if performance.run != candidate.strategy_binding.run:
        raise TraderLabValidationError(
            "instrument-bound performance run must match the candidate"
        )
    validate_trader_lab_evidence_reference(
        economic_evidence,
        field_name="first-cohort economic evidence",
    )
    if economic_evidence.kind is not TraderLabEvidenceKind.ECONOMIC_EVALUATION:
        raise TraderLabValidationError(
            "first-cohort economic evidence must be ECONOMIC_EVALUATION"
        )
    if economic_evidence.schema_version != INSTRUMENT_BOUND_ECONOMIC_SCHEMA:
        raise TraderLabValidationError(
            "first-cohort economics require instrument-bound v2 evidence"
        )
    if (
        economic_evidence.strategy_binding_fingerprint
        != candidate.strategy_binding.binding_fingerprint.value
    ):
        raise TraderLabValidationError(
            "first-cohort economics must match candidate strategy lineage"
        )

    for observation in performance.observations:
        if research_return_instrument(observation) != frozen_instrument:
            raise TraderLabValidationError(
                "performance observations must all use the frozen Trader instrument"
            )

    matches = tuple(
        observation
        for observation in performance.observations
        if observation.observation_id.value == economic_evidence.reference_id
    )
    if len(matches) != 1:
        raise TraderLabValidationError(
            "economic evidence must identify exactly one retained performance observation"
        )
    expected = reference_instrument_bound_research_economic(candidate, matches[0])
    if expected != economic_evidence:
        raise TraderLabValidationError(
            "economic evidence digest does not match retained instrument-bound observation"
        )
