"""VT08 Index R23 — concurrent portfolio drawdown closure.

R23 preserves the permanent three-market concurrent contract:
- NAS100, SP500 and US30 signal independently;
- one active position per symbol, up to three cross-market positions;
- no valid signal is suppressed because another market is already open;
- risk may resize valid signals but may never assign zero risk.

R23 does not change the 1574-signal opportunity architecture. It narrows the
R22 stable-formation quality hierarchy and searches tighter concurrent capital
budgets / rolling defenses to close the remaining conservative portfolio-DD
gap. Both -0.05R and -0.10R stress surfaces must remain <= 6R.
"""

from __future__ import annotations

import argparse
import itertools
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import vt08_index_concurrent_market_contract as contract
from qore.infrastructure.trader_lab import vt08_index_r15_concurrent_portfolio_validation as r15
from qore.infrastructure.trader_lab import vt08_index_r22_concurrent_stable_formation as r22

SCHEMA = "qore.trader_lab.vt08_index_r23_concurrent_dd_closure.v1"
IDENTITY = "VT08_INDEX_R23_CONCURRENT_DD_CLOSURE_001"

PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
PF_PRIMARY_MIN = Decimal("1.50")
PF_SECONDARY_MIN = Decimal("1.30")
PORTFOLIO_DD_MAX = Decimal("6")


def _quality_profiles() -> tuple[r22.QualityProfile, ...]:
    return tuple(
        r22.QualityProfile(
            base_weight=base,
            tier_a_weight=tier_a,
            tier_b_weight=tier_b,
            tier_c_weight=tier_c,
        )
        for base, tier_a, tier_b, tier_c in itertools.product(
            (Decimal("0.005"), Decimal("0.010")),
            (Decimal("1.25"), Decimal("1.50")),
            (Decimal("0.50"), Decimal("0.75"), Decimal("1.00")),
            (Decimal("0.05"), Decimal("0.10"), Decimal("0.20")),
        )
    )


def _risk_profiles() -> tuple[r22.RiskProfile, ...]:
    rows: list[r22.RiskProfile] = []
    for (
        rolling,
        warn_dd,
        warn_mult,
        hard_dd,
        hard_mult,
        loss_mult,
        cap,
    ) in itertools.product(
        (40, 60),
        (Decimal("0.50"), Decimal("0.75"), Decimal("1.00"), Decimal("1.25")),
        (Decimal("0.05"), Decimal("0.10"), Decimal("0.15")),
        (Decimal("1.00"), Decimal("1.25"), Decimal("1.50"), Decimal("1.75")),
        (Decimal("0.025"), Decimal("0.05"), Decimal("0.10")),
        (Decimal("0.05"), Decimal("0.10")),
        (
            Decimal("0.40"),
            Decimal("0.50"),
            Decimal("0.60"),
            Decimal("0.75"),
            Decimal("0.90"),
        ),
    ):
        if hard_dd <= warn_dd:
            continue
        rows.append(
            r22.RiskProfile(
                rolling_trades=rolling,
                warn_dd_r=warn_dd,
                warn_multiplier=warn_mult,
                hard_dd_r=hard_dd,
                hard_multiplier=hard_mult,
                loss_multiplier=loss_mult,
                portfolio_risk_budget_r=cap,
            )
        )
    return tuple(rows)


def _realized_rank(row: dict[str, Any]) -> tuple[int, Decimal, Decimal, Decimal]:
    p = row["primary"]
    s = row["secondary"]
    primary_pf = Decimal(str(p["profit_factor"] or "0"))
    secondary_pf = Decimal(str(s["profit_factor"] or "0"))
    primary_dd = Decimal(str(p["max_drawdown_r"]))
    secondary_dd = Decimal(str(s["max_drawdown_r"]))
    pre_mtm_pass = (
        primary_pf >= PF_PRIMARY_MIN
        and secondary_pf >= PF_SECONDARY_MIN
        and primary_dd <= PORTFOLIO_DD_MAX
        and secondary_dd <= PORTFOLIO_DD_MAX
    )
    return (
        int(pre_mtm_pass),
        primary_pf,
        -max(primary_dd, secondary_dd),
        Decimal(str(p["total_r"])),
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
    (
        stream,
        bars_by_symbol,
        _indexed,
        opened_by_symbol,
        provenance,
    ) = r15._build_five_year_stream(roots=roots)

    if not contract.validates_trade_count(years=5, sample=len(stream)):
        raise ValueError(
            f"permanent concurrent density drift: {len(stream)} trades"
        )

    quality_rows = [
        r22._static_quality_row(stream, profile=profile)
        for profile in _quality_profiles()
    ]
    quality_rows.sort(key=r22._quality_rank, reverse=True)

    selected_quality_ids = {
        row["profile"]["profile_id"] for row in quality_rows[:10]
    }
    selected_quality = tuple(
        profile
        for profile in _quality_profiles()
        if profile.profile_id in selected_quality_ids
    )

    search: list[
        tuple[dict[str, Any], tuple[r15.AssignedTrade, ...]]
    ] = []
    for quality, risk in itertools.product(
        selected_quality,
        _risk_profiles(),
    ):
        search.append(
            r22._realized_row(
                stream,
                quality=quality,
                risk=risk,
            )
        )
    search.sort(key=lambda item: _realized_rank(item[0]), reverse=True)

    finalists: list[dict[str, Any]] = []
    # Compute the expensive concurrent MTM surface only on the strongest
    # realized candidates.
    for row, assigned in search[:64]:
        primary_mtm = r15._portfolio_mark_to_market(
            assigned,
            bars_by_symbol=bars_by_symbol,
            opened_by_symbol=opened_by_symbol,
            stress=PRIMARY_STRESS,
            adverse=True,
        )
        secondary_mtm = r15._portfolio_mark_to_market(
            assigned,
            bars_by_symbol=bars_by_symbol,
            opened_by_symbol=opened_by_symbol,
            stress=SECONDARY_STRESS,
            adverse=True,
        )
        p = row["primary"]
        s = row["secondary"]
        diagnostics = row["diagnostics"]
        goal_pass = (
            len(assigned) == len(stream)
            and int(diagnostics["suppressed_trade_count"]) == 0
            and int(diagnostics["max_concurrent_open_positions"]) >= 2
            and Decimal(str(p["profit_factor"] or "0")) >= PF_PRIMARY_MIN
            and Decimal(str(s["profit_factor"] or "0")) >= PF_SECONDARY_MIN
            and Decimal(primary_mtm["max_drawdown_r"]) <= PORTFOLIO_DD_MAX
            and Decimal(secondary_mtm["max_drawdown_r"]) <= PORTFOLIO_DD_MAX
        )
        final = dict(row)
        final["primary_conservative_mark_to_market"] = primary_mtm
        final["secondary_conservative_mark_to_market"] = secondary_mtm
        final["goal_pass"] = goal_pass
        finalists.append(final)

    finalists.sort(
        key=lambda row: (
            int(bool(row["goal_pass"])),
            Decimal(str(row["primary"]["profit_factor"] or "0")),
            -max(
                Decimal(
                    row["primary_conservative_mark_to_market"][
                        "max_drawdown_r"
                    ]
                ),
                Decimal(
                    row["secondary_conservative_mark_to_market"][
                        "max_drawdown_r"
                    ]
                ),
            ),
            Decimal(str(row["primary"]["total_r"])),
        ),
        reverse=True,
    )
    goals = [row for row in finalists if bool(row["goal_pass"])]

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "contract": {
            "contract_id": contract.CONTRACT_ID,
            "markets": list(contract.MARKETS),
            "global_single_position_rule": False,
            "cross_market_concurrency_required": True,
            "signal_suppression_allowed": False,
            "zero_risk_allowed": False,
            "five_year_density": list(contract.FIVE_YEAR_TRADE_RANGE),
            "portfolio_dd_max_r": str(PORTFOLIO_DD_MAX),
            "primary_pf_minimum": str(PF_PRIMARY_MIN),
            "secondary_pf_minimum": str(PF_SECONDARY_MIN),
            "both_stress_surfaces_dd_must_pass": True,
        },
        "sample": len(stream),
        "quality_profile_count": len(quality_rows),
        "selected_quality_profile_count": len(selected_quality),
        "risk_profile_count": len(_risk_profiles()),
        "realized_combination_count": len(search),
        "mtm_finalist_count": len(finalists),
        "goal_candidate_count": len(goals),
        "best": finalists[0] if finalists else None,
        "top_10": finalists[:10],
        "goal_candidates": goals[:10],
        "provenance": provenance,
        "governance": {
            "development_only": True,
            "all_trades_preserved": True,
            "cross_market_concurrency_preserved": True,
            "same_timestamp_batch_allocation": True,
            "future_outcome_used_for_new_signal_risk": False,
            "signal_suppression_allowed": False,
            "zero_risk_allowed": False,
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
                "sample": report["sample"],
                "goal_candidate_count": report["goal_candidate_count"],
                "best": report["best"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
