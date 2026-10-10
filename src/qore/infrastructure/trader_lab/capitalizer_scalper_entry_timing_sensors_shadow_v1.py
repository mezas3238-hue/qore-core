"""Predecision, non-executing QORE Scalper H1/M15/M1 entry sensor panel.

Every feature can be evaluated as the NEXT M1 candle closes, before any
future return, target hit, H1 future expiry or trade settlement exists.
Source CISD confirmation is a *methodology event*, NOT proven good timing.
Research-only panel; does not authorize, rank, veto, or size any trade.

The V49 source detectors remain unmodified. Qualitative sensor conditions
are observability/evidence labels only, never trained cutoffs or trade gates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from statistics import median

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import (
    CapitalizerSide,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_h1_timing_session_diagnostic_v1 import (
    h1_observed_position,
    session_end_at,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
    CapitalizerSourcePOIKind,
    bar_interacts_with_poi,
    detect_fair_value_gap,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_m1_cisd_observer_v48 import (
    _pivot_indices,
    _series_ending_at,
    observe_first_m1_cisd,
)
from qore.infrastructure.trader_lab.capitalizer_ttrades_m1_fvg_cisd_continuation_v48 import (
    _source_bar,
    observe_first_m1_fvg_cisd_continuation,
)

IDENTITY = "QORE_SCALPER_ENTRY_TIMING_SENSORS_SHADOW_V1"


class SensorStatus(StrEnum):
    OBSERVED = "OBSERVED"
    DEVELOPING = "DEVELOPING"
    NOT_OBSERVED = "NOT_OBSERVED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    CONTRADICTORY = "CONTRADICTORY"


@dataclass(frozen=True, slots=True)
class EntrySensorInput:
    """Authority-limited facts all supplied at or before this M1 decision.

    No original V49 h1_state_until or future trade fields are accepted.
    M15 stop and H1 basis are upstream declarations: *not* re-attested by
    this M1-only module. A1 Master Frame must verify their own source chain.
    """

    symbol: str
    session: str
    decision_at: datetime
    h1_direction: str
    h1_basis: str
    h1_confirmed_at: datetime
    m15_confirmed_at: datetime
    m15_protected_stop: Decimal
    m1_bars: tuple[CapitalizerM1Bar, ...]
    witnessed_h1_target: Decimal | None = None
    h1_target_confirmed_at: datetime | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    commission_round_trip_per_lot: Decimal | None = None

    def __post_init__(self) -> None:
        for moment in (self.decision_at, self.h1_confirmed_at, self.m15_confirmed_at):
            if moment.utcoffset() is None:
                raise ValueError("all sensor timestamps must be aware")
        if not self.h1_confirmed_at <= self.m15_confirmed_at < self.decision_at:
            raise ValueError("upstream H1/M15 confirmations must precede decision")
        if self.h1_direction not in ("BULLISH", "BEARISH"):
            raise ValueError("unknown H1 source direction")
        if self.session not in ("ASIA", "LONDON", "NEW_YORK"):
            raise ValueError("unsupported NY scalper session")
        if not self.symbol or not self.h1_basis or self.m15_protected_stop <= 0:
            raise ValueError("missing upstream provenance or M15 stop")
        if not self.m1_bars:
            raise ValueError("M1 evidence required")
        if any(b.symbol != self.symbol for b in self.m1_bars):
            raise ValueError("M1 symbol mismatch")
        if any(
            b.opened_at >= b.closed_at or b.closed_at > self.decision_at
            for b in self.m1_bars
        ):
            raise ValueError("future/inflight M1 data forbidden")
        if any(
            self.m1_bars[i].opened_at >= self.m1_bars[i + 1].opened_at
            for i in range(len(self.m1_bars) - 1)
        ):
            raise ValueError("M1 must be chronological without duplicate bar")
        if self.m1_bars[-1].closed_at != self.decision_at:
            raise ValueError("decision must match the last CLOSED M1 bar")
        if (self.witnessed_h1_target is None) != (
            self.h1_target_confirmed_at is None
        ):
            raise ValueError("H1 target must carry its causal witness timestamp")
        if self.h1_target_confirmed_at is not None:
            if (
                self.h1_target_confirmed_at.utcoffset() is None
                or self.h1_target_confirmed_at > self.decision_at
                or self.witnessed_h1_target is None
                or self.witnessed_h1_target <= 0
            ):
                raise ValueError("H1 target lacks a confirmed as-of witness")
        if (self.bid is None) != (self.ask is None):
            raise ValueError("cannot use incomplete broker bid/ask")
        if self.bid is not None and self.ask is not None and not (
            0 < self.bid < self.ask
        ):
            raise ValueError("invalid broker quotes")
        if (
            self.commission_round_trip_per_lot is not None
            and self.commission_round_trip_per_lot < 0
        ):
            raise ValueError("negative broker commission invalid")


@dataclass(frozen=True, slots=True)
class SensorEvidence:
    sensor: str
    status: SensorStatus
    observed_at: str
    value: str | None
    explanation: str
    provenance: str

    def __post_init__(self) -> None:
        if not self.sensor or not self.explanation or not self.provenance:
            raise ValueError("sensor requires explanation and evidence provenance")


@dataclass(frozen=True, slots=True)
class EntrySensorFrame:
    identity: str
    symbol: str
    session: str
    decision_at: str
    h1_direction: str
    sensors: tuple[SensorEvidence, ...]
    first_source_cisd_family: str | None
    first_source_cisd_confirmed_at: str | None
    source_event_observed: bool
    execution_authorized: bool = False
    trade_size_authorized: bool = False
    hard_entry_gate_added: bool = False
    cognitive_master_frame_attested: bool = False
    future_data_consulted: bool = False
    outcome_used: bool = False
    live_authorized: bool = False
    trader_certified: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY or any((
            self.execution_authorized,
            self.trade_size_authorized,
            self.hard_entry_gate_added,
            self.cognitive_master_frame_attested,
            self.future_data_consulted,
            self.outcome_used,
            self.live_authorized,
            self.trader_certified,
        )):
            raise ValueError("research shadow panel cannot grant execution authority")
        if self.source_event_observed != (self.first_source_cisd_family is not None):
            raise ValueError("source CISD event must carry route identity")


def observe_entry_timing_sensors(context: EntrySensorInput) -> EntrySensorFrame:
    """Update all sensor readings on each closed M1 candle.

    Do not feed retrospective directional labels, MFE/MAE or V49 exit reason.
    This panel describes the *state now*; no arbitrary score or trade decision.
    """

    at = context.decision_at
    bars = context.m1_bars
    price = bars[-1].close
    bullish = context.h1_direction == "BULLISH"
    if not (context.m15_protected_stop < price if bullish
            else context.m15_protected_stop > price):
        raise ValueError("M15 structural stop no longer on risk side of decision")
    risk = abs(price - context.m15_protected_stop)
    direction = (
        CapitalizerSourceDirection.BULLISH
        if bullish else CapitalizerSourceDirection.BEARISH
    )
    side = CapitalizerSide.LONG if bullish else CapitalizerSide.SHORT
    rows: list[SensorEvidence] = []

    def record(
        key: str, status: SensorStatus, value: str | None,
        explanation: str, provenance: str,
    ) -> None:
        rows.append(SensorEvidence(
            sensor=key, status=status, observed_at=at.isoformat(),
            value=value, explanation=explanation, provenance=provenance,
        ))

    record("H1_BIAS_DECLARED", SensorStatus.OBSERVED, context.h1_direction,
           "H1 direction declared by source; this panel does not revalidate H1 candles",
           context.h1_basis)
    h1_age = Decimal(str((at - context.h1_confirmed_at).total_seconds())) / 60
    record("H1_THESIS_AGE_MINUTES", SensorStatus.OBSERVED, str(h1_age),
           "Age measured from confirmed origin, NEVER future h1_state_until",
           "h1_confirmed_at")
    m15_age = Decimal(str((at - context.m15_confirmed_at).total_seconds())) / 60
    record("M15_PROTECTED_STOP_DECLARED", SensorStatus.OBSERVED,
           str(context.m15_protected_stop),
           "M15 protected-swing declaration; requires independent M15 source attestation",
           "m15_confirmed_at+m15_protected_stop")
    record("M15_TO_M1_ELAPSED_MINUTES", SensorStatus.OBSERVED, str(m15_age),
           "Elapsed time since M15 source confirmation, not a veto",
           "m15_confirmed_at")
    record("M15_ORIGINAL_RISK_PRICE_DISTANCE", SensorStatus.OBSERVED, str(risk),
           "Stop-to-current-close distance; no risk sizing or broker money inferred",
           "m15_protected_stop+last_closed_m1.close")

    gap_count = sum(
        a.closed_at != b.opened_at for a, b in zip(bars, bars[1:], strict=False)
    )
    record("NATIVE_M1_GAP_COUNT", SensorStatus.OBSERVED, str(gap_count),
           "Source bars may have missing native M1; prices are never interpolated",
           "native_m1.closed_at/opened_at")

    current_hour = tuple(
        b for b in bars
        if b.opened_at >= at.replace(minute=0, second=0, microsecond=0)
    )
    rank, clock, observed_count = h1_observed_position(
        current_hour, at, price, "LONG" if bullish else "SHORT"
    )
    record("H1_CURRENT_CLOCK_FRACTION", SensorStatus.OBSERVED, str(clock),
           "Position in H1 clock, not final H1 candle range",
           "decision_at")
    record(
        "H1_ASOF_PARTIAL_PRICE_RANK",
        SensorStatus.OBSERVED if rank is not None else SensorStatus.NOT_AVAILABLE,
        str(rank) if rank is not None else None,
        f"Directional rank in partial H1 with {observed_count} CLOSED M1 bars",
        "current_H1_closed_M1_only",
    )
    runway = (session_end_at(at, context.session) - at).total_seconds() / 60
    record("SESSION_REMAINING_MINUTES", SensorStatus.OBSERVED, str(runway),
           "Known NY-DST session boundary, not future price reachability",
           "NY_policy_session_clock")

    recent = bars[-20:]
    widths = [b.high - b.low for b in recent]
    typical = median(widths)
    record("M1_LOCAL_MEDIAN_BAR_RANGE", SensorStatus.OBSERVED, str(typical),
           "Median observed M1 high-low; not an uncalibrated hard noise gate",
           "last_20_or_fewer_closed_M1")
    displacement = (price - bars[-1].open) * (1 if bullish else -1)
    record("M1_LAST_BODY_DIRECTIONAL", SensorStatus.OBSERVED,
           str(displacement),
           "Signed completed-M1 candle body vs H1, not a predicted move",
           "last_closed_m1.open/close")

    # Both original route observers are called with ONLY the closed bars
    # available NOW and the already confirmed M15 thesis.
    m1_window = tuple(b for b in bars if b.closed_at > context.m15_confirmed_at)
    sweep = observe_first_m1_cisd(
        m1_window, thesis_at=context.m15_confirmed_at,
        deadline_at=at, side=side,
    )
    fvg = observe_first_m1_fvg_cisd_continuation(
        m1_window, thesis_at=context.m15_confirmed_at,
        deadline_at=at, direction=direction,
    )
    confirmed_routes: list[tuple[datetime, str]] = []
    if sweep.confirmed and sweep.confirmed_at is not None:
        confirmed_routes.append((sweep.confirmed_at, "LIQUIDITY_SWEEP_CISD"))
    if fvg.confirmed and fvg.cisd_confirmed_at is not None:
        confirmed_routes.append((fvg.cisd_confirmed_at, "FVG_RETRACE_CISD"))
    earliest = min(confirmed_routes, key=lambda x: (x[0], x[1])) if confirmed_routes else None

    # The incomplete-route sensors expose AS-OF intermediate observations.
    # They must never pretend that sweep or FVG alone is an executable trade.
    raw_sweep_at: datetime | None = None
    raw_series_at: datetime | None = None
    for i in range(2, len(m1_window)):
        pivots = _pivot_indices(m1_window, before_index=i, side=side)
        if not pivots:
            continue
        pivot = m1_window[pivots[-1]]
        b = m1_window[i]
        was_swept = b.low < pivot.low if bullish else b.high > pivot.high
        if not was_swept:
            continue
        raw_sweep_at = b.closed_at
        series = _series_ending_at(m1_window, end_index=i, side=side)
        if series:
            raw_series_at = m1_window[series[-1]].closed_at
        break
    record("M1_SWEEP_OBSERVED",
           SensorStatus.OBSERVED if raw_sweep_at is not None
           else SensorStatus.NOT_OBSERVED,
           raw_sweep_at.isoformat() if raw_sweep_at is not None else None,
           "Observed closed-M1 local sweep; not an entry or protected pivot",
           "original_sweep_pivot_observer")
    record("M1_OPPOSING_SERIES",
           SensorStatus.OBSERVED if sweep.confirmed
           else SensorStatus.DEVELOPING if raw_series_at is not None
           else SensorStatus.NOT_OBSERVED,
           str(sweep.causal_series_open) if sweep.confirmed else (
               raw_series_at.isoformat() if raw_series_at is not None else None
           ),
           "Series of opposite candles is NOT a sweep high/low; requires close-through",
           "original_sweep_CISD_series")
    record(
        "M1_SWEEP_CISD_CLOSED",
        SensorStatus.OBSERVED if sweep.confirmed else SensorStatus.DEVELOPING,
        sweep.confirmed_at.isoformat() if sweep.confirmed_at is not None else None,
        f"Actual first source sweep observer status: {sweep.status.value}",
        "observe_first_m1_cisd",
    )

    fvg_formed_at: datetime | None = None
    fvg_retest_at: datetime | None = None
    kind = CapitalizerSourcePOIKind.BULLISH_FVG if bullish else (
        CapitalizerSourcePOIKind.BEARISH_FVG
    )
    for i in range(2, len(m1_window)):
        poi = detect_fair_value_gap(
            candle1=_source_bar(m1_window[i - 2]),
            candle2=_source_bar(m1_window[i - 1]),
            candle3=_source_bar(m1_window[i]),
        )
        if poi is None or poi.kind is not kind:
            continue
        fvg_formed_at = m1_window[i].closed_at
        for b in m1_window[i + 1:]:
            if bar_interacts_with_poi(bar=_source_bar(b), poi=poi):
                fvg_retest_at = b.closed_at
                break
        break
    record("M1_FVG_FORMED", SensorStatus.OBSERVED
           if fvg_formed_at is not None else SensorStatus.NOT_OBSERVED,
           fvg_formed_at.isoformat() if fvg_formed_at is not None else None,
           "Confirmed three-bar directional M1 FVG, not a buy/sell command",
           "detect_fair_value_gap")
    record("M1_FVG_RETRACE",
           SensorStatus.OBSERVED if fvg_retest_at is not None
           else SensorStatus.DEVELOPING if fvg_formed_at is not None
           else SensorStatus.NOT_OBSERVED,
           fvg_retest_at.isoformat() if fvg_retest_at is not None else None,
           "Retest of first as-of FVG; first valid route may use a later FVG",
           "bar_interacts_with_poi")
    record("M1_FVG_CISD_CLOSED",
           SensorStatus.OBSERVED if fvg.confirmed else SensorStatus.DEVELOPING,
           fvg.cisd_confirmed_at.isoformat()
           if fvg.cisd_confirmed_at is not None else None,
           "Original FVG retrace + structural CISD, not a simulated new order",
           "observe_first_m1_fvg_cisd_continuation")
    record("M1_PROTECTED_SWING_ATTESTATION", SensorStatus.NOT_AVAILABLE,
           None,
           "Sweep route has no independent M1 protected swing witness; FVG "
           "pivot is only protected at structural CISD, and must be attested "
           "with local structural observer, never inferred from sweep alone",
           "source_observer_contract")

    if context.witnessed_h1_target is not None:
        distance = (
            context.witnessed_h1_target - price
            if bullish else price - context.witnessed_h1_target
        )
        record(
            "H1_TARGET_ROOM_R",
            SensorStatus.OBSERVED if distance > 0
            else SensorStatus.CONTRADICTORY,
            str(distance / risk),
            "Distance to provided causal H1 witness (not target-selection gate)",
            "h1_target_confirmed_at",
        )
    else:
        record("H1_TARGET_ROOM_R", SensorStatus.NOT_AVAILABLE, None,
               "No independently witnessed H1 liquidity destination",
               "unavailable_external_liquidity_witness")
    record("BROKER_BID_ASK_SPREAD",
           SensorStatus.OBSERVED if context.bid is not None
           else SensorStatus.NOT_AVAILABLE,
           str(context.ask - context.bid)
           if context.bid is not None and context.ask is not None else None,
           "Observed bid-ask distance; do not confuse quote with executable fill",
           "broker_bid_ask_or_unavailable")
    record("BROKER_COMMISSION_PER_LOT",
           SensorStatus.OBSERVED
           if context.commission_round_trip_per_lot is not None
           else SensorStatus.NOT_AVAILABLE,
           str(context.commission_round_trip_per_lot)
           if context.commission_round_trip_per_lot is not None else None,
           "Commission alone does not prove QDLE lot sizing or effective R",
           "broker_account_fee_schedule_or_unavailable")
    record("FULL_COGNITIVE_MASTER_FRAME", SensorStatus.NOT_AVAILABLE, None,
           "Read-only methodology panel; A1 must attest full as-of Master Frame",
           "A1_cognitive_integration_pending")
    record("ACTUAL_M15_STRUCTURE_REVALIDATION", SensorStatus.NOT_AVAILABLE, None,
           "Requires native M15 POI/protected swing causal witness; stop was declared",
           "M15_raw_attestation_pending")
    record("SOURCE_SIGNAL_OBSERVED",
           SensorStatus.OBSERVED if earliest is not None
           else SensorStatus.DEVELOPING,
           earliest[1] if earliest is not None else None,
           "First confirmed source route is NOT an economically validated entry",
           "V49_two_alternative_route_detectors")
    return EntrySensorFrame(
        identity=IDENTITY, symbol=context.symbol,
        session=context.session, decision_at=at.isoformat(),
        h1_direction=context.h1_direction, sensors=tuple(rows),
        first_source_cisd_family=earliest[1] if earliest is not None else None,
        first_source_cisd_confirmed_at=earliest[0].isoformat()
        if earliest is not None else None,
        source_event_observed=earliest is not None,
    )
