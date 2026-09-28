"""Independent CIBO USD60 / six-month capitalization capability experiment.

Measurement only. This is not Phase20/21/22 certification evidence.

The seven retained Phase18 lineages are R-denominated and do not carry complete
historical broker economics. Therefore the experiment uses normalized USD
structural-stop risk:

    realized_pnl_usd = assigned_stop_risk_usd * observed_structural_R

Initial seed is USD60. Before USD60 of realized protected profit exists, CIBO
uses a frozen USD1 normalized minimum seed. After protection, CIBO may deploy
all currently unreserved protected-profit capacity. There is no profit cap.
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
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    frozen_train_prior_for,
)

getcontext().prec = 50

EXPERIMENT_ID = "CIBO_60USD_6M_CAPITALIZATION_CAPABILITY_EXPERIMENT_V1"
INITIAL_SEED_USD = Decimal("60")
SURVIVAL_CAPITAL_USD = Decimal("60")
NORMALIZED_MINIMUM_SEED_RISK_USD = Decimal("1")
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
    normalized_outcome_r: Decimal
    expected_structural_r: Decimal
    expected_capital_minutes: Decimal

    @property
    def expected_efficiency(self) -> Decimal:
        return self.expected_structural_r / self.expected_capital_minutes


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _fingerprint(
    *,
    trader_id: TraderLineage,
    symbol: str,
    signal_at: datetime,
    entry_at: datetime,
    exit_at: datetime,
    index: int,
) -> str:
    payload = {
        "trader_id": trader_id.value,
        "symbol": symbol,
        "signal_at": signal_at.isoformat(),
        "entry_at": entry_at.isoformat(),
        "exit_at": exit_at.isoformat(),
        "index": index,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _parse_source(
    *,
    path: Path,
    spec: SourceSpec,
    start: datetime,
    end: datetime,
) -> list[Trade]:
    prior = frozen_train_prior_for(spec.trader_id)
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
            _aware(value, name)
        if not signal_at <= entry_at < exit_at:
            raise ValueError(
                f"{spec.trader_id.value} invalid chronology at source row {index}"
            )
        if entry_at < start or exit_at > end:
            continue
        outcome = Decimal(str(row[spec.outcome_field]))
        if not outcome.is_finite():
            raise ValueError(
                f"{spec.trader_id.value} non-finite R at source row {index}"
            )
        symbol = spec.qore_symbol or str(row["symbol"])
        trades.append(
            Trade(
                trader_id=spec.trader_id,
                symbol=symbol,
                fingerprint=_fingerprint(
                    trader_id=spec.trader_id,
                    symbol=symbol,
                    signal_at=signal_at,
                    entry_at=entry_at,
                    exit_at=exit_at,
                    index=index,
                ),
                signal_at=signal_at,
                entry_at=entry_at,
                exit_at=exit_at,
                normalized_outcome_r=outcome,
                expected_structural_r=prior.expected_structural_r,
                expected_capital_minutes=prior.expected_capital_minutes,
            )
        )
    return trades


def _money(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.000001")), "f")


def _days_elapsed(start: datetime, at: datetime) -> str:
    days = Decimal(str((at - start).total_seconds())) / Decimal("86400")
    return format(days, "f")


def run_experiment(
    *,
    source_paths: dict[str, Path],
    output_dir: Path,
    start: datetime,
    end: datetime,
    initial_seed_usd: Decimal = INITIAL_SEED_USD,
    survival_capital_usd: Decimal = SURVIVAL_CAPITAL_USD,
    minimum_seed_risk_usd: Decimal = NORMALIZED_MINIMUM_SEED_RISK_USD,
) -> dict[str, Any]:
    if end <= start:
        raise ValueError("experiment end must follow start")
    if initial_seed_usd <= 0 or survival_capital_usd <= 0:
        raise ValueError("capital inputs must be positive")
    if minimum_seed_risk_usd <= 0:
        raise ValueError("minimum seed risk must be positive")
    if set(source_paths) != {spec.key for spec in SOURCE_SPECS}:
        raise ValueError("seven-Trader source set is incomplete")

    all_trades: list[Trade] = []
    counts: dict[str, int] = {}
    for spec in SOURCE_SPECS:
        parsed = _parse_source(
            path=source_paths[spec.key],
            spec=spec,
            start=start,
            end=end,
        )
        counts[spec.trader_id.value] = len(parsed)
        all_trades.extend(parsed)

    required = {spec.trader_id for spec in SOURCE_SPECS}
    represented = {trade.trader_id for trade in all_trades}
    if represented != required:
        missing = sorted(item.value for item in required - represented)
        raise ValueError(f"six-month window missing Traders: {missing}")

    by_id = {trade.fingerprint: trade for trade in all_trades}
    if len(by_id) != len(all_trades):
        raise ValueError("fingerprint collision")

    events: list[tuple[datetime, int, Decimal, str, str]] = []
    for trade in all_trades:
        events.append(
            (
                trade.entry_at,
                0,
                -trade.expected_efficiency,
                trade.trader_id.value,
                trade.fingerprint,
            )
        )
        events.append(
            (
                trade.exit_at,
                1,
                Decimal(0),
                trade.trader_id.value,
                trade.fingerprint,
            )
        )
    events.sort()

    stats: dict[str, dict[str, Any]] = {}
    for spec in SOURCE_SPECS:
        stats[spec.trader_id.value] = {
            "opportunities": counts[spec.trader_id.value],
            "executed_entries": 0,
            "rejected_entries": 0,
            "wins": 0,
            "losses": 0,
            "breakeven": 0,
            "gross_profit_usd": Decimal(0),
            "gross_loss_usd": Decimal(0),
            "net_pnl_usd": Decimal(0),
            "total_risk_assigned_usd": Decimal(0),
            "minimal_seed_entries": 0,
            "protected_full_capacity_entries": 0,
            "reject_reasons": defaultdict(int),
        }

    realized_pnl = Decimal(0)
    realized_capital = initial_seed_usd
    peak_capital = realized_capital
    min_capital = realized_capital
    max_drawdown = Decimal(0)
    reserved_risk = Decimal(0)
    peak_reserved_risk = Decimal(0)
    open_risk: dict[str, Decimal] = {}
    entry_record: dict[str, dict[str, Any]] = {}
    first_protected_at: datetime | None = None
    first_seed_penetration_at: datetime | None = None
    seed_penetrations = 0
    insolvency_at: datetime | None = None
    milestone_hits: dict[Decimal, datetime] = {}
    ledger: list[dict[str, Any]] = []
    trading_dates = sorted({trade.entry_at.date() for trade in all_trades})

    for at, kind, _rank, _trader_name, fingerprint in events:
        trade = by_id[fingerprint]
        trader = stats[trade.trader_id.value]

        if kind == 0:
            capital_before = realized_capital
            pnl_before = realized_pnl
            protected_profit = max(Decimal(0), realized_pnl)
            base_protected = protected_profit >= survival_capital_usd
            mode = (
                "PROTECTED_FULL_CAPACITY"
                if base_protected
                else "SURVIVAL_MINIMAL_SEED"
            )
            reject: str | None = None
            risk = Decimal(0)

            if realized_capital <= 0:
                reject = "INSOLVENT_CAPITAL"
            elif trade.expected_structural_r <= 0:
                reject = "NON_POSITIVE_FROZEN_CAUSAL_EXPECTATION"
            elif base_protected:
                available = max(
                    Decimal(0),
                    protected_profit - reserved_risk,
                )
                if available <= 0:
                    reject = "NO_UNRESERVED_PROTECTED_CAPACITY"
                else:
                    risk = available
            else:
                available = max(
                    Decimal(0),
                    realized_capital - reserved_risk,
                )
                if available < minimum_seed_risk_usd:
                    reject = "INSUFFICIENT_CAPACITY_FOR_MINIMUM_SEED"
                else:
                    risk = minimum_seed_risk_usd

            if reject is not None:
                trader["rejected_entries"] += 1
                trader["reject_reasons"][reject] += 1
                ledger.append(
                    {
                        "fingerprint": fingerprint,
                        "trader": trade.trader_id.value,
                        "symbol": trade.symbol,
                        "signal_at": trade.signal_at.isoformat(),
                        "entry_at": trade.entry_at.isoformat(),
                        "exit_at": trade.exit_at.isoformat(),
                        "decision": "REJECT",
                        "reason": reject,
                        "sizing_mode": mode,
                        "base_protected": base_protected,
                        "expected_structural_r": str(
                            trade.expected_structural_r
                        ),
                        "assigned_risk_usd": "0",
                        "normalized_outcome_r": str(
                            trade.normalized_outcome_r
                        ),
                        "realized_pnl_usd": None,
                        "capital_before_usd": _money(capital_before),
                        "capital_after_usd": _money(capital_before),
                        "cumulative_pnl_before_usd": _money(pnl_before),
                        "cumulative_pnl_after_usd": _money(pnl_before),
                    }
                )
                continue

            if risk <= 0:
                raise ValueError("accepted risk must be positive")
            if base_protected and risk > protected_profit - reserved_risk:
                raise ValueError("protected capacity double-spend")
            if not base_protected and risk != minimum_seed_risk_usd:
                raise ValueError("pre-protection sizing drift")

            reserved_risk += risk
            peak_reserved_risk = max(peak_reserved_risk, reserved_risk)
            open_risk[fingerprint] = risk
            trader["executed_entries"] += 1
            trader["total_risk_assigned_usd"] += risk
            if base_protected:
                trader["protected_full_capacity_entries"] += 1
            else:
                trader["minimal_seed_entries"] += 1
            entry_record[fingerprint] = {
                "fingerprint": fingerprint,
                "trader": trade.trader_id.value,
                "symbol": trade.symbol,
                "signal_at": trade.signal_at.isoformat(),
                "entry_at": trade.entry_at.isoformat(),
                "exit_at": trade.exit_at.isoformat(),
                "decision": "EXECUTE",
                "reason": "CAUSAL_EXPECTATION_AND_CAPITAL_ALLOW",
                "sizing_mode": mode,
                "base_protected": base_protected,
                "expected_structural_r": str(
                    trade.expected_structural_r
                ),
                "expected_capital_minutes": str(
                    trade.expected_capital_minutes
                ),
                "assigned_risk_usd": _money(risk),
                "normalized_outcome_r": str(trade.normalized_outcome_r),
                "capital_before_usd": _money(capital_before),
                "cumulative_pnl_before_usd": _money(pnl_before),
            }
            continue

        if fingerprint not in open_risk:
            continue

        risk = open_risk.pop(fingerprint)
        reserved_risk -= risk
        if reserved_risk < 0:
            raise ValueError("reserved risk accounting went negative")

        delta = risk * trade.normalized_outcome_r
        realized_pnl += delta
        realized_capital = initial_seed_usd + realized_pnl
        peak_capital = max(peak_capital, realized_capital)
        min_capital = min(min_capital, realized_capital)
        max_drawdown = max(max_drawdown, peak_capital - realized_capital)

        if first_protected_at is None and realized_pnl >= survival_capital_usd:
            first_protected_at = at
        if (
            first_protected_at is not None
            and at >= first_protected_at
            and realized_capital < initial_seed_usd
        ):
            seed_penetrations += 1
            if first_seed_penetration_at is None:
                first_seed_penetration_at = at
        if realized_capital <= 0 and insolvency_at is None:
            insolvency_at = at

        for milestone in MILESTONES_USD:
            if milestone not in milestone_hits and realized_pnl >= milestone:
                milestone_hits[milestone] = at

        if delta > 0:
            trader["wins"] += 1
            trader["gross_profit_usd"] += delta
        elif delta < 0:
            trader["losses"] += 1
            trader["gross_loss_usd"] += delta
        else:
            trader["breakeven"] += 1
        trader["net_pnl_usd"] += delta

        row = entry_record.pop(fingerprint)
        row["realized_pnl_usd"] = _money(delta)
        row["capital_after_usd"] = _money(realized_capital)
        row["cumulative_pnl_after_usd"] = _money(realized_pnl)
        row["settled_at"] = at.isoformat()
        ledger.append(row)

    if open_risk or reserved_risk != 0:
        raise ValueError("experiment ended with unsettled risk")

    per_trader: dict[str, dict[str, Any]] = {}
    reconciled_pnl = Decimal(0)
    executed = wins = losses = breakeven = 0
    for trader_name, row in sorted(stats.items()):
        gross_profit = row["gross_profit_usd"]
        gross_loss = row["gross_loss_usd"]
        net = row["net_pnl_usd"]
        reconciled_pnl += net
        executed += row["executed_entries"]
        wins += row["wins"]
        losses += row["losses"]
        breakeven += row["breakeven"]
        pf = None if gross_loss == 0 else gross_profit / abs(gross_loss)
        per_trader[trader_name] = {
            "opportunities": row["opportunities"],
            "executed_entries": row["executed_entries"],
            "rejected_entries": row["rejected_entries"],
            "wins": row["wins"],
            "losses": row["losses"],
            "breakeven": row["breakeven"],
            "gross_profit_usd": _money(gross_profit),
            "gross_loss_usd": _money(gross_loss),
            "net_pnl_usd": _money(net),
            "profit_factor": None if pf is None else str(pf),
            "total_risk_assigned_usd": _money(
                row["total_risk_assigned_usd"]
            ),
            "minimal_seed_entries": row["minimal_seed_entries"],
            "protected_full_capacity_entries": (
                row["protected_full_capacity_entries"]
            ),
            "reject_reasons": dict(sorted(row["reject_reasons"].items())),
        }

    if reconciled_pnl != realized_pnl:
        raise ValueError("Trader PnL does not reconcile")
    if executed != wins + losses + breakeven:
        raise ValueError("win/loss accounting drift")

    milestone_report: dict[str, Any] = {}
    for milestone in MILESTONES_USD:
        hit = milestone_hits.get(milestone)
        milestone_report[str(milestone)] = {
            "reached": hit is not None,
            "reached_at": None if hit is None else hit.isoformat(),
            "calendar_days_elapsed": (
                None if hit is None else _days_elapsed(start, hit)
            ),
            "trading_days_elapsed": (
                None
                if hit is None
                else sum(day <= hit.date() for day in trading_dates)
            ),
        }

    survival_pass = insolvency_at is None and min_capital > 0
    protection_pass = seed_penetrations == 0
    target_pass = Decimal("300") in milestone_hits

    report: dict[str, Any] = {
        "schema": "qore.cibo.research.60usd-6m-capitalization.v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "COMPLETED_MEASUREMENT",
        "measurement_window": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "fixed_six_calendar_month_window": True,
            "certification_holdout_claimed": False,
            "purpose": "CAPABILITY_MEASUREMENT_ONLY",
        },
        "capital_contract": {
            "initial_seed_usd": _money(initial_seed_usd),
            "survival_capital_usd": _money(survival_capital_usd),
            "normalized_minimum_seed_risk_usd": _money(
                minimum_seed_risk_usd
            ),
            "profit_cap_enabled": False,
            "profit_cap_usd": None,
            "pre_protection_mode": "SURVIVAL_MINIMAL_SEED",
            "post_protection_mode": "PROTECTED_FULL_CAPACITY",
            "post_protection_deployable_capacity": (
                "ALL_UNRESERVED_POSITIVE_REALIZED_PROTECTED_PROFIT"
            ),
            "outcome_aware_sizing": False,
            "martingale": False,
            "loss_recovery_sizing": False,
            "same_timestamp_exit_recycling": False,
        },
        "evidence_scope": {
            "represented_traders": len(represented),
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
            "opportunities": len(all_trades),
            "executed_entries": executed,
            "rejected_entries": len(all_trades) - executed,
            "wins": wins,
            "losses": losses,
            "breakeven": breakeven,
            "net_realized_profit_usd": _money(realized_pnl),
            "ending_realized_capital_usd": _money(realized_capital),
            "minimum_realized_capital_usd": _money(min_capital),
            "peak_realized_capital_usd": _money(peak_capital),
            "max_realized_drawdown_usd": _money(max_drawdown),
            "peak_reserved_risk_usd": _money(peak_reserved_risk),
            "first_base_protected_at": (
                None if first_protected_at is None else first_protected_at.isoformat()
            ),
            "protection_seed_penetration_count": seed_penetrations,
            "first_protection_seed_penetration_at": (
                None
                if first_seed_penetration_at is None
                else first_seed_penetration_at.isoformat()
            ),
            "insolvency_at": (
                None if insolvency_at is None else insolvency_at.isoformat()
            ),
            "capital_amplification_net_profit_over_seed": str(
                realized_pnl / initial_seed_usd
            ),
        },
        "milestones": milestone_report,
        "per_trader": per_trader,
        "gates": {
            "survival": "PASS" if survival_pass else "FAIL",
            "capital_protection_integrity": (
                "PASS" if protection_pass else "FAIL"
            ),
            "net_profit_gt_300": "PASS" if target_pass else "FAIL",
            "full_experiment": (
                "PASS"
                if survival_pass and protection_pass and target_pass
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
    (output_dir / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "trade-ledger.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in ledger),
        encoding="utf-8",
    )

    with (output_dir / "per-trader.csv").open(
        "w", encoding="utf-8", newline=""
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
                "gross_profit_usd",
                "gross_loss_usd",
                "net_pnl_usd",
                "profit_factor",
                "total_risk_assigned_usd",
                "minimal_seed_entries",
                "protected_full_capacity_entries",
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
                    row["gross_profit_usd"],
                    row["gross_loss_usd"],
                    row["net_pnl_usd"],
                    row["profit_factor"],
                    row["total_risk_assigned_usd"],
                    row["minimal_seed_entries"],
                    row["protected_full_capacity_entries"],
                ]
            )

    m300 = milestone_report["300"]
    summary = [
        "# CIBO USD60 / 6M Capitalization Capability Experiment V1",
        "",
        f"- Window: {start.isoformat()} -> {end.isoformat()}",
        f"- Initial seed: USD {_money(initial_seed_usd)}",
        f"- Net realized profit: USD {_money(realized_pnl)}",
        f"- Ending realized capital: USD {_money(realized_capital)}",
        f"- Minimum realized capital: USD {_money(min_capital)}",
        f"- Max realized drawdown: USD {_money(max_drawdown)}",
        f"- Executed entries: {executed}",
        f"- Wins / Losses / BE: {wins} / {losses} / {breakeven}",
        f"- Survival: {report['gates']['survival']}",
        (
            "- Capital protection integrity: "
            f"{report['gates']['capital_protection_integrity']}"
        ),
        f"- +USD300 reached: {m300['reached']}",
    ]
    if m300["reached"]:
        summary.extend(
            [
                f"- +USD300 reached at: {m300['reached_at']}",
                (
                    "- +USD300 calendar days elapsed: "
                    f"{m300['calendar_days_elapsed']}"
                ),
                (
                    "- +USD300 trading days elapsed: "
                    f"{m300['trading_days_elapsed']}"
                ),
            ]
        )
    summary.extend(
        [
            "",
            "## Scope caveat",
            "",
            (
                "V1 is a closed-trade normalized-risk measurement. It does "
                "not fabricate historical broker economics or missing "
                "intratrade protected-floor/expansion observations."
            ),
        ]
    )
    (output_dir / "SUMMARY.md").write_text(
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
    parser.add_argument(
        "--minimum-seed-risk-usd",
        default=str(NORMALIZED_MINIMUM_SEED_RISK_USD),
    )
    args = parser.parse_args()
    source_paths = {
        spec.key: getattr(args, spec.key)
        for spec in SOURCE_SPECS
    }
    report = run_experiment(
        source_paths=source_paths,
        output_dir=args.output_dir,
        start=datetime.fromisoformat(args.start),
        end=datetime.fromisoformat(args.end),
        minimum_seed_risk_usd=Decimal(args.minimum_seed_risk_usd),
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
