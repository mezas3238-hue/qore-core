from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import AccountWideRiskError
from qore.infrastructure.fundednext_mt5 import Mt5SymbolSpecification
from qore.infrastructure.vt08_forex_cibo_operational import (
    R315_METHOD_FINGERPRINT,
    R315_RISK_FINGERPRINT,
    Vt08ForexCiboAuthorization,
    Vt08ForexCiboPosture,
    Vt08ForexCiboSetup,
    evaluate_vt08_forex_cibo,
)
from qore.infrastructure.vt08_forex_fundednext_sizing import build_certified_vt08_forex_cibo_request

_NOW = datetime(2026, 9, 14, 4, 0, tzinfo=UTC)


def _spec(symbol: str, *, step: str = "0.01") -> Mt5SymbolSpecification:
    return Mt5SymbolSpecification(
        provider_symbol=f"{symbol}.a",
        bid=Decimal("99.99"),
        ask=Decimal("100.01"),
        spread_points=Decimal("2"),
        digits=2,
        point=Decimal("0.01"),
        contract_size=Decimal("100000"),
        tick_size=Decimal("0.01"),
        tick_value=Decimal("1"),
        minimum_volume=Decimal(step),
        maximum_volume=Decimal("100"),
        volume_step=Decimal(step),
        minimum_stop_distance_points=Decimal("5"),
        freeze_level_points=Decimal("0"),
        margin_per_volume=Decimal("50"),
        trade_enabled=True,
        session_open=True,
        observed_at=_NOW,
    )


def _cibo(
    symbol: str,
    *,
    enabled: bool = True,
    posture: Vt08ForexCiboPosture = Vt08ForexCiboPosture.NORMAL,
) -> Vt08ForexCiboAuthorization:
    side = "long" if symbol == "GBPJPY" else "short"
    stop = Decimal("99") if side == "long" else Decimal("101")
    target = Decimal("102") if side == "long" else Decimal("98")
    setup = Vt08ForexCiboSetup(
        signal_fingerprint=f"signal-{symbol}",
        setup_fingerprint=f"setup-{symbol}",
        qore_symbol=symbol,
        side=side,
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=stop,
        take_profit=target,
        methodology_fingerprint=R315_METHOD_FINGERPRINT,
        risk_policy_fingerprint=R315_RISK_FINGERPRINT,
        decided_at=_NOW,
        expires_at=_NOW + timedelta(minutes=2),
    )
    return evaluate_vt08_forex_cibo(
        setup,
        enabled=enabled,
        certification_current=True,
        now=_NOW,
        requested_posture=posture,
    )


@pytest.mark.parametrize(
    ("symbol", "expected_volume"),
    (("AUDJPY", "0.04"), ("GBPUSD", "0.04"), ("GBPJPY", "0.03")),
)
def test_certified_bps_size_includes_opening_commission(
    symbol: str,
    expected_volume: str,
) -> None:
    request = build_certified_vt08_forex_cibo_request(
        request_id=f"request-{symbol}",
        cibo_authorization=_cibo(symbol),
        provider_spec=_spec(symbol),
        account_equity=Decimal("2000"),
    )
    assert request.requested_volume == Decimal(expected_volume)
    assert request.stop_loss_per_volume == Decimal("107")
    assert request.provider_symbol == f"{symbol}.a"


def test_bank_and_attack_do_not_increase_frozen_per_trade_vt08_size() -> None:
    normal = build_certified_vt08_forex_cibo_request(
        request_id="request-normal",
        cibo_authorization=_cibo("GBPUSD", posture=Vt08ForexCiboPosture.NORMAL),
        provider_spec=_spec("GBPUSD"),
        account_equity=Decimal("2000"),
    )
    bank = build_certified_vt08_forex_cibo_request(
        request_id="request-bank",
        cibo_authorization=_cibo("GBPUSD", posture=Vt08ForexCiboPosture.BANK),
        provider_spec=_spec("GBPUSD"),
        account_equity=Decimal("2000"),
    )
    attack = build_certified_vt08_forex_cibo_request(
        request_id="request-attack",
        cibo_authorization=_cibo("GBPUSD", posture=Vt08ForexCiboPosture.ATTACK),
        provider_spec=_spec("GBPUSD"),
        account_equity=Decimal("2000"),
    )
    assert normal.requested_volume == bank.requested_volume == attack.requested_volume
    assert attack.requested_stop_risk == normal.requested_stop_risk


def test_broker_volume_step_change_is_obeyed() -> None:
    request = build_certified_vt08_forex_cibo_request(
        request_id="request-GBPUSD",
        cibo_authorization=_cibo("GBPUSD"),
        provider_spec=_spec("GBPUSD", step="0.02"),
        account_equity=Decimal("2000"),
    )
    assert request.requested_volume == Decimal("0.04")


def test_cibo_deny_cannot_reach_risk_request() -> None:
    with pytest.raises(AccountWideRiskError, match="CIBO denied setup"):
        build_certified_vt08_forex_cibo_request(
            request_id="request-GBPUSD",
            cibo_authorization=_cibo("GBPUSD", enabled=False),
            provider_spec=_spec("GBPUSD"),
            account_equity=Decimal("2000"),
        )


def test_vt08_requests_broker_minimum_and_delegates_actual_risk() -> None:
    request = build_certified_vt08_forex_cibo_request(
        request_id="request-minimum-uplift",
        cibo_authorization=_cibo("GBPUSD"),
        provider_spec=_spec("GBPUSD"),
        account_equity=Decimal("100"),
    )
    assert request.strategy_requested_risk_usd == Decimal("0.25")
    assert request.requested_volume == Decimal("0.01")
    assert request.requested_stop_risk == Decimal("1.07")
    assert request.minimum_volume_uplifted is True
