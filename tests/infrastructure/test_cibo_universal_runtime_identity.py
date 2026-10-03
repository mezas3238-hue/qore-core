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
    TraderLineage,
    canonical_trader_identity,
    canonical_trader_lineage,
)
from qore.infrastructure.cibo_account_capital_mission import CiboAccountCapitalIdentity
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CapitalSource,
    CapitalStage,
    CiboCapitalActionPlan,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_cma_risk_request import build_cma_risk_request
from qore.infrastructure.cibo_compound_capital import (
    CompoundRealizedProfitEvidence,
    create_realized_profit_lot,
)
from qore.infrastructure.cibo_compound_path_monte_carlo import CompoundMonteCarloEpisode
from qore.infrastructure.cibo_meta_capital_memory import Genc13CapitalEpisode
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment


NOW = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)


@dataclass(frozen=True)
class _Budget:
    provider_headroom: Decimal
    max_risk_at_any_time: Decimal
    active_mll: Decimal
    hard_breach: bool


def test_unseen_trader_lineage_is_stable_enum_compatible_identity() -> None:
    trader_id = "UNSEEN_STABLE_TRADER_V42"
    first = canonical_trader_lineage(trader_id)
    second = TraderLineage(trader_id)

    assert type(first) is TraderLineage
    assert first is second
    assert first.value == trader_id
    assert canonical_trader_identity(first) == trader_id


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


def _account() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="universal-test",
        account_ref="universal-runtime",
        environment=MarketRuntimeEnvironment.TEST,
    )


def test_unseen_trader_identity_survives_compound_monte_carlo_and_genc13() -> None:
    trader_id = "UNSEEN_CRYPTO_SCALPER_V9"
    settlement_sha = "sha256:" + "a" * 64
    evidence = CompoundRealizedProfitEvidence(
        evidence_id="unseen-profit-evidence",
        account_identity=_account(),
        origin_trader=trader_id,
        signal_fingerprint="unseen-signal",
        position_id=1001,
        settlement_deal_ids=(2001,),
        realized_net_profit_usd=Decimal("2.50"),
        realized_at=NOW,
        source_settlement_sha256=settlement_sha,
        settlement_reconciled=True,
        position_closed=True,
        floating_pnl_used_as_capital=False,
    )
    lot = create_realized_profit_lot(
        evidence,
        lot_id="unseen-profit-lot",
        created_at=NOW + timedelta(seconds=1),
    )
    assert canonical_trader_identity(lot.origin_trader) == trader_id

    episode = CompoundMonteCarloEpisode(
        episode_id="unseen-mc-episode",
        deployment_id="unseen-deployment",
        market_event_id="unseen-market-event",
        decision_id="unseen-decision",
        candidate_id="unseen-candidate",
        trader_id=trader_id,
        signal_fingerprint="unseen-signal",
        deployed_at=NOW,
        settled_at=NOW + timedelta(minutes=10),
        source_generation=1,
        deployed_capital_usd=Decimal("1"),
        stop_risk_usd=Decimal("0.25"),
        margin_usd=Decimal("0.50"),
        realized_pnl_usd=Decimal("0.20"),
        protected_floor_graduation_usd=Decimal("0"),
        floor_evidence_sha256=None,
        market_record_present=True,
        terminal_release_present=True,
        future_leakage_used=False,
    )
    assert canonical_trader_identity(episode.trader_id) == trader_id

    memory = Genc13CapitalEpisode(
        episode_id="unseen-memory-episode",
        account_identity=_account(),
        trader_id=trader_id,
        decision_id="unseen-decision",
        decision_sha256="sha256:" + "b" * 64,
        decision_at=NOW,
        outcome_at=NOW + timedelta(minutes=10),
        outcome_sha256="sha256:" + "c" * 64,
        capital_state_before_sha256="sha256:" + "d" * 64,
        capital_state_after_sha256="sha256:" + "e" * 64,
        action_code="COMPOUND",
        allocated_capital_usd=Decimal("1"),
        peak_plausible_loss_usd=Decimal("0.25"),
        capital_minutes=Decimal("10"),
        realized_pnl_usd=Decimal("0.20"),
    )
    assert canonical_trader_identity(memory.trader_id) == trader_id
    assert memory.fingerprint().startswith("sha256:")
