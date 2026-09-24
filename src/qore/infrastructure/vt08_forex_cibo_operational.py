"""Operational CIBO gate for the frozen VT-08 R3.15 Forex capability.

CIBO preserves the independently certified VT-08 methodology, retained portfolio
sides and per-trade Risk fingerprint. It may request NORMAL/BANK/ATTACK operating
posture, but it cannot mint capital authority, resize the frozen setup, alter
entry/stop/target, or override Account-Wide Risk.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256

from qore.infrastructure.account_wide_risk import AccountWideRiskError
CERTIFIED_LIVE_DIRECTIONS: dict[str, frozenset[str]] = {
    "AUDJPY": frozenset({"short"}),
    "GBPUSD": frozenset({"short"}),
    "GBPJPY": frozenset({"long", "short"}),
    "EURUSD": frozenset({"long", "short"}),
    "XAUUSD": frozenset({"long", "short"}),
    "NAS100": frozenset({"long", "short"}),
}

R315_METHOD_FINGERPRINT = (
    "0c3fe8e1353386f7384a8532c7fe71bbbe9fcfdf1da7530be4b53e01bc59de0d"
)
R315_RISK_FINGERPRINT = (
    "dfb3fc8217b9895356ed19f8d7e1ee47fae765d39a9bb2e72e14c4ac41fad1f5"
)
R315_CIBO_AUTHORITY = "qore-vt08-b01-r315-cibo-authority-v1"
R315_CIBO_MARKETS = ("AUDJPY", "GBPJPY", "GBPUSD")
R315_CIBO_VERSION = "r3.15-operational-posture-under-sovereign-risk-v3"


class Vt08ForexCiboDecision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class Vt08ForexCiboPosture(StrEnum):
    NORMAL = "NORMAL"
    BANK = "BANK"
    ATTACK = "ATTACK"


@dataclass(frozen=True, slots=True)
class Vt08ForexCiboSetup:
    signal_fingerprint: str
    setup_fingerprint: str
    qore_symbol: str
    side: str
    entry_type: str
    intended_entry: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    methodology_fingerprint: str
    risk_policy_fingerprint: str
    decided_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        for name, value in (
            ("signal_fingerprint", self.signal_fingerprint),
            ("setup_fingerprint", self.setup_fingerprint),
            ("qore_symbol", self.qore_symbol),
            ("side", self.side),
            ("entry_type", self.entry_type),
        ):
            if not isinstance(value, str) or not value:
                raise AccountWideRiskError(f"CIBO {name} must be non-empty")
        if self.qore_symbol not in R315_CIBO_MARKETS:
            raise AccountWideRiskError("CIBO market outside R3.15 certification")
        if self.side not in {"long", "short"}:
            raise AccountWideRiskError("CIBO side must be long or short")
        if self.side not in CERTIFIED_LIVE_DIRECTIONS[self.qore_symbol]:
            raise AccountWideRiskError("CIBO side outside certified live portfolio")
        if self.entry_type not in {"market", "limit"}:
            raise AccountWideRiskError("CIBO entry type must be market or limit")
        if self.methodology_fingerprint != R315_METHOD_FINGERPRINT:
            raise AccountWideRiskError("CIBO methodology fingerprint mismatch")
        if self.risk_policy_fingerprint != R315_RISK_FINGERPRINT:
            raise AccountWideRiskError("CIBO Risk fingerprint mismatch")
        _aware(self.decided_at, "decided_at")
        _aware(self.expires_at, "expires_at")
        if self.expires_at <= self.decided_at:
            raise AccountWideRiskError("CIBO expiry must follow decision")
        if self.side == "long" and not (
            self.stop_loss < self.intended_entry < self.take_profit
        ):
            raise AccountWideRiskError("CIBO long geometry invalid")
        if self.side == "short" and not (
            self.take_profit < self.intended_entry < self.stop_loss
        ):
            raise AccountWideRiskError("CIBO short geometry invalid")


@dataclass(frozen=True, slots=True)
class Vt08ForexCiboAuthorization:
    setup: Vt08ForexCiboSetup
    decision: Vt08ForexCiboDecision
    requested_posture: Vt08ForexCiboPosture
    reason: str
    cibo_version: str
    cibo_policy_fingerprint: str

    def __post_init__(self) -> None:
        if not isinstance(self.setup, Vt08ForexCiboSetup):
            raise AccountWideRiskError("CIBO authorization setup invalid")
        if type(self.decision) is not Vt08ForexCiboDecision:
            raise AccountWideRiskError("CIBO decision invalid")
        if type(self.requested_posture) is not Vt08ForexCiboPosture:
            raise AccountWideRiskError("CIBO posture must be canonical")
        if not self.reason:
            raise AccountWideRiskError("CIBO decision reason required")
        if self.cibo_version != R315_CIBO_VERSION:
            raise AccountWideRiskError("CIBO version mismatch")
        if self.cibo_policy_fingerprint != cibo_policy_fingerprint():
            raise AccountWideRiskError("CIBO policy fingerprint mismatch")


def cibo_policy_fingerprint() -> str:
    material = {
        "authority": R315_CIBO_AUTHORITY,
        "version": R315_CIBO_VERSION,
        "methodology_fingerprint": R315_METHOD_FINGERPRINT,
        "risk_policy_fingerprint": R315_RISK_FINGERPRINT,
        "markets": R315_CIBO_MARKETS,
        "certified_live_directions": {
            symbol: tuple(sorted(sides))
            for symbol, sides in sorted(CERTIFIED_LIVE_DIRECTIONS.items())
        },
        "postures": tuple(item.value for item in Vt08ForexCiboPosture),
        "capital_authority": False,
        "risk_is_final_capital_authority": True,
        "attack_requires_risk_budget": True,
        "per_trade_risk_augmentation": False,
        "r3_17_research_copied_blindly": False,
    }
    return sha256(
        json.dumps(
            material,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def evaluate_vt08_forex_cibo(
    setup: Vt08ForexCiboSetup,
    *,
    enabled: bool,
    certification_current: bool,
    now: datetime,
    requested_posture: Vt08ForexCiboPosture = Vt08ForexCiboPosture.NORMAL,
) -> Vt08ForexCiboAuthorization:
    """Pass the certified setup unchanged or deny it; posture never creates capital."""

    if not isinstance(setup, Vt08ForexCiboSetup):
        raise AccountWideRiskError("CIBO requires canonical VT08 Forex setup")
    if type(requested_posture) is not Vt08ForexCiboPosture:
        raise AccountWideRiskError("CIBO requested posture must be canonical")
    _aware(now, "now")
    if now > setup.expires_at:
        decision = Vt08ForexCiboDecision.DENY
        reason = "setup-expired"
    elif not certification_current:
        decision = Vt08ForexCiboDecision.DENY
        reason = "r3.15-certification-not-current"
    elif not enabled:
        decision = Vt08ForexCiboDecision.DENY
        reason = "cibo-forex-disabled"
    else:
        decision = Vt08ForexCiboDecision.ALLOW
        reason = "r3.15-certified-capability-posture-request-forwarded-to-risk"
    return Vt08ForexCiboAuthorization(
        setup=setup,
        decision=decision,
        requested_posture=requested_posture,
        reason=reason,
        cibo_version=R315_CIBO_VERSION,
        cibo_policy_fingerprint=cibo_policy_fingerprint(),
    )


def _aware(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise AccountWideRiskError(f"CIBO {name} must be timezone-aware")
