"""Persistent real-time telemetry for the independent GitHub Trader Lab."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class RealtimeMonitor:
    def __init__(self, root: Path, run_id: str, lanes: tuple[str, ...]) -> None:
        self.root = root
        self.run_id = run_id
        self.root.mkdir(parents=True, exist_ok=True)
        self.events_path = root / "events.jsonl"
        self.reports_path = root / "live-reports.jsonl"
        self.status_path = root / "status.json"
        self._seq = 0
        self._lock = threading.RLock()
        self._status: dict[str, Any] = {
            "schema": "qore.github-trader-lab.realtime.v1",
            "run_id": run_id,
            "status": "CREATED",
            "created_at": utc_now(),
            "started_at": None,
            "completed_at": None,
            "lanes": {
                lane: {
                    "status": "PENDING",
                    "stage": "PENDING",
                    "elapsed_seconds": None,
                    "summary": None,
                    "error": None,
                }
                for lane in lanes
            },
            "governance": {
                "independent_trader_lab": True,
                "research_only": True,
                "fresh_holdout_opened": False,
                "certification_claimed": False,
                "broker_mutation": False,
                "live_authorized": False,
                "production_authorized": False,
                "real_capital_authorized": False,
            },
        }
        self._write()

    def _write(self) -> None:
        self.status_path.write_text(
            json.dumps(self._status, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def emit(
        self,
        kind: str,
        payload: dict[str, Any] | None = None,
        *,
        lane: str | None = None,
    ) -> None:
        with self._lock:
            self._seq += 1
            event = {
                "seq": self._seq,
                "run_id": self.run_id,
                "at": utc_now(),
                "kind": kind,
                "lane": lane,
                "payload": payload or {},
            }
            with self.events_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, sort_keys=True) + "\n")
            compact = json.dumps(event, sort_keys=True, separators=(",", ":"))
            print(f"QORE_TRADER_LAB_EVENT {compact}", flush=True)
            if kind.endswith(".completed") or kind.endswith(".failed"):
                title = f"Trader Lab {kind}"
                message = compact.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
                print(f"::notice title={title}::{message}", flush=True)

    def report(
        self,
        report_type: str,
        payload: dict[str, Any],
        *,
        lane: str | None = None,
        variant: str | None = None,
    ) -> None:
        """Publish a compact structured report immediately to disk and stdout."""

        with self._lock:
            row = {
                "run_id": self.run_id,
                "at": utc_now(),
                "report_type": report_type,
                "lane": lane,
                "variant": variant,
                "payload": payload,
            }
            with self.reports_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(row, sort_keys=True, separators=(",", ":"))
                    + "\n"
                )
            compact = json.dumps(
                row,
                sort_keys=True,
                separators=(",", ":"),
            )
            print(f"QORE_TRADER_LAB_REPORT {compact}", flush=True)

    def set_run(self, status: str) -> None:
        with self._lock:
            self._status["status"] = status
            if status == "RUNNING" and self._status["started_at"] is None:
                self._status["started_at"] = utc_now()
            if status in {"COMPLETE", "FAILED"}:
                self._status["completed_at"] = utc_now()
            self._write()

    def set_lane(
        self,
        lane: str,
        *,
        status: str | None = None,
        stage: str | None = None,
        elapsed_seconds: float | None = None,
        summary: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock:
            row = self._status["lanes"][lane]
            if status is not None:
                row["status"] = status
            if stage is not None:
                row["stage"] = stage
            if elapsed_seconds is not None:
                row["elapsed_seconds"] = round(elapsed_seconds, 3)
            if summary is not None:
                row["summary"] = summary
            if error is not None:
                row["error"] = error
            self._write()
