from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from qore.infrastructure.fundednext_rule_refresh import (
    RollingStellarInstantRuleVerification,
    load_provider_rules_refresh,
)
from qore.infrastructure.fundednext_stellar_instant import (
    AutomationVerificationState,
    RuleVerificationState,
    StellarInstantRuleVerification,
)

FINGERPRINT = "a" * 64


def _baseline(*, current: bool = True) -> StellarInstantRuleVerification:
    return StellarInstantRuleVerification(
        verification_state=(
            RuleVerificationState.CURRENT if current else RuleVerificationState.STALE
        ),
        automation_state=AutomationVerificationState.VERIFIED,
        ea_addon_verified=True,
        platform_verified=True,
        exact_product_verified=True,
    )


def _write_evidence(
    path: Path,
    *,
    fingerprint: str = FINGERPRINT,
    maximum_loss: str = "0.06",
) -> None:
    payload = {
        "schema": "qore.fundednext.provider-rules-refresh.v3",
        "provider_rules_fingerprint": fingerprint,
        "facts": {
            "no_daily_loss_limit": True,
            "maximum_loss_fraction": maximum_loss,
            "trailing_maximum_loss": True,
            "ea_allowed_mt5": True,
            "cumulative_open_risk_fraction": "0.03",
            "reclassified_open_risk_fraction": "0.01",
            "cumulative_open_risk_applies": True,
            "stop_loss_required": True,
        },
        "sources": {},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_jit_rule_gate_revalidates_on_every_authorization_check(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 9, 16, 15, 0, tzinfo=UTC)
    refresh = tmp_path / "provider-rules-refresh.json"
    calls = 0

    def refresh_action() -> None:
        nonlocal calls
        calls += 1
        _write_evidence(refresh)

    gate = RollingStellarInstantRuleVerification(
        baseline=_baseline(),
        refresh_path=refresh,
        expected_provider_rules_fingerprint=FINGERPRINT,
        refresh_action=refresh_action,
    )
    assert gate.automated_mt5_allowed(now) is True
    assert gate.automated_mt5_allowed(now) is True
    assert calls == 2
    evidence = load_provider_rules_refresh(refresh)
    assert evidence.maximum_loss_fraction == "0.06"
    assert evidence.cumulative_open_risk_fraction == "0.03"


def test_jit_rule_gate_fails_closed_without_cached_fallback(tmp_path: Path) -> None:
    now = datetime(2026, 9, 16, 15, 0, tzinfo=UTC)
    refresh = tmp_path / "provider-rules-refresh.json"
    _write_evidence(refresh)

    def refresh_action() -> None:
        raise OSError("provider unavailable")

    gate = RollingStellarInstantRuleVerification(
        baseline=_baseline(),
        refresh_path=refresh,
        expected_provider_rules_fingerprint=FINGERPRINT,
        refresh_action=refresh_action,
    )
    assert gate.automated_mt5_allowed(now) is False


def test_jit_rule_gate_blocks_wrong_fingerprint_contract_or_baseline(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 9, 16, 15, 0, tzinfo=UTC)
    refresh = tmp_path / "provider-rules-refresh.json"

    def noop() -> None:
        return None

    _write_evidence(refresh, fingerprint="b" * 64)
    gate = RollingStellarInstantRuleVerification(
        baseline=_baseline(),
        refresh_path=refresh,
        expected_provider_rules_fingerprint=FINGERPRINT,
        refresh_action=noop,
    )
    assert gate.automated_mt5_allowed(now) is False

    _write_evidence(refresh, maximum_loss="0.03")
    assert gate.automated_mt5_allowed(now) is False

    _write_evidence(refresh)
    stale_baseline = RollingStellarInstantRuleVerification(
        baseline=_baseline(current=False),
        refresh_path=refresh,
        expected_provider_rules_fingerprint=FINGERPRINT,
        refresh_action=noop,
    )
    assert stale_baseline.automated_mt5_allowed(now) is False


def test_jit_rule_gate_requires_refresh_action(tmp_path: Path) -> None:
    with pytest.raises((TypeError, ValueError)):
        RollingStellarInstantRuleVerification(
            baseline=_baseline(),
            refresh_path=tmp_path / "rules.json",
            expected_provider_rules_fingerprint=FINGERPRINT,
            refresh_action=None,  # type: ignore[arg-type]
        )
