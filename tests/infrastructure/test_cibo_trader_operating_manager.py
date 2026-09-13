from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_trader_capability_profile import (
    CiboEvidenceRef,
    CiboTraderConfigFingerprint,
)
from qore.infrastructure.cibo_trader_manager import CiboRiskMode
from qore.infrastructure.cibo_trader_operating_manager import (
    CiboCapitalSnapshot,
    CiboOperatingAuthority,
    CiboOperatingManagerValidationError,
    CiboOperatingPosture,
    CiboRiskRequestMode,
    CiboTraderOperatingManager,
)
from qore.infrastructure.research_evaluator_identity import (
    ResearchDecisionEvaluatorFamily,
    ResearchDecisionEvaluatorIdentity,
    ResearchDecisionEvaluatorSchemaVersion,
)
from qore.infrastructure.research_run import ResearchSoftwareRevision

_NOW = datetime(2026, 9, 13, 16, 0, tzinfo=UTC)
_MANAGER = CiboTraderOperatingManager()


def _authority() -> CiboOperatingAuthority:
    return CiboOperatingAuthority(
        trader_identity=ResearchDecisionEvaluatorIdentity(
            family=ResearchDecisionEvaluatorFamily("virtual.trader.vt08"),
            schema_version=ResearchDecisionEvaluatorSchemaVersion("v1"),
            software_revision=ResearchSoftwareRevision("r3.8-b01"),
        ),
        config_fingerprint=CiboTraderConfigFingerprint("1" * 64),
        risk_mode=CiboRiskMode.CIBO_MANAGED_TRADERS_RISK,
        authority_ref=CiboEvidenceRef("evidence:r317-research-authority"),
        research_only=True,
    )


def _capital(
    *,
    equity: str = "1.03",
    peak: str = "1.03",
    banked: str = "1.005",
) -> CiboCapitalSnapshot:
    return CiboCapitalSnapshot(
        starting_equity=Decimal("1"),
        equity=Decimal(equity),
        peak_equity=Decimal(peak),
        day_start_equity=Decimal("1.025"),
        risk_floor=Decimal("0.98"),
        current_banked_floor=Decimal(banked),
        observed_at=_NOW,
    )


def test_cibo_attack_is_manager_decision_not_risk_authorization() -> None:
    result = _MANAGER.issue(
        _authority(),
        CiboOperatingPosture.ATTACK,
        _capital(),
        protected_capital_floor=Decimal("1.005"),
        requested_risk_envelope=CiboEvidenceRef("evidence:risk-envelope.attack"),
        decided_at=_NOW,
        reasons=("free-cushion-available",),
    )
    assert result.posture is CiboOperatingPosture.ATTACK
    assert result.risk_request.mode is CiboRiskRequestMode.ATTACK
    assert result.risk_request.cibo_loss_budget_ceiling == Decimal("0.025")
    assert not hasattr(result.risk_request, "authorized_quantity")
    assert not hasattr(result.risk_request, "risk_authorization")


def test_attack_requires_previously_banked_profit() -> None:
    with pytest.raises(CiboOperatingManagerValidationError):
        _MANAGER.issue(
            _authority(),
            CiboOperatingPosture.ATTACK,
            _capital(banked="0"),
            protected_capital_floor=Decimal("1"),
            requested_risk_envelope=CiboEvidenceRef("evidence:risk-envelope.attack"),
            decided_at=_NOW,
            reasons=("attack-without-bank",),
        )


def test_bank_is_monotonic_and_cannot_be_unbanked() -> None:
    with pytest.raises(CiboOperatingManagerValidationError):
        _MANAGER.issue(
            _authority(),
            CiboOperatingPosture.BANK,
            _capital(banked="1.01"),
            protected_capital_floor=Decimal("1.009"),
            requested_risk_envelope=CiboEvidenceRef("evidence:risk-envelope.base"),
            decided_at=_NOW,
            reasons=("bank-profit",),
        )


def test_suspend_requests_zero_risk_and_no_envelope() -> None:
    result = _MANAGER.issue(
        _authority(),
        CiboOperatingPosture.SUSPEND,
        _capital(),
        protected_capital_floor=Decimal("1.005"),
        requested_risk_envelope=None,
        decided_at=_NOW,
        reasons=("capital-protection",),
    )
    assert result.risk_request.mode is CiboRiskRequestMode.ZERO
    assert result.risk_request.requested_envelope_ref is None
    assert result.risk_request.cibo_loss_budget_ceiling == 0


def test_non_managed_risk_cannot_enter_cibo_operating_authority() -> None:
    with pytest.raises(CiboOperatingManagerValidationError):
        CiboOperatingAuthority(
            trader_identity=_authority().trader_identity,
            config_fingerprint=_authority().config_fingerprint,
            risk_mode=CiboRiskMode.TRADERS_RISK_ONLY,
            authority_ref=CiboEvidenceRef("evidence:invalid-authority"),
            research_only=True,
        )
