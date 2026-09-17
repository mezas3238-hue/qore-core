"""Consumed-evidence counterfactuals for Turtle Soup structural-break families.

Research only. This module starts from the frozen R7 structural abstention state
and evaluates two pre-registered R6 STRUCTURAL_BREAK families individually and
jointly. It does not promote either family into an operating rule and does not
consume a fresh holdout.
"""
from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_causal_regime_forensics as causal
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r5_regime_journey_validity_forensics as r5
from qore.infrastructure.trader_lab import turtle_soup_xauusd_r7_structural_abstention_lab as r7

IDENTITY = "TURTLE_SOUP_XAUUSD_R8_STRUCTURAL_BREAK_COUNTERFACTUAL_V1"
EVIDENCE_STATUS = "CONSUMED_CIBO_10Y_STRUCTURAL_BREAK_COUNTERFACTUAL_NOT_FRESH_HOLDOUT"

BREAK_A = {
    "raid_depth_range_bucket": "q4:<=0.50",
    "cisd_progress_bucket": "q3:<=0.75",
    "reclaim_latency_bucket": "<=5m",
    "protected_risk_range_bucket": "q3:<=1.0",
}

BREAK_B = {
    "raid_depth_range_bucket": "q3:<=0.25",
    "cisd_progress_bucket": "q2:<=0.50",
    "reclaim_latency_bucket": "<=5m",
    "protected_risk_range_bucket": "q3:<=1.0",
    "h4_range_3v20": "normal_0.75_1.25",
}

BREAK_FAMILIES: dict[str, Mapping[str, str]] = {
    "BREAK_A_DEEP_RAID_MID_LATE_CISD": BREAK_A,
    "BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4": BREAK_B,
}


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _matches(row: Mapping[str, Any], signature: Mapping[str, str]) -> bool:
    return all(str(row.get(key)) == value for key, value in signature.items())


def _slice(rows: Sequence[dict[str, Any]], years: set[int]) -> list[dict[str, Any]]:
    return [row for row in rows if int(row["year"]) in years]


def _periods() -> dict[str, set[int]]:
    return {
        "full_2016_2026": set(range(2016, 2027)),
        "early_2016_2020": set(range(2016, 2021)),
        "transition_2021_2023": {2021, 2022, 2023},
        "recent_2024_2026": {2024, 2025, 2026},
        **{str(year): {year} for year in range(2016, 2027)},
    }


def _delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    bp = before["primary"]
    ap = after["primary"]
    bs = before["stress_0p10R"]
    ass = after["stress_0p10R"]
    return {
        "primary_total_r_delta": str(_d(ap["total_r"]) - _d(bp["total_r"])),
        "primary_mean_r_delta": str(_d(ap["mean_r"]) - _d(bp["mean_r"])),
        "primary_pf_delta": None if ap["profit_factor"] is None or bp["profit_factor"] is None else str(_d(ap["profit_factor"]) - _d(bp["profit_factor"])),
        "primary_max_dd_delta": str(_d(ap["max_drawdown_r"]) - _d(bp["max_drawdown_r"])),
        "stress_total_r_delta": str(_d(ass["total_r"]) - _d(bs["total_r"])),
        "stress_pf_delta": None if ass["profit_factor"] is None or bs["profit_factor"] is None else str(_d(ass["profit_factor"]) - _d(bs["profit_factor"])),
        "trade_delta": int(ap["trades"]) - int(bp["trades"]),
    }


def _counterfactual(
    base_rows: Sequence[dict[str, Any]],
    removed_rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    removed_ids = {id(row) for row in removed_rows}
    kept = [row for row in base_rows if id(row) not in removed_ids]
    out: dict[str, Any] = {}
    for period_name, years in _periods().items():
        before_rows = _slice(base_rows, years)
        after_rows = _slice(kept, years)
        cut_rows = _slice(removed_rows, years)
        before = r7._pack(before_rows)
        after = r7._pack(after_rows)
        out[period_name] = {
            "before": before,
            "after": after,
            "removed": r7._pack(cut_rows),
            "delta": _delta(before, after),
        }
    return {
        "removed_trades": len(removed_rows),
        "retained_trades": len(kept),
        "comparison": out,
    }


def run(source_root: Path, target_root: Path, output: Path) -> dict[str, Any]:
    evidence, selected, reproduction = causal._reproduce_selected(source_root, target_root)
    opens = tuple(bar.opened_at for bar in evidence.bars)
    base_rows = [causal._record(setup, trade, evidence.bars, opens) for setup, trade in selected]
    if len(base_rows) != 5885:
        raise ValueError(f"R3 reproduction drift: {len(base_rows)}")
    total = sum((_d(row["primary_net_r"]) for row in base_rows), Decimal(0))
    if abs(total - Decimal("707.7490491424")) > Decimal("0.0001"):
        raise ValueError(f"R3 R-total reproduction drift: {total}")

    d1 = r5._aggregate(evidence.bars, "D1")
    h4 = r5._aggregate(evidence.bars, "H4")
    rows: list[dict[str, Any]] = []
    for raw in base_rows:
        row = dict(raw)
        row.update(r5._regime_features(row, d1, h4))
        rows.append(row)

    r7_removed = [row for row in rows if r7._is_abstain(row)]
    r7_kept = [row for row in rows if not r7._is_abstain(row)]
    if len(r7_removed) != 273:
        raise ValueError(f"R7 frozen invalid drift: expected 273, got {len(r7_removed)}")

    family_rows: dict[str, list[dict[str, Any]]] = {
        name: [row for row in r7_kept if _matches(row, signature)]
        for name, signature in BREAK_FAMILIES.items()
    }

    overlap = set(map(id, family_rows["BREAK_A_DEEP_RAID_MID_LATE_CISD"])) & set(
        map(id, family_rows["BREAK_B_MODERATE_RAID_MID_CISD_NORMAL_H4"])
    )
    if overlap:
        raise ValueError(f"unexpected R8 family overlap: {len(overlap)}")

    experiments: dict[str, Any] = {}
    for name, removed in family_rows.items():
        experiments[f"R7_PLUS_{name}"] = _counterfactual(r7_kept, removed)

    combined_removed = [row for name in BREAK_FAMILIES for row in family_rows[name]]
    experiments["R7_PLUS_BREAK_A_AND_BREAK_B"] = _counterfactual(r7_kept, combined_removed)

    family_diagnostics: dict[str, Any] = {}
    for name, removed in family_rows.items():
        family_diagnostics[name] = {
            "signature": dict(BREAK_FAMILIES[name]),
            "trades": len(removed),
            "full": r7._pack(removed),
            "early_2016_2020": r7._pack(_slice(removed, set(range(2016, 2021)))),
            "transition_2021_2023": r7._pack(_slice(removed, {2021, 2022, 2023})),
            "recent_2024_2026": r7._pack(_slice(removed, {2024, 2025, 2026})),
            "recent_by_year": {
                str(year): r7._pack(_slice(removed, {year})) for year in (2024, 2025, 2026)
            },
        }

    payload = {
        "schema": "qore.turtle_soup_xauusd_r8.structural_break_counterfactual.v1",
        "identity": IDENTITY,
        "evidence_status": EVIDENCE_STATUS,
        "reproduction": reproduction,
        "r3_baseline": r7._pack(rows),
        "r7_baseline": r7._pack(r7_kept),
        "r7_removed_structural_invalid": r7._pack(r7_removed),
        "pre_registered_break_families": {name: dict(signature) for name, signature in BREAK_FAMILIES.items()},
        "family_diagnostics": family_diagnostics,
        "experiments": experiments,
        "research_question": "WHICH_PRE_REGISTERED_STRUCTURAL_BREAK_FAMILY_EXPLAINS_RESIDUAL_2024_2026_LOSS_AFTER_R7_WITHOUT_USING_YEAR_AS_AN_OPERATING_RULE",
        "governance": {
            "diagnostic_counterfactual_only": True,
            "families_pre_registered_from_r6": True,
            "families_tested_individually_before_joint": True,
            "year_or_date_allowed_as_rule": False,
            "post_entry_leakage_allowed": False,
            "fresh_holdout_consumed": False,
            "rules_promoted": False,
            "automatic_candidate_promotion": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "structural-break-counterfactual.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    (output / "r7-retained-enriched-trades.json").write_text(json.dumps(r7_kept, indent=2, sort_keys=True) + "\n")
    return payload


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: module SOURCE_ROOT TARGET_ROOT OUTPUT_DIR")
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])), sort_keys=True))


if __name__ == "__main__":
    main()
