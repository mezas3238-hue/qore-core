"""VT-08 B01 -> CIBO translation for the independent cTrader DEMO laboratory."""

from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal
from hashlib import sha256

from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Candidate
from qore.infrastructure.vt08_forex_cibo_operational import (
    R315_METHOD_FINGERPRINT,
    R315_RISK_FINGERPRINT,
    Vt08ForexCiboPosture,
    Vt08ForexCiboSetup,
)

R315_OPERATIONAL_ENTRY_TYPE = "market"
R315_SIGNAL_VALIDITY = timedelta(minutes=2)
R315_ATTACK_MIN_EARNED_CUSHION_FRACTION = Decimal("0.005")


def cibo_setup_from_b01(candidate: Vt08B01Candidate) -> Vt08ForexCiboSetup:
    if not isinstance(candidate, Vt08B01Candidate):
        raise TypeError("exact Vt08B01Candidate required")
    if candidate.methodology_fingerprint != R315_METHOD_FINGERPRINT:
        raise ValueError("B01 executable fingerprint is outside R3.15 certification")
    side = "long" if candidate.side is DemoTradingSetupSide.LONG else "short"
    material = {
        "symbol": candidate.symbol,
        "side": side,
        "decision_at": candidate.decision_at.isoformat(),
        "entry": str(candidate.setup.entry_price),
        "stop": str(candidate.setup.invalidation_price),
        "target": str(candidate.setup.take_profit_price),
        "methodology": candidate.methodology_fingerprint,
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    return Vt08ForexCiboSetup(
        signal_fingerprint=sha256(b"signal|" + encoded).hexdigest(),
        setup_fingerprint=sha256(b"setup|" + encoded).hexdigest(),
        qore_symbol=candidate.symbol,
        side=side,
        entry_type=R315_OPERATIONAL_ENTRY_TYPE,
        intended_entry=candidate.setup.entry_price,
        stop_loss=candidate.setup.invalidation_price,
        take_profit=candidate.setup.take_profit_price,
        methodology_fingerprint=R315_METHOD_FINGERPRINT,
        risk_policy_fingerprint=R315_RISK_FINGERPRINT,
        decided_at=candidate.decision_at,
        expires_at=candidate.decision_at + R315_SIGNAL_VALIDITY,
    )


def request_cibo_posture(
    *,
    initial_balance: Decimal,
    balance: Decimal,
    equity: Decimal,
    current_aggregate_risk: Decimal,
) -> Vt08ForexCiboPosture:
    earned = max(Decimal(0), balance - initial_balance)
    floating_loss = max(Decimal(0), balance - equity)
    attack_threshold = initial_balance * R315_ATTACK_MIN_EARNED_CUSHION_FRACTION
    if earned >= attack_threshold and floating_loss == 0:
        return Vt08ForexCiboPosture.ATTACK
    if floating_loss > 0 or current_aggregate_risk >= initial_balance * Decimal("0.005"):
        return Vt08ForexCiboPosture.BANK
    return Vt08ForexCiboPosture.NORMAL
