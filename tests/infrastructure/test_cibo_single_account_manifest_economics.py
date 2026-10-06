from copy import deepcopy
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
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
            "evidence_available_at": "2025-12-31T23:59:00+00:00",
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
    assert (
        evidence.expectation_basis
        is CausalExpectationBasis.FROZEN_HISTORICAL_PRIOR
    )
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
    assert context["cibo_context_quality_rules"] == "none"
    assert context["cibo_expected_value_usd"] == "5"
    assert context["cibo_expected_net_utility_usd"] == "4.91"
    assert context["cibo_expected_capital_minutes"] == "30"


def test_walk_forward_confidence_is_exposed_to_cognition_causally() -> None:
    row = _row()
    row["expectation"] = {
        **row["expectation"],
        "evidence_id": "CIBO_WALK_FORWARD_EMPIRICAL_V1:sha256:abc:R34_XAUUSD",
        "evidence_available_at": "2026-01-05T14:00:00+00:00",
        "basis": "WALK_FORWARD_EMPIRICAL_FORECAST",
        "walk_forward_observation_count": 25,
        "walk_forward_maturity": "MATURE",
        "walk_forward_mature_for_capital_consideration": True,
        "walk_forward_positive_block_count": 4,
        "walk_forward_nonpositive_block_count": 1,
        "walk_forward_block_dispersion_r": "1.25",
        "walk_forward_median_absolute_deviation_r": "0.20",
        "walk_forward_maturity_fraction": "1",
    }

    evidence = manifest_row_to_ceiling_opportunity_evidence(row)
    context = dict(evidence.opportunity.decision_context)

    assert context["cibo_walk_forward_observation_count"] == "25"
    assert context["cibo_walk_forward_maturity"] == "MATURE"
    assert (
        context["cibo_walk_forward_mature_for_capital_consideration"]
        == "true"
    )
    assert context["cibo_walk_forward_positive_block_count"] == "4"
    assert context["cibo_walk_forward_nonpositive_block_count"] == "1"
    assert context["cibo_walk_forward_block_dispersion_r"] == "1.25"
    assert (
        context["cibo_walk_forward_median_absolute_deviation_r"]
        == "0.20"
    )
    assert context["cibo_walk_forward_maturity_fraction"] == "1"
    assert context["cibo_walk_forward_evidence_age_minutes"] == "30"


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


def test_manifest_rejects_prior_content_that_did_not_exist_yet() -> None:
    row = _row()
    row["market_decision_at"] = "2019-07-01T14:31:00+00:00"
    row["expectation"] = {
        **row["expectation"],
        "evidence_id": (
            "CIBO_PHASE20_TRAIN_PRIOR_V1:"
            "sha256:15b059ea1e303fee7a9ed0894480ee1da6091647482a0811f1090335925b6caa:"
            "R34_XAUUSD"
        ),
        "as_of": "2019-07-01T14:31:00+00:00",
    }
    row["expectation"].pop("evidence_available_at", None)

    with pytest.raises(
        CiboCapitalManagementError,
        match="expectation evidence was not available at decision time",
    ):
        manifest_row_to_ceiling_opportunity_evidence(row)


def test_manifest_requires_availability_provenance_for_other_expectations() -> None:
    row = _row()
    row["expectation"].pop("evidence_available_at")

    with pytest.raises(
        CiboCapitalManagementError,
        match="expectation must declare when its evidence became available",
    ):
        manifest_row_to_ceiling_opportunity_evidence(row)


def test_burned_context_research_cannot_hard_veto_capital() -> None:
    row = _row()
    row["context_quality"] = {
        **row["context_quality"],
        "disposition": "ABSTAIN",
        "matched_rule_ids": ["LOW_PROJECTED_R_BUCKET"],
        "research_mode": (
            "NON_CERTIFYING_REUSED_HOLDOUT_ADAPTIVE_RESEARCH"
        ),
    }

    evidence = manifest_row_to_ceiling_opportunity_evidence(row)
    context = dict(evidence.opportunity.decision_context)

    assert evidence.context_allowed is True
    assert (
        context["cibo_context_quality_hard_gate_authorized"]
        == "false"
    )
    assert (
        context["cibo_context_quality_research_mode"]
        == "NON_CERTIFYING_REUSED_HOLDOUT_ADAPTIVE_RESEARCH"
    )


def test_causal_context_policy_can_hard_veto_when_already_available() -> None:
    row = _row()
    row["context_quality"] = {
        **row["context_quality"],
        "disposition": "ABSTAIN",
        "matched_rule_ids": ["CAUSAL_RULE_A"],
        "research_mode": "CAUSAL_POLICY",
        "hard_gate_authorized": True,
        "policy_available_at": "2025-12-31T00:00:00+00:00",
    }

    evidence = manifest_row_to_ceiling_opportunity_evidence(row)
    context = dict(evidence.opportunity.decision_context)

    assert evidence.context_allowed is False
    assert (
        context["cibo_context_quality_hard_gate_authorized"]
        == "true"
    )


def test_context_policy_cannot_veto_before_policy_existed() -> None:
    row = _row()
    row["context_quality"] = {
        **row["context_quality"],
        "disposition": "ABSTAIN",
        "matched_rule_ids": ["CAUSAL_RULE_A"],
        "research_mode": "CAUSAL_POLICY",
        "hard_gate_authorized": True,
        "policy_available_at": "2026-02-01T00:00:00+00:00",
    }

    with pytest.raises(
        CiboCapitalManagementError,
        match="context-quality policy was not available at decision time",
    ):
        manifest_row_to_ceiling_opportunity_evidence(row)
