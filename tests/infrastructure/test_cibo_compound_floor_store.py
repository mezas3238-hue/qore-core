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
    CompoundCapitalState,
    CompoundRealizedProfitEvidence,
    create_realized_profit_lot,
)
from qore.infrastructure.cibo_compound_floor import (
    ProtectedCapitalFloorLedger,
)
from qore.infrastructure.cibo_compound_floor_store import (
    DurableProtectedCapitalFloorStore,
)
from qore.infrastructure.cibo_compound_portfolio_ledger import (
    CompoundPortfolioLedger,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

T0 = datetime(2026, 9, 29, 17, 0, tzinfo=UTC)


def _identity(
    account_ref: str = "floor-store-account",
) -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref=account_ref,
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _floor(
    identity: CiboAccountCapitalIdentity,
) -> ProtectedCapitalFloorLedger:
    evidence = CompoundRealizedProfitEvidence(
        evidence_id="floor-store-settlement",
        account_identity=identity,
        origin_trader=TraderLineage.VT31_NAS100,
        signal_fingerprint="floor-store-signal",
        position_id=501,
        settlement_deal_ids=(601,),
        realized_net_profit_usd=Decimal("50"),
        realized_at=T0,
        source_settlement_sha256="sha256:" + "a" * 64,
        settlement_reconciled=True,
        position_closed=True,
    )
    lot = create_realized_profit_lot(
        evidence,
        lot_id="floor-store-realized",
        created_at=T0 + timedelta(seconds=1),
    )
    portfolio = CompoundPortfolioLedger(
        account_identity=identity
    ).admit_realized_profit(
        lot,
        event_id="floor-store-admit-profit",
        occurred_at=T0 + timedelta(seconds=2),
    )
    portfolio = portfolio.transition(
        source_lot_id=lot.lot_id,
        to_state=CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
        amount_usd=Decimal("50"),
        moved_lot_id="floor-store-retired",
        event_id="floor-store-retire",
        occurred_at=T0 + timedelta(seconds=3),
    )
    return ProtectedCapitalFloorLedger(
        account_identity=identity
    ).admit_retired_lot(
        portfolio.lot("floor-store-retired"),
        tranche_id="floor-store-tranche",
        event_id="floor-store-floor-admit",
        admitted_at=T0 + timedelta(seconds=4),
    )


def test_floor_store_hash_chain_cas_restart_and_policy_upgrade(
    tmp_path: Path,
) -> None:
    identity = _identity()
    store = DurableProtectedCapitalFloorStore(
        tmp_path / "floor.json",
        account_identity=identity,
    )
    floor = _floor(identity)
    first = store.store(floor, expected_generation=0)

    assert first.generation == 1
    assert first.ledger.total_floor_usd == Decimal("50")
    assert first.chain_sha256.startswith("sha256:")
    assert store.load() == first

    upgraded = floor.upgrade_to_policy_protected(
        tranche_id="floor-store-tranche",
        event_id="floor-store-policy",
        occurred_at=T0 + timedelta(seconds=5),
        policy_id="GEN-C2-SHADOW-POLICY",
        policy_sha256="sha256:" + "b" * 64,
    )
    second = store.store(upgraded, expected_generation=1)

    assert second.generation == 2
    assert second.ledger.total_floor_usd == Decimal("50")
    assert second.ledger.policy_protected_floor_usd == Decimal("50")
    assert store.load() == second

    with pytest.raises(
        CiboCompoundCapitalError,
        match="generation conflict",
    ):
        store.store(upgraded, expected_generation=1)


def test_floor_store_rejects_cross_account_reopen(
    tmp_path: Path,
) -> None:
    identity = _identity()
    path = tmp_path / "floor.json"
    store = DurableProtectedCapitalFloorStore(
        path,
        account_identity=identity,
    )
    store.store(_floor(identity), expected_generation=0)

    wrong_account = DurableProtectedCapitalFloorStore(
        path,
        account_identity=_identity("other-account"),
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="account identity mismatch",
    ):
        wrong_account.load()
