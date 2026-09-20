"""Raw causal source-observation engine for QORE Capitalizer V2.

This is the bridge from historical bars/source metadata to reviewed ICT/TTrades observations.
It does not decide economic viability, execute, size, or use terminal outcomes.

The engine supports the source-faithful fractal continuation path:
- resolve source session context;
- derive HTF daily bias from C2/C3 closure at a source POI;
- derive H1 C2/C3 closure at a source POI;
- derive M15 CISD at an important source POI;
- derive M1 CISD and protected swing;
- derive prior-day structural liquidity target;
- compose H1 -> M15 -> M1 alignment.

Failure-to-Manipulate raw composition remains a separate source path because it starts from a
specific taken liquidity reference and post-sweep sequence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    CapitalizerCISDObservation,
    detect_cisd,
)
from qore.infrastructure.trader_lab.capitalizer_source_daily_bias_v2 import (
    CapitalizerDailyBiasObservation,
    derive_daily_bias,
)
from qore.infrastructure.trader_lab.capitalizer_source_fractal_alignment_v2 import (
    CapitalizerFractalAlignmentObservation,
    assess_fractal_alignment,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingObservation,
    CapitalizerProtectedSwingOrigin,
    CapitalizerSourceBar,
    CapitalizerSourceClosureObservation,
    CapitalizerSourceDirection,
    CapitalizerStructuralTargetObservation,
    detect_candle2_reversal_closure,
    detect_candle3_confirmation,
)
from qore.infrastructure.trader_lab.capitalizer_source_poi_v2 import (
    CapitalizerSourcePOI,
    any_source_poi_interaction,
)
from qore.infrastructure.trader_lab.capitalizer_source_session_context_v2 import (
    CapitalizerSourceSessionAssessment,
    assess_source_session_context,
)
from qore.infrastructure.trader_lab.capitalizer_source_structural_extraction_v2 import (
    extract_previous_day_liquidity_target,
    protected_swing_from_cisd,
)


@dataclass(frozen=True, slots=True)
class CapitalizerSourceClosureWindow:
    previous: CapitalizerSourceBar
    candle2: CapitalizerSourceBar
    candle3: CapitalizerSourceBar | None
    pois: tuple[CapitalizerSourcePOI, ...]

    def __post_init__(self) -> None:
        if not self.pois:
            raise ValueError("source closure window requires at least one causal POI")


@dataclass(frozen=True, slots=True)
class CapitalizerSourceCISDWindow:
    causal_series: tuple[CapitalizerSourceBar, ...]
    confirmation_bar: CapitalizerSourceBar
    important_pois: tuple[CapitalizerSourcePOI, ...]
    protected_swing_origin: CapitalizerProtectedSwingOrigin

    def __post_init__(self) -> None:
        if not self.causal_series:
            raise ValueError("CISD window requires causal series")
        if not self.important_pois:
            raise ValueError("CISD window requires at least one important source POI")


@dataclass(frozen=True, slots=True)
class CapitalizerFractalObservationInput:
    symbol: str
    session: CapitalizerSession
    observed_at: datetime
    entry_price: Decimal
    asian_open_reference_at: datetime | None
    daily_closure_window: CapitalizerSourceClosureWindow
    h1_closure_window: CapitalizerSourceClosureWindow
    m15_cisd_window: CapitalizerSourceCISDWindow
    m1_cisd_window: CapitalizerSourceCISDWindow
    previous_daily_bar: CapitalizerSourceBar
    bars_since_current_day_open: tuple[CapitalizerSourceBar, ...]

    def __post_init__(self) -> None:
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("source observation symbol must be uppercase")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("source observation timestamp must be timezone-aware")
        if not isinstance(self.entry_price, Decimal) or not self.entry_price.is_finite():
            raise ValueError("source observation entry price must be finite Decimal")


@dataclass(frozen=True, slots=True)
class CapitalizerFractalObservationSnapshot:
    symbol: str
    observed_at: datetime
    session: CapitalizerSourceSessionAssessment
    daily_bias: CapitalizerDailyBiasObservation
    daily_closure: CapitalizerSourceClosureObservation | None
    h1_closure: CapitalizerSourceClosureObservation | None
    m15_cisd: CapitalizerCISDObservation | None
    m1_cisd: CapitalizerCISDObservation | None
    m1_protected_swing: CapitalizerProtectedSwingObservation | None
    structural_target: CapitalizerStructuralTargetObservation | None
    fractal_alignment: CapitalizerFractalAlignmentObservation | None
    complete: bool
    reasons: tuple[str, ...]
    future_outcomes_used: bool = False
    manual_context_boolean_used: bool = False

    def __post_init__(self) -> None:
        if self.future_outcomes_used:
            raise ValueError("source observation snapshot cannot use future outcomes")
        if self.manual_context_boolean_used:
            raise ValueError("source observation engine cannot use manual context booleans")


def resolve_source_closure_window(
    window: CapitalizerSourceClosureWindow,
) -> CapitalizerSourceClosureObservation | None:
    c2_at_poi = any_source_poi_interaction(bar=window.candle2, pois=window.pois)
    candle2 = detect_candle2_reversal_closure(
        previous=window.previous,
        candle2=window.candle2,
        point_of_interest_present=c2_at_poi,
    )
    if candle2 is not None and candle2.source_rule_satisfied:
        return candle2

    if window.candle3 is None:
        return None
    c3_at_poi = any_source_poi_interaction(bar=window.candle3, pois=window.pois)
    return detect_candle3_confirmation(
        candle2=window.candle2,
        candle3=window.candle3,
        point_of_interest_present=c3_at_poi,
        candle2_reversal_already_confirmed=(
            candle2 is not None and candle2.source_rule_satisfied
        ),
    )


def resolve_source_cisd_window(
    *,
    window: CapitalizerSourceCISDWindow,
    direction: CapitalizerSourceDirection,
    higher_timeframe_closure: CapitalizerSourceClosureObservation | None,
) -> CapitalizerCISDObservation:
    important_level_reached = any(
        any_source_poi_interaction(bar=bar, pois=window.important_pois)
        for bar in (*window.causal_series, window.confirmation_bar)
    )
    return detect_cisd(
        causal_series=window.causal_series,
        confirmation_bar=window.confirmation_bar,
        direction=direction,
        important_level_reached=important_level_reached,
        higher_timeframe_closure=higher_timeframe_closure,
    )


def build_fractal_observation_snapshot(
    facts: CapitalizerFractalObservationInput,
) -> CapitalizerFractalObservationSnapshot:
    """Derive the complete fractal source context from causal bars and source POIs."""

    session = assess_source_session_context(
        session=facts.session,
        observed_at=facts.observed_at,
        asian_open_reference_at=facts.asian_open_reference_at,
    )

    daily_closure = resolve_source_closure_window(facts.daily_closure_window)
    daily_bias = derive_daily_bias(daily_closure)
    if daily_bias.direction is None:
        return CapitalizerFractalObservationSnapshot(
            symbol=facts.symbol,
            observed_at=facts.observed_at,
            session=session,
            daily_bias=daily_bias,
            daily_closure=daily_closure,
            h1_closure=None,
            m15_cisd=None,
            m1_cisd=None,
            m1_protected_swing=None,
            structural_target=None,
            fractal_alignment=None,
            complete=False,
            reasons=("DAILY_BIAS_UNRESOLVED",),
        )

    direction = daily_bias.direction
    h1_closure = resolve_source_closure_window(facts.h1_closure_window)

    m15_cisd = resolve_source_cisd_window(
        window=facts.m15_cisd_window,
        direction=direction,
        higher_timeframe_closure=h1_closure,
    )
    m1_cisd = resolve_source_cisd_window(
        window=facts.m1_cisd_window,
        direction=direction,
        higher_timeframe_closure=h1_closure,
    )

    m1_protected: CapitalizerProtectedSwingObservation | None = None
    if m1_cisd.structural_confirmed:
        m1_protected = protected_swing_from_cisd(
            cisd=m1_cisd,
            causal_series=facts.m1_cisd_window.causal_series,
            confirmation_bar=facts.m1_cisd_window.confirmation_bar,
            origin=facts.m1_cisd_window.protected_swing_origin,
        )

    target_extraction = extract_previous_day_liquidity_target(
        previous_daily_bar=facts.previous_daily_bar,
        bars_since_current_day_open=facts.bars_since_current_day_open,
        direction=direction,
        entry_price=facts.entry_price,
    )
    target = target_extraction.observation

    alignment = assess_fractal_alignment(
        higher_timeframe_bias=direction,
        h1_closure=h1_closure,
        m15_cisd=m15_cisd,
        m1_protected_swing=m1_protected,
    )
    complete = (
        session.resolved
        and session.eligible
        and alignment.confirmed
        and target.valid
    )

    reasons: list[str] = []
    reasons.extend(session.reasons)
    reasons.extend(daily_bias.reasons)
    reasons.extend(alignment.reasons)
    reasons.extend(target.reasons)
    if not complete:
        reasons.append("SOURCE_FRACTAL_OBSERVATION_INCOMPLETE")
    else:
        reasons.append("SOURCE_FRACTAL_OBSERVATION_COMPLETE")

    return CapitalizerFractalObservationSnapshot(
        symbol=facts.symbol,
        observed_at=facts.observed_at,
        session=session,
        daily_bias=daily_bias,
        daily_closure=daily_closure,
        h1_closure=h1_closure,
        m15_cisd=m15_cisd,
        m1_cisd=m1_cisd,
        m1_protected_swing=m1_protected,
        structural_target=target,
        fractal_alignment=alignment,
        complete=complete,
        reasons=tuple(dict.fromkeys(reasons)),
    )
