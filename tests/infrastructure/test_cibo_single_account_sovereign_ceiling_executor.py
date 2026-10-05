from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    RiskDecision,
    TraderLineage,
)
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure import cibo_single_account_sovereign_ceiling_executor as executor

T0 = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)


def _opportunity(
    *,
    trader: TraderLineage,
    signal: str,
    symbol: str,
) -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=trader,
        signal_fingerprint=signal,
        qore_symbol=symbol,
        provider_symbol=symbol,
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("20"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("1"),
        decision_context=(),
    )


@dataclass(frozen=True)
class _Budget:
    provider_headroom: Decimal = Decimal("60")
    max_risk_at_any_time: Decimal = Decimal("60")
    active_mll: Decimal = Decimal("0")
    hard_breach: bool = False


def _snapshot() -> AccountRiskSnapshot:
    return AccountRiskSnapshot(
        account_binding_id="ceiling-account",
        equity=Decimal("60"),
        margin_used=Decimal("0"),
        free_margin=Decimal("60"),
        open_stop_worst_case_loss=Decimal("0"),
        open_floating_loss=Decimal("0"),
        pending_broker_worst_case_loss=Decimal("0"),
        qore_authorizable_headroom=Decimal("60"),
        provider_budget=_Budget(),
        reconciled_at=T0,
    )


class _RiskEngine:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.headrooms: list[Decimal] = []

    def authorize(self, request, snapshot, *, now):
        self.calls.append(request.signal_fingerprint)
        self.headrooms.append(snapshot.qore_authorizable_headroom)
        return SimpleNamespace(
            signal_fingerprint=request.signal_fingerprint,
            request_id=request.request_id,
            decision=RiskDecision.ALLOW,
            authorized_volume=request.requested_volume,
        )


def test_epoch_uses_full_surface_and_risk_priority_not_manifest_order(
    monkeypatch,
) -> None:
    a = _opportunity(
        trader=TraderLineage.R34_XAUUSD,
        signal="signal-a",
        symbol="XAUUSD",
    )
    b = _opportunity(
        trader=TraderLineage.R38_EURUSD,
        signal="signal-b",
        symbol="EURUSD",
    )
    opportunities = (a, b)
    runtime_calls: list[tuple[str, tuple[str, ...], bool]] = []

    utilities = {
        "signal-a": Decimal("1"),
        "signal-b": Decimal("5"),
    }

    def fake_runtime(**kwargs):
        opportunity = kwargs["opportunity"]
        signal = opportunity.signal_fingerprint
        runtime_calls.append(
            (
                signal,
                tuple(
                    item.signal_fingerprint
                    for item in kwargs["simultaneous_opportunities"]
                ),
                not kwargs["world_paths"] and not kwargs["option_schedules"],
            )
        )
        request = SimpleNamespace(
            signal_fingerprint=signal,
            request_id=kwargs["request_id"],
            requested_volume=Decimal("0.10"),
        )
        line = SimpleNamespace(
            option_id=kwargs["option_id"],
            expected_net_utility_usd=utilities[signal],
            expected_capital_minutes=Decimal("1"),
            stop_risk_usd=Decimal("1"),
        )
        return SimpleNamespace(
            capital=SimpleNamespace(
                risk_request=request,
                option_id=kwargs["option_id"],
                economic_run=SimpleNamespace(
                    portfolio_plan=SimpleNamespace(lines=(line,))
                ),
            )
        )

    def fake_receipt(**kwargs):
        return SimpleNamespace(
            signal_fingerprint=kwargs["opportunity"].signal_fingerprint
        )

    monkeypatch.setattr(
        executor,
        "run_cibo_native_sovereign_capital_runtime",
        fake_runtime,
    )
    monkeypatch.setattr(
        executor,
        "decision_receipt_from_native_runtime",
        fake_receipt,
    )
    # Keep the executor focused on orchestration in this test; the canonical
    # Twin/Regime constructors have their own dedicated contract tests.
    monkeypatch.setattr(executor, "CiboObservedEconomicTwin", object)
    monkeypatch.setattr(executor, "CiboCapitalRegimeState", object)

    twin = SimpleNamespace(
        captured_at=T0,
        opportunities=(
            SimpleNamespace(
                option_id="option-a",
                provider_cost_usd=Decimal("0.01"),
            ),
            SimpleNamespace(
                option_id="option-b",
                provider_cost_usd=Decimal("0.01"),
            ),
        ),
    )
    regime = SimpleNamespace(opportunity_count=2)
    risk = _RiskEngine()

    result = executor.execute_sovereign_ceiling_epoch(
        decision_epoch_id="epoch-1",
        decision_at=T0,
        expires_at=T0 + timedelta(minutes=2),
        opportunities=opportunities,
        option_id_by_signal=(
            ("signal-a", "option-a"),
            ("signal-b", "option-b"),
        ),
        twin=twin,
        capital=object(),
        regime_state=regime,
        evidence_ref=object(),
        mission_policy=object(),
        risk_snapshot=_snapshot(),
        risk_engine=risk,
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("0"),
    )

    assert runtime_calls == [
        ("signal-a", ("signal-a", "signal-b"), True),
        ("signal-b", ("signal-a", "signal-b"), True),
    ]
    assert risk.calls == ["signal-b", "signal-a"]
    assert risk.headrooms == [Decimal("59.90"), Decimal("59.80")]
    assert result.provider_cost_reserve_usd == Decimal("0.20")
    assert result.risk_submission_order == ("signal-b", "signal-a")
    assert tuple(
        item.signal_fingerprint for item in result.decision_receipts
    ) == ("signal-a", "signal-b")
    assert result.full_simultaneous_surface_used is True
    assert result.outcome_used_for_predecision is False
    assert result.broker_mutation is False


def test_epoch_does_not_call_risk_for_native_cognitive_or_capital_block(
    monkeypatch,
) -> None:
    opportunity = _opportunity(
        trader=TraderLineage.R34_XAUUSD,
        signal="signal-a",
        symbol="XAUUSD",
    )

    def fake_runtime(**kwargs):
        line = SimpleNamespace(
            option_id=kwargs["option_id"],
            expected_net_utility_usd=Decimal("0"),
            expected_capital_minutes=Decimal("1"),
            stop_risk_usd=Decimal("0"),
        )
        return SimpleNamespace(
            capital=SimpleNamespace(
                risk_request=None,
                option_id=kwargs["option_id"],
                economic_run=SimpleNamespace(
                    portfolio_plan=SimpleNamespace(lines=(line,))
                ),
            )
        )

    def fake_receipt(**kwargs):
        assert kwargs["risk_authorization"] is None
        return SimpleNamespace(
            signal_fingerprint=kwargs["opportunity"].signal_fingerprint
        )

    monkeypatch.setattr(
        executor,
        "run_cibo_native_sovereign_capital_runtime",
        fake_runtime,
    )
    monkeypatch.setattr(
        executor,
        "decision_receipt_from_native_runtime",
        fake_receipt,
    )
    monkeypatch.setattr(executor, "CiboObservedEconomicTwin", object)
    monkeypatch.setattr(executor, "CiboCapitalRegimeState", object)

    twin = SimpleNamespace(
        captured_at=T0,
        opportunities=(
            SimpleNamespace(
                option_id="option-a",
                provider_cost_usd=Decimal("0.01"),
            ),
        ),
    )
    risk = _RiskEngine()

    result = executor.execute_sovereign_ceiling_epoch(
        decision_epoch_id="epoch-1",
        decision_at=T0,
        expires_at=T0 + timedelta(minutes=2),
        opportunities=(opportunity,),
        option_id_by_signal=(("signal-a", "option-a"),),
        twin=twin,
        capital=object(),
        regime_state=SimpleNamespace(opportunity_count=1),
        evidence_ref=object(),
        mission_policy=object(),
        risk_snapshot=object(),
        risk_engine=risk,
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("0"),
    )

    assert risk.calls == []
    assert result.risk_submission_order == ()
    assert result.risk_authorizations == ()
    assert result.provider_cost_reserve_usd == Decimal("0")
