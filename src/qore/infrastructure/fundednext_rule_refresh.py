"""Automated FundedNext provider-rule verification for LIVE operation.

LIVE order submission never depends on an Owner-entered expiry date or a cached
TTL. The production gate re-runs the official-source verifier immediately before
each real provider submission and fails closed on any fetch, contract, or
fingerprint mismatch. Scheduled refresh remains telemetry/prewarming only.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from qore.infrastructure.fundednext_stellar_instant import (
    AutomationVerificationState,
    RuleVerificationState,
    StellarInstantRuleVerification,
)

_SCHEMA = "qore.fundednext.provider-rules-refresh.v3"


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")

@dataclass(frozen=True, slots=True)
class ProviderRulesRefreshEvidence:
    provider_rules_fingerprint: str
    no_daily_loss_limit: bool
    maximum_loss_fraction: str
    trailing_maximum_loss: bool
    ea_allowed_mt5: bool
    cumulative_open_risk_fraction: str
    reclassified_open_risk_fraction: str
    cumulative_open_risk_applies: bool
    stop_loss_required: bool

    def __post_init__(self) -> None:
        fingerprint = self.provider_rules_fingerprint
        if len(fingerprint) != 64 or any(
            ch not in "0123456789abcdef" for ch in fingerprint
        ):
            raise ValueError(
                "provider_rules_fingerprint must be lowercase SHA-256 hex"
            )

    def matches_contract(self, *, expected_fingerprint: str) -> bool:
        return (
            self.provider_rules_fingerprint == expected_fingerprint
            and self.no_daily_loss_limit
            and self.maximum_loss_fraction == "0.06"
            and self.trailing_maximum_loss
            and self.ea_allowed_mt5
            and self.cumulative_open_risk_fraction == "0.03"
            and self.reclassified_open_risk_fraction == "0.01"
            and self.cumulative_open_risk_applies
            and self.stop_loss_required
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
        no_daily_loss_limit=facts.get("no_daily_loss_limit") is True,
        maximum_loss_fraction=str(facts.get("maximum_loss_fraction", "")),
        trailing_maximum_loss=facts.get("trailing_maximum_loss") is True,
        ea_allowed_mt5=facts.get("ea_allowed_mt5") is True,
        cumulative_open_risk_fraction=str(
            facts.get("cumulative_open_risk_fraction", "")
        ),
        reclassified_open_risk_fraction=str(
            facts.get("reclassified_open_risk_fraction", "")
        ),
        cumulative_open_risk_applies=(
            facts.get("cumulative_open_risk_applies") is True
        ),
        stop_loss_required=facts.get("stop_loss_required") is True,
    )


@dataclass(frozen=True, slots=True)
class RollingStellarInstantRuleVerification:
    """Compatibility name for the no-expiry, just-in-time LIVE rule gate."""

    baseline: StellarInstantRuleVerification
    refresh_path: Path
    expected_provider_rules_fingerprint: str
    refresh_action: Callable[[], None]

    def __post_init__(self) -> None:
        if not isinstance(self.baseline, StellarInstantRuleVerification):
            raise ValueError("baseline Stellar Instant rule verification required")
        fingerprint = self.expected_provider_rules_fingerprint
        if len(fingerprint) != 64 or any(
            ch not in "0123456789abcdef" for ch in fingerprint
        ):
            raise ValueError(
                "expected provider fingerprint must be lowercase SHA-256 hex"
            )
        if not callable(self.refresh_action):
            raise ValueError("just-in-time provider refresh action is required")

    def automated_mt5_allowed(self, now: datetime) -> bool:
        _aware(now, "now")
        entitlement_ok = (
            self.baseline.verification_state is RuleVerificationState.CURRENT
            and self.baseline.automation_state is AutomationVerificationState.VERIFIED
            and self.baseline.ea_addon_verified
            and self.baseline.platform_verified
            and self.baseline.exact_product_verified
        )
        if not entitlement_ok:
            return False
        try:
            self.refresh_action()
            evidence = load_provider_rules_refresh(self.refresh_path)
        except (OSError, ValueError, KeyError, json.JSONDecodeError, RuntimeError):
            return False
        except Exception:  # noqa: BLE001 - external verification must fail closed
            return False
        return evidence.matches_contract(
            expected_fingerprint=self.expected_provider_rules_fingerprint,
        )
