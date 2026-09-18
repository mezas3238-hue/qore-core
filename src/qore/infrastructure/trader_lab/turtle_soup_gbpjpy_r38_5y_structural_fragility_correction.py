"""R38 GBPJPY five-year structural-fragility risk correction.

R37 proved the frozen signal survives five years: 897 trades, PF > 1.50 and
5/5 positive annual blocks, but capital drawdown was too high. R38 therefore
keeps every R37 signal and changes only risk size using three GBPJPY-specific
pre-entry fragility flags identified in the consumed R37 drawdown forensics.

No date rule, future information, stop change, DOL change or signal suppression
is introduced. Fresh holdout remains sealed.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

IDENTITY = "TURTLE_SOUP_GBPJPY_R38_5Y_STRUCTURAL_FRAGILITY_CORRECTION_V1"
CANDIDATE_IDENTITY = "TURTLE_SOUP_GBPJPY_R36_CONFIDENCE_CANDIDATE_001"
SOURCE_IDENTITY = "TURTLE_SOUP_GBPJPY_R37_FROZEN_R36_5Y_VALIDATION_V1"

SOURCE_RUN_ID = 35371203863
SOURCE_ARTIFACT_ID = 10558603038
SOURCE_ARTIFACT_DIGEST = (
    "sha256:0c005ed71d7476fb48aa901a347ed833772e4729f341b800abca1a9b29cbf7c9"
)
SOURCE_GIT_SHA = "eb62226e05f63cf94c1940634de676c55285e6dd"
SOURCE_REPORT_SHA256 = (
    "6b88e132a6dca5721084c434d2268b5dd171ba6b8d1a79659dde4d509f031da4"
)

EVAL_OPEN = datetime(2021, 9, 17, tzinfo=UTC)
EVAL_CLOSE = datetime(2026, 9, 17, tzinfo=UTC)
TWO_YEAR_OPEN = datetime(2024, 9, 17, tzinfo=UTC)

MIN_TRADES_5Y = 800
MIN_PF_5Y = Decimal("1.50")
MAX_DD_5Y = Decimal("6.0")
REQUIRED_POSITIVE_ANNUAL_BLOCKS = 5

MIN_TRADES_2Y = 350
MIN_PF_2Y = Decimal("1.90")
MAX_DD_2Y = Decimal("6.0")

FLAG_CORE_SOURCE_OPPOSITE_H1 = "CORE_SOURCE_OPPOSITE_BOUNDARY_H1"
FLAG_CORE_CLOSE_Q4 = "CORE_CLOSE_LOCATION_Q4"
FLAG_CORE_H4_BODY_WITH = "CORE_H4_BODY_WITH"

FRAGILITY_FLAGS = (
    FLAG_CORE_SOURCE_OPPOSITE_H1,
    FLAG_CORE_CLOSE_Q4,
    FLAG_CORE_H4_BODY_WITH,
)

# 0 flags / 1 flag / 2 flags / 3 flags.
# This is a risk-only overlay; a non-zero scale preserves every signal.
FRAGILITY_POLICY = (
    Decimal("1"),
    Decimal("0.25"),
    Decimal("0.10"),
    Decimal("0.05"),
)


@dataclass(frozen=True, slots=True)
class CorrectedTrade:
    entry_at: str
    exit_at: str
    side: str
    posture: str
    source_scheme: str
    authority_tier: str
    validation_class: str
    target_rank: int
    target_route: str
    exit_reason: str
    raw_net_010_r: str
    base_risk_scale: str
    base_scaled_net_010_r: str
    fragility_flags: tuple[str, ...]
    fragility_flag_count: int
    structural_overlay_scale: str
    final_risk_scale: str
    corrected_scaled_net_010_r: str
    setup_context: dict[str, Any]
    regime: dict[str, str]


def _single(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _load_source(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    report_path = _single(root, "r37-5y-validation-report.json")
    report_bytes = report_path.read_bytes()
    if hashlib.sha256(report_bytes).hexdigest() != SOURCE_REPORT_SHA256:
        raise ValueError("R37 report hash drift")
    report = json.loads(report_bytes)
    if report["identity"] != SOURCE_IDENTITY:
        raise ValueError("R37 identity drift")
    if report["candidate"]["identity"] != CANDIDATE_IDENTITY:
        raise ValueError("candidate identity drift")
    if report["window"]["fresh_holdout"] is not False:
        raise ValueError("R37 holdout classification drift")
    if report["governance"]["fresh_holdout_consumed"] is not False:
        raise ValueError("fresh holdout consumption drift")

    git_sha = _single(root, "git-sha.txt").read_text().strip()
    if git_sha != SOURCE_GIT_SHA:
        raise ValueError("R37 git binding drift")

    rows: list[dict[str, Any]] = []
    with _single(root, "r37-5y-scaled-trades.jsonl").open(
        encoding="utf-8"
    ) as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    if len(rows) != int(report["result"]["trades"]):
        raise ValueError("R37 trade-ledger count drift")
    return report, rows


def _fragility_flags(row: dict[str, Any]) -> tuple[str, ...]:
    if row["authority_tier"] != "CORE":
        return ()
    flags: list[str] = []
    if row["target_route"] == "SOURCE_OPPOSITE_BOUNDARY:H1":
        flags.append(FLAG_CORE_SOURCE_OPPOSITE_H1)
    if row["setup_context"]["close_location_bucket"] == "q4:>0.75":
        flags.append(FLAG_CORE_CLOSE_Q4)
    if row["regime"]["h4_body_alignment"] == "with":
        flags.append(FLAG_CORE_H4_BODY_WITH)
    return tuple(flags)


def _overlay_scale(flag_count: int) -> Decimal:
    return FRAGILITY_POLICY[min(flag_count, len(FRAGILITY_POLICY) - 1)]


def _raw_pf(values: Sequence[Decimal]) -> Decimal | None:
    gains = sum((value for value in values if value > 0), Decimal(0))
    losses = -sum((value for value in values if value < 0), Decimal(0))
    return None if losses == 0 else gains / losses


def _block_stats(rows: Sequence[CorrectedTrade]) -> dict[str, Any]:
    values = [Decimal(row.corrected_scaled_net_010_r) for row in rows]
    equity = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    losing = 0
    max_losing = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            losing += 1
            max_losing = max(max_losing, losing)
        else:
            losing = 0
    pf = _raw_pf(values)
    return {
        "trades": len(rows),
        "total_scaled_net_010_r": str(equity),
        "mean_scaled_net_010_r": (
            None if not rows else str(equity / Decimal(len(rows)))
        ),
        "profit_factor_scaled_net_010": None if pf is None else str(pf),
        "max_drawdown_r": str(max_dd),
        "max_losing_streak": max_losing,
        "positive_total": equity > 0,
    }


def _annual_blocks(rows: Sequence[CorrectedTrade]) -> list[dict[str, Any]]:
    boundaries = [
        datetime(2021, 9, 17, tzinfo=UTC),
        datetime(2022, 9, 17, tzinfo=UTC),
        datetime(2023, 9, 17, tzinfo=UTC),
        datetime(2024, 9, 17, tzinfo=UTC),
        datetime(2025, 9, 17, tzinfo=UTC),
        datetime(2026, 9, 17, tzinfo=UTC),
    ]
    result: list[dict[str, Any]] = []
    for start, end in zip(boundaries[:-1], boundaries[1:], strict=True):
        members = [
            row
            for row in rows
            if start <= datetime.fromisoformat(row.entry_at) < end
        ]
        result.append(
            {
                "open": start.isoformat(),
                "close": end.isoformat(),
                **_block_stats(members),
            }
        )
    return result


def _group_stats(
    rows: Sequence[CorrectedTrade],
    field: str,
) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[CorrectedTrade]] = defaultdict(list)
    for row in rows:
        groups[str(getattr(row, field))].append(row)
    return {key: _block_stats(value) for key, value in sorted(groups.items())}


def run(source_root: Path, output: Path) -> dict[str, Any]:
    source_report, source_rows = _load_source(source_root)
    corrected: list[CorrectedTrade] = []
    flag_counts: Counter[str] = Counter()
    overlay_counts: Counter[str] = Counter()

    for row in source_rows:
        raw = Decimal(str(row["raw_net_010_r"]))
        base_scale = Decimal(str(row["risk_scale"]))
        recorded_base = Decimal(str(row["scaled_net_010_r"]))
        expected_base = raw * base_scale
        if recorded_base != expected_base:
            raise ValueError("R37 base risk arithmetic drift")

        flags = _fragility_flags(row)
        overlay = _overlay_scale(len(flags))
        final_scale = base_scale * overlay
        corrected_value = raw * final_scale

        for flag in flags:
            flag_counts[flag] += 1
        overlay_counts[str(overlay)] += 1

        corrected.append(
            CorrectedTrade(
                entry_at=str(row["entry_at"]),
                exit_at=str(row["exit_at"]),
                side=str(row["side"]),
                posture=str(row["posture"]),
                source_scheme=str(row["source_scheme"]),
                authority_tier=str(row["authority_tier"]),
                validation_class=str(row["validation_class"]),
                target_rank=int(row["target_rank"]),
                target_route=str(row["target_route"]),
                exit_reason=str(row["exit_reason"]),
                raw_net_010_r=str(raw),
                base_risk_scale=str(base_scale),
                base_scaled_net_010_r=str(recorded_base),
                fragility_flags=flags,
                fragility_flag_count=len(flags),
                structural_overlay_scale=str(overlay),
                final_risk_scale=str(final_scale),
                corrected_scaled_net_010_r=str(corrected_value),
                setup_context=dict(row["setup_context"]),
                regime=dict(row["regime"]),
            )
        )

    overall = _block_stats(corrected)
    annual = _annual_blocks(corrected)
    positive_annual = sum(bool(item["positive_total"]) for item in annual)
    two_year = [
        row
        for row in corrected
        if TWO_YEAR_OPEN <= datetime.fromisoformat(row.entry_at) < EVAL_CLOSE
    ]
    two_year_stats = _block_stats(two_year)

    pf5_raw = overall["profit_factor_scaled_net_010"]
    pf5 = None if pf5_raw is None else Decimal(str(pf5_raw))
    dd5 = Decimal(str(overall["max_drawdown_r"]))
    total5 = Decimal(str(overall["total_scaled_net_010_r"]))
    pass_5y = bool(
        len(corrected) >= MIN_TRADES_5Y
        and pf5 is not None
        and pf5 >= MIN_PF_5Y
        and dd5 <= MAX_DD_5Y
        and total5 > 0
        and positive_annual == REQUIRED_POSITIVE_ANNUAL_BLOCKS
    )

    pf2_raw = two_year_stats["profit_factor_scaled_net_010"]
    pf2 = None if pf2_raw is None else Decimal(str(pf2_raw))
    dd2 = Decimal(str(two_year_stats["max_drawdown_r"]))
    total2 = Decimal(str(two_year_stats["total_scaled_net_010_r"]))
    pass_2y = bool(
        len(two_year) >= MIN_TRADES_2Y
        and pf2 is not None
        and pf2 >= MIN_PF_2Y
        and dd2 <= MAX_DD_2Y
        and total2 > 0
    )

    output.mkdir(parents=True, exist_ok=True)
    with (output / "r38-5y-corrected-trades.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in corrected:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")

    report: dict[str, Any] = {
        "schema": "qore.turtle_soup_gbpjpy.r38_5y_structural_fragility_correction.v1",
        "identity": IDENTITY,
        "source": {
            "identity": SOURCE_IDENTITY,
            "run_id": SOURCE_RUN_ID,
            "artifact_id": SOURCE_ARTIFACT_ID,
            "artifact_digest": SOURCE_ARTIFACT_DIGEST,
            "git_sha": SOURCE_GIT_SHA,
            "report_sha256": SOURCE_REPORT_SHA256,
            "baseline_acceptance_pass": bool(
                source_report["result"]["acceptance_pass"]
            ),
            "baseline_failure": {
                "trades": source_report["result"]["trades"],
                "profit_factor_scaled_net_010": source_report["result"][
                    "profit_factor_scaled_net_010"
                ],
                "max_drawdown_r": source_report["result"][
                    "max_drawdown_within_block_r"
                ],
                "positive_annual_blocks": source_report["result"][
                    "positive_annual_blocks"
                ],
            },
        },
        "correction_contract": {
            "candidate_identity": CANDIDATE_IDENTITY,
            "signal_count_preserved": len(corrected) == len(source_rows),
            "signals_suppressed": False,
            "entry_changed": False,
            "c2_changed": False,
            "cisd_changed": False,
            "dol_changed": False,
            "protected_swing_changed": False,
            "single_position_busy_changed": False,
            "structural_rearm_changed": False,
            "date_filter_added": False,
            "post_entry_information_used_for_risk": False,
            "gbpjpy_specific_fragility_flags": list(FRAGILITY_FLAGS),
            "fragility_policy_0_1_2_3plus": [
                str(value) for value in FRAGILITY_POLICY
            ],
            "risk_only_nonzero_scaling": True,
        },
        "forensic_rationale": {
            FLAG_CORE_SOURCE_OPPOSITE_H1: {
                "source_5y_trades": 39,
                "source_5y_total_r": "-4.597049870073778528642535370",
                "source_5y_pf": "0.7958258504572136511801816712",
                "source_5y_dd_r": "12.04460571599581026485111477",
            },
            FLAG_CORE_CLOSE_Q4: {
                "source_5y_trades": 184,
                "source_5y_total_r": "-2.698016721983855296605153129",
                "source_5y_pf": "0.9570402636912895447589917919",
                "source_5y_dd_r": "21.18584612514931092867199213",
            },
            FLAG_CORE_H4_BODY_WITH: {
                "source_5y_trades": 197,
                "source_5y_total_r": "19.35277635631407429729143895",
                "source_5y_pf": "1.262891882579507949860047325",
                "source_5y_dd_r": "16.97747407780033350215376304",
            },
        },
        "predeclared_acceptance": {
            "5y": {
                "minimum_trades": MIN_TRADES_5Y,
                "minimum_pf": str(MIN_PF_5Y),
                "maximum_dd_r": str(MAX_DD_5Y),
                "required_positive_annual_blocks": REQUIRED_POSITIVE_ANNUAL_BLOCKS,
            },
            "2y_recheck": {
                "minimum_trades": MIN_TRADES_2Y,
                "minimum_pf": str(MIN_PF_2Y),
                "maximum_dd_r": str(MAX_DD_2Y),
            },
        },
        "result_5y": {
            **overall,
            "positive_annual_blocks": positive_annual,
            "annual_blocks": annual,
            "acceptance_pass": pass_5y,
        },
        "result_2y_recheck": {
            "window_open": TWO_YEAR_OPEN.isoformat(),
            "window_close": EVAL_CLOSE.isoformat(),
            **two_year_stats,
            "acceptance_pass": pass_2y,
        },
        "risk_distribution": {
            "fragility_flag_counts": dict(flag_counts),
            "overlay_scale_counts": dict(overlay_counts),
        },
        "diagnostics": {
            "by_side": _group_stats(corrected, "side"),
            "by_source_scheme": _group_stats(corrected, "source_scheme"),
            "by_validation_class": _group_stats(corrected, "validation_class"),
            "by_fragility_flag_count": _group_stats(
                corrected,
                "fragility_flag_count",
            ),
            "by_final_risk_scale": _group_stats(corrected, "final_risk_scale"),
        },
        "decision": {
            "eligible_for_final_freeze": pass_5y and pass_2y,
            "fresh_holdout_status": "SEALED_UNTOUCHED",
        },
        "governance": {
            "consumed_5y_forensic_correction": True,
            "fresh_holdout_consumed": False,
            "trader_certified": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
            "merge_authorized": False,
        },
    }
    (output / "r38-5y-structural-fragility-correction-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    return report


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: module R37_ARTIFACT_ROOT OUTPUT_DIR")
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))


if __name__ == "__main__":
    main()
