from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    CiboCapitalProvenanceLot,
    CiboRiskRequest,
    RiskDecision,
    TraderLineage,
)
from qore.infrastructure.account_wide_risk_ledger import (
    DurableAccountWideRiskEngine,
    DurableAccountWideRiskLedger,
)
from qore.infrastructure.cibo_ce2i_phase20_demo_risk_bridge import (
    authorize_phase20_demo_request,
)
from qore.infrastructure.cibo_ce2i_phase20_demo_shadow_risk import (
    CiboDemoCapabilitySolvencyBudget,
)

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _snapshot(
    *,
    equity: str = "100",
    free_margin: str = "100",
    open_risk: str = "0",
) -> AccountRiskSnapshot:
    value = Decimal(equity)
    return AccountRiskSnapshot(
        account_binding_id="ctrader-demo-risk-bridge",
        equity=value,
        margin_used=Decimal("0"),
        free_margin=Decimal(free_margin),
        open_stop_worst_case_loss=Decimal(open_risk),
        open_floating_loss=Decimal("0"),
        pending_broker_worst_case_loss=Decimal("0"),
        qore_authorizable_headroom=value,
        provider_budget=CiboDemoCapabilitySolvencyBudget(
            provider_headroom=value,
            max_risk_at_any_time=value,
            active_mll=Decimal("0"),
            hard_breach=False,
        ),
        reconciled_at=NOW,
    )


def _request(
    *,
    volume: str,
    stop_risk_per_volume: str = "5",
    margin_per_volume: str = "10",
) -> CiboRiskRequest:
    requested_volume = Decimal(volume)
    stop_per_volume = Decimal(stop_risk_per_volume)
    total = requested_volume * stop_per_volume
    return CiboRiskRequest(
        request_id="phase20-demo-risk-bridge",
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint="phase20-demo-risk-bridge-signal",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("1.10"),
        stop_loss=Decimal("1.09"),
        take_profit=Decimal("1.12"),
        requested_volume=requested_volume,
        volume_step=Decimal("1"),
        minimum_volume=Decimal("1"),
        stop_loss_per_volume=stop_per_volume,
        margin_per_volume=Decimal(margin_per_volume),
        requested_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        capital_provenance=(
            CiboCapitalProvenanceLot(
                source_kind="ORIGINAL_BASE_CAPITAL",
                source_id="demo-base",
                amount_usd=total,
            ),
        ),
    )


def _risk(tmp_path) -> DurableAccountWideRiskEngine:
    return DurableAccountWideRiskEngine(
        DurableAccountWideRiskLedger(tmp_path / "risk.json")
    )


def test_allow_preserves_cibo_requested_volume(tmp_path) -> None:
    report = authorize_phase20_demo_request(
        risk=_risk(tmp_path),
        request=_request(volume="5"),
        snapshot=_snapshot(),
        observed_at=NOW,
    )

    assert report.authorization.decision is RiskDecision.ALLOW
    assert report.execution_request is not None
    assert report.execution_request.requested_volume == Decimal("5")
    assert (
        report.execution_request.requested_stop_risk
        == report.authorization.monetary_stop_loss
    )


def test_reduce_scales_volume_and_capital_provenance(tmp_path) -> None:
    report = authorize_phase20_demo_request(
        risk=_risk(tmp_path),
        request=_request(
            volume="10",
            stop_risk_per_volume="5",
            margin_per_volume="20",
        ),
        snapshot=_snapshot(free_margin="100"),
        observed_at=NOW,
    )

    assert report.authorization.decision is RiskDecision.REDUCE
    assert report.authorization.authorized_volume == Decimal("5")
    assert report.execution_request is not None
    assert report.execution_request.requested_volume == Decimal("5")
    assert report.execution_request.requested_margin == Decimal("100")
    assert report.execution_request.requested_stop_risk == Decimal("25")
    assert sum(
        item.amount_usd
        for item in report.execution_request.capital_provenance
    ) == Decimal("25")


def test_reject_emits_no_execution_request(tmp_path) -> None:
    report = authorize_phase20_demo_request(
        risk=_risk(tmp_path),
        request=_request(volume="2"),
        snapshot=_snapshot(
            equity="2",
            free_margin="1",
        ),
        observed_at=NOW,
    )

    assert report.authorization.decision is RiskDecision.REJECT
    assert report.execution_request is None


def test_restart_reconciliation_occurs_before_new_authorization(tmp_path) -> None:
    path = tmp_path / "risk.json"
    first = DurableAccountWideRiskEngine(
        DurableAccountWideRiskLedger(path)
    )
    first_report = authorize_phase20_demo_request(
        risk=first,
        request=_request(volume="2"),
        snapshot=_snapshot(),
        observed_at=NOW,
    )
    assert first_report.authorization.decision is RiskDecision.ALLOW

    restarted = DurableAccountWideRiskEngine(
        DurableAccountWideRiskLedger(path)
    )
    assert restarted.recovery_required is True

    snapshot = _snapshot(open_risk="10")
    second_request = replace(
        _request(volume="2"),
        request_id="phase20-demo-risk-bridge-2",
        signal_fingerprint="phase20-demo-risk-bridge-signal-2",
    )
    report = authorize_phase20_demo_request(
        risk=restarted,
        request=second_request,
        snapshot=snapshot,
        observed_at=NOW,
    )

    assert restarted.recovery_required is False
    assert report.authorization.decision in {
        RiskDecision.ALLOW,
        RiskDecision.REDUCE,
        RiskDecision.REJECT,
    }
