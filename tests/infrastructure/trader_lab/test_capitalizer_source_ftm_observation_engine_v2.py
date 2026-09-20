from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_source_ftm_observation_engine_v2 import (
    CapitalizerFTMObservationInput,
    build_ftm_observation_snapshot,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingOrigin,
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_engine_v2 import (
    CapitalizerSourceCISDWindow,
    CapitalizerSourceClosureWindow,
)
from qore.infrastructure.trader_lab.capitalizer_source_poi_v2 import (
    CapitalizerSourcePOI,
    detect_external_liquidity_swing,
)


def _bar(open_: str, high: str, low: str, close: str) -> CapitalizerSourceBar:
    return CapitalizerSourceBar(
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def _swing_high(price: str) -> CapitalizerSourcePOI:
    level = Decimal(price)
    poi = detect_external_liquidity_swing(
        left=_bar(str(level - 2), str(level - 1), str(level - 3), str(level - 1.5)),
        center=_bar(str(level - 1), str(level), str(level - 2), str(level - 0.5)),
        right=_bar(str(level - 1), str(level - 0.5), str(level - 2), str(level - 1.5)),
    )
    assert poi is not None
    return poi


def _swing_low(price: str) -> CapitalizerSourcePOI:
    level = Decimal(price)
    poi = detect_external_liquidity_swing(
        left=_bar(str(level + 2), str(level + 3), str(level + 1), str(level + 2)),
        center=_bar(str(level + 1), str(level + 2), str(level), str(level + 1)),
        right=_bar(str(level + 1), str(level + 3), str(level + 0.5), str(level + 2)),
    )
    assert poi is not None
    return poi


def _input(*, reversal_confirmation_close: str) -> CapitalizerFTMObservationInput:
    daily_poi = _swing_low("97")
    external_high = _swing_high("102")
    continuation_poi = _swing_low("100.5")

    return CapitalizerFTMObservationInput(
        symbol="USDCAD",
        session=CapitalizerSession.NEW_YORK,
        observed_at=datetime(2026, 1, 5, 12, 30, tzinfo=UTC),
        entry_price=Decimal("102.4"),
        asian_open_reference_at=None,
        daily_closure_window=CapitalizerSourceClosureWindow(
            previous=_bar("100", "102", "98", "99"),
            candle2=_bar("99", "101", "97", "99.5"),
            candle3=None,
            pois=(daily_poi,),
        ),
        external_liquidity_poi=external_high,
        sweep_bar=_bar("101", "103", "100.8", "102.2"),
        expected_reversal_window=CapitalizerSourceCISDWindow(
            causal_series=(
                _bar("101", "103", "100.8", "102.5"),
            ),
            confirmation_bar=_bar(
                "102.4",
                "102.8",
                "100.3",
                reversal_confirmation_close,
            ),
            important_pois=(external_high,),
            protected_swing_origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
        ),
        continuation_window=CapitalizerSourceCISDWindow(
            causal_series=(
                _bar("102.2", "102.5", "100.5", "101"),
            ),
            confirmation_bar=_bar("101", "103", "100.8", "102.6"),
            important_pois=(continuation_poi,),
            protected_swing_origin=CapitalizerProtectedSwingOrigin.LIQUIDITY_SWEEP,
        ),
        previous_daily_bar=_bar("100", "105", "95", "102"),
        bars_since_current_day_open=(
            _bar("100", "103", "99", "102"),
        ),
    )


def test_raw_ftm_confirms_only_when_expected_reversal_fails() -> None:
    snapshot = build_ftm_observation_snapshot(
        _input(reversal_confirmation_close="101.5")
    )

    assert snapshot.session.eligible is True
    assert snapshot.daily_bias.direction is CapitalizerSourceDirection.BULLISH
    assert snapshot.liquidity_take.level_taken is True
    assert snapshot.expected_reversal_cisd.structural_confirmed is False
    assert snapshot.continuation_cisd.structural_confirmed is True
    assert snapshot.continuation_protected_swing is not None
    assert snapshot.failure_to_manipulate.confirmed is True
    assert snapshot.structural_target is not None
    assert snapshot.structural_target.valid is True
    assert snapshot.complete is True
    assert snapshot.future_outcomes_used is False
    assert snapshot.manual_liquidity_boolean_used is False


def test_raw_ftm_is_rejected_when_expected_reversal_cisd_confirms() -> None:
    snapshot = build_ftm_observation_snapshot(
        _input(reversal_confirmation_close="100.5")
    )

    assert snapshot.expected_reversal_cisd.structural_confirmed is True
    assert snapshot.failure_to_manipulate.expected_reversal_cisd_confirmed is True
    assert snapshot.failure_to_manipulate.confirmed is False
    assert snapshot.complete is False
