from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import CiboRiskRequest, TraderLineage
from qore.infrastructure.cibo_trader_opportunity_adapter import (
    ACTIVE_CMA_TRADERS,
    legacy_request_to_cma_opportunity,
)


def _request(trader: TraderLineage) -> CiboRiskRequest:
    now = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
    return CiboRiskRequest(
        request_id="req-1",
        trader_id=trader,
        signal_fingerprint=f"signal-{trader.value}",
        qore_symbol="NAS100" if trader is TraderLineage.VT31_NAS100 else "EURUSD",
        provider_symbol="USTEC" if trader is TraderLineage.VT31_NAS100 else "EURUSD",
        side="long",
        entry_type="MARKET",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("90"),
        take_profit=Decimal("120"),
        requested_volume=Decimal("5.00"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("20"),
        requested_at=now,
        expires_at=now + timedelta(minutes=1),
        strategy_requested_risk_usd=Decimal("50"),
    )


@pytest.mark.parametrize("trader", ACTIVE_CMA_TRADERS)
def test_adapter_strips_legacy_volume_authority(trader: TraderLineage) -> None:
    request = _request(trader)

    opportunity = legacy_request_to_cma_opportunity(
        request,
        provider_maximum_volume=Decimal("100"),
    )

    assert not hasattr(opportunity, "requested_volume")
    assert opportunity.signal_fingerprint == request.signal_fingerprint
    assert opportunity.stop_loss == request.stop_loss
    assert opportunity.take_profit == request.take_profit
    assert opportunity.stop_loss_per_volume == request.stop_loss_per_volume


def test_vt31_preserves_four_step_management_indivisibility() -> None:
    opportunity = legacy_request_to_cma_opportunity(
        _request(TraderLineage.VT31_NAS100),
        provider_maximum_volume=Decimal("100"),
    )

    assert opportunity.minimum_execution_steps == 4


def test_other_active_traders_default_to_one_execution_step() -> None:
    for trader in ACTIVE_CMA_TRADERS:
        if trader is TraderLineage.VT31_NAS100:
            continue
        opportunity = legacy_request_to_cma_opportunity(
            _request(trader),
            provider_maximum_volume=Decimal("100"),
        )
        assert opportunity.minimum_execution_steps == 1


def test_vt08_index_is_not_silently_migrated_into_current_cma_scope() -> None:
    request = _request(TraderLineage.VT08_INDEX)

    with pytest.raises(ValueError, match="outside active CMA"):
        legacy_request_to_cma_opportunity(
            request,
            provider_maximum_volume=Decimal("100"),
        )
