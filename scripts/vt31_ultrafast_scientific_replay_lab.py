#!/usr/bin/env python3
"""VT31 ultra-fast scientific replay laboratory.

Research-only runner.  It executes the four retained NAS100 evidence folds in
parallel on one GitHub runner, streams structured progress in real time, reuses
safe cache entries when available, and adjudicates the complete scientific
battery already embedded in the VT31 comparator replay.

It never opens fresh holdout evidence and never claims certification.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.realtime_run_monitor import (
    RealtimeRunMonitor,
    github_log_sink,
)

FOLDS = ("r5", "r6", "r8", "consumed")
CONTROL = "COMP006_CONTROL"
SCHEMA = "qore.vt31.ultrafast-scientific-replay-lab.v1"


class UltraFastLabError(RuntimeError):
    """Raised for infrastructure or evidence failures in the research lab."""


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _pf(metrics: dict[str, Any]) -> Decimal:
    value = metrics.get("profit_factor")
    if value is not None:
        return _d(value)
    wins = int(metrics.get("wins", 0))
    losses = int(metrics.get("losses", 0))
    if wins > 0 and losses == 0:
        return Decimal("Infinity")
    return Decimal("-Infinity")


def _parse_fold(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("fold must be NAME=PATH")
    name, raw_path = value.split("=", 1)
    if name not in FOLDS:
        raise argparse.ArgumentTypeError(f"unexpected fold: {name}")
    return name, Path(raw_path)


def _compact_variant(row: dict[str, Any]) -> dict[str, Any]:
    metrics = row["stress_0_05r"]
    mc = row["monte_carlo"]
    winner = row["winner_preservation_vs_comp006"]
    return {
        "trade_count": row["trade_count"],
        "relative_density_vs_comp006": row["relative_density_vs_comp006"],
        "profit_factor": metrics.get("profit_factor"),
        "mean_r": metrics.get("mean_r"),
        "max_drawdown_r": metrics.get("max_drawdown_r"),
        "wins": metrics.get("wins"),
        "losses": metrics.get("losses"),
        "mc_paths": mc.get("paths"),
        "mc_positive_terminal_probability": mc.get(
            "positive_terminal_probability"
        ),
        "mc_p95_max_drawdown_r": mc.get("p95_max_drawdown_r"),
        "winner_count_preservation": winner.get("winner_count_preservation"),
        "winner_r_preservation": winner.get("winner_r_preservation"),
    }


def _tail(path: Path, limit: int = 20) -> list[str]:
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-limit:]


def _run_fold(
    *,
    name: str,
    evidence: Path,
    target_script: Path,
    output_root: Path,
    cache_root: Path,
    monitor: RealtimeRunMonitor,
    heartbeat_seconds: float,
) -> dict[str, Any]:
    fold_root = output_root / "folds" / name
    fold_root.mkdir(parents=True, exist_ok=True)
    cache_root.mkdir(parents=True, exist_ok=True)
    result_path = fold_root / "result.json"
    cache_path = cache_root / f"{name}.json"
    log_path = fold_root / "process.log"
    started = time.monotonic()

    if cache_path.is_file():
        shutil.copy2(cache_path, result_path)
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        elapsed = time.monotonic() - started
        summary = {
            "cache_hit": True,
            "elapsed_seconds": round(elapsed, 3),
            "variants": {
                key: _compact_variant(value)
                for key, value in payload["variants"].items()
            },
        }
        monitor.set_lane(
            name,
            status="COMPLETE",
            stage="CACHE_HIT",
            elapsed_seconds=elapsed,
            summary=summary,
        )
        monitor.emit("fold.cache_hit", summary, lane=name)
        return payload

    monitor.set_lane(name, status="RUNNING", stage="REPLAY")
    monitor.emit(
        "fold.started",
        {
            "evidence": str(evidence),
            "target_script": str(target_script),
            "cache_hit": False,
        },
        lane=name,
    )

    command = [
        sys.executable,
        str(target_script),
        str(evidence),
        "--output",
        str(result_path),
    ]
    env = {
        **os.environ,
        "PYTHONUNBUFFERED": "1",
    }
    with log_path.open("w", encoding="utf-8") as handle:
        process = subprocess.Popen(
            command,
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        last_heartbeat = 0.0
        while process.poll() is None:
            elapsed = time.monotonic() - started
            if elapsed - last_heartbeat >= heartbeat_seconds:
                last_heartbeat = elapsed
                monitor.set_lane(
                    name,
                    status="RUNNING",
                    stage="REPLAY",
                    elapsed_seconds=elapsed,
                )
                monitor.emit(
                    "fold.heartbeat",
                    {
                        "elapsed_seconds": round(elapsed, 3),
                        "log_bytes": (
                            log_path.stat().st_size if log_path.exists() else 0
                        ),
                    },
                    lane=name,
                )
            time.sleep(min(1.0, heartbeat_seconds))

    elapsed = time.monotonic() - started
    if process.returncode != 0:
        message = {
            "exit_code": process.returncode,
            "elapsed_seconds": round(elapsed, 3),
            "log_tail": _tail(log_path),
        }
        monitor.set_lane(
            name,
            status="FAILED",
            stage="FAILED",
            elapsed_seconds=elapsed,
            error=json.dumps(message, sort_keys=True),
        )
        monitor.emit("fold.failed", message, lane=name)
        raise UltraFastLabError(
            f"{name} replay failed with exit {process.returncode}"
        )
    if not result_path.is_file():
        raise UltraFastLabError(f"{name} did not produce {result_path}")

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    shutil.copy2(result_path, cache_path)
    summary = {
        "cache_hit": False,
        "elapsed_seconds": round(elapsed, 3),
        "variants": {
            key: _compact_variant(value)
            for key, value in payload["variants"].items()
        },
    }
    monitor.set_lane(
        name,
        status="COMPLETE",
        stage="COMPLETE",
        elapsed_seconds=elapsed,
        summary=summary,
    )
    monitor.emit("fold.completed", summary, lane=name)
    return payload


def _halfyear_nondegrade(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    common = sorted(
        set(baseline["halfyear_stress"])
        & set(candidate["halfyear_stress"])
    )
    details: dict[str, Any] = {}
    all_ok = bool(common)
    for key in common:
        base = baseline["halfyear_stress"][key]
        cand = candidate["halfyear_stress"][key]
        mean_delta = _d(cand["mean_r"]) - _d(base["mean_r"])
        dd_ok = _d(cand["max_drawdown_r"]) <= _d(base["max_drawdown_r"])
        ok = mean_delta >= 0 and dd_ok
        all_ok &= ok
        details[key] = {
            "mean_r_delta": format(mean_delta, "f"),
            "dd_nondegrade": dd_ok,
            "nondegrade": ok,
        }
    return all_ok, details


def _scientific_battery(
    payloads: dict[str, dict[str, Any]],
    *,
    target_script: Path,
) -> dict[str, Any]:
    variant_names = tuple(payloads["consumed"]["variants"])
    if CONTROL not in variant_names:
        raise UltraFastLabError(f"required control {CONTROL} not found")
    if any(tuple(payloads[fold]["variants"]) != variant_names for fold in FOLDS):
        raise UltraFastLabError("variant identity differs across folds")

    report: dict[str, Any] = {}
    for variant in variant_names:
        per_fold: dict[str, Any] = {}
        pf_ok = 0
        mean_ok = 0
        dd_ok = 0
        density_ok = 0
        winner_all = True
        temporal_all = True
        mc_complete = True

        for fold in FOLDS:
            baseline = payloads[fold]["variants"][CONTROL]
            candidate = payloads[fold]["variants"][variant]
            bm = baseline["stress_0_05r"]
            cm = candidate["stress_0_05r"]
            winner = candidate["winner_preservation_vs_comp006"]
            mc = candidate["monte_carlo"]

            pf_non = _pf(cm) >= _pf(bm)
            mean_non = _d(cm["mean_r"]) >= _d(bm["mean_r"])
            dd_non = _d(cm["max_drawdown_r"]) <= _d(bm["max_drawdown_r"])
            density = _d(candidate["relative_density_vs_comp006"]) >= Decimal(
                "0.75"
            )
            winner_ok = (
                _d(winner["winner_count_preservation"]) >= Decimal("0.80")
                and _d(winner["winner_r_preservation"]) >= Decimal("0.90")
            )
            temporal_ok, temporal = _halfyear_nondegrade(
                baseline,
                candidate,
            )
            mc_ok = (
                int(mc.get("paths", 0)) == 10000
                and mc.get("positive_terminal_probability") is not None
                and mc.get("p95_max_drawdown_r") is not None
            )

            pf_ok += int(pf_non)
            mean_ok += int(mean_non)
            dd_ok += int(dd_non)
            density_ok += int(density)
            winner_all &= winner_ok
            temporal_all &= temporal_ok
            mc_complete &= mc_ok

            per_fold[fold] = {
                "baseline": _compact_variant(baseline),
                "candidate": _compact_variant(candidate),
                "pf_nondegrade": pf_non,
                "mean_nondegrade": mean_non,
                "dd_nondegrade": dd_non,
                "density_floor_pass": density,
                "winner_floor_pass": winner_ok,
                "halfyear_nondegrade": temporal_ok,
                "halfyears": temporal,
                "monte_carlo_complete_10000": mc_ok,
            }

        recent = payloads["consumed"]["variants"][variant]
        recent_metrics = recent["stress_0_05r"]
        recent_mc = recent["monte_carlo"]
        owner = {
            "pf_at_least_1_70": _pf(recent_metrics) >= Decimal("1.70"),
            "mean_at_least_0_15r": _d(recent_metrics["mean_r"])
            >= Decimal("0.15"),
            "observed_dd_at_most_6r": _d(recent_metrics["max_drawdown_r"])
            <= Decimal("6"),
            "mc_positive_at_least_0_90": _d(
                recent_mc["positive_terminal_probability"]
            )
            >= Decimal("0.90"),
            "mc_p95_dd_at_most_15r": _d(recent_mc["p95_max_drawdown_r"])
            <= Decimal("15"),
        }
        era_pf_all = all(
            _pf(payloads[fold]["variants"][variant]["stress_0_05r"])
            >= Decimal("1.50")
            for fold in FOLDS
        )
        all_dd_6 = all(
            _d(
                payloads[fold]["variants"][variant]["stress_0_05r"][
                    "max_drawdown_r"
                ]
            )
            <= Decimal("6")
            for fold in FOLDS
        )
        development_survivor = (
            pf_ok == len(FOLDS)
            and mean_ok == len(FOLDS)
            and dd_ok == len(FOLDS)
            and density_ok == len(FOLDS)
            and winner_all
            and temporal_all
            and mc_complete
        )
        scientific_pass = (
            development_survivor
            and era_pf_all
            and all_dd_6
            and all(owner.values())
        )

        worst_pf = min(
            _pf(payloads[fold]["variants"][variant]["stress_0_05r"])
            for fold in FOLDS
        )
        worst_mean = min(
            _d(payloads[fold]["variants"][variant]["stress_0_05r"]["mean_r"])
            for fold in FOLDS
        )
        worst_dd = max(
            _d(
                payloads[fold]["variants"][variant]["stress_0_05r"][
                    "max_drawdown_r"
                ]
            )
            for fold in FOLDS
        )

        report[variant] = {
            "folds": per_fold,
            "pf_nondegrade_folds": pf_ok,
            "mean_nondegrade_folds": mean_ok,
            "dd_nondegrade_folds": dd_ok,
            "density_floor_folds": density_ok,
            "winner_preservation_all_folds": winner_all,
            "halfyears_all_nondegrade": temporal_all,
            "monte_carlo_10000_all_folds": mc_complete,
            "era_pf_at_least_1_50_all_folds": era_pf_all,
            "all_consumed_folds_observed_dd_at_most_6r": all_dd_6,
            "owner_direction_gates_recent": owner,
            "cross_fold_worst_case": {
                "profit_factor": format(worst_pf, "f"),
                "mean_r": format(worst_mean, "f"),
                "max_drawdown_r": format(worst_dd, "f"),
            },
            "development_survivor": development_survivor,
            "scientific_pass": scientific_pass,
            "promotion_authorized": False,
            "certification_authorized": False,
        }

    survivors = [
        name
        for name, row in report.items()
        if row["development_survivor"]
    ]
    six_r_survivors = [
        name
        for name, row in report.items()
        if row["development_survivor"]
        and row["all_consumed_folds_observed_dd_at_most_6r"]
    ]
    scientific_passes = [
        name for name, row in report.items() if row["scientific_pass"]
    ]
    return {
        "schema": SCHEMA,
        "target_script": str(target_script),
        "folds": list(FOLDS),
        "control": CONTROL,
        "battery_layers": [
            "FOUR_INDEPENDENT_RETAINED_FOLDS",
            "FIXED_0_05R_FRICTION",
            "PF_MEAN_DD_NONDEGRADE",
            "DENSITY_FLOOR",
            "WINNER_COUNT_AND_R_PRESERVATION",
            "HALFYEAR_TEMPORAL_STRESS",
            "DETERMINISTIC_10000_PATH_BLOCK_BOOTSTRAP_MONTE_CARLO",
            "CROSS_FOLD_ERA_PF",
            "OBSERVED_DD_HARD_GATE_6R",
            "RECENT_OWNER_DIRECTION_GATES",
        ],
        "variants": report,
        "development_survivors": survivors,
        "six_r_all_fold_survivors": six_r_survivors,
        "scientific_passes": scientific_passes,
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "pure_edge_only": True,
            "observed_dd_certification_max_r": "6",
            "sizing_for_certification_forbidden": True,
            "fresh_holdout_opened": False,
            "policy_promoted": False,
            "candidate_frozen": False,
            "candidate_certified": False,
            "broker_mutation": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
            "sovereign_workflow_modified": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target-script",
        type=Path,
        default=Path(
            "scripts/vt31_nas100_rapid_breaker_conflict_admission_frontier_v1.py"
        ),
    )
    parser.add_argument(
        "--fold",
        action="append",
        type=_parse_fold,
        required=True,
        help="repeat exactly four times: r5=PATH, r6=PATH, r8=PATH, consumed=PATH",
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--cache-dir", required=True, type=Path)
    parser.add_argument("--heartbeat-seconds", type=float, default=5.0)
    parser.add_argument(
        "--run-id",
        default=os.environ.get("GITHUB_RUN_ID", "local"),
    )
    args = parser.parse_args()

    fold_map = dict(args.fold)
    if set(fold_map) != set(FOLDS) or len(args.fold) != len(FOLDS):
        raise UltraFastLabError(
            "exactly r5, r6, r8 and consumed must be supplied once"
        )
    if not args.target_script.is_file():
        raise UltraFastLabError(f"target script not found: {args.target_script}")
    for name, path in fold_map.items():
        if not path.is_file():
            raise UltraFastLabError(f"{name} evidence not found: {path}")

    monitor = RealtimeRunMonitor(
        root=args.output_dir,
        run_id=str(args.run_id),
        lanes=FOLDS,
        event_sink=github_log_sink,
    )
    monitor.set_run_status("RUNNING")
    monitor.emit(
        "run.started",
        {
            "target_script": str(args.target_script),
            "folds": {key: str(value) for key, value in fold_map.items()},
            "max_parallel_folds": len(FOLDS),
            "scientific_battery": True,
        },
    )

    try:
        payloads: dict[str, dict[str, Any]] = {}
        with ThreadPoolExecutor(
            max_workers=len(FOLDS),
            thread_name_prefix="vt31-ultrafast",
        ) as pool:
            futures = {
                pool.submit(
                    _run_fold,
                    name=name,
                    evidence=fold_map[name],
                    target_script=args.target_script,
                    output_root=args.output_dir,
                    cache_root=args.cache_dir,
                    monitor=monitor,
                    heartbeat_seconds=args.heartbeat_seconds,
                ): name
                for name in FOLDS
            }
            for future in as_completed(futures):
                name = futures[future]
                payloads[name] = future.result()

        monitor.emit("battery.started", {"layers": 10})
        battery = _scientific_battery(
            {name: payloads[name] for name in FOLDS},
            target_script=args.target_script,
        )
        battery_path = args.output_dir / "scientific-battery.json"
        battery_path.write_text(
            json.dumps(battery, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        headline = {
            "schema": "qore.vt31.ultrafast-scientific-replay-headline.v1",
            "development_survivors": battery["development_survivors"],
            "six_r_all_fold_survivors": battery["six_r_all_fold_survivors"],
            "scientific_passes": battery["scientific_passes"],
            "certification_claimed": False,
            "fresh_holdout_opened": False,
        }
        (args.output_dir / "headline.json").write_text(
            json.dumps(headline, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        monitor.emit("battery.completed", headline)
        monitor.set_run_status("COMPLETE")
        monitor.emit("run.completed", headline)
        print(
            "QORE_ULTRAFAST_HEADLINE "
            + json.dumps(headline, sort_keys=True),
            flush=True,
        )
        return 0
    except Exception as error:
        monitor.set_run_status("FAILED")
        monitor.emit("run.failed", {"error": str(error)})
        raise


if __name__ == "__main__":
    raise SystemExit(main())
