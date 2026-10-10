"""ACTUAL A2 as-of M1 sensors -> A1 nine-market full frame -> PAPER trades.

No fabricated epistemic readiness, nine-market data, broker quotes or as-of
target witnesses. A1 externally attested world/H1/M15 hypotheses remain
authoritative. A2 sensor evidence is bound to EVERY source hypothesis and
forwarded as source-tagged cognitive observation tokens; the sensor-to-original
CISD family/time mismatch is a provenance warning, NOT an automatic veto.

A1 full frame then decides PASS/WAIT/ABSTAIN before PAPER intent selection.
This file does NOT synthesize the nine-market barrier inputs from source
opportunities; an upstream evidence collector must provide observed native
M1, world, nine perceptions/regimes/causal graph/pressure and actual causal
H1/M15 hypothesis witnesses.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from qore.infrastructure.trader_lab.capitalizer_a1_master_frame_paper_trader_integration_v1 import (
    A1PaperSource,
    A1PaperTraderReport,
    run_real_master_frame_paper_trader,
)
from qore.infrastructure.trader_lab.capitalizer_a1_multi_hypothesis_research import (
    A1MultiHypothesisBarrier,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_entry_timing_sensors_shadow_v1 import (
    EntrySensorInput,
    observe_entry_timing_sensors,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_sensor_master_frame_bridge_v1 import (
    bind_scalper_sensors_into_master_context,
)


@dataclass(frozen=True, slots=True)
class A1SensorizedPaperBridgeResult:
    report: A1PaperTraderReport
    observed_sensor_frames: int
    source_cisd_identity_conflicts: int
    full_master_frame_invoked: bool
    sensors_reached_full_master_frame: bool
    automatically_vetoed_cisd_conflicts: bool = False
    synthetic_nine_market_world_created: bool = False
    virtual_broker_quotes_created: bool = False
    live_authorized: bool = False

    def __post_init__(self) -> None:
        if (
            self.automatically_vetoed_cisd_conflicts
            or self.synthetic_nine_market_world_created
            or self.virtual_broker_quotes_created
            or self.live_authorized
        ):
            raise ValueError("sensorized research bridge cannot fake observations or order")


def run_sensorized_master_frame_paper(
    *,
    barriers: tuple[A1MultiHypothesisBarrier, ...],
    source_evidence: Mapping[str, EntrySensorInput],
    source_originals: tuple[A1PaperSource, ...],
    baseline_selected_source_ids: tuple[str, ...],
) -> A1SensorizedPaperBridgeResult:
    """Run 9-market A1 cognition with genuine A2 sensor observations per source."""

    if not barriers:
        raise ValueError("observed nine-market barriers missing")
    expected = {
        row.source_opportunity_id for row in source_originals
    }
    if (
        len(expected) != len(source_originals)
        or set(source_evidence) != expected
    ):
        raise ValueError("A2 sensors must have exactly the original source IDs")
    source_table = {
        row.source_opportunity_id: row for row in source_originals
    }
    observed = 0
    conflicts = 0
    wrapped_barriers: list[A1MultiHypothesisBarrier] = []
    for barrier in barriers:
        alternatives = []
        for alt in barrier.alternatives:
            sid = alt.binding.source_opportunity_id
            if sid not in source_evidence:
                raise ValueError("M1 source missing from complete as-of source feed")
            value = source_evidence[sid]
            if (
                value.symbol != alt.binding.symbol
                or value.decision_at != barrier.observed_at
                or value.h1_confirmed_at != alt.h1_confirmed_at
                or value.m15_confirmed_at != alt.m15_confirmed_at
                or alt.context.observed_at != barrier.observed_at
            ):
                raise ValueError("sensor does not match exact H1/M15/M1 decision frontier")
            historical = source_table[sid].trade
            if (
                value.m15_protected_stop != historical.stop_price
                and str(value.m15_protected_stop) != historical.stop_price
            ):
                raise ValueError("M15 stop from sensor differs from original V49")
            if value.m1_bars[-1].close != historical.entry_price:
                raise ValueError("M1 decision close differs from original V49 fill")
            if (value.h1_direction == "BULLISH") != (historical.direction == "LONG"):
                raise ValueError("sensor H1 bias conflicts with original trade direction")
            frame = observe_entry_timing_sensors(value)
            binding = bind_scalper_sensors_into_master_context(frame)
            if binding.grants_entry_authority:
                raise ValueError("read-only A2 sensor grant is illegal")
            match = (
                frame.first_source_cisd_confirmed_at == barrier.observed_at.isoformat()
                and frame.first_source_cisd_family == historical.trigger_family
            )
            conflict = not match
            conflicts += int(conflict)
            observed += 1
            # Never alter A1's independently proven H1/M15/HTF target truths:
            # the A2 frame only carries what is observable from its own M1
            # and honestly marks raw-M15/HTF target proof as unavailable.
            # Prematurely treating those missing sensor fields as disproving
            # a separately attested A1 source would reject nearly all trades.
            if not alt.context.evidence_provenance_complete:
                raise ValueError("A1 native H1/M15 provenance independently incomplete")
            if alt.context.symbol != frame.symbol:
                raise ValueError("A1 source symbol differs from as-of sensor")
            tokens = (
                *alt.context.observation_tokens,
                *binding.context.observation_tokens,
                f"SCALPER_SENSOR_SOURCE_CISD_MATCH={not conflict}",
                "SCALPER_SENSOR_DIFFERENCE_NOT_A_GATE=YES",
            )
            alternatives.append(replace(
                alt, context=replace(alt.context, observation_tokens=tokens),
            ))
        wrapped_barriers.append(replace(
            barrier, alternatives=tuple(alternatives),
        ))
    if observed != len(expected):
        raise ValueError("some original source IDs were never cognitively evaluated")
    result = run_real_master_frame_paper_trader(
        barriers=tuple(wrapped_barriers),
        original_sources=source_originals,
        baseline_selected_source_ids=baseline_selected_source_ids,
    )
    if (
        not result.all_sensor_inputs_evidenced
        or not result.nine_market_frame_per_candidate
        or result.source_candidates_seen != observed
    ):
        raise ValueError("A2 sensors never reached full A1 frame for every source")
    return A1SensorizedPaperBridgeResult(
        report=result,
        observed_sensor_frames=observed,
        source_cisd_identity_conflicts=conflicts,
        full_master_frame_invoked=True,
        sensors_reached_full_master_frame=True,
    )
