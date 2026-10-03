"""Standalone real-time CIBO Trader Lab test bench.

This bench executes the three fixed 1Y integrated seven-Trader groups directly
from local evidence. It has no GitHub Actions, broker, LIVE, Production or real
capital dependency.

The bench streams structured events while the three groups run concurrently,
persists every run under a local workspace, and evaluates the canonical
all-seven-positive 3x1Y sensor after all groups finish.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from qore.infrastructure.cibo_phase22_provider_numeric_execution_receipt import (
    PHASE22_PROVIDER_NUMERIC_EXECUTION_FREEZE_RECEIPT,
)
from qore.infrastructure.trader_lab.cibo_three_holdout_1y_contract import (
    GROUP_WINDOWS,
    evaluate_three_groups,
)

BENCH_SCHEMA = "qore.cibo.trader-lab.realtime-bench.v1"
CONFIG_SCHEMA = "qore.cibo.trader-lab.realtime-bench-config.v1"
GROUP_IDS = tuple(row[0] for row in GROUP_WINDOWS)
REGIME_SYMBOLS = ("AUDJPY", "EURUSD", "GBPJPY", "GBPUSD", "XAUUSD")


class RealtimeBenchError(RuntimeError):
    """Raised when the standalone bench contract is invalid or execution fails."""


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise RealtimeBenchError(f"expected JSON object: {path}")
    return raw


def _resolve(base: Path, raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise RealtimeBenchError(f"{label} must be a non-empty path")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (base / path).resolve()
    return path


@dataclass(frozen=True, slots=True)
class RealtimeBenchConfig:
    config_path: Path
    repository_root: Path
    workspace: Path
    assembly_root: Path
    provider_numeric: Path
    provider_numeric_freeze_sha256: str
    regime_roots: tuple[tuple[str, Path], ...]
    replay_started_at: str
    max_parallel_groups: int = 3

    @classmethod
    def load(cls, path: Path) -> "RealtimeBenchConfig":
        path = path.resolve()
        raw = _json(path)
        if raw.get("schema") != CONFIG_SCHEMA:
            raise RealtimeBenchError("unexpected realtime bench config schema")
        base = path.parent

        repository_root = _resolve(
            base,
            raw.get("repository_root", "."),
            "repository_root",
        )
        workspace = _resolve(base, raw.get("workspace"), "workspace")
        assembly_root = _resolve(
            base,
            raw.get("assembly_root"),
            "assembly_root",
        )
        provider_numeric = _resolve(
            base,
            raw.get("provider_numeric"),
            "provider_numeric",
        )

        freeze = raw.get("provider_numeric_freeze_sha256")
        if freeze is None:
            freeze = (
                PHASE22_PROVIDER_NUMERIC_EXECUTION_FREEZE_RECEIPT
                .provider_numeric_freeze_file_sha256
            )
        if not isinstance(freeze, str) or not freeze.startswith("sha256:"):
            raise RealtimeBenchError(
                "provider_numeric_freeze_sha256 must be sha256:..."
            )

        raw_regime = raw.get("regime_roots")
        if not isinstance(raw_regime, dict):
            raise RealtimeBenchError("regime_roots must be an object")
        if set(raw_regime) != set(REGIME_SYMBOLS):
            raise RealtimeBenchError(
                "regime_roots must contain exact five regime symbols"
            )
        regime_roots = tuple(
            (
                symbol,
                _resolve(
                    base,
                    raw_regime[symbol],
                    f"regime_roots.{symbol}",
                ),
            )
            for symbol in REGIME_SYMBOLS
        )

        replay_started_at = raw.get("replay_started_at")
        if not isinstance(replay_started_at, str) or not replay_started_at:
            raise RealtimeBenchError("replay_started_at is required")
        parsed = datetime.fromisoformat(replay_started_at)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise RealtimeBenchError("replay_started_at must be timezone-aware")

        parallel = raw.get("max_parallel_groups", 3)
        if type(parallel) is not int or not 1 <= parallel <= 3:
            raise RealtimeBenchError("max_parallel_groups must be 1..3")

        return cls(
            config_path=path,
            repository_root=repository_root,
            workspace=workspace,
            assembly_root=assembly_root,
            provider_numeric=provider_numeric,
            provider_numeric_freeze_sha256=freeze,
            regime_roots=regime_roots,
            replay_started_at=replay_started_at,
            max_parallel_groups=parallel,
        )

    def regime_root(self, symbol: str) -> Path:
        return dict(self.regime_roots)[symbol]

    def group_batch(self, group_id: str) -> Path:
        return self.assembly_root / group_id / "seven-trader-cibo-batch.json"

    def lab_script(self) -> Path:
        return self.repository_root / "scripts" / "cibo_t02_three_lane_capital_lab_arch2.py"

    def report_script(self) -> Path:
        return self.repository_root / "scripts" / "cibo_three_holdout_group_report.py"

    def doctor(self) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []

        def add(name: str, ok: bool, path: Path | None = None) -> None:
            checks.append(
                {
                    "name": name,
                    "ok": ok,
                    "path": None if path is None else str(path),
                }
            )

        add("repository_root", self.repository_root.is_dir(), self.repository_root)
        add("workspace_parent", self.workspace.parent.is_dir(), self.workspace.parent)
        add("lab_script", self.lab_script().is_file(), self.lab_script())
        add("report_script", self.report_script().is_file(), self.report_script())
        add("provider_numeric", self.provider_numeric.is_file(), self.provider_numeric)
        for group_id in GROUP_IDS:
            path = self.group_batch(group_id)
            add(f"batch:{group_id}", path.is_file(), path)
        for symbol in REGIME_SYMBOLS:
            root = self.regime_root(symbol)
            manifests = tuple(root.rglob("symbol-consumption-manifest.json"))
            add(f"regime:{symbol}", len(manifests) == 1, root)

        result = {
            "schema": "qore.cibo.trader-lab.realtime-bench-doctor.v1",
            "ready": all(item["ok"] for item in checks),
            "checks": checks,
            "workflow_dependency": False,
            "broker_dependency": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
        }
        return result


@dataclass(frozen=True, slots=True)
class BenchEvent:
    seq: int
    run_id: str
    at: str
    kind: str
    group_id: str | None
    payload: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "run_id": self.run_id,
            "at": self.at,
            "kind": self.kind,
            "group_id": self.group_id,
            "payload": self.payload,
        }


EventSink = Callable[[BenchEvent], None]


class BenchRun:
    """Persistent state for one local bench execution."""

    def __init__(
        self,
        *,
        config: RealtimeBenchConfig,
        run_id: str | None = None,
    ) -> None:
        self.config = config
        self.run_id = run_id or (
            datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            + "-"
            + uuid.uuid4().hex[:8]
        )
        self.root = config.workspace / "runs" / self.run_id
        self.root.mkdir(parents=True, exist_ok=False)
        self.events_path = self.root / "events.jsonl"
        self.status_path = self.root / "status.json"
        self.sensor_path = self.root / "sensor.json"
        self._seq = 0
        self._lock = threading.RLock()
        self._subscribers: list[queue.Queue[BenchEvent]] = []
        self._status = {
            "schema": BENCH_SCHEMA,
            "run_id": self.run_id,
            "status": "CREATED",
            "created_at": _utc_now(),
            "started_at": None,
            "completed_at": None,
            "groups": {
                group_id: {
                    "status": "PENDING",
                    "stage": "PENDING",
                    "result": None,
                    "error": None,
                }
                for group_id in GROUP_IDS
            },
            "sensor": None,
            "workflow_dependency": False,
            "broker_mutation": False,
            "live": False,
            "production": False,
            "real_capital": False,
        }
        self._write_status()

    def _write_status(self) -> None:
        self.status_path.write_text(
            json.dumps(self._status, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(json.dumps(self._status))

    def subscribe(self) -> queue.Queue[BenchEvent]:
        q: queue.Queue[BenchEvent] = queue.Queue()
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue[BenchEvent]) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def emit(
        self,
        kind: str,
        payload: dict[str, Any],
        *,
        group_id: str | None = None,
    ) -> BenchEvent:
        with self._lock:
            self._seq += 1
            event = BenchEvent(
                seq=self._seq,
                run_id=self.run_id,
                at=_utc_now(),
                kind=kind,
                group_id=group_id,
                payload=payload,
            )
            with self.events_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event.as_dict(), sort_keys=True) + "\n")
            for subscriber in tuple(self._subscribers):
                subscriber.put(event)
            return event

    def set_run_status(self, status: str) -> None:
        with self._lock:
            self._status["status"] = status
            if status == "RUNNING" and self._status["started_at"] is None:
                self._status["started_at"] = _utc_now()
            if status in {"COMPLETE", "FAILED"}:
                self._status["completed_at"] = _utc_now()
            self._write_status()

    def set_group(
        self,
        group_id: str,
        *,
        status: str | None = None,
        stage: str | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock:
            row = self._status["groups"][group_id]
            if status is not None:
                row["status"] = status
            if stage is not None:
                row["stage"] = stage
            if result is not None:
                row["result"] = result
            if error is not None:
                row["error"] = error
            self._write_status()

    def set_sensor(self, sensor: dict[str, Any]) -> None:
        with self._lock:
            self._status["sensor"] = sensor
            self._write_status()


class RealtimeBenchRunner:
    """Runs all three integrated 1Y groups concurrently from local evidence."""

    def __init__(
        self,
        *,
        config: RealtimeBenchConfig,
        event_sink: EventSink | None = None,
    ) -> None:
        self.config = config
        self.event_sink = event_sink

    def create_run(self, run_id: str | None = None) -> BenchRun:
        self.config.workspace.mkdir(parents=True, exist_ok=True)
        (self.config.workspace / "runs").mkdir(parents=True, exist_ok=True)
        return BenchRun(config=self.config, run_id=run_id)

    def _emit(
        self,
        run: BenchRun,
        kind: str,
        payload: dict[str, Any],
        *,
        group_id: str | None = None,
    ) -> None:
        event = run.emit(kind, payload, group_id=group_id)
        if self.event_sink is not None:
            self.event_sink(event)

    def _run_command(
        self,
        run: BenchRun,
        *,
        group_id: str,
        stage: str,
        command: list[str],
        cwd: Path,
    ) -> None:
        self._emit(
            run,
            "stage.started",
            {"stage": stage, "command": command},
            group_id=group_id,
        )
        run.set_group(group_id, status="RUNNING", stage=stage)
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        assert process.stdout is not None
        for raw_line in process.stdout:
            line = raw_line.rstrip()
            if not line:
                continue
            payload: dict[str, Any] = {"stage": stage, "line": line}
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                payload["json"] = parsed
            self._emit(run, "stage.output", payload, group_id=group_id)
        return_code = process.wait()
        if return_code != 0:
            raise RealtimeBenchError(
                f"{group_id} stage {stage} failed with exit {return_code}"
            )
        self._emit(
            run,
            "stage.completed",
            {"stage": stage},
            group_id=group_id,
        )

    def _group_commands(
        self,
        *,
        group_id: str,
        group_root: Path,
    ) -> tuple[list[str], list[str]]:
        lab_root = group_root / "lab"
        result_path = group_root / "group-result.json"
        source_args: list[str] = []
        for symbol in REGIME_SYMBOLS:
            source_args.extend(
                [
                    "--source-root",
                    f"{symbol}={self.config.regime_root(symbol)}",
                ]
            )
        lab = [
            sys.executable,
            str(self.config.lab_script()),
            "--batch",
            str(self.config.group_batch(group_id)),
            "--provider-numeric",
            str(self.config.provider_numeric),
            "--provider-numeric-freeze-sha256",
            self.config.provider_numeric_freeze_sha256,
            *source_args,
            "--replay-started-at",
            self.config.replay_started_at,
            "--output-dir",
            str(lab_root),
        ]
        report = [
            sys.executable,
            str(self.config.report_script()),
            "--three-lane",
            str(lab_root / "three-lane-result.json"),
            "--output",
            str(result_path),
        ]
        return lab, report

    def _run_group(self, run: BenchRun, group_id: str) -> dict[str, Any]:
        group_root = run.root / group_id
        group_root.mkdir(parents=True, exist_ok=True)
        self._emit(
            run,
            "group.started",
            {
                "batch": str(self.config.group_batch(group_id)),
                "shared_initial_capital_usd": "60",
                "seven_traders_together": True,
            },
            group_id=group_id,
        )
        started = time.monotonic()
        try:
            lab_command, report_command = self._group_commands(
                group_id=group_id,
                group_root=group_root,
            )
            self._run_command(
                run,
                group_id=group_id,
                stage="CIBO_REPLAY",
                command=lab_command,
                cwd=self.config.repository_root,
            )
            self._run_command(
                run,
                group_id=group_id,
                stage="SCIENTIFIC_REPORT",
                command=report_command,
                cwd=self.config.repository_root,
            )
            result = _json(group_root / "group-result.json")
            elapsed = time.monotonic() - started
            candidate_summaries: dict[str, Any] = {}
            for candidate in result.get("candidates", []):
                if not isinstance(candidate, dict):
                    continue
                fingerprint = str(candidate.get("configuration_fingerprint"))
                measurements = candidate.get("measurements", {})
                if not isinstance(measurements, dict):
                    continue
                per_trader = measurements.get("per_trader_under_cibo", {})
                if not isinstance(per_trader, dict):
                    per_trader = {}
                config = candidate.get("configuration", {})
                if not isinstance(config, dict):
                    config = {}
                candidate_summaries[fingerprint] = {
                    "leverage": config.get("compound_seed_multiplier"),
                    "final_ending_capital_usd": measurements.get(
                        "final_ending_capital_usd"
                    ),
                    "core_net_pnl_usd": (
                        measurements.get("core", {}).get("net_pnl_usd")
                        if isinstance(measurements.get("core"), dict)
                        else None
                    ),
                    "compound_incremental_pnl_usd": (
                        measurements.get("compound", {}).get("incremental_pnl_usd")
                        if isinstance(measurements.get("compound"), dict)
                        else None
                    ),
                    "portfolio_incremental_pnl_usd": (
                        measurements.get("compound_portfolio", {}).get(
                            "incremental_pnl_usd"
                        )
                        if isinstance(measurements.get("compound_portfolio"), dict)
                        else None
                    ),
                    "all_7_positive": all(
                        Decimal(str(row.get("final_pnl_usd", "0"))) > 0
                        for row in per_trader.values()
                        if isinstance(row, dict)
                    )
                    and len(per_trader) == 7,
                    "per_trader": {
                        trader: {
                            "pnl_usd": row.get("final_pnl_usd"),
                            "profit_factor": row.get("profit_factor"),
                            "expectancy_usd": row.get("expectancy_usd"),
                            "settled_count": row.get("settled_count"),
                        }
                        for trader, row in per_trader.items()
                        if isinstance(row, dict)
                    },
                }
            summary = {
                "group_id": group_id,
                "elapsed_seconds": round(elapsed, 3),
                "candidate_count": len(result.get("candidates", [])),
                "candidates": candidate_summaries,
            }
            run.set_group(
                group_id,
                status="COMPLETE",
                stage="COMPLETE",
                result=summary,
            )
            self._emit(
                run,
                "group.completed",
                summary,
                group_id=group_id,
            )
            return result
        except Exception as error:
            run.set_group(
                group_id,
                status="FAILED",
                stage="FAILED",
                error=str(error),
            )
            self._emit(
                run,
                "group.failed",
                {"error": str(error)},
                group_id=group_id,
            )
            raise

    def run(self, run: BenchRun) -> dict[str, Any]:
        doctor = self.config.doctor()
        if not doctor["ready"]:
            raise RealtimeBenchError("bench doctor failed; inspect doctor output")
        run.set_run_status("RUNNING")
        self._emit(run, "run.started", {"doctor": doctor})

        group_results: dict[str, dict[str, Any]] = {}
        try:
            with ThreadPoolExecutor(
                max_workers=self.config.max_parallel_groups,
                thread_name_prefix="cibo-bench",
            ) as pool:
                futures = {
                    pool.submit(self._run_group, run, group_id): group_id
                    for group_id in GROUP_IDS
                }
                for future in as_completed(futures):
                    group_id = futures[future]
                    group_results[group_id] = future.result()

            ordered = tuple(group_results[group_id] for group_id in GROUP_IDS)
            sensor = evaluate_three_groups(ordered)
            run.sensor_path.write_text(
                json.dumps(sensor, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            run.set_sensor(sensor)
            self._emit(run, "sensor.completed", sensor)
            run.set_run_status("COMPLETE")
            self._emit(
                run,
                "run.completed",
                {
                    "status": sensor["status"],
                    "cross_holdout_full_pass_count": sensor[
                        "cross_holdout_full_pass_count"
                    ],
                },
            )
            return sensor
        except Exception as error:
            run.set_run_status("FAILED")
            self._emit(run, "run.failed", {"error": str(error)})
            raise


def list_runs(config: RealtimeBenchConfig) -> list[dict[str, Any]]:
    root = config.workspace / "runs"
    if not root.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for status_path in sorted(root.glob("*/status.json"), reverse=True):
        try:
            rows.append(_json(status_path))
        except (OSError, json.JSONDecodeError, RealtimeBenchError):
            continue
    return rows
