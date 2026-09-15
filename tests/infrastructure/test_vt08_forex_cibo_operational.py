from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import AccountWideRiskError
from qore.infrastructure.vt08_forex_cibo_operational import (
    R315_CIBO_VERSION,
    R315_METHOD_FINGERPRINT,
    R315_RISK_FINGERPRINT,
    Vt08ForexCiboDecision,
    Vt08ForexCiboPosture,
    Vt08ForexCiboSetup,
    cibo_policy_fingerprint,
    evaluate_vt08_forex_cibo,
)

_NOW = datetime(2026, 9, 15, 3, 0, tzinfo=UTC)


def _setup() -> Vt08ForexCiboSetup:
    return Vt08ForexCiboSetup(
        signal_fingerprint="signal-gbpusd-001",
        setup_fingerprint="setup-gbpusd-001",
        qore_symbol="GBPUSD",
        side="short",
        entry_type="market",
        intended_entry=Decimal("1.2500"),
        stop_loss=Decimal("1.2550"),
        take_profit=Decimal("1.2400"),
        methodology_fingerprint=R315_METHOD_FINGERPRINT,
        risk_policy_fingerprint=R315_RISK_FINGERPRINT,
        decided_at=_NOW,
        expires_at=_NOW + timedelta(minutes=5),
    )


def test_cibo_forwards_normal_bank_attack_as_requests_not_capital_authority() -> None:
    for posture in Vt08ForexCiboPosture:
        authorization = evaluate_vt08_forex_cibo(
            _setup(),
            enabled=True,
            certification_current=True,
            now=_NOW,
            requested_posture=posture,
        )
        assert authorization.decision is Vt08ForexCiboDecision.ALLOW
        assert authorization.requested_posture is posture
        assert authorization.setup == _setup()
        assert authorization.cibo_version == R315_CIBO_VERSION
        assert authorization.cibo_policy_fingerprint == cibo_policy_fingerprint()


def test_uncertified_gbpusd_long_is_rejected_at_setup_boundary() -> None:
    with pytest.raises(AccountWideRiskError, match="outside certified live portfolio"):
        Vt08ForexCiboSetup(
            signal_fingerprint="signal-gbpusd-long",
            setup_fingerprint="setup-gbpusd-long",
            qore_symbol="GBPUSD",
            side="long",
            entry_type="market",
            intended_entry=Decimal("1.2500"),
            stop_loss=Decimal("1.2450"),
            take_profit=Decimal("1.2600"),
            methodology_fingerprint=R315_METHOD_FINGERPRINT,
            risk_policy_fingerprint=R315_RISK_FINGERPRINT,
            decided_at=_NOW,
            expires_at=_NOW + timedelta(minutes=5),
        )


def test_cibo_deny_cannot_be_overridden_by_attack_request() -> None:
    authorization = evaluate_vt08_forex_cibo(
        _setup(),
        enabled=False,
        certification_current=True,
        now=_NOW,
        requested_posture=Vt08ForexCiboPosture.ATTACK,
    )
    assert authorization.decision is Vt08ForexCiboDecision.DENY
    assert authorization.requested_posture is Vt08ForexCiboPosture.ATTACK


def test_cibo_fingerprint_is_stable_and_sha256() -> None:
    assert len(cibo_policy_fingerprint()) == 64
    assert cibo_policy_fingerprint() == cibo_policy_fingerprint()
