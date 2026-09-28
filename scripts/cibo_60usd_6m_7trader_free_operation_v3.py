"""CIBO USD60 / six-month seven-Trader free-operation experiment V3.

Purpose
-------
Measure the capitalization path when every valid Trader opportunity is admitted
without any expectation, ranking, identity, or performance filter. Trader
methodology owns whether an opportunity exists. CIBO owns sizing only.

This is an independent research measurement. It is NOT Phase20/21/22
certification evidence and does not claim exact historical broker economics.

Sizing law
----------
- Initial operating seed: USD 60.
- Before realized protected profit reaches USD 60, every valid opportunity gets
  normalized minimum-seed risk up to USD 1, down-sized only if actual remaining
  capital cannot support that stressed loss.
- Once realized protected profit is at least USD 60, sizing is funded only from
  current positive realized profit. No profit ceiling exists.
- A causal pre-window loss envelope protects the base. V3 uses no pre-window
  expected-return filter.
- Optionality reserve is derived only from pre-window maximum portfolio
  concurrency; it controls sizing, never signal admission.
- Every valid opportunity executes with any strictly positive available size.
  A zero-size rejection can only occur if real capital capacity is exhausted.

Normalized PnL:
    pnl_usd = assigned_structural_stop_risk_usd * observed_structural_R
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage

getcontext().prec = 50

EXPERIMENT_ID = "CIBO_60USD_6M_7TRADER_FREE_OPERATION_V3"
INITIAL_SEED_USD = Decimal("60")
PROTECTION_THRESHOLD_USD = Decimal("60")
NORMALIZED_MINIMUM_SEED_RISK_USD = Decimal("1")
LOSS_ENVELOPE_STRESS = Decimal("1.25")
ACCOUNTING_EPSILON = Decimal("1e-30")
TRAIN_START = "2021-09-23T05:00:00+00:00"
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
    signal_at: datetime
    entry_at: datetime
    exit_at: datetime
    outcome_r: Decimal


@dataclass(frozen=True, slots=True)
class LossEnvelope:
    train_rows: int
    worst_loss_r: Decimal
    stressed_loss_r: Decimal


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
    index: int,
) -> str:
    material = json.dumps(
        {
            "trader": spec.trader_id.value,
            "symbol": spec.qore_symbol or str(row["symbol"]),
            "signal_at": str(row["signal_at"]),
            "entry_at": str(row["entry_at"]),
            "exit_at": str(row["exit_at"]),
            "index": index,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(material).hexdigest()


def _load(path: Path, spec: SourceSpec) -> list[Trade]:
    trades: list[Trade] = []
    for index, row in enumerate(_jsonl(path)):
        signal_at = datetime.fromisoformat(str(row["signal_at"]))
        entry_at = datetime.fromisoformat(str(row["entry_at"]))
        exit_at = datetime.fromisoformat(str(row["exit_at"]))
        for name, value in (
            ("signal_at", signal_at),
            ("entry_at", entry_at),
            ("exit_at", exit_at),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if not signal_at <= entry_at < exit_at:
            raise ValueError(
                f"{spec.trader_id.value} causal chronology drift at {index}"
            )
        outcome = Decimal(str(row[spec.outcome_field]))
        if not outcome.is_finite():
            raise ValueError(
                f"{spec.trader_id.value} non-finite outcome at {index}"
            )
        trades.append(
            Trade(
                trader_id=spec.trader_id,
                symbol=spec.qore_symbol or str(row["symbol"]),
                fingerprint=_fingerprint(spec=spec, row=row, index=index),
                signal_at=signal_at,
                entry_at=entry_at,
                exit_at=exit_at,
                outcome_r=outcome,
            )
        )
    return trades


def _max_concurrency(trades: list[Trade]) -> int:
    events: list[tuple[datetime, int]] = []
    for trade in trades:
        events.append((trade.entry_at, 1))
        events.append((trade.exit_at, -1))
    # Exit before entry at identical timestamp: no fabricated recycling overlap.
    events.sort(key=lambda item: (item[0], item[1]))
    active = 0
    peak = 0
    for _at, delta in events:
        active += delta
        if active < 0:
            raise ValueError("concurrency accounting drift")
        peak = max(peak, active)
    if active != 0:
        raise ValueError("concurrency did not settle")
    return peak


def _loss_envelope(
    trades: list[Trade],
    *,
    train_start: datetime,
    train_end: datetime,
) -> LossEnvelope:
    train = [
        trade
        for trade in trades
        if trade.entry_at >= train_start and trade.exit_at <= train_end
    ]
    if not train:
        raise ValueError("loss envelope requires pre-window observations")
    losses = [-trade.outcome_r for trade in train if trade.outcome_r < 0]
    worst = max(losses, default=Decimal("1"))
    stressed = max(Decimal("1"), worst) * LOSS_ENVELOPE_STRESS
    return LossEnvelope(
        train_rows=len(train),
        worst_loss_r=worst,
        stressed_loss_r=stressed,
    )


def run(
    *,
    source_paths: dict[str, Path],
    output_dir: Path,
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    train_start = datetime.fromisoformat(TRAIN_START)
    if not train_start < start < end:
        raise ValueError("training/measurement chronology invalid")
    if set(source_paths) != {spec.key for spec in SOURCE_SPECS}:
        raise ValueError("seven-Trader source set incomplete")

    source_rows: dict[TraderLineage, list[Trade]] = {}
    envelopes: dict[TraderLineage, LossEnvelope] = {}
    prewindow: list[Trade] = []
    measured: list[Trade] = []

    for spec in SOURCE_SPECS:
        rows = _load(source_paths[spec.key], spec)
        source_rows[spec.trader_id] = rows
        envelopes[spec.trader_id] = _loss_envelope(
            rows,
            train_start=train_start,
            train_end=start,
        )
        prewindow.extend(
            trade
            for trade in rows
            if trade.entry_at >= train_start and trade.exit_at <= start
        )
        selected = [
            trade
            for trade in rows
            if trade.entry_at >= start and trade.exit_at <= end
        ]
        if not selected:
            raise ValueError(
                f"{spec.trader_id.value} missing six-month opportunities"
            )
        measured.extend(selected)

    required = {spec.trader_id for spec in SOURCE_SPECS}
    if {trade.trader_id for trade in measured} != required:
        raise ValueError("measurement does not contain all seven Traders")

    prewindow_max_concurrency = _max_concurrency(prewindow)
    if prewindow_max_concurrency <= 0:
        raise ValueError("pre-window concurrency must be positive")
    reserve_slots = Decimal(prewindow_max_concurrency)

    by_id = {trade.fingerprint: trade for trade in measured}
    if len(by_id) != len(measured):
        raise ValueError("duplicate measurement fingerprint")

    events: list[tuple[datetime, int, str, str]] = []
    for trade in measured:
        # Entries precede exits at the same timestamp: no same-timestamp PnL
        # recycling into a fresh position.
        events.append(
            (
                trade.entry_at,
                0,
                trade.trader_id.value,
                trade.fingerprint,
            )
        )
        events.append(
            (
                trade.exit_at,
                1,
                trade.trader_id.value,
                trade.fingerprint,
            )
        )
    events.sort()

    stats: dict[str, dict[str, Any]] = {}
    for spec in SOURCE_SPECS:
        stats[spec.trader_id.value] = {
            "opportunities": sum(
                trade.trader_id is spec.trader_id for trade in measured
            ),
            "executed": 0,
            "zero_capacity": 0,
            "wins": 0,
            "losses": 0,
            "be": 0,
            "gross_profit": Decimal(0),
            "gross_loss": Decimal(0),
            "net": Decimal(0),
            "risk": Decimal(0),
            "minimal": 0,
            "protected": 0,
            "envelope_breaches": 0,
        }

    capital = INITIAL_SEED_USD
    realized_pnl = Decimal(0)
    peak_capital = capital
    minimum_capital = capital
    max_drawdown = Decimal(0)
    reserved_stressed_loss = Decimal(0)
    peak_reserved_stressed_loss = Decimal(0)
    open_positions: dict[str, tuple[Decimal, Decimal]] = {}
    entry_records: dict[str, dict[str, Any]] = {}
    ledger: list[dict[str, Any]] = []

    first_protected_at: datetime | None = None
    first_seed_penetration_at: datetime | None = None
    seed_penetrations = 0
    protected_overcommit_events = 0
    insolvency_at: datetime | None = None
    milestones: dict[Decimal, datetime] = {}
    trading_dates = sorted({trade.entry_at.date() for trade in measured})

    for at, kind, trader_name, fingerprint in events:
        trade = by_id[fingerprint]
        envelope = envelopes[trade.trader_id]
        trader = stats[trader_name]

        if kind == 0:
            protected_profit = max(Decimal(0), realized_pnl)
            base_protected = protected_profit >= PROTECTION_THRESHOLD_USD
            if base_protected:
                total_loss_capacity = protected_profit
                mode = "PROTECTED_SIZING"
            else:
                total_loss_capacity = max(Decimal(0), capital)
                mode = "SURVIVAL_MINIMAL_SEED"

            available_loss_capacity = max(
                Decimal(0),
                total_loss_capacity - reserved_stressed_loss,
            )
            max_risk_now = (
                available_loss_capacity / envelope.stressed_loss_r
                if available_loss_capacity > 0
                else Decimal(0)
            )

            if base_protected:
                optionality_risk = (
                    available_loss_capacity
                    / envelope.stressed_loss_r
                    / reserve_slots
                    if available_loss_capacity > 0
                    else Decimal(0)
                )
                minimum_if_possible = min(
                    NORMALIZED_MINIMUM_SEED_RISK_USD,
                    max_risk_now,
                )
                assigned_risk = max(
                    minimum_if_possible,
                    optionality_risk,
                )
            else:
                assigned_risk = min(
                    NORMALIZED_MINIMUM_SEED_RISK_USD,
                    max_risk_now,
                )

            if assigned_risk <= 0:
                trader["zero_capacity"] += 1
                ledger.append(
                    {
                        "fingerprint": fingerprint,
                        "trader": trader_name,
                        "symbol": trade.symbol,
                        "signal_at": trade.signal_at.isoformat(),
                        "entry_at": trade.entry_at.isoformat(),
                        "exit_at": trade.exit_at.isoformat(),
                        "decision": "ZERO_CAPACITY",
                        "reason": "NO_POSITIVE_CAPITAL_CAPACITY",
                        "sizing_mode": mode,
                        "base_protected": base_protected,
                        "assigned_risk_usd": "0",
                        "stressed_loss_reserve_usd": "0",
                        "observed_outcome_r": str(trade.outcome_r),
                        "realized_pnl_usd": None,
                        "capital_before_usd": _money(capital),
                        "capital_after_usd": _money(capital),
                    }
                )
                continue

            stressed_reserve = assigned_risk * envelope.stressed_loss_r
            if stressed_reserve > available_loss_capacity:
                raise ValueError("sizing exceeds available loss capacity")

            reserved_stressed_loss += stressed_reserve
            peak_reserved_stressed_loss = max(
                peak_reserved_stressed_loss,
                reserved_stressed_loss,
            )
            open_positions[fingerprint] = (
                assigned_risk,
                stressed_reserve,
            )
            trader["executed"] += 1
            trader["risk"] += assigned_risk
            if base_protected:
                trader["protected"] += 1
            else:
                trader["minimal"] += 1

            entry_records[fingerprint] = {
                "fingerprint": fingerprint,
                "trader": trader_name,
                "symbol": trade.symbol,
                "signal_at": trade.signal_at.isoformat(),
                "entry_at": trade.entry_at.isoformat(),
                "exit_at": trade.exit_at.isoformat(),
                "decision": "EXECUTE",
                "reason": "TRADER_ENTRY_ADMITTED_CIBO_SIZING_ONLY",
                "sizing_mode": mode,
                "base_protected": base_protected,
                "assigned_risk_usd": _money(assigned_risk),
                "stressed_loss_reserve_usd": _money(stressed_reserve),
                "loss_envelope_r": str(envelope.stressed_loss_r),
                "observed_outcome_r": str(trade.outcome_r),
                "capital_before_usd": _money(capital),
                "cumulative_pnl_before_usd": _money(realized_pnl),
            }
            continue

        if fingerprint not in open_positions:
            continue

        assigned_risk, stressed_reserve = open_positions.pop(fingerprint)
        reserved_stressed_loss -= stressed_reserve
        if reserved_stressed_loss < 0:
            if abs(reserved_stressed_loss) <= ACCOUNTING_EPSILON:
                reserved_stressed_loss = Decimal(0)
            else:
                raise ValueError("negative stressed-loss reserve")

        envelope_breach = (
            trade.outcome_r < 0
            and -trade.outcome_r > envelope.stressed_loss_r
        )
        if envelope_breach:
            trader["envelope_breaches"] += 1

        delta = assigned_risk * trade.outcome_r
        realized_pnl += delta
        capital = INITIAL_SEED_USD + realized_pnl
        peak_capital = max(peak_capital, capital)
        minimum_capital = min(minimum_capital, capital)
        max_drawdown = max(max_drawdown, peak_capital - capital)

        if (
            first_protected_at is None
            and realized_pnl >= PROTECTION_THRESHOLD_USD
        ):
            first_protected_at = at

        if (
            first_protected_at is not None
            and capital < INITIAL_SEED_USD
        ):
            seed_penetrations += 1
            if first_seed_penetration_at is None:
                first_seed_penetration_at = at

        current_protected_profit = max(Decimal(0), realized_pnl)
        if (
            current_protected_profit >= PROTECTION_THRESHOLD_USD
            and reserved_stressed_loss > current_protected_profit
        ):
            protected_overcommit_events += 1

        if capital <= 0 and insolvency_at is None:
            insolvency_at = at

        for milestone in MILESTONES_USD:
            if milestone not in milestones and realized_pnl >= milestone:
                milestones[milestone] = at

        if delta > 0:
            trader["wins"] += 1
            trader["gross_profit"] += delta
        elif delta < 0:
            trader["losses"] += 1
            trader["gross_loss"] += delta
        else:
            trader["be"] += 1
        trader["net"] += delta

        record = entry_records.pop(fingerprint)
        record["loss_envelope_breached"] = envelope_breach
        record["realized_pnl_usd"] = _money(delta)
        record["capital_after_usd"] = _money(capital)
        record["cumulative_pnl_after_usd"] = _money(realized_pnl)
        record["settled_at"] = at.isoformat()
        ledger.append(record)

    if open_positions or reserved_stressed_loss != 0:
        raise ValueError("measurement ended with unsettled positions")

    per_trader: dict[str, dict[str, Any]] = {}
    reconciled = Decimal(0)
    total_executed = 0
    total_zero_capacity = 0
    total_wins = 0
    total_losses = 0
    total_be = 0

    for spec in SOURCE_SPECS:
        name = spec.trader_id.value
        row = stats[name]
        envelope = envelopes[spec.trader_id]
        reconciled += row["net"]
        total_executed += row["executed"]
        total_zero_capacity += row["zero_capacity"]
        total_wins += row["wins"]
        total_losses += row["losses"]
        total_be += row["be"]
        pf = (
            None
            if row["gross_loss"] == 0
            else row["gross_profit"] / abs(row["gross_loss"])
        )
        per_trader[name] = {
            "opportunities": row["opportunities"],
            "executed_entries": row["executed"],
            "zero_capacity_entries": row["zero_capacity"],
            "wins": row["wins"],
            "losses": row["losses"],
            "breakeven": row["be"],
            "gross_profit_usd": _money(row["gross_profit"]),
            "gross_loss_usd": _money(row["gross_loss"]),
            "net_pnl_usd": _money(row["net"]),
            "profit_factor": None if pf is None else str(pf),
            "total_risk_assigned_usd": _money(row["risk"]),
            "minimal_seed_entries": row["minimal"],
            "protected_sizing_entries": row["protected"],
            "prewindow_train_rows": envelope.train_rows,
            "prewindow_worst_loss_r": str(envelope.worst_loss_r),
            "causal_stressed_loss_envelope_r": str(
                envelope.stressed_loss_r
            ),
            "loss_envelope_breaches": row["envelope_breaches"],
            "policy_filter_rejections": 0,
        }

    if abs(reconciled - realized_pnl) > ACCOUNTING_EPSILON:
        raise ValueError("per-Trader PnL reconciliation failed")
    if total_executed != total_wins + total_losses + total_be:
        raise ValueError("outcome counts do not reconcile")
    if total_executed + total_zero_capacity != len(measured):
        raise ValueError("opportunity admission accounting drift")

    milestone_report: dict[str, Any] = {}
    for milestone in MILESTONES_USD:
        hit = milestones.get(milestone)
        milestone_report[str(milestone)] = {
            "reached": hit is not None,
            "reached_at": None if hit is None else hit.isoformat(),
            "calendar_days_elapsed": None if hit is None else _days(start, hit),
            "trading_days_elapsed": (
                None
                if hit is None
                else sum(day <= hit.date() for day in trading_dates)
            ),
        }

    all_traders_operated = all(
        row["executed_entries"] > 0 for row in per_trader.values()
    )
    no_policy_filters = all(
        row["policy_filter_rejections"] == 0
        for row in per_trader.values()
    )
    survival = insolvency_at is None and minimum_capital > 0
    protection = (
        seed_penetrations == 0
        and protected_overcommit_events == 0
    )
    target_300 = Decimal("300") in milestones

    report: dict[str, Any] = {
        "schema": "qore.cibo.research.60usd-6m-7trader-free-operation.v3",
        "experiment_id": EXPERIMENT_ID,
        "status": "COMPLETED_MEASUREMENT",
        "measurement_window": {
            "prewindow_start": train_start.isoformat(),
            "prewindow_end": start.isoformat(),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "six_month_measurement": True,
            "certification_holdout_claimed": False,
        },
        "admission_contract": {
            "all_valid_trader_entries_admitted": True,
            "expectation_filter": False,
            "ranking_filter": False,
            "identity_filter": False,
            "historical_performance_filter": False,
            "policy_filter_rejections": 0,
            "only_zero_real_capital_capacity_can_zero_size": True,
        },
        "capital_contract": {
            "initial_seed_usd": _money(INITIAL_SEED_USD),
            "protection_threshold_usd": _money(
                PROTECTION_THRESHOLD_USD
            ),
            "normalized_minimum_seed_risk_usd": _money(
                NORMALIZED_MINIMUM_SEED_RISK_USD
            ),
            "loss_envelope_stress_multiplier": str(
                LOSS_ENVELOPE_STRESS
            ),
            "prewindow_max_portfolio_concurrency": (
                prewindow_max_concurrency
            ),
            "post_protection_optionality_reserve_slots": (
                prewindow_max_concurrency
            ),
            "profit_cap_enabled": False,
            "profit_cap_usd": None,
            "outcome_aware_sizing": False,
            "martingale": False,
            "loss_recovery_sizing": False,
        },
        "evidence_scope": {
            "represented_traders": 7,
            "r_denominated_phase18_evidence": True,
            "historical_provider_economics_complete": False,
            "usd_numeraire": (
                "ASSIGNED_NORMALIZED_STRUCTURAL_STOP_RISK_X_OBSERVED_R"
            ),
            "intratrade_protected_floor_replayed": False,
            "full_broker_executable_profit_claimed": False,
        },
        "portfolio": {
            "opportunities": len(measured),
            "executed_entries": total_executed,
            "zero_capacity_entries": total_zero_capacity,
            "wins": total_wins,
            "losses": total_losses,
            "breakeven": total_be,
            "net_realized_profit_usd": _money(realized_pnl),
            "ending_realized_capital_usd": _money(capital),
            "minimum_realized_capital_usd": _money(minimum_capital),
            "peak_realized_capital_usd": _money(peak_capital),
            "max_realized_drawdown_usd": _money(max_drawdown),
            "peak_reserved_stressed_loss_usd": _money(
                peak_reserved_stressed_loss
            ),
            "first_base_protected_at": (
                None
                if first_protected_at is None
                else first_protected_at.isoformat()
            ),
            "seed_penetration_count_after_first_protection": (
                seed_penetrations
            ),
            "first_seed_penetration_at": (
                None
                if first_seed_penetration_at is None
                else first_seed_penetration_at.isoformat()
            ),
            "protected_overcommit_events": protected_overcommit_events,
            "insolvency_at": (
                None if insolvency_at is None else insolvency_at.isoformat()
            ),
            "capital_amplification_net_profit_over_seed": str(
                realized_pnl / INITIAL_SEED_USD
            ),
        },
        "milestones": milestone_report,
        "per_trader": per_trader,
        "gates": {
            "all_7_traders_operated": (
                "PASS" if all_traders_operated else "FAIL"
            ),
            "no_policy_filtering": (
                "PASS" if no_policy_filters else "FAIL"
            ),
            "survival": "PASS" if survival else "FAIL",
            "capital_protection_integrity": (
                "PASS" if protection else "FAIL"
            ),
            "net_profit_gt_300": "PASS" if target_300 else "FAIL",
            "full_capability_experiment": (
                "PASS"
                if (
                    all_traders_operated
                    and no_policy_filters
                    and survival
                    and protection
                    and target_300
                )
                else "FAIL"
            ),
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
        "".join(
            json.dumps(row, sort_keys=True) + "\n"
            for row in ledger
        ),
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
                "executed_entries",
                "zero_capacity_entries",
                "wins",
                "losses",
                "breakeven",
                "gross_profit_usd",
                "gross_loss_usd",
                "net_pnl_usd",
                "profit_factor",
                "total_risk_assigned_usd",
                "minimal_seed_entries",
                "protected_sizing_entries",
                "loss_envelope_breaches",
            ]
        )
        for trader_name, row in per_trader.items():
            writer.writerow(
                [
                    trader_name,
                    row["opportunities"],
                    row["executed_entries"],
                    row["zero_capacity_entries"],
                    row["wins"],
                    row["losses"],
                    row["breakeven"],
                    row["gross_profit_usd"],
                    row["gross_loss_usd"],
                    row["net_pnl_usd"],
                    row["profit_factor"],
                    row["total_risk_assigned_usd"],
                    row["minimal_seed_entries"],
                    row["protected_sizing_entries"],
                    row["loss_envelope_breaches"],
                ]
            )

    m300 = milestone_report["300"]
    lines = [
        "# CIBO USD60 / 6M Seven-Trader Free-Operation V3",
        "",
        f"- Measurement: {start.isoformat()} -> {end.isoformat()}",
        f"- Opportunities: {len(measured)}",
        f"- Executed: {total_executed}",
        f"- Zero-capacity: {total_zero_capacity}",
        f"- All 7 Traders operated: {all_traders_operated}",
        f"- Initial seed: USD {_money(INITIAL_SEED_USD)}",
        f"- Net realized profit: USD {_money(realized_pnl)}",
        f"- Ending capital: USD {_money(capital)}",
        f"- Minimum capital: USD {_money(minimum_capital)}",
        f"- Max drawdown: USD {_money(max_drawdown)}",
        f"- Wins / Losses / BE: {total_wins} / {total_losses} / {total_be}",
        f"- First protection: {report['portfolio']['first_base_protected_at']}",
        f"- Survival: {report['gates']['survival']}",
        f"- Protection integrity: {report['gates']['capital_protection_integrity']}",
        f"- +USD300 reached: {m300['reached']}",
    ]
    if m300["reached"]:
        lines.extend(
            [
                f"- +USD300 reached at: {m300['reached_at']}",
                f"- Calendar days to +USD300: {m300['calendar_days_elapsed']}",
                f"- Trading days to +USD300: {m300['trading_days_elapsed']}",
            ]
        )
    (output_dir / "SUMMARY-V3.md").write_text(
        "\n".join(lines) + "\n",
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
