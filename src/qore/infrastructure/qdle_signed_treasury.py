"""Verify signed event from QORE sovereign finance before MT5-QDLE ingestion.

No external capital can be manufactured by this adapter. QORE's authenticated
ledger must supply available, UNRESERVED cash in the correct source lane and
provider-rule risk headroom. HMAC provides integrity/authenticity of a locally
delivered event, not evidence that its numbers are economically correct.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from qore.infrastructure.qore_dynamic_lot_engine import QDLEError


@dataclass(frozen=True)
class QDLETreasuryEvent:
    account_id: str
    sequence: int
    observed_at: datetime
    qore_unreserved_risk_usd: Decimal
    qore_trading_capital_usd: Decimal
    sovereign_free_source_usd: Decimal
    cushion_free_source_usd: Decimal
    active_provider_mll_floor_usd: Decimal
    covered_fill_tickets: tuple[str, ...]
    ledger_receipt: str


def verify_treasury_hmac_event(
    envelope: dict, secret: bytes, *, now: datetime,
    expected_account_id: str, max_age_seconds: int = 10,
) -> QDLETreasuryEvent:
    if not isinstance(envelope, dict) or not isinstance(secret, bytes) or len(secret) < 32:
        raise QDLEError("signed treasury event and strong key required")
    payload = envelope.get("payload")
    tag = envelope.get("hmac_sha256")
    if not isinstance(payload, dict) or not isinstance(tag, str):
        raise QDLEError("missing QORE treasury signature")
    canonical = json.dumps(payload, sort_keys=True,
                           separators=(",", ":"), ensure_ascii=True).encode()
    expect = hmac.new(secret, canonical, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(tag, expect):
        raise QDLEError("QORE sovereign treasury signature mismatch")
    try:
        account_id = payload["account_id"]
        sequence = int(payload["sequence"])
        when = datetime.fromisoformat(payload["observed_at"])
        values = [Decimal(str(payload[k])) for k in (
            "qore_unreserved_risk_usd",
            "qore_trading_capital_usd",
            "sovereign_free_source_usd",
            "cushion_free_source_usd",
            "active_provider_mll_floor_usd",
        )]
        covered = tuple(str(ticket) for ticket in payload["covered_fill_tickets"])
        receipt = str(payload["ledger_receipt"])
    except (KeyError, TypeError, ValueError) as exc:
        raise QDLEError("invalid QORE treasury payload") from exc
    if account_id != expected_account_id or sequence <= 0 or not receipt:
        raise QDLEError("treasury account, sequence or receipt invalid")
    if (when.tzinfo is None or now.tzinfo is None or
        not timedelta() <= now - when <= timedelta(seconds=max_age_seconds)):
        raise QDLEError("stale or future-dated treasury receipt")
    if any(not val.is_finite() or val < 0 for val in values):
        raise QDLEError("treasury has negative/invalid economic source")
    if len(covered) != len(set(covered)):
        raise QDLEError("repeated covered broker position ticket")
    return QDLETreasuryEvent(
        account_id=account_id, sequence=sequence, observed_at=when,
        qore_unreserved_risk_usd=values[0],
        qore_trading_capital_usd=values[1],
        sovereign_free_source_usd=values[2],
        cushion_free_source_usd=values[3],
        active_provider_mll_floor_usd=values[4],
        covered_fill_tickets=covered,
        ledger_receipt=receipt,
    )
