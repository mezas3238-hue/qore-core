from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_a2_internal_capital_market_phase22_receipt import (
    RECEIPT_ID,
    SOURCE_WORKSTREAM,
    build_a2_internal_capital_market_phase22_receipt,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_internal_capital_market import (
    GENC6_MARKET_ID,
    GENC6_POLICY_FROZEN_AT,
    GENC6_POLICY_ID,
    Genc6Action,
    Genc6InternalCapitalMarketDecision,
    genc6_policy_sha256,
)


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def _decision() -> Genc6InternalCapitalMarketDecision:
    return Genc6InternalCapitalMarketDecision(
        market_id=GENC6_MARKET_ID,
        policy_id=GENC6_POLICY_ID,
        policy_sha256=genc6_policy_sha256(),
        policy_frozen_at=GENC6_POLICY_FROZEN_AT,
        decision_id="genc6:decision:a2",
        scarcity_event_id="genc6:scarcity:a2",
        decision_at=datetime(2026, 10, 1, 22, 0, tzinfo=UTC),
        account_provider_key="CTRADER_DEMO",
        account_ref="A2-SCIENCE",
        candidate_set_sha256=_sha("candidates"),
        legal_action_set_sha256=_sha("legal-actions"),
        legal_candidate_ids=(),
        reserve_action_legal=True,
        candidate_evidence_sha256s=(),
        genc5_decision_sha256s=(),
        portfolio_state_sha256=_sha("portfolio"),
        t19_ledger_sha256=_sha("t19"),
        available_capital_usd=Decimal("60"),
        true_scarcity=True,
        control_action=Genc6Action.RESERVE_NO_DEPLOYMENT,
        control_candidate_id=None,
        control_amount_usd=Decimal("0"),
        treatment_action=Genc6Action.RESERVE_NO_DEPLOYMENT,
        treatment_candidate_id=None,
        treatment_amount_usd=Decimal("0"),
        reserve_amount_usd=Decimal("60"),
        active_comparable_dimensions=(),
        control_reason="reserve under true scarcity",
        treatment_reason="reserve under true scarcity",
        blocker_codes=(),
        treatment_differs_from_control=False,
    )


def _receipt(decision: Genc6InternalCapitalMarketDecision | None = None):
    return build_a2_internal_capital_market_phase22_receipt(
        decisions=(decision or _decision(),),
        source_head="d" * 40,
        artifact_sha256=_sha("artifact"),
        canonical_phase22_manifest_sha256=_sha("phase22"),
        source_population_sha256=_sha("population"),
    )


def test_a2_internal_capital_market_receipt_binds_true_scarcity() -> None:
    receipt = _receipt()

    assert receipt.receipt_id == RECEIPT_ID
    assert receipt.source_workstream == SOURCE_WORKSTREAM
    assert receipt.policy_id == GENC6_POLICY_ID
    assert receipt.policy_sha256 == genc6_policy_sha256()
    assert receipt.decision_count == 1
    assert receipt.true_scarcity_decision_count == 1
    assert receipt.true_scarcity_binding is True
    assert receipt.capital_conservation_proven is True
    assert receipt.double_spend_detected is False
    assert receipt.outcome_freeze_preserved is True
    assert receipt.productive_authority is False


def test_a2_internal_capital_market_rejects_non_scarcity_population() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="accepts true scarcity only",
    ):
        _receipt(replace(_decision(), true_scarcity=False))


def test_a2_internal_capital_market_rejects_capital_creation() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="capital conservation violated",
    ):
        _receipt(
            replace(
                _decision(),
                reserve_amount_usd=Decimal("61"),
            )
        )


def test_a2_internal_capital_market_rejects_outcome_at_seal() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="shadow decision cannot contain outcome/authority",
    ):
        replace(_decision(), outcome_present_at_seal=True)


def test_a2_internal_capital_market_receipt_is_deterministic() -> None:
    left = _receipt()
    right = _receipt()

    assert left.decision_population_sha256 == right.decision_population_sha256
    assert left.fingerprint() == right.fingerprint()
