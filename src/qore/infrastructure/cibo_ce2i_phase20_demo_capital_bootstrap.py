"""Durable assigned-capital bootstrap for cTrader DEMO Phase20D forward work.

The bootstrap does not claim to reconstruct the broker account's historical
initial deposit.  It freezes the broker-reported cash balance observed when the
forward qualification experiment is first activated and treats that amount as
the experiment's assigned base capital.  Dynamic deployable capacity remains
owned by contemporaneous QORE Risk constraints.

Research-only: no reservation, sizing, Risk authorization or broker mutation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_capital_source_ledger_store import (
    DurableCapitalSourceLedgerStore,
    VersionedCapitalSourceLedger,
)
from qore.infrastructure.ctrader_demo_compat import CTraderDemoAccountState
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
    MarketTestAccountIdentity,
)

_SOURCE_PREFIX = "phase20d-demo-assigned-base:"


@dataclass(frozen=True, slots=True)
class Phase20DemoAssignedCapitalBootstrap:
    account_ref: str
    activated_at: datetime
    assigned_base_usd: Decimal
    source_id: str

    def __post_init__(self) -> None:
        if not self.account_ref or not self.source_id.startswith(_SOURCE_PREFIX):
            raise CiboCapitalManagementError(
                "Phase20D DEMO assigned-capital identity is invalid"
            )
        _aware(self.activated_at, name="activated_at")
        if (
            not isinstance(self.assigned_base_usd, Decimal)
            or not self.assigned_base_usd.is_finite()
            or self.assigned_base_usd <= 0
        ):
            raise CiboCapitalManagementError(
                "Phase20D DEMO assigned base must be finite positive Decimal"
            )


def bootstrap_phase20_demo_assigned_capital(
    *,
    store: DurableCapitalSourceLedgerStore,
    account: MarketTestAccountIdentity,
    account_state: CTraderDemoAccountState,
    activated_at: datetime,
) -> tuple[Phase20DemoAssignedCapitalBootstrap, VersionedCapitalSourceLedger]:
    """Freeze the forward experiment base exactly once and return durable state."""

    if not isinstance(store, DurableCapitalSourceLedgerStore):
        raise CiboCapitalManagementError(
            "Phase20D DEMO capital bootstrap requires durable ledger store"
        )
    if not isinstance(account, MarketTestAccountIdentity):
        raise CiboCapitalManagementError(
            "Phase20D DEMO capital bootstrap requires account identity"
        )
    if (
        account.provider_key != "ctrader-demo"
        or account.environment is not MarketRuntimeEnvironment.DEMO
    ):
        raise CiboCapitalManagementError(
            "Phase20D assigned-capital bootstrap is cTrader DEMO-only"
        )
    if not isinstance(account_state, CTraderDemoAccountState):
        raise CiboCapitalManagementError(
            "Phase20D DEMO capital bootstrap requires canonical account state"
        )
    _aware(activated_at, name="activated_at")
    if account_state.observed_at > activated_at:
        raise CiboCapitalManagementError(
            "Phase20D DEMO assigned base cannot use future account state"
        )
    if account_state.balance <= 0:
        raise CiboCapitalManagementError(
            "Phase20D DEMO assigned base requires positive broker cash balance"
        )

    current = store.load()
    if current.generation == 0 and not current.ledger.accounts:
        source_id = _assigned_base_source_id(
            account=account,
            account_state=account_state,
            activated_at=activated_at,
        )
        ledger = CapitalSourceLedger().add_source(
            source_id=source_id,
            source=CapitalSource.ORIGINAL_BASE_CAPITAL,
            proven_amount_usd=account_state.balance,
        )
        current = store.store(
            ledger,
            expected_generation=0,
        )

    if len(current.ledger.accounts) != 1:
        raise CiboCapitalManagementError(
            "Phase20D DEMO assigned-capital ledger must contain one frozen base source"
        )
    source = current.ledger.accounts[0]
    if (
        source.source is not CapitalSource.ORIGINAL_BASE_CAPITAL
        or not source.source_id.startswith(_SOURCE_PREFIX)
    ):
        raise CiboCapitalManagementError(
            "Phase20D DEMO assigned-capital ledger lineage drift"
        )
    if current.ledger.reservations:
        raise CiboCapitalManagementError(
            "Phase20D observational assigned-capital ledger cannot carry reservations"
        )
    bootstrap = _bootstrap_from_source_id(
        account_ref=account.account_ref,
        source_id=source.source_id,
        assigned_base_usd=source.proven_amount_usd,
    )
    return bootstrap, current


def _assigned_base_source_id(
    *,
    account: MarketTestAccountIdentity,
    account_state: CTraderDemoAccountState,
    activated_at: datetime,
) -> str:
    payload = {
        "schema": "CIBO_PHASE20D_DEMO_ASSIGNED_BASE_V1",
        "provider_key": account.provider_key,
        "account_ref": account.account_ref,
        "environment": account.environment.value,
        "activated_at": activated_at.isoformat(),
        "broker_balance_usd": format(account_state.balance, "f"),
        "account_observed_at": account_state.observed_at.isoformat(),
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return (
        f"{_SOURCE_PREFIX}"
        f"{activated_at.isoformat()}:{sha256(raw).hexdigest()}"
    )


def _bootstrap_from_source_id(
    *,
    account_ref: str,
    source_id: str,
    assigned_base_usd: Decimal,
) -> Phase20DemoAssignedCapitalBootstrap:
    if not source_id.startswith(_SOURCE_PREFIX):
        raise CiboCapitalManagementError(
            "Phase20D DEMO assigned-capital source prefix invalid"
        )
    remainder = source_id[len(_SOURCE_PREFIX) :]
    try:
        activated_raw, digest = remainder.rsplit(":", 1)
        activated_at = datetime.fromisoformat(activated_raw)
    except ValueError as error:
        raise CiboCapitalManagementError(
            "Phase20D DEMO assigned-capital source identity invalid"
        ) from error
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise CiboCapitalManagementError(
            "Phase20D DEMO assigned-capital source digest invalid"
        )
    return Phase20DemoAssignedCapitalBootstrap(
        account_ref=account_ref,
        activated_at=activated_at,
        assigned_base_usd=assigned_base_usd,
        source_id=source_id,
    )


def _aware(value: datetime, *, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"Phase20D DEMO {name} must be timezone-aware"
        )
