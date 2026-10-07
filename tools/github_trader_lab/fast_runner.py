#!/usr/bin/env python3
"""Prepared-ledger execution engine for QORE GitHub Trader Lab."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from certification import evaluate_certification_readiness
from loss_compression import evaluate_loss_compression
from realtime import RealtimeMonitor
from science import evaluate


class FastRunnerError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise FastRunnerError(f"expected object: {path}")
    return raw


def realtime_report_payload(row: dict[str, Any]) -> dict[str, Any]:
    """Keep decision-grade report content while omitting raw trade vectors."""

    return {
        key: value
        for key, value in row.items()
        if key not in {"net_r_values"}
    }


def command(template: list[str], values: dict[str, str]) -> list[str]:
    result = [token.format(**values) for token in template]
    if result and result[0] == "python":
        result[0] = sys.executable
    return result


def run_command(
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
) -> None:
    subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        check=True,
    )


def prepare_lane(
    *,
    lane: str,
    profile: dict[str, Any],
    lab_root: Path,
    subject_root: Path,
    evidence_dir: Path,
    prepared_dir: Path,
    monitor: RealtimeMonitor,
) -> None:
    prepared = (prepared_dir / f"{lane}.json").resolve()
    if prepared.is_file():
        monitor.emit(
            "prepare.cache_hit",
            {"prepared": str(prepared)},
            lane=lane,
        )
        return

    evidence = (evidence_dir / f"{lane}.json").resolve()
    values = {
        "lane": lane,
        "lab_root": str(lab_root.resolve()),
        "subject_root": str(subject_root.resolve()),
        "evidence_dir": str(evidence_dir.resolve()),
        "evidence": str(evidence),
        "prepared": str(prepared),
    }
    started = time.monotonic()
    monitor.set_lane(lane, status="RUNNING", stage="PREPARE")
    monitor.emit("prepare.started", {"evidence": str(evidence)}, lane=lane)
    run_command(
        command(profile["preparation"]["command"], values),
        cwd=subject_root.resolve(),
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    elapsed = time.monotonic() - started
    if not prepared.is_file():
        raise FastRunnerError(f"{lane}: preparation did not create {prepared}")
    monitor.emit(
        "prepare.completed",
        {"elapsed_seconds": round(elapsed, 3)},
        lane=lane,
    )


def experiment_lane(
    *,
    lane: str,
    profile: dict[str, Any],
    lab_root: Path,
    subject_root: Path,
    evidence_dir: Path,
    prepared_dir: Path,
    output_dir: Path,
    monitor: RealtimeMonitor,
) -> dict[str, Any]:
    prepared = (prepared_dir / f"{lane}.json").resolve()
    lane_root = (output_dir / "lanes" / lane).resolve()
    lane_root.mkdir(parents=True, exist_ok=True)
    normalized = lane_root / "normalized.json"
    values = {
        "lane": lane,
        "lab_root": str(lab_root.resolve()),
        "subject_root": str(subject_root.resolve()),
        "evidence_dir": str(evidence_dir.resolve()),
        "prepared": str(prepared),
        "normalized_output": str(normalized.resolve()),
        "lane_root": str(lane_root),
    }
    started = time.monotonic()
    monitor.set_lane(lane, status="RUNNING", stage="EXPERIMENT")
    monitor.emit("experiment.started", {}, lane=lane)
    run_command(
        command(profile["experiment"]["command"], values),
        cwd=subject_root.resolve(),
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    elapsed = time.monotonic() - started
    payload = load(normalized)
    summary = {
        "elapsed_seconds": round(elapsed, 3),
        "variants": {
            name: {
                "trade_count": row["trade_count"],
                "profit_factor": row["metrics"].get("profit_factor"),
                "mean_r": row["metrics"].get("mean_r"),
                "max_drawdown_r": row["metrics"].get("max_drawdown_r"),
            }
            for name, row in payload["variants"].items()
        },
    }
    for name, row in payload["variants"].items():
        monitor.report(
            "experiment.variant",
            realtime_report_payload(row),
            lane=lane,
            variant=name,
        )
    case_failures = payload.get("case_failures", {})
    if isinstance(case_failures, dict):
        for name, failure in case_failures.items():
            if isinstance(failure, dict):
                monitor.report(
                    "experiment.case_failure",
                    failure,
                    lane=lane,
                    variant=str(name),
                )
        summary["failed_cases"] = sorted(str(name) for name in case_failures)

    monitor.set_lane(
        lane,
        status="COMPLETE",
        stage="EXPERIMENT_COMPLETE",
        elapsed_seconds=elapsed,
        summary=summary,
    )
    monitor.emit("experiment.completed", summary, lane=lane)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--lab-root", required=True, type=Path)
    parser.add_argument("--subject-root", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--prepared-dir", required=True, type=Path)
    parser.add_argument("--science-cache-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--run-id",
        default=os.environ.get("GITHUB_RUN_ID", "local"),
    )
    args = parser.parse_args()

    profile = load(args.profile)
    if profile.get("schema") != "qore.github-trader-lab.profile.v2":
        raise FastRunnerError("unsupported fast profile schema")
    lanes = tuple(profile["lanes"])
    workers = min(
        len(lanes),
        int(profile.get("max_parallel_lanes", len(lanes))),
    )
    args.prepared_dir.mkdir(parents=True, exist_ok=True)
    args.science_cache_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    monitor = RealtimeMonitor(args.output_dir.resolve(), str(args.run_id), lanes)
    monitor.set_run("RUNNING")
    overall_started = time.monotonic()
    monitor.emit(
        "run.started",
        {
            "profile_id": profile["profile_id"],
            "subject": profile["subject"],
            "lanes": lanes,
            "prepared_ledger_architecture": True,
            "max_parallel_lanes": workers,
        },
    )

    try:
        with ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="qore-prepare",
        ) as pool:
            futures = [
                pool.submit(
                    prepare_lane,
                    lane=lane,
                    profile=profile,
                    lab_root=args.lab_root,
                    subject_root=args.subject_root,
                    evidence_dir=args.evidence_dir,
                    prepared_dir=args.prepared_dir,
                    monitor=monitor,
                )
                for lane in lanes
            ]
            for future in as_completed(futures):
                future.result()

        experiment_started = time.monotonic()
        payloads: dict[str, dict[str, Any]] = {}
        with ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix="qore-experiment",
        ) as pool:
            futures = {
                pool.submit(
                    experiment_lane,
                    lane=lane,
                    profile=profile,
                    lab_root=args.lab_root,
                    subject_root=args.subject_root,
                    evidence_dir=args.evidence_dir,
                    prepared_dir=args.prepared_dir,
                    output_dir=args.output_dir,
                    monitor=monitor,
                ): lane
                for lane in lanes
            }
            for future in as_completed(futures):
                lane = futures[future]
                payloads[lane] = future.result()

        replay_seconds = time.monotonic() - experiment_started

        loss_compression_started = time.monotonic()
        loss_compression = evaluate_loss_compression(
            profile,
            {lane: payloads[lane] for lane in lanes},
        )
        loss_compression_seconds = (
            time.monotonic() - loss_compression_started
        )
        if loss_compression is not None:
            (args.output_dir / "loss-compression-report.json").write_text(
                json.dumps(
                    loss_compression,
                    indent=2,
                    sort_keys=True,
                ) + "\n",
                encoding="utf-8",
            )
            for name, row in loss_compression["variants"].items():
                monitor.report(
                    "loss_compression.variant",
                    row,
                    variant=name,
                )
            monitor.report(
                "loss_compression.summary",
                {
                    "control": loss_compression["control"],
                    "control_baseline": loss_compression[
                        "control_baseline"
                    ],
                    **loss_compression["summary"],
                },
            )

        science_started = time.monotonic()
        monitor.emit("science.started", {})
        battery = evaluate(
            profile,
            {lane: payloads[lane] for lane in lanes},
            mc_cache_dir=args.science_cache_dir,
        )
        science_seconds = time.monotonic() - science_started
        (args.output_dir / "scientific-battery.json").write_text(
            json.dumps(battery, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        for name, row in battery["variants"].items():
            monitor.report(
                "science.variant",
                realtime_report_payload(row),
                variant=name,
            )
        monitor.report(
            "science.summary",
            {
                "development_survivors": battery["development_survivors"],
                "hard_dd_survivors": battery["hard_dd_survivors"],
                "scientific_passes": battery["scientific_passes"],
                "monte_carlo_required_variants": battery[
                    "monte_carlo_required_variants"
                ],
                "monte_carlo_skipped_variants": battery[
                    "monte_carlo_skipped_variants"
                ],
                "monte_carlo_cache": battery.get("monte_carlo_cache", {}),
            },
        )

        certification_started = time.monotonic()
        monitor.emit("certification_readiness.started", {})
        readiness = evaluate_certification_readiness(
            profile,
            {lane: payloads[lane] for lane in lanes},
            battery,
        )
        certification_seconds = time.monotonic() - certification_started
        (args.output_dir / "certification-readiness.json").write_text(
            json.dumps(readiness, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        for name, row in readiness["variants"].items():
            monitor.report(
                "certification.variant",
                realtime_report_payload(row),
                variant=name,
            )

        readiness_statuses = {
            name: row["readiness_status"]
            for name, row in readiness["variants"].items()
        }
        primary_lane = str(profile["science"]["primary_lane"])
        primary_risk_adjusted = {
            name: {
                "sharpe": row["lanes"][primary_lane]["risk_adjusted"].get(
                    "sharpe_per_trade_nonannualized"
                ),
                "sortino": row["lanes"][primary_lane]["risk_adjusted"].get(
                    "sortino_per_trade_nonannualized_mar0"
                ),
                "recovery_factor": row["lanes"][primary_lane][
                    "risk_adjusted"
                ].get("recovery_factor_total_r_over_max_dd"),
                "cvar_05_r": row["lanes"][primary_lane]["risk_adjusted"].get(
                    "cvar_05_trade_r"
                ),
            }
            for name, row in readiness["variants"].items()
        }
        monitor.emit(
            "certification_readiness.completed",
            {
                "readiness_statuses": readiness_statuses,
                "primary_lane": primary_lane,
                "primary_risk_adjusted": primary_risk_adjusted,
            },
        )

        compute_seconds = (
            replay_seconds
            + loss_compression_seconds
            + science_seconds
            + certification_seconds
        )
        total_seconds = time.monotonic() - overall_started
        headline = {
            "schema": "qore.github-trader-lab.fast-headline.v2",
            "profile_id": profile["profile_id"],
            "subject": profile["subject"],
            "experiment_replay_seconds": round(replay_seconds, 3),
            "loss_compression_seconds": round(
                loss_compression_seconds, 3
            ),
            "scientific_battery_seconds": round(science_seconds, 3),
            "certification_readiness_seconds": round(
                certification_seconds, 3
            ),
            "hot_compute_seconds": round(compute_seconds, 3),
            "runner_total_seconds": round(total_seconds, 3),
            "development_survivors": battery["development_survivors"],
            "hard_dd_survivors": battery["hard_dd_survivors"],
            "scientific_passes": battery["scientific_passes"],
            "monte_carlo_cache": battery.get("monte_carlo_cache", {}),
            "loss_compression_available": loss_compression is not None,
            "loss_compression_summary": (
                None
                if loss_compression is None
                else loss_compression["summary"]
            ),
            "certification_readiness": readiness_statuses,
            "primary_lane": primary_lane,
            "primary_risk_adjusted": primary_risk_adjusted,
            "walk_forward_oos_present": any(
                role == "WALK_FORWARD_OOS"
                for role in readiness["evidence_roles"].values()
            ),
            "fresh_oos_present": any(
                role == "FRESH_OOS"
                for role in readiness["evidence_roles"].values()
            ),
            "fresh_holdout_opened": False,
            "certification_claimed": False,
            "sovereign_workflow_modified": False,
        }
        (args.output_dir / "headline.json").write_text(
            json.dumps(headline, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        monitor.emit("science.completed", headline)
        monitor.set_run("COMPLETE")
        monitor.emit("run.completed", headline)
        monitor.report("run.headline", headline)
        monitor.report(
            "run.report_index",
            {
                "stream_file": "live-reports.jsonl",
                "events_file": "events.jsonl",
                "status_file": "status.json",
                "scientific_battery_file": "scientific-battery.json",
                "certification_readiness_file": "certification-readiness.json",
                "loss_compression_file": (
                    "loss-compression-report.json"
                    if loss_compression is not None
                    else None
                ),
                "lane_normalized_files": {
                    lane: f"lanes/{lane}/normalized.json"
                    for lane in lanes
                },
                "artifact_download_required_for_reports": False,
            },
        )
        print(
            "QORE_TRADER_LAB_FAST_HEADLINE "
            + json.dumps(headline, sort_keys=True),
            flush=True,
        )
        return 0
    except Exception as error:
        monitor.set_run("FAILED")
        monitor.emit("run.failed", {"error": str(error)})
        raise


if __name__ == "__main__":
    raise SystemExit(main())
