#!/usr/bin/env python3
"""Independent GitHub Trader Lab execution engine.

A profile declares lanes, replay commands, an adapter, and scientific gates.
The engine knows nothing about any specific Trader. It executes lanes
concurrently, streams structured events, persists status, and delegates final
adjudication to the generic scientific battery.
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
from pathlib import Path
from typing import Any

from realtime import RealtimeMonitor
from science import evaluate


class TraderLabError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TraderLabError(f"expected object: {path}")
    return raw


def format_command(
    template: list[str],
    values: dict[str, str],
) -> list[str]:
    command = [token.format(**values) for token in template]
    if command and command[0] == "python":
        command[0] = sys.executable
    return command


def tail(path: Path, count: int = 30) -> list[str]:
    if not path.is_file():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()[-count:]


def run_process(
    *,
    command: list[str],
    cwd: Path,
    log_path: Path,
    lane: str,
    stage: str,
    monitor: RealtimeMonitor,
    heartbeat_seconds: float,
    started: float,
) -> None:
    monitor.set_lane(lane, status="RUNNING", stage=stage)
    monitor.emit(
        "stage.started",
        {"stage": stage, "command": command},
        lane=lane,
    )
    with log_path.open("a", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        last_heartbeat = -heartbeat_seconds
        while process.poll() is None:
            elapsed = time.monotonic() - started
            if elapsed - last_heartbeat >= heartbeat_seconds:
                last_heartbeat = elapsed
                monitor.set_lane(
                    lane,
                    status="RUNNING",
                    stage=stage,
                    elapsed_seconds=elapsed,
                )
                monitor.emit(
                    "stage.heartbeat",
                    {
                        "stage": stage,
                        "elapsed_seconds": round(elapsed, 3),
                        "log_bytes": log_path.stat().st_size if log_path.exists() else 0,
                    },
                    lane=lane,
                )
            time.sleep(min(1.0, heartbeat_seconds))
    if process.returncode != 0:
        raise TraderLabError(
            f"{lane} {stage} failed with exit {process.returncode}; "
            f"tail={tail(log_path)}"
        )
    monitor.emit(
        "stage.completed",
        {
            "stage": stage,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        },
        lane=lane,
    )


def compact_summary(payload: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, row in payload["variants"].items():
        metrics = row["metrics"]
        mc = row["monte_carlo"]
        out[name] = {
            "trade_count": row["trade_count"],
            "density": row["relative_density_vs_control"],
            "profit_factor": metrics.get("profit_factor"),
            "mean_r": metrics.get("mean_r"),
            "max_drawdown_r": metrics.get("max_drawdown_r"),
            "mc_positive": mc.get("positive_terminal_probability"),
            "mc_p95_dd_r": mc.get("p95_max_drawdown_r"),
        }
    return out


def run_lane(
    *,
    lane: str,
    profile: dict[str, Any],
    lab_root: Path,
    subject_root: Path,
    evidence_dir: Path,
    output_root: Path,
    cache_dir: Path,
    monitor: RealtimeMonitor,
    heartbeat_seconds: float,
) -> dict[str, Any]:
    started = time.monotonic()
    lane_root = output_root / "lanes" / lane
    lane_root.mkdir(parents=True, exist_ok=True)
    log_path = lane_root / "process.log"
    raw_output = lane_root / "raw.json"
    normalized_output = lane_root / "normalized.json"
    cache_raw = cache_dir / f"{lane}.raw.json"
    cache_normalized = cache_dir / f"{lane}.normalized.json"
    cache_dir.mkdir(parents=True, exist_ok=True)

    if cache_raw.is_file() and cache_normalized.is_file():
        shutil.copy2(cache_raw, raw_output)
        shutil.copy2(cache_normalized, normalized_output)
        payload = load_json(normalized_output)
        elapsed = time.monotonic() - started
        summary = {
            "cache_hit": True,
            "elapsed_seconds": round(elapsed, 3),
            "variants": compact_summary(payload),
        }
        monitor.set_lane(
            lane,
            status="COMPLETE",
            stage="CACHE_HIT",
            elapsed_seconds=elapsed,
            summary=summary,
        )
        monitor.emit("lane.completed", summary, lane=lane)
        return payload

    evidence = (evidence_dir / f"{lane}.json").resolve()
    if not evidence.is_file():
        raise TraderLabError(f"missing evidence for lane {lane}: {evidence}")

    values = {
        "lane": lane,
        "lab_root": str(lab_root),
        "subject_root": str(subject_root),
        "evidence": str(evidence),
        "raw_output": str(raw_output),
        "normalized_output": str(normalized_output),
        "lane_root": str(lane_root),
    }

    replay_template = profile["replay"]["command"]
    adapter_template = profile["replay"]["adapter_command"]
    replay_command = format_command(replay_template, values)
    adapter_command = format_command(adapter_template, values)

    monitor.emit(
        "lane.started",
        {
            "cache_hit": False,
            "evidence": str(evidence),
            "subject": profile["subject"],
        },
        lane=lane,
    )
    try:
        run_process(
            command=replay_command,
            cwd=subject_root,
            log_path=log_path,
            lane=lane,
            stage="REPLAY",
            monitor=monitor,
            heartbeat_seconds=heartbeat_seconds,
            started=started,
        )
        run_process(
            command=adapter_command,
            cwd=lab_root,
            log_path=log_path,
            lane=lane,
            stage="NORMALIZE",
            monitor=monitor,
            heartbeat_seconds=heartbeat_seconds,
            started=started,
        )
        if not raw_output.is_file() or not normalized_output.is_file():
            raise TraderLabError(f"{lane} missing replay/normalized outputs")
        payload = load_json(normalized_output)
        shutil.copy2(raw_output, cache_raw)
        shutil.copy2(normalized_output, cache_normalized)
        elapsed = time.monotonic() - started
        summary = {
            "cache_hit": False,
            "elapsed_seconds": round(elapsed, 3),
            "variants": compact_summary(payload),
        }
        monitor.set_lane(
            lane,
            status="COMPLETE",
            stage="COMPLETE",
            elapsed_seconds=elapsed,
            summary=summary,
        )
        monitor.emit("lane.completed", summary, lane=lane)
        return payload
    except Exception as error:
        elapsed = time.monotonic() - started
        monitor.set_lane(
            lane,
            status="FAILED",
            stage="FAILED",
            elapsed_seconds=elapsed,
            error=str(error),
        )
        monitor.emit(
            "lane.failed",
            {
                "error": str(error),
                "elapsed_seconds": round(elapsed, 3),
                "log_tail": tail(log_path),
            },
            lane=lane,
        )
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--lab-root", required=True, type=Path)
    parser.add_argument("--subject-root", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--cache-dir", required=True, type=Path)
    parser.add_argument("--heartbeat-seconds", type=float, default=5.0)
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    args = parser.parse_args()

    profile = load_json(args.profile)
    if profile.get("schema") != "qore.github-trader-lab.profile.v1":
        raise TraderLabError("unsupported profile schema")
    lanes = tuple(profile["lanes"])
    if not lanes:
        raise TraderLabError("profile has no lanes")

    monitor = RealtimeMonitor(args.output_dir, str(args.run_id), lanes)
    monitor.set_run("RUNNING")
    monitor.emit(
        "run.started",
        {
            "profile_id": profile["profile_id"],
            "subject": profile["subject"],
            "lanes": lanes,
            "max_parallel_lanes": min(
                len(lanes), int(profile.get("max_parallel_lanes", len(lanes)))
            ),
            "scientific_battery": True,
        },
    )

    try:
        payloads: dict[str, dict[str, Any]] = {}
        max_workers = min(
            len(lanes), int(profile.get("max_parallel_lanes", len(lanes)))
        )
        with ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="qore-github-trader-lab",
        ) as pool:
            futures = {
                pool.submit(
                    run_lane,
                    lane=lane,
                    profile=profile,
                    lab_root=args.lab_root,
                    subject_root=args.subject_root,
                    evidence_dir=args.evidence_dir,
                    output_root=args.output_dir,
                    cache_dir=args.cache_dir,
                    monitor=monitor,
                    heartbeat_seconds=args.heartbeat_seconds,
                ): lane
                for lane in lanes
            }
            for future in as_completed(futures):
                lane = futures[future]
                payloads[lane] = future.result()

        monitor.emit("science.started", {"profile_id": profile["profile_id"]})
        battery = evaluate(
            profile,
            {lane: payloads[lane] for lane in lanes},
        )
        science_path = args.output_dir / "scientific-battery.json"
        science_path.write_text(
            json.dumps(battery, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        headline = {
            "schema": "qore.github-trader-lab.headline.v1",
            "profile_id": profile["profile_id"],
            "subject": profile["subject"],
            "development_survivors": battery["development_survivors"],
            "hard_dd_survivors": battery["hard_dd_survivors"],
            "scientific_passes": battery["scientific_passes"],
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
        print("QORE_TRADER_LAB_HEADLINE " + json.dumps(headline, sort_keys=True), flush=True)
        return 0
    except Exception as error:
        monitor.set_run("FAILED")
        monitor.emit("run.failed", {"error": str(error)})
        raise


if __name__ == "__main__":
    raise SystemExit(main())
