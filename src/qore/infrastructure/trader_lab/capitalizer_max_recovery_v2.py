"""MAX_RECOVERY V2: H1-arbitrated causal recovery union.

V1 proved that causal closeback arbitration plus protected-swing rescue can add
density, but a plain union can theoretically double-count two recovery families
inside the same market/H1.

V2 fixes that accounting:
- load the frozen causal-arbitration trade ledger;
- reconstruct protected-swing geometry rescues from frozen evidence;
- group candidates by symbol + operating date + H1;
- earliest causal executable timestamp wins that market/H1;
- if opposite sides tie at the earliest timestamp, fail closed for that H1;
- same-side duplicates resolve deterministically in favor of the already-valid
  arbitration baseline;
- portfolio MAX3/session/date is then applied unchanged.

No threshold relaxation, target change, or outcome-based admission is allowed.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_wait5_protected_swing_rescue_2y_v1 as rescue,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    _index_day_inputs,
)

IDENTITY = "QORE_CAPITALIZER_MAX_RECOVERY_V2"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_MAX_RECOVERY_V2"
ARBITRATION_RAW = 854
ARBITRATION_MAX3 = 841


@dataclass(frozen=True, slots=True)
class RecoveryTrade:
    symbol: str
    session: str
    operating_date: str
    side: str
    h1_open: str
    h1_deadline: str
    entry_at: str
    exit_at: str
    realized_gross_r: str
    exit_reason: str
    same_minute_stop_target_ambiguity: bool
    provenance: str


def _load_arbitration(root: Path) -> tuple[RecoveryTrade, ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-v3-source-first-no-rearm-"
            "closeback-arbitration-2y-v1-trades.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("MAX_RECOVERY V2 requires one arbitration ledger")
    rows: list[RecoveryTrade] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            rows.append(
                RecoveryTrade(
                    symbol=str(raw["symbol"]),
                    session=str(raw["session"]),
                    operating_date=str(raw["operating_date"]),
                    side=str(raw["side"]),
                    h1_open=str(raw["h1_open"]),
                    h1_deadline=str(raw["h1_deadline"]),
                    entry_at=str(raw["entry_at"]),
                    exit_at=str(raw["exit_at"]),
                    realized_gross_r=str(raw["realized_gross_r"]),
                    exit_reason=str(raw["exit_reason"]),
                    same_minute_stop_target_ambiguity=bool(
                        raw["same_minute_stop_target_ambiguity"]
                    ),
                    provenance="CAUSAL_ARBITRATION_BASE",
                )
            )
    return tuple(rows)


def _protected_additions(
    *,
    stop_rows: tuple[dict[str, Any], ...],
    funnel_rows: tuple[dict[str, Any], ...],
    execution_by_day: dict[str, tuple[Any, ...]],
) -> tuple[RecoveryTrade, ...]:
    funnel_by_key = {rescue._funnel_key(row): row for row in funnel_rows}
    additions: list[RecoveryTrade] = []

    for row in stop_rows:
        if row.get("protected_at_mss_stop_valid") is not True:
            continue
        protected_raw = row.get("protected_at_mss_stop_price")
        if protected_raw is None:
            continue

        funnel = funnel_by_key.get(rescue._stop_key(row))
        if funnel is None:
            raise ValueError("MAX_RECOVERY V2 missing funnel counterpart")

        day = str(row["operating_date"])
        execution = execution_by_day.get(day, ())
        if not execution:
            raise ValueError("MAX_RECOVERY V2 missing execution day")

        entry_at = datetime.fromisoformat(str(row["final_fill_at"]))
        mss_at = datetime.fromisoformat(str(row["source_first_mss_at"]))
        deadline = datetime.fromisoformat(str(funnel["h1_deadline"]))
        h1_open = deadline - timedelta(hours=1)
        entry_price = Decimal(str(row["entry_price"]))
        stop_price = Decimal(str(protected_raw))
        side = str(row["side"])

        entry_index = next(
            (
                index
                for index, bar in enumerate(execution)
                if bar.opened_at == entry_at
            ),
            None,
        )
        if entry_index is None:
            raise ValueError("MAX_RECOVERY V2 protected fill not found")

        prefill = tuple(
            bar for bar in execution if mss_at <= bar.opened_at < entry_at
        )
        if any(
            rescue._stop_hit(bar, side=side, stop_price=stop_price)
            for bar in prefill
        ):
            continue

        risk = abs(entry_price - stop_price)
        if risk <= 0:
            raise ValueError("MAX_RECOVERY V2 requires positive protected risk")
        target_price = (
            entry_price + Decimal("2") * risk
            if side == "LONG"
            else entry_price - Decimal("2") * risk
        )
        realized, reason, _, ambiguous, exit_at = rescue.v3._lifecycle(
            execution,
            entry_index=entry_index,
            side=CapitalizerSide(side),
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            deadline=deadline,
        )
        additions.append(
            RecoveryTrade(
                symbol=str(row["symbol"]),
                session=str(row["session"]),
                operating_date=day,
                side=side,
                h1_open=h1_open.isoformat(),
                h1_deadline=deadline.isoformat(),
                entry_at=entry_at.isoformat(),
                exit_at=exit_at.isoformat(),
                realized_gross_r=str(realized),
                exit_reason=reason,
                same_minute_stop_target_ambiguity=ambiguous,
                provenance="PROTECTED_SWING_GEOMETRY_RESCUE",
            )
        )
    return tuple(
        sorted(
            additions,
            key=lambda item: (datetime.fromisoformat(item.entry_at), item.symbol),
        )
    )


def _h1_key(trade: RecoveryTrade) -> tuple[str, str, str]:
    return (trade.symbol, trade.operating_date, trade.h1_open)


def _arbitrate_h1(
    trades: tuple[RecoveryTrade, ...],
) -> tuple[tuple[RecoveryTrade, ...], int, int]:
    grouped: dict[tuple[str, str, str], list[RecoveryTrade]] = defaultdict(list)
    for trade in trades:
        grouped[_h1_key(trade)].append(trade)

    selected: list[RecoveryTrade] = []
    duplicate_h1 = 0
    opposite_tie_fail_closed = 0
    priority = {
        "CAUSAL_ARBITRATION_BASE": 0,
        "PROTECTED_SWING_GEOMETRY_RESCUE": 1,
    }

    for key in sorted(grouped):
        rows = grouped[key]
        if len(rows) > 1:
            duplicate_h1 += 1
        earliest_at = min(datetime.fromisoformat(item.entry_at) for item in rows)
        earliest = tuple(
            item
            for item in rows
            if datetime.fromisoformat(item.entry_at) == earliest_at
        )
        if len({item.side for item in earliest}) > 1:
            opposite_tie_fail_closed += 1
            continue
        winner = min(
            earliest,
            key=lambda item: (
                priority.get(item.provenance, 99),
                item.provenance,
            ),
        )
        selected.append(winner)

    return (
        tuple(
            sorted(
                selected,
                key=lambda item: (
                    datetime.fromisoformat(item.entry_at),
                    item.symbol,
                ),
            )
        ),
        duplicate_h1,
        opposite_tie_fail_closed,
    )


def _portfolio_max3(
    trades: tuple[RecoveryTrade, ...],
) -> tuple[RecoveryTrade, ...]:
    grouped: dict[str, list[RecoveryTrade]] = defaultdict(list)
    for trade in trades:
        grouped[f"{trade.session}:{trade.operating_date}"].append(trade)
    selected: list[RecoveryTrade] = []
    for key in sorted(grouped):
        ordered = sorted(
            grouped[key],
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
        selected.extend(ordered[:MAX_EXECUTIONS_PER_SESSION])
    return tuple(
        sorted(
            selected,
            key=lambda item: (
                datetime.fromisoformat(item.entry_at),
                item.symbol,
            ),
        )
    )


def _metrics(trades: tuple[RecoveryTrade, ...]) -> dict[str, Any] | None:
    proxy = tuple(
        rescue.PortfolioTrade(
            symbol=item.symbol,
            session=item.session,
            operating_date=item.operating_date,
            entry_at=item.entry_at,
            exit_at=item.exit_at,
            realized_gross_r=item.realized_gross_r,
            exit_reason=item.exit_reason,
            same_minute_stop_target_ambiguity=(
                item.same_minute_stop_target_ambiguity
            ),
            provenance=item.provenance,
        )
        for item in trades
    )
    return rescue._metrics(proxy)


def build_market_report(
    arbitration_root: Path,
    stop_root: Path,
    funnel_root: Path,
    m1_root: Path,
    *,
    session: CapitalizerSession,
) -> tuple[
    dict[str, Any],
    tuple[RecoveryTrade, ...],
    tuple[RecoveryTrade, ...],
]:
    baseline = _load_arbitration(arbitration_root)
    stop_rows = rescue._stop_rows(stop_root)
    funnel_rows = rescue._funnel_rows(funnel_root)

    bars = tuple(iter_cibo_m1(m1_root))
    if not bars:
        raise ValueError("MAX_RECOVERY V2 requires native M1")
    symbol = bars[0].symbol
    if any(item.symbol != symbol for item in baseline):
        raise ValueError("MAX_RECOVERY V2 arbitration/M1 symbol mismatch")

    execution_by_day, _ = _index_day_inputs(bars, session=session)
    protected = _protected_additions(
        stop_rows=stop_rows,
        funnel_rows=funnel_rows,
        execution_by_day=execution_by_day,
    )
    candidate, duplicate_h1, opposite_ties = _arbitrate_h1(
        tuple((*baseline, *protected))
    )

    provenance = Counter(item.provenance for item in candidate)
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "arbitration_raw": len(baseline),
        "protected_raw": len(protected),
        "h1_arbitrated_raw": len(candidate),
        "duplicate_h1_candidates": duplicate_h1,
        "opposite_tie_fail_closed": opposite_ties,
        "selected_provenance": dict(sorted(provenance.items())),
        "one_trade_per_market_h1": True,
        "earliest_causal_entry_wins": True,
        "opposite_tie_fail_closed_policy": True,
        "threshold_relaxations_included": False,
        "target_changes_included": False,
        "outcome_used_for_admission": False,
        "recovery_phase_open": True,
        "target_phase_open": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }, baseline, candidate


def write_market(
    report: dict[str, Any],
    baseline: tuple[RecoveryTrade, ...],
    candidate: tuple[RecoveryTrade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-max-recovery-v2"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for variant, trades in (("baseline", baseline), ("candidate", candidate)):
        with (output / f"{stem}-{variant}-trades.jsonl").open(
            "w",
            encoding="utf-8",
        ) as handle:
            for trade in trades:
                handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.rglob("capitalizer-*-max-recovery-v2.json"))
    if len(paths) != 9:
        raise ValueError(f"MAX_RECOVERY V2 requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def _load_portfolio(
    root: Path,
    *,
    variant: str,
) -> tuple[RecoveryTrade, ...]:
    paths = sorted(
        root.rglob(f"capitalizer-*-max-recovery-v2-{variant}-trades.jsonl")
    )
    if len(paths) != 9:
        raise ValueError(f"MAX_RECOVERY V2 requires 9 {variant} ledgers")
    rows: list[RecoveryTrade] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(RecoveryTrade(**json.loads(line)))
    return tuple(rows)


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    baseline_raw = _load_portfolio(root, variant="baseline")
    candidate_raw = _load_portfolio(root, variant="candidate")
    baseline_max3 = _portfolio_max3(baseline_raw)
    candidate_max3 = _portfolio_max3(candidate_raw)
    baseline_metrics = _metrics(baseline_max3)
    candidate_metrics = _metrics(candidate_max3)
    if baseline_metrics is None or candidate_metrics is None:
        raise ValueError("MAX_RECOVERY V2 requires complete metrics")

    pf_base = Decimal(str(baseline_metrics["profit_factor"]))
    pf_candidate = Decimal(str(candidate_metrics["profit_factor"]))
    total_base = Decimal(str(baseline_metrics["total_r"]))
    total_candidate = Decimal(str(candidate_metrics["total_r"]))
    dd_base = Decimal(str(baseline_metrics["max_drawdown_r"]))
    dd_candidate = Decimal(str(candidate_metrics["max_drawdown_r"]))

    provenance = Counter(item.provenance for item in candidate_max3)
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "baseline_raw_trades": len(baseline_raw),
        "candidate_raw_trades": len(candidate_raw),
        "baseline_max3_trades": len(baseline_max3),
        "candidate_max3_trades": len(candidate_max3),
        "baseline_metrics": baseline_metrics,
        "candidate_metrics": candidate_metrics,
        "selected_max3_provenance": dict(sorted(provenance.items())),
        "duplicate_h1_candidates": sum(
            int(item["duplicate_h1_candidates"]) for item in reports
        ),
        "opposite_tie_fail_closed": sum(
            int(item["opposite_tie_fail_closed"]) for item in reports
        ),
        "delta_vs_arbitration": {
            "raw_trades": len(candidate_raw) - len(baseline_raw),
            "max3_trades": len(candidate_max3) - len(baseline_max3),
            "profit_factor": str(pf_candidate - pf_base),
            "total_r": str(total_candidate - total_base),
            "max_drawdown_r": str(dd_candidate - dd_base),
            "losing_streak": (
                int(candidate_metrics["max_losing_streak"])
                - int(baseline_metrics["max_losing_streak"])
            ),
        },
        "arbitration_controls": {
            "expected_raw": ARBITRATION_RAW,
            "expected_max3": ARBITRATION_MAX3,
            "raw_reproduced": len(baseline_raw) == ARBITRATION_RAW,
            "max3_reproduced": len(baseline_max3) == ARBITRATION_MAX3,
        },
        "one_trade_per_market_h1": True,
        "earliest_causal_entry_wins": True,
        "opposite_tie_fail_closed_policy": True,
        "threshold_relaxations_included": False,
        "target_changes_included": False,
        "outcome_used_for_admission": False,
        "recovery_phase_open": True,
        "target_phase_open": False,
        "automatic_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-max-recovery-v2.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("arbitration_root", type=Path)
    market.add_argument("stop_root", type=Path)
    market.add_argument("funnel_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument(
        "--session",
        required=True,
        choices=[item.value for item in CapitalizerSession],
    )

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report, baseline, candidate = build_market_report(
            args.arbitration_root,
            args.stop_root,
            args.funnel_root,
            args.m1_root,
            session=CapitalizerSession(args.session),
        )
        write_market(report, baseline, candidate, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
