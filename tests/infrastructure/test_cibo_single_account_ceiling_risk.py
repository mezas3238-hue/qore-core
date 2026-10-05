from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_single_account_ceiling_risk import (
    build_ceiling_risk_snapshot,
)
from qore.infrastructure.cibo_single_account_ceiling_state import (
    CiboCeilingOpenExposure,
    initialize_ceiling_account_state,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment


NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


@dataclass(frozen=True)
class _Budget:
    provider_headroom: Decimal
    max_risk_at_any_time: Decimal
    active_mll: Decimal
    hard_breach: bool = False


def _account():
    identity = CiboAccountCapitalIdentity(
        provider_key="ctrader-research",
        account_ref="ceiling-account",
        environment=MarketRuntimeEnvironment.DEMO,
    )
    account = initialize_ceiling_account_state(account_identity=identity)
    exposure = CiboCeilingOpenExposure(
        signal_fingerprint="open-1",
        trader_id=TraderLineage.R34_XAUUSD,
        qore_symbol="XAUUSD",
        side="long",
        entry_at=NOW - timedelta(minutes=10),
        volume=Decimal("1"),
        stop_risk_usd=Decimal("7"),
        margin_usd=Decimal("11"),
        provider_cost_usd=Decimal("0.1"),
        entry_price=Decimal("100"),
        structural_stop=Decimal("99"),
        technical_target=Decimal("103"),
        entry_expected_net_value_usd=Decimal("1"),
        entry_expected_capital_minutes=Decimal("30"),
        expectation_evidence_sha256="sha256:" + "a" * 64,
    )
    return replace(account, open_exposures=(exposure,))


def test_risk_snapshot_uses_account_risk_but_explicit_provider_budget() -> None:
    account = _account()
    budget = _Budget(
        provider_headroom=Decimal("50"),
        max_risk_at_any_time=Decimal("40"),
        active_mll=Decimal("5"),
    )

    snapshot = build_ceiling_risk_snapshot(
        account=account,
        provider_budget=budget,
        reconciled_at=NOW,
        provider_free_margin_usd=Decimal("42"),
        open_floating_loss_usd=Decimal("2"),
        pending_broker_worst_case_loss_usd=Decimal("3"),
        qore_authorizable_headroom_usd=Decimal("35"),
    )

    assert snapshot.account_binding_id == "ceiling-account"
    assert snapshot.equity == Decimal("60")
    assert snapshot.open_stop_worst_case_loss == Decimal("7")
    assert snapshot.margin_used == Decimal("11")
    assert snapshot.free_margin == Decimal("42")
    assert snapshot.open_floating_loss == Decimal("2")
    assert snapshot.pending_broker_worst_case_loss == Decimal("3")
    assert snapshot.qore_authorizable_headroom == Decimal("35")
    assert snapshot.provider_budget is budget


def test_risk_snapshot_rejects_internal_headroom_above_realized_equity() -> None:
    account = _account()
    budget = _Budget(
        provider_headroom=Decimal("100"),
        max_risk_at_any_time=Decimal("100"),
        active_mll=Decimal("0"),
    )

    with pytest.raises(CiboCapitalManagementError):
        build_ceiling_risk_snapshot(
            account=account,
            provider_budget=budget,
            reconciled_at=NOW,
            provider_free_margin_usd=Decimal("60"),
            open_floating_loss_usd=Decimal("0"),
            pending_broker_worst_case_loss_usd=Decimal("0"),
            qore_authorizable_headroom_usd=Decimal("61"),
        )
