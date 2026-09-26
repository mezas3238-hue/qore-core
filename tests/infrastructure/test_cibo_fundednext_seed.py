# ruff: noqa: I001
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    TraderLineage,
)
from qore.infrastructure.account_wide_risk_ledger import (
    DurableAccountWideRiskEngine,
    DurableAccountWideRiskLedger,
)
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_fundednext_seed import build_fundednext_cibo_seed


NOW = datetime(2026, 9, 26, 14, 0, tzinfo=UTC)


@dataclass(slots=True)
class _ProviderBudget:
    provider_headroom: Decimal = Decimal("120")
    max_risk_at_any_time: Decimal = Decimal("120")
    active_mll: Decimal = Decimal("1880")
    hard_breach: bool = False


def _snapshot() -> AccountRiskSnapshot:
    return AccountRiskSnapshot(
        account_binding_id="funded-2k",
        equity=Decimal("2000"),
        margin_used=Decimal("0"),
        free_margin=Decimal("500"),
        open_stop_worst_case_loss=Decimal("0"),
        open_floating_loss=Decimal("0"),
        pending_broker_worst_case_loss=Decimal("0"),
        qore_authorizable_headroom=Decimal("60"),
        provider_budget=_ProviderBudget(),
        reconciled_at=NOW,
    )


def _opportunity() -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint="signal-1",
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("2600"),
        stop_loss=Decimal("2590"),
        take_profit=Decimal("2620"),
        stop_loss_per_volume=Decimal("800"),
        margin_per_volume=Decimal("100"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("100"),
    )


def test_fundednext_seed_uses_minimum_volume_inside_sixty_dollar_headroom(
    tmp_path: Path,
) -> None:
    risk = DurableAccountWideRiskEngine(
        DurableAccountWideRiskLedger(tmp_path / "risk.json")
    )

    seed = build_fundednext_cibo_seed(
        request_id="seed-1",
        opportunity=_opportunity(),
        risk=risk,
        snapshot=_snapshot(),
        assigned_capital_usd=Decimal("2000"),
        requested_at=NOW,
        expires_at=NOW + timedelta(seconds=30),
    )

    assert seed.plan.volume == Decimal("0.01")
    assert seed.plan.stop_risk_usd == Decimal("8.00")
    assert seed.request.strategy_requested_risk_usd is None
