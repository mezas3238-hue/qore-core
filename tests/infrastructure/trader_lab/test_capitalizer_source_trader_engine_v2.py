from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_decision_sovereignty import (
    CapitalizerCognitiveGateDecision,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    CapitalizerLiquiditySideTaken,
    assess_failure_to_manipulate,
    detect_cisd,
)
from qore.infrastructure.trader_lab.capitalizer_source_fractal_alignment_v2 import (
    assess_fractal_alignment,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingOrigin,
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
    assess_structural_target,
    confirm_protected_swing,
    detect_candle2_reversal_closure,
)
from qore.infrastructure.trader_lab.capitalizer_source_session_context_v2 import (
    assess_source_session_context,
)
from qore.infrastructure.trader_lab.capitalizer_source_strategy_grammar_v2 import (
    CapitalizerSourceEntryRoute,
    CapitalizerSourceStrategyDecision,
)
from qore.infrastructure.trader_lab.capitalizer_source_trade_plan_v2 import (
    CapitalizerSourceTargetKind,
)
from qore.infrastructure.trader_lab.capitalizer_source_trader_engine_v2 import (
    CapitalizerSourceTraderEngineFacts,
    assess_source_trader_engine,
)


def _bar(open_: str, high: str, low: str, close: str) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def _bullish_structure():
    h1 = detect_candle2_reversal_closure(
        previous=_bar("100", "102", "98", "99"),
        candle2=_bar("99", "101", "97", "99.5"),
        point_of_interest_present=True,
    )
    assert h1 is not None
    m15 = detect_cisd(
        causal_series=(
            _bar("100", "100.4", "99.1", "99.4"),
            _bar("99.4", "99.7", "98.8", "99.0"),
        ),
        confirmation_bar=_bar("99", "101", "98.9", "100.2"),
        direction=CapitalizerSourceDirection.BULLISH,
        important_level_reached=True,
        higher_timeframe_closure=h1,
    )
    m1 = confirm_protected_swing(
        direction=CapitalizerSourceDirection.BULLISH,
        swing_price=Decimal("98.8"),
        origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
        closure_through_causal_series_confirmed=True,
    )
    alignment = assess_fractal_alignment(
        higher_timeframe_bias=CapitalizerSourceDirection.BULLISH,
        h1_closure=h1,
        m15_cisd=m15,
        m1_protected_swing=m1,
    )
    return alignment, m1


def test_fractal_engine_passes_only_complete_source_plan_to_qore_risk() -> None:
    alignment, protected = _bullish_structure()
    entry = Decimal("100")
    target = assess_structural_target(
        direction=CapitalizerSourceDirection.BULLISH,
        entry_price=entry,
        target_price=Decimal("104"),
        untouched=True,
        higher_timeframe=True,
    )
    source_session = assess_source_session_context(
        session=CapitalizerSession.LONDON,
        observed_at=datetime(2026, 1, 5, 7, 30, tzinfo=UTC),
    )

    result = assess_source_trader_engine(
        CapitalizerSourceTraderEngineFacts(
            symbol="EURUSD",
            side=CapitalizerSide.LONG,
            route=CapitalizerSourceEntryRoute.FRACTAL_SCALP_CONTINUATION,
            cognitive_gate_decision=CapitalizerCognitiveGateDecision.PASS_TO_STRATEGY,
            source_session=source_session,
            higher_timeframe_bias=CapitalizerSourceDirection.BULLISH,
            entry_price=entry,
            protected_swing=protected,
            structural_target=target,
            target_kind=CapitalizerSourceTargetKind.HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE,
            fractal_alignment=alignment,
        )
    )

    assert result.strategy_assessment.decision is (
        CapitalizerSourceStrategyDecision.ELIGIBLE_FOR_QORE_RISK
    )
    assert result.trade_plan is not None
    assert result.trade_plan.initial_stop_price == Decimal("98.8")
    assert result.trade_plan.target_price == Decimal("104")
    assert result.passes_to_qore_risk is True
    assert result.executes_trade is False
    assert result.sizes_position is False
    assert result.grants_capital_authority is False


def test_ftm_engine_passes_confirmed_continuation_only_after_closure() -> None:
    protected = confirm_protected_swing(
        direction=CapitalizerSourceDirection.BULLISH,
        swing_price=Decimal("99"),
        origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
        closure_through_causal_series_confirmed=True,
    )
    ftm = assess_failure_to_manipulate(
        taken_side=CapitalizerLiquiditySideTaken.HIGH,
        level_taken=True,
        post_sweep_closure_observed=True,
        expected_reversal_cisd=None,
        continuation_protected_swing=protected,
        higher_timeframe_bias=CapitalizerSourceDirection.BULLISH,
    )
    entry = Decimal("100")
    target = assess_structural_target(
        direction=CapitalizerSourceDirection.BULLISH,
        entry_price=entry,
        target_price=Decimal("105"),
        untouched=True,
        higher_timeframe=True,
    )
    source_session = assess_source_session_context(
        session=CapitalizerSession.NEW_YORK,
        observed_at=datetime(2026, 1, 5, 12, 30, tzinfo=UTC),
    )

    result = assess_source_trader_engine(
        CapitalizerSourceTraderEngineFacts(
            symbol="USDCAD",
            side=CapitalizerSide.LONG,
            route=CapitalizerSourceEntryRoute.FAILURE_TO_MANIPULATE_CONTINUATION,
            cognitive_gate_decision=CapitalizerCognitiveGateDecision.PASS_TO_STRATEGY,
            source_session=source_session,
            higher_timeframe_bias=CapitalizerSourceDirection.BULLISH,
            entry_price=entry,
            protected_swing=protected,
            structural_target=target,
            target_kind=CapitalizerSourceTargetKind.HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE,
            failure_to_manipulate=ftm,
        )
    )

    assert ftm.confirmed is True
    assert result.passes_to_qore_risk is True
    assert result.trade_plan is not None


def test_engine_rejects_consumed_target_before_qore_risk() -> None:
    alignment, protected = _bullish_structure()
    entry = Decimal("100")
    consumed = assess_structural_target(
        direction=CapitalizerSourceDirection.BULLISH,
        entry_price=entry,
        target_price=Decimal("104"),
        untouched=False,
        higher_timeframe=True,
    )
    source_session = assess_source_session_context(
        session=CapitalizerSession.LONDON,
        observed_at=datetime(2026, 1, 5, 7, 30, tzinfo=UTC),
    )

    result = assess_source_trader_engine(
        CapitalizerSourceTraderEngineFacts(
            symbol="EURUSD",
            side=CapitalizerSide.LONG,
            route=CapitalizerSourceEntryRoute.FRACTAL_SCALP_CONTINUATION,
            cognitive_gate_decision=CapitalizerCognitiveGateDecision.PASS_TO_STRATEGY,
            source_session=source_session,
            higher_timeframe_bias=CapitalizerSourceDirection.BULLISH,
            entry_price=entry,
            protected_swing=protected,
            structural_target=consumed,
            target_kind=CapitalizerSourceTargetKind.HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE,
            fractal_alignment=alignment,
        )
    )

    assert result.strategy_assessment.decision is CapitalizerSourceStrategyDecision.REJECT
    assert result.trade_plan is None
    assert result.passes_to_qore_risk is False
    assert result.reasons == ("STRUCTURAL_TARGET_INVALID_OR_CONSUMED",)


def test_engine_waits_when_source_session_context_is_unresolved() -> None:
    alignment, protected = _bullish_structure()
    entry = Decimal("100")
    target = assess_structural_target(
        direction=CapitalizerSourceDirection.BULLISH,
        entry_price=entry,
        target_price=Decimal("104"),
        untouched=True,
        higher_timeframe=True,
    )
    unresolved_asia = assess_source_session_context(
        session=CapitalizerSession.ASIA,
        observed_at=datetime(2026, 1, 5, 1, 0, tzinfo=UTC),
    )

    result = assess_source_trader_engine(
        CapitalizerSourceTraderEngineFacts(
            symbol="USDJPY",
            side=CapitalizerSide.LONG,
            route=CapitalizerSourceEntryRoute.FRACTAL_SCALP_CONTINUATION,
            cognitive_gate_decision=CapitalizerCognitiveGateDecision.PASS_TO_STRATEGY,
            source_session=unresolved_asia,
            higher_timeframe_bias=CapitalizerSourceDirection.BULLISH,
            entry_price=entry,
            protected_swing=protected,
            structural_target=target,
            target_kind=CapitalizerSourceTargetKind.HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE,
            fractal_alignment=alignment,
        )
    )

    assert result.strategy_assessment.decision is CapitalizerSourceStrategyDecision.WAIT
    assert result.passes_to_qore_risk is False
    assert "SOURCE_SESSION_CONTEXT_UNRESOLVED" in result.reasons
