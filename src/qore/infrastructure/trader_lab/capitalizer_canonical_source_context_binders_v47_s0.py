"""Causal source-context binders for Capitalizer V47-S0.

These binders turn provider-native M1 history into canonical H1 and M15
observations without opening strategy economics. They deliberately reuse the
already-frozen source detectors and the V46 provider reconstruction semantics.

Frozen parent contract: PR #623 comment 5889541472.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_canonical_structural_targets_v47_s0 as structural_targets,
)
from qore.infrastructure.trader_lab import (
    capitalizer_native_source_fact_remediation_v46 as remediation,
)
from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3_source,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    AggregatedBar,
    _aggregate_h1,
)
from qore.infrastructure.trader_lab.capitalizer_native_source_fact_remediation_v46 import (
    CapitalizerHTFPOIContext,
)
from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    CapitalizerCISDObservation,
    detect_cisd,
)
from qore.infrastructure.trader_lab.capitalizer_source_daily_bias_v2 import (
    CapitalizerDailyBiasObservation,
    derive_daily_bias,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingObservation,
    CapitalizerProtectedSwingOrigin,
    CapitalizerSourceBar,
    CapitalizerSourceClosureObservation,
    CapitalizerSourceDirection,
    confirm_protected_swing,
    detect_candle2_reversal_closure,
    detect_candle3_confirmation,
)
from qore.infrastructure.trader_lab.capitalizer_source_poi_v2 import (
    CapitalizerSourcePOI,
    CapitalizerSourcePOIKind,
    bar_interacts_with_poi,
    detect_external_liquidity_swing,
    detect_fair_value_gap,
)
from qore.infrastructure.trader_lab.capitalizer_source_structural_extraction_v2 import (
    protected_swing_from_cisd,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    _aggregate_tf,
)

PARENT_IDENTITY = "QORE_CAPITALIZER_CANONICAL_SOURCE_CANDIDATE_ASSEMBLY_V47_S0"


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("V47-S0 context binder requires aware timestamp")
    return value


def _compatible(
    poi: CapitalizerSourcePOI,
    direction: CapitalizerSourceDirection,
) -> bool:
    if direction is CapitalizerSourceDirection.BULLISH:
        return poi.kind in {
            CapitalizerSourcePOIKind.BULLISH_FVG,
            CapitalizerSourcePOIKind.SWING_LOW,
        }
    return poi.kind in {
        CapitalizerSourcePOIKind.BEARISH_FVG,
        CapitalizerSourcePOIKind.SWING_HIGH,
    }


@dataclass(frozen=True, slots=True)
class S0HTFContext:
    confirmed_at: datetime
    closure: CapitalizerSourceClosureObservation
    daily_bias: CapitalizerDailyBiasObservation
    poi_context: CapitalizerHTFPOIContext
    causal: bool = True

    def __post_init__(self) -> None:
        _aware(self.confirmed_at)
        if not self.closure.source_rule_satisfied:
            raise ValueError("S0 HTF context requires source-valid closure")
        if not self.poi_context.present:
            raise ValueError("S0 HTF context requires bound POI")
        if not self.causal:
            raise ValueError("S0 HTF context cannot be non-causal")


@dataclass(frozen=True, slots=True)
class S0CISDBinding:
    confirmed_at: datetime
    cisd: CapitalizerCISDObservation
    protected_swing: CapitalizerProtectedSwingObservation
    causal_series: tuple[CapitalizerSourceBar, ...]
    causal: bool = True

    def __post_init__(self) -> None:
        _aware(self.confirmed_at)
        if not self.cisd.setup_confirmed:
            raise ValueError("S0 CISD binding requires setup-confirmed CISD")
        if not self.protected_swing.confirmed:
            raise ValueError("S0 CISD binding requires protected swing")
        if not self.causal_series:
            raise ValueError("S0 CISD binding requires causal series")
        if not self.causal:
            raise ValueError("S0 CISD binding cannot be non-causal")


@dataclass(frozen=True, slots=True)
class S0M1StructureBinding:
    confirmed_at: datetime
    m1_mss: remediation.CapitalizerM1MSSObservation
    m1_cisd: CapitalizerCISDObservation
    protected_swing: CapitalizerProtectedSwingObservation
    order_block: remediation.CapitalizerM1OrderBlockObservation
    causal_series: tuple[CapitalizerSourceBar, ...]
    confirmation_bar: CapitalizerSourceBar
    fvg_confirmed: bool
    source_zone_bound: bool
    causal: bool = True

    def __post_init__(self) -> None:
        _aware(self.confirmed_at)
        if not self.m1_mss.confirmed:
            raise ValueError("S0 M1 structure requires confirmed MSS")
        if not self.m1_cisd.setup_confirmed:
            raise ValueError("S0 M1 structure requires setup-confirmed CISD")
        if not self.protected_swing.confirmed:
            raise ValueError("S0 M1 structure requires M1 protected swing")
        if not self.order_block.confirmed:
            raise ValueError("S0 M1 structure requires validated order block")
        if not self.causal_series:
            raise ValueError("S0 M1 structure requires causal series")
        if not self.fvg_confirmed or not self.source_zone_bound:
            raise ValueError("S0 M1 structure requires bound FVG/OB source zone")
        if not self.causal:
            raise ValueError("S0 M1 structure cannot be non-causal")


@dataclass(frozen=True, slots=True)
class S0SourceContextBinding:
    decision_at: datetime
    direction: CapitalizerSourceDirection
    htf: S0HTFContext
    m15: S0CISDBinding
    structural_target: structural_targets.S0StructuralTargetBinding
    causal: bool = True

    def __post_init__(self) -> None:
        decision = _aware(self.decision_at)
        if self.htf.confirmed_at > decision or self.m15.confirmed_at > decision:
            raise ValueError("S0 source context cannot use future confirmation")
        if self.htf.closure.direction is not self.direction:
            raise ValueError("S0 HTF closure direction drift")
        if self.htf.daily_bias.direction is not self.direction:
            raise ValueError("S0 daily bias direction drift")
        if self.m15.cisd.direction is not self.direction:
            raise ValueError("S0 M15 CISD direction drift")
        if self.m15.protected_swing.direction is not self.direction:
            raise ValueError("S0 protected swing direction drift")
        resolution = self.structural_target.resolution
        observation = resolution.observation
        if not resolution.resolved or observation is None:
            raise ValueError("S0 source context requires resolved structural target")
        if observation.direction is not self.direction:
            raise ValueError("S0 structural target direction drift")
        if not self.causal:
            raise ValueError("S0 source context cannot be non-causal")


@dataclass(frozen=True, slots=True)
class _HTFEvent:
    confirmed_at: datetime
    closure: CapitalizerSourceClosureObservation
    pois: tuple[CapitalizerSourcePOI, ...]


def _confirmed_h1(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    decision_at: datetime,
) -> tuple[AggregatedBar, ...]:
    decision = _aware(decision_at)
    # Aggregate from the immutable full source first, then retain only H1
    # candles whose provider-derived close is already known by decision time.
    return tuple(
        bar
        for bar in _aggregate_h1(bars)
        if bar.closed_at <= decision
    )


def _htf_events(
    h1: tuple[AggregatedBar, ...],
) -> tuple[_HTFEvent, ...]:
    if len(h1) < 3:
        return ()

    pois_by_confirm_index: dict[int, list[CapitalizerSourcePOI]] = {}
    for center in range(1, len(h1) - 1):
        left = h1[center - 1].source
        middle = h1[center].source
        right = h1[center + 1].source
        detected: list[CapitalizerSourcePOI] = []
        fvg = detect_fair_value_gap(
            candle1=left,
            candle2=middle,
            candle3=right,
        )
        if fvg is not None:
            detected.append(fvg)
        swing = detect_external_liquidity_swing(
            left=left,
            center=middle,
            right=right,
        )
        if swing is not None:
            detected.append(swing)
        if detected:
            pois_by_confirm_index[center + 1] = detected

    active_pois: list[CapitalizerSourcePOI] = []
    events: list[_HTFEvent] = []
    previous_interacted: tuple[CapitalizerSourcePOI, ...] = ()
    previous_c2_confirmed = False

    for index in range(1, len(h1)):
        # A POI confirmed by a three-bar pattern becomes usable only after
        # its right-hand confirming H1 has closed. Matching the existing
        # scanner, do not let the current H1 create its own prerequisite POI.
        for poi in pois_by_confirm_index.get(index - 1, ()):
            active_pois.append(poi)

        current = h1[index]
        previous = h1[index - 1]

        if index >= 2:
            c3 = detect_candle3_confirmation(
                candle2=previous.source,
                candle3=current.source,
                point_of_interest_present=bool(previous_interacted),
                candle2_reversal_already_confirmed=previous_c2_confirmed,
            )
            if c3 is not None and c3.source_rule_satisfied:
                compatible = tuple(
                    poi
                    for poi in previous_interacted
                    if _compatible(poi, c3.direction)
                )
                if compatible:
                    events.append(
                        _HTFEvent(
                            confirmed_at=current.closed_at,
                            closure=c3,
                            pois=compatible,
                        )
                    )

        bullish = tuple(
            poi
            for poi in active_pois
            if _compatible(poi, CapitalizerSourceDirection.BULLISH)
            and bar_interacts_with_poi(bar=current.source, poi=poi)
        )
        bearish = tuple(
            poi
            for poi in active_pois
            if _compatible(poi, CapitalizerSourceDirection.BEARISH)
            and bar_interacts_with_poi(bar=current.source, poi=poi)
        )
        interacted = bullish + bearish

        c2 = detect_candle2_reversal_closure(
            previous=previous.source,
            candle2=current.source,
            point_of_interest_present=bool(interacted),
        )
        current_c2_confirmed = False
        if c2 is not None and c2.source_rule_satisfied:
            compatible = (
                bullish
                if c2.direction is CapitalizerSourceDirection.BULLISH
                else bearish
            )
            current_c2_confirmed = bool(compatible)
            if compatible:
                events.append(
                    _HTFEvent(
                        confirmed_at=current.closed_at,
                        closure=c2,
                        pois=compatible,
                    )
                )

        previous_interacted = interacted
        previous_c2_confirmed = current_c2_confirmed

    return tuple(sorted(events, key=lambda item: item.confirmed_at))


def bind_latest_h1_context(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    decision_at: datetime,
) -> S0HTFContext | None:
    """Bind the latest causal H1 C2/C3 closure-at-POI before a decision."""

    decision = _aware(decision_at)
    events = tuple(
        event
        for event in _htf_events(
            _confirmed_h1(bars, decision_at=decision)
        )
        if event.confirmed_at <= decision
    )
    if not events:
        return None
    event = events[-1]
    bias = derive_daily_bias(event.closure)
    # The event POIs were already proven interacting with the actual
    # completed H1 candle; retain that authentic causal set directly.
    context = CapitalizerHTFPOIContext(
        present=True,
        interacting_pois=event.pois,
    )
    return S0HTFContext(
        confirmed_at=event.confirmed_at,
        closure=event.closure,
        daily_bias=bias,
        poi_context=context,
    )


def _opposing(
    bar: CapitalizerSourceBar,
    direction: CapitalizerSourceDirection,
) -> bool:
    if bar.close == bar.open:
        return False
    if direction is CapitalizerSourceDirection.BULLISH:
        return bar.close < bar.open
    return bar.close > bar.open


def _series_extreme(
    series: tuple[CapitalizerSourceBar, ...],
    direction: CapitalizerSourceDirection,
) -> Decimal:
    if direction is CapitalizerSourceDirection.BULLISH:
        return min(bar.low for bar in series)
    return max(bar.high for bar in series)


def bind_first_m15_cisd(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    direction: CapitalizerSourceDirection,
    higher_timeframe_closure: CapitalizerSourceClosureObservation,
    important_pois: tuple[CapitalizerSourcePOI, ...],
    after: datetime,
    before: datetime,
) -> S0CISDBinding | None:
    """Bind first M15 opposing-series CISD after the causal HTF boundary."""

    after_at = _aware(after)
    before_at = _aware(before)
    if before_at < after_at:
        raise ValueError("S0 M15 CISD before must be >= after")

    frames = tuple(
        frame
        for frame in _aggregate_tf(bars, minutes=15)
        if frame.closed_at <= before_at
    )
    for index, confirmation in enumerate(frames):
        if confirmation.closed_at <= after_at:
            continue

        cursor = index - 1
        if cursor < 0 or not _opposing(frames[cursor].source, direction):
            continue
        start = cursor
        while (
            start > 0
            and frames[start - 1].closed_at > after_at
            and _opposing(frames[start - 1].source, direction)
        ):
            start -= 1
        series_frames = tuple(
            frame
            for frame in frames[start:index]
            if frame.opened_at >= after_at
        )
        if not series_frames:
            continue
        series = tuple(frame.source for frame in series_frames)
        important_level_reached = any(
            bar_interacts_with_poi(bar=bar, poi=poi)
            for bar in (*series, confirmation.source)
            for poi in important_pois
        )
        observed = detect_cisd(
            causal_series=series,
            confirmation_bar=confirmation.source,
            direction=direction,
            important_level_reached=important_level_reached,
            higher_timeframe_closure=higher_timeframe_closure,
        )
        if not observed.setup_confirmed:
            continue
        swing = confirm_protected_swing(
            direction=direction,
            swing_price=_series_extreme(series, direction),
            origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
            closure_through_causal_series_confirmed=True,
        )
        return S0CISDBinding(
            confirmed_at=confirmation.closed_at,
            cisd=observed,
            protected_swing=swing,
            causal_series=series,
        )
    return None


def _m1_source(bar: CapitalizerM1Bar) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
    )


def _opposing_m1(
    bar: CapitalizerM1Bar,
    direction: CapitalizerSourceDirection,
) -> bool:
    return _opposing(_m1_source(bar), direction)


def bind_m1_source_structure(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    direction: CapitalizerSourceDirection,
    higher_timeframe_closure: CapitalizerSourceClosureObservation,
    zone: v3_source.M1EntryZone,
    after: datetime,
    before: datetime,
) -> S0M1StructureBinding | None:
    """Bind M1 CISD/MSS/FVG/OB and the canonical M1 protected swing.

    The protected stop anchor is extracted from the M1 CISD causal series,
    matching the source-observation/trade-plan contract. The M15 swing is not
    promoted to the canonical stop.
    """

    after_at = _aware(after)
    before_at = _aware(before)
    if before_at < after_at:
        raise ValueError("S0 M1 structure before must be >= after")
    ordered = tuple(sorted(bars, key=lambda row: row.opened_at))
    if ordered != bars:
        raise ValueError("S0 M1 structure requires chronological bars")
    causal = tuple(row for row in bars if row.closed_at <= before_at)
    if not causal:
        return None

    ob_index = next(
        (
            index
            for index, row in enumerate(causal)
            if row.opened_at == zone.ob_opened_at
        ),
        None,
    )
    if ob_index is None:
        return None
    if causal[ob_index].closed_at <= after_at:
        return None

    series_rows: list[CapitalizerM1Bar] = []
    cursor = ob_index
    while cursor < len(causal) and _opposing_m1(causal[cursor], direction):
        if causal[cursor].closed_at > after_at:
            series_rows.append(causal[cursor])
        cursor += 1
    if not series_rows or cursor >= len(causal):
        return None
    confirmation = causal[cursor]
    if confirmation.closed_at > before_at:
        return None

    series = tuple(_m1_source(row) for row in series_rows)
    source_zone_bound = series_rows[0].opened_at == zone.ob_opened_at
    cisd = detect_cisd(
        causal_series=series,
        confirmation_bar=_m1_source(confirmation),
        direction=direction,
        important_level_reached=source_zone_bound,
        higher_timeframe_closure=higher_timeframe_closure,
    )
    if not cisd.setup_confirmed:
        return None

    mss = remediation.detect_m1_mss(
        bars=causal,
        direction=direction,
        after=confirmation.opened_at,
        before=before_at,
    )
    if not mss.confirmed or mss.confirmed_at is None:
        return None
    if mss.confirmed_at < confirmation.closed_at:
        return None
    if zone.fvg_confirmed_at > mss.confirmed_at:
        return None

    protected = protected_swing_from_cisd(
        cisd=cisd,
        causal_series=series,
        confirmation_bar=_m1_source(confirmation),
        origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
    )
    order_block = remediation.assess_m1_order_block(
        direction=direction,
        causal_series=series,
        poi_reached=source_zone_bound,
        cisd=cisd,
    )
    if not order_block.confirmed:
        return None

    return S0M1StructureBinding(
        confirmed_at=mss.confirmed_at,
        m1_mss=mss,
        m1_cisd=cisd,
        protected_swing=protected,
        order_block=order_block,
        causal_series=series,
        confirmation_bar=_m1_source(confirmation),
        fvg_confirmed=True,
        source_zone_bound=source_zone_bound,
    )


def bind_canonical_source_context(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    direction: CapitalizerSourceDirection,
    entry_price: Decimal,
    decision_at: datetime,
    source_opposite_boundary: (
        structural_targets.S0SourceOppositeBoundary | None
    ) = None,
) -> S0SourceContextBinding | None:
    """Compose the causal HTF/M15/stop/target chain used by S0 assembly.

    This binder is deliberately pre-economic. It returns only when every
    source-context dependency is directionally aligned and known no later than
    the decision timestamp.
    """

    decision = _aware(decision_at)
    htf = bind_latest_h1_context(bars, decision_at=decision)
    if htf is None:
        return None
    if (
        htf.closure.direction is not direction
        or htf.daily_bias.direction is not direction
    ):
        return None

    m15 = bind_first_m15_cisd(
        bars,
        direction=direction,
        higher_timeframe_closure=htf.closure,
        important_pois=htf.poi_context.interacting_pois,
        after=htf.confirmed_at,
        before=decision,
    )
    if m15 is None:
        return None

    target = structural_targets.bind_structural_target(
        bars,
        direction=direction,
        entry_price=entry_price,
        decision_at=decision,
        source_opposite_boundary=source_opposite_boundary,
    )
    if not target.resolution.resolved:
        return None

    return S0SourceContextBinding(
        decision_at=decision,
        direction=direction,
        htf=htf,
        m15=m15,
        structural_target=target,
    )
