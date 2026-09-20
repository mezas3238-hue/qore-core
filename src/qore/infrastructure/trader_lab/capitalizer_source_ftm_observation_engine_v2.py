"""Raw causal Failure-to-Manipulate observation engine for QORE Capitalizer V2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    CapitalizerCISDObservation,
    CapitalizerFailureToManipulateObservation,
    CapitalizerLiquiditySideTaken,
)
from qore.infrastructure.trader_lab.capitalizer_source_daily_bias_v2 import (
    CapitalizerDailyBiasObservation,
    derive_daily_bias,
)
from qore.infrastructure.trader_lab.capitalizer_source_entry_execution_v2 import (
    CapitalizerSourceEntryObservation,
    CapitalizerSourceExecutionOpen,
    derive_next_bar_open_entry,
)
from qore.infrastructure.trader_lab.capitalizer_source_ftm_composer_v2 import (
    compose_failure_to_manipulate,
)
from qore.infrastructure.trader_lab.capitalizer_source_liquidity_take_v2 import (
    CapitalizerLiquidityTakeObservation,
    detect_liquidity_take,
    liquidity_reference_from_poi,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingObservation,
    CapitalizerSourceBar,
    CapitalizerSourceClosureObservation,
    CapitalizerSourceDirection,
    CapitalizerStructuralTargetObservation,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_engine_v2 import (
    CapitalizerSourceCISDWindow,
    CapitalizerSourceClosureWindow,
    resolve_source_cisd_window,
    resolve_source_closure_window,
)
from qore.infrastructure.trader_lab.capitalizer_source_poi_v2 import CapitalizerSourcePOI
from qore.infrastructure.trader_lab.capitalizer_source_session_context_v2 import (
    CapitalizerSourceSessionAssessment,
    assess_source_session_context,
)
from qore.infrastructure.trader_lab.capitalizer_source_structural_extraction_v2 import (
    extract_previous_day_liquidity_target,
    protected_swing_from_cisd,
)


@dataclass(frozen=True, slots=True)
class CapitalizerFTMObservationInput:
    symbol: str
    session: CapitalizerSession
    observed_at: datetime
    execution_open: CapitalizerSourceExecutionOpen
    asian_open_reference_at: datetime | None
    daily_closure_window: CapitalizerSourceClosureWindow
    external_liquidity_poi: CapitalizerSourcePOI
    sweep_bar: CapitalizerSourceBar
    expected_reversal_window: CapitalizerSourceCISDWindow
    continuation_window: CapitalizerSourceCISDWindow
    previous_daily_bar: CapitalizerSourceBar
    bars_since_current_day_open: tuple[CapitalizerSourceBar, ...]

    def __post_init__(self) -> None:
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("FTM observation symbol must be uppercase")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("FTM observation timestamp must be timezone-aware")


@dataclass(frozen=True, slots=True)
class CapitalizerFTMObservationSnapshot:
    symbol: str
    observed_at: datetime
    entry: CapitalizerSourceEntryObservation | None
    session: CapitalizerSourceSessionAssessment
    daily_closure: CapitalizerSourceClosureObservation | None
    daily_bias: CapitalizerDailyBiasObservation
    liquidity_take: CapitalizerLiquidityTakeObservation
    expected_reversal_cisd: CapitalizerCISDObservation
    continuation_cisd: CapitalizerCISDObservation
    continuation_protected_swing: CapitalizerProtectedSwingObservation | None
    failure_to_manipulate: CapitalizerFailureToManipulateObservation
    structural_target: CapitalizerStructuralTargetObservation | None
    complete: bool
    reasons: tuple[str, ...]
    future_outcomes_used: bool = False
    manual_liquidity_boolean_used: bool = False

    def __post_init__(self) -> None:
        if self.future_outcomes_used:
            raise ValueError("FTM snapshot cannot use future outcomes")
        if self.manual_liquidity_boolean_used:
            raise ValueError("FTM snapshot cannot accept manual liquidity-take booleans")


def _ftm_directions(
    side: CapitalizerLiquiditySideTaken,
) -> tuple[CapitalizerSourceDirection, CapitalizerSourceDirection]:
    if side is CapitalizerLiquiditySideTaken.HIGH:
        return CapitalizerSourceDirection.BEARISH, CapitalizerSourceDirection.BULLISH
    return CapitalizerSourceDirection.BULLISH, CapitalizerSourceDirection.BEARISH


def build_ftm_observation_snapshot(
    facts: CapitalizerFTMObservationInput,
) -> CapitalizerFTMObservationSnapshot:
    session = assess_source_session_context(
        session=facts.session,
        observed_at=facts.observed_at,
        asian_open_reference_at=facts.asian_open_reference_at,
    )
    daily_closure = resolve_source_closure_window(facts.daily_closure_window)
    daily_bias = derive_daily_bias(daily_closure)

    reference = liquidity_reference_from_poi(facts.external_liquidity_poi)
    take = detect_liquidity_take(
        reference_side=reference.side,
        reference_price=reference.price,
        closed_bar=facts.sweep_bar,
    )
    reversal_direction, continuation_direction = _ftm_directions(reference.side)

    expected_reversal = resolve_source_cisd_window(
        window=facts.expected_reversal_window,
        direction=reversal_direction,
        higher_timeframe_closure=None,
    )
    continuation = resolve_source_cisd_window(
        window=facts.continuation_window,
        direction=continuation_direction,
        higher_timeframe_closure=daily_closure,
    )

    protected: CapitalizerProtectedSwingObservation | None = None
    if continuation.structural_confirmed:
        protected = protected_swing_from_cisd(
            cisd=continuation,
            causal_series=facts.continuation_window.causal_series,
            confirmation_bar=facts.continuation_window.confirmation_bar,
            origin=facts.continuation_window.protected_swing_origin,
        )

    ftm = compose_failure_to_manipulate(
        liquidity_take=take,
        expected_reversal_cisd=expected_reversal,
        continuation_protected_swing=protected,
        daily_bias=daily_bias,
    )

    entry: CapitalizerSourceEntryObservation | None = None
    target: CapitalizerStructuralTargetObservation | None = None
    if ftm.confirmed and daily_bias.direction is not None:
        entry = derive_next_bar_open_entry(
            direction=daily_bias.direction,
            source_framework_confirmed=True,
            execution_open=facts.execution_open,
        )
        target = extract_previous_day_liquidity_target(
            previous_daily_bar=facts.previous_daily_bar,
            bars_since_current_day_open=facts.bars_since_current_day_open,
            direction=daily_bias.direction,
            entry_price=entry.entry_price,
        ).observation

    complete = (
        session.resolved
        and session.eligible
        and ftm.confirmed
        and entry is not None
        and target is not None
        and target.valid
    )

    reasons = tuple(
        dict.fromkeys(
            (
                *session.reasons,
                *daily_bias.reasons,
                *take.reasons,
                *expected_reversal.reasons,
                *continuation.reasons,
                *ftm.reasons,
                *((target.reasons) if target is not None else ("TARGET_UNRESOLVED",)),
                (
                    "SOURCE_FTM_OBSERVATION_COMPLETE"
                    if complete
                    else "SOURCE_FTM_OBSERVATION_INCOMPLETE"
                ),
            )
        )
    )

    return CapitalizerFTMObservationSnapshot(
        symbol=facts.symbol,
        observed_at=facts.observed_at,
        entry=entry,
        session=session,
        daily_closure=daily_closure,
        daily_bias=daily_bias,
        liquidity_take=take,
        expected_reversal_cisd=expected_reversal,
        continuation_cisd=continuation,
        continuation_protected_swing=protected,
        failure_to_manipulate=ftm,
        structural_target=target,
        complete=complete,
        reasons=reasons,
    )
