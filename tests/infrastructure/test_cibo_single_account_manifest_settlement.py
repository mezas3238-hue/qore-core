from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import RiskDecision
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_single_account_manifest_settlement import (
    manifest_row_to_sovereign_settlement,
)
from qore.infrastructure.cibo_single_account_sovereign_ceiling_run import (
    CiboSovereignCeilingDecisionReceipt,
)


NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


def _decision(
    *,
    volume: str = "1",
    risk: str = "10",
    decision: str = RiskDecision.ALLOW.value,
) -> CiboSovereignCeilingDecisionReceipt:
    authorized = Decimal(volume) if decision != RiskDecision.REJECT.value else Decimal(0)
    authorized_risk = Decimal(risk) if decision != RiskDecision.REJECT.value else Decimal(0)
    authorized_margin = Decimal("20") if decision != RiskDecision.REJECT.value else Decimal(0)
    return CiboSovereignCeilingDecisionReceipt(
        decision_epoch_id="epoch-1",
        decision_id="decision-1",
        option_id="ceiling:signal-1",
        signal_fingerprint="signal-1",
        trader_id="R34_XAUUSD",
        decided_at=NOW,
        capital_disposition="CAPITALIZE",
        risk_decision=decision,
        requested_volume=Decimal(volume),
        authorized_volume=authorized,
        requested_stop_risk_usd=Decimal(risk),
        authorized_stop_risk_usd=authorized_risk,
        authorized_margin_usd=authorized_margin,
        adaptive_leverage_multiplier=1,
        sizing_mode="CAPABILITY_MAXIMUM",
        semantic_digest="sha256:" + "a" * 64,
        native_mpc_derived_from_cognition=True,
    )


def _row() -> dict[str, object]:
    return {
        "signal_fingerprint": "signal-1",
        "trader_id": "R34_XAUUSD",
        "outcome_available_to_predecision": False,
        "market_predecision_state": {
            "provider_observation": {
                "ask": "101",
                "bid": "100",
                "tick_size": "1",
                "tick_value": "2",
                "commission_per_volume_usd": "3",
                "slippage_reserve_per_volume_usd": "4",
            }
        },
        "settlement_outcome_research_only": {
            "entry_at": (NOW + timedelta(minutes=1)).isoformat(),
            "exit_at": (NOW + timedelta(minutes=10)).isoformat(),
            "gross_structural_outcome_r": "2",
            "exit_reason": "TARGET",
            "not_available_to_predecision": True,
            "used_for_decision": False,
        },
    }


def test_structural_outcome_is_rescaled_to_sovereign_authorized_size() -> None:
    full = manifest_row_to_sovereign_settlement(
        row=_row(),
        decision=_decision(volume="1", risk="10"),
    )
    half = manifest_row_to_sovereign_settlement(
        row=_row(),
        decision=_decision(volume="0.5", risk="5"),
    )

    assert full.gross_pnl_usd == Decimal("20")
    assert full.provider_cost_usd == Decimal("9")
    assert full.realized_net_pnl_usd == Decimal("11")
    assert half.gross_pnl_usd == Decimal("10")
    assert half.provider_cost_usd == Decimal("4.5")
    assert half.realized_net_pnl_usd == Decimal("5.5")
    assert full.receipt.outcome_available_to_predecision is False
    assert full.receipt.settlement_sha256.startswith("sha256:")


def test_settlement_rejects_predecision_outcome_exposure() -> None:
    row = _row()
    row["outcome_available_to_predecision"] = True

    with pytest.raises(CiboCapitalManagementError):
        manifest_row_to_sovereign_settlement(
            row=row,
            decision=_decision(),
        )


def test_settlement_requires_risk_authorized_decision() -> None:
    with pytest.raises(CiboCapitalManagementError):
        manifest_row_to_sovereign_settlement(
            row=_row(),
            decision=_decision(decision=RiskDecision.REJECT.value),
        )
