"""CLI and report composition for VT-08 R3.16 CIBO capital protection."""
from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import cast

from qore.infrastructure.trader_lab.vt08_cibo_data_r3_16 import (
    CHALLENGE_END,
    CHALLENGE_RUN_ID,
    CHALLENGE_SHA,
    CHALLENGE_START,
    LONG_END,
    LONG_RUN_ID,
    LONG_SHA,
    LONG_START,
    PORTFOLIOS,
    PRIMARY_COST_BPS,
    STOP_POLICIES,
    build_records,
    load_period,
)
from qore.infrastructure.trader_lab.vt08_cibo_engine_r3_16 import (
    BLOCK_DAYS,
    CAPITAL_GUARDS,
    FINAL_PATHS,
    FINAL_SEED,
    HARD_DRAWDOWN,
    PHASE_DAYS,
    PRIMARY_PHASE1_TARGET,
    PRIMARY_PHASE2_TARGET,
    RISK_LEVELS,
    SEARCH_PATHS,
    SEARCH_SEED,
    SENSITIVITY_PHASE1_TARGET,
    SENSITIVITY_PHASE2_TARGET,
)
from qore.infrastructure.trader_lab.vt08_cibo_study_r3_16 import (
    challenge_study,
    long_run_study,
)

SCHEMA = "qore.vt08.r3.16.cibo-capital-protection.v1"


def _number(mapping: Mapping[str, object], key: str) -> float:
    value = mapping[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{key} must be numeric")
    return float(value)


def build_report(challenge_root: Path, long_root: Path) -> dict[str, object]:
    challenge_trades, challenge_bars = load_period(
        challenge_root,
        expected_sha=CHALLENGE_SHA,
    )
    long_trades, long_bars = load_period(long_root, expected_sha=LONG_SHA)
    challenge_records = {
        policy.name: build_records(
            challenge_trades,
            challenge_bars,
            policy,
            opened=CHALLENGE_START,
            closed=CHALLENGE_END,
        )
        for policy in STOP_POLICIES
    }
    long_records = {
        policy.name: build_records(
            long_trades,
            long_bars,
            policy,
            opened=LONG_START,
            closed=LONG_END,
        )
        for policy in STOP_POLICIES
    }
    return {
        "schema": SCHEMA,
        "authority": {
            "research_only": True,
            "cibo_may_generate_entries": False,
            "cibo_may_filter_entries": False,
            "cibo_may_change_direction": False,
            "cibo_may_increase_risk_above_risk_authority": False,
            "cibo_post_entry_protection_only": True,
            "hard_drawdown_fraction": HARD_DRAWDOWN,
            "live_authorized": False,
            "production_authorized": False,
        },
        "portfolio_freeze": {
            "A_CORE": ["AUDJPY short", "GBPUSD short"],
            "GBPJPY_RETURN_ENHANCER": ["GBPJPY long", "GBPJPY short"],
            "B_COMBINED_PORTFOLIO": [
                "AUDJPY short",
                "GBPUSD short",
                "GBPJPY long",
                "GBPJPY short",
            ],
        },
        "experiment": {
            "primary_cost_bps": PRIMARY_COST_BPS,
            "challenge_run_id": CHALLENGE_RUN_ID,
            "long_run_id": LONG_RUN_ID,
            "phase_days": PHASE_DAYS,
            "block_days": BLOCK_DAYS,
            "search_paths": SEARCH_PATHS,
            "final_paths": FINAL_PATHS,
            "search_seed": SEARCH_SEED,
            "final_seed": FINAL_SEED,
            "primary_targets": [PRIMARY_PHASE1_TARGET, PRIMARY_PHASE2_TARGET],
            "sensitivity_targets": [
                SENSITIVITY_PHASE1_TARGET,
                SENSITIVITY_PHASE2_TARGET,
            ],
            "risk_levels": [asdict(item) for item in RISK_LEVELS],
            "stop_policies": [asdict(item) for item in STOP_POLICIES],
            "capital_guards": [asdict(item) for item in CAPITAL_GUARDS],
        },
        "challenge": challenge_study(challenge_records),
        "long_run": long_run_study(long_records),
    }


def summary(report: Mapping[str, object]) -> str:
    challenge = cast(Mapping[str, object], report["challenge"])
    long_run = cast(Mapping[str, object], report["long_run"])
    challenge_selected = cast(Mapping[str, object], challenge["selected"])
    long_selected = cast(Mapping[str, object], long_run["selected"])
    lines = [
        "# VT-08 R3.16 CIBO Capital Protection",
        "",
        "CIBO does not generate, filter, cancel or redirect VT-08 entries.",
        "Risk remains sovereign. LIVE_AUTHORIZED=false.",
        "",
        "## 30 + 30 challenge study",
    ]
    for portfolio in PORTFOLIOS:
        item = cast(Mapping[str, object], challenge_selected[portfolio])
        primary = cast(Mapping[str, object], item["primary_10_5"])
        sensitivity = cast(Mapping[str, object], item["sensitivity_11_6"])
        policy = cast(Mapping[str, object], item["selected_policy"])
        lines.append(
            f"- {portfolio}: {policy['risk_level']} / {policy['stop_policy']} / "
            f"{policy['capital_guard']}; P(10% then 5%)="
            f"{100 * _number(primary, 'two_phase_pass_probability'):.2f}%; "
            f"P(11% then 6%)="
            f"{100 * _number(sensitivity, 'two_phase_pass_probability'):.2f}%; "
            f"DD p99={100 * _number(primary, 'drawdown_p99'):.2f}%"
        )
    lines.extend(["", "## 2024-2026 retained two-year study"])
    for portfolio in PORTFOLIOS:
        item = cast(Mapping[str, object], long_selected[portfolio])
        metrics = cast(Mapping[str, object], item["selected_metrics"])
        policy = cast(Mapping[str, object], item["selected_policy"])
        lines.append(
            f"- {portfolio}: {policy['risk_level']} / {policy['stop_policy']} / "
            f"{policy['capital_guard']}; return="
            f"{100 * _number(metrics, 'terminal_return'):.2f}%; "
            f"max DD={100 * _number(metrics, 'maximum_drawdown'):.2f}%; "
            f"CIBO delta return={100 * _number(item, 'cibo_delta_return'):+.2f}pp"
        )
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--challenge-root", type=Path, required=True)
    parser.add_argument("--long-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_report(args.challenge_root, args.long_root)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "cibo-capital-protection.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    (args.out / "summary.md").write_text(summary(report), encoding="utf-8")
    challenge = cast(Mapping[str, object], report["challenge"])
    long_run = cast(Mapping[str, object], report["long_run"])
    (args.out / "challenge-search.json").write_text(
        json.dumps(challenge["search_surface"], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (args.out / "long-run-search.json").write_text(
        json.dumps(long_run["search_surface"], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(summary(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
