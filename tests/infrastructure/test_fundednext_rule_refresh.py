from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

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


def _baseline(now: datetime, *, current: bool = False) -> StellarInstantRuleVerification:
    return StellarInstantRuleVerification(
        rules_verified_at=now - timedelta(hours=2),
        rules_valid_until=now + timedelta(hours=1) if current else now - timedelta(hours=1),
        verification_state=RuleVerificationState.CURRENT,
        automation_state=AutomationVerificationState.VERIFIED,
        ea_addon_verified=True,
        platform_verified=True,
        exact_product_verified=True,
    )


def _write_evidence(
    path: Path, *, now: datetime, valid: bool = True, fingerprint: str = FINGERPRINT
) -> None:
    payload = {
        "schema": "qore.fundednext.provider-rules-refresh.v1",
        "provider_rules_fingerprint": fingerprint,
        "verified_at": (now - timedelta(minutes=5)).isoformat(),
        "valid_until": (
            now + timedelta(hours=6) if valid else now - timedelta(minutes=1)
        ).isoformat(),
        "facts": {
            "no_daily_loss_limit": True,
            "trailing_mll_fraction": "0.06",
            "ea_allowed_mt5": True,
            "cumulative_open_risk_fraction": "0.03",
            "cumulative_open_risk_applies": True,
        },
        "sources": {},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_rolling_rule_gate_uses_current_baseline_without_refresh(tmp_path: Path) -> None:
    now = datetime(2026, 9, 16, 15, 0, tzinfo=UTC)
    gate = RollingStellarInstantRuleVerification(
        baseline=_baseline(now, current=True),
        refresh_path=tmp_path / "missing.json",
        expected_provider_rules_fingerprint=FINGERPRINT,
    )
    assert gate.automated_mt5_allowed(now) is True


def test_rolling_rule_gate_accepts_fresh_matching_refresh_after_baseline_expiry(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 9, 16, 15, 0, tzinfo=UTC)
    refresh = tmp_path / "provider-rules-refresh.json"
    _write_evidence(refresh, now=now)
    gate = RollingStellarInstantRuleVerification(
        baseline=_baseline(now),
        refresh_path=refresh,
        expected_provider_rules_fingerprint=FINGERPRINT,
    )
    assert gate.automated_mt5_allowed(now) is True
    evidence = load_provider_rules_refresh(refresh)
    assert evidence.trailing_mll_fraction == "0.06"
    assert evidence.cumulative_open_risk_fraction == "0.03"


def test_rolling_rule_gate_fails_closed_for_stale_missing_or_wrong_fingerprint(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 9, 16, 15, 0, tzinfo=UTC)
    refresh = tmp_path / "provider-rules-refresh.json"
    gate = RollingStellarInstantRuleVerification(
        baseline=_baseline(now),
        refresh_path=refresh,
        expected_provider_rules_fingerprint=FINGERPRINT,
    )
    assert gate.automated_mt5_allowed(now) is False

    _write_evidence(refresh, now=now, valid=False)
    assert gate.automated_mt5_allowed(now) is False

    _write_evidence(refresh, now=now, fingerprint="b" * 64)
    assert gate.automated_mt5_allowed(now) is False

    refresh.write_text("{broken", encoding="utf-8")
    assert gate.automated_mt5_allowed(now) is False
