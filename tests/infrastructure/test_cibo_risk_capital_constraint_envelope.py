# ruff: noqa: I001
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    AccountWideRiskEngine,
    AccountWideRiskError,
    CiboRiskRequest,
    RiskDecision,
    TraderLineage,
)
from qore.infrastructure.account_wide_risk_ledger import (
    DurableAccountWideRiskEngine,
    DurableAccountWideRiskLedger,
)


NOW = datetime(2026, 9, 26, 14, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class _ProviderBudget:
    provider_headroom: Decimal = Decimal("120")
    max_risk_at_any_time: Decimal = Decimal("120")
    active_mll: Decimal = Decimal("1880")
    hard_breach: bool = False


def _snapshot(
    *,
    qore_headroom: str = "60",
    free_margin: str = "500",
    open_risk: str = "0",
    pending_risk: str = "0",
    equity: str = "2000",
    provider: _ProviderBudget | None = None,
) -> AccountRiskSnapshot:
    return AccountRiskSnapshot(
        account_binding_id="funded-account-2k",
        equity=Decimal(equity),
        margin_used=Decimal("0"),
        free_margin=Decimal(free_margin),
        open_stop_worst_case_loss=Decimal(open_risk),
        open_floating_loss=Decimal("0"),
        pending_broker_worst_case_loss=Decimal(pending_risk),
        qore_authorizable_headroom=Decimal(qore_headroom),
        provider_budget=provider or _ProviderBudget(),
        reconciled_at=NOW,
    )


def _request(
    signal: str,
    *,
    volume: str = "1",
    stop_per_volume: str = "20",
    margin_per_volume: str = "50",
) -> CiboRiskRequest:
    return CiboRiskRequest(
        request_id=f"request-{signal}",
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint=signal,
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("2600"),
        stop_loss=Decimal("2590"),
        take_profit=Decimal("2620"),
        requested_volume=Decimal(volume),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        stop_loss_per_volume=Decimal(stop_per_volume),
        margin_per_volume=Decimal(margin_per_volume),
        requested_at=NOW,
        expires_at=NOW + timedelta(minutes=2),
        strategy_requested_risk_usd=None,
    )


def test_constraint_envelope_discounts_external_and_reserved_risk() -> None:
    engine = AccountWideRiskEngine()
    snapshot = _snapshot(
        qore_headroom="60",
        open_risk="10",
        pending_risk="5",
    )
    before = engine.capital_constraint_envelope(snapshot, now=NOW)

    assert before.aggregate_pre_order_worst_case_usd == Decimal("15")
    assert before.hard_risk_headroom_usd == Decimal("45")
    assert before.margin_headroom_usd == Decimal("500")

    authorization = engine.authorize(
        _request("first"),
        snapshot,
        now=NOW,
    )
    assert authorization.decision is RiskDecision.ALLOW

    after = engine.capital_constraint_envelope(snapshot, now=NOW)
    assert after.active_reserved_stop_risk_usd == Decimal("20")
    assert after.active_reserved_margin_usd == Decimal("50")
    assert after.aggregate_pre_order_worst_case_usd == Decimal("35")
    assert after.hard_risk_headroom_usd == Decimal("25")
    assert after.margin_headroom_usd == Decimal("450")


def test_constraint_envelope_matches_authorization_capacity() -> None:
    engine = AccountWideRiskEngine()
    snapshot = _snapshot(qore_headroom="60")
    engine.authorize(_request("first"), snapshot, now=NOW)

    constraints = engine.capital_constraint_envelope(snapshot, now=NOW)
    assert constraints.hard_risk_headroom_usd == Decimal("40")

    exact = engine.authorize(
        _request("second", volume="2"),
        snapshot,
        now=NOW,
    )
    assert exact.decision is RiskDecision.ALLOW
    assert exact.monetary_stop_loss == constraints.hard_risk_headroom_usd


def test_provider_breach_and_mll_block_all_new_cibo_headroom() -> None:
    breached = AccountWideRiskEngine().capital_constraint_envelope(
        _snapshot(
            provider=_ProviderBudget(hard_breach=True),
        ),
        now=NOW,
    )
    assert breached.survival_blocked is True
    assert breached.hard_risk_headroom_usd == 0
    assert breached.margin_headroom_usd == 0
    assert breached.reason == "provider-hard-breach"

    at_mll = AccountWideRiskEngine().capital_constraint_envelope(
        _snapshot(equity="1880"),
        now=NOW,
    )
    assert at_mll.survival_blocked is True
    assert at_mll.hard_risk_headroom_usd == 0
    assert at_mll.margin_headroom_usd == 0
    assert at_mll.reason == "no-provider-equity-headroom"


def test_expired_reservation_is_removed_before_envelope_is_exposed() -> None:
    engine = AccountWideRiskEngine()
    snapshot = _snapshot(qore_headroom="60")
    engine.authorize(_request("first"), snapshot, now=NOW)

    later = NOW + timedelta(minutes=3)
    refreshed = AccountRiskSnapshot(
        account_binding_id=snapshot.account_binding_id,
        equity=snapshot.equity,
        margin_used=snapshot.margin_used,
        free_margin=snapshot.free_margin,
        open_stop_worst_case_loss=snapshot.open_stop_worst_case_loss,
        open_floating_loss=snapshot.open_floating_loss,
        pending_broker_worst_case_loss=snapshot.pending_broker_worst_case_loss,
        qore_authorizable_headroom=snapshot.qore_authorizable_headroom,
        provider_budget=snapshot.provider_budget,
        reconciled_at=later,
    )
    constraints = engine.capital_constraint_envelope(refreshed, now=later)

    assert constraints.active_reserved_stop_risk_usd == 0
    assert constraints.active_reserved_margin_usd == 0
    assert constraints.hard_risk_headroom_usd == Decimal("60")


def test_durable_risk_never_exposes_headroom_before_restart_reconciliation(
    tmp_path: Path,
) -> None:
    path = tmp_path / "risk.json"
    first = DurableAccountWideRiskEngine(
        DurableAccountWideRiskLedger(path)
    )
    first.authorize(_request("first"), _snapshot(), now=NOW)

    restarted = DurableAccountWideRiskEngine(
        DurableAccountWideRiskLedger(path)
    )
    assert restarted.recovery_required is True
    with pytest.raises(
        AccountWideRiskError,
        match="restart-reconciliation-required-before-capital-envelope",
    ):
        restarted.capital_constraint_envelope(_snapshot(), now=NOW)

    restarted.complete_boot_reconciliation(_snapshot(), now=NOW)
    constraints = restarted.capital_constraint_envelope(
        _snapshot(),
        now=NOW,
    )
    assert constraints.hard_risk_headroom_usd == Decimal("40")
    assert constraints.margin_headroom_usd == Decimal("450")
