from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    CiboCapitalProvenanceLot,
    CiboRiskRequest,
    RiskDecision,
)
from qore.infrastructure.cibo_capital_management_authority import CapitalSource
from qore.infrastructure.cibo_single_account_historical_ceiling_epoch import (
    CiboHistoricalProviderAssumption,
)
from qore.infrastructure.cibo_single_account_historical_ceiling_replay import (
    _causal_regime,
    run_historical_ceiling_replay,
)
from qore.infrastructure.cibo_single_account_manifest_integrity import (
    reseal_single_account_manifest,
)
from qore.infrastructure.cibo_single_account_sovereign_ceiling_run import (
    CiboSovereignCeilingDecisionReceipt,
)

T0 = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)


@dataclass(frozen=True)
class _Budget:
    provider_headroom: Decimal = Decimal("1000")
    max_risk_at_any_time: Decimal = Decimal("1000")
    active_mll: Decimal = Decimal("0")
    hard_breach: bool = False


def _row(
    *,
    epoch: str,
    signal: str,
    decision_at: datetime,
    exit_at: datetime,
    gross_r: str,
) -> dict[str, object]:
    return {
        "decision_epoch_id": epoch,
        "market_decision_at": decision_at.isoformat(),
        "trader_id": "R34_XAUUSD",
        "qore_symbol": "XAUUSD",
        "signal_fingerprint": signal,
        "decision_evidence_sha256": "sha256:" + "d" * 64,
        "trader_opportunity": {
            "provider_symbol": "XAUUSD",
            "side": "long",
            "entry_type": "market",
            "intended_entry": "100",
            "stop_loss": "90",
            "take_profit": "120",
            "stop_loss_per_volume": "10",
            "margin_per_volume": "20",
            "volume_step": "1",
            "minimum_volume": "1",
            "maximum_volume": "10",
            "minimum_execution_steps": 1,
            "decision_context": [["cibo_native_perception_complete", "true"]],
        },
        "market_predecision_state": {
            "provider_observation": {
                "ask": "100",
                "bid": "100",
                "tick_size": "1",
                "tick_value": "1",
                "commission_per_volume_usd": "0",
                "slippage_reserve_per_volume_usd": "0",
            }
        },
        "expectation": {
            "evidence_id": "frozen:" + signal,
            "as_of": decision_at.isoformat(),
            "basis": "FROZEN_HISTORICAL_PRIOR",
            "expected_net_value_usd": "5",
            "expected_capital_minutes": "30",
            "future_market_used": False,
            "outcome_used": False,
            "pnl_used": False,
            "post_entry_path_used": False,
            "sizing_authority": False,
            "risk_authority": False,
            "order_authority": False,
            "execution_authority": False,
        },
        "context_quality": {
            "disposition": "ALLOW",
            "causal_predecision": True,
            "identity_predicate_used": False,
            "outcome_used": False,
            "sizing_authority": False,
            "risk_authority": False,
            "execution_authority": False,
            "broker_mutation": False,
            "certification_claimed": False,
        },
        "ce2i_predecision_evidence": {
            "runtime_receipts": [
                {
                    "engine_name": "select_ce2i_tools_for_regime",
                    "input_payload": {
                        "liquidity": "NORMAL",
                        "volatility": "NORMAL",
                        "correlation": "NORMAL",
                        "provider_condition": "HEALTHY",
                        "risk_utilization": "0",
                        "margin_utilization": "0",
                        "drawdown_utilization": "0",
                        "opportunity_count": 1,
                        "position_path_adverse": False,
                        "evidence_stale": False,
                    },
                }
            ]
        },
        "settlement_outcome_research_only": {
            "entry_at": (decision_at + timedelta(seconds=1)).isoformat(),
            "exit_at": exit_at.isoformat(),
            "gross_structural_outcome_r": gross_r,
            "exit_reason": "RESEARCH",
            "not_available_to_predecision": True,
            "used_for_decision": False,
        },
        "outcome_available_to_predecision": False,
    }


def _manifest(rows: list[dict[str, object]], epochs: int) -> dict[str, object]:
    return reseal_single_account_manifest(
        {
            "schema": "qore.cibo.single-account-7trader-maximum-capability.v1",
            "initial_capital_usd": "60",
            "account_count": 1,
            "account_reset_count": 0,
            "economic_era_reset_count": 0,
            "continuous_realized_profit_compound": True,
            "shared_portfolio_state": True,
            "shared_qore_risk_state": True,
            "sovereign_cibo_required": True,
            "full_cognitive_semantics_required": True,
            "target_capital_used_for_tuning": False,
            "opportunity_decision_count": len(rows),
            "decision_epoch_count": epochs,
            "opportunities": rows,
        }
    )


def test_regime_reconstruction_uses_actual_simultaneous_surface() -> None:
    rows = (
        _row(
            epoch="epoch-1",
            signal="alpha",
            decision_at=T0,
            exit_at=T0 + timedelta(minutes=5),
            gross_r="1",
        ),
        _row(
            epoch="epoch-1",
            signal="beta",
            decision_at=T0,
            exit_at=T0 + timedelta(minutes=5),
            gross_r="1",
        ),
    )
    from qore.infrastructure.cibo_single_account_historical_capital_ledger import (
        initialize_historical_research_capital,
    )

    regime = _causal_regime(
        rows=rows,
        capital=initialize_historical_research_capital(),
        provider_assumption=CiboHistoricalProviderAssumption(),
    )

    # Archived receipts declared one opportunity per row.  The replay must use
    # the actual simultaneous surface instead of preserving that stale count.
    assert regime.opportunity_count == 2
    assert regime.risk_utilization == Decimal("0")
    assert regime.margin_utilization == Decimal("0")


def test_replay_settles_due_outcome_before_next_epoch(monkeypatch) -> None:
    first = _row(
        epoch="epoch-1",
        signal="alpha",
        decision_at=T0,
        exit_at=T0 + timedelta(minutes=5),
        gross_r="1",
    )
    second_time = T0 + timedelta(minutes=10)
    second = _row(
        epoch="epoch-2",
        signal="beta",
        decision_at=second_time,
        exit_at=second_time + timedelta(minutes=5),
        gross_r="-1",
    )
    observed_capital: list[Decimal] = []

    def _fake_epoch(**kwargs):
        observed_capital.append(kwargs["historical_capital"].realized_capital_usd)
        opportunity = kwargs["opportunities"][0].opportunity
        signal = opportunity.signal_fingerprint
        request = CiboRiskRequest(
            request_id=kwargs["decision_epoch_id"] + ":risk",
            trader_id=opportunity.trader_id,
            signal_fingerprint=signal,
            qore_symbol=opportunity.qore_symbol,
            provider_symbol=opportunity.provider_symbol,
            side=opportunity.side,
            entry_type=opportunity.entry_type,
            intended_entry=opportunity.intended_entry,
            stop_loss=opportunity.stop_loss,
            take_profit=opportunity.take_profit,
            requested_volume=Decimal("1"),
            volume_step=Decimal("1"),
            minimum_volume=Decimal("1"),
            stop_loss_per_volume=Decimal("10"),
            margin_per_volume=Decimal("20"),
            requested_at=kwargs["decision_at"],
            expires_at=kwargs["expires_at"],
            capital_provenance=(
                CiboCapitalProvenanceLot(
                    source_kind=CapitalSource.ORIGINAL_BASE_CAPITAL.value,
                    source_id="cibo:assigned-original-base",
                    amount_usd=Decimal("10"),
                ),
            ),
        )
        snapshot = AccountRiskSnapshot(
            account_binding_id=kwargs["account_identity"].account_ref,
            equity=kwargs["historical_capital"].realized_capital_usd,
            margin_used=Decimal("0"),
            free_margin=Decimal("1000"),
            open_stop_worst_case_loss=Decimal("0"),
            open_floating_loss=Decimal("0"),
            pending_broker_worst_case_loss=Decimal("0"),
            qore_authorizable_headroom=Decimal("1000"),
            provider_budget=_Budget(),
            reconciled_at=kwargs["decision_at"],
        )
        authorization = kwargs["risk_engine"].authorize(
            request,
            snapshot,
            now=kwargs["decision_at"],
        )
        assert authorization.decision is RiskDecision.ALLOW
        receipt = CiboSovereignCeilingDecisionReceipt(
            decision_epoch_id=kwargs["decision_epoch_id"],
            decision_id=kwargs["decision_epoch_id"] + ":" + signal,
            option_id="ceiling:" + signal,
            signal_fingerprint=signal,
            trader_id=opportunity.trader_id.value,
            decided_at=kwargs["decision_at"],
            capital_disposition="RISK_REVIEW_READY",
            risk_decision=RiskDecision.ALLOW.value,
            requested_volume=Decimal("1"),
            authorized_volume=Decimal("1"),
            requested_stop_risk_usd=Decimal("10"),
            authorized_stop_risk_usd=Decimal("10"),
            authorized_margin_usd=Decimal("20"),
            adaptive_leverage_multiplier=1,
            sizing_mode="CAPABILITY_MAXIMUM",
            semantic_digest="sha256:" + "a" * 64,
            native_mpc_derived_from_cognition=True,
        )
        execution = SimpleNamespace(
            decision_receipts=(receipt,),
            risk_submission_order=(signal,),
            risk_authorizations=(authorization,),
        )
        return SimpleNamespace(execution=execution)

    monkeypatch.setattr(
        "qore.infrastructure.cibo_single_account_historical_ceiling_replay."
        "run_predecision_historical_sovereign_ceiling_epoch",
        _fake_epoch,
    )

    result = run_historical_ceiling_replay(
        _manifest([first, second], epochs=2)
    )

    assert observed_capital == [Decimal("60"), Decimal("70")]
    assert result.ending_capital_usd == Decimal("60")
    assert result.peak_capital_usd == Decimal("70")
    assert result.net_pnl_usd == Decimal("0")
    assert len(result.decision_receipts) == 2
    assert len(result.settlement_receipts) == 2
    assert result.final_open_exposures == ()
    assert result.final_capital.open_deployments == ()
    assert result.regime_reconstruction_count == 2
    assert result.external_ai_call_count == 0
    assert result.outcome_used_for_predecision is False
