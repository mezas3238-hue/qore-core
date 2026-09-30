from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.account_wide_risk_ledger import (
    DurableAccountWideRiskEngine,
    DurableAccountWideRiskLedger,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_demo_shadow_risk import (
    DEMO_CAPABILITY_SHADOW_RISK_POLICY_ID,
    build_demo_capability_risk_snapshot,
    demo_capability_shadow_risk_policy_sha256,
    observe_demo_capability_constraints,
)
from qore.infrastructure.cibo_ce2i_phase20_outcome_reconciliation import (
    Phase20ExecutedRiskEvidence,
)
from qore.infrastructure.ctrader_demo_compat import CTraderDemoAccountState

NOW = datetime(2026, 9, 27, 19, 0, tzinfo=UTC)


def _account(*, equity: str = "1000") -> CTraderDemoAccountState:
    return CTraderDemoAccountState(
        balance=Decimal("1050"),
        equity=Decimal(equity),
        margin=Decimal("100"),
        free_margin=Decimal("900") if equity != "0" else Decimal("0"),
        observed_at=NOW,
    )


def _risk(
    *,
    position_id: int = 77,
    observed_at: datetime = NOW - timedelta(seconds=1),
) -> Phase20ExecutedRiskEvidence:
    return Phase20ExecutedRiskEvidence(
        evidence_id=f"risk-{position_id}",
        decision_evidence_sha256="sha256:" + "a" * 64,
        signal_fingerprint=f"signal-{position_id}",
        qore_symbol="NAS100",
        provider_order_ref=f"order-{position_id}",
        side="long",
        position_id=position_id,
        authorized_source_volume=Decimal("1"),
        filled_source_volume=Decimal("1"),
        weighted_fill_price=Decimal("104"),
        intended_entry_price=Decimal("100"),
        structural_stop_price=Decimal("99"),
        stop_risk_per_volume_at_intended_entry_usd=Decimal("10"),
        executed_initial_stop_risk_usd=Decimal("50"),
        observed_at=observed_at,
        fill_evidence_refs=(f"fill-{position_id}",),
        fill_reconciled=True,
        mutation_outcome_known=True,
    )


def test_demo_shadow_risk_uses_only_actual_solvency_and_reconciled_risk(
    tmp_path: Path,
) -> None:
    snapshot = build_demo_capability_risk_snapshot(
        account_binding_id="ctrader-demo-free",
        account_state=_account(),
        open_position_ids=(77,),
        open_executed_risks=(_risk(),),
        pending_broker_worst_case_loss_usd=Decimal("25"),
    )
    engine = DurableAccountWideRiskEngine(
        DurableAccountWideRiskLedger(tmp_path / "risk.json")
    )

    constraints = observe_demo_capability_constraints(
        risk=engine,
        snapshot=snapshot,
        observed_at=NOW,
    )

    assert snapshot.open_stop_worst_case_loss == Decimal("50")
    assert snapshot.open_floating_loss == Decimal("50")
    assert snapshot.provider_budget.active_mll == Decimal("0")
    assert snapshot.provider_budget.provider_headroom == Decimal("1000")
    assert snapshot.qore_authorizable_headroom == Decimal("1000")
    assert constraints.aggregate_pre_order_worst_case_usd == Decimal("75")
    assert constraints.hard_risk_headroom_usd == Decimal("925")
    assert constraints.margin_headroom_usd == Decimal("900")
    assert constraints.survival_blocked is False


def test_demo_shadow_risk_fails_closed_if_open_position_lacks_risk_evidence() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="exact risk evidence for every open position",
    ):
        build_demo_capability_risk_snapshot(
            account_binding_id="ctrader-demo-free",
            account_state=_account(),
            open_position_ids=(77, 78),
            open_executed_risks=(_risk(position_id=77),),
            pending_broker_worst_case_loss_usd=Decimal("0"),
        )


def test_demo_shadow_risk_rejects_future_risk_evidence() -> None:
    with pytest.raises(
        CiboCapitalManagementError,
        match="cannot postdate account snapshot",
    ):
        build_demo_capability_risk_snapshot(
            account_binding_id="ctrader-demo-free",
            account_state=_account(),
            open_position_ids=(77,),
            open_executed_risks=(
                _risk(observed_at=NOW + timedelta(microseconds=1)),
            ),
            pending_broker_worst_case_loss_usd=Decimal("0"),
        )


def test_demo_shadow_risk_zero_equity_blocks_all_capacity(
    tmp_path: Path,
) -> None:
    snapshot = build_demo_capability_risk_snapshot(
        account_binding_id="ctrader-demo-free",
        account_state=_account(equity="0"),
        open_position_ids=(),
        open_executed_risks=(),
        pending_broker_worst_case_loss_usd=Decimal("0"),
    )
    engine = DurableAccountWideRiskEngine(
        DurableAccountWideRiskLedger(tmp_path / "risk.json")
    )

    constraints = observe_demo_capability_constraints(
        risk=engine,
        snapshot=snapshot,
        observed_at=NOW,
    )

    assert constraints.survival_blocked is True
    assert constraints.hard_risk_headroom_usd == 0
    assert constraints.margin_headroom_usd == 0


def test_demo_shadow_risk_policy_identity_is_deterministic() -> None:
    assert DEMO_CAPABILITY_SHADOW_RISK_POLICY_ID == (
        "CIBO_DEMO_CAPABILITY_SOLVENCY_ONLY_RISK_V1"
    )
    left = demo_capability_shadow_risk_policy_sha256()
    right = demo_capability_shadow_risk_policy_sha256()
    assert left == right
    assert left.startswith("sha256:")
    assert len(left) == 71
