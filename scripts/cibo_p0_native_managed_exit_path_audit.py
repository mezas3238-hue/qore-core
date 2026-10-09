"""P0 Native MAX managed-exit price-path JOIN for paper research.

Only complete causal executable bid/ask bar paths can yield shadow managed
outcomes. The result is NOT a global NAV ledger, a real fill, or MT5 evidence.
Uncovered original Trader signals and independent QDLE quotes are preserved.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.cibo_managed_exit_replay import (
    CiboExitPolicy, CiboManagedTrade, ExecutableOhlcBar,
    ManagedReplayError, replay_cibo_managed_position,
)


SCHEMA = "qore.cibo.native-max-executable-bars-research.v1"
QUOTE_STATUS = "CIBO_NATIVE_COGNITIVE_QDLE_QUOTE_SHADOW"
FIELDS = ("bid_open", "bid_high", "bid_low", "bid_close",
          "ask_open", "ask_high", "ask_low", "ask_close")


class ManagedPathEvidenceError(ValueError):
    pass


def _dict_unique(rows: list[dict], id_key: str) -> dict:
    if not isinstance(rows, list):
        raise ManagedPathEvidenceError("expected evidence list")
    out = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get(id_key), str):
            raise ManagedPathEvidenceError("missing evidence ID")
        if row[id_key] in out:
            raise ManagedPathEvidenceError("duplicate signal evidence")
        out[row[id_key]] = row
    return out


def _bars(data: list[dict]) -> tuple[ExecutableOhlcBar, ...]:
    if not isinstance(data, list):
        raise ManagedPathEvidenceError("bid/ask bar array required")
    try:
        return tuple(ExecutableOhlcBar(
            opened_at=datetime.fromisoformat(b["opened_at"]),
            closed_at=datetime.fromisoformat(b["closed_at"]),
            **{field: Decimal(str(b[field])) for field in FIELDS},
            evidence_sha256=b["evidence_sha256"],
        ) for b in data)
    except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
        raise ManagedPathEvidenceError("invalid executable path observation") from exc


def audit_native_managed_paths(
    manifest: dict, qdle_report: dict, price_paths: dict,
    *, expected_count: int = 3368,
) -> dict:
    """Causal P0 coverage audit. Zero new dollars credited to the manager NAV."""
    originals = _dict_unique(manifest["opportunities"], "signal_fingerprint")
    decisions = _dict_unique(qdle_report["decisions"], "signal_fingerprint")
    if len(originals) != expected_count or set(originals) != set(decisions):
        raise ManagedPathEvidenceError("sealed Trader/QDLE population mismatch")
    if (qdle_report.get("native_max_cognitive_economic_intents_applied") != expected_count
        or qdle_report.get("native_max_control_cashflows_excluded_from_manager_nav") is not True
        or qdle_report.get("real_fundednext_fills") != 0):
        raise ManagedPathEvidenceError("requires isolated Native MAX QDLE paper receipts")
    if price_paths.get("schema") != SCHEMA:
        raise ManagedPathEvidenceError("unrecognized executable price-path schema")
    if price_paths.get("source_type") not in (
        "BROKER_HISTORICAL_BID_ASK_RESEARCH_UNVERIFIED", "SYNTHETIC_TEST_FIXTURE"
    ):
        raise ManagedPathEvidenceError("source provenance must be explicit")
    source = price_paths.get("source_description")
    if not isinstance(source, str) or not source.strip():
        raise ManagedPathEvidenceError("price path source description required")
    provided = _dict_unique(price_paths.get("items"), "signal_fingerprint")
    if not set(provided) <= set(originals):
        raise ManagedPathEvidenceError("price paths include foreign Trader identity")
    rows = []
    status = Counter()
    shadow_subset_net = Decimal(0)
    for sid, origin in originals.items():
        decision = decisions[sid]
        lots = Decimal(str(decision.get("lots", "0")))
        if decision.get("status") != QUOTE_STATUS or lots <= 0:
            outcome = {"signal_fingerprint": sid, "status": "NOT_PHYSICALLY_QUOTED",
                       "broker_fills": 0, "global_manager_nav_credited": False}
            if sid in provided:
                raise ManagedPathEvidenceError("bars supplied for non-quoted signal")
        elif sid not in provided:
            outcome = {"signal_fingerprint": sid, "status": "MISSING_BID_ASK_PRICE_PATH",
                       "broker_fills": 0, "global_manager_nav_credited": False}
        else:
            feed = provided[sid]
            if feed.get("symbol") != decision["symbol"]:
                raise ManagedPathEvidenceError("executable path symbol mismatch")
            opportunity = origin["trader_opportunity"]
            entry = Decimal(str(opportunity["intended_entry"]))
            structure = Decimal(str(opportunity["stop_loss"]))
            economic = Decimal(str(decision["cibo_manager_stop_proposed"]))
            stop_usd_per_lot = Decimal(str(decision["stop_loss_usd_per_lot"]))
            unit_usd = stop_usd_per_lot / abs(entry - economic)
            fraction_cap = Decimal(str(
                decision["cibo_max_native_economic_budget_requested_usd"]
            ))
            nav_5pct = Decimal(str(decision["nav_at_decision_usd"])) * Decimal("0.05")
            trade = CiboManagedTrade(
                signal_id=sid, symbol=decision["symbol"],
                side="BUY" if opportunity["side"] == "long" else "SELL",
                entry_at=datetime.fromisoformat(decision["at"]),
                entry_price=entry, trader_structural_stop_price=structure,
                economic_stop_price=economic,
                trader_take_profit_price=Decimal(str(opportunity["take_profit"])),
                lots=lots, min_lot=Decimal("0.01"), lot_step=Decimal("0.01"),
                price_pnl_usd_per_lot_per_unit=unit_usd,
                roundtrip_commission_usd_per_lot=Decimal(str(
                    decision["commission_roundtrip_proxy_per_lot"]
                )),
                maximum_all_in_risk_usd=min(fraction_cap, nav_5pct),
            )
            policy = CiboExitPolicy(**{
                k: Decimal(str(v)) for k, v in
                decision["cibo_max_native_proposed_exit_management"].items()
            })
            result = replay_cibo_managed_position(trade, _bars(feed["bars"]), policy=policy)
            outcome = {
                "signal_fingerprint": sid, "status": result.status,
                "exit_at": result.exit_at.isoformat() if result.exit_at else None,
                "exit_reason": result.exit_reason,
                "gross_usd_research": str(result.gross_pnl_usd_proxy) if result.gross_pnl_usd_proxy is not None else None,
                "net_usd_research": str(result.net_pnl_usd_proxy) if result.net_pnl_usd_proxy is not None else None,
                "commission_usd_research": str(result.commission_usd_proxy) if result.commission_usd_proxy is not None else None,
                "partial_count": result.partial_count,
                "stop_update_count": result.stop_update_count,
                "defensive_count": result.defensive_trigger_count,
                "intratrade_worst_usd_research": str(result.intratrade_worst_pnl_usd_proxy) if result.intratrade_worst_pnl_usd_proxy is not None else None,
                "bars_consumed": result.bars_consumed,
                "actions": list(result.actions),
                "broker_fills": 0, "global_manager_nav_credited": False,
            }
            if result.status == "SHADOW_SETTLED":
                shadow_subset_net += result.net_pnl_usd_proxy
        status[outcome["status"]] += 1
        rows.append(outcome)
    return {
        "schema": "qore.cibo.native-max-managed-path-coverage-audit.v1",
        "certified": False, "real_mt5_fills": 0,
        "source_type": price_paths["source_type"],
        "source_description": source,
        "signal_count": len(originals),
        "native_qdle_quote_count": sum(d.get("status") == QUOTE_STATUS for d in decisions.values()),
        "price_paths_supplied": len(provided),
        "outcomes": dict(status),
        "shadow_subset_net_usd_research_only": str(shadow_subset_net),
        "global_manager_nav_usd": None,
        "global_manager_dd_and_pf": None,
        "not_global_portfolio_settlements": True,
        "missing_bars_are_never_filled_using_trader_structural_r": True,
        "decisions": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--qdle-report", type=Path, required=True)
    parser.add_argument("--executable-bars", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit_native_managed_paths(
        json.loads(args.manifest.read_text()),
        json.loads(args.qdle_report.read_text()),
        json.loads(args.executable_bars.read_text()),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("CIBO_MANAGED_PATH_COVERAGE", json.dumps({
        k: v for k, v in report.items() if k != "decisions"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
