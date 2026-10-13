"""Synthetic offline contracts; never use fake examples as economic evidence."""
from __future__ import annotations

import csv
import json
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

import pytest

from qore.infrastructure.research_accelerator.core import (
    DatasetManifest,
    Quote,
    ResearchDataError,
    assert_same_venue,
    ingest,
    load_bars,
    load_quotes,
    verify_lake,
)
from qore.infrastructure.research_accelerator.execution import LimitOrder, simulate_ticks
from qore.infrastructure.research_accelerator.experiments import (
    ExperimentSpec,
    day_block_interval,
    read_signals,
    screen,
)
from qore.infrastructure.research_accelerator.memory import read_ledger, register
from qore.infrastructure.research_accelerator.ultrafast import main

BASE = datetime(2024, 1, 2, 13, 0, tzinfo=UTC)


def fixture_feed(folder: Path, *, kind: str = "m1_bid") -> tuple[Path, Path]:
    folder.mkdir(parents=True, exist_ok=True)
    csvfile = folder / ("bars.csv" if kind == "m1_bid" else "quotes.csv")
    with csvfile.open("w", newline="", encoding="utf-8") as out:
        writer = csv.writer(out, lineterminator="\n")
        if kind == "m1_bid":
            writer.writerow(("closed_at", "open", "high", "low", "close"))
            for i in range(120):
                price = Decimal("100") + Decimal(i) / 10
                writer.writerow((
                    (BASE + timedelta(minutes=i)).isoformat(),
                    str(price), str(price + 1), str(price - 1), str(price),
                ))
        else:
            writer.writerow(("at", "bid", "ask"))
            for i in range(120):
                price = Decimal("100") + Decimal(i) / 10
                writer.writerow((
                    (BASE + timedelta(minutes=i)).isoformat(),
                    str(price), str(price + Decimal(".2")),
                ))
    manifest = {
        "kind": kind, "sha256": sha256(csvfile.read_bytes()).hexdigest(),
        "broker": "IC Markets DEMO", "provider": "cTrader Open API",
        "instrument": "USTEC", "symbol_id": "10014", "feed_version": "test",
        "timezone": "UTC", "timeframe": "M1" if kind == "m1_bid" else "TICK",
        "provenance": "SYNTHETIC_TEST_ONLY", "license": "synthetic",
    }
    manifestfile = folder / "manifest.json"
    manifestfile.write_text(json.dumps(manifest), encoding="utf-8")
    return csvfile, manifestfile


def fixture_spec(folder: Path) -> tuple[Path, Path]:
    spec = folder / "spec.json"
    spec.write_text(json.dumps({
        "name": "sample_precommitted", "horizons_minutes": [5, 15, 30, 60],
        "feature_min": {"ob": 0.5}, "controls": ["local_extreme"],
        "block_bootstrap_draws": 100, "seed": 42,
    }), encoding="utf-8")
    signals = folder / "signals.csv"
    with signals.open("w", newline="", encoding="utf-8") as out:
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(("event_id", "anchor_at", "available_at", "side", "anchor_price", "ob"))
        writer.writerow(("e1", (BASE + timedelta(minutes=40)).isoformat(),
                         (BASE + timedelta(minutes=40)).isoformat(), "long", "104", ".8"))
        writer.writerow(("e2", (BASE + timedelta(minutes=41)).isoformat(),
                         (BASE + timedelta(minutes=41)).isoformat(), "short", "104.1", ".2"))
    return spec, signals


def test_data_lake_hash_and_tamper(tmp_path: Path) -> None:
    data, manifest_path = fixture_feed(tmp_path / "source")
    manifest = DatasetManifest.read(manifest_path)
    assert len(load_bars(data, manifest)) == 120
    first = ingest(data, manifest_path, tmp_path / "lake")
    assert first["row_count"] == "120"
    assert verify_lake(tmp_path / "lake") == 1
    assert ingest(data, manifest_path, tmp_path / "lake") == first
    (tmp_path / "lake" / (manifest.sha256 + ".csv")).write_text("modified")
    with pytest.raises(ResearchDataError, match="SHA256"):
        verify_lake(tmp_path / "lake")
    data.write_text("modified")
    with pytest.raises(ResearchDataError, match="SHA256"):
        load_bars(data, manifest)


def test_quote_integrity_and_venue(tmp_path: Path) -> None:
    bar_data, bar_manifest_path = fixture_feed(tmp_path / "bars")
    quote_data, quote_manifest_path = fixture_feed(tmp_path / "ticks", kind="tick_bidask")
    assert len(load_bars(bar_data, DatasetManifest.read(bar_manifest_path))) == 120
    bars = DatasetManifest.read(bar_manifest_path)
    quotes = DatasetManifest.read(quote_manifest_path)
    assert_same_venue(bars, quotes)
    assert len(load_quotes(quote_data, quotes)) == 120
    payload = json.loads(quote_manifest_path.read_text())
    payload["symbol_id"] = "DIFFERENT"
    quote_manifest_path.write_text(json.dumps(payload))
    with pytest.raises(ResearchDataError, match="unhomologated"):
        assert_same_venue(bars, DatasetManifest.read(quote_manifest_path))


def test_future_signal_rejected_and_anchor_exact(tmp_path: Path) -> None:
    data, manifest_path = fixture_feed(tmp_path)
    spec_file, signals = fixture_spec(tmp_path)
    lines = signals.read_text().splitlines()
    bad = lines[1].replace(
        (BASE + timedelta(minutes=40)).isoformat(),
        (BASE + timedelta(minutes=42)).isoformat(),
        1,
    )
    # Replacing the first occurrence changes anchor, leaving mismatched close.
    signals.write_text("\n".join((lines[0], bad, lines[2])) + "\n")
    parsed = read_signals(signals)
    with pytest.raises(ResearchDataError, match="anchor"):
        screen(
            ExperimentSpec.read(spec_file),
            load_bars(data, DatasetManifest.read(manifest_path)), parsed,
        )
    lines[1] = lines[1].replace(
        (BASE + timedelta(minutes=40)).isoformat(),
        (BASE + timedelta(minutes=45)).isoformat(),
    )
    signals.write_text("\n".join(lines) + "\n")
    # After replacing BOTH occurrences, anchor no longer matches 104.
    with pytest.raises(ResearchDataError):
        screen(ExperimentSpec.read(spec_file),
               load_bars(data, DatasetManifest.read(manifest_path)), read_signals(signals))


def test_indexed_screen_control_and_regime(tmp_path: Path) -> None:
    data, manifest_path = fixture_feed(tmp_path)
    spec_file, signals_file = fixture_spec(tmp_path)
    result = screen(
        ExperimentSpec.read(spec_file),
        load_bars(data, DatasetManifest.read(manifest_path)),
        read_signals(signals_file),
    )
    assert result["signals_selected"] == 1
    horizons = result["horizons"]
    assert isinstance(horizons, dict)
    horizon_15 = horizons["15"]
    assert isinstance(horizon_15, dict)
    assert horizon_15["n"] == 1
    assert horizon_15["mean_bps"] > 0
    controls = result["controls"]
    assert isinstance(controls, dict)
    assert "local_extreme" in controls
    assert isinstance(result["regime_diagnostics"], dict)
    paired = [(BASE, 2.), (BASE + timedelta(days=1), 5.)]
    assert day_block_interval(paired, draws=100, seed=42) == day_block_interval(
        paired, draws=100, seed=42,
    )


def test_memory_duplicate_chain_and_corruption(tmp_path: Path) -> None:
    ledger = tmp_path / "events.jsonl"
    item: dict[str, object] = {
        "config_sha256": "a" * 64,
        "artifact_sha256": "b" * 64,
    }
    one = register(ledger, item)
    assert len(read_ledger(ledger)) == 1
    assert len(str(one["chain_sha256"])) == 64
    with pytest.raises(ResearchDataError, match="equivalent"):
        register(ledger, item)
    ledger.write_bytes(ledger.read_bytes().replace(b"a" * 64, b"c" * 64))
    with pytest.raises(ResearchDataError):
        read_ledger(ledger)


def test_limit_execution_uses_ask_and_bid(tmp_path: Path) -> None:
    times = [BASE + timedelta(minutes=i) for i in range(4)]
    ticks = (
        Quote(times[0], Decimal("101"), Decimal("101.2")),
        Quote(times[1], Decimal("99.7"), Decimal("99.9")),
        Quote(times[2], Decimal("101.2"), Decimal("101.4")),
        Quote(times[3], Decimal("101.5"), Decimal("101.7")),
    )
    order = LimitOrder("a", times[0], times[3], times[3], "long",
                       Decimal("100"), Decimal("99"), Decimal("101"))
    report = simulate_ticks(ticks, (order,), tick_size=Decimal(".1"))
    assert report[0]["status"] == "CLOSED_OBSERVED_TICKS"
    assert report[0]["fill_price"] == "99.9"
    assert report[0]["exit_reason"] == "TARGET"
    assert Decimal(report[0]["gross_price_points_per_unit"]) == Decimal("1.1")
    unfilled = LimitOrder("b", times[0], times[1], times[3], "long",
                          Decimal("98"), Decimal("97"), Decimal("102"))
    result = simulate_ticks(ticks, (unfilled,), tick_size=Decimal(".1"))
    assert result[0]["status"] == "UNFILLED_OBSERVED_ONLY"


def test_ultrafast_cli_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data, manifest_path = fixture_feed(tmp_path)
    spec, signals = fixture_spec(tmp_path)
    output, registry = tmp_path / "out.json", tmp_path / "memory.jsonl"
    cmd = [
        "program", "screen", "--bars", str(data), "--manifest", str(manifest_path),
        "--signals", str(signals), "--spec", str(spec),
        "--out", str(output), "--registry", str(registry), "--code-sha", "a" * 40,
    ]
    monkeypatch.setattr(sys, "argv", cmd)
    assert main() == 0
    assert output.exists()
    assert output.with_name(output.name + ".sha256").exists()
    assert len(read_ledger(registry)) == 1
    with pytest.raises(ResearchDataError, match="equivalent"):
        main()


def test_limit_stop_immediately_on_entry_quote() -> None:
    first = BASE
    ticks = (
        Quote(first, Decimal("98"), Decimal("99.9")),
        Quote(first + timedelta(minutes=1), Decimal("100"), Decimal("100.2")),
    )
    order = LimitOrder(
        "immediate", first, first + timedelta(minutes=1),
        first + timedelta(minutes=1), "long",
        Decimal("100"), Decimal("99"), Decimal("102"),
    )
    ledger = simulate_ticks(ticks, (order,), tick_size=Decimal(".1"))
    assert ledger[0]["status"] == "CLOSED_OBSERVED_TICKS"
    assert ledger[0]["exit_reason"] == "STOP"
    assert ledger[0]["duration_seconds"] == "0"
