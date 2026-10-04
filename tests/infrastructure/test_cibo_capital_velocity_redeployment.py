from datetime import timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_capital_velocity_redeployment import (
    CiboCapitalReleaseEvent,
    CiboCapitalVelocityLedger,
    consume_release_once,
    propose_redeployment,
    record_redeployment,
)
from qore.infrastructure.cibo_full_economic_digital_twin import (
    CiboIdleCapitalClass,
)
from tests.infrastructure.test_cibo_full_economic_digital_twin import T0, _full_twin


def _release() -> CiboCapitalReleaseEvent:
    return CiboCapitalReleaseEvent(
        release_id="t14:position-1:release-1",
        released_at=T0,
        signal_fingerprint="position-1",
        released_stop_risk_usd=Decimal("1"),
        released_margin_usd=Decimal("2"),
        source="T14",
    )


def test_release_is_consumed_exactly_once() -> None:
    release = _release()
    first = consume_release_once(CiboCapitalVelocityLedger(), release)

    assert first.total_released_stop_risk_usd == Decimal("1")
    assert first.total_released_margin_usd == Decimal("2")

    with pytest.raises(
        CiboCapitalManagementError,
        match="double release",
    ):
        consume_release_once(first, release)


def test_released_capacity_finds_causal_current_opportunity() -> None:
    twin = _full_twin()
    release = _release()

    proposal = propose_redeployment(twin=twin, release=release)

    assert proposal.selected_option_id == "known-r34"
    assert proposal.idle_classification is CiboIdleCapitalClass.UNNECESSARY_IDLE
    assert proposal.proposed_stop_risk_usd == Decimal("1")
    assert proposal.proposed_margin_usd == Decimal("2")
    assert proposal.risk_authority is False
    assert proposal.execution_authority is False


def test_redeployment_cannot_exceed_released_capacity() -> None:
    release = _release()
    ledger = consume_release_once(CiboCapitalVelocityLedger(), release)
    proposal = propose_redeployment(twin=_full_twin(), release=release)

    updated = record_redeployment(ledger, proposal)

    assert updated.total_redeployed_stop_risk_usd == Decimal("1")
    assert updated.total_redeployed_margin_usd == Decimal("2")

    with pytest.raises(
        CiboCapitalManagementError,
        match="cannot redeploy more risk than released",
    ):
        record_redeployment(updated, proposal)


def test_twin_predating_release_cannot_redeploy_future_capacity() -> None:
    release = CiboCapitalReleaseEvent(
        release_id="future-release",
        released_at=T0 + timedelta(minutes=1),
        signal_fingerprint="position-1",
        released_stop_risk_usd=Decimal("1"),
        released_margin_usd=Decimal("2"),
        source="T14",
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="predates capital release",
    ):
        propose_redeployment(twin=_full_twin(), release=release)
