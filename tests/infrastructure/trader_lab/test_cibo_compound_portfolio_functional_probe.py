from __future__ import annotations

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
from qore.infrastructure.cibo_compound_floor import ProtectedCapitalFloorLedger
from qore.infrastructure.cibo_compound_portfolio_ledger import CompoundPortfolioLedger
from qore.infrastructure.cibo_core_compound_portfolio import (
    AccountCoreCompoundPortfolio,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment
from qore.infrastructure.trader_lab.candidate import TraderLabCandidateBinding

NOW = datetime(2026, 10, 3, 3, 20, tzinfo=UTC)


def _tag(candidate: TraderLabCandidateBinding, suffix: str) -> str:
    return f"trader-lab:{candidate.fingerprint.value}:{suffix}"


def _identity(candidate: TraderLabCandidateBinding) -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="trader-lab",
        account_ref=_tag(candidate, "compound-portfolio"),
        environment=MarketRuntimeEnvironment.TEST,
    )


def _lot(
    candidate: TraderLabCandidateBinding,
    *,
    trader: TraderLineage,
    suffix: str,
    amount: str,
    position_id: int,
    deal_id: int,
):
    identity = _identity(candidate)
    evidence = CompoundRealizedProfitEvidence(
        evidence_id=_tag(candidate, f"settlement:{suffix}"),
        account_identity=identity,
        origin_trader=trader,
        signal_fingerprint=_tag(candidate, f"signal:{suffix}"),
        position_id=position_id,
        settlement_deal_ids=(deal_id,),
        realized_net_profit_usd=Decimal(amount),
        realized_at=NOW,
        source_settlement_sha256=(
            "sha256:" + ("a" if suffix == "vt31" else "b") * 64
        ),
        settlement_reconciled=True,
        position_closed=True,
    )
    return create_realized_profit_lot(
        evidence,
        lot_id=_tag(candidate, f"lot:{suffix}"),
        created_at=NOW + timedelta(seconds=1),
    )


def test_trader_lab_compound_portfolio_multi_trader_conservation(
    candidate_factory,
) -> None:
    candidate = candidate_factory(candidate_suffix=950)
    identity = _identity(candidate)
    vt31 = _lot(
        candidate,
        trader=TraderLineage.VT31_NAS100,
        suffix="vt31",
        amount="60",
        position_id=95001,
        deal_id=95101,
    )
    r34 = _lot(
        candidate,
        trader=TraderLineage.R34_XAUUSD,
        suffix="r34",
        amount="40",
        position_id=95002,
        deal_id=95102,
    )

    ledger = CompoundPortfolioLedger(account_identity=identity)
    ledger = ledger.admit_realized_profit(
        vt31,
        event_id=_tag(candidate, "admit:vt31"),
        occurred_at=NOW + timedelta(seconds=2),
    )
    ledger = ledger.admit_realized_profit(
        r34,
        event_id=_tag(candidate, "admit:r34"),
        occurred_at=NOW + timedelta(seconds=3),
    )
    ledger = ledger.transition(
        source_lot_id=vt31.lot_id,
        to_state=CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
        amount_usd=Decimal("20"),
        moved_lot_id=_tag(candidate, "floor:vt31"),
        remainder_lot_id=_tag(candidate, "remainder:vt31"),
        event_id=_tag(candidate, "protect:vt31"),
        occurred_at=NOW + timedelta(seconds=4),
    )

    floor = ProtectedCapitalFloorLedger(
        account_identity=identity
    ).admit_retired_lot(
        ledger.lot(_tag(candidate, "floor:vt31")),
        tranche_id=_tag(candidate, "floor-tranche"),
        event_id=_tag(candidate, "floor-admit"),
        admitted_at=NOW + timedelta(seconds=5),
    )
    portfolio = AccountCoreCompoundPortfolio(
        account_identity=identity,
        compound_ledger=ledger,
        protected_floor_ledger=floor,
    )

    assert portfolio.admitted_realized_profit_usd == Decimal("100")
    assert portfolio.current_partition_usd == Decimal("100")
    assert portfolio.current_economic_value_usd == Decimal("100")
    assert portfolio.protected_floor_usd == Decimal("20")
    by_trader = dict(
        (row.origin_trader, row.current_economic_value_usd)
        for row in portfolio.attribution
    )
    assert by_trader[TraderLineage.VT31_NAS100] == Decimal("60")
    assert by_trader[TraderLineage.R34_XAUUSD] == Decimal("40")
    assert portfolio.runtime_authority is False
    assert portfolio.cross_account_transfer_authority is False


def test_trader_lab_compound_portfolio_prevents_double_spend(
    candidate_factory,
) -> None:
    candidate = candidate_factory(candidate_suffix=951)
    identity = _identity(candidate)
    lot = _lot(
        candidate,
        trader=TraderLineage.VT31_NAS100,
        suffix="vt31",
        amount="50",
        position_id=95101,
        deal_id=95201,
    )
    ledger = CompoundPortfolioLedger(account_identity=identity)
    ledger = ledger.admit_realized_profit(
        lot,
        event_id=_tag(candidate, "admit"),
        occurred_at=NOW + timedelta(seconds=2),
    )
    ledger = ledger.transition(
        source_lot_id=lot.lot_id,
        to_state=CompoundCapitalState.COMPOUNDABLE,
        amount_usd=Decimal("50"),
        moved_lot_id=_tag(candidate, "compoundable"),
        event_id=_tag(candidate, "to-compoundable"),
        occurred_at=NOW + timedelta(seconds=3),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="active compound lot not found",
    ):
        ledger.transition(
            source_lot_id=lot.lot_id,
            to_state=CompoundCapitalState.COMPOUNDABLE,
            amount_usd=Decimal("1"),
            moved_lot_id=_tag(candidate, "double-spend"),
            event_id=_tag(candidate, "double-spend-event"),
            occurred_at=NOW + timedelta(seconds=4),
        )
