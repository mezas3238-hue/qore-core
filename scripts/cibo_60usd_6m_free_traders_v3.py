"""Independent CIBO USD60 / six-month free-Trader capitalization experiment V3.

Purpose
-------
Measure the current CIBO account sizing architecture without adding any
opportunity-quality filter above the Traders.

All seven Trader lineages submit every valid retained Phase18 entry in the
measurement window.  The harness does not reject opportunities by expectation,
rank, identity, historical score, or custom loss envelope.

For every entry, the harness calls the current account-scoped CIBO sizing
authority directly:

    plan_account_sizing(...)

CIBO therefore decides SURVIVAL_MINIMAL_SEED vs PROTECTED_FULL_CAPACITY from
its own architecture.  The harness only supplies causal account facts:
- initial seed/economic capital,
- realized closed PnL,
- already reserved open stop risk,
- a non-binding normalized margin envelope because exact historical broker
  margin economics are not complete for all seven Phase18 lineages.

The historical trade rows are R-denominated.  To measure capital in USD
without fabricating broker contract economics, one normalized volume unit is
defined as exactly USD1 structural-stop risk.  Realized trade PnL is therefore:

    CIBO stop_risk_usd * observed structural R

This is research measurement only. It is not Phase20D/21/22 certification
evidence and it makes no exact historical broker-executability claim.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    derive_cibo_capital_mission,
    fundednext_stellar_instant_identity,
)
from qore.infrastructure.cibo_account_sizing_authority import (
    CiboAccountSizingMode,
    account_capital_state,
    plan_account_sizing,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)

getcontext().prec = 50

EXPERIMENT_ID = "CIBO_60USD_6M_FREE_TRADERS_CURRENT_ARCHITECTURE_V3"
INITIAL_SEED_USD = Decimal("60")
SURVIVAL_CAPITAL_USD = Decimal("60")
NORMALIZED_STOP_RISK_PER_VOLUME_USD = Decimal("1")
NORMALIZED_MARGIN_PER_VOLUME_USD = Decimal("0.000001")
NORMALIZED_MAXIMUM_VOLUME = Decimal("1e30")
NORMALIZED_MARGIN_HEADROOM_USD = Decimal("1e30")
DEFAULT_START = "2021-12-29T09:00:00+00:00"
DEFAULT_END = "2022-06-29T09:00:00+00:00"
MILESTONES_USD = (
    Decimal("300"),
    Decimal("1000"),
    Decimal("5000"),
    Decimal("10000"),
)


@dataclass(frozen=True, slots=True)
class SourceSpec:
    key: str
    trader_id: TraderLineage
    qore_symbol: str | None
    outcome_field: str


SOURCE_SPECS: tuple[SourceSpec, ...] = (
    SourceSpec("gbpjpy", TraderLineage.R38_GBPJPY, "GBPJPY", "raw_net_010_r"),
    SourceSpec("gbpusd", TraderLineage.R43_GBPUSD, "GBPUSD", "raw_net_010_r"),
    SourceSpec("audjpy", TraderLineage.R42_AUDJPY, "AUDJPY", "raw_net_010_r"),
    SourceSpec("eurusd", TraderLineage.R38_EURUSD, "EURUSD", "raw_net_010_r"),
    SourceSpec("xauusd", TraderLineage.R34_XAUUSD, "XAUUSD", "raw_net_010_r"),
    SourceSpec("vt08", TraderLineage.VT08_FOREX, None, "raw_outcome_r"),
    SourceSpec(
        "vt31",
        TraderLineage.VT31_NAS100,
        "NAS100",
        "legacy_vt31_net_r_per_requested_r",
    ),
)


@dataclass(frozen=True, slots=True)
class Trade:
    trader_id: TraderLineage
    symbol: str
    fingerprint: str
    side: str
    signal_at: datetime
    entry_at: datetime
    exit_at: datetime
    entry_price: Decimal
    structural_stop: Decimal
    technical_target: Decimal
    outcome_r: Decimal


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _money(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.000001")), "f")


def _days(start: datetime, at: datetime) -> str:
    return format(
        Decimal(str((at - start).total_seconds())) / Decimal("86400"),
        "f",
    )


def _fingerprint(
    *,
    spec: SourceSpec,
    row: dict[str, Any],
    source_index: int,
) -> str:
    payload = {
        "trader": spec.trader_id.value,
        "symbol": spec.qore_symbol or str(row["symbol"]),
        "signal_at": str(row["signal_at"]),
        "entry_at": str(row["entry_at"]),
        "exit_at": str(row["exit_at"]),
        "source_index": source_index,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _load_source(
    path: Path,
    *,
    spec: SourceSpec,
    start: datetime,
    end: datetime,
) -> list[Trade]:
    selected: list[Trade] = []
    for index, row in enumerate(_jsonl(path)):
        signal_at = datetime.fromisoformat(str(row["signal_at"]))
        entry_at = datetime.fromisoformat(str(row["entry_at"]))
        exit_at = datetime.fromisoformat(str(row["exit_at"]))
        for value in (signal_at, entry_at, exit_at):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("timestamps must be timezone-aware")
        if not signal_at <= entry_at < exit_at:
            raise ValueError(
                f"{spec.trader_id.value} chronology drift at source row {index}"
            )
        if entry_at < start or exit_at > end:
            continue

        side = str(row["side"]).lower()
        entry = Decimal(str(row["entry_price"]))
        stop = Decimal(str(row["structural_stop"]))
        target = Decimal(str(row["technical_target"]))
        if side == "long":
            valid_geometry = stop < entry < target
        elif side == "short":
            valid_geometry = target < entry < stop
        else:
            valid_geometry = False
        if not valid_geometry:
            raise ValueError(
                f"{spec.trader_id.value} invalid geometry at source row {index}"
            )

        outcome = Decimal(str(row[spec.outcome_field]))
        if not outcome.is_finite():
            raise ValueError(
                f"{spec.trader_id.value} non-finite R at source row {index}"
            )

        selected.append(
            Trade(
                trader_id=spec.trader_id,
                symbol=spec.qore_symbol or str(row["symbol"]),
                fingerprint=_fingerprint(
                    spec=spec,
                    row=row,
                    source_index=index,
                ),
                side=side,
                signal_at=signal_at,
                entry_at=entry_at,
                exit_at=exit_at,
                entry_price=entry,
                structural_stop=stop,
                technical_target=target,
                outcome_r=outcome,
            )
        )
    return selected


def _opportunity(trade: Trade) -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=trade.trader_id,
        signal_fingerprint=trade.fingerprint,
        qore_symbol=trade.symbol,
        provider_symbol=f"NORMALIZED:{trade.symbol}",
        side=trade.side,
        entry_type="historical_normalized_replay",
        intended_entry=trade.entry_price,
        stop_loss=trade.structural_stop,
        take_profit=trade.technical_target,
        stop_loss_per_volume=NORMALIZED_STOP_RISK_PER_VOLUME_USD,
        margin_per_volume=NORMALIZED_MARGIN_PER_VOLUME_USD,
        volume_step=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=NORMALIZED_MAXIMUM_VOLUME,
        minimum_execution_steps=1,
    )


def run(
    *,
    source_paths: dict[str, Path],
    output_dir: Path,
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    if end <= start:
        raise ValueError("measurement end must follow start")
    if set(source_paths) != {spec.key for spec in SOURCE_SPECS}:
        raise ValueError("seven-Trader source set incomplete")

    all_trades: list[Trade] = []
    counts: dict[str, int] = {}
    for spec in SOURCE_SPECS:
        rows = _load_source(
            source_paths[spec.key],
            spec=spec,
            start=start,
            end=end,
        )
        if not rows:
            raise ValueError(f"{spec.trader_id.value} has no measurement rows")
        counts[spec.trader_id.value] = len(rows)
        all_trades.extend(rows)

    required = {spec.trader_id for spec in SOURCE_SPECS}
    represented = {row.trader_id for row in all_trades}
    if represented != required:
        raise ValueError("measurement window does not contain all seven Traders")

    by_id = {row.fingerprint: row for row in all_trades}
    if len(by_id) != len(all_trades):
        raise ValueError("signal fingerprint collision")

    mission = derive_cibo_capital_mission(
        fundednext_stellar_instant_identity(
            account_ref="research-normalized-60usd-v3",
        )
    )

    events: list[tuple[datetime, int, str, str]] = []
    for row in all_trades:
        # Entries occur before exits at identical timestamps. No outcome,
        # expectation, score, or Trader ranking participates in tie-breaking.
        events.append(
            (row.entry_at, 0, row.trader_id.value, row.fingerprint)
        )
        events.append(
            (row.exit_at, 1, row.trader_id.value, row.fingerprint)
        )
    events.sort()

    per_stats: dict[str, dict[str, Any]] = {}
    for spec in SOURCE_SPECS:
        per_stats[spec.trader_id.value] = {
            "opportunities": counts[spec.trader_id.value],
            "cibo_calls": 0,
            "executed_entries": 0,
            "cibo_holds_or_no_capacity": 0,
            "wins": 0,
            "losses": 0,
            "breakeven": 0,
            "gross_profit": Decimal(0),
            "gross_loss": Decimal(0),
            "net": Decimal(0),
            "risk": Decimal(0),
            "minimal_seed_entries": 0,
            "protected_full_capacity_entries": 0,
            "capacity_reasons": defaultdict(int),
        }

    realized_pnl = Decimal(0)
    realized_capital = INITIAL_SEED_USD
    peak_realized_capital = realized_capital
    minimum_realized_capital = realized_capital
    max_realized_drawdown = Decimal(0)

    open_risk: dict[str, Decimal] = {}
    open_mode: dict[str, str] = {}
    reserved_stop_risk = Decimal(0)
    peak_reserved_stop_risk = Decimal(0)
    entries: dict[str, dict[str, Any]] = {}
    ledger: list[dict[str, Any]] = []

    first_base_protected_at: datetime | None = None
    first_full_capacity_entry_at: datetime | None = None
    insolvency_at: datetime | None = None
    milestone_hits: dict[Decimal, datetime] = {}
    trading_dates = sorted({row.entry_at.date() for row in all_trades})

    for at, event_kind, _trader_name, fingerprint in events:
        trade = by_id[fingerprint]
        trader = per_stats[trade.trader_id.value]

        if event_kind == 0:
            trader["cibo_calls"] += 1

            protected_capital = max(Decimal(0), realized_pnl)
            base_protected_before = (
                protected_capital >= SURVIVAL_CAPITAL_USD
            )

            if base_protected_before:
                # Observed account fact: expansion may consume only realized
                # protected-profit stop-risk capacity that is not already
                # reserved by another open CIBO allocation.
                hard_headroom = max(
                    Decimal(0),
                    protected_capital - reserved_stop_risk,
                )
            else:
                # Observed account fact before protection: surviving economic
                # capital remaining after currently open stop-risk reservations.
                hard_headroom = max(
                    Decimal(0),
                    realized_capital - reserved_stop_risk,
                )

            decision_reason: str
            try:
                capital = account_capital_state(
                    assigned_capital_usd=max(
                        realized_capital,
                        Decimal("0.000001"),
                    ),
                    hard_risk_headroom_usd=hard_headroom,
                    margin_headroom_usd=NORMALIZED_MARGIN_HEADROOM_USD,
                    survival_capital_usd=SURVIVAL_CAPITAL_USD,
                    protected_capital_usd=protected_capital,
                )
                decision = plan_account_sizing(
                    opportunity=_opportunity(trade),
                    capital=capital,
                    mission_policy=mission,
                    survival_capital_usd=SURVIVAL_CAPITAL_USD,
                    protected_capital_usd=protected_capital,
                )
                plan = decision.plan
                mode = decision.mode.value
                base_protected = decision.base_protected
                decision_reason = plan.reason
            except CiboCapitalManagementError as error:
                plan = None
                mode = (
                    CiboAccountSizingMode.PROTECTED_FULL_CAPACITY.value
                    if base_protected_before
                    else CiboAccountSizingMode.SURVIVAL_MINIMAL_SEED.value
                )
                base_protected = base_protected_before
                decision_reason = f"CIBO_ERROR:{error}"

            executable_actions = {
                CapitalAction.OPEN_MINIMAL_SEED,
                CapitalAction.OPEN_CAPABILITY_MAX,
                CapitalAction.EXPAND,
            }
            if plan is None or plan.action not in executable_actions:
                trader["cibo_holds_or_no_capacity"] += 1
                trader["capacity_reasons"][decision_reason] += 1
                ledger.append(
                    {
                        "fingerprint": fingerprint,
                        "trader": trade.trader_id.value,
                        "symbol": trade.symbol,
                        "signal_at": trade.signal_at.isoformat(),
                        "entry_at": trade.entry_at.isoformat(),
                        "exit_at": trade.exit_at.isoformat(),
                        "opportunity_forwarded_to_cibo": True,
                        "decision": "CIBO_HOLD_OR_NO_CAPACITY",
                        "cibo_reason": decision_reason,
                        "sizing_mode": mode,
                        "base_protected": base_protected,
                        "protected_capital_before_usd": _money(
                            protected_capital
                        ),
                        "hard_risk_headroom_before_usd": _money(
                            hard_headroom
                        ),
                        "assigned_stop_risk_usd": "0",
                        "observed_outcome_r": str(trade.outcome_r),
                        "realized_pnl_usd": None,
                        "capital_before_usd": _money(realized_capital),
                        "capital_after_usd": _money(realized_capital),
                    }
                )
                continue

            risk = plan.stop_risk_usd
            if risk <= 0:
                raise ValueError("CIBO executable plan has non-positive risk")
            if risk > hard_headroom:
                raise ValueError("CIBO plan exceeded supplied causal risk headroom")

            reserved_stop_risk += risk
            peak_reserved_stop_risk = max(
                peak_reserved_stop_risk,
                reserved_stop_risk,
            )
            open_risk[fingerprint] = risk
            open_mode[fingerprint] = mode

            trader["executed_entries"] += 1
            trader["risk"] += risk
            if decision.mode is CiboAccountSizingMode.SURVIVAL_MINIMAL_SEED:
                trader["minimal_seed_entries"] += 1
            elif decision.mode is CiboAccountSizingMode.PROTECTED_FULL_CAPACITY:
                trader["protected_full_capacity_entries"] += 1
                if first_full_capacity_entry_at is None:
                    first_full_capacity_entry_at = at

            entries[fingerprint] = {
                "fingerprint": fingerprint,
                "trader": trade.trader_id.value,
                "symbol": trade.symbol,
                "signal_at": trade.signal_at.isoformat(),
                "entry_at": trade.entry_at.isoformat(),
                "exit_at": trade.exit_at.isoformat(),
                "opportunity_forwarded_to_cibo": True,
                "decision": "EXECUTE",
                "cibo_action": plan.action.value,
                "cibo_reason": plan.reason,
                "sizing_mode": mode,
                "base_protected": base_protected,
                "protected_capital_before_usd": _money(protected_capital),
                "hard_risk_headroom_before_usd": _money(hard_headroom),
                "assigned_stop_risk_usd": _money(risk),
                "cibo_volume_normalized": str(plan.volume),
                "observed_outcome_r": str(trade.outcome_r),
                "capital_before_usd": _money(realized_capital),
                "cumulative_pnl_before_usd": _money(realized_pnl),
            }
            continue

        if fingerprint not in open_risk:
            continue

        risk = open_risk.pop(fingerprint)
        open_mode.pop(fingerprint)
        reserved_stop_risk -= risk
        if reserved_stop_risk < 0:
            raise ValueError("reserved stop risk became negative")

        delta = risk * trade.outcome_r
        realized_pnl += delta
        realized_capital = INITIAL_SEED_USD + realized_pnl
        peak_realized_capital = max(
            peak_realized_capital,
            realized_capital,
        )
        minimum_realized_capital = min(
            minimum_realized_capital,
            realized_capital,
        )
        max_realized_drawdown = max(
            max_realized_drawdown,
            peak_realized_capital - realized_capital,
        )

        if (
            first_base_protected_at is None
            and realized_pnl >= SURVIVAL_CAPITAL_USD
        ):
            first_base_protected_at = at

        if realized_capital <= 0 and insolvency_at is None:
            insolvency_at = at

        for milestone in MILESTONES_USD:
            if milestone not in milestone_hits and realized_pnl >= milestone:
                milestone_hits[milestone] = at

        if delta > 0:
            trader["wins"] += 1
            trader["gross_profit"] += delta
        elif delta < 0:
            trader["losses"] += 1
            trader["gross_loss"] += delta
        else:
            trader["breakeven"] += 1
        trader["net"] += delta

        record = entries.pop(fingerprint)
        record["realized_pnl_usd"] = _money(delta)
        record["capital_after_usd"] = _money(realized_capital)
        record["cumulative_pnl_after_usd"] = _money(realized_pnl)
        record["settled_at"] = at.isoformat()
        ledger.append(record)

    if open_risk or reserved_stop_risk != 0:
        raise ValueError("measurement ended with unsettled open risk")

    per_trader: dict[str, dict[str, Any]] = {}
    reconciled = Decimal(0)
    total_calls = total_executed = total_holds = 0
    total_wins = total_losses = total_be = 0

    for spec in SOURCE_SPECS:
        name = spec.trader_id.value
        row = per_stats[name]
        reconciled += row["net"]
        total_calls += row["cibo_calls"]
        total_executed += row["executed_entries"]
        total_holds += row["cibo_holds_or_no_capacity"]
        total_wins += row["wins"]
        total_losses += row["losses"]
        total_be += row["breakeven"]
        pf = (
            None
            if row["gross_loss"] == 0
            else row["gross_profit"] / abs(row["gross_loss"])
        )
        per_trader[name] = {
            "opportunities": row["opportunities"],
            "opportunities_forwarded_to_cibo": row["cibo_calls"],
            "executed_entries": row["executed_entries"],
            "cibo_holds_or_no_capacity": row[
                "cibo_holds_or_no_capacity"
            ],
            "wins": row["wins"],
            "losses": row["losses"],
            "breakeven": row["breakeven"],
            "gross_profit_usd": _money(row["gross_profit"]),
            "gross_loss_usd": _money(row["gross_loss"]),
            "net_pnl_usd": _money(row["net"]),
            "profit_factor": None if pf is None else str(pf),
            "total_cibo_stop_risk_assigned_usd": _money(row["risk"]),
            "minimal_seed_entries": row["minimal_seed_entries"],
            "protected_full_capacity_entries": row[
                "protected_full_capacity_entries"
            ],
            "cibo_capacity_reasons": dict(
                sorted(row["capacity_reasons"].items())
            ),
        }

    if reconciled != realized_pnl:
        raise ValueError("per-Trader PnL does not reconcile")
    if total_calls != len(all_trades):
        raise ValueError("not every Trader opportunity reached CIBO")
    if total_executed + total_holds != len(all_trades):
        raise ValueError("CIBO disposition coverage drift")
    if total_executed != total_wins + total_losses + total_be:
        raise ValueError("executed outcome accounting drift")

    milestones: dict[str, Any] = {}
    for milestone in MILESTONES_USD:
        hit = milestone_hits.get(milestone)
        milestones[str(milestone)] = {
            "reached": hit is not None,
            "reached_at": None if hit is None else hit.isoformat(),
            "calendar_days_elapsed": (
                None if hit is None else _days(start, hit)
            ),
            "trading_days_elapsed": (
                None
                if hit is None
                else sum(day <= hit.date() for day in trading_dates)
            ),
        }

    report: dict[str, Any] = {
        "schema": "qore.cibo.research.60usd-6m-free-traders.v3",
        "experiment_id": EXPERIMENT_ID,
        "status": "COMPLETED_MEASUREMENT",
        "measurement_window": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "fixed_six_calendar_month_window": True,
            "certification_holdout_claimed": False,
        },
        "architecture_binding": {
            "sizing_authority": (
                "qore.infrastructure.cibo_account_sizing_authority."
                "plan_account_sizing"
            ),
            "mission": mission.mission.value,
            "custom_expectation_filter": False,
            "custom_trader_rank_filter": False,
            "custom_loss_envelope": False,
            "identity_based_block": False,
            "all_valid_trader_entries_forwarded_to_cibo": True,
            "profit_cap_enabled": False,
        },
        "normalized_measurement_contract": {
            "initial_seed_usd": _money(INITIAL_SEED_USD),
            "survival_capital_usd": _money(SURVIVAL_CAPITAL_USD),
            "one_normalized_volume_stop_risk_usd": _money(
                NORMALIZED_STOP_RISK_PER_VOLUME_USD
            ),
            "margin_constraint": "NON_BINDING_FOR_MEASUREMENT",
            "historical_provider_economics_complete": False,
            "full_broker_executable_profit_claimed": False,
        },
        "portfolio": {
            "opportunities": len(all_trades),
            "opportunities_forwarded_to_cibo": total_calls,
            "executed_entries": total_executed,
            "cibo_holds_or_no_capacity": total_holds,
            "wins": total_wins,
            "losses": total_losses,
            "breakeven": total_be,
            "net_realized_profit_usd": _money(realized_pnl),
            "ending_realized_capital_usd": _money(realized_capital),
            "minimum_realized_capital_usd": _money(
                minimum_realized_capital
            ),
            "peak_realized_capital_usd": _money(peak_realized_capital),
            "max_realized_drawdown_usd": _money(max_realized_drawdown),
            "peak_reserved_stop_risk_usd": _money(
                peak_reserved_stop_risk
            ),
            "first_base_protected_at": (
                None
                if first_base_protected_at is None
                else first_base_protected_at.isoformat()
            ),
            "first_protected_full_capacity_entry_at": (
                None
                if first_full_capacity_entry_at is None
                else first_full_capacity_entry_at.isoformat()
            ),
            "insolvency_at": (
                None if insolvency_at is None else insolvency_at.isoformat()
            ),
            "capital_amplification_net_profit_over_seed": str(
                realized_pnl / INITIAL_SEED_USD
            ),
        },
        "milestones": milestones,
        "per_trader": per_trader,
        "measurement_flags": {
            "survival_positive_capital": (
                insolvency_at is None and minimum_realized_capital > 0
            ),
            "base_protection_reached": first_base_protected_at is not None,
            "protected_full_capacity_used": (
                first_full_capacity_entry_at is not None
            ),
            "target_300_reached": Decimal("300") in milestone_hits,
        },
        "governance": {
            "independent_from_pr651_certification": True,
            "phase20d_evidence": False,
            "phase21_evidence": False,
            "phase22_evidence": False,
            "vps_used": False,
            "broker_mutation": False,
            "live_authority": False,
            "real_capital_authority": False,
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report-v3.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "trade-ledger-v3.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in ledger),
        encoding="utf-8",
    )

    with (output_dir / "per-trader-v3.csv").open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "trader",
                "opportunities",
                "opportunities_forwarded_to_cibo",
                "executed_entries",
                "cibo_holds_or_no_capacity",
                "wins",
                "losses",
                "breakeven",
                "gross_profit_usd",
                "gross_loss_usd",
                "net_pnl_usd",
                "profit_factor",
                "total_cibo_stop_risk_assigned_usd",
                "minimal_seed_entries",
                "protected_full_capacity_entries",
            ]
        )
        for trader_name, row in per_trader.items():
            writer.writerow(
                [
                    trader_name,
                    row["opportunities"],
                    row["opportunities_forwarded_to_cibo"],
                    row["executed_entries"],
                    row["cibo_holds_or_no_capacity"],
                    row["wins"],
                    row["losses"],
                    row["breakeven"],
                    row["gross_profit_usd"],
                    row["gross_loss_usd"],
                    row["net_pnl_usd"],
                    row["profit_factor"],
                    row["total_cibo_stop_risk_assigned_usd"],
                    row["minimal_seed_entries"],
                    row["protected_full_capacity_entries"],
                ]
            )

    m300 = milestones["300"]
    summary = [
        "# CIBO USD60 / 6M Free-Trader Current-Architecture Experiment V3",
        "",
        f"- Window: {start.isoformat()} -> {end.isoformat()}",
        f"- Initial seed: USD {_money(INITIAL_SEED_USD)}",
        f"- Opportunities forwarded to CIBO: {total_calls}/{len(all_trades)}",
        f"- Executed entries: {total_executed}",
        f"- CIBO holds/no-capacity: {total_holds}",
        f"- Wins / Losses / BE: {total_wins} / {total_losses} / {total_be}",
        f"- Net realized profit: USD {_money(realized_pnl)}",
        f"- Ending realized capital: USD {_money(realized_capital)}",
        f"- Minimum realized capital: USD {_money(minimum_realized_capital)}",
        f"- Max realized drawdown: USD {_money(max_realized_drawdown)}",
        (
            "- Base protection reached: "
            f"{report['measurement_flags']['base_protection_reached']}"
        ),
        (
            "- Protected full capacity used: "
            f"{report['measurement_flags']['protected_full_capacity_used']}"
        ),
        f"- +USD300 reached: {m300['reached']}",
    ]
    if m300["reached"]:
        summary.extend(
            [
                f"- +USD300 reached at: {m300['reached_at']}",
                f"- Calendar days to +USD300: {m300['calendar_days_elapsed']}",
                f"- Trading days to +USD300: {m300['trading_days_elapsed']}",
            ]
        )
    summary.extend(
        [
            "",
            "## Architecture rule",
            "",
            (
                "No opportunity-quality law exists in this harness. Every "
                "retained valid Trader entry reaches the current CIBO sizing "
                "authority. The only non-executions are CIBO's own HOLD or "
                "lack-of-capacity outcomes."
            ),
            "",
            "## Evidence boundary",
            "",
            (
                "This is a normalized structural-stop-risk measurement because "
                "exact historical broker economics are not complete across all "
                "seven Phase18 lineages."
            ),
        ]
    )
    (output_dir / "SUMMARY-V3.md").write_text(
        "\n".join(summary) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    for spec in SOURCE_SPECS:
        parser.add_argument(f"--{spec.key}", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    args = parser.parse_args()
    report = run(
        source_paths={
            spec.key: getattr(args, spec.key)
            for spec in SOURCE_SPECS
        },
        output_dir=args.output_dir,
        start=datetime.fromisoformat(args.start),
        end=datetime.fromisoformat(args.end),
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
