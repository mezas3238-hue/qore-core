"""AUDJPY R41 five-year structural fragility correction.

Consumes the exact frozen R40 5Y ledger. No signal is removed or added.
A second, non-zero risk-only overlay is applied from pre-entry structural
states identified in consumed R40 drawdown forensics.

Fresh holdout remains sealed.
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

IDENTITY = "TURTLE_SOUP_AUDJPY_R41_5Y_STRUCTURAL_FRAGILITY_CORRECTION_V1"
SOURCE_IDENTITY = "TURTLE_SOUP_AUDJPY_R40_FROZEN_R39_5Y_VALIDATION_V1"
CANDIDATE_IDENTITY = "TURTLE_SOUP_AUDJPY_R39_STRUCTURAL_RISK_CANDIDATE_001"

SOURCE_RUN_ID = 35397390781
SOURCE_ARTIFACT_ID = 10570170141
SOURCE_ARTIFACT_DIGEST = (
    "sha256:fa03006b95fd0ae52bed951327dee4620b65de75a181d2fa6825914de6d1e2ad"
)
SOURCE_GIT_SHA = "a332b077598e070a42b2497b3766d55e731f7dca"
SOURCE_REPORT_SHA256 = (
    "fd79fc485317969dfa1db4e1bba156cafb8ddfa3ef24fbf4754d9914abcf17bb"
)
SOURCE_LEDGER_SHA256 = (
    "70d3118b7620f93c3c3b33b660c5815351f8c44a9349f4108a55d515815f39ec"
)

F1 = "D1_BODY_ALIGNMENT_OPPOSED"
F2 = "RAID_DEPTH_Q4_LE_0_50"
F3 = "SOURCE_RANGE_Q2_LE_1_0"
FRAGILITY_FLAGS = (F1, F2, F3)
FRAGILITY_POLICY = (
    Decimal("1"),
    Decimal("0.50"),
    Decimal("0.25"),
    Decimal("0.10"),
)

EVAL_5Y_OPEN = datetime(2021, 9, 17, tzinfo=UTC)
EVAL_2Y_OPEN = datetime(2024, 9, 17, tzinfo=UTC)
EVAL_CLOSE = datetime(2026, 9, 17, tzinfo=UTC)

MIN_TRADES_5Y = 800
MIN_PF_5Y = Decimal("1.50")
MAX_DD_5Y = Decimal("6.0")
REQUIRED_POSITIVE_ANNUAL_BLOCKS = 5

MIN_TRADES_2Y = 350
MIN_PF_2Y = Decimal("1.90")
MAX_DD_2Y = Decimal("6.0")


@dataclass(frozen=True, slots=True)
class CorrectedTrade:
    entry_at: str
    exit_at: str
    side: str
    source_scheme: str
    authority_tier: str
    validation_class: str
    target_rank: int
    target_route: str
    exit_reason: str
    raw_net_010_r: str
    base_risk_scale: str
    base_scaled_net_010_r: str
    first_layer_fragility_flags: tuple[str, ...]
    second_layer_fragility_flags: tuple[str, ...]
    second_layer_fragility_flag_count: int
    second_layer_overlay_scale: str
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
    report_path = _single(root, "r40-5y-validation-report.json")
    ledger_path = _single(root, "r40-5y-scaled-trades.jsonl")
    report_bytes = report_path.read_bytes()
    ledger_bytes = ledger_path.read_bytes()
    if hashlib.sha256(report_bytes).hexdigest() != SOURCE_REPORT_SHA256:
        raise ValueError("R40 report hash drift")
    if hashlib.sha256(ledger_bytes).hexdigest() != SOURCE_LEDGER_SHA256:
        raise ValueError("R40 ledger hash drift")
    report = json.loads(report_bytes)
    if report["identity"] != SOURCE_IDENTITY:
        raise ValueError("R40 identity drift")
    if report["candidate"]["identity"] != CANDIDATE_IDENTITY:
        raise ValueError("candidate identity drift")
    if int(report["result"]["trades"]) != 1039:
        raise ValueError("R40 trade-count drift")
    if str(report["result"]["profit_factor_scaled_net_010"]) != (
        "1.591776252307511394085813805"
    ):
        raise ValueError("R40 PF drift")
    if str(report["result"]["max_drawdown_within_block_r"]) != (
        "13.02659568901031182385302577"
    ):
        raise ValueError("R40 drawdown drift")
    if int(report["result"]["positive_annual_blocks"]) != 4:
        raise ValueError("R40 annual-block drift")
    git_sha = _single(root, "git-sha.txt").read_text().strip()
    if git_sha != SOURCE_GIT_SHA:
        raise ValueError("R40 git binding drift")
    rows = [
        json.loads(line)
        for line in ledger_bytes.decode("utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != 1039:
        raise ValueError("R40 ledger count drift")
    return report, rows


def _fragility_flags(row: dict[str, Any]) -> tuple[str, ...]:
    flags: list[str] = []
    regime = row["regime"]
    setup = row["setup_context"]
    if regime["d1_body_alignment"] == "opposed":
        flags.append(F1)
    if setup["raid_depth_range_bucket"] == "q4:<=0.50":
        flags.append(F2)
    if setup["source_range_state_bucket"] == "q2:<=1.0":
        flags.append(F3)
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
    grouped: dict[str, list[CorrectedTrade]] = defaultdict(list)
    for row in rows:
        grouped[str(getattr(row, field))].append(row)
    return {
        key: _block_stats(members)
        for key, members in sorted(grouped.items())
    }


def run(source_root: Path, output: Path) -> dict[str, Any]:
    source_report, source_rows = _load_source(source_root)
    corrected: list[CorrectedTrade] = []
    flag_counts: Counter[str] = Counter()
    flag_count_distribution: Counter[str] = Counter()
    overlay_counts: Counter[str] = Counter()

    for row in source_rows:
        flags = _fragility_flags(row)
        overlay = _overlay_scale(len(flags))
        base_scale = Decimal(str(row["risk_scale"]))
        base_value = Decimal(str(row["scaled_net_010_r"]))
        raw_value = Decimal(str(row["raw_net_010_r"]))
        if raw_value * base_scale != base_value:
            raise ValueError("R40 base risk arithmetic drift")
        final_scale = base_scale * overlay
        corrected_value = base_value * overlay
        for flag in flags:
            flag_counts[flag] += 1
        flag_count_distribution[str(len(flags))] += 1
        overlay_counts[str(overlay)] += 1
        corrected.append(
            CorrectedTrade(
                entry_at=str(row["entry_at"]),
                exit_at=str(row["exit_at"]),
                side=str(row["side"]),
                source_scheme=str(row["source_scheme"]),
                authority_tier=str(row["authority_tier"]),
                validation_class=str(row["validation_class"]),
                target_rank=int(row["target_rank"]),
                target_route=str(row["target_route"]),
                exit_reason=str(row["exit_reason"]),
                raw_net_010_r=str(raw_value),
                base_risk_scale=str(base_scale),
                base_scaled_net_010_r=str(base_value),
                first_layer_fragility_flags=tuple(row["fragility_flags"]),
                second_layer_fragility_flags=flags,
                second_layer_fragility_flag_count=len(flags),
                second_layer_overlay_scale=str(overlay),
                final_risk_scale=str(final_scale),
                corrected_scaled_net_010_r=str(corrected_value),
                setup_context=dict(row["setup_context"]),
                regime=dict(row["regime"]),
            )
        )

    overall_5y = _block_stats(corrected)
    annual = _annual_blocks(corrected)
    positive_annual = sum(bool(item["positive_total"]) for item in annual)
    two_year = [
        row
        for row in corrected
        if EVAL_2Y_OPEN <= datetime.fromisoformat(row.entry_at) < EVAL_CLOSE
    ]
    overall_2y = _block_stats(two_year)

    pf5_raw = overall_5y["profit_factor_scaled_net_010"]
    pf5 = None if pf5_raw is None else Decimal(str(pf5_raw))
    dd5 = Decimal(str(overall_5y["max_drawdown_r"]))
    total5 = Decimal(str(overall_5y["total_scaled_net_010_r"]))
    pass_5y = bool(
        len(corrected) >= MIN_TRADES_5Y
        and pf5 is not None
        and pf5 >= MIN_PF_5Y
        and dd5 <= MAX_DD_5Y
        and total5 > 0
        and positive_annual == REQUIRED_POSITIVE_ANNUAL_BLOCKS
    )

    pf2_raw = overall_2y["profit_factor_scaled_net_010"]
    pf2 = None if pf2_raw is None else Decimal(str(pf2_raw))
    dd2 = Decimal(str(overall_2y["max_drawdown_r"]))
    total2 = Decimal(str(overall_2y["total_scaled_net_010_r"]))
    pass_2y = bool(
        len(two_year) >= MIN_TRADES_2Y
        and pf2 is not None
        and pf2 >= MIN_PF_2Y
        and dd2 <= MAX_DD_2Y
        and total2 > 0
    )

    output.mkdir(parents=True, exist_ok=True)
    with (output / "r41-5y-corrected-trades.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in corrected:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")

    report: dict[str, Any] = {
        "schema": "qore.turtle_soup_audjpy.r41_5y_structural_fragility_correction.v1",
        "identity": IDENTITY,
        "source": {
            "identity": SOURCE_IDENTITY,
            "candidate_identity": CANDIDATE_IDENTITY,
            "run_id": SOURCE_RUN_ID,
            "artifact_id": SOURCE_ARTIFACT_ID,
            "artifact_digest": SOURCE_ARTIFACT_DIGEST,
            "git_sha": SOURCE_GIT_SHA,
            "report_sha256": SOURCE_REPORT_SHA256,
            "ledger_sha256": SOURCE_LEDGER_SHA256,
            "source_5y_result": source_report["result"],
        },
        "correction_contract": {
            "signals_added": False,
            "signals_removed": False,
            "trade_count_preserved": True,
            "post_entry_information_used_for_risk": False,
            "pre_entry_context_only": True,
            "risk_only_nonzero_scaling": True,
            "first_layer_risk_contract_changed": False,
            "second_layer_fragility_flags": list(FRAGILITY_FLAGS),
            "second_layer_policy_0_1_2_3plus": [
                str(value) for value in FRAGILITY_POLICY
            ],
            "forensic_rationale": {
                F1: "R40_CONSUMED_5Y_MULTIYEAR_FRAGILITY",
                F2: "R40_CONSUMED_5Y_MULTIYEAR_FRAGILITY",
                F3: "R40_CONSUMED_5Y_MULTIYEAR_FRAGILITY",
            },
        },
        "predeclared_acceptance": {
            "five_year": {
                "minimum_trades": MIN_TRADES_5Y,
                "minimum_pf": str(MIN_PF_5Y),
                "maximum_dd_r": str(MAX_DD_5Y),
                "total_must_be_positive": True,
                "required_positive_annual_blocks": REQUIRED_POSITIVE_ANNUAL_BLOCKS,
            },
            "two_year_revalidation": {
                "minimum_trades": MIN_TRADES_2Y,
                "minimum_pf": str(MIN_PF_2Y),
                "maximum_dd_r": str(MAX_DD_2Y),
                "total_must_be_positive": True,
            },
        },
        "result_5y": {
            **overall_5y,
            "positive_annual_blocks": positive_annual,
            "annual_blocks": annual,
            "acceptance_pass": pass_5y,
        },
        "result_2y": {
            "window": {
                "open": EVAL_2Y_OPEN.isoformat(),
                "close": EVAL_CLOSE.isoformat(),
            },
            **overall_2y,
            "acceptance_pass": pass_2y,
        },
        "risk_distribution": {
            "second_layer_flag_counts": dict(flag_counts),
            "second_layer_flag_count_distribution": dict(flag_count_distribution),
            "second_layer_overlay_counts": dict(overlay_counts),
            "by_side": _group_stats(corrected, "side"),
            "by_source_scheme": _group_stats(corrected, "source_scheme"),
            "by_authority_tier": _group_stats(corrected, "authority_tier"),
            "by_validation_class": _group_stats(corrected, "validation_class"),
            "by_second_layer_flag_count": _group_stats(
                corrected,
                "second_layer_fragility_flag_count",
            ),
            "by_final_risk_scale": _group_stats(corrected, "final_risk_scale"),
        },
        "decision": {
            "five_year_pass": pass_5y,
            "two_year_pass": pass_2y,
            "eligible_for_final_freeze": pass_5y and pass_2y,
        },
        "governance": {
            "consumed_5y_forensic_correction": True,
            "fresh_holdout_consumed": False,
            "candidate_rules_changed_only_by_preentry_risk_overlay": True,
            "trader_certified": False,
            "demo_eligible": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
            "merge_authorized": False,
        },
    }
    (output / "r41-5y-structural-fragility-correction-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    return report


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: module R40_ARTIFACT_ROOT OUTPUT_DIR")
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2])), sort_keys=True))


if __name__ == "__main__":
    main()
