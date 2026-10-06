from copy import deepcopy
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_single_account_manifest_economics import (
    manifest_row_to_ceiling_opportunity_evidence,
    manifest_to_ceiling_opportunity_evidence,
)
from qore.infrastructure.cibo_single_account_manifest_integrity import (
    reseal_single_account_manifest,
)


def _row(*, settlement_pnl: str = "1") -> dict[str, object]:
    return {
        "decision_epoch_id": "epoch-1",
        "market_decision_at": "2026-01-05T14:30:00+00:00",
        "trader_id": "R34_XAUUSD",
        "qore_symbol": "XAUUSD",
        "signal_fingerprint": "signal-a",
        "trader_opportunity": {
            "provider_symbol": "XAUUSD",
            "side": "long",
            "entry_type": "market",
            "intended_entry": "100",
            "stop_loss": "99",
            "take_profit": "102",
            "stop_loss_per_volume": "1",
            "margin_per_volume": "10",
            "volume_step": "0.01",
            "minimum_volume": "0.01",
            "maximum_volume": "100",
            "minimum_execution_steps": 1,
            "decision_context": [["ctx_session", "new_york"]],
        },
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
        "expectation": {
            "evidence_id": "CIBO_FROZEN_TRAIN_PRIOR:sha256:abc:R34_XAUUSD",
            "as_of": "2026-01-05T14:30:00+00:00",
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
        "settlement_outcome_research_only": {
            "net_pnl_usd": settlement_pnl,
            "not_available_to_predecision": True,
            "used_for_decision": False,
        },
        "outcome_available_to_predecision": False,
    }


def test_manifest_row_builds_exact_causal_ceiling_economics() -> None:
    evidence = manifest_row_to_ceiling_opportunity_evidence(_row())

    assert evidence.expected_net_value_usd == Decimal("5")
    assert evidence.expected_capital_minutes == Decimal("30")
    assert evidence.provider_cost_per_volume_usd == Decimal("9")
    assert evidence.context_allowed is True
    assert evidence.provider_viable is True
    assert evidence.capital_source_eligible is True
    assert evidence.uncertainty_penalty_usd == Decimal("0")
    assert evidence.expectation_evidence_sha256.startswith("sha256:")
    assert len(evidence.expectation_evidence_sha256) == 71
    context = dict(evidence.opportunity.decision_context)
    assert context["ctx_session"] == "new_york"
    assert context["cibo_context_quality_disposition"] == "ALLOW"
    assert context["cibo_expectation_basis"] == "FROZEN_HISTORICAL_PRIOR"
    assert context["cibo_expected_value_usd"] == "5"
    assert context["cibo_expected_capital_minutes"] == "30"


def test_settlement_outcome_cannot_change_predecision_economics() -> None:
    positive = manifest_row_to_ceiling_opportunity_evidence(
        _row(settlement_pnl="500")
    )
    negative = manifest_row_to_ceiling_opportunity_evidence(
        _row(settlement_pnl="-500")
    )

    assert positive == negative


def test_manifest_adapter_validates_digest_before_conversion() -> None:
    manifest = reseal_single_account_manifest(
        {
            "schema": "qore.cibo.single-account-7trader-maximum-capability.v1",
            "opportunities": [_row()],
        }
    )

    evidence = manifest_to_ceiling_opportunity_evidence(manifest)
    assert len(evidence) == 1

    tampered = deepcopy(manifest)
    tampered["opportunities"][0]["expectation"]["expected_net_value_usd"] = "999"
    with pytest.raises(CiboCapitalManagementError):
        manifest_to_ceiling_opportunity_evidence(tampered)


def test_manifest_adapter_rejects_outcome_aware_expectation() -> None:
    row = _row()
    row["expectation"]["outcome_used"] = True

    with pytest.raises(CiboCapitalManagementError):
        manifest_row_to_ceiling_opportunity_evidence(row)
