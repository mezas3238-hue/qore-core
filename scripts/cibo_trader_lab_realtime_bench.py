#!/usr/bin/env python3
"""CLI and local dashboard for the standalone CIBO Trader Lab test bench."""

from __future__ import annotations

import argparse
import json
import queue
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from qore.infrastructure.trader_lab.cibo_realtime_bench import (
    BenchEvent,
    BenchRun,
    RealtimeBenchConfig,
    RealtimeBenchError,
    RealtimeBenchRunner,
    list_runs,
)


DASHBOARD = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>QORE CIBO Trader Lab Bench</title>
<style>
:root{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color-scheme:dark}
body{max-width:1200px;margin:24px auto;padding:0 16px;background:#0b0d10;color:#e8edf2}
button{padding:10px 14px;border:1px solid #525b66;background:#151a20;color:#fff;border-radius:8px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:16px 0}
.card{border:1px solid #303741;border-radius:10px;padding:14px;background:#11151a}
pre{white-space:pre-wrap;word-break:break-word;background:#080a0d;padding:12px;border-radius:8px;max-height:420px;overflow:auto}
.ok{color:#83e38c}.bad{color:#ff8585}.run{color:#ffd166}
@media(max-width:800px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<h1>CIBO Trader Lab · Real-Time Bench</h1>
<p>Three integrated 1Y groups · seven frozen Traders together · shared CIBO/QORE per group.</p>
<button id="start">Start 3×1Y run</button>
<span id="state"></span>
<div class="grid" id="groups"></div>
<h2>Sensor</h2><pre id="sensor">{}</pre>
<h2>Live events</h2><pre id="events"></pre>
<script>
let source=null;
function card(id){
  return '<div class="card"><h3>'+id+'</h3><div id="'+id+'">PENDING</div></div>';
}
document.getElementById('groups').innerHTML=['GROUP_1','GROUP_2','GROUP_3'].map(card).join('');
function showStatus(s){
  document.getElementById('state').textContent=' '+s.status+' · '+s.run_id;
  for(const [id,row] of Object.entries(s.groups||{})){
    const target=document.getElementById(id);
    let text=row.status+' / '+row.stage;
    if(row.result){
      text+='\n'+JSON.stringify(row.result,null,2);
    }
    if(row.error){
      text+='\nERROR: '+row.error;
    }
    target.textContent=text;
  }
  document.getElementById('sensor').textContent=JSON.stringify(s.sensor||{},null,2);
}
async function refresh(){
  const r=await fetch('/api/runs');
  const rows=await r.json();
  if(rows.length) showStatus(rows[0]);
}
function watch(runId){
  if(source) source.close();
  source=new EventSource('/api/runs/'+runId+'/events');
  source.onmessage=(e)=>{
    const row=JSON.parse(e.data);
    const log=document.getElementById('events');
    log.textContent+=JSON.stringify(row)+'\n';
    log.scrollTop=log.scrollHeight;
    fetch('/api/runs/'+runId).then(r=>r.json()).then(showStatus);
  };
}
document.getElementById('start').onclick=async()=>{
  const r=await fetch('/api/runs',{method:'POST'});
  const body=await r.json();
  if(!r.ok){alert(JSON.stringify(body));return;}
  showStatus(body);
  watch(body.run_id);
};
refresh();
setInterval(refresh,2000);
</script>
</body>
</html>
"""


class BenchRegistry:
    def __init__(self, config: RealtimeBenchConfig) -> None:
        self.config = config
        self.runner = RealtimeBenchRunner(config=config)
        self._lock = threading.RLock()
        self._active: dict[str, BenchRun] = {}

    def start(self) -> BenchRun:
        with self._lock:
            for run in self._active.values():
                if run.snapshot()["status"] in {"CREATED", "RUNNING"}:
                    raise RealtimeBenchError(
                        "one bench run is already active; each run already "
                        "executes GROUP_1/GROUP_2/GROUP_3 concurrently"
                    )
            run = self.runner.create_run()
            self._active[run.run_id] = run
            thread = threading.Thread(
                target=self._execute,
                args=(run,),
                daemon=True,
                name=f"cibo-bench-{run.run_id}",
            )
            thread.start()
            return run

    def _execute(self, run: BenchRun) -> None:
        try:
            self.runner.run(run)
        except Exception:
            return

    def active(self, run_id: str) -> BenchRun | None:
        with self._lock:
            return self._active.get(run_id)

    def snapshot(self, run_id: str) -> dict[str, Any] | None:
        active = self.active(run_id)
        if active is not None:
            return active.snapshot()
        path = self.config.workspace / "runs" / run_id / "status.json"
        if not path.is_file():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None


def _historical_events(config: RealtimeBenchConfig, run_id: str) -> list[dict[str, Any]]:
    path = config.workspace / "runs" / run_id / "events.jsonl"
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        raw = json.loads(line)
        if isinstance(raw, dict):
            rows.append(raw)
    return rows


def make_handler(registry: BenchRegistry) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "QORECIBOBench/1"

        def log_message(self, format: str, *args: object) -> None:
            return

        def _json(self, status: int, body: object) -> None:
            raw = json.dumps(body, sort_keys=True).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/":
                raw = DASHBOARD.encode()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return
            if path == "/api/health":
                self._json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "doctor": registry.config.doctor(),
                        "workflow_dependency": False,
                    },
                )
                return
            if path == "/api/runs":
                self._json(HTTPStatus.OK, list_runs(registry.config))
                return
            parts = [part for part in path.split("/") if part]
            if len(parts) >= 3 and parts[:2] == ["api", "runs"]:
                run_id = parts[2]
                if len(parts) == 3:
                    snapshot = registry.snapshot(run_id)
                    if snapshot is None:
                        self._json(HTTPStatus.NOT_FOUND, {"error": "run not found"})
                    else:
                        self._json(HTTPStatus.OK, snapshot)
                    return
                if len(parts) == 4 and parts[3] == "events":
                    self._events(run_id)
                    return
                if len(parts) == 4 and parts[3] == "sensor":
                    sensor = registry.config.workspace / "runs" / run_id / "sensor.json"
                    if not sensor.is_file():
                        self._json(
                            HTTPStatus.NOT_FOUND,
                            {"error": "sensor not available yet"},
                        )
                    else:
                        self._json(
                            HTTPStatus.OK,
                            json.loads(sensor.read_text(encoding="utf-8")),
                        )
                    return
                if (
                    len(parts) == 5
                    and parts[3] == "groups"
                    and parts[4] in {"GROUP_1", "GROUP_2", "GROUP_3"}
                ):
                    result = (
                        registry.config.workspace
                        / "runs"
                        / run_id
                        / parts[4]
                        / "group-result.json"
                    )
                    if not result.is_file():
                        self._json(
                            HTTPStatus.NOT_FOUND,
                            {"error": "group result not available yet"},
                        )
                    else:
                        self._json(
                            HTTPStatus.OK,
                            json.loads(result.read_text(encoding="utf-8")),
                        )
                    return
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def _events(self, run_id: str) -> None:
            snapshot = registry.snapshot(run_id)
            if snapshot is None:
                self._json(HTTPStatus.NOT_FOUND, {"error": "run not found"})
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            seen = 0
            for event in _historical_events(registry.config, run_id):
                seen = max(seen, int(event.get("seq", 0)))
                raw = json.dumps(event, sort_keys=True)
                self.wfile.write(f"data: {raw}\n\n".encode())
            self.wfile.flush()

            active = registry.active(run_id)
            if active is None or snapshot["status"] in {"COMPLETE", "FAILED"}:
                return
            subscriber = active.subscribe()
            try:
                while True:
                    try:
                        event = subscriber.get(timeout=15)
                    except queue.Empty:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                        current = active.snapshot()["status"]
                        if current in {"COMPLETE", "FAILED"}:
                            return
                        continue
                    if event.seq <= seen:
                        continue
                    seen = event.seq
                    raw = json.dumps(event.as_dict(), sort_keys=True)
                    self.wfile.write(f"data: {raw}\n\n".encode())
                    self.wfile.flush()
                    if event.kind in {"run.completed", "run.failed"}:
                        return
            except (BrokenPipeError, ConnectionResetError):
                return
            finally:
                active.unsubscribe(subscriber)

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/api/runs":
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            try:
                run = registry.start()
            except RealtimeBenchError as error:
                self._json(HTTPStatus.CONFLICT, {"error": str(error)})
                return
            self._json(HTTPStatus.ACCEPTED, run.snapshot())

    return Handler


def _print_event(event: BenchEvent) -> None:
    print(json.dumps(event.as_dict(), sort_keys=True), flush=True)


def command_doctor(config: RealtimeBenchConfig) -> int:
    result = config.doctor()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ready"] else 2


def command_run(config: RealtimeBenchConfig, run_id: str | None) -> int:
    runner = RealtimeBenchRunner(config=config, event_sink=_print_event)
    run = runner.create_run(run_id=run_id)
    try:
        sensor = runner.run(run)
    except Exception as error:
        print(json.dumps({"status": "FAILED", "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps({"run_id": run.run_id, "sensor": sensor}, sort_keys=True))
    return 0


def command_serve(config: RealtimeBenchConfig, host: str, port: int) -> int:
    doctor = config.doctor()
    if not doctor["ready"]:
        print(json.dumps(doctor, indent=2, sort_keys=True))
        return 2
    registry = BenchRegistry(config)
    server = ThreadingHTTPServer((host, port), make_handler(registry))
    print(
        json.dumps(
            {
                "status": "SERVING",
                "address": f"http://{host}:{port}",
                "workflow_dependency": False,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Standalone bench JSON config with local evidence paths.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor")

    run_parser = sub.add_parser("run")
    run_parser.add_argument("--run-id")

    serve_parser = sub.add_parser("serve")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)

    args = parser.parse_args()
    config = RealtimeBenchConfig.load(args.config)

    if args.command == "doctor":
        return command_doctor(config)
    if args.command == "run":
        return command_run(config, args.run_id)
    if args.command == "serve":
        return command_serve(config, args.host, args.port)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
