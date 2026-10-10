#!/usr/bin/env python3
"""Research-only 3368-intent QDLE replay with dual capital ledgers.

Pinned burned 2019-2022 research opportunity source, NO MT5 broker fills.
Broker USD2000 initial margin; proprietary QORE NAV USD60 initial, 5% risk.
Observed 2026 MT5 mobile margin/symbol grids are STATIC COST PROXIES, not
historical provider conditions. Structural R outcome consumed ONLY at exit.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
from datetime import timedelta
from dataclasses import replace
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal as D
from pathlib import Path

from qore.infrastructure.cibo_account_sizing_authority import propose_p0_sizing_vote
from qore.infrastructure.cibo_compound_capital import propose_p0_compound_vote
from qore.infrastructure.cibo_marginal_leverage_utility import propose_p0_adaptive_leverage_vote
from qore.infrastructure.cibo_core_compound_portfolio import propose_p0_portfolio_vote
from qore.infrastructure.cibo_four_motor_policy import FourMotorObservation, ReconciledQoreCashflow
from qore.infrastructure.cibo_four_motor_qdle_proposal import build_four_motor_qdle_intent
from qore.infrastructure.cibo_native_sovereign_qdle import apply_native_qdle_risk_cap
from qore.infrastructure.qdle_stellar_instant_costs import LEGACY_REPLAY_PROXY, MODELS, estimate_per_lot_fees
from qore.infrastructure.qdle_cibo_authority import CiboEconomicInstruction, build_cibo_directed_qdle_intent, audit_cibo_qdle_lotage
from qore.infrastructure.cibo_trader_signal_administration import (
    TraderSignalIntake, EconomicStopBudget, propose_received_trader_management,
)
from qore.infrastructure.qore_dynamic_lot_engine import (
    BrokerValuation, Position, QDLE, QDLEAccount, QDLEError, QDLEIntent, QDLESymbol,
)

ZERO = D("0")
FIVE = D("0.05")
START_QORE = D("60")
START_BROKER = D("2000")
# Screenshot fields, not broker-historical order_calc_margin().
CONTRACTS = {"AUDJPY": D("100000"), "EURUSD": D("100000"),
             "GBPJPY": D("100000"), "GBPUSD": D("100000"),
             "XAUUSD": D("100"), "NDX100": D("10")}
MARGINS = {
    "AUDJPY": {"BUY": D("2318.93"), "SELL": D("2318.67")},
    "EURUSD": {"BUY": D("3735.03"), "SELL": D("3734.77")},
    "GBPJPY": {"BUY": D("4407.40"), "SELL": D("4407.40")},
    "GBPUSD": {"BUY": D("4407.63"), "SELL": D("4407.63")},
    "XAUUSD": {"BUY": D("53637.48"), "SELL": D("53629.68")},
    "NDX100": {"BUY": D("61481.98"), "SELL": D("61478.78")},
}
TICKS = {"AUDJPY": D(".001"), "EURUSD": D(".00001"),
         "GBPJPY": D(".001"), "GBPUSD": D(".00001"),
         "XAUUSD": D(".01"), "NDX100": D(".01")}
PROFIT = {"AUDJPY": "JPY", "GBPJPY": "JPY", "EURUSD": "USD",
          "GBPUSD": "USD", "XAUUSD": "USD", "NDX100": "USD"}
# Swap points and triple-rollover day transcribed from mobile MT5 (2026).
# RESEARCH UTC midnight proxy ONLY: historical rate/server rollover not known.
SWAP = {
    "AUDJPY": {"BUY": D("-11.27"), "SELL": D("-19.841")},
    "EURUSD": {"BUY": D("-13.472"), "SELL": D("0.107")},
    "GBPJPY": {"BUY": D("-25.806"), "SELL": D("-44.278")},
    "GBPUSD": {"BUY": D("-17.13"), "SELL": D("-2.977")},
    "XAUUSD": {"BUY": D("-107.151"), "SELL": D("-46.917")},
    "NDX100": {"BUY": D("-372.912"), "SELL": D("-57.6")},
}
SWAP_TRIPLE_WEEKDAY = {"NDX100": 4, "XAUUSD": 2,
                        "AUDJPY": 2, "EURUSD": 2, "GBPJPY": 2, "GBPUSD": 2}
TICK_VALUES_PER_LOT_USD = {"XAUUSD": D("1"), "NDX100": D("0.10")}


def utc_midnight_swap_proxy(trade: dict, exit_at: datetime) -> D:
    # Count rollovers on the previous UTC weekday. An MT5 server may
    # have a different rollover clock, so this MUST NOT imply real swaps.
    day = trade["opened_at"].date()
    last = exit_at.date()
    swaps = ZERO
    while day < last:
        multiple = 3 if day.weekday() == SWAP_TRIPLE_WEEKDAY[trade["symbol"]] else 1
        swaps += trade["lots"] * trade["swap_usd_per_lot"] * multiple
        day += timedelta(days=1)
    return swaps


class HistoricalProxy:
    """Immutable decision-time research proxy. Never calls MT5 order_send."""
    def __init__(self) -> None:
        self.quote: BrokerValuation | None = None

    def value(self, instrument: QDLESymbol, intent: QDLEIntent, now: datetime) -> BrokerValuation:
        if self.quote is None or self.quote.as_of != now:
            raise QDLEError("MISSING_DECISION_TIME_RESEARCH_VALUATION")
        return self.quote

    def check_volume(self, instrument: QDLESymbol, intent: QDLEIntent, lots: D) -> None:
        if not (instrument.min_lot <= lots <= instrument.max_lot):
            raise QDLEError("RESEARCH_VOLUME_NOT_ON_BROKER_GRID")
        if lots % instrument.lot_step:
            raise QDLEError("RESEARCH_VOLUME_OFF_BROKER_GRID")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--motor-policy", choices=["shared_proxy", "independent_four_motors"], default="shared_proxy")
    p.add_argument("--target-lots", type=D, default=None, help="Optional maximum broker lots requested, never additional risk authorization")
    p.add_argument("--cibo-instructions", type=Path, default=None,
                   help="CIBO-authorized bank/cushion and per-signal budget; never synthesized")
    p.add_argument("--experimental-native-ceiling-report", type=Path, default=None,
                   help="CEO research: Native MAX causal approval projected to new 5pct QDLE physical NAV, NOT original strategy PnL")
    p.add_argument("--experimental-native-lane-policy", choices=["all_bank", "split_30_30_alternate"], default="all_bank",
                   help="Hypothetical Bank/Cushion scenario only; NOT actual native CIBO fund allocation")
    p.add_argument("--ndx-roundtrip-fee-proxy-usd-per-lot", type=D, default=None,
                   help="Legacy NDX fee scenario; Stellar Instant published index fee is zero")
    p.add_argument("--fee-model", choices=MODELS, default=LEGACY_REPLAY_PROXY,
                   help="Published Stellar tariff vs old model; not evidence of account-specific historical fees")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--min-policy", choices=["original_trader", "broker_grid"], default="original_trader")
    p.add_argument("--native-max-management-advisories", type=Path, default=None,
                   help="Pinned 3368 original Native MAX cognitive receipts mapped to PAPER CIBO exit-management modes (NEVER admissions).")
    p.add_argument("--experimental-paper-bypass-strategy-caps", action="store_true",
                   help="PAPER-ONLY research ablation: bypass Sizing/Compound/Leverage/Portfolio discretionary caps for all signals, while QDLE retains 5pct NAV, real volume grid, broker margin, actual source and fees. NO LIVE or real fills.")
    p.add_argument("--experimental-cibo-administrator", action="store_true",
                   help="CEO CIBO manager: re-quote economic SL physically via QDLE for EVERY Trader signal. Changed-stop lots are quote-only, NEVER settled with old Trader R.")
    p.add_argument("--swap-proxy", choices=["off", "utc_midnight"], default="utc_midnight")
    p.add_argument("--provider-trailing-usd", type=str, default="120",
                   help="USD loss threshold sensitivity; disabled = provider rule NOT modeled")
    args = p.parse_args()
    if args.experimental_cibo_administrator and (
        args.motor_policy != "independent_four_motors"
        or args.cibo_instructions is not None
        or args.experimental_native_ceiling_report is not None
        or args.min_policy != "broker_grid"
    ):
        raise SystemExit("CEO CIBO administrator requires four-motor broker-grid research without legacy admission gate")
    if args.experimental_paper_bypass_strategy_caps and (
        not args.experimental_cibo_administrator
        or args.motor_policy != "independent_four_motors"
        or args.cibo_instructions is not None
        or args.experimental_native_ceiling_report is not None
        or args.min_policy != "broker_grid"
        or args.provider_trailing_usd != "disabled"
    ):
        raise SystemExit("PAPER-ONLY strategy ablation requires manager+four-motor broker-grid and provider proxy disabled; cannot target LIVE or original CIBO.")
    if args.native_max_management_advisories is not None and (
        not args.experimental_cibo_administrator
        or args.cibo_instructions is not None
        or args.experimental_native_ceiling_report is not None
        or args.motor_policy != "independent_four_motors"
        or args.min_policy != "broker_grid"
    ):
        raise SystemExit("Native MAX management is a PAPER predecision advisory, never a pretrade veto or LIVE signal.")
    if args.target_lots is not None and (not args.target_lots.is_finite() or args.target_lots <= ZERO):
        raise SystemExit("Invalid target lots")
    if args.fee_model != LEGACY_REPLAY_PROXY and args.motor_policy != "independent_four_motors":
        raise SystemExit("Stellar fee scenarios require independent four-motor policy")
    if args.fee_model == LEGACY_REPLAY_PROXY and args.motor_policy == "independent_four_motors" and (
        args.ndx_roundtrip_fee_proxy_usd_per_lot is None
        or not args.ndx_roundtrip_fee_proxy_usd_per_lot.is_finite()
        or args.ndx_roundtrip_fee_proxy_usd_per_lot < ZERO
    ):
        raise SystemExit("Legacy model requires explicit NDX assumption")
    if args.fee_model != LEGACY_REPLAY_PROXY and args.ndx_roundtrip_fee_proxy_usd_per_lot not in (None, ZERO):
        raise SystemExit("Cannot mix old NDX assumption with Stellar published fee scenario")
    provider_limit = None if args.provider_trailing_usd == "disabled" else D(args.provider_trailing_usd)
    if provider_limit is not None and provider_limit <= 0:
        raise SystemExit("Invalid trailing USD model")
    raw = json.loads(args.manifest.read_text(encoding="utf-8"))
    opportunities = raw["opportunities"]
    if len(opportunities) != 3368 or len({x["signal_fingerprint"] for x in opportunities}) != 3368:
        raise SystemExit("FAIL CLOSED: 3368 unique original signals required")
    native_management_by_signal = None
    native_management_modes = Counter()
    native_mode_instructions_consumed = 0
    native_mode_qdle_quotes = Counter()
    native_mode_qdle_unfundable = Counter()
    native_shadow_only = args.native_max_management_advisories is not None
    # No executable bid/ask price trajectories in the sealed Trader manifest.
    # Native cognitive management may QUOTE but cannot settle Trader CONTROL R.
    if args.native_max_management_advisories is not None:
        advisory = json.loads(args.native_max_management_advisories.read_text(encoding="utf-8"))
        receipt_rows = advisory.get("receipts")
        if (advisory.get("schema") != "qore.cibo.p0.native-max-3368-received-manager-advisory.v1"
            or advisory.get("admission_gate_applied") is not False
            or not isinstance(receipt_rows, list) or len(receipt_rows) != 3368
            or advisory.get("cognitive_intelligence_receipts_consumed") != 3368):
            raise SystemExit("Native MAX 3368 management source untrusted, cannot proceed")
        native_management_by_signal = {x["signal_fingerprint"]: x for x in receipt_rows}
        if len(native_management_by_signal) != 3368 or set(native_management_by_signal) != {
            x["signal_fingerprint"] for x in opportunities
        }:
            raise SystemExit("Native MAX 3368 management fingerprints missing or duplicate")
        for opportunity in opportunities:
            a = native_management_by_signal[opportunity["signal_fingerprint"]]
            if (a.get("trader_id") != opportunity["trader_id"]
                or a.get("decided_at") != opportunity["market_decision_at"]
                or a.get("native_max_cognition_read") is not True
                or a.get("admission_gate_applied") is not False
                or a.get("manager_mode_SHADOW_from_native_cognitive_sensors") not in (
                    "BANK", "MEDIUM", "ATTACK"
                ) or a.get("manager_cognitive_sensor_evidence_SHADOW", {}).get(
                    "native_disposition_used_for_policy") is not False
                or a.get("manager_cognitive_sensor_evidence_SHADOW", {}).get(
                    "producer") not in (
                        "CIBO_NATIVE_MAX_SOVEREIGN_MODE_QDLE_PAPER",
                        "P0_DETERMINISTIC_SENSOR_DERIVED_RESEARCH_ADAPTER_NOT_NATIVE_BROKER_AUTHORIZATION",
                    )
                ):
                raise SystemExit("Native MAX management causal sensor/trader clock mismatch")
            if advisory.get("source") == "FRESH_NATIVE_MAX_REPLAY_3368_SAME_SEALED_TRADER_INPUT":
                if (a.get("native_cibo_mode_instruction_issued") is not True
                    or a.get("bank_medium_attack_request_qdle_physical_lotage") is not True
                    or not str(a.get("native_cibo_mode_instruction_sha256", "")).startswith("sha256:")):
                    raise SystemExit("Native runtime did not issue BANK/MEDIUM/ATTACK QDLE instruction")
            if a.get("native_cibo_mode_instruction_issued") is True:
                native_mode_instructions_consumed += 1
            fraction = D(str(a.get("manager_risk_fraction_of_nav_SHADOW", "NaN")))
            if not fraction.is_finite() or not ZERO < fraction <= FIVE:
                raise SystemExit("Native MAX paper risk fraction violates 5pct all-in cap")
            native_management_modes[a["manager_mode_SHADOW_from_native_cognitive_sensors"]] += 1
    if any(opportunities[i]["market_decision_at"] > opportunities[i + 1]["market_decision_at"]
           for i in range(len(opportunities) - 1)):
        raise SystemExit("FAIL CLOSED: sealed opportunity order not chronological")

    if args.experimental_native_ceiling_report is not None and (
        args.cibo_instructions is not None or args.motor_policy != "independent_four_motors"
    ):
        raise SystemExit("FAIL CLOSED: experimental native CIBO requires four motors and excludes explicit CIBO directions")
    native_decisions_by_signal = None
    cibo_by_signal = None
    cibo_declared_provenance = None
    cibo_managed_outcomes = {}
    lane_cash = None
    transfer_events = []
    if args.experimental_native_ceiling_report is not None:
        native = json.loads(args.experimental_native_ceiling_report.read_text(encoding="utf-8"))
        if native.get("governance", {}).get("certification_claimed") is not False:
            raise SystemExit("FAIL CLOSED: native source must be noncertifying research")
        native_rows = native.get("decision_receipts")
        signals = {x["signal_fingerprint"] for x in opportunities}
        if (not isinstance(native_rows, list) or len(native_rows) != 3368
            or {x.get("signal_fingerprint") for x in native_rows} != signals):
            raise SystemExit("FAIL CLOSED: exact 3368 Native CIBO decision identities needed")
        native_decisions_by_signal = {x["signal_fingerprint"]: x for x in native_rows}
        if len(native_decisions_by_signal) != 3368:
            raise SystemExit("FAIL CLOSED: duplicate Native CIBO signal")
        for row in opportunities:
            n = native_decisions_by_signal[row["signal_fingerprint"]]
            decision_time = datetime.fromisoformat(str(n["decided_at"]))
            first_entry = datetime.fromisoformat(str(row["settlement_outcome_research_only"]["entry_at"]))
            if (n["trader_id"] != row["trader_id"]
                or decision_time.tzinfo is None or decision_time > first_entry
                or D(str(n["authorized_volume"])) < ZERO
                or D(str(n["authorized_stop_risk_usd"])) < ZERO
                or (D(str(n["authorized_volume"])) == ZERO and D(str(n["authorized_stop_risk_usd"])) > ZERO)
                or not str(n["semantic_digest"]).startswith("sha256:")
                or len(str(n["semantic_digest"])) != 71):
                raise SystemExit("FAIL CLOSED: native CIBO approval/chronology/trader contract invalid")
        lane_cash = ({"SOVEREIGN_BANK": START_QORE, "PORTFOLIO_CUSHION": ZERO}
                     if args.experimental_native_lane_policy == "all_bank"
                     else {"SOVEREIGN_BANK": D("30"), "PORTFOLIO_CUSHION": D("30")})
        cibo_declared_provenance = "EXPERIMENTAL_NATIVE_CIBO_PREDECISION_GATE_WITH_SIMULATED_ENTRY_NAV_AND_DECLARED_LANE_POLICY"
    if args.cibo_instructions:
        if args.motor_policy != "independent_four_motors":
            raise SystemExit("CIBO instructions require independent four-motor policy")
        authority = json.loads(args.cibo_instructions.read_text(encoding="utf-8"))
        if authority.get("schema") != "qore.cibo.qdle-authoritative-economic-input.v1":
            raise SystemExit("FAIL CLOSED: canonical CIBO economic instructions required")
        instructions = authority.get("instructions")
        source_ids = {row["signal_fingerprint"] for row in opportunities}
        if (not isinstance(instructions, list) or len(instructions) != len(opportunities)
            or any(not isinstance(x, dict) or not x.get("signal_id") for x in instructions)
            or {x["signal_id"] for x in instructions} != source_ids
            or len({x["signal_id"] for x in instructions}) != len(opportunities)):
            raise SystemExit("FAIL CLOSED: missing, duplicated or foreign CIBO instructions")
        cibo_by_signal = {x["signal_id"]: x for x in instructions}
        cibo_declared_provenance = authority.get("provenance", "CIBO_EXTERNAL_RESEARCH_INPUT_NOT_BROKER_AUTHENTICATED")
        if not isinstance(cibo_declared_provenance, str) or not cibo_declared_provenance.strip():
            raise SystemExit("FAIL CLOSED: CIBO source provenance declaration required")
        settlements = authority.get("managed_settlement_receipts", [])
        if not isinstance(settlements, list) or any(
            not isinstance(x, dict) or not x.get("signal_id")
            or x["signal_id"] not in source_ids for x in settlements
        ):
            raise SystemExit("FAIL CLOSED: invalid CIBO managed settlement list")
        if len({x["signal_id"] for x in settlements}) != len(settlements):
            raise SystemExit("FAIL CLOSED: duplicate CIBO management settlement")
        cibo_managed_outcomes = {x["signal_id"]: x for x in settlements}
        # A hypothetical funded operation cannot quietly inherit the
        # Trader's structural historical R if CIBO did not supply its managed
        # exit. Do NOT use outcome amount when deciding budget or volume.
        for instruction in instructions:
            if D(str(instruction["authorized_all_in_risk_usd"])) > ZERO:
                if instruction["signal_id"] not in cibo_managed_outcomes:
                    raise SystemExit("FAIL CLOSED: CIBO authorizes risk without its management settlement")
        for exit_receipt in settlements:
            try:
                final_at = datetime.fromisoformat(str(exit_receipt["exit_at"]))
                r_value = D(str(exit_receipt["gross_outcome_r"]))
                evidence = str(exit_receipt["evidence_sha256"])
                if (final_at.tzinfo is None or final_at.utcoffset() is None
                    or not r_value.is_finite() or len(evidence) != 71
                    or not evidence.startswith("sha256:")):
                    raise ValueError("managed exit chronology/rate/evidence invalid")
            except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
                raise SystemExit("FAIL CLOSED: managed exit incomplete: " + str(exc)) from exc
        try:
            lane_cash = {
                "SOVEREIGN_BANK": D(str(authority["initial_bank_usd"])),
                "PORTFOLIO_CUSHION": D(str(authority["initial_cushion_usd"])),
            }
            if (any(not x.is_finite() or x < ZERO for x in lane_cash.values())
                or sum(lane_cash.values()) != START_QORE):
                raise ValueError("CIBO bank+cushion must equal USD60")
            transfer_events = authority.get("capital_transfers", [])
            if not isinstance(transfer_events, list):
                raise ValueError("capital_transfers must be list")
            transfer_events = sorted(transfer_events, key=lambda x: x["at"])
            for tx in transfer_events:
                if (tx.get("from_lane") not in lane_cash
                    or tx.get("to_lane") not in lane_cash
                    or tx["from_lane"] == tx["to_lane"]
                    or not str(tx.get("evidence_sha256", "")).startswith("sha256:")
                    or len(str(tx["evidence_sha256"])) != 71
                    or not D(str(tx["usd"])).is_finite()
                    or D(str(tx["usd"])) <= ZERO):
                    raise ValueError("invalid CIBO transfer receipt")
        except (ValueError, KeyError, TypeError, ArithmeticError) as err:
            raise SystemExit("FAIL CLOSED: CIBO cash or transfer: " + str(err)) from err

    nav = START_QORE
    peak_nav = nav
    broker_peak = START_BROKER
    realized_gains = ZERO
    wins = ZERO
    losses = ZERO
    peak_to_trough = ZERO
    maximum_absolute_dd = ZERO
    max_dd_ratio = ZERO
    active: dict[str, dict] = {}
    exits: list[tuple[datetime, str]] = []
    source_counts = Counter()
    rejection_binding_counts = Counter()
    module_binding_ties = Counter()
    module_summed_limits_usd = defaultdict(lambda: ZERO)
    module_audit_present = Counter()
    sym_counts: dict[str, Counter] = defaultdict(Counter)
    total_cost = ZERO
    entry_commission_paid = ZERO
    closing_commission_paid = ZERO
    recent_settlements: list[tuple[datetime, str, D]] = []
    swap_pnl = ZERO
    rollover_count = 0
    realized_count = 0
    provider_floor_breach = 0
    provider_closed_at = None
    unresolved_at_breach = 0
    decisions = []
    last_spec_time: dict[str, datetime] = {}
    cibo_transfers_applied = 0
    cibo_directions_consumed = 0
    cibo_managed_exit_receipts_consumed = 0
    manager_actions = Counter()
    manager_qdle_quoted = 0
    manager_changed_stop_quoted = 0
    manager_qdle_quoted_lots = ZERO
    manager_funded_with_original_stop = 0
    manager_requoted_ids: list[str] = []
    last_account_snapshot: QDLEAccount | None = None
    last_symbol_snapshot: QDLESymbol | None = None
    symbol_snapshots: dict[str, QDLESymbol] = {}

    with tempfile.TemporaryDirectory() as t:
        broker = HistoricalProxy()
        research_tmpdir = t  # do not reuse loop-local Trader dict named t
        qdle = QDLE(Path(research_tmpdir) / "qdle_3368_sealed.sqlite", broker)
        sequence = 0
        def apply_cibo_transfers(at: datetime) -> None:
            nonlocal cibo_transfers_applied
            if lane_cash is None:
                return
            while cibo_transfers_applied < len(transfer_events):
                tx = transfer_events[cibo_transfers_applied]
                when = datetime.fromisoformat(tx["at"])
                if when > at:
                    break
                debit, credit, amount = tx["from_lane"], tx["to_lane"], D(str(tx["usd"]))
                reserved = sum((v["planned_risk"] for v in active.values()
                                if v["source_lane"] == debit), ZERO)
                if lane_cash[debit] - reserved < amount:
                    raise QDLEError("CIBO_TRANSFER_UNBACKED_OR_ALREADY_RESERVED")
                lane_cash[debit] -= amount
                lane_cash[credit] += amount
                cibo_transfers_applied += 1

        def publish(at: datetime) -> None:
            nonlocal sequence, broker_peak, provider_floor_breach, last_account_snapshot
            sequence += 1
            broker_equity = START_BROKER + nav - START_QORE
            broker_peak = max(broker_peak, broker_equity)
            # Sensitivity proxy ONLY, not independently verified account rules.
            assumed_floor = broker_peak - provider_limit if provider_limit is not None else ZERO
            headroom = max(ZERO, broker_equity - assumed_floor)
            if provider_limit is not None and broker_equity <= assumed_floor:
                provider_floor_breach += 1
            open_risk = sum((x["planned_risk"] for x in active.values()), ZERO)
            open_margin = sum((x["margin"] for x in active.values()), ZERO)
            available_qore = max(ZERO, nav - open_risk)
            if lane_cash is not None:
                apply_cibo_transfers(at)
                if any(balance < ZERO for balance in lane_cash.values()):
                    raise QDLEError("CIBO_SOURCE_LANE_INSOLVENT_NO_AUTOMATIC_BANK_BAILOUT")
                if abs(sum(lane_cash.values()) - nav) > D("0.00000001"):
                    raise QDLEError("CIBO_SOURCE_LEDGER_DIVERGES_FROM_QORE_NAV")
                free_bank = max(ZERO, lane_cash["SOVEREIGN_BANK"] -
                    sum((v["planned_risk"] for v in active.values()
                         if v["source_lane"] == "SOVEREIGN_BANK"), ZERO))
                free_cushion = max(ZERO, lane_cash["PORTFOLIO_CUSHION"] -
                    sum((v["planned_risk"] for v in active.values()
                         if v["source_lane"] == "PORTFOLIO_CUSHION"), ZERO))
            else:
                free_bank, free_cushion = available_qore, ZERO
            broker_free_margin = max(ZERO, broker_equity - open_margin)
            last_account_snapshot = QDLEAccount(
                account_id="SEALED_RESEARCH_2000", provider="FundedNext", currency="USD",
                sequence=sequence, as_of=at,
                balance=max(ZERO, broker_equity), equity=max(ZERO, broker_equity),
                free_margin=broker_free_margin,
                qore_unreserved_risk_usd=min(available_qore, headroom),
                sovereign_free_source_usd=free_bank,
                cushion_free_source_usd=free_cushion,
                qore_trading_capital_usd=max(ZERO, nav),
                positions=tuple(Position(k, v["symbol"], v["side"], v["lots"])
                                for k, v in sorted(active.items())),
                covered_fill_tickets=tuple(sorted(active)),
            )
            qdle.publish_account(last_account_snapshot)
        def settle_until(at: datetime) -> None:
            nonlocal nav, peak_nav, max_dd_ratio, maximum_absolute_dd
            nonlocal provider_closed_at, unresolved_at_breach
            nonlocal realized_count, total_cost, wins, losses, realized_gains
            nonlocal closing_commission_paid
            nonlocal swap_pnl, rollover_count
            if provider_closed_at is not None:
                return
            while exits and exits[0][0] <= at:
                when, ticket = heapq.heappop(exits)
                trade = active.pop(ticket)
                gross = trade["lots"] * trade["stop_per_lot"] * trade["r"]
                cost = trade["lots"] * trade["fee_per_lot"]
                swap = utc_midnight_swap_proxy(trade, when) if args.swap_proxy == "utc_midnight" else ZERO
                if swap != ZERO:
                    rollover_count += 1
                swap_pnl += swap
                pnl = gross - cost + swap
                trade["decision_event"].update(
                    realized_pnl_usd_proxy=str(pnl),
                    pnl_gross_usd_proxy=str(gross),
                    realized_exit_at=when.isoformat(),
                    swap_usd_proxy=str(swap),
                    commission_close_paid_usd_proxy=str(trade.get("deferred_close_fee", ZERO)),
                )
                realized_gains += pnl
                # Entry commission was already removed from NAV at hypothetical fill.
                nav += gross + swap - trade.get("deferred_close_fee", ZERO)
                if lane_cash is not None:
                    lane_cash[trade["source_lane"]] += gross + swap - trade.get("deferred_close_fee", ZERO)
                closing_commission_paid += trade.get("deferred_close_fee", ZERO)
                recent_settlements.append((when, ticket, pnl))
                wins += max(ZERO, pnl)
                losses += max(ZERO, -pnl)
                realized_count += 1
                peak_nav = max(peak_nav, nav)
                dd = max(ZERO, peak_nav - nav)
                maximum_absolute_dd = max(maximum_absolute_dd, dd)
                if peak_nav > 0:
                    max_dd_ratio = max(max_dd_ratio, dd / peak_nav)
                sym_counts[trade["symbol"]]["research_settlements"] += 1
                publish(when)
                if provider_limit is not None and START_BROKER + nav - START_QORE <= broker_peak - provider_limit:
                    provider_closed_at = when.isoformat()
                    unresolved_at_breach = len(active)
                    source_counts["PROVIDER_CLOSED_EQUITY_TRAILING_BREACH"] += 1
                    # Provider breach: stop accounting future hypothetical gains;
                    # actual forced-close PnL requires missing intratrade ticks.
                    return
                # synthetic lifecycle: NOT a verified broker ticket/deal.
                # Do not call record_broker_settlement: that method requires
                # authentic broker settlement receipts not present in source.

        # The original manifest orders decisions, not hypothetical fills.
        # Historical entry_at can lag a limit decision by >2 days.
        # Evaluate economic/margin capacity when a hypothetical entry would fill.
        chronological = sorted(enumerate(opportunities),
                               key=lambda x: (x[1]["settlement_outcome_research_only"]["entry_at"], x[0]))
        for index, row in chronological:
            at = datetime.fromisoformat(row["settlement_outcome_research_only"]["entry_at"])
            decision_at = datetime.fromisoformat(row["market_decision_at"])
            if provider_closed_at is None:
                settle_until(at)  # no PnL after provider shutdown; no future leakage.
            t = row["trader_opportunity"]
            symbol = "NDX100" if row["qore_symbol"] == "NAS100" else row["qore_symbol"]
            side = "BUY" if t["side"] == "long" else "SELL"
            entry, stop = D(t["intended_entry"]), D(t["stop_loss"])
            rid = row["signal_fingerprint"]
            event = {"index": index, "signal_fingerprint": rid, "at": at.isoformat(),
                     "signal_at": decision_at.isoformat(),
                     "research_entry_type": t["entry_type"],
                     "symbol": symbol, "trader": row["trader_id"],
                     "status": "UNFUNDABLE", "lots": "0"}
            sym_counts[symbol]["original_signals"] += 1
            if native_management_by_signal is not None:
                native_advice = native_management_by_signal[rid]
                event["cibo_max_native_cognition_consumed"] = True
                event["cibo_max_native_semantic_digest"] = native_advice["native_max_semantic_digest"]
                event["cibo_max_native_legacy_reason_observation_only"] = native_advice[
                    "native_legacy_capital_disposition_for_diagnostics_only"
                ]
                event["cibo_max_native_calibration_note"] = native_advice["native_max_calibration_note"]
                event["cibo_max_native_management_mode"] = native_advice[
                    "manager_mode_SHADOW_from_native_cognitive_sensors"
                ]
                event["cibo_max_native_proposed_exit_management"] = native_advice["manager_exit_policy_SHADOW"]
                event["cibo_max_native_requested_risk_fraction_of_nav"] = native_advice[
                    "manager_risk_fraction_of_nav_SHADOW"
                ]
                event["cibo_max_native_management_source"] = native_advice[
                    "manager_cognitive_sensor_evidence_SHADOW"]["producer"]
                event["cibo_max_native_cashflow_provenance"] = "NO_CIBO_MANAGED_SETTLEMENT_EVIDENCE"
                event["trader_control_settlements_allowed_to_fund_manager"] = False
                event["cibo_max_native_exit_policy_executed"] = False
                event["cibo_max_native_trade_admission_gate_used"] = False
            if provider_closed_at is not None:
                event["status"] = "BLOCKED_AFTER_PROVIDER_LIMIT"
                event["reason"] = "PROVIDER_TRAILING_LIMIT_TRIGGERED_CLOSED_EQUITY_PROXY"
                decisions.append(event)
                sym_counts[symbol]["unfundable"] += 1
                source_counts["BLOCKED_AFTER_PROVIDER_LIMIT"] += 1
                continue
            publish(at)
            try:
                if entry <= 0 or stop <= 0:
                    raise QDLEError("INVALID_HISTORICAL_ENTRY_OR_STOP")
                if (side == "BUY" and stop >= entry) or (side == "SELL" and stop <= entry):
                    raise QDLEError("INVALID_DIRECTIONAL_STOP")
                if nav <= 0:
                    raise QDLEError("QORE_PROPRIETARY_NAV_EXHAUSTED")
                # FXJPY uses USD-per-lot proxy captured in original research
                # manifest; EUR/GBPUSD recompute from USD quote; XAU/NDX
                # contract economics come from user screenshots.
                stop_per_lot = (
                    abs(entry - stop) * CONTRACTS[symbol] if symbol in
                    {"EURUSD", "GBPUSD", "XAUUSD", "NDX100"}
                    else D(t["stop_loss_per_volume"])
                )
                if stop_per_lot <= 0:
                    raise QDLEError("INVALID_RESEARCH_STOP_VALUATION")
                # Explicit OPEN/CLOSE tariff per symbol, never falsely marked MT5-verified.
                if args.motor_policy == "independent_four_motors":
                    tariff = estimate_per_lot_fees(
                        symbol, entry_price=entry, contract_size=CONTRACTS[symbol],
                        model=args.fee_model,
                        legacy_ndx_fee_usd=args.ndx_roundtrip_fee_proxy_usd_per_lot,
                    )
                    opening_fee, closing_fee = tariff.opening_usd, tariff.closing_usd
                    fee_source = tariff.fee_evidence
                else:
                    opening_fee = (
                        D("7") if symbol in {"AUDJPY", "GBPJPY", "GBPUSD", "EURUSD"}
                        else D("0.000016") * CONTRACTS[symbol] * entry
                        if symbol == "XAUUSD" else ZERO
                    )
                    closing_fee = ZERO
                    fee_source = "SHARED_LEGACY_RESEARCH_ENTRY_ONLY_PROXY"
                fee = opening_fee + closing_fee
                event["fee_model"] = args.fee_model
                event["fee_source"] = fee_source
                event["commission_open_estimated_usd_per_lot"] = str(opening_fee)
                event["commission_close_estimated_usd_per_lot"] = str(closing_fee)
                event["commission_actual_account_verified"] = False
                # CEO MANAGER, NOT SELECTOR: record a valid CIBO management
                # action for every Trader signal, and use DYNAMIC entry-time
                # NAV and independent remaining risk source to propose a
                # protective economic stop. This is RESEARCH ONLY.
                manager_revised_stop = False
                manager_original_stop = stop
                if args.experimental_cibo_administrator:
                    signal = TraderSignalIntake(
                        signal_fingerprint=rid, trader_id=row["trader_id"],
                        symbol=symbol, side=side, entry_price=entry,
                        structural_stop_price=stop,
                        take_profit_price=D(str(t["take_profit"])),
                        decided_at=decision_at,
                        trader_evidence_sha256="sha256:" + hashlib.sha256(
                            (rid + "|SEALED_TRADER_MANIFEST").encode()
                        ).hexdigest(),
                    )
                    source_free = max(ZERO, nav - sum(
                        (x["planned_risk"] for x in active.values()), ZERO
                    ))
                    valuation_per_price = stop_per_lot / abs(entry - stop)
                    receipt = propose_received_trader_management(
                        signal=signal,
                        budget=EconomicStopBudget(
                            qore_reconciled_nav_usd=max(ZERO,nav),
                            cibo_max_loss_usd=max(ZERO,nav)*FIVE,
                            source_unreserved_loss_capacity_usd=source_free,
                            broker_min_lot=D(".01"),broker_lot_step=D(".01"),
                            tick_size_price=TICKS[symbol],
                            # Historical provider min-stops unverified.
                            broker_min_stop_distance_price=ZERO,
                            price_loss_usd_per_price_unit_per_lot=valuation_per_price,
                            opening_commission_usd_per_lot=opening_fee,
                            closing_commission_usd_per_lot=closing_fee,
                            execution_buffer_usd_per_lot=ZERO,
                            broker_data_as_of=decision_at,
                            price_valuation_evidence_sha256="sha256:"+hashlib.sha256(
                                (rid+"|DECISION_TIME_PROXY_MARGIN_PRICE").encode()
                            ).hexdigest(),
                        ),
                    )
                    manager_action = receipt.reason_codes[0]
                    manager_actions[manager_action] += 1
                    event["cibo_manager_status"] = receipt.status
                    event["cibo_manager_action"] = manager_action
                    event["cibo_manager_stop_original"] = str(manager_original_stop)
                    event["cibo_manager_stop_proposed"] = (
                        str(receipt.proposed_protective_stop_price)
                        if receipt.proposed_protective_stop_price is not None else None
                    )
                    event["cibo_manager_budget_dynamic_usd"] = str(receipt.budget_usd)
                    event["cibo_manager_received"] = True
                    if receipt.proposed_protective_stop_price is not None:
                        stop = receipt.proposed_protective_stop_price
                        stop_per_lot = abs(entry - stop) * valuation_per_price
                        manager_revised_stop = stop != manager_original_stop
                    else:
                        # No viable protective stop; CIBO does not reject the
                        # signal, but cannot request an unsafe physical lot.
                        event["status"] = "RECEIVED_UNFUNDABLE_CIBO_NO_SAFE_STOP"
                        event["reason"] = manager_action
                        event["lots"] = "0"
                        decisions.append(event)
                        sym_counts[symbol]["unfundable"] += 1
                        sym_counts[symbol]["manager_no_safe_stop"] += 1
                        source_counts[manager_action] += 1
                        continue
                if at > last_spec_time.get(symbol, datetime.min.replace(tzinfo=at.tzinfo)):
                    last_symbol_snapshot = QDLESymbol(
                        broker_symbol=symbol, aliases=(symbol, "NAS100") if symbol == "NDX100" else (symbol,),
                        min_lot=D(".01"), max_lot=D("50") if symbol == "XAUUSD" else D("40"),
                        lot_step=D(".01"), directional_volume_limit=ZERO,
                        tick_size=TICKS[symbol], tick_value_loss_usd=D("1"),
                        contract_size=CONTRACTS[symbol], currency_profit=PROFIT[symbol],
                        # Price-dependent XAU costs travel as a per-entry extra
                        # allowance below; fixed FX/NDX fees live in broker spec.
                        fee_usd_per_lot=(fee if args.motor_policy == "independent_four_motors"
                                         and symbol != "XAUUSD" else ZERO),
                        fee_provenance="SCENARIO_COST_PROXY_UNVERIFIED",
                        as_of=at, tradable=True,
                    )
                    qdle.publish_symbol(last_symbol_snapshot)
                    symbol_snapshots[symbol] = last_symbol_snapshot
                    last_spec_time[symbol] = at
                broker.quote = BrokerValuation(
                    stop_per_lot, MARGINS[symbol][side], at, "SCREENSHOT_2026_STATIC_MARGIN_RESEARCH_PROXY",
                )
                risk_budget = max(ZERO, nav) * FIVE
                free_qore = max(ZERO, nav - sum((x["planned_risk"] for x in active.values()), ZERO))
                free_broker = max(ZERO, START_BROKER + nav - START_QORE -
                                  sum((x["margin"] for x in active.values()), ZERO))
                limit_lots = D("40") if symbol != "XAUUSD" else D("50")
                policy_min = D(t["minimum_volume"]) * D(t.get("minimum_execution_steps", 1))
                if args.min_policy == "broker_grid":
                    policy_min = D(".01")
                event["stop_loss_usd_per_lot"] = str(stop_per_lot)
                event["commission_roundtrip_proxy_per_lot"] = str(fee) if args.motor_policy == "independent_four_motors" else None
                event["commission_entry_usd_per_lot_proxy"] = str(opening_fee)
                if args.motor_policy == "independent_four_motors":
                    cibo = None
                    if cibo_by_signal is not None:
                        raw_cibo = cibo_by_signal[rid]
                        cibo = CiboEconomicInstruction(
                            signal_id=str(raw_cibo["signal_id"]),
                            trader_id=str(raw_cibo["trader_id"]),
                            symbol=str(raw_cibo["symbol"]),
                            side=str(raw_cibo["side"]),
                            entry_price=D(str(raw_cibo["entry_price"])),
                            stop_price=D(str(raw_cibo["stop_price"])),
                            source_lane=str(raw_cibo["source_lane"]),
                            allocated_source_funds_usd=D(str(raw_cibo["allocated_source_funds_usd"])),
                            authorized_all_in_risk_usd=D(str(raw_cibo["authorized_all_in_risk_usd"])),
                            maximum_requested_lots=(D(str(raw_cibo["maximum_requested_lots"]))
                                if raw_cibo.get("maximum_requested_lots") is not None else None),
                            account_sequence=int(raw_cibo["account_sequence"]),
                            issued_at=datetime.fromisoformat(str(raw_cibo["issued_at"])),
                            evidence_sha256=str(raw_cibo["evidence_sha256"]),
                        )
                        if (cibo.trader_id != row["trader_id"]
                            or cibo.symbol != symbol or cibo.side != side
                            or cibo.entry_price != entry or cibo.stop_price != stop):
                            raise QDLEError("CIBO_IDENTITY_OR_GEOMETRY_DRIFT")
                    elif native_decisions_by_signal is not None:
                        n = native_decisions_by_signal[rid]
                        # Only Native CIBO's causal allow/risk budget is consumed here.
                        # Research lane, entry-time NAV, broker fees and historic
                        # Trader structural exits are DECLARED counterfactuals.
                        native_approval = D(str(n["authorized_volume"])) > ZERO
                        native_cap = D(str(n["authorized_stop_risk_usd"])) if native_approval else ZERO
                        research_risk = min(native_cap, max(ZERO, nav) * FIVE)
                        lane = ("SOVEREIGN_BANK"
                                if args.experimental_native_lane_policy == "all_bank"
                                or index % 2 == 0 else "PORTFOLIO_CUSHION")
                        lane_held = sum((v["planned_risk"] for v in active.values()
                                         if v["source_lane"] == lane), ZERO)
                        backing = max(ZERO, lane_cash[lane] - lane_held)
                        cibo = CiboEconomicInstruction(
                            signal_id=rid, trader_id=row["trader_id"], symbol=symbol,
                            side=side, entry_price=entry, stop_price=stop,
                            source_lane=lane, allocated_source_funds_usd=backing,
                            authorized_all_in_risk_usd=research_risk,
                            maximum_requested_lots=None, account_sequence=sequence,
                            issued_at=at, evidence_sha256=str(n["semantic_digest"]),
                        )
                        event["native_cibo_risk_decision"] = n["risk_decision"]
                        event["native_cibo_authorized_volume_abstract"] = str(n["authorized_volume"])
                        event["native_cibo_authorized_stop_risk_usd"] = str(native_cap)
                        event["native_cibo_decided_at"] = n["decided_at"]
                        event["native_cibo_semantic_digest"] = n["semantic_digest"]
                        event["cibo_lane_model"] = "EXPERIMENTAL_UNVERIFIED_" + args.experimental_native_lane_policy
                        event["cibo_budget_recomputed_on_simulated_entry_epoch"] = True
                    open_stop = sum((x["planned_risk"] for x in active.values()), ZERO)
                    open_margin = sum((x["margin"] for x in active.values()), ZERO)
                    same_symbol_stop = sum((x["planned_risk"] for x in active.values()
                                            if x["symbol"] == symbol), ZERO)
                    same_trader_stop = sum((x["planned_risk"] for x in active.values()
                                            if x.get("trader") == row["trader_id"]), ZERO)
                    same_direction = sum((x["lots"] for x in active.values()
                                          if x["symbol"] == symbol and x["side"] == side), ZERO)
                    # Simulated cashbook is NOT a broker settlement statement.
                    # For Native MAX, NO synthetic CONTROL settlement can be
                    # used to invent managed NAV or a three-loss streak.
                    if native_shadow_only and (recent_settlements or nav != START_QORE):
                        raise QDLEError("NATIVE_CIBO_NAV_CONTAMINATED_BY_TRADER_CONTROL")
                    digest = "sha256:" + hashlib.sha256(
                        (rid + at.isoformat() + str(nav) + str(fee)).encode()
                    ).hexdigest()
                    # Keep 3 most recent completed trade settlements distinct,
                    # so Compound's three-loss defense can really activate.
                    # Aggregate earlier cashflows + already debited opening fees
                    # in a prior synthetic cashbook receipt without inventing profit.
                    recent = recent_settlements[-3:]
                    previous_amount = nav - START_QORE - sum(
                        (v for _, _, v in recent), ZERO
                    )
                    prior_time = (recent[0][0] - timedelta(microseconds=1)
                                  if recent else at)
                    simulated_flows = (
                        ((ReconciledQoreCashflow(
                            "REPLAY_PRIOR_CASHBOOK:" + rid, prior_time,
                            previous_amount, digest, True),)
                         if previous_amount != ZERO else ())
                        + tuple(ReconciledQoreCashflow(
                            "REPLAY_SETTLED:" + trade_id, completed_at,
                            net, digest, True,
                        ) for completed_at, trade_id, net in recent)
                    )
                    obs = FourMotorObservation(
                        request_id=rid, trader_id=row["trader_id"], symbol=symbol, side=side,
                        source_lane=cibo.source_lane if cibo is not None else "SOVEREIGN_BANK", observed_at=at,
                        account_sequence=sequence, broker_evidence_sha256=digest,
                        initial_qore_nav_usd=START_QORE, reconciled_cashflows=simulated_flows,
                        protected_capital_usd=ZERO, floating_loss_reserve_usd=ZERO,
                        risk_reservations_usd=open_stop,
                        bank_unreserved_usd=(
                            max(ZERO, lane_cash["SOVEREIGN_BANK"] -
                                sum((x["planned_risk"] for x in active.values()
                                     if x["source_lane"] == "SOVEREIGN_BANK"), ZERO))
                            if lane_cash is not None else free_qore),
                        cushion_unreserved_usd=(
                            max(ZERO, lane_cash["PORTFOLIO_CUSHION"] -
                                sum((x["planned_risk"] for x in active.values()
                                     if x["source_lane"] == "PORTFOLIO_CUSHION"), ZERO))
                            if lane_cash is not None else ZERO),
                        total_open_stop_risk_usd=open_stop,
                        correlated_open_stop_risk_usd=same_symbol_stop,
                        trader_open_stop_risk_usd=same_trader_stop,
                        broker_free_margin_usd=START_BROKER + nav - START_QORE,
                        broker_margin_reservations_usd=open_margin,
                        stop_loss_usd_per_lot=stop_per_lot,
                        roundtrip_fees_usd_per_lot=fee,
                        execution_buffer_usd_per_lot=ZERO,
                        stress_extra_loss_usd_per_lot=ZERO,
                        broker_margin_usd_per_lot=MARGINS[symbol][side],
                        symbol_max_lots=limit_lots, provider_direction_max_lots=limit_lots,
                        open_and_reserved_direction_lots=same_direction,
                        broker_quote_at=at, broker_fees_complete=True,
                        broker_profit_valuation_complete=True,
                        broker_margin_valuation_complete=True,
                    )
                    votes = (propose_p0_sizing_vote(obs),
                             propose_p0_compound_vote(obs),
                             propose_p0_adaptive_leverage_vote(obs),
                             propose_p0_portfolio_vote(obs))
                    if cibo is not None:
                        requested = build_cibo_directed_qdle_intent(
                            cibo=cibo, observation=obs, votes=votes,
                            methodology_min_lots=policy_min,
                        )
                        cibo_directions_consumed += 1
                        event["cibo_source_lane"] = cibo.source_lane
                        event["cibo_source_allocation_usd"] = str(cibo.allocated_source_funds_usd)
                        event["cibo_authorized_risk_usd"] = str(cibo.authorized_all_in_risk_usd)
                        event["cibo_evidence_sha256"] = cibo.evidence_sha256
                    else:
                        requested = build_four_motor_qdle_intent(
                            observation=obs, votes=votes, entry_price=entry,
                            stop_price=stop, methodology_min_lots=policy_min,
                            requested_target_lots=args.target_lots,
                        )
                    # XAU percent fee is price-dependent in this sensitivity,
                    # carried through QDLE's per-entry buffer. FX fees in Symbol.
                    if symbol == "XAUUSD":
                        requested = replace(requested, slippage_usd_per_lot=fee)
                    event["four_engine_reason_codes"] = {
                        v.producer: list(v.reason_codes) for v in votes
                    }
                    event["four_engine_caps_usd"] = {
                        "SIZING": votes[0].limits["approved_risk_usd"],
                        "CIBO_COMPOUND": votes[1].limits["approved_risk_usd"],
                        "PORTFOLIO_COMPOUND_AVAILABLE_SOURCE": votes[3].limits["approved_source_funds_usd"],
                    }
                    event["leverage_margin_budget_usd"] = votes[2].limits["approved_margin_usd"]
                    event["leverage_max_lots"] = votes[2].limits["approved_max_lots"]
                else:
                    event["four_engine_caps_usd"] = {
                        "SIZING": str(risk_budget),
                        "CIBO_COMPOUND": str(risk_budget),
                        "PORTFOLIO_COMPOUND_AVAILABLE_SOURCE": str(free_qore),
                    }
                    event["leverage_margin_budget_usd"] = str(free_broker)
                    event["leverage_max_lots"] = str(limit_lots)
                    requested = QDLEIntent(
                        request_id=rid, trader_id=row["trader_id"], symbol=symbol, side=side,
                        entry_price=entry, stop_price=stop,
                        requested_risk_usd=risk_budget, sizing_cap_usd=risk_budget,
                        cibo_compound_cap_usd=risk_budget,
                        portfolio_cap_usd=free_qore,
                        leverage_cap_lots=limit_lots,
                        margin_cap_usd=free_broker,
                        source_lane="SOVEREIGN_BANK",
                        slippage_usd_per_lot=fee, expected_account_sequence=sequence,
                        methodology_min_lots=policy_min,
                    )
                if args.experimental_paper_bypass_strategy_caps:
                    # PAPER-ONLY bypass discretionary recommendations: physical
                    # QDLE nevertheless enforces risk <= 5pct NAV (as well as
                    # broker grid, fees and available source/margin). Never
                    # alter QDLEIntent authority or remove the LIVE guards.
                    event["four_engine_caps_before_research_bypass"] = dict(
                        event["four_engine_caps_usd"]
                    )
                    event["strategy_policy_ablation"] = "RESEARCH_ONLY_ALL_FOUR_STRATEGY_VOTES_BYPASSED"
                    requested = replace(
                        requested,
                        requested_risk_usd=risk_budget,
                        sizing_cap_usd=risk_budget,
                        cibo_compound_cap_usd=risk_budget,
                        portfolio_cap_usd=free_qore,
                        leverage_cap_lots=limit_lots,
                        margin_cap_usd=free_broker,
                    )
                    event["cibo_paper_bypass_applied"] = True
                if native_shadow_only:
                    # Economic intent actually depends on causal MAX sensor output.
                    # Upstream 4 motors still vote; 5% NAV remains the ceiling.
                    # NO legacy disposition or Trader settlement drives this cap.
                    cognitive_cap = max(ZERO, nav) * D(
                        native_management_by_signal[rid]["manager_risk_fraction_of_nav_SHADOW"]
                    )
                    requested = apply_native_qdle_risk_cap(
                        intent=requested,
                        qore_nav_usd=max(ZERO, nav),
                        native_plan=native_management_by_signal[rid][
                            "manager_cognitive_sensor_evidence_SHADOW"
                        ],
                    )
                    event["cibo_max_native_economic_budget_requested_usd"] = str(cognitive_cap)
                    event["cibo_max_native_economic_budget_applied_to_qdle"] = True
                if args.target_lots is not None and args.motor_policy != "independent_four_motors":
                    requested = replace(requested, requested_target_lots=args.target_lots)
                for label, value in event["four_engine_caps_usd"].items():
                    module_summed_limits_usd[label] += D(value)
                    module_audit_present[label] += 1
                module_audit_present["ADAPTIVE_LEVERAGE"] += 1
                if args.experimental_cibo_administrator and (manager_revised_stop or native_shadow_only):
                    # Independent ephemeral QDLE instance: its HOLD is a
                    # physical **RESEARCH QUOTE** only, not a broker rejected
                    # or filled trade. Never contaminate the original-stop
                    # account ledger or invent a no-fill broker receipt.
                    quote_qdle = QDLE(Path(research_tmpdir) / ("manager-quote-" + str(index) + ".sqlite"), broker)
                    if last_account_snapshot is None or last_symbol_snapshot is None:
                        raise QDLEError("MANAGER_QUOTE_MISSING_CAUSAL_ACCOUNT_SPEC")
                    quote_qdle.publish_account(last_account_snapshot)
                    quote_qdle.publish_symbol(symbol_snapshots[symbol])
                    result = quote_qdle.reserve_for_trader(requested, now=at)
                else:
                    result = qdle.reserve_for_trader(requested, now=at)
                if cibo_by_signal is not None or native_decisions_by_signal is not None:
                    receipt = audit_cibo_qdle_lotage(
                        cibo=cibo, observation=obs, votes=votes, result=result,
                        broker_min_lot=D(".01"), broker_lot_step=D(".01"),
                    )
                    event["cibo_qdle_audit"] = {
                        "decision_state": receipt.decision_state,
                        "source_lane": receipt.source_lane,
                        "trader_id": receipt.trader_id,
                        "entry_price": str(receipt.entry_price),
                        "stop_price": str(receipt.stop_price),
                        "qore_nav_usd": str(receipt.qore_nav_usd),
                        "five_percent_max_usd": str(receipt.sovereign_5pct_ceiling_usd),
                        "cibo_authorized_risk_usd": str(receipt.cibo_risk_budget_usd),
                        "cibo_allocated_working_capital_usd": str(receipt.cibo_allocated_funds_usd),
                        "lots": str(receipt.lots),
                        "stop_loss_usd": str(receipt.stop_loss_usd),
                        "roundtrip_cost_reserved_usd": str(receipt.total_roundtrip_cost_usd),
                        "all_in_risk_reserved_usd": str(receipt.all_in_risk_usd),
                        "margin_usd": str(receipt.broker_margin_usd),
                        "binding_reason_codes": list(receipt.reason_codes),
                        "account_sequence": receipt.account_sequence,
                        "cibo_source_evidence_sha256": receipt.cibo_source_evidence_sha256,
                        "broker_source_evidence_sha256": receipt.broker_source_evidence_sha256,
                        "real_mt5_fill_proven": receipt.real_mt5_fill_proven,
                    }
                event.update(status=result.state, lots=str(result.lots),
                             bound_modules=list(result.binding_limits),
                             fees_entry_usd_proxy=str(result.cost_usd),
                             commission_roundtrip_reserved_usd_proxy=str(result.cost_usd),
                             commission_open_reserved_usd_proxy=str(result.lots * opening_fee),
                             commission_close_reserved_usd_proxy=str(result.lots * closing_fee),
                             commission_open_paid_usd_proxy="0",
                             planned_stop_usd=str(result.total_risk_usd),
                             margin_usd=str(result.margin_usd),
                             risk_budget_usd=str(risk_budget),
                             nav_at_decision_usd=str(nav))
                if result.lots > 0:
                    for bound in result.binding_limits:
                        module_binding_ties[bound] += 1
                if args.experimental_cibo_administrator and (manager_revised_stop or native_shadow_only) and result.lots > 0:
                    # Native management NEVER takes the Trader CONTROL outcome
                    # even when its economic stop equals the original stop:
                    # cognitive partials/trailing/defense change the outcome.
                    manager_qdle_quoted += 1
                    if native_shadow_only:
                        native_mode_qdle_quotes[
                            native_management_by_signal[rid]["manager_mode_SHADOW_from_native_cognitive_sensors"]
                        ] += 1
                    manager_qdle_quoted_lots += result.lots
                    if manager_revised_stop:
                        manager_changed_stop_quoted += 1
                        manager_requoted_ids.append(rid)
                    event["status"] = ("CIBO_NATIVE_COGNITIVE_QDLE_QUOTE_SHADOW"
                                       if native_shadow_only else "ECONOMIC_STOP_QDLE_PHYSICAL_QUOTE_SHADOW")
                    event["cibo_manager_action"] = "COGNITIVE_MANAGEMENT_AND_QDLE_QUOTE" if native_shadow_only else "ECONOMIC_STOP_AND_QDLE_QUOTE"
                    event["cibo_manager_exit_status"] = "NEEDS_CAUSAL_PRICE_PATH"
                    event["historical_structural_R_used_for_modified_stop"] = False
                    event["position_opened"] = False
                    event["opening_commission_debited"] = False
                    sym_counts[symbol]["manager_cognitive_qdle_quote_only"] += 1
                    if manager_revised_stop:
                        sym_counts[symbol]["manager_economic_sl_quote_only"] += 1
                    source_counts["CIBO_QDLE_QUOTE_NOT_HISTORICAL_FILL"] += 1
                elif result.lots == 0:
                    if native_shadow_only:
                        native_mode_qdle_unfundable[
                            native_management_by_signal[rid]["manager_mode_SHADOW_from_native_cognitive_sensors"]
                        ] += 1
                    primary_constraint = result.binding_limits[0] if result.binding_limits else "UNKNOWN_BROKER_GRID"
                    rejection_binding_counts[primary_constraint] += 1
                    event["reason"] = "BROKER_MINIMUM_UNFINANCEABLE_BY_" + primary_constraint
                    source_counts[event["reason"]] += 1
                    sym_counts[symbol]["unfundable"] += 1
                else:
                    if args.experimental_cibo_administrator:
                        manager_funded_with_original_stop += 1
                    if result.total_risk_usd > risk_budget or result.margin_usd > free_broker:
                        raise QDLEError("QDLE_INTERNAL_RISK_OR_MARGIN_BREACH")
                    # Research-only hypothetical fill at supplied structural entry,
                    # NEVER counts as broker-confirmed trade execution.
                    synthetic_ticket = "RESEARCH:" + rid
                    qdle.acknowledge_fill(rid, synthetic_ticket)
                    # Fee debited at entry, not at settlement: immediate QORE
                    # NAV and broker equity reduction feeds subsequent decisions.
                    # Broker-style simulated timing: opening fee at entry;
                    # closing fee ONLY at the modeled exit. QDLE pre-reserves
                    # the full two-leg cost before entry in both cases.
                    full_fee = result.lots * fee
                    entry_fee = result.lots * opening_fee
                    close_fee = result.lots * closing_fee
                    if entry_fee + close_fee != full_fee:
                        raise QDLEError("BROKER_FEE_OPEN_CLOSE_SPLIT_MISMATCH")
                    event["commission_open_paid_usd_proxy"] = str(entry_fee)
                    event["commission_close_committed_usd_proxy"] = str(close_fee)
                    nav -= entry_fee
                    if lane_cash is not None:
                        lane_cash[requested.source_lane] -= entry_fee
                    entry_commission_paid += entry_fee
                    total_cost += full_fee
                    peak_nav = max(peak_nav, nav)
                    dd_at_entry = max(ZERO, peak_nav - nav)
                    maximum_absolute_dd = max(maximum_absolute_dd, dd_at_entry)
                    if peak_nav > ZERO:
                        max_dd_ratio = max(max_dd_ratio, dd_at_entry / peak_nav)
                    if cibo_by_signal is not None:
                        managed = cibo_managed_outcomes[rid]
                        expiration = datetime.fromisoformat(str(managed["exit_at"]))
                        outcome_r = D(str(managed["gross_outcome_r"]))
                        event["cibo_managed_exit_evidence_sha256"] = managed["evidence_sha256"]
                        event["cibo_managed_exit_at"] = expiration.isoformat()
                        cibo_managed_exit_receipts_consumed += 1
                    else:
                        expiration = datetime.fromisoformat(row["settlement_outcome_research_only"]["exit_at"])
                        outcome_r = D(row["settlement_outcome_research_only"]["gross_structural_outcome_r"])
                        if native_decisions_by_signal is not None:
                            event["research_exit_source"] = "HISTORICAL_TRADER_STRUCTURAL_R_NOT_NATIVE_CIBO_MANAGED_EXIT"
                    if expiration < at:
                        raise QDLEError("HISTORICAL_EXIT_PRECEDES_DECISION")
                    # Tick values observed for metals/index; FX conversion
                    # from the historical research manifest loss-per-volume.
                    if symbol in TICK_VALUES_PER_LOT_USD:
                        usd_per_swap_point_per_lot = TICK_VALUES_PER_LOT_USD[symbol]
                    else:
                        usd_per_swap_point_per_lot = (
                            stop_per_lot * TICKS[symbol] / abs(entry - stop))
                    active[synthetic_ticket] = {
                        "decision_event": event,
                        "opened_at": at,
                        "swap_usd_per_lot": SWAP[symbol][side] * usd_per_swap_point_per_lot,
                        "symbol": symbol, "side": side, "trader": row["trader_id"], "lots": result.lots,
                        "margin": result.margin_usd, "planned_risk": result.total_risk_usd,
                        "source_lane": requested.source_lane,
                        "stop_per_lot": stop_per_lot, "fee_per_lot": fee,
                        "deferred_close_fee": close_fee,
                        "r": outcome_r,
                    }
                    publish(at)
                    qdle.reconcile_fill(rid)
                    heapq.heappush(exits, (expiration, synthetic_ticket))
                    if provider_limit is not None and START_BROKER + nav - START_QORE <= broker_peak - provider_limit:
                        provider_closed_at = at.isoformat()
                        unresolved_at_breach = len(active)
                        source_counts["PROVIDER_ENTRY_FEE_TRAILING_BREACH"] += 1
                    source_counts["RESEARCH_HYPOTHETICAL_FUNDED"] += 1
                    sym_counts[symbol]["research_financed"] += 1
            except (QDLEError, ValueError, KeyError) as exc:
                source_counts[str(exc)[:110]] += 1
                event["reason"] = str(exc)
                sym_counts[symbol]["unfundable"] += 1
            decisions.append(event)
            if (index + 1) % 500 == 0:
                print("QDLE_PROGRESS", index + 1, "NAV", str(nav), "active", len(active), flush=True)
        if provider_closed_at is None:
            settle_until(datetime.max.replace(tzinfo=at.tzinfo))
        # Restore original manifest index order in the independent audit output.
        decisions.sort(key=lambda x: x["index"])
        broker_end = START_BROKER + nav - START_QORE
        report = {
            "schema": "qore.qdle.3368.dual-capital-research.v1",
            "cibo_manager_experimental_activated": args.experimental_cibo_administrator,
            "experimental_paper_bypass_strategy_caps": args.experimental_paper_bypass_strategy_caps,
            "native_max_3368_cognitive_evidence_joined": native_management_by_signal is not None,
            "native_max_cognitive_evidence_receipts_joined": (
                len(native_management_by_signal) if native_management_by_signal is not None else 0
            ),
            "native_max_management_mode_counts": dict(sorted(native_management_modes.items())),
            "native_cibo_bank_medium_attack_instructions_consumed": native_mode_instructions_consumed,
            "native_cibo_modes_qdle_physically_quoted": dict(sorted(native_mode_qdle_quotes.items())),
            "native_cibo_modes_qdle_no_financeable_lot": dict(sorted(native_mode_qdle_unfundable.items())),
            "native_cibo_all_three_modes_pass_through_physical_qdle": (
                native_mode_instructions_consumed == len(opportunities)
                and sum(native_mode_qdle_quotes.values())
                + sum(native_mode_qdle_unfundable.values()) == len(opportunities)
            ),
            "native_max_cognitive_economic_intents_applied": len(native_management_by_signal) if native_shadow_only else 0,
            "native_max_all_qdle_quotes_nonsettling_without_price_path": native_shadow_only,
            "native_max_control_cashflows_excluded_from_manager_nav": native_shadow_only,
            "native_max_manager_nav_funded_from_proven_managed_settlements": False,
            "native_max_legacy_admission_filter_disabled": native_management_by_signal is not None,
            "native_max_real_managed_trade_exits_rebuilt": False,
            "native_max_management_plans_research_only": native_management_by_signal is not None,
            "research_policy_bypassed_four_voters": (
                ["SIZING", "CIBO_COMPOUND", "ADAPTIVE_LEVERAGE", "PORTFOLIO_COMPOUND"]
                if args.experimental_paper_bypass_strategy_caps else []
            ),
            "qdle_physical_and_5pct_caps_preserved": True,
            "paper_only_hard_no_live_gateway": True,
            "cibo_manager_actions": dict(manager_actions),
            "cibo_manager_economic_stop_qdle_quote_only": manager_changed_stop_quoted,
            "cibo_manager_native_policy_qdle_quote_only": manager_qdle_quoted if native_shadow_only else 0,
            "cibo_manager_original_stop_native_qdle_quote_only": (
                manager_qdle_quoted - manager_changed_stop_quoted if native_shadow_only else 0
            ),
            "cibo_manager_economic_stop_quoted_lots_not_filled": str(manager_qdle_quoted_lots),
            "cibo_manager_economic_stop_quoted_signal_ids": manager_requoted_ids,
            "cibo_manager_original_stop_historical_structural_proxy_funded": manager_funded_with_original_stop,
            "cibo_manager_full_real_strategy_NAV_USD": None if args.experimental_cibo_administrator else str(nav),
            "cibo_manager_full_real_strategy_PF": None,
            "cibo_manager_full_real_strategy_DD": None,
            "cibo_manager_synthetic_ledger_nav_not_performance": str(nav) if native_shadow_only else None,
            "cibo_manager_managed_exits_replayed": False,
            "cibo_manager_exit_path_missing": True if args.experimental_cibo_administrator else None,
            "cibo_manager_static_provider_stop_distance_assumed_zero": args.experimental_cibo_administrator,

            "certified": False,
            "broker_execution_proven": False,
            "real_fundednext_fills": 0,
            "physical_broker_MT5_probe_used": False,
            "source": "PINNED_WALK_FORWARD_MANIFEST_2019_2022_BURNED_RESEARCH",
            "risk_policy": "CONSTANT_5PCT_QORE_NAV_DYNAMIC_USD",
            "broker_initial_equity_usd": "2000",
            "qore_initial_capital_usd": "60",
            "historical_exposure_model": "STATIC_2026_SCREENSHOT_MARGIN_NOT_HISTORICAL_BROKER",
            "provider_loss_limit_model": ("RESEARCH_SENSITIVITY_TRAILING_" + str(provider_limit) + "_USD_NOT_VERIFIED") if provider_limit is not None else "NO_VERIFIED_PROVIDER_LIMIT_NOT_SIMULATED",
            "commission_model": (
                "FUNDEDNEXT_STELLAR_INSTANT_HELP_OPEN_ONLY__PUBLIC_TARIFF_UNVERIFIED_ACCOUNT"
                if args.fee_model == "stellar_instant_open_only" else
                "FUNDEDNEXT_GENERAL_RULES_PER_SIDE_RESEARCH_SENSITIVITY"
                if args.fee_model == "stellar_general_per_side" else
                "FOREX_7_OPEN_PLUS_7_CLOSE_PER_LOT__XAU_SYMMETRIC_2_LEG_NOTIONAL_PROXY__NDX_EXPLICIT_SENSITIVITY"
                if args.motor_policy == "independent_four_motors" else
                "FOREX_ENTRY_ONLY_7USD_LOT__XAU_NOTIONAL_PROXY__NDX_ZERO_UNKNOWN"
            ),
            "fee_model": args.fee_model,
            "broker_account_commission_verified": False,
            "fee_tariff_only_public_stellar_instant": args.fee_model != LEGACY_REPLAY_PROXY,
            "ndx_assumed_total_fee_usd_per_lot": (
                str(args.ndx_roundtrip_fee_proxy_usd_per_lot)
                if args.fee_model == LEGACY_REPLAY_PROXY and args.motor_policy == "independent_four_motors"
                else "0" if args.fee_model != LEGACY_REPLAY_PROXY else None
            ),
            "module_caps_provenance": ("SIMULATED_INDEPENDENT_FOUR_MOTOR_VOTES" if args.motor_policy == "independent_four_motors" else "PROXY_SHARED_5PCT_NOT_INDEPENDENT_MOTOR_DECISIONS"),
            "economic_motor_mode": args.motor_policy,
            "cibo_authority_mode": (
                "CIBO_EXPLICIT_DIRECTIVES" if cibo_by_signal is not None
                else "EXPERIMENTAL_NATIVE_CIBO_APPROVAL_GATE_QDLE_PHYSICAL_PROJECTION"
                if native_decisions_by_signal is not None
                else "NATIVE_SOVEREIGN_BANK_MEDIUM_ATTACK_INSTRUCTIONS_TO_QDLE_QUOTE_ONLY_NO_MANAGED_EXITS"
                if native_shadow_only and native_mode_instructions_consumed == 3368
                else "NATIVE_SENSOR_DERIVED_RESEARCH_QDLE_QUOTE_ONLY_NO_MANAGED_EXITS"
                if native_shadow_only
                else "NOT_CIBO_INTEGRATED_ECONOMIC_PROXIES"
            ),
            "native_cibo_cognitive_decisions_consumed": (
                len(native_decisions_by_signal)
                if native_decisions_by_signal is not None
                else native_mode_instructions_consumed
            ),
            "native_cibo_true_source_lanes_verified": False,
            "native_cibo_actual_management_settlements_verified": False,
            "experimental_native_lane_policy": (args.experimental_native_lane_policy
                                                if native_decisions_by_signal is not None else None),
            "cibo_instruction_provenance": cibo_declared_provenance,
            "cibo_management_broker_authenticated": False,
            "cibo_directives_consumed": cibo_directions_consumed,
            "cibo_exit_management_replayed": (
                cibo_by_signal is not None
                and cibo_managed_exit_receipts_consumed == sum(
                    x["research_financed"] for x in sym_counts.values())
                and cibo_managed_exit_receipts_consumed > 0
            ),
            "cibo_managed_exit_receipts_consumed": cibo_managed_exit_receipts_consumed,
            "cibo_capital_transfers_applied": cibo_transfers_applied,
            "cibo_source_balances_usd": {k: str(v) for k, v in lane_cash.items()} if lane_cash is not None else None,
            "requested_target_lots": str(args.target_lots) if args.target_lots is not None else None,
            "module_binding_ties_on_funded": dict(module_binding_ties),
            "module_audit_observations": dict(module_audit_present),
            "module_summed_approved_usd_not_disbursed": {k: str(v) for k,v in module_summed_limits_usd.items()},
            "module_pnl_attribution_usd": None,
            "pnl_model": (
                "NATIVE_COGNITIVE_POLICY_QUOTE_ONLY_NO_SETTLEMENT_NO_PNL"
                if native_shadow_only else
                "POST_EXIT_STRUCTURAL_R_TIMES_CAUSAL_STOP_LOSS_PROXY_MINUS_ENTRY_COST"
            ),
            "research_volume_policy": args.min_policy,
            "signal_count": len(opportunities),
            "unique_signal_count": len({x["signal_fingerprint"] for x in opportunities}),
            "research_financed_proposals": sum(v["research_financed"] for v in sym_counts.values()),
            "research_unfundable_or_invalid": sum(v["unfundable"] for v in sym_counts.values()),
            "settled_research_outcomes": realized_count,
            "open_at_end": len(active),
            "qore_ending_capital_usd": str(nav),
            "broker_ending_equity_usd": str(broker_end),
            "net_research_pnl_usd": None if native_shadow_only else str(nav - START_QORE),
            "settled_trade_net_pnl_excluding_open_fee_effect_usd": str(realized_gains),
            "provider_trailing_closed_equity_stop_at": provider_closed_at,
            "provider_unresolved_positions_at_stop": unresolved_at_breach,
            "provider_stopped": provider_closed_at is not None,
            "risk_revaluation_epoch": "HYPOTHETICAL_ENTRY_AT_NOT_SIGNAL_AT",
            "gross_wins_usd": str(wins),
            "gross_losses_usd": str(losses),
            "entry_cost_proxy_usd": str(total_cost),
            "roundtrip_total_commission_committed_proxy_usd": str(total_cost),
            "per_trade_fees_entry_usd_proxy_field_is_historical_compatibility": True,
            "per_trade_commission_open_and_close_fields_are_authoritative_research": True,
            "opening_commission_paid_proxy_usd": str(entry_commission_paid),
            "closing_commission_paid_proxy_usd": str(closing_commission_paid),
            "unsettled_future_close_fee_not_charged_usd": str(sum((x.get("deferred_close_fee", ZERO) for x in active.values()), ZERO)),
            "net_swap_pnl_utc_midnight_proxy_usd": str(swap_pnl),
            "swap_rollover_position_count_proxy": rollover_count,
            "swap_model": "SCREENSHOT_2026_POINTS_AT_UTC_MIDNIGHT_PROXY" if args.swap_proxy == "utc_midnight" else "OMITTED_NO_DATA",
            "profit_factor_proxy": None if native_shadow_only else str(wins / losses) if losses > 0 else None,
            "max_closed_equity_drawdown_usd": None if native_shadow_only else str(maximum_absolute_dd),
            "max_closed_equity_drawdown_pct": None if native_shadow_only else str(max_dd_ratio * 100),
            "intratrade_drawdown_measured": False,
            "provider_floor_proxy_breach_sample_count": provider_floor_breach,
            "by_symbol": {k: dict(v) for k, v in sorted(sym_counts.items())},
            "reasons": dict(source_counts.most_common()),
            "unfundable_binding_constraints": dict(rejection_binding_counts.most_common()),
            "decisions": decisions,
            "limitations": [
                "Not historical MT5 symbol/margin or account-specific fees",
                "USDJPY currency-conversion uses original manifest research risk proxy",
                "NDX100 replaces USTEC: contract/strategy equivalence not established",
                "Historical research entry_at used as hypothetical fill: no tick/path proof",
                "Broker stop triggered on sampled closed equity only; unresolved forced liquidation",
                "At stop, capital is mark from last settlement/fee, NOT liquidation cash",
                "Original limit-order fill/partial fills not reconstructed",
                "Broker actual deals/spreads/slippage/swaps not measured",
                "Swap rollover model uses UTC midnight and current screenshot points, NOT historical broker records",
                "Closed-equity-only DD understates possible intratrade DD",
                "Pnl from realized structural R after exit, not actual MT5 transactions",
                "Four-module decisions are research policies calculated on simulated cashflows/quotes, not authentic historical broker votes",
                "Independent 4-motor mode assumes fee completeness for RESEARCH ONLY; fake evidence must never be used for live authorization",
                ("CIBO economic instructions supplied and honored, but broker authenticity not proved"
                 if cibo_by_signal is not None else
                 "NATIVE CIBO APPROVAL used, but source lane/entry-time budget projected as a RESEARCH scenario"
                 if native_decisions_by_signal is not None else
                 "NO CIBO trade management or portfolio allocation instructions; economic cap proxy ONLY"),
                ("CIBO-supplied managed exit date and gross R dictate research settlement; no actual MT5 broker deal"
                 if cibo_managed_exit_receipts_consumed else
                 "No CIBO-managed exits; original historical structural R dictates settlement"),
                "No per-trader allocation receipts proved independently of the replay scenario",
                "Binding cap ties do NOT establish incremental independent module performance",
                "Research proxy is NOT a certified 36-month broker-financed backtest",
            ],
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True))
        print("QDLE_3368_REPORT_SUMMARY", json.dumps(
            {k: v for k, v in report.items() if k not in {"decisions", "limitations", "by_symbol", "reasons"}},
            sort_keys=True), flush=True)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
