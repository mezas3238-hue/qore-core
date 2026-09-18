"""VT08 Index R14 — bounded local refinement of R13 rolling governor.

R14 does not change entries, target, POI architecture, or trade count. It only
refines the already-successful causal rolling governor around the R13 best
region. The search is intentionally local and rejects pseudo-skips by requiring
a minimum non-zero effective risk weight of 0.005.

The 5Y window remains consumed development evidence.
"""

from __future__ import annotations

import argparse
import itertools
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_density_round4 as r4
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_management_round5 as r5
from qore.infrastructure.trader_lab import vt08_index_r6_5y_failure_forensics as fx
from qore.infrastructure.trader_lab import vt08_index_r6_five_year_validation as v5y
from qore.infrastructure.trader_lab import vt08_index_r8_priority_poi_rearm_reset as r8
from qore.infrastructure.trader_lab import vt08_index_r10_contextual_risk as r10
from qore.infrastructure.trader_lab import vt08_index_r13_rolling_drawdown_governor as r13
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_r14_rolling_refinement.v1"
IDENTITY = "VT08_INDEX_R14_ROLLING_REFINEMENT_001"
MIN_TRADES = 1500
MAX_TRADES = 1600
MIN_EFFECTIVE_WEIGHT = Decimal("0.005")
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
PRIMARY_PF_GOAL = Decimal("1.50")
PRIMARY_DD_GOAL = Decimal("6")
SECONDARY_PF_GOAL = Decimal("1.30")
SECONDARY_DD_GOAL = Decimal("8")


@dataclass(frozen=True, slots=True)
class RefinedScheme:
    aligned_weight: Decimal
    warn_dd_r: Decimal
    warn_multiplier: Decimal
    hard_dd_r: Decimal
    hard_multiplier: Decimal
    loss_multiplier: Decimal

    @property
    def scheme_id(self) -> str:
        return (
            "R14-"
            f"A{self.aligned_weight}-"
            f"D{self.warn_dd_r}x{self.warn_multiplier}-"
            f"H{self.hard_dd_r}x{self.hard_multiplier}-"
            f"L2x{self.loss_multiplier}"
        )

    def as_r13(self) -> r13.RollingScheme:
        return r13.RollingScheme(
            aligned_weight=self.aligned_weight,
            c2_cap=Decimal("0.50"),
            short_cap=Decimal("0.50"),
            rolling_trades=60,
            warn_dd_r=self.warn_dd_r,
            warn_multiplier=self.warn_multiplier,
            hard_dd_r=self.hard_dd_r,
            hard_multiplier=self.hard_multiplier,
            loss_trigger=2,
            loss_multiplier=self.loss_multiplier,
        )

    def payload(self) -> dict[str, str]:
        return {
            "scheme_id": self.scheme_id,
            "aligned_weight": str(self.aligned_weight),
            "rolling_trades": "60",
            "c2_cap": "0.50",
            "short_cap": "0.50",
            "warn_dd_r": str(self.warn_dd_r),
            "warn_multiplier": str(self.warn_multiplier),
            "hard_dd_r": str(self.hard_dd_r),
            "hard_multiplier": str(self.hard_multiplier),
            "loss_trigger": "2",
            "loss_multiplier": str(self.loss_multiplier),
        }


def _schemes() -> tuple[RefinedScheme, ...]:
    rows: list[RefinedScheme] = []
    for (
        aligned,
        warn_dd,
        warn_mult,
        hard_dd,
        hard_mult,
        loss_mult,
    ) in itertools.product(
        (Decimal("0.20"), Decimal("0.25")),
        (Decimal("1.50"), Decimal("1.75"), Decimal("2.00")),
        (Decimal("0.15"), Decimal("0.20"), Decimal("0.25")),
        (Decimal("2.50"), Decimal("2.75"), Decimal("3.00")),
        (Decimal("0.05"), Decimal("0.10")),
        (Decimal("0.15"), Decimal("0.20"), Decimal("0.25")),
    ):
        if hard_dd <= warn_dd:
            continue
        rows.append(
            RefinedScheme(
                aligned_weight=aligned,
                warn_dd_r=warn_dd,
                warn_multiplier=warn_mult,
                hard_dd_r=hard_dd,
                hard_multiplier=hard_mult,
                loss_multiplier=loss_mult,
            )
        )
    return tuple(rows)


def _candidate(
    stream: Sequence[tuple[Any, r5.ManagedTrade]],
    contexts: Sequence[r10.Context],
    *,
    scheme: RefinedScheme,
) -> dict[str, Any]:
    outcomes = tuple(outcome for _opportunity, outcome in stream)
    r13_scheme = scheme.as_r13()
    primary_values, primary_diag = r13._weighted_values(
        outcomes,
        contexts,
        scheme=r13_scheme,
        stress=PRIMARY_STRESS,
    )
    secondary_values, secondary_diag = r13._weighted_values(
        outcomes,
        contexts,
        scheme=r13_scheme,
        stress=SECONDARY_STRESS,
    )
    primary = fx._metrics(primary_values)
    secondary = fx._metrics(secondary_values)
    years = r13._year_metrics(stream, primary_values)
    positive_years = sum(
        Decimal(str(row["total_r"])) > 0 for row in years.values()
    )
    min_weight = Decimal(str(primary_diag["minimum_weight"]))
    admissible = min_weight >= MIN_EFFECTIVE_WEIGHT
    sample = len(stream)
    return {
        "scheme": scheme.payload(),
        "sample": sample,
        "primary": primary,
        "secondary": secondary,
        "primary_diagnostics": primary_diag,
        "secondary_diagnostics": secondary_diag,
        "positive_years": positive_years,
        "primary_by_year": years,
        "minimum_weight_guard_pass": admissible,
        "goal_pass": (
            admissible
            and MIN_TRADES <= sample <= MAX_TRADES
            and Decimal(str(primary["profit_factor"] or "0")) >= PRIMARY_PF_GOAL
            and Decimal(str(primary["max_drawdown_r"])) <= PRIMARY_DD_GOAL
            and Decimal(str(secondary["profit_factor"] or "0")) >= SECONDARY_PF_GOAL
            and Decimal(str(secondary["max_drawdown_r"])) <= SECONDARY_DD_GOAL
            and positive_years >= 4
        ),
    }


def _rank(row: dict[str, Any]) -> tuple[int, int, Decimal, Decimal, Decimal]:
    primary = row["primary"]
    return (
        int(bool(row["goal_pass"])),
        int(bool(row["minimum_weight_guard_pass"])),
        Decimal(str(primary["profit_factor"] or "0")),
        -Decimal(str(primary["max_drawdown_r"])),
        Decimal(str(primary["total_r"])),
    )


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]] = {}
    indexed_by_symbol: dict[str, dict[datetime, Vt08IndexC2R1Bar]] = {}
    opportunities_by_symbol: dict[
        str,
        tuple[r4.ExpandedOpportunity, ...],
    ] = {}
    provenance: dict[str, Any] = {}

    for symbol in ("NAS100", "SP500", "US30"):
        bars, source = v5y._load_cibo_m15_5y(roots[symbol], symbol=symbol)
        bars_by_symbol[symbol] = bars
        indexed_by_symbol[symbol] = {
            bar.opened_at.astimezone(UTC): bar for bar in bars
        }
        opportunities_by_symbol[symbol] = r8._opportunities(
            symbol=symbol,
            bars=bars,
        )
        provenance[symbol] = source

    stream = r10._base_stream(
        opportunities_by_symbol=opportunities_by_symbol,
        bars_by_symbol=bars_by_symbol,
    )
    contexts = tuple(
        r10._context(
            opportunity,
            indexed=indexed_by_symbol[opportunity.signal.symbol],
        )
        for opportunity, _outcome in stream
    )

    rows = [
        _candidate(stream, contexts, scheme=scheme)
        for scheme in _schemes()
    ]
    rows.sort(key=_rank, reverse=True)
    goals = [row for row in rows if bool(row["goal_pass"])]

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "window": {
            "start_date": v5y.START_DATE.isoformat(),
            "end_date_exclusive": v5y.END_DATE_EXCLUSIVE.isoformat(),
            "status": "CONSUMED_DEVELOPMENT",
            "fresh_certification_holdout": False,
        },
        "execution_architecture": r8.IDENTITY,
        "parent_governor": r13.IDENTITY,
        "sample": len(stream),
        "scheme_count": len(rows),
        "goal_candidate_count": len(goals),
        "minimum_effective_weight": str(MIN_EFFECTIVE_WEIGHT),
        "best": rows[0],
        "top_20": rows[:20],
        "goal_candidates": goals[:20],
        "provenance": provenance,
        "governance": {
            "development_only": True,
            "local_refinement_only": True,
            "all_trades_preserved": True,
            "zero_risk_allowed": False,
            "minimum_effective_weight_guard": str(MIN_EFFECTIVE_WEIGHT),
            "rolling_drawdown_state_only": True,
            "five_year_window_consumed": True,
            "fresh_holdout_claim": False,
            "candidate_promoted": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "scheme_count": report["scheme_count"],
                "goal_candidate_count": report["goal_candidate_count"],
                "best": report["best"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
