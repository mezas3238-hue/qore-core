from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    AccountWideRiskEngine,
    CiboCapitalProvenanceLot,
    CiboRiskRequest,
    TraderLineage,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_single_account_historical_capital_ledger import (
    initialize_historical_research_capital,
    reserve_historical_authorization,
    settle_historical_deployment,
)
from qore.infrastructure.cibo_single_account_manifest_settlement import (
    CiboManifestOutcomeSettlement,
)
from qore.infrastructure.cibo_single_account_sovereign_ceiling_run import (
    CiboSovereignCeilingSettlementReceipt,
)

T0 = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)


@dataclass(frozen=True)
class _Budget:
    provider_headroom: Decimal = Decimal("200")
    max_risk_at_any_time: Decimal = Decimal("200")
    active_mll: Decimal = Decimal("0")
    hard_breach: bool = False


def _authorization(
    *,
    signal: str,
    source: CapitalSource,
    stop_risk_usd: Decimal = Decimal("10"),
):
    request = CiboRiskRequest(
        request_id="request:" + signal,
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint=signal,
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("90"),
        take_profit=Decimal("120"),
        requested_volume=Decimal("1"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        stop_loss_per_volume=stop_risk_usd,
        margin_per_volume=Decimal("20"),
        requested_at=T0,
        expires_at=T0 + timedelta(minutes=5),
        capital_provenance=(
            CiboCapitalProvenanceLot(
                source_kind=source.value,
                source_id=(
                    "cibo:assigned-original-base"
                    if source is CapitalSource.ORIGINAL_BASE_CAPITAL
                    else "cibo:realized-profit-pool"
                ),
                amount_usd=stop_risk_usd,
            ),
        ),
    )
    snapshot = AccountRiskSnapshot(
        account_binding_id="ceiling-account",
        equity=Decimal("200"),
        margin_used=Decimal("0"),
        free_margin=Decimal("200"),
        open_stop_worst_case_loss=Decimal("0"),
        open_floating_loss=Decimal("0"),
        pending_broker_worst_case_loss=Decimal("0"),
        qore_authorizable_headroom=Decimal("200"),
        provider_budget=_Budget(),
        reconciled_at=T0,
    )
    return AccountWideRiskEngine().authorize(request, snapshot, now=T0)


def _settlement(
    *,
    signal: str,
    gross_r: Decimal,
    provider_cost: Decimal,
    gross_pnl: Decimal,
    net_pnl: Decimal,
    suffix: str,
) -> CiboManifestOutcomeSettlement:
    receipt = CiboSovereignCeilingSettlementReceipt(
        signal_fingerprint=signal,
        trader_id=TraderLineage.R34_XAUUSD.value,
        settled_at=T0 + timedelta(minutes=10),
        realized_net_pnl_usd=net_pnl,
        settlement_sha256="sha256:" + suffix * 64,
        outcome_available_to_predecision=False,
    )
    return CiboManifestOutcomeSettlement(
        signal_fingerprint=signal,
        trader_id=TraderLineage.R34_XAUUSD.value,
        entry_at=T0 + timedelta(minutes=1),
        exit_at=T0 + timedelta(minutes=10),
        gross_structural_outcome_r=gross_r,
        provider_cost_usd=provider_cost,
        gross_pnl_usd=gross_pnl,
        realized_net_pnl_usd=net_pnl,
        receipt=receipt,
    )


def test_base_funded_profit_creates_generation_one_without_fake_broker_ids() -> None:
    state = initialize_historical_research_capital()
    authorization = _authorization(
        signal="base-win",
        source=CapitalSource.ORIGINAL_BASE_CAPITAL,
    )
    state = reserve_historical_authorization(
        state,
        authorization=authorization,
        provider_cost_usd=Decimal("2"),
    )

    assert state.original_base_reserved_usd == Decimal("12")
    assert state.realized_capital_usd == Decimal("60")
    assert state.non_certifying_research is True

    state = settle_historical_deployment(
        state,
        settlement=_settlement(
            signal="base-win",
            gross_r=Decimal("2"),
            provider_cost=Decimal("2"),
            gross_pnl=Decimal("20"),
            net_pnl=Decimal("18"),
            suffix="a",
        ),
    )

    assert state.original_base_economic_value_usd == Decimal("58")
    assert state.realized_profit_economic_value_usd == Decimal("20")
    assert state.realized_capital_usd == Decimal("78")
    assert state.profit_generations[0].generation == 1
    assert state.peak_realized_capital_usd == Decimal("78")
    assert state.open_deployments == ()


def test_profit_funded_trade_advances_compound_generation() -> None:
    state = initialize_historical_research_capital()
    first = _authorization(
        signal="base-win",
        source=CapitalSource.ORIGINAL_BASE_CAPITAL,
    )
    state = reserve_historical_authorization(
        state,
        authorization=first,
        provider_cost_usd=Decimal("2"),
    )
    state = settle_historical_deployment(
        state,
        settlement=_settlement(
            signal="base-win",
            gross_r=Decimal("2"),
            provider_cost=Decimal("2"),
            gross_pnl=Decimal("20"),
            net_pnl=Decimal("18"),
            suffix="b",
        ),
    )

    second = _authorization(
        signal="profit-win",
        source=CapitalSource.REALIZED_PROFIT,
    )
    state = reserve_historical_authorization(
        state,
        authorization=second,
        provider_cost_usd=Decimal("2"),
    )
    deployment = state.open_deployments[0]
    assert deployment.parent_generation == 1

    state = settle_historical_deployment(
        state,
        settlement=_settlement(
            signal="profit-win",
            gross_r=Decimal("1"),
            provider_cost=Decimal("2"),
            gross_pnl=Decimal("10"),
            net_pnl=Decimal("8"),
            suffix="c",
        ),
    )

    generations = {
        item.generation: item.economic_value_usd
        for item in state.profit_generations
    }
    assert generations == {1: Decimal("20"), 2: Decimal("10")}
    assert state.original_base_economic_value_usd == Decimal("56")
    assert state.realized_capital_usd == Decimal("86")


def test_minus_one_r_consumes_stop_and_provider_cost_exactly() -> None:
    state = initialize_historical_research_capital()
    authorization = _authorization(
        signal="base-loss",
        source=CapitalSource.ORIGINAL_BASE_CAPITAL,
    )
    state = reserve_historical_authorization(
        state,
        authorization=authorization,
        provider_cost_usd=Decimal("2"),
    )
    state = settle_historical_deployment(
        state,
        settlement=_settlement(
            signal="base-loss",
            gross_r=Decimal("-1"),
            provider_cost=Decimal("2"),
            gross_pnl=Decimal("-10"),
            net_pnl=Decimal("-12"),
            suffix="d",
        ),
    )

    assert state.original_base_economic_value_usd == Decimal("48")
    assert state.realized_profit_economic_value_usd == Decimal("0")
    assert state.realized_capital_usd == Decimal("48")
    assert state.cumulative_provider_cost_usd == Decimal("2")
    assert state.cumulative_gross_loss_usd == Decimal("10")


def test_long_decimal_settlement_preserves_exact_capital() -> None:
    state = initialize_historical_research_capital()
    authorization = _authorization(
        signal="long-decimal-win",
        source=CapitalSource.ORIGINAL_BASE_CAPITAL,
    )
    provider_cost = Decimal(
        "0.111111111111111111111111111111111111111"
    )
    state = reserve_historical_authorization(
        state,
        authorization=authorization,
        provider_cost_usd=provider_cost,
    )
    state = settle_historical_deployment(
        state,
        settlement=_settlement(
            signal="long-decimal-win",
            gross_r=Decimal(
                "0.3333333333333333333333333333333333333333"
            ),
            provider_cost=provider_cost,
            gross_pnl=Decimal(
                "3.333333333333333333333333333333333333333"
            ),
            net_pnl=Decimal(
                "3.222222222222222222222222222222222222222"
            ),
            suffix="f",
        ),
    )

    assert state.realized_capital_usd == Decimal(
        "63.222222222222222222222222222222222222222"
    )


def test_outcome_below_minus_one_r_fails_without_gap_evidence() -> None:
    state = initialize_historical_research_capital()
    authorization = _authorization(
        signal="gap-loss",
        source=CapitalSource.ORIGINAL_BASE_CAPITAL,
    )
    state = reserve_historical_authorization(
        state,
        authorization=authorization,
        provider_cost_usd=Decimal("2"),
    )

    with pytest.raises(CiboCapitalManagementError):
        settle_historical_deployment(
            state,
            settlement=_settlement(
                signal="gap-loss",
                gross_r=Decimal("-1.1"),
                provider_cost=Decimal("2"),
                gross_pnl=Decimal("-11"),
                net_pnl=Decimal("-13"),
                suffix="e",
            ),
        )
