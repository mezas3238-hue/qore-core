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
    Vt08ForexCiboSetup,
    evaluate_vt08_forex_cibo,
)
from qore.infrastructure.vt08_forex_fundednext_sizing import (
    build_certified_vt08_forex_cibo_request,
)

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


def _cibo(symbol: str, *, enabled: bool = True) -> Vt08ForexCiboAuthorization:
    setup = Vt08ForexCiboSetup(
        signal_fingerprint=f"signal-{symbol}",
        setup_fingerprint=f"setup-{symbol}",
        qore_symbol=symbol,
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
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
    )


@pytest.mark.parametrize(
    ("symbol", "expected_volume"),
    (("AUDJPY", "0.05"), ("GBPUSD", "0.05"), ("GBPJPY", "0.04")),
)
def test_certified_bps_size_from_mt5_tick_value(
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
    assert request.stop_loss_per_volume == Decimal("100")
    assert request.provider_symbol == f"{symbol}.a"


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
