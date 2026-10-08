"""QDLE loopback-only authenticated IPC API (no order submission capability).

The service exposes a stable trader-neutral request contract. Separate authority
tokens for Trader, QORE treasury and MT5 provider events prevent a Trader from
fabricating broker margin or the sovereign bank. The real deployment must use
protected environment secrets, localhost binding, and a trusted treasury feed.
"""
from __future__ import annotations

import hmac
import json
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

from qore.infrastructure.qore_dynamic_lot_engine import (
    Position, QDLE, QDLEAccount, QDLEError, QDLEIntent, QDLESymbol,
)


def _decimal(row, name: str) -> Decimal:
    return Decimal(str(row[name]))


def _intent(row: dict) -> QDLEIntent:
    return QDLEIntent(
        request_id=row["request_id"], trader_id=row["trader_id"],
        symbol=row["symbol"], side=row["side"],
        entry_price=_decimal(row, "entry_price"),
        stop_price=_decimal(row, "stop_price"),
        requested_risk_usd=_decimal(row, "requested_risk_usd"),
        sizing_cap_usd=_decimal(row, "sizing_cap_usd"),
        cibo_compound_cap_usd=_decimal(row, "cibo_compound_cap_usd"),
        portfolio_cap_usd=_decimal(row, "portfolio_cap_usd"),
        leverage_cap_lots=_decimal(row, "leverage_cap_lots"),
        margin_cap_usd=_decimal(row, "margin_cap_usd"),
        source_lane=row["source_lane"],
        slippage_usd_per_lot=_decimal(row, "slippage_usd_per_lot"),
        expected_account_sequence=int(row["expected_account_sequence"]),
            methodology_min_lots=Decimal(str(row.get("methodology_min_lots", "0"))),
                    )


def build_local_handler(engine: QDLE, *, trader_token: str,
                        treasury_token: str, provider_token: str):
    if not engine.enforce_finance_approval:
        raise QDLEError("production IPC requires sovereign four-engine approval enforcement")
    tokens = (trader_token, treasury_token, provider_token)
    if any(len(t) < 24 for t in tokens) or len(set(tokens)) != 3:
        raise QDLEError("three distinct high-entropy authority tokens required")

    class QDLEHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format, *args):
            # Do not log tokens or request bodies.
            return

        def _reply(self, status: int, payload: dict):
            raw = json.dumps(payload, default=str, sort_keys=True).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _authorized(self, expected: str) -> bool:
            return hmac.compare_digest(self.headers.get("X-QDLE-Token", ""), expected)

        def do_GET(self):
            if self.path != "/health":
                return self._reply(404, {"error": "unknown_endpoint"})
            if not self._authorized(trader_token):
                return self._reply(403, {"error": "unauthorized"})
            return self._reply(200, engine.health())

        def do_POST(self):
            permitted = {
                "/v1/reserve": trader_token,
                "/v1/finance-approval": treasury_token,
                "/v1/account-event": treasury_token,
                "/v1/symbol-event": provider_token,
                "/v1/fill": provider_token,
                "/v1/reject": provider_token,
                "/v1/settlement": provider_token,
                "/v1/reconcile": treasury_token,
            }
            expected = permitted.get(self.path)
            if expected is None:
                return self._reply(404, {"error": "unknown_endpoint"})
            if not self._authorized(expected):
                return self._reply(403, {"error": "unauthorized"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size <= 0 or size > 64_000:
                    raise QDLEError("invalid body size")
                row = json.loads(self.rfile.read(size))
                if not isinstance(row, dict):
                    raise QDLEError("JSON object required")
                if self.path == "/v1/reserve":
                    cmd = _intent(row)
                    response = asdict(engine.reserve_for_trader(cmd))
                elif self.path == "/v1/finance-approval":
                    cmd = _intent(row)
                    engine.publish_finance_approval(cmd, approved_at=datetime.fromisoformat(row["approved_at"]))
                    response = {"approval_recorded": True, "request_id": cmd.request_id}
                elif self.path == "/v1/account-event":
                    cmd = QDLEAccount(
                        account_id=row["account_id"], provider=row["provider"],
                        currency=row["currency"], sequence=int(row["sequence"]),
                        as_of=datetime.fromisoformat(row["as_of"]),
                        balance=_decimal(row, "balance"), equity=_decimal(row, "equity"),
                        free_margin=_decimal(row, "free_margin"),
                        qore_unreserved_risk_usd=_decimal(row, "qore_unreserved_risk_usd"),
                        sovereign_free_source_usd=_decimal(row, "sovereign_free_source_usd"),
                        cushion_free_source_usd=_decimal(row, "cushion_free_source_usd"),
                        positions=tuple(Position(p["ticket"], p["symbol"], p["side"],
                                                 _decimal(p, "lots"))
                                        for p in row.get("positions", [])),
                        covered_fill_tickets=tuple(row.get("covered_fill_tickets", [])),
                    )
                    engine.publish_account(cmd)
                    response = {"updated": True, "sequence": cmd.sequence}
                elif self.path == "/v1/symbol-event":
                    cmd = QDLESymbol(
                        broker_symbol=row["broker_symbol"], aliases=tuple(row["aliases"]),
                        min_lot=_decimal(row, "min_lot"),
                        max_lot=_decimal(row, "max_lot"),
                        lot_step=_decimal(row, "lot_step"),
                        directional_volume_limit=_decimal(row, "directional_volume_limit"),
                        tick_size=_decimal(row, "tick_size"),
                        tick_value_loss_usd=_decimal(row, "tick_value_loss_usd"),
                        contract_size=_decimal(row, "contract_size"),
                        currency_profit=row["currency_profit"],
                        fee_usd_per_lot=_decimal(row, "fee_usd_per_lot"),
                        fee_provenance=row["fee_provenance"],
                        as_of=datetime.fromisoformat(row["as_of"]),
                        tradable=bool(row["tradable"]),
                    )
                    engine.publish_symbol(cmd)
                    response = {"updated": True, "symbol": cmd.broker_symbol}
                elif self.path == "/v1/fill":
                    engine.acknowledge_fill(row["request_id"], row["broker_ticket"])
                    response = {"fill_held_until_qore_and_mt5_reconcile": True}
                elif self.path == "/v1/reject":
                    engine.confirm_rejection(row["request_id"], row["broker_rejection_ref"])
                    response = {"no_fill_confirmed": True}
                elif self.path == "/v1/settlement":
                    engine.record_broker_settlement(
                        row["request_id"], row["broker_ticket"], row["deal_receipt"],
                        _decimal(row, "realized_net_pnl_usd"))
                    response = {"settlement_telemetry_recorded": True}
                else:
                    engine.reconcile_fill(row["request_id"])
                    response = {"funded_position_absorbed": True}
                self._reply(200, response)
            except (QDLEError, ValueError, KeyError, TypeError) as exc:
                self._reply(409, {"error": type(exc).__name__, "details": str(exc)})
            except Exception:
                # No internal exception traceback, raw credentials or MT5 state to callers.
                self._reply(503, {"error": "service_unavailable_fail_closed"})
    return QDLEHandler


def serve_loopback(engine: QDLE, *, trader_token: str,
                   treasury_token: str, provider_token: str, port: int = 18761) -> None:
    handler = build_local_handler(engine, trader_token=trader_token,
                                  treasury_token=treasury_token,
                                  provider_token=provider_token)
    ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()
