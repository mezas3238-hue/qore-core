from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_decision_sovereignty import (
    CapitalizerCognitiveGateDecision,
)
from qore.infrastructure.trader_lab.capitalizer_source_entry_execution_v2 import (
    CapitalizerSourceExecutionOpen,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingOrigin,
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_engine_v2 import (
    CapitalizerFractalObservationInput,
    CapitalizerSourceCISDWindow,
    CapitalizerSourceClosureWindow,
    build_fractal_observation_snapshot,
)
from qore.infrastructure.trader_lab.capitalizer_source_poi_v2 import (
    CapitalizerSourcePOI,
    detect_external_liquidity_swing,
)
from qore.infrastructure.trader_lab.capitalizer_source_trader_pipeline_v2 import (
    CapitalizerSourcePipelineState,
    evaluate_fractal_snapshot,
)


def _bar(open_: str, high: str, low: str, close: str) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def _swing_low(price: str) -> CapitalizerSourcePOI:
    level = Decimal(price)
    poi = detect_external_liquidity_swing(
        left=CapitalizerSourceBar(
            open=level + Decimal("2"),
            high=level + Decimal("3"),
            low=level + Decimal("1"),
            close=level + Decimal("2"),
        ),
        center=CapitalizerSourceBar(
            open=level + Decimal("1"),
            high=level + Decimal("2"),
            low=level,
            close=level + Decimal("1"),
        ),
        right=CapitalizerSourceBar(
            open=level + Decimal("1"),
            high=level + Decimal("3"),
            low=level + Decimal("0.5"),
            close=level + Decimal("2"),
        ),
    )
    assert poi is not None
    return poi


def test_raw_fractal_observation_derives_context_without_manual_booleans() -> None:
    daily_poi = _swing_low("97")
    h1_poi = _swing_low("97")
    m15_poi = _swing_low("98.7")
    m1_poi = _swing_low("99.0")

    snapshot = build_fractal_observation_snapshot(
        CapitalizerFractalObservationInput(
            symbol="EURUSD",
            session=CapitalizerSession.LONDON,
            observed_at=datetime(2026, 1, 5, 7, 30, tzinfo=UTC),
            execution_open=CapitalizerSourceExecutionOpen(Decimal("100.3")),
            asian_open_reference_at=None,
            daily_closure_window=CapitalizerSourceClosureWindow(
                previous=_bar("100", "102", "98", "99"),
                candle2=_bar("99", "101", "97", "99.5"),
                candle3=None,
                pois=(daily_poi,),
            ),
            h1_closure_window=CapitalizerSourceClosureWindow(
                previous=_bar("100", "102", "98", "99"),
                candle2=_bar("99", "101", "97", "99.5"),
                candle3=None,
                pois=(h1_poi,),
            ),
            m15_cisd_window=CapitalizerSourceCISDWindow(
                causal_series=(
                    _bar("100", "100.4", "99.2", "99.5"),
                    _bar("99.5", "99.8", "98.7", "99.0"),
                ),
                confirmation_bar=_bar("99", "100.8", "98.9", "100.2"),
                important_pois=(m15_poi,),
                protected_swing_origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
            ),
            m1_cisd_window=CapitalizerSourceCISDWindow(
                causal_series=(
                    _bar("100", "100.2", "99.3", "99.5"),
                    _bar("99.5", "99.7", "99.0", "99.2"),
                ),
                confirmation_bar=_bar("99.2", "100.7", "99.1", "100.4"),
                important_pois=(m1_poi,),
                protected_swing_origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
            ),
            previous_daily_bar=_bar("100", "105", "95", "102"),
            bars_since_current_day_open=(
                _bar("99", "103", "98", "101"),
                _bar("101", "104", "100", "102"),
            ),
        )
    )

    assert snapshot.session.eligible is True
    assert snapshot.daily_bias.direction is CapitalizerSourceDirection.BULLISH
    assert snapshot.h1_closure is not None
    assert snapshot.m15_cisd is not None
    assert snapshot.m15_cisd.setup_confirmed is True
    assert snapshot.m1_cisd is not None
    assert snapshot.m1_cisd.structural_confirmed is True
    assert snapshot.m1_protected_swing is not None
    assert snapshot.m1_protected_swing.swing_price == Decimal("99.0")
    assert snapshot.entry is not None
    assert snapshot.entry.entry_price == Decimal("100.3")
    assert snapshot.entry.future_execution_bar_close_used is False
    assert snapshot.structural_target is not None
    assert snapshot.structural_target.target_price == Decimal("105")
    assert snapshot.fractal_alignment is not None
    assert snapshot.fractal_alignment.confirmed is True
    assert snapshot.complete is True
    assert snapshot.future_outcomes_used is False
    assert snapshot.manual_context_boolean_used is False

    pipeline = evaluate_fractal_snapshot(
        snapshot=snapshot,
        cognitive_gate_decision=CapitalizerCognitiveGateDecision.PASS_TO_STRATEGY,
    )
    assert pipeline.state is CapitalizerSourcePipelineState.WAIT
    assert pipeline.source_engine is not None
    assert pipeline.source_engine.passes_to_qore_risk is False
    assert pipeline.source_engine.reasons == ("DUAL_SOURCE_ENTRY_ACCEPTANCE_REQUIRED",)
    assert pipeline.executes_trade is False
    assert pipeline.sizes_position is False
    assert pipeline.grants_capital_authority is False


def test_raw_fractal_observation_fails_closed_when_daily_poi_not_reached() -> None:
    distant_poi = _swing_low("80")
    local_poi = _swing_low("98.7")

    snapshot = build_fractal_observation_snapshot(
        CapitalizerFractalObservationInput(
            symbol="EURUSD",
            session=CapitalizerSession.LONDON,
            observed_at=datetime(2026, 1, 5, 7, 30, tzinfo=UTC),
            execution_open=CapitalizerSourceExecutionOpen(Decimal("100")),
            asian_open_reference_at=None,
            daily_closure_window=CapitalizerSourceClosureWindow(
                previous=_bar("100", "102", "98", "99"),
                candle2=_bar("99", "101", "97", "99.5"),
                candle3=None,
                pois=(distant_poi,),
            ),
            h1_closure_window=CapitalizerSourceClosureWindow(
                previous=_bar("100", "102", "98", "99"),
                candle2=_bar("99", "101", "97", "99.5"),
                candle3=None,
                pois=(local_poi,),
            ),
            m15_cisd_window=CapitalizerSourceCISDWindow(
                causal_series=(_bar("100", "100.4", "99", "99.5"),),
                confirmation_bar=_bar("99.5", "101", "99", "100.5"),
                important_pois=(local_poi,),
                protected_swing_origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
            ),
            m1_cisd_window=CapitalizerSourceCISDWindow(
                causal_series=(_bar("100", "100.2", "99", "99.5"),),
                confirmation_bar=_bar("99.5", "101", "99", "100.5"),
                important_pois=(local_poi,),
                protected_swing_origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
            ),
            previous_daily_bar=_bar("100", "105", "95", "102"),
            bars_since_current_day_open=(),
        )
    )

    assert snapshot.daily_bias.direction is None
    assert snapshot.complete is False
    assert snapshot.reasons == ("DAILY_BIAS_UNRESOLVED",)
