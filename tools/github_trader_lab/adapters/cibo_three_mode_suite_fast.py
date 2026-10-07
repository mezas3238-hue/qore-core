#!/usr/bin/env python3
"""Hot CIBO three-mode suite using prepared lifecycle sidecars."""

from __future__ import annotations

import argparse
import inspect
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any


ZERO = Decimal(0)
INITIAL = Decimal("60")
SYMBOLS = ("AUDJPY", "EURUSD", "GBPJPY", "GBPUSD", "NAS100", "XAUUSD")


def d(value: object) -> Decimal:
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("non-finite decimal")
    return result


def find_one(root: Path, name: str) -> Path:
    matches = sorted(root.rglob(name))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"{root}: expected exactly one {name}, got {len(matches)}"
        )
    return matches[0]


def series_metrics(values: list[Decimal]) -> dict[str, str | int | None]:
    gains = sum((value for value in values if value > 0), ZERO)
    losses = -sum((value for value in values if value < 0), ZERO)
    mean = ZERO if not values else sum(values, ZERO) / Decimal(len(values))
    equity = ZERO
    peak = ZERO
    max_dd = ZERO
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return {
        "profit_factor": None if losses == 0 else format(gains / losses, "f"),
        "mean_r": format(mean, "f"),
        "max_drawdown_r": format(max_dd, "f"),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
    }


def temporal_blocks(
    values: list[Decimal],
    blocks: int = 5,
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    n = len(values)
    for index in range(blocks):
        lo = n * index // blocks
        hi = n * (index + 1) // blocks
        chunk = values[lo:hi]
        metrics = series_metrics(chunk)
        result[f"B{index + 1}"] = {
            "trade_count": len(chunk),
            "profit_factor": metrics["profit_factor"],
            "mean_r": metrics["mean_r"],
            "max_drawdown_r": metrics["max_drawdown_r"],
        }
    return result


def normalize_case(name: str, result: dict[str, Any]) -> dict[str, Any]:
    receipts = result.get("trade_receipts")
    if not isinstance(receipts, list) or not receipts:
        raise ValueError(f"{name}: trade receipts missing")

    net_r_values: list[Decimal] = []
    for row in receipts:
        if not isinstance(row, dict):
            raise ValueError(f"{name}: malformed trade receipt")
        if "realized_net_r" not in row or "realized_net_pnl_usd" not in row:
            raise ValueError(
                f"{name}: realized lifecycle settlement missing from trade receipt"
            )
        realized_net_r = d(row["realized_net_r"])
        realized_net_pnl = d(row["realized_net_pnl_usd"])
        stop_risk = d(row["stop_risk_usd"])
        if stop_risk > 0:
            reconstructed = realized_net_r * stop_risk
            tolerance = max(Decimal("0.00000001"), abs(realized_net_pnl) * Decimal("0.00000001"))
            if abs(reconstructed - realized_net_pnl) > tolerance:
                raise ValueError(
                    f"{name}: realized net R/PnL receipt consistency failure"
                )
        net_r_values.append(realized_net_r)

    if int(result["decision_count"]) != int(result["trade_count"]):
        raise ValueError(f"{name}: Trader base entry conservation failed")

    return {
        "trade_count": int(result["trade_count"]),
        "metrics": series_metrics(net_r_values),
        "net_r_values": [format(value, "f") for value in net_r_values],
        "temporal_blocks": temporal_blocks(net_r_values),
        "relative_density_vs_control": "1",
        "winner_preservation": {"count": "1", "r": "1"},
        "capital_path": {
            "initial_capital_usd": format(INITIAL, "f"),
            "ending_capital_usd": str(result["ending_total_capital_usd"]),
            "net_pnl_usd": format(
                d(result["ending_total_capital_usd"]) - INITIAL,
                "f",
            ),
            "peak_capital_usd": str(result["peak_total_capital_usd"]),
            "maximum_drawdown_usd": str(result["max_drawdown_usd"]),
            "maximum_drawdown_fraction": str(result["max_drawdown_fraction"]),
            "average_selected_multiplier": str(
                result["average_selected_multiplier"]
            ),
            "maximum_selected_multiplier": int(
                result["maximum_selected_multiplier"]
            ),
            "attack_trade_count": int(result["attack_trade_count"]),
            "attack_density_fraction": str(result["attack_density_fraction"]),
        },
        "three_mode_report": {
            "research_lane": result["research_lane"],
            "mode_epoch_counts": result["mode_epoch_counts"],
            "trade_mode_counts": result["trade_mode_counts"],
            "economic_group_report": result["economic_group_report"],
            "position_lifecycle_report": result["position_lifecycle_report"],
            "native_telemetry_report": result.get(
                "native_telemetry_report",
                {},
            ),
            "function_sensors": result["function_sensors"],
            "engineering_sensor_report": {
                "execution_funnel": result["engineering_sensor_report"][
                    "execution_funnel"
                ],
                "upstream_economic_intake": result[
                    "engineering_sensor_report"
                ]["upstream_economic_intake"],
                "bottleneck_ranking": result["engineering_sensor_report"][
                    "bottleneck_ranking"
                ],
            },
        },
        "governance": {
            "trader_base_entries_preserved": True,
            "telemetry_is_authority": False,
            "fresh_holdout_opened": False,
            "certification_claimed": False,
        },
    }


def apply_preservation(
    variants: dict[str, dict[str, Any]],
    control: str,
) -> None:
    base = variants[control]
    base_values = [d(value) for value in base["net_r_values"]]
    base_winners = [value for value in base_values if value > 0]
    base_win_count = len(base_winners)
    base_win_r = sum(base_winners, ZERO)
    base_count = int(base["trade_count"])
    for row in variants.values():
        values = [d(value) for value in row["net_r_values"]]
        winners = [value for value in values if value > 0]
        winner_r = sum(winners, ZERO)
        row["relative_density_vs_control"] = format(
            Decimal(row["trade_count"]) / Decimal(base_count),
            "f",
        )
        row["winner_preservation"] = {
            "count": format(
                Decimal(len(winners)) / Decimal(base_win_count)
                if base_win_count
                else Decimal(1),
                "f",
            ),
            "r": format(
                winner_r / base_win_r if base_win_r > 0 else Decimal(1),
                "f",
            ),
        }


def deserialize_lifecycle(
    path: Path,
    subject_root: Path,
) -> dict[str, dict[str, object]]:
    sys.path.insert(0, str((subject_root / "src").resolve()))
    from qore.infrastructure.cibo_position_lifecycle import (  # noqa: PLC0415
        CiboLifecycleEvent,
    )

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: lifecycle sidecar must be mapping")
    result: dict[str, dict[str, object]] = {}
    for signal, profile_raw in raw.items():
        if not isinstance(profile_raw, dict):
            raise ValueError(f"{path}: malformed lifecycle profile")
        profile = dict(profile_raw)
        events_raw = profile.get("events")
        if not isinstance(events_raw, list) or not events_raw:
            raise ValueError(f"{path}: lifecycle events missing")
        profile["events"] = tuple(
            CiboLifecycleEvent(
                occurred_at=datetime.fromisoformat(str(event["occurred_at"])),
                action=str(event["action"]),
                realized_r_delta=d(event["realized_r_delta"]),
                remaining_volume_fraction=d(
                    event["remaining_volume_fraction"]
                ),
                risk_fraction_remaining=d(
                    event["risk_fraction_remaining"]
                ),
                margin_fraction_remaining=d(
                    event["margin_fraction_remaining"]
                ),
            )
            for event in events_raw
        )
        profile["actions"] = tuple(profile.get("actions", []))
        profile["enabled_features"] = tuple(
            profile.get("enabled_features", [])
        )
        result[str(signal)] = profile
    return result


def run_case_worker(
    job: dict[str, object],
) -> tuple[str, dict[str, Any] | None, dict[str, str] | None]:
    name = str(job["name"])
    subject_root = Path(str(job["subject_root"]))
    sys.path.insert(0, str((subject_root / "src").resolve()))
    sys.path.insert(0, str((subject_root / "scripts").resolve()))
    import cibo_trader_lab_three_mode_ceiling as subject  # noqa: PLC0415

    lifecycle_path_raw = job.get("lifecycle_sidecar")
    original_builder = subject._build_lifecycle_map
    original_run = subject.run_three_mode_trader_lab
    fast_parameters = inspect.signature(original_run).parameters
    if {
        "collect_engineering_trace",
        "collect_epoch_receipts",
        "compact_trade_receipts",
    }.issubset(fast_parameters):
        def fast_run(*run_args: object, **run_kwargs: object) -> dict[str, object]:
            run_kwargs["collect_engineering_trace"] = False
            run_kwargs["collect_epoch_receipts"] = False
            run_kwargs["compact_trade_receipts"] = True
            return original_run(*run_args, **run_kwargs)

        subject.run_three_mode_trader_lab = fast_run
    if lifecycle_path_raw:
        lifecycle_map = deserialize_lifecycle(
            Path(str(lifecycle_path_raw)),
            subject_root,
        )

        def prepared_builder(*_args: object, **_kwargs: object) -> dict[str, dict[str, object]]:
            return lifecycle_map

        subject._build_lifecycle_map = prepared_builder

    case_output = Path(str(job["case_output"]))
    argv = [
        "cibo_trader_lab_three_mode_ceiling.py",
        "--manifest",
        str(job["manifest"]),
        "--output",
        str(case_output),
        "--baseline-replay",
        str(job["baseline"]),
        "--historical-manifest",
        str(job["primary"]),
        "--historical-replay",
        str(job["historical_replay"]),
    ]
    if bool(job["uses_atlas"]):
        for symbol in SYMBOLS:
            argv.extend(
                [
                    "--lifecycle-source-root",
                    f"{symbol}={job['atlas_roots'][symbol]}",
                ]
            )
    extra = job["extra"]
    if not isinstance(extra, list) or any(
        not isinstance(item, str) for item in extra
    ):
        raise ValueError(f"{name}: args must be string list")
    argv.extend(extra)

    previous = sys.argv
    try:
        sys.argv = argv
        rc = subject.main()
        if rc != 0:
            raise RuntimeError(f"{name}: subject runner returned {rc}")
        result = json.loads(case_output.read_text(encoding="utf-8"))
        return name, normalize_case(name, result), None
    except Exception as error:
        return (
            name,
            None,
            {
                "status": "FAILED_CASE",
                "error_type": type(error).__name__,
                "message": str(error),
            },
        )
    finally:
        sys.argv = previous
        subject._build_lifecycle_map = original_builder
        subject.run_three_mode_trader_lab = original_run


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--prepared", required=True, type=Path)
    parser.add_argument("--subject-root", required=True, type=Path)
    parser.add_argument("--suite", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    prepared = json.loads(args.prepared.read_text(encoding="utf-8"))
    if (
        prepared.get("schema")
        != "qore.github-trader-lab.cibo-three-mode-prepared.v2"
    ):
        raise ValueError("CIBO prepared lifecycle cache schema mismatch")
    if prepared.get("hot_path_requires_atlas_scan") is not False:
        raise ValueError("CIBO hot path unexpectedly requires Atlas scan")

    primary = Path(str(prepared["primary_evidence"]))
    assets = args.evidence_dir / "assets"
    walk_root = assets / "walk-forward"
    control_root = assets / "historical-control"
    manifest = find_one(walk_root, "walk-forward-manifest.json")
    baseline = find_one(walk_root, "walk-forward-replay.json")
    historical_replay = find_one(
        control_root,
        "historical-ceiling-replay.json",
    )
    atlas_roots = {
        symbol: str((assets / f"atlas-{symbol}").resolve())
        for symbol in SYMBOLS
    }

    suite = json.loads(args.suite.read_text(encoding="utf-8"))
    cases = suite.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("suite has no cases")

    lifecycle_sidecars = prepared.get("lifecycle_sidecars", {})
    if not isinstance(lifecycle_sidecars, dict):
        raise ValueError("prepared lifecycle sidecar index missing")

    raw_root = args.output.parent / "raw-cases"
    raw_root.mkdir(parents=True, exist_ok=True)
    jobs: list[dict[str, object]] = []
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("suite case must be mapping")
        name = str(case["name"])
        uses_atlas = bool(case.get("uses_atlas"))
        lifecycle_sidecar = None
        if uses_atlas:
            relative = lifecycle_sidecars.get(name)
            if not isinstance(relative, str):
                raise ValueError(f"{name}: prepared lifecycle sidecar missing")
            lifecycle_sidecar = str(
                (args.prepared.parent / relative).resolve()
            )
        jobs.append(
            {
                "name": name,
                "subject_root": str(args.subject_root.resolve()),
                "manifest": str(manifest.resolve()),
                "baseline": str(baseline.resolve()),
                "primary": str(primary.resolve()),
                "historical_replay": str(historical_replay.resolve()),
                "atlas_roots": atlas_roots,
                "uses_atlas": uses_atlas,
                "lifecycle_sidecar": lifecycle_sidecar,
                "extra": case.get("args", []),
                "case_output": str((raw_root / f"{name}.json").resolve()),
            }
        )

    requested = int(os.environ.get("QORE_TRADER_LAB_CASE_WORKERS", "4"))
    workers = max(1, min(len(jobs), requested, os.cpu_count() or 1))
    completed: dict[str, dict[str, Any]] = {}
    failures: dict[str, dict[str, str]] = {}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(run_case_worker, job): str(job["name"])
            for job in jobs
        }
        for future in as_completed(futures):
            name, row, failure = future.result()
            if failure is not None:
                failures[name] = failure
            elif row is not None:
                completed[name] = row

    control = str(cases[0]["name"])
    if control not in completed:
        raise RuntimeError(
            f"control case failed: {failures.get(control, {})}"
        )
    variants = {
        str(case["name"]): completed[str(case["name"])]
        for case in cases
        if str(case["name"]) in completed
    }
    apply_preservation(variants, control)

    payload = {
        "schema": "qore.github-trader-lab.normalized.v2",
        "subject": "CIBO",
        "lane": "cibo-three-mode-suite",
        "control": control,
        "variants": variants,
        "case_failures": failures,
        "governance": {
            "research_only": True,
            "same_subject_code_reused": True,
            "lifecycle_resolved_during_prepare": True,
            "atlas_scans_in_hot_path": 0,
            "case_workers": workers,
            "failed_case_count": len(failures),
            "failed_cases_are_research_outcomes": True,
            "trader_base_entry_conservation_required": True,
            "fresh_holdout_opened": False,
            "certification_claimed": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "control": control,
                "case_workers": workers,
                "atlas_scans_in_hot_path": 0,
                "case_failures": failures,
                "variants": {
                    name: {
                        "trade_count": row["trade_count"],
                        "ending_capital_usd": row["capital_path"][
                            "ending_capital_usd"
                        ],
                        "max_drawdown_fraction": row["capital_path"][
                            "maximum_drawdown_fraction"
                        ],
                    }
                    for name, row in variants.items()
                },
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
