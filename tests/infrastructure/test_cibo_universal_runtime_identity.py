from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    AccountWideRiskEngine,
    AccountWideRiskError,
    RiskDecision,
    canonical_trader_identity,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CapitalSource,
    CapitalStage,
    CiboCapitalActionPlan,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_cma_risk_request import build_cma_risk_request


NOW = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)


@dataclass(frozen=True)
class _Budget:
    provider_headroom: Decimal
    max_risk_at_any_time: Decimal
    active_mll: Decimal
    hard_breach: bool


@pytest.mark.parametrize(
    ("trader_id", "symbol"),
    (
        ("SCALPER_BTCUSD_V1", "BTCUSD"),
        ("GENERIC_USDCAD_R1", "USDCAD"),
        ("PORTFOLIO.EURAUD/R2", "EURAUD"),
        ("UNSEEN_ZZZXYZ", "ZZZXYZ"),
    ),
)
def test_unseen_trader_and_symbol_reach_sovereign_qore_risk(
    trader_id: str,
    symbol: str,
) -> None:
    opportunity = TraderOpportunityEnvelope(
        trader_id=trader_id,
        signal_fingerprint=f"universal:{trader_id}:{symbol}",
        qore_symbol=symbol,
        provider_symbol=symbol,
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal("1"),
        margin_per_volume=Decimal("10"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("1"),
    )
    plan = CiboCapitalActionPlan(
        trader_id=(" " + trader_id).strip(),
        qore_symbol=symbol,
        stage=CapitalStage.MINIMAL_SEED,
        action=CapitalAction.OPEN_MINIMAL_SEED,
        volume=Decimal("0.01"),
        stop_risk_usd=Decimal("0.01"),
        margin_usd=Decimal("0.10"),
        capital_source=CapitalSource.ORIGINAL_BASE_CAPITAL,
        capital_source_amount_usd=Decimal("0.01"),
        reason="universal identity contract test",
    )
    request = build_cma_risk_request(
        request_id=f"request:{trader_id}:{symbol}",
        opportunity=opportunity,
        plan=plan,
        requested_at=NOW,
        expires_at=NOW + timedelta(minutes=1),
    )

    assert canonical_trader_identity(request.trader_id) == trader_id
    assert request.qore_symbol == symbol

    snapshot = AccountRiskSnapshot(
        account_binding_id="universal-runtime-test",
        equity=Decimal("100"),
        margin_used=Decimal("0"),
        free_margin=Decimal("100"),
        open_stop_worst_case_loss=Decimal("0"),
        open_floating_loss=Decimal("0"),
        pending_broker_worst_case_loss=Decimal("0"),
        qore_authorizable_headroom=Decimal("100"),
        provider_budget=_Budget(
            provider_headroom=Decimal("100"),
            max_risk_at_any_time=Decimal("100"),
            active_mll=Decimal("0"),
            hard_breach=False,
        ),
        reconciled_at=NOW,
    )
    authorization = AccountWideRiskEngine().authorize(
        request,
        snapshot,
        now=NOW,
    )

    assert authorization.decision is RiskDecision.ALLOW
    assert canonical_trader_identity(authorization.trader_id) == trader_id
    assert authorization.qore_symbol == symbol


@pytest.mark.parametrize(
    "trader_id",
    ("lowercase_trader", "BAD SPACE", "", "ÁRBITRO"),
)
def test_universal_trader_identity_still_fails_closed_on_noncanonical_input(
    trader_id: str,
) -> None:
    with pytest.raises(AccountWideRiskError):
        canonical_trader_identity(trader_id)
