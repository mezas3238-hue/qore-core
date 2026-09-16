"""Rolling FundedNext rule-freshness evidence for 24/7 LIVE operation.

The Owner's live authorization remains explicit and account/SHA bound.  This
module only replaces a manually chosen provider-rule expiry with a renewable,
fail-closed lease backed by fresh checks of official FundedNext documentation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from qore.infrastructure.fundednext_stellar_instant import (
    AutomationVerificationState,
    RuleVerificationState,
    StellarInstantRuleVerification,
)

_SCHEMA = "qore.fundednext.provider-rules-refresh.v1"


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _timestamp(value: object, name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be an ISO-8601 string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    _aware(parsed, name)
    return parsed


@dataclass(frozen=True, slots=True)
class ProviderRulesRefreshEvidence:
    provider_rules_fingerprint: str
    verified_at: datetime
    valid_until: datetime
    no_daily_loss_limit: bool
    trailing_mll_fraction: str
    ea_allowed_mt5: bool
    cumulative_open_risk_fraction: str
    cumulative_open_risk_applies: bool

    def __post_init__(self) -> None:
        _aware(self.verified_at, "verified_at")
        _aware(self.valid_until, "valid_until")
        if self.valid_until <= self.verified_at:
            raise ValueError("valid_until must follow verified_at")
        if len(self.provider_rules_fingerprint) != 64:
            raise ValueError("provider_rules_fingerprint must be SHA-256 hex")

    def is_current(self, *, now: datetime, expected_fingerprint: str) -> bool:
        _aware(now, "now")
        return (
            self.provider_rules_fingerprint == expected_fingerprint
            and self.verified_at <= now <= self.valid_until
            and self.no_daily_loss_limit
            and self.trailing_mll_fraction == "0.06"
            and self.ea_allowed_mt5
            and self.cumulative_open_risk_fraction == "0.03"
            and self.cumulative_open_risk_applies
        )


def load_provider_rules_refresh(path: Path) -> ProviderRulesRefreshEvidence:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != _SCHEMA:
        raise ValueError("provider rule refresh schema mismatch")
    facts = payload.get("facts")
    if not isinstance(facts, dict):
        raise ValueError("provider rule refresh facts missing")
    return ProviderRulesRefreshEvidence(
        provider_rules_fingerprint=str(payload["provider_rules_fingerprint"]),
        verified_at=_timestamp(payload["verified_at"], "verified_at"),
        valid_until=_timestamp(payload["valid_until"], "valid_until"),
        no_daily_loss_limit=facts.get("no_daily_loss_limit") is True,
        trailing_mll_fraction=str(facts.get("trailing_mll_fraction", "")),
        ea_allowed_mt5=facts.get("ea_allowed_mt5") is True,
        cumulative_open_risk_fraction=str(facts.get("cumulative_open_risk_fraction", "")),
        cumulative_open_risk_applies=facts.get("cumulative_open_risk_applies") is True,
    )


@dataclass(frozen=True, slots=True)
class RollingStellarInstantRuleVerification:
    baseline: StellarInstantRuleVerification
    refresh_path: Path
    expected_provider_rules_fingerprint: str

    def __post_init__(self) -> None:
        if not isinstance(self.baseline, StellarInstantRuleVerification):
            raise ValueError("baseline Stellar Instant rule verification required")
        if len(self.expected_provider_rules_fingerprint) != 64:
            raise ValueError("expected provider fingerprint must be SHA-256 hex")

    def automated_mt5_allowed(self, now: datetime) -> bool:
        _aware(now, "now")
        entitlement_ok = (
            self.baseline.automation_state is AutomationVerificationState.VERIFIED
            and self.baseline.ea_addon_verified
            and self.baseline.platform_verified
            and self.baseline.exact_product_verified
        )
        if not entitlement_ok:
            return False
        if (
            self.baseline.verification_state is RuleVerificationState.CURRENT
            and self.baseline.is_current(now)
        ):
            return True
        try:
            evidence = load_provider_rules_refresh(self.refresh_path)
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return False
        return evidence.is_current(
            now=now,
            expected_fingerprint=self.expected_provider_rules_fingerprint,
        )
