from __future__ import annotations

import json
from pathlib import Path

from qore.infrastructure.trader_lab.cibo_realtime_bench import (
    BenchRun,
    RealtimeBenchConfig,
    RealtimeBenchRunner,
)


def _write(path: Path, text: str = "{}\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _config(tmp_path: Path) -> RealtimeBenchConfig:
    repo = tmp_path / "repo"
    scripts = repo / "scripts"
    scripts.mkdir(parents=True)
    _write(scripts / "cibo_t02_three_lane_capital_lab_arch2.py", "pass\n")
    _write(scripts / "cibo_three_holdout_group_report.py", "pass\n")

    assembly = tmp_path / "assembly"
    for group in ("GROUP_1", "GROUP_2", "GROUP_3"):
        _write(assembly / group / "seven-trader-cibo-batch.json")

    provider = tmp_path / "provider" / "provider.json"
    _write(provider)

    regime: dict[str, str] = {}
    for symbol in ("AUDJPY", "EURUSD", "GBPJPY", "GBPUSD", "XAUUSD"):
        root = tmp_path / "regime" / symbol
        _write(root / "symbol-consumption-manifest.json")
        regime[symbol] = str(root)

    raw = {
        "schema": "qore.cibo.trader-lab.realtime-bench-config.v1",
        "repository_root": str(repo),
        "workspace": str(tmp_path / "workspace"),
        "assembly_root": str(assembly),
        "provider_numeric": str(provider),
        "provider_numeric_freeze_sha256": "sha256:" + "a" * 64,
        "regime_roots": regime,
        "replay_started_at": "2026-10-03T18:15:00+00:00",
        "max_parallel_groups": 3,
    }
    config_path = tmp_path / "bench.json"
    config_path.write_text(json.dumps(raw), encoding="utf-8")
    return RealtimeBenchConfig.load(config_path)


def test_doctor_accepts_complete_local_evidence_surface(tmp_path: Path) -> None:
    config = _config(tmp_path)
    doctor = config.doctor()
    assert doctor["ready"] is True
    assert doctor["workflow_dependency"] is False
    assert doctor["broker_dependency"] is False
    assert doctor["live_authorized"] is False
    assert doctor["real_capital_authorized"] is False


def test_bench_run_persists_events_and_status(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config.workspace.mkdir(parents=True)
    (config.workspace / "runs").mkdir()

    run = BenchRun(config=config, run_id="test-run")
    event = run.emit("unit.event", {"value": 7}, group_id="GROUP_1")
    run.set_run_status("RUNNING")
    run.set_group(
        "GROUP_1",
        status="RUNNING",
        stage="CIBO_REPLAY",
    )

    persisted = json.loads(run.status_path.read_text(encoding="utf-8"))
    lines = run.events_path.read_text(encoding="utf-8").splitlines()
    stored_event = json.loads(lines[0])

    assert event.seq == 1
    assert stored_event["kind"] == "unit.event"
    assert stored_event["group_id"] == "GROUP_1"
    assert persisted["status"] == "RUNNING"
    assert persisted["groups"]["GROUP_1"]["stage"] == "CIBO_REPLAY"
    assert persisted["workflow_dependency"] is False
    assert persisted["broker_mutation"] is False


def test_group_commands_are_local_and_workflow_independent(tmp_path: Path) -> None:
    config = _config(tmp_path)
    runner = RealtimeBenchRunner(config=config)
    group_root = tmp_path / "run" / "GROUP_1"
    lab, report = runner._group_commands(  # noqa: SLF001
        group_id="GROUP_1",
        group_root=group_root,
    )
    joined = " ".join((*lab, *report)).lower()

    assert "github" not in joined
    assert "gh " not in joined
    assert "actions" not in joined
    assert "ctrader" not in joined
    assert "broker" not in joined
    assert str(config.group_batch("GROUP_1")) in lab
    assert "--source-root" in lab
    assert str(group_root / "group-result.json") in report


def test_config_requires_exact_three_way_parallelism_range(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert config.max_parallel_groups == 3
