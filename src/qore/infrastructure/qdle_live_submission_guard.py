"""Fail-closed LIVE gateway -> standalone QDLE one-shot reservation gate.

This is called by the existing FundedNext gateway AFTER final live tick, risk
and order_check but BEFORE any order_send and mutation ledger intent record.
QDLE's provider-authenticated IPC atomically transitions HELD -> SENDING.
It never creates/changes CIBO budgets and cannot send orders on its own.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlsplit

from qore.infrastructure.execution_boundary import ExecutionSubmission
from qore.infrastructure.fundednext_mt5 import (
    FundedNextMt5OrderPlan, Mt5ExecutionBlockedError,
)
from qore.infrastructure.order_intent import OrderSide


class QdleHttpPresendGate:
    def __init__(self, endpoint: str, provider_token: str, timeout_seconds: float = 2) -> None:
        url = urlsplit(endpoint)
        if (url.scheme != "http" or url.hostname != "127.0.0.1"
                or not url.port or url.path not in ("", "/")
                or url.username or url.password or url.query or url.fragment):
            raise Mt5ExecutionBlockedError("QDLE pre-send gate MUST use localhost HTTP")
        if len(provider_token) < 24 or timeout_seconds <= 0 or timeout_seconds > 5:
            raise Mt5ExecutionBlockedError("QDLE provider token or timeout invalid")
        self.endpoint = endpoint.rstrip("/")
        self.provider_token = provider_token
        self.timeout = timeout_seconds

    def assert_reserved(self, submission: ExecutionSubmission,
                        plan: FundedNextMt5OrderPlan, now: datetime) -> None:
        if not isinstance(submission, ExecutionSubmission):
            raise Mt5ExecutionBlockedError("missing canonical QORE submission")
        attrs = submission.authorized_intent.intent.metadata.attributes
        signal = attrs.get("signal-fingerprint")
        if not signal:
            raise Mt5ExecutionBlockedError("missing immutable QDLE signal identity")
        if attrs.get("risk-authorized-volume") != str(plan.volume):
            raise Mt5ExecutionBlockedError("QDLE volume differs from sovereign Risk")
        if plan.stop_loss is None:
            raise Mt5ExecutionBlockedError("no QDLE live stop")
        payload = dict(
            request_id=signal, provider_symbol=plan.provider_symbol,
            side="BUY" if plan.side is OrderSide.BUY else "SELL",
            lots=format(plan.volume, "f"),
            executable_entry=format(plan.effective_entry, "f"),
            stop_price=format(plan.stop_loss, "f"),
            at=now.isoformat(),
        )
        request = urllib.request.Request(
            self.endpoint + "/v1/pre-send-check",
            data=json.dumps(payload, sort_keys=True).encode("utf-8"),
            headers={
                "X-QDLE-Token": self.provider_token,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read(4096))
                if response.status != 200 or body.get("qdle_live_send_armed_once") is not True:
                    raise Mt5ExecutionBlockedError("QDLE did not arm this exact live lotage")
        except (OSError, ValueError, urllib.error.HTTPError) as exc:
            raise Mt5ExecutionBlockedError(
                "QDLE unreachable, refused or stale; NEVER call order_send"
            ) from exc
