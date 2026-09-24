from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import AccountWideRiskError
from qore.infrastructure.ctrader_demo_compat import CTraderDemoSymbolSpecification
from qore.infrastructure.ctrader_demo_vt08_sizing import build_ctrader_demo_vt08_cibo_request
from qore.infrastructure.vt08_forex_cibo_operational import (
    R315_METHOD_FINGERPRINT,
    R315_RISK_FINGERPRINT,
    Vt08ForexCiboAuthorization,
    Vt08ForexCiboPosture,
    Vt08ForexCiboSetup,
    evaluate_vt08_forex_cibo,
)

_NOW = datetime(2026, 9, 24, 14, 0, tzinfo=UTC)


def _spec(symbol: str, *, step: str = "0.01") -> CTraderDemoSymbolSpecification:
    return CTraderDemoSymbolSpecification(
        provider_symbol=symbol,
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
        minimum_stop_distance_points=Decimal("0"),
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
    (("AUDJPY", "0.05"), ("GBPUSD", "0.05"), ("GBPJPY", "0.04")),
)
def test_demo_sizing_uses_ctrader_tick_economics_only(
    symbol: str,
    expected_volume: str,
) -> None:
    request = build_ctrader_demo_vt08_cibo_request(
        request_id=f"request-{symbol}",
        cibo_authorization=_cibo(symbol),
        provider_spec=_spec(symbol),
        account_equity=Decimal("2000"),
    )
    assert request.requested_volume == Decimal(expected_volume)
    assert request.stop_loss_per_volume == Decimal("100")
    assert request.provider_symbol == symbol


def test_cibo_posture_is_not_reduced_by_account_allocator() -> None:
    normal = build_ctrader_demo_vt08_cibo_request(
        request_id="request-normal",
        cibo_authorization=_cibo("GBPUSD", posture=Vt08ForexCiboPosture.NORMAL),
        provider_spec=_spec("GBPUSD"),
        account_equity=Decimal("2000"),
    )
    attack = build_ctrader_demo_vt08_cibo_request(
        request_id="request-attack",
        cibo_authorization=_cibo("GBPUSD", posture=Vt08ForexCiboPosture.ATTACK),
        provider_spec=_spec("GBPUSD"),
        account_equity=Decimal("2000"),
    )
    assert normal.requested_volume == attack.requested_volume


def test_demo_sizing_obeys_ctrader_volume_step() -> None:
    request = build_ctrader_demo_vt08_cibo_request(
        request_id="request-step",
        cibo_authorization=_cibo("GBPUSD"),
        provider_spec=_spec("GBPUSD", step="0.02"),
        account_equity=Decimal("2000"),
    )
    assert request.requested_volume == Decimal("0.04")


def test_cibo_deny_cannot_submit() -> None:
    with pytest.raises(AccountWideRiskError, match="CIBO denied setup"):
        build_ctrader_demo_vt08_cibo_request(
            request_id="request-denied",
            cibo_authorization=_cibo("GBPUSD", enabled=False),
            provider_spec=_spec("GBPUSD"),
            account_equity=Decimal("2000"),
        )
