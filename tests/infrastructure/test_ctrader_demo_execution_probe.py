from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.ctrader_demo_execution_probe import (
    CTraderDemoOperationalCredentialBlockedError,
    CTraderDemoOperationalProbeInputs,
    CTraderDemoOperationalProbeValidationError,
    run_ctrader_demo_operational_probe,
)
from qore.infrastructure.order_intent import OrderSide, OrderType
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 23, 30, tzinfo=UTC)


def _inputs(
    *,
    token_material: bytes = b"demo-token-material",
    instrument: str = "EURUSD",
    side: OrderSide = OrderSide.BUY,
    quantity: str = "10",
    order_type: OrderType = OrderType.MARKET,
) -> CTraderDemoOperationalProbeInputs:
    return CTraderDemoOperationalProbeInputs(
        run_key="42-1",
        account_ref="demo-001",
        instrument=instrument,
        side=side,
        order_type=order_type,
        quantity=Decimal(quantity),
        started_at=_NOW,
        token_material=token_material,
    )


def test_probe_planning_is_secret_free() -> None:
    result = run_ctrader_demo_operational_probe(_inputs())
    assert isinstance(result, Success)
    evidence = result.value
    assert evidence.status == "planned"
    assert evidence.provider_key == "ctrader-demo"
    assert evidence.environment == "demo"
    assert evidence.account_fingerprint.startswith("sha256:")
    assert "demo-001" not in evidence.to_json()
    assert "demo-token-material" not in evidence.to_json()


def test_probe_absent_credentials_is_operational_blocker() -> None:
    result = run_ctrader_demo_operational_probe(_inputs(token_material=b""))
    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderDemoOperationalCredentialBlockedError)


def test_probe_rejects_limit_order_slice() -> None:
    with pytest.raises(CTraderDemoOperationalProbeValidationError):
        _inputs(order_type=OrderType.LIMIT)


def test_probe_rejects_invalid_instrument() -> None:
    with pytest.raises(CTraderDemoOperationalProbeValidationError):
        _inputs(instrument="eur usd")


def test_probe_inputs_repr_redacts_token_and_account() -> None:
    inputs = _inputs()
    rendered = repr(inputs)
    assert "<redacted>" in rendered
    assert "demo-token-material" not in rendered
    assert "demo-001" not in rendered


def test_probe_evidence_public_payload_is_stable() -> None:
    result = run_ctrader_demo_operational_probe(_inputs())
    assert isinstance(result, Success)
    first = result.value.public_payload()
    second = run_ctrader_demo_operational_probe(_inputs())
    assert isinstance(second, Success)
    assert first == second.value.public_payload()


def test_evidence_schema_is_fixed() -> None:
    result = run_ctrader_demo_operational_probe(_inputs())
    assert isinstance(result, Success)
    assert result.value.public_payload()["schema"] == (
        "qore.ctrader-demo.execution-plan-evidence.v1"
    )
