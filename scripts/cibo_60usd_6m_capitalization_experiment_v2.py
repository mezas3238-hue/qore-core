"""CIBO USD60 / six-month capitalization capability experiment V2.

Independent measurement only; never Phase20/21/22 certification evidence.

V2 fixes two V1 limitations:
1. all opportunity expectation and loss-envelope evidence is derived strictly
   before the six-month measurement window;
2. post-protection sizing reserves a causal stressed-loss envelope so CIBO can
   expand without intentionally exposing the protected USD60 base.

There is no profit cap. Risk may grow without a fixed ceiling as protected
realized profit grows, but every open position consumes stressed-loss capacity.
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
from statistics import median
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage

getcontext().prec = 50

EXPERIMENT_ID = "CIBO_60USD_6M_CAPITALIZATION_CAPABILITY_EXPERIMENT_V2"
INITIAL_SEED_USD = Decimal("60")
SURVIVAL_CAPITAL_USD = Decimal("60")
NORMALIZED_MINIMUM_SEED_RISK_USD = Decimal("1")
LOSS_ENVELOPE_STRESS = Decimal("1.25")
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
class RawTrade:
    trader_id: TraderLineage
    symbol: str
    fingerprint: str
    signal_at: datetime
    entry_at: datetime
    exit_at: datetime
    outcome_r: Decimal

    @property
    def duration_minutes(self) -> Decimal:
        return Decimal(str((self.exit_at - self.entry_at).total_seconds())) / Decimal(60)


@dataclass(frozen=True, slots=True)
class CausalPrior:
    train_rows: int
    expected_r: Decimal
    expected_minutes: Decimal
    worst_loss_r: Decimal
    loss_envelope_r: Decimal
    block_means_r: tuple[Decimal, ...]

    @property
    def expected_efficiency(self) -> Decimal:
        return self.expected_r / self.expected_minutes


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
    spec: SourceSpec,
    row: dict[str, Any],
    index: int,
) -> str:
    payload = {
        "trader": spec.trader_id.value,
        "symbol": spec.qore_symbol or str(row["symbol"]),
        "signal_at": str(row["signal_at"]),
        "entry_at": str(row["entry_at"]),
        "exit_at": str(row["exit_at"]),
        "index": index,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _load_source(path: Path, spec: SourceSpec) -> list[RawTrade]:
    result: list[RawTrade] = []
    for index, row in enumerate(_jsonl(path)):
        signal_at = datetime.fromisoformat(str(row["signal_at"]))
        entry_at = datetime.fromisoformat(str(row["entry_at"]))
        exit_at = datetime.fromisoformat(str(row["exit_at"]))
        for value in (signal_at, entry_at, exit_at):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("timestamps must be timezone-aware")
        if not signal_at <= entry_at < exit_at:
            raise ValueError(
                f"{spec.trader_id.value} chronology drift at row {index}"
            )
        outcome = Decimal(str(row[spec.outcome_field]))
        if not outcome.is_finite():
            raise ValueError(
                f"{spec.trader_id.value} non-finite R at row {index}"
            )
        result.append(
            RawTrade(
                trader_id=spec.trader_id,
                symbol=spec.qore_symbol or str(row["symbol"]),
                fingerprint=_fingerprint(spec, row, index),
                signal_at=signal_at,
                entry_at=entry_at,
                exit_at=exit_at,
                outcome_r=outcome,
            )
        )
    return result


def _median_decimal(values: list[Decimal]) -> Decimal:
    if not values:
        raise ValueError("median requires observations")
    return Decimal(str(median(values)))


def _build_prior(
    rows: list[RawTrade],
    *,
    train_start: datetime,
    train_end: datetime,
) -> CausalPrior:
    train = sorted(
        (
            row
            for row in rows
            if row.entry_at >= train_start and row.exit_at <= train_end
        ),
        key=lambda row: (row.entry_at, row.fingerprint),
    )
    if len(train) < 5:
        raise ValueError(
            f"{rows[0].trader_id.value} requires at least five pre-window rows"
        )

    buckets: list[list[RawTrade]] = [[] for _ in range(5)]
    for index, row in enumerate(train):
        bucket = min(4, (index * 5) // len(train))
        buckets[bucket].append(row)
    block_means = tuple(
        sum((row.outcome_r for row in bucket), Decimal(0))
        / Decimal(len(bucket))
        for bucket in buckets
        if bucket
    )
    expected_r = _median_decimal(list(block_means))
    expected_minutes = _median_decimal(
        [row.duration_minutes for row in train]
    )
    losses = [-row.outcome_r for row in train if row.outcome_r < 0]
    worst_loss = max(losses, default=Decimal("1"))
    base_envelope = max(Decimal("1"), worst_loss)
    loss_envelope = base_envelope * LOSS_ENVELOPE_STRESS
    return CausalPrior(
        train_rows=len(train),
        expected_r=expected_r,
        expected_minutes=expected_minutes,
        worst_loss_r=worst_loss,
        loss_envelope_r=loss_envelope,
        block_means_r=block_means,
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
        raise ValueError("training/window chronology invalid")
    if set(source_paths) != {spec.key for spec in SOURCE_SPECS}:
        raise ValueError("seven-Trader source set incomplete")

    raw_by_trader: dict[TraderLineage, list[RawTrade]] = {}
    priors: dict[TraderLineage, CausalPrior] = {}
    holdout: list[RawTrade] = []

    for spec in SOURCE_SPECS:
        rows = _load_source(source_paths[spec.key], spec)
        raw_by_trader[spec.trader_id] = rows
        prior = _build_prior(rows, train_start=train_start, train_end=start)
        priors[spec.trader_id] = prior
        selected = [
            row
            for row in rows
            if row.entry_at >= start and row.exit_at <= end
        ]
        if not selected:
            raise ValueError(f"{spec.trader_id.value} has no six-month rows")
        holdout.extend(selected)

    represented = {row.trader_id for row in holdout}
    if represented != {spec.trader_id for spec in SOURCE_SPECS}:
        raise ValueError("six-month window missing Trader lineage")

    by_id = {row.fingerprint: row for row in holdout}
    if len(by_id) != len(holdout):
        raise ValueError("fingerprint collision")

    events: list[tuple[datetime, int, Decimal, str, str]] = []
    for row in holdout:
        prior = priors[row.trader_id]
        events.append(
            (
                row.entry_at,
                0,
                -prior.expected_efficiency,
                row.trader_id.value,
                row.fingerprint,
            )
        )
        events.append(
            (
                row.exit_at,
                1,
                Decimal(0),
                row.trader_id.value,
                row.fingerprint,
            )
        )
    events.sort()

    stats: dict[str, dict[str, Any]] = {}
    for spec in SOURCE_SPECS:
        count = sum(row.trader_id is spec.trader_id for row in holdout)
        stats[spec.trader_id.value] = {
            "opportunities": count,
            "executed": 0,
            "rejected": 0,
            "wins": 0,
            "losses": 0,
            "breakeven": 0,
            "gross_profit": Decimal(0),
            "gross_loss": Decimal(0),
            "net": Decimal(0),
            "risk": Decimal(0),
            "minimal": 0,
            "protected": 0,
            "rejects": defaultdict(int),
            "envelope_breaches": 0,
        }

    realized_pnl = Decimal(0)
    capital = INITIAL_SEED_USD
    peak_capital = capital
    minimum_capital = capital
    max_drawdown = Decimal(0)
    reserved_stressed_loss = Decimal(0)
    peak_reserved_stressed_loss = Decimal(0)
    open_positions: dict[str, tuple[Decimal, Decimal]] = {}
    entry_records: dict[str, dict[str, Any]] = {}
    first_protected_at: datetime | None = None
    first_seed_penetration_at: datetime | None = None
    seed_penetrations = 0
    loss_envelope_breaches = 0
    insolvency_at: datetime | None = None
    milestone_hits: dict[Decimal, datetime] = {}
    ledger: list[dict[str, Any]] = []
    trading_dates = sorted({row.entry_at.date() for row in holdout})

    for at, kind, _rank, _trader, fingerprint in events:
        row = by_id[fingerprint]
        prior = priors[row.trader_id]
        trader = stats[row.trader_id.value]

        if kind == 0:
            protected_profit = max(Decimal(0), realized_pnl)
            base_protected = protected_profit >= SURVIVAL_CAPITAL_USD
            mode = (
                "PROTECTED_FULL_CAPACITY"
                if base_protected
                else "SURVIVAL_MINIMAL_SEED"
            )
            reject: str | None = None
            risk = Decimal(0)

            if capital <= 0:
                reject = "INSOLVENT_CAPITAL"
            elif prior.expected_r <= 0:
                reject = "NON_POSITIVE_PREWINDOW_CAUSAL_EXPECTATION"
            elif base_protected:
                available_loss_capacity = max(
                    Decimal(0),
                    protected_profit - reserved_stressed_loss,
                )
                if available_loss_capacity <= 0:
                    reject = "NO_UNRESERVED_PROTECTED_LOSS_CAPACITY"
                else:
                    risk = available_loss_capacity / prior.loss_envelope_r
            else:
                stressed_seed_reserve = (
                    NORMALIZED_MINIMUM_SEED_RISK_USD
                    * prior.loss_envelope_r
                )
                available_loss_capacity = max(
                    Decimal(0),
                    capital - reserved_stressed_loss,
                )
                if available_loss_capacity < stressed_seed_reserve:
                    reject = "INSUFFICIENT_STRESSED_CAPACITY_FOR_MINIMUM_SEED"
                else:
                    risk = NORMALIZED_MINIMUM_SEED_RISK_USD

            if reject is not None:
                trader["rejected"] += 1
                trader["rejects"][reject] += 1
                ledger.append(
                    {
                        "fingerprint": fingerprint,
                        "trader": row.trader_id.value,
                        "symbol": row.symbol,
                        "signal_at": row.signal_at.isoformat(),
                        "entry_at": row.entry_at.isoformat(),
                        "exit_at": row.exit_at.isoformat(),
                        "decision": "REJECT",
                        "reason": reject,
                        "sizing_mode": mode,
                        "base_protected": base_protected,
                        "prior_expected_r": str(prior.expected_r),
                        "prior_loss_envelope_r": str(prior.loss_envelope_r),
                        "assigned_risk_usd": "0",
                        "observed_outcome_r": str(row.outcome_r),
                        "realized_pnl_usd": None,
                        "capital_before_usd": _money(capital),
                        "capital_after_usd": _money(capital),
                    }
                )
                continue

            stressed_reserve = risk * prior.loss_envelope_r
            if base_protected:
                available = max(
                    Decimal(0),
                    protected_profit - reserved_stressed_loss,
                )
                if stressed_reserve > available:
                    raise ValueError("protected stressed-loss double-spend")
            reserved_stressed_loss += stressed_reserve
            peak_reserved_stressed_loss = max(
                peak_reserved_stressed_loss,
                reserved_stressed_loss,
            )
            open_positions[fingerprint] = (risk, stressed_reserve)
            trader["executed"] += 1
            trader["risk"] += risk
            if base_protected:
                trader["protected"] += 1
            else:
                trader["minimal"] += 1
            entry_records[fingerprint] = {
                "fingerprint": fingerprint,
                "trader": row.trader_id.value,
                "symbol": row.symbol,
                "signal_at": row.signal_at.isoformat(),
                "entry_at": row.entry_at.isoformat(),
                "exit_at": row.exit_at.isoformat(),
                "decision": "EXECUTE",
                "reason": "CAUSAL_EXPECTATION_AND_STRESSED_CAPITAL_ALLOW",
                "sizing_mode": mode,
                "base_protected": base_protected,
                "prior_expected_r": str(prior.expected_r),
                "prior_expected_minutes": str(prior.expected_minutes),
                "prior_loss_envelope_r": str(prior.loss_envelope_r),
                "assigned_risk_usd": _money(risk),
                "stressed_loss_reserve_usd": _money(stressed_reserve),
                "observed_outcome_r": str(row.outcome_r),
                "capital_before_usd": _money(capital),
                "cumulative_pnl_before_usd": _money(realized_pnl),
            }
            continue

        if fingerprint not in open_positions:
            continue

        risk, stressed_reserve = open_positions.pop(fingerprint)
        reserved_stressed_loss -= stressed_reserve
        if reserved_stressed_loss < 0:
            raise ValueError("stressed-loss reserve went negative")

        envelope_breach = (
            row.outcome_r < 0
            and -row.outcome_r > prior.loss_envelope_r
        )
        if envelope_breach:
            trader["envelope_breaches"] += 1
            loss_envelope_breaches += 1

        delta = risk * row.outcome_r
        realized_pnl += delta
        capital = INITIAL_SEED_USD + realized_pnl
        peak_capital = max(peak_capital, capital)
        minimum_capital = min(minimum_capital, capital)
        max_drawdown = max(max_drawdown, peak_capital - capital)

        if first_protected_at is None and realized_pnl >= SURVIVAL_CAPITAL_USD:
            first_protected_at = at
        if (
            first_protected_at is not None
            and at >= first_protected_at
            and capital < INITIAL_SEED_USD
        ):
            seed_penetrations += 1
            if first_seed_penetration_at is None:
                first_seed_penetration_at = at
        if capital <= 0 and insolvency_at is None:
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

        record = entry_records.pop(fingerprint)
        record["loss_envelope_breached"] = envelope_breach
        record["realized_pnl_usd"] = _money(delta)
        record["capital_after_usd"] = _money(capital)
        record["cumulative_pnl_after_usd"] = _money(realized_pnl)
        record["settled_at"] = at.isoformat()
        ledger.append(record)

    if open_positions or reserved_stressed_loss != 0:
        raise ValueError("experiment ended with unsettled capacity")

    per_trader: dict[str, dict[str, Any]] = {}
    reconciled = Decimal(0)
    total_executed = total_wins = total_losses = total_be = 0
    for spec in SOURCE_SPECS:
        name = spec.trader_id.value
        row = stats[name]
        prior = priors[spec.trader_id]
        net = row["net"]
        reconciled += net
        total_executed += row["executed"]
        total_wins += row["wins"]
        total_losses += row["losses"]
        total_be += row["breakeven"]
        pf = (
            None
            if row["gross_loss"] == 0
            else row["gross_profit"] / abs(row["gross_loss"])
        )
        per_trader[name] = {
            "prewindow_train_rows": prior.train_rows,
            "prewindow_expected_r": str(prior.expected_r),
            "prewindow_expected_minutes": str(prior.expected_minutes),
            "prewindow_worst_loss_r": str(prior.worst_loss_r),
            "causal_loss_envelope_r": str(prior.loss_envelope_r),
            "opportunities": row["opportunities"],
            "executed_entries": row["executed"],
            "rejected_entries": row["rejected"],
            "wins": row["wins"],
            "losses": row["losses"],
            "breakeven": row["breakeven"],
            "gross_profit_usd": _money(row["gross_profit"]),
            "gross_loss_usd": _money(row["gross_loss"]),
            "net_pnl_usd": _money(net),
            "profit_factor": None if pf is None else str(pf),
            "total_risk_assigned_usd": _money(row["risk"]),
            "minimal_seed_entries": row["minimal"],
            "protected_full_capacity_entries": row["protected"],
            "loss_envelope_breaches": row["envelope_breaches"],
            "reject_reasons": dict(sorted(row["rejects"].items())),
        }

    if reconciled != realized_pnl:
        raise ValueError("per-Trader PnL reconciliation failed")
    if total_executed != total_wins + total_losses + total_be:
        raise ValueError("trade outcome reconciliation failed")

    milestones: dict[str, Any] = {}
    for milestone in MILESTONES_USD:
        hit = milestone_hits.get(milestone)
        milestones[str(milestone)] = {
            "reached": hit is not None,
            "reached_at": None if hit is None else hit.isoformat(),
            "calendar_days_elapsed": None if hit is None else _days(start, hit),
            "trading_days_elapsed": (
                None
                if hit is None
                else sum(day <= hit.date() for day in trading_dates)
            ),
        }

    survival = insolvency_at is None and minimum_capital > 0
    protection = seed_penetrations == 0
    target300 = Decimal("300") in milestone_hits

    report: dict[str, Any] = {
        "schema": "qore.cibo.research.60usd-6m-capitalization.v2",
        "experiment_id": EXPERIMENT_ID,
        "status": "COMPLETED_MEASUREMENT",
        "measurement_window": {
            "prewindow_train_start": train_start.isoformat(),
            "prewindow_train_end": start.isoformat(),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "fixed_six_calendar_month_window": True,
            "certification_holdout_claimed": False,
            "purpose": "CAPABILITY_MEASUREMENT_ONLY",
        },
        "capital_contract": {
            "initial_seed_usd": _money(INITIAL_SEED_USD),
            "survival_capital_usd": _money(SURVIVAL_CAPITAL_USD),
            "normalized_minimum_seed_risk_usd": _money(
                NORMALIZED_MINIMUM_SEED_RISK_USD
            ),
            "loss_envelope_stress_multiplier": str(LOSS_ENVELOPE_STRESS),
            "profit_cap_enabled": False,
            "profit_cap_usd": None,
            "pre_protection_mode": "SURVIVAL_MINIMAL_SEED",
            "post_protection_mode": "PROTECTED_FULL_CAPACITY",
            "post_protection_rule": (
                "RISK = UNRESERVED_PROTECTED_PROFIT / CAUSAL_LOSS_ENVELOPE_R"
            ),
            "outcome_aware_sizing": False,
            "future_holdout_used_for_priors": False,
            "martingale": False,
            "loss_recovery_sizing": False,
            "same_timestamp_exit_recycling": False,
        },
        "evidence_scope": {
            "represented_traders": 7,
            "r_denominated_phase18_evidence": True,
            "historical_provider_economics_complete": False,
            "usd_numeraire": (
                "ASSIGNED_NORMALIZED_STRUCTURAL_STOP_RISK_X_OBSERVED_R"
            ),
            "intratrade_protected_floor_replayed": False,
            "intratrade_expansion_replayed": False,
            "full_broker_executable_profit_claimed": False,
        },
        "portfolio": {
            "opportunities": len(holdout),
            "executed_entries": total_executed,
            "rejected_entries": len(holdout) - total_executed,
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
                None if first_protected_at is None else first_protected_at.isoformat()
            ),
            "protection_seed_penetration_count": seed_penetrations,
            "first_protection_seed_penetration_at": (
                None
                if first_seed_penetration_at is None
                else first_seed_penetration_at.isoformat()
            ),
            "loss_envelope_breaches": loss_envelope_breaches,
            "insolvency_at": (
                None if insolvency_at is None else insolvency_at.isoformat()
            ),
            "capital_amplification_net_profit_over_seed": str(
                realized_pnl / INITIAL_SEED_USD
            ),
        },
        "milestones": milestones,
        "per_trader": per_trader,
        "gates": {
            "survival": "PASS" if survival else "FAIL",
            "capital_protection_integrity": "PASS" if protection else "FAIL",
            "net_profit_gt_300": "PASS" if target300 else "FAIL",
            "full_experiment": (
                "PASS" if survival and protection and target300 else "FAIL"
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
    (output_dir / "report-v2.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "trade-ledger-v2.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in ledger),
        encoding="utf-8",
    )

    with (output_dir / "per-trader-v2.csv").open(
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
                "rejected_entries",
                "wins",
                "losses",
                "breakeven",
                "net_pnl_usd",
                "profit_factor",
                "minimal_seed_entries",
                "protected_full_capacity_entries",
                "loss_envelope_breaches",
                "prewindow_expected_r",
                "causal_loss_envelope_r",
            ]
        )
        for trader_name, row in per_trader.items():
            writer.writerow(
                [
                    trader_name,
                    row["opportunities"],
                    row["executed_entries"],
                    row["rejected_entries"],
                    row["wins"],
                    row["losses"],
                    row["breakeven"],
                    row["net_pnl_usd"],
                    row["profit_factor"],
                    row["minimal_seed_entries"],
                    row["protected_full_capacity_entries"],
                    row["loss_envelope_breaches"],
                    row["prewindow_expected_r"],
                    row["causal_loss_envelope_r"],
                ]
            )

    m300 = milestones["300"]
    summary = [
        "# CIBO USD60 / 6M Capitalization Capability Experiment V2",
        "",
        f"- Measurement: {start.isoformat()} -> {end.isoformat()}",
        f"- Causal prior only through: {start.isoformat()}",
        f"- Initial seed: USD {_money(INITIAL_SEED_USD)}",
        f"- Net realized profit: USD {_money(realized_pnl)}",
        f"- Ending realized capital: USD {_money(capital)}",
        f"- Minimum realized capital: USD {_money(minimum_capital)}",
        f"- Max realized drawdown: USD {_money(max_drawdown)}",
        f"- Entries: {total_executed}",
        f"- Wins / Losses / BE: {total_wins} / {total_losses} / {total_be}",
        f"- Survival: {report['gates']['survival']}",
        f"- Protection integrity: {report['gates']['capital_protection_integrity']}",
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
            "## Evidence boundary",
            "",
            (
                "V2 is causal at the closed-trade level and protects the seed "
                "with a pre-window stressed-loss envelope. It still does not "
                "claim missing intratrade protected-floor expansion or exact "
                "historical broker economics."
            ),
        ]
    )
    (output_dir / "SUMMARY-V2.md").write_text(
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
