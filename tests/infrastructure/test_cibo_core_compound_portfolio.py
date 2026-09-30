from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
    CompoundCapitalState,
    CompoundRealizedProfitEvidence,
    create_realized_profit_lot,
)
from qore.infrastructure.cibo_compound_floor import (
    ProtectedCapitalFloorLedger,
)
from qore.infrastructure.cibo_compound_portfolio_ledger import (
    CompoundPortfolioLedger,
)
from qore.infrastructure.cibo_core_compound_portfolio import (
    AccountCoreCompoundPortfolio,
    QoreCoreCompoundPortfolio,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

T0 = datetime(2026, 9, 29, 17, 15, tzinfo=UTC)


def _identity(account_ref: str) -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref=account_ref,
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _account_snapshot(
    account_ref: str,
    *,
    trader: TraderLineage,
    profit: str,
    floor_amount: str,
) -> AccountCoreCompoundPortfolio:
    identity = _identity(account_ref)
    evidence = CompoundRealizedProfitEvidence(
        evidence_id=f"{account_ref}-settlement",
        account_identity=identity,
        origin_trader=trader,
        signal_fingerprint=f"{account_ref}-signal",
        position_id=101,
        settlement_deal_ids=(201,),
        realized_net_profit_usd=Decimal(profit),
        realized_at=T0,
        source_settlement_sha256="sha256:" + "a" * 64,
        settlement_reconciled=True,
        position_closed=True,
    )
    lot = create_realized_profit_lot(
        evidence,
        lot_id=f"{account_ref}-realized",
        created_at=T0 + timedelta(seconds=1),
    )
    portfolio = CompoundPortfolioLedger(
        account_identity=identity
    ).admit_realized_profit(
        lot,
        event_id=f"{account_ref}-admit",
        occurred_at=T0 + timedelta(seconds=2),
    )
    floor_value = Decimal(floor_amount)
    if floor_value > 0:
        portfolio = portfolio.transition(
            source_lot_id=lot.lot_id,
            to_state=CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
            amount_usd=floor_value,
            moved_lot_id=f"{account_ref}-floor",
            remainder_lot_id=(
                None
                if floor_value == Decimal(profit)
                else f"{account_ref}-remainder"
            ),
            event_id=f"{account_ref}-protect",
            occurred_at=T0 + timedelta(seconds=3),
        )
        floor = ProtectedCapitalFloorLedger(
            account_identity=identity
        ).admit_retired_lot(
            portfolio.lot(f"{account_ref}-floor"),
            tranche_id=f"{account_ref}-tranche",
            event_id=f"{account_ref}-floor-admit",
            admitted_at=T0 + timedelta(seconds=4),
        )
    else:
        floor = ProtectedCapitalFloorLedger(
            account_identity=identity
        )
    return AccountCoreCompoundPortfolio(
        account_identity=identity,
        compound_ledger=portfolio,
        protected_floor_ledger=floor,
    )


def test_account_portfolio_binds_floor_to_retired_capital_exactly() -> None:
    account = _account_snapshot(
        "account-a",
        trader=TraderLineage.VT31_NAS100,
        profit="100",
        floor_amount="40",
    )

    assert account.admitted_realized_profit_usd == Decimal("100")
    assert account.current_partition_usd == Decimal("100")
    assert account.current_economic_value_usd == Decimal("100")
    assert account.protected_floor_usd == Decimal("40")
    assert account.realized_unclassified_profit_usd == Decimal("60")
    assert account.runtime_authority is False
    assert account.cross_account_transfer_authority is False


def test_account_portfolio_rejects_unbound_retired_floor_capital() -> None:
    valid = _account_snapshot(
        "account-b",
        trader=TraderLineage.R34_XAUUSD,
        profit="80",
        floor_amount="20",
    )
    empty_floor = ProtectedCapitalFloorLedger(
        account_identity=valid.account_identity
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="floor/retired-lot coverage mismatch",
    ):
        AccountCoreCompoundPortfolio(
            account_identity=valid.account_identity,
            compound_ledger=valid.compound_ledger,
            protected_floor_ledger=empty_floor,
        )


def test_global_view_aggregates_but_never_makes_accounts_fungible() -> None:
    left = _account_snapshot(
        "account-left",
        trader=TraderLineage.VT31_NAS100,
        profit="100",
        floor_amount="40",
    )
    right = _account_snapshot(
        "account-right",
        trader=TraderLineage.R34_XAUUSD,
        profit="60",
        floor_amount="10",
    )
    global_view = QoreCoreCompoundPortfolio(accounts=(left, right))

    assert global_view.total_admitted_realized_profit_usd == Decimal("160")
    assert global_view.total_current_economic_value_usd == Decimal("160")
    assert global_view.total_protected_floor_usd == Decimal("50")
    assert global_view.read_only is True
    assert global_view.cross_account_transfer_authority is False
    assert global_view.runtime_authority is False
    assert all(
        row.economic_owner == "CORE"
        for row in global_view.attribution
    )

    by_trader = dict(global_view.attributed_value_by_trader())
    assert by_trader[TraderLineage.VT31_NAS100] == Decimal("100")
    assert by_trader[TraderLineage.R34_XAUUSD] == Decimal("60")


def test_global_view_rejects_duplicate_account_domain() -> None:
    account = _account_snapshot(
        "duplicate-account",
        trader=TraderLineage.VT31_NAS100,
        profit="50",
        floor_amount="0",
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="account domains must be unique",
    ):
        QoreCoreCompoundPortfolio(accounts=(account, account))
