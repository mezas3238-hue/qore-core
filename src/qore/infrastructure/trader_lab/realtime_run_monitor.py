"""Generic persistent real-time telemetry for QORE research runners.

Ported from the event/status model used by the standalone CIBO Trader Lab
real-time bench.  This module is intentionally domain-neutral: research
workflows can emit structured progress into GitHub Actions logs while also
persisting machine-readable events.jsonl and status.json artifacts.
"""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


EventSink = Callable[[dict[str, Any]], None]


class RealtimeRunMonitor:
    """Thread-safe event stream and status snapshot for one research run."""

    def __init__(
        self,
        *,
        root: Path,
        run_id: str,
        lanes: tuple[str, ...],
        event_sink: EventSink | None = None,
    ) -> None:
        self.root = root
        self.run_id = run_id
        self.event_sink = event_sink
        self.root.mkdir(parents=True, exist_ok=True)
        self.events_path = self.root / "events.jsonl"
        self.status_path = self.root / "status.json"
        self._lock = threading.RLock()
        self._seq = 0
        self._status: dict[str, Any] = {
            "schema": "qore.trader-lab.realtime-monitor.v1",
            "run_id": run_id,
            "status": "CREATED",
            "created_at": _utc_now(),
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
                "research_only": True,
                "certification_claimed": False,
                "fresh_holdout_opened": False,
                "broker_mutation": False,
                "live_authorized": False,
                "production_authorized": False,
                "real_capital_authorized": False,
            },
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

    def emit(
        self,
        kind: str,
        payload: dict[str, Any] | None = None,
        *,
        lane: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            self._seq += 1
            event = {
                "seq": self._seq,
                "run_id": self.run_id,
                "at": _utc_now(),
                "kind": kind,
                "lane": lane,
                "payload": payload or {},
            }
            with self.events_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, sort_keys=True) + "\n")
            if self.event_sink is not None:
                self.event_sink(event)
            return event

    def set_run_status(self, status: str) -> None:
        with self._lock:
            self._status["status"] = status
            if status == "RUNNING" and self._status["started_at"] is None:
                self._status["started_at"] = _utc_now()
            if status in {"COMPLETE", "FAILED"}:
                self._status["completed_at"] = _utc_now()
            self._write_status()

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
            self._write_status()


def github_log_sink(event: dict[str, Any]) -> None:
    """Emit one compact JSON line; GitHub Actions streams it live."""
    print(
        "QORE_REALTIME_EVENT "
        + json.dumps(event, sort_keys=True, separators=(",", ":")),
        flush=True,
    )
