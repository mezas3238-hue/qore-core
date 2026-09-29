"""V47-S2 canonical source-composition remediation.

Repairs composition defects proven by V47-S1/S1R before economics:
- source event stops at sweep -> M5 closeback -> M3 MSS;
- event-specific opposite boundary restores source target identity;
- M15 does not have to re-touch the exact retained H1 POI;
- M1 is independently reconstructed after upstream source + M15;
- FRACTAL candidate is then passed back through the frozen S0/V46 contracts.

No outcome, economics, Fresh Holdout or execution authority is present here.

Frozen by PR #623 comment 5900501860.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_canonical_source_candidate_assembly_v47_s0 as s0,
)
from qore.infrastructure.trader_lab import (
    capitalizer_canonical_source_context_binders_v47_s0 as context_binders,
)
from qore.infrastructure.trader_lab import (
    capitalizer_canonical_structural_targets_v47_s0 as structural_targets,
)
from qore.infrastructure.trader_lab import (
    capitalizer_event_opposite_boundary_v47_s1r_e as opposite_boundary,
)
from qore.infrastructure.trader_lab import (
    capitalizer_native_source_fact_remediation_v46 as remediation,
)
from qore.infrastructure.trader_lab import (
    capitalizer_owner_h1_m3_m1_causal_reversal_1y_v3 as v3_source,
)
from qore.infrastructure.trader_lab import (
    capitalizer_source_strategy_isolation_v47_s1 as s1,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_full_ict_density_scanner_1y_v1 import (
    AggregatedBar,
)
from qore.infrastructure.trader_lab.capitalizer_ict_2022_m1_entry_1y_replay_v1 import (
    _pivot_indices,
)
from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    detect_cisd,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingOrigin,
    CapitalizerSourceBar,
    CapitalizerSourceClosureObservation,
    CapitalizerSourceDirection,
    confirm_protected_swing,
)
from qore.infrastructure.trader_lab.capitalizer_source_poi_v2 import (
    CapitalizerSourcePOI,
    CapitalizerSourcePOIKind,
    detect_fair_value_gap,
)
from qore.infrastructure.trader_lab.capitalizer_source_structural_extraction_v2 import (
    protected_swing_from_cisd,
)
from qore.infrastructure.trader_lab.capitalizer_source_trade_plan_v2 import (
    CapitalizerSourceTargetKind,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    TFBar,
    _aggregate_tf,
    _pivots,
)

IDENTITY = "QORE_CAPITALIZER_CANONICAL_SOURCE_COMPOSITION_REMEDIATION_V47_S2"
PREDECLARATION_COMMENT_ID = 5900501860


@dataclass(frozen=True, slots=True)
class S2UpstreamICTEvent:
    symbol: str
    session: CapitalizerSession
    operating_date: date
    side: CapitalizerSide
    upstream_confirmed_at: datetime
    h1_deadline: datetime
    closeback: v3_source.SweepCloseback
    m3_mss: v3_source.M3MssEvent
    causal: bool = True
    legacy_m1_zone_required: bool = False
    economics_read: bool = False

    def __post_init__(self) -> None:
        confirmed = s1._aware(self.upstream_confirmed_at)
        deadline = s1._aware(self.h1_deadline)
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("S2 upstream symbol must be uppercase")
        if confirmed != s1._aware(self.m3_mss.confirmed_at):
            raise ValueError("S2 upstream identity must end at M3 MSS")
        if s1._aware(self.closeback.closeback_at) > confirmed:
            raise ValueError("S2 upstream closeback cannot follow M3 MSS")
        if confirmed >= deadline:
            raise ValueError("S2 upstream event must precede H1 deadline")
        if not self.causal or self.legacy_m1_zone_required or self.economics_read:
            raise ValueError("S2 upstream governance drift")


@dataclass(frozen=True, slots=True)
class S2IndependentM1:
    binding: context_binders.S0M1StructureBinding
    zone: v3_source.M1EntryZone
    armed_at: datetime
    local_sweep_price: Decimal
    local_sweep_at: datetime
    causal: bool = True
    legacy_m3_zone_inherited: bool = False

    def __post_init__(self) -> None:
        armed = s1._aware(self.armed_at)
        if armed != s1._aware(self.zone.fvg_confirmed_at):
            raise ValueError("S2 M1 arms only when displacement FVG is confirmed")
        if self.binding.confirmed_at > armed:
            raise ValueError("S2 M1 binding cannot confirm after arm")
        if not self.causal or self.legacy_m3_zone_inherited:
            raise ValueError("S2 M1 governance drift")


@dataclass(frozen=True, slots=True)
class S2CanonicalFractalCandidate:
    routed: s0.S0RoutedCanonicalCandidate
    upstream_confirmed_at: datetime
    target_provenance: str
    m15_same_h1_poi_retouch_required: bool = False
    m1_legacy_m3_zone_required: bool = False
    generic_target_priority_used: bool = False
    outcome_used: bool = False

    def __post_init__(self) -> None:
        if (
            self.m15_same_h1_poi_retouch_required
            or self.m1_legacy_m3_zone_required
            or self.generic_target_priority_used
            or self.outcome_used
        ):
            raise ValueError("S2 remediation governance drift")


def _direction(side: CapitalizerSide) -> CapitalizerSourceDirection:
    return (
        CapitalizerSourceDirection.BULLISH
        if side is CapitalizerSide.LONG
        else CapitalizerSourceDirection.BEARISH
    )


def _source(bar: CapitalizerM1Bar) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
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
        return min(row.low for row in series)
    return max(row.high for row in series)


def bind_s2_m15_cisd(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    direction: CapitalizerSourceDirection,
    higher_timeframe_closure: CapitalizerSourceClosureObservation,
    after: datetime,
    before: datetime,
) -> context_binders.S0CISDBinding | None:
    """Bind aligned M15 CISD without a second touch of the exact H1 POI."""

    after_at = s1._aware(after)
    before_at = s1._aware(before)
    if before_at < after_at:
        raise ValueError("S2 M15 requires after <= before")
    frames = tuple(
        frame
        for frame in _aggregate_tf(bars, minutes=15)
        if after_at < frame.closed_at <= before_at
    )
    for index, confirmation in enumerate(frames):
        cursor = index - 1
        if cursor < 0 or not _opposing(frames[cursor].source, direction):
            continue
        start = cursor
        while start > 0 and _opposing(frames[start - 1].source, direction):
            start -= 1
        series_frames = frames[start:index]
        if not series_frames:
            continue
        series = tuple(frame.source for frame in series_frames)
        observed = detect_cisd(
            causal_series=series,
            confirmation_bar=confirmation.source,
            direction=direction,
            important_level_reached=True,
            higher_timeframe_closure=higher_timeframe_closure,
        )
        if not observed.setup_confirmed:
            continue
        protected = confirm_protected_swing(
            direction=direction,
            swing_price=_series_extreme(series, direction),
            origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
            closure_through_causal_series_confirmed=True,
        )
        return context_binders.S0CISDBinding(
            confirmed_at=confirmation.closed_at,
            cisd=observed,
            protected_swing=protected,
            causal_series=series,
        )
    return None


def _opposing_series_ending_at(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    end_index: int,
    side: CapitalizerSide,
) -> tuple[int, ...]:
    selected: list[int] = []
    index = end_index
    while index >= 0:
        row = bars[index]
        is_opposing = (
            row.close < row.open
            if side is CapitalizerSide.LONG
            else row.close > row.open
        )
        if not is_opposing:
            break
        selected.append(index)
        index -= 1
    selected.reverse()
    return tuple(selected)


def _directional_fvg(
    first: CapitalizerM1Bar,
    middle: CapitalizerM1Bar,
    third: CapitalizerM1Bar,
    *,
    direction: CapitalizerSourceDirection,
) -> CapitalizerSourcePOI | None:
    poi = detect_fair_value_gap(
        candle1=_source(first),
        candle2=_source(middle),
        candle3=_source(third),
    )
    if poi is None:
        return None
    expected = (
        CapitalizerSourcePOIKind.BULLISH_FVG
        if direction is CapitalizerSourceDirection.BULLISH
        else CapitalizerSourcePOIKind.BEARISH_FVG
    )
    return poi if poi.kind is expected else None


def bind_independent_m1_structure(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    side: CapitalizerSide,
    higher_timeframe_closure: CapitalizerSourceClosureObservation,
    after: datetime,
    before: datetime,
) -> S2IndependentM1 | None:
    """Build local-sweep CISD -> MSS -> FVG -> OB independently of M3."""

    direction = _direction(side)
    after_at = s1._aware(after)
    before_at = s1._aware(before)
    selected = tuple(
        row
        for row in bars
        if after_at < row.closed_at <= before_at
    )
    if len(selected) < 6:
        return None

    for sweep_index in range(2, len(selected) - 2):
        pivots = _pivot_indices(
            selected,
            before_index=sweep_index - 1,
            high=side is CapitalizerSide.SHORT,
        )
        if not pivots:
            continue
        pivot = selected[pivots[-1]]
        swept_level = pivot.low if side is CapitalizerSide.LONG else pivot.high
        sweep_bar = selected[sweep_index]
        swept = (
            sweep_bar.low < swept_level
            if side is CapitalizerSide.LONG
            else sweep_bar.high > swept_level
        )
        if not swept:
            continue

        series_indices = _opposing_series_ending_at(
            selected,
            end_index=sweep_index,
            side=side,
        )
        if not series_indices:
            probe = sweep_index + 1
            while probe < len(selected) - 2:
                row = selected[probe]
                is_opposing = (
                    row.close < row.open
                    if side is CapitalizerSide.LONG
                    else row.close > row.open
                )
                if is_opposing:
                    series_indices = _opposing_series_ending_at(
                        selected,
                        end_index=probe,
                        side=side,
                    )
                    break
                probe += 1
        if not series_indices:
            continue

        series_rows = tuple(selected[index] for index in series_indices)
        series = tuple(_source(row) for row in series_rows)
        confirmation_start = series_indices[-1] + 1
        for confirmation_index in range(confirmation_start, len(selected) - 1):
            confirmation = selected[confirmation_index]
            crossed = (
                confirmation.close > series[0].open
                if side is CapitalizerSide.LONG
                else confirmation.close < series[0].open
            )
            if not crossed:
                continue

            cisd = detect_cisd(
                causal_series=series,
                confirmation_bar=_source(confirmation),
                direction=direction,
                important_level_reached=True,
                higher_timeframe_closure=higher_timeframe_closure,
            )
            if not cisd.setup_confirmed:
                continue
            order_block = remediation.assess_m1_order_block(
                direction=direction,
                causal_series=series,
                poi_reached=True,
                cisd=cisd,
            )
            if not order_block.confirmed:
                continue
            protected = protected_swing_from_cisd(
                cisd=cisd,
                causal_series=series,
                confirmation_bar=_source(confirmation),
                origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
            )
            if not protected.confirmed:
                continue

            mss = remediation.detect_m1_mss(
                bars=selected,
                direction=direction,
                after=confirmation.opened_at,
                before=before_at,
            )
            if not mss.confirmed or mss.confirmed_at is None:
                continue
            mss_index = next(
                (
                    index
                    for index, row in enumerate(selected)
                    if row.closed_at == mss.confirmed_at
                ),
                None,
            )
            if mss_index is None or mss_index <= 0 or mss_index + 1 >= len(selected):
                continue
            fvg = _directional_fvg(
                selected[mss_index - 1],
                selected[mss_index],
                selected[mss_index + 1],
                direction=direction,
            )
            if fvg is None:
                continue
            fvg_confirmed_at = selected[mss_index + 1].closed_at
            if fvg_confirmed_at > before_at:
                continue

            ob_low = min(row.low for row in series_rows)
            ob_high = max(row.high for row in series_rows)
            overlap_low = max(ob_low, fvg.lower_price)
            overlap_high = min(ob_high, fvg.upper_price)
            if overlap_low > overlap_high:
                overlap_low = None
                overlap_high = None
            zone = v3_source.M1EntryZone(
                ob_opened_at=series_rows[0].opened_at,
                ob_low=ob_low,
                ob_high=ob_high,
                fvg_confirmed_at=fvg_confirmed_at,
                fvg_low=fvg.lower_price,
                fvg_high=fvg.upper_price,
                overlap_low=overlap_low,
                overlap_high=overlap_high,
            )
            binding = context_binders.S0M1StructureBinding(
                confirmed_at=fvg_confirmed_at,
                m1_mss=mss,
                m1_cisd=cisd,
                protected_swing=protected,
                order_block=order_block,
                causal_series=series,
                confirmation_bar=_source(confirmation),
                fvg_confirmed=True,
                source_zone_bound=True,
            )
            return S2IndependentM1(
                binding=binding,
                zone=zone,
                armed_at=fvg_confirmed_at,
                local_sweep_price=swept_level,
                local_sweep_at=sweep_bar.opened_at,
            )
    return None


def bind_upstream_source_events(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    session: CapitalizerSession,
    operating_day: date,
    prepared: s1._PreparedSourceSeries | None = None,
) -> tuple[S2UpstreamICTEvent, ...]:
    """Build source events without calling the legacy V3 M1-zone function."""

    ordered = tuple(sorted(bars, key=lambda row: row.opened_at))
    if ordered != bars:
        raise ValueError("S2 source events require chronological M1")
    if not ordered:
        return ()
    symbol = ordered[0].symbol
    if any(row.symbol != symbol for row in ordered):
        raise ValueError("S2 source events require one symbol")

    source_start, source_end = s1.source_session_bounds(
        operating_day,
        session=session,
    )
    execution = (
        s1._bars_between(ordered, start=source_start, end=source_end)
        if prepared is None
        else s1._prepared_m1_between(
            prepared,
            start=source_start,
            end=source_end,
        )
    )
    if len(execution) < 15:
        return ()

    previous_day = (
        v3_source._previous_day_range(
            ordered,
            operating_day=operating_day,
        )
        if prepared is None
        else s1._prepared_previous_day_range(
            prepared,
            operating_day=operating_day,
        )
    )
    prior_session = s1._reference_liquidity(
        ordered,
        operating_day=operating_day,
        session=session,
        prepared=prepared,
    )

    if prepared is None:
        h1 = s1._aggregate_h1(ordered)
        m5 = _aggregate_tf(ordered, minutes=5)
        m3 = _aggregate_tf(ordered, minutes=3)
    else:
        context_start = source_start - s1.LOOKBACK
        context_end = source_end + timedelta(hours=1)
        h1 = tuple(
            row
            for row in s1._prepared_tf_between(
                prepared.h1,
                prepared.h1_opened,
                start=context_start,
                end=context_end,
            )
            if isinstance(row, AggregatedBar) and row.closed_at <= context_end
        )
        m5 = tuple(
            row
            for row in s1._prepared_tf_between(
                prepared.m5,
                prepared.m5_opened,
                start=context_start,
                end=context_end,
            )
            if isinstance(row, TFBar) and row.closed_at <= context_end
        )
        m3 = tuple(
            row
            for row in s1._prepared_tf_between(
                prepared.m3,
                prepared.m3_opened,
                start=context_start,
                end=context_end,
            )
            if isinstance(row, TFBar) and row.closed_at <= context_end
        )

    h1_swings = v3_source._build_h1_swings(h1)
    m5_closes = tuple(row.closed_at for row in m5)
    m3_closes = tuple(row.closed_at for row in m3)
    m3_pivots = _pivots(m3)

    result: list[S2UpstreamICTEvent] = []
    for h1_open, h1_deadline, hour_bars in v3_source._h1_windows(execution):
        deadline = min(h1_deadline, source_end)
        levels = v3_source._liquidity_levels(
            prior_session=prior_session,
            previous_day=previous_day,
            h1_swings=h1_swings,
            hour_open=h1_open,
        )
        if not levels:
            continue
        _sweep_seen, closeback = v3_source._find_sweep_closeback(
            hour_bars,
            levels=levels,
            m5=m5,
            m5_closes=m5_closes,
            h1_open=h1_open,
            h1_deadline=deadline,
        )
        if closeback is None:
            continue
        mss = v3_source._find_m3_mss(
            m3,
            m3_closes,
            m3_pivots,
            after=closeback.closeback_at,
            before=deadline,
            side=closeback.side,
        )
        if mss is None or mss.confirmed_at >= deadline:
            continue
        result.append(
            S2UpstreamICTEvent(
                symbol=symbol,
                session=session,
                operating_date=operating_day,
                side=closeback.side,
                upstream_confirmed_at=mss.confirmed_at,
                h1_deadline=deadline,
                closeback=closeback,
                m3_mss=mss,
            )
        )
    return tuple(
        sorted(
            result,
            key=lambda row: (
                row.upstream_confirmed_at,
                row.side.value,
                row.closeback.reference.price,
            ),
        )
    )


def _target_binding(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    prepared: s1._PreparedSourceSeries,
    event: s0.S0ICTSourceEvent,
) -> tuple[structural_targets.S0StructuralTargetBinding, str] | None:
    paired = opposite_boundary.reconstruct_event_opposite_boundary(
        bars,
        prepared=prepared,
        event=event,
    )
    if paired is None:
        return None
    direction = _direction(event.side)
    target_price = paired.price
    directionally_valid = (
        target_price > event.primary_armed_level
        if event.side is CapitalizerSide.LONG
        else target_price < event.primary_armed_level
    )
    if not directionally_valid:
        return None
    if any(
        (
            row.high >= target_price
            if event.side is CapitalizerSide.LONG
            else row.low <= target_price
        )
        for row in bars
        if event.closeback.sweep_at <= row.opened_at < event.source_event_at
    ):
        return None
    candidate = remediation.CapitalizerStructuralTargetCandidate(
        kind=CapitalizerSourceTargetKind.HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE,
        target_price=target_price,
        observed_at=paired.known_at,
        untouched=True,
        higher_timeframe=True,
    )
    resolution = remediation.resolve_structural_target(
        direction=direction,
        entry_price=event.primary_armed_level,
        decision_at=event.source_event_at,
        candidates=(candidate,),
    )
    if not resolution.resolved:
        return None
    return (
        structural_targets.S0StructuralTargetBinding(
            candidates=(candidate,),
            resolution=resolution,
        ),
        paired.provenance,
    )


def bind_s2_fractal_candidates(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    session: CapitalizerSession,
    operating_day: date,
    prepared: s1._PreparedSourceSeries | None = None,
    funnel: dict[str, int] | None = None,
    rejections: dict[str, int] | None = None,
) -> tuple[S2CanonicalFractalCandidate, ...]:
    """Assemble remediated FRACTAL candidates without outcomes."""

    prepared_source = (
        s1._prepare_source_series(bars)
        if prepared is None
        else prepared
    )
    upstream = bind_upstream_source_events(
        bars,
        session=session,
        operating_day=operating_day,
        prepared=prepared_source,
    )
    if funnel is not None:
        funnel["upstream_events"] = funnel.get("upstream_events", 0) + len(upstream)

    def reject(key: str) -> None:
        if rejections is not None:
            rejections[key] = rejections.get(key, 0) + 1

    result: list[S2CanonicalFractalCandidate] = []
    for source_event in upstream:
        direction = _direction(source_event.side)
        htf = context_binders.bind_latest_h1_context(
            bars,
            decision_at=source_event.upstream_confirmed_at,
        )
        if htf is None:
            reject("HTF_CONTEXT_UNRESOLVED")
            continue
        if (
            htf.closure.direction is not direction
            or htf.daily_bias.direction is not direction
        ):
            reject("HTF_DIRECTION_NOT_ALIGNED")
            continue
        if funnel is not None:
            funnel["htf_aligned"] = funnel.get("htf_aligned", 0) + 1

        m15 = bind_s2_m15_cisd(
            bars,
            direction=direction,
            higher_timeframe_closure=htf.closure,
            after=htf.confirmed_at,
            before=source_event.h1_deadline,
        )
        if m15 is None:
            reject("M15_STRUCTURAL_CISD_UNRESOLVED")
            continue
        if funnel is not None:
            funnel["m15_bound"] = funnel.get("m15_bound", 0) + 1

        m1_after = max(source_event.upstream_confirmed_at, m15.confirmed_at)
        m1 = bind_independent_m1_structure(
            bars,
            side=source_event.side,
            higher_timeframe_closure=htf.closure,
            after=m1_after,
            before=source_event.h1_deadline,
        )
        if m1 is None:
            reject("INDEPENDENT_M1_TRIAD_UNRESOLVED")
            continue
        if funnel is not None:
            funnel["independent_m1_bound"] = (
                funnel.get("independent_m1_bound", 0) + 1
            )

        primary, fallback, mode = s0.resolve_s0_armed_levels(
            side=source_event.side,
            zone=m1.zone,
        )
        event = s0.S0ICTSourceEvent(
            symbol=source_event.symbol,
            session=source_event.session,
            operating_date=source_event.operating_date,
            side=source_event.side,
            source_event_at=m1.armed_at,
            h1_deadline=source_event.h1_deadline,
            closeback=source_event.closeback,
            m3_mss=source_event.m3_mss,
            zone=m1.zone,
            primary_armed_level=primary,
            fallback_armed_level=fallback,
            primary_entry_mode=mode,
        )
        target = _target_binding(
            bars,
            prepared=prepared_source,
            event=event,
        )
        if target is None:
            reject("EVENT_SPECIFIC_TARGET_INVALID")
            continue
        target_binding, target_provenance = target
        if funnel is not None:
            funnel["event_target_bound"] = funnel.get("event_target_bound", 0) + 1

        context = context_binders.S0SourceContextBinding(
            decision_at=event.source_event_at,
            direction=direction,
            htf=htf,
            m15=m15,
            structural_target=target_binding,
        )
        try:
            armed = s0.S0CanonicalArmedCandidate(
                event=event,
                context=context,
                m1=m1.binding,
                armed_at=event.source_event_at,
            )
            route_wick = s0.bind_s0_route_and_wick(armed)
            if not route_wick.route_resolution.resolved:
                reject("FRACTAL_ROUTE_UNRESOLVED")
                continue
            if not route_wick.wick_formation.confirmed:
                reject("WICK_FORMATION_UNRESOLVED")
                continue
            routed = s0.S0RoutedCanonicalCandidate(
                candidate=armed,
                route_wick=route_wick,
            )
        except ValueError:
            reject("CANONICAL_INVARIANT_REJECT")
            continue

        route = routed.route_wick.route_resolution.route
        if route is None or route.value != "FRACTAL_SCALP_CONTINUATION":
            reject("NON_FRACTAL_ROUTE_REJECTED_FROM_FRACTAL_STREAM")
            continue
        result.append(
            S2CanonicalFractalCandidate(
                routed=routed,
                upstream_confirmed_at=source_event.upstream_confirmed_at,
                target_provenance=target_provenance,
            )
        )
        if funnel is not None:
            funnel["routed_fractal_candidates"] = (
                funnel.get("routed_fractal_candidates", 0) + 1
            )

    return tuple(
        sorted(
            result,
            key=lambda row: (
                row.routed.candidate.armed_at,
                row.routed.candidate.event.side.value,
                row.routed.candidate.event.primary_armed_level,
            ),
        )
    )
