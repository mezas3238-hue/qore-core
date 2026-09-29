from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
    CompoundCapitalLot,
    CompoundCapitalState,
    CompoundRealizedProfitEvidence,
    create_realized_profit_lot,
)
from qore.infrastructure.cibo_compound_portfolio_ledger import (
    CompoundPortfolioLedger,
)
from qore.infrastructure.cibo_compound_portfolio_store import (
    DurableCompoundPortfolioStore,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

T0 = datetime(2026, 9, 29, 16, 0, tzinfo=UTC)


def _identity(
    account_ref: str = "compound-demo-1",
) -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref=account_ref,
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _evidence(
    *,
    account: CiboAccountCapitalIdentity | None = None,
    evidence_id: str = "settlement-1",
    profit: str = "100",
    reconciled: bool = True,
    closed: bool = True,
    floating: bool = False,
) -> CompoundRealizedProfitEvidence:
    return CompoundRealizedProfitEvidence(
        evidence_id=evidence_id,
        account_identity=account or _identity(),
        origin_trader=TraderLineage.VT31_NAS100,
        signal_fingerprint=f"signal-{evidence_id}",
        position_id=1001,
        settlement_deal_ids=(2001, 2002),
        realized_net_profit_usd=Decimal(profit),
        realized_at=T0,
        source_settlement_sha256="sha256:" + "a" * 64,
        settlement_reconciled=reconciled,
        position_closed=closed,
        floating_pnl_used_as_capital=floating,
    )


def _lot(
    *,
    lot_id: str = "lot-1",
    account: CiboAccountCapitalIdentity | None = None,
    profit: str = "100",
    parent_lots: tuple[CompoundCapitalLot, ...] = (),
) -> CompoundCapitalLot:
    return create_realized_profit_lot(
        _evidence(
            account=account,
            evidence_id=f"evidence-{lot_id}",
            profit=profit,
        ),
        lot_id=lot_id,
        created_at=T0 + timedelta(seconds=1),
        parent_lots=parent_lots,
    )


def test_compound_capital_requires_terminal_reconciled_realized_profit() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="unreconciled settlement",
    ):
        create_realized_profit_lot(
            _evidence(reconciled=False),
            lot_id="bad-unreconciled",
            created_at=T0 + timedelta(seconds=1),
        )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="non-terminal settlement",
    ):
        create_realized_profit_lot(
            _evidence(closed=False),
            lot_id="bad-open",
            created_at=T0 + timedelta(seconds=1),
        )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="floating PnL",
    ):
        create_realized_profit_lot(
            _evidence(floating=True),
            lot_id="bad-floating",
            created_at=T0 + timedelta(seconds=1),
        )


def test_compound_generation_is_account_local_and_parent_derived() -> None:
    parent = _lot(lot_id="gen1")
    assert parent.generation == 1

    child = create_realized_profit_lot(
        _evidence(evidence_id="settlement-gen2", profit="25"),
        lot_id="gen2",
        created_at=T0 + timedelta(seconds=2),
        parent_lots=(parent,),
    )
    assert child.generation == 2
    assert child.parent_lot_ids == ("gen1",)
    assert child.core_owned is True
    assert child.runtime_authority is False

    other_account_parent = _lot(
        lot_id="other-account",
        account=_identity("compound-demo-2"),
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="cannot cross account domains",
    ):
        create_realized_profit_lot(
            _evidence(evidence_id="cross-account"),
            lot_id="cross-account-child",
            created_at=T0 + timedelta(seconds=2),
            parent_lots=(other_account_parent,),
        )


def test_portfolio_partition_prevents_double_spend_and_reserve_shortcut() -> None:
    ledger = CompoundPortfolioLedger(account_identity=_identity())
    lot = _lot()
    ledger = ledger.admit_realized_profit(
        lot,
        event_id="admit-1",
        occurred_at=T0 + timedelta(seconds=2),
    )

    ledger = ledger.transition(
        source_lot_id="lot-1",
        to_state=CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
        amount_usd=Decimal("40"),
        moved_lot_id="floor-40",
        remainder_lot_id="realized-60",
        event_id="protect-40",
        occurred_at=T0 + timedelta(seconds=3),
    )

    assert ledger.current_partition_usd == Decimal("100")
    assert ledger.balance(
        CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR
    ) == Decimal("40")
    assert ledger.balance(
        CompoundCapitalState.REALIZED_PROFIT
    ) == Decimal("60")

    with pytest.raises(
        CiboCompoundCapitalError,
        match="active compound lot not found",
    ):
        ledger.transition(
            source_lot_id="lot-1",
            to_state=CompoundCapitalState.COMPOUNDABLE,
            amount_usd=Decimal("10"),
            moved_lot_id="double-spend",
            remainder_lot_id="double-spend-rem",
            event_id="double-spend-event",
            occurred_at=T0 + timedelta(seconds=4),
        )

    ledger = ledger.transition(
        source_lot_id="realized-60",
        to_state=CompoundCapitalState.STRATEGIC_RESERVE,
        amount_usd=Decimal("20"),
        moved_lot_id="reserve-20",
        remainder_lot_id="realized-40",
        event_id="reserve-20-event",
        occurred_at=T0 + timedelta(seconds=4),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="illegal compound transition",
    ):
        ledger.transition(
            source_lot_id="reserve-20",
            to_state=CompoundCapitalState.DEPLOYED_COMPOUND_CAPITAL,
            amount_usd=Decimal("20"),
            moved_lot_id="illegal-deploy",
            event_id="illegal-deploy-event",
            occurred_at=T0 + timedelta(seconds=5),
        )


def test_deployment_settlement_preserves_loss_as_consumed_capital() -> None:
    ledger = CompoundPortfolioLedger(account_identity=_identity())
    ledger = ledger.admit_realized_profit(
        _lot(),
        event_id="admit",
        occurred_at=T0 + timedelta(seconds=2),
    )
    ledger = ledger.transition(
        source_lot_id="lot-1",
        to_state=CompoundCapitalState.COMPOUNDABLE,
        amount_usd=Decimal("100"),
        moved_lot_id="compoundable",
        event_id="compoundable-event",
        occurred_at=T0 + timedelta(seconds=3),
    )
    ledger = ledger.transition(
        source_lot_id="compoundable",
        to_state=CompoundCapitalState.ACTIVE_COMPOUND_CAPACITY,
        amount_usd=Decimal("100"),
        moved_lot_id="active",
        event_id="activate-event",
        occurred_at=T0 + timedelta(seconds=4),
    )
    ledger = ledger.transition(
        source_lot_id="active",
        to_state=CompoundCapitalState.DEPLOYED_COMPOUND_CAPITAL,
        amount_usd=Decimal("100"),
        moved_lot_id="deployed",
        event_id="deploy-event",
        occurred_at=T0 + timedelta(seconds=5),
    )
    ledger = ledger.settle_deployment(
        source_lot_id="deployed",
        returned_capacity_usd=Decimal("70"),
        returned_lot_id="returned-70",
        consumed_lot_id="consumed-30",
        event_id="settle-event",
        occurred_at=T0 + timedelta(seconds=6),
    )

    assert ledger.current_partition_usd == Decimal("100")
    assert ledger.current_economic_value_usd == Decimal("70")
    assert ledger.balance(
        CompoundCapitalState.RELEASED_COMPOUND_CAPITAL
    ) == Decimal("70")
    assert ledger.balance(
        CompoundCapitalState.CONSUMED
    ) == Decimal("30")


def test_compound_store_hash_chain_cas_restart_and_account_isolation(
    tmp_path: Path,
) -> None:
    identity = _identity()
    store = DurableCompoundPortfolioStore(
        tmp_path / "compound.json",
        account_identity=identity,
    )
    ledger = CompoundPortfolioLedger(
        account_identity=identity,
    ).admit_realized_profit(
        _lot(),
        event_id="admit-store",
        occurred_at=T0 + timedelta(seconds=2),
    )

    first = store.store(ledger, expected_generation=0)
    assert first.generation == 1
    assert first.ledger == ledger
    assert first.chain_sha256.startswith("sha256:")
    assert store.load() == first

    idempotent = store.store(ledger, expected_generation=1)
    assert idempotent == first

    with pytest.raises(
        CiboCompoundCapitalError,
        match="generation conflict",
    ):
        store.store(ledger, expected_generation=0)

    other = DurableCompoundPortfolioStore(
        tmp_path / "compound.json",
        account_identity=_identity("different-account"),
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="account identity mismatch",
    ):
        other.load()
