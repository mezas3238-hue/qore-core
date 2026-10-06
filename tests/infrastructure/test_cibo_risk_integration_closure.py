from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    CiboRiskRequest,
    RiskDecision,
    TraderLineage,
)
from qore.infrastructure.account_wide_risk_ledger import (
    DurableAccountWideRiskEngine,
    DurableAccountWideRiskLedger,
)
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_fundednext_seed import (
    build_fundednext_cibo_seed,
)

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)


@dataclass(slots=True)
class _ProviderBudget:
    provider_headroom: Decimal = Decimal("120")
    max_risk_at_any_time: Decimal = Decimal("120")
    active_mll: Decimal = Decimal("1880")
    hard_breach: bool = False


def _snapshot(*, qore_headroom: Decimal = Decimal("60")) -> AccountRiskSnapshot:
    return AccountRiskSnapshot(
        account_binding_id="funded-2k",
        equity=Decimal("2000"),
        margin_used=Decimal("0"),
        free_margin=Decimal("500"),
        open_stop_worst_case_loss=Decimal("0"),
        open_floating_loss=Decimal("0"),
        pending_broker_worst_case_loss=Decimal("0"),
        qore_authorizable_headroom=qore_headroom,
        provider_budget=_ProviderBudget(),
        reconciled_at=NOW,
    )


def _opportunity() -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint="xau-minimal-seed",
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


def _risk(tmp_path: Path, name: str) -> DurableAccountWideRiskEngine:
    return DurableAccountWideRiskEngine(
        DurableAccountWideRiskLedger(tmp_path / name)
    )


def test_fundednext_sixty_dollar_minimal_seed_reaches_risk_allow(
    tmp_path: Path,
) -> None:
    risk = _risk(tmp_path, "minimal-seed-risk.json")
    snapshot = _snapshot()

    seed = build_fundednext_cibo_seed(
        request_id="minimal-seed",
        opportunity=_opportunity(),
        risk=risk,
        snapshot=snapshot,
        assigned_capital_usd=Decimal("2000"),
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("0"),
        requested_at=NOW,
        expires_at=NOW + timedelta(seconds=30),
    )
    authorization = risk.authorize(seed.request, snapshot, now=NOW)

    assert seed.request.strategy_requested_risk_usd is None
    assert seed.plan.volume == Decimal("0.01")
    assert seed.plan.stop_risk_usd == Decimal("8.00")
    assert authorization.decision is RiskDecision.ALLOW
    assert authorization.authorized_volume == Decimal("0.01")
    assert authorization.monetary_stop_loss == Decimal("8.00")


def test_risk_downsizes_large_cibo_request_instead_of_rejecting_all(
    tmp_path: Path,
) -> None:
    risk = _risk(tmp_path, "downsize-risk.json")
    snapshot = _snapshot()
    request = CiboRiskRequest(
        request_id="large-cibo-request",
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint="xau-downsize",
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("2600"),
        stop_loss=Decimal("2590"),
        take_profit=Decimal("2620"),
        requested_volume=Decimal("0.10"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        stop_loss_per_volume=Decimal("800"),
        margin_per_volume=Decimal("100"),
        requested_at=NOW,
        expires_at=NOW + timedelta(seconds=30),
        strategy_requested_risk_usd=None,
    )

    authorization = risk.authorize(request, snapshot, now=NOW)

    assert authorization.decision is RiskDecision.REDUCE
    assert authorization.authorized_volume == Decimal("0.07")
    assert authorization.monetary_stop_loss == Decimal("56.00")
    assert authorization.authorized_volume >= request.minimum_volume
    assert authorization.reason == "request-reduced-to-shared-account-budget"


def test_risk_rejects_only_when_even_provider_minimum_cannot_fit(
    tmp_path: Path,
) -> None:
    risk = _risk(tmp_path, "reject-risk.json")
    snapshot = _snapshot(qore_headroom=Decimal("7"))
    request = CiboRiskRequest(
        request_id="cannot-fit-minimum",
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint="xau-no-fit",
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("2600"),
        stop_loss=Decimal("2590"),
        take_profit=Decimal("2620"),
        requested_volume=Decimal("0.01"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        stop_loss_per_volume=Decimal("800"),
        margin_per_volume=Decimal("100"),
        requested_at=NOW,
        expires_at=NOW + timedelta(seconds=30),
        strategy_requested_risk_usd=None,
    )

    authorization = risk.authorize(request, snapshot, now=NOW)

    assert authorization.decision is RiskDecision.REJECT
    assert authorization.authorized_volume == Decimal("0")
    assert authorization.monetary_stop_loss == Decimal("0")
    assert authorization.reason == "insufficient-shared-risk-or-margin-headroom"
