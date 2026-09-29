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
    CompoundProtectionClass,
    CompoundRealizedProfitEvidence,
    create_realized_profit_lot,
)
from qore.infrastructure.cibo_compound_floor import (
    ProtectedCapitalFloorLedger,
    ProtectedFloorEvent,
    ProtectedFloorEventType,
)
from qore.infrastructure.cibo_compound_portfolio_ledger import (
    CompoundPortfolioLedger,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

T0 = datetime(2026, 9, 29, 16, 45, tzinfo=UTC)


def _identity(
    account_ref: str = "compound-floor-demo",
) -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref=account_ref,
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _retired_lot(
    *,
    identity: CiboAccountCapitalIdentity | None = None,
    amount: str = "80",
):
    account = identity or _identity()
    evidence = CompoundRealizedProfitEvidence(
        evidence_id="floor-settlement",
        account_identity=account,
        origin_trader=TraderLineage.VT31_NAS100,
        signal_fingerprint="floor-signal",
        position_id=111,
        settlement_deal_ids=(211, 212),
        realized_net_profit_usd=Decimal(amount),
        realized_at=T0,
        source_settlement_sha256="sha256:" + "a" * 64,
        settlement_reconciled=True,
        position_closed=True,
    )
    lot = create_realized_profit_lot(
        evidence,
        lot_id="realized-floor-lot",
        created_at=T0 + timedelta(seconds=1),
    )
    portfolio = CompoundPortfolioLedger(
        account_identity=account,
    ).admit_realized_profit(
        lot,
        event_id="admit-floor-profit",
        occurred_at=T0 + timedelta(seconds=2),
    )
    portfolio = portfolio.transition(
        source_lot_id=lot.lot_id,
        to_state=CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR,
        amount_usd=Decimal(amount),
        moved_lot_id="retired-floor-lot",
        event_id="retire-to-floor",
        occurred_at=T0 + timedelta(seconds=3),
    )
    return account, portfolio.lot("retired-floor-lot")


def test_floor_accepts_only_already_retired_account_local_capital() -> None:
    account, retired = _retired_lot()
    floor = ProtectedCapitalFloorLedger(account_identity=account)
    floor = floor.admit_retired_lot(
        retired,
        tranche_id="floor-tranche-1",
        event_id="floor-admit-1",
        admitted_at=T0 + timedelta(seconds=4),
    )

    assert floor.total_floor_usd == Decimal("80")
    assert floor.policy_protected_floor_usd == Decimal("0")
    assert floor.broker_guaranteed_floor_usd == Decimal("0")
    assert (
        floor.tranche("floor-tranche-1").protection_class
        is CompoundProtectionClass.ACCOUNTING_PROTECTED
    )

    other_account, other_retired = _retired_lot(
        identity=_identity("other-account")
    )
    assert other_account != account
    with pytest.raises(
        CiboCompoundCapitalError,
        match="cannot cross account domains",
    ):
        floor.admit_retired_lot(
            other_retired,
            tranche_id="cross-account",
            event_id="cross-account-event",
            admitted_at=T0 + timedelta(seconds=4),
        )


def test_policy_floor_is_not_broker_guarantee() -> None:
    account, retired = _retired_lot()
    floor = ProtectedCapitalFloorLedger(
        account_identity=account
    ).admit_retired_lot(
        retired,
        tranche_id="tranche",
        event_id="admit",
        admitted_at=T0 + timedelta(seconds=4),
    )
    floor = floor.upgrade_to_policy_protected(
        tranche_id="tranche",
        event_id="policy-protect",
        occurred_at=T0 + timedelta(seconds=5),
        policy_id="GEN-C2-SHADOW-POLICY",
        policy_sha256="sha256:" + "b" * 64,
    )

    tranche = floor.tranche("tranche")
    assert (
        tranche.protection_class
        is CompoundProtectionClass.POLICY_PROTECTED
    )
    assert floor.policy_protected_floor_usd == Decimal("80")
    assert floor.broker_guaranteed_floor_usd == Decimal("0")
    assert tranche.broker_guarantee_evidence_id is None

    with pytest.raises(
        CiboCompoundCapitalError,
        match="broker guarantee requires evidence identity",
    ):
        floor.upgrade_to_broker_guaranteed(
            tranche_id="tranche",
            event_id="bad-broker",
            occurred_at=T0 + timedelta(seconds=6),
            broker_guarantee_evidence_id="",
            broker_guarantee_sha256="sha256:" + "c" * 64,
        )


def test_broker_guarantee_requires_prior_policy_protection_and_evidence() -> None:
    account, retired = _retired_lot()
    floor = ProtectedCapitalFloorLedger(
        account_identity=account
    ).admit_retired_lot(
        retired,
        tranche_id="tranche",
        event_id="admit",
        admitted_at=T0 + timedelta(seconds=4),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="requires policy-protected source",
    ):
        floor.upgrade_to_broker_guaranteed(
            tranche_id="tranche",
            event_id="skip-policy",
            occurred_at=T0 + timedelta(seconds=5),
            broker_guarantee_evidence_id="broker-proof",
            broker_guarantee_sha256="sha256:" + "c" * 64,
        )

    floor = floor.upgrade_to_policy_protected(
        tranche_id="tranche",
        event_id="policy",
        occurred_at=T0 + timedelta(seconds=5),
        policy_id="GEN-C2-SHADOW-POLICY",
        policy_sha256="sha256:" + "b" * 64,
    )
    floor = floor.upgrade_to_broker_guaranteed(
        tranche_id="tranche",
        event_id="broker",
        occurred_at=T0 + timedelta(seconds=6),
        broker_guarantee_evidence_id="broker-proof",
        broker_guarantee_sha256="sha256:" + "c" * 64,
    )

    assert floor.total_floor_usd == Decimal("80")
    assert floor.policy_protected_floor_usd == Decimal("80")
    assert floor.broker_guaranteed_floor_usd == Decimal("80")
    assert (
        floor.tranche("tranche").protection_class
        is CompoundProtectionClass.BROKER_GUARANTEED
    )


def test_floor_ratchet_cannot_double_admit_or_ratchet_down() -> None:
    account, retired = _retired_lot()
    floor = ProtectedCapitalFloorLedger(
        account_identity=account
    ).admit_retired_lot(
        retired,
        tranche_id="tranche",
        event_id="admit",
        admitted_at=T0 + timedelta(seconds=4),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="already admitted",
    ):
        floor.admit_retired_lot(
            retired,
            tranche_id="tranche-2",
            event_id="duplicate-source",
            admitted_at=T0 + timedelta(seconds=5),
        )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="cannot ratchet downward",
    ):
        ProtectedFloorEvent(
            event_id="illegal-downward-ratchet",
            event_type=ProtectedFloorEventType.UPGRADE_TO_POLICY_PROTECTED,
            tranche_id="tranche",
            occurred_at=T0 + timedelta(seconds=5),
            floor_before_usd=Decimal("80"),
            floor_after_usd=Decimal("79"),
            from_class=CompoundProtectionClass.ACCOUNTING_PROTECTED,
            to_class=CompoundProtectionClass.POLICY_PROTECTED,
            evidence_ref="sha256:" + "b" * 64,
        )
