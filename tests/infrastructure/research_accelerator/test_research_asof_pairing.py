"""As-of tick-state pairing never mistakes side-only streams for simultaneous ticks."""
from __future__ import annotations

import csv
import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import pytest

from qore.infrastructure.research_accelerator.asof import (
    SideInput,
    asof_pair,
    load_side,
    pair_files,
)
from qore.infrastructure.research_accelerator.core import (
    DatasetManifest,
    ResearchDataError,
    load_quotes,
)


def _stream(tmp_path: Path, side: str, offset_ms: int) -> tuple[Path, Path]:
    folder = tmp_path / side
    folder.mkdir()
    data = folder / "ticks.csv"
    origin = datetime(2024, 1, 2, tzinfo=UTC)
    with data.open("w", newline="", encoding="utf-8") as out:
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(("at", "price"))
        for i in range(3):
            t = origin + timedelta(seconds=i, milliseconds=offset_ms)
            writer.writerow((t.isoformat(), "100" if side == "bid" else "100.5"))
    manifest = folder / "manifest.json"
    manifest.write_text(json.dumps({
        "side": side, "sha256": sha256(data.read_bytes()).hexdigest(),
        "broker": "IC Markets DEMO", "provider": "cTrader Open API",
        "instrument": "USTEC", "symbol_id": "10014",
        "feed_version": "synthetic", "license": "test",
        "provenance": "synthetic_test_no_live",
    }))
    return data, manifest


def test_asof_receipt_and_homologation(tmp_path: Path) -> None:
    bid, bmeta = _stream(tmp_path, "bid", 0)
    ask, ameta = _stream(tmp_path, "ask", 100)
    out, meta, receipt_file = (tmp_path / "pair.csv", tmp_path / "paired.json",
                               tmp_path / "receipt.json")
    receipt = pair_files(
        bid, bmeta, ask, ameta, max_staleness_ms=200,
        output_csv=out, output_manifest=meta, receipt_file=receipt_file,
    )
    assert receipt["observed_state_count"] == 3
    quarantined = receipt["quarantined"]
    assert isinstance(quarantined, dict)
    assert quarantined["stale"] == 2
    assert len(load_quotes(out, DatasetManifest.read(meta))) == 3
    with pytest.raises(FileExistsError):
        pair_files(
            bid, bmeta, ask, ameta, max_staleness_ms=200,
            output_csv=out, output_manifest=meta, receipt_file=receipt_file,
        )


def test_asof_staleness_and_missing_source(tmp_path: Path) -> None:
    bid, bmeta = _stream(tmp_path, "bid", 0)
    ask, ameta = _stream(tmp_path, "ask", 100)
    b = load_side(bid, SideInput.read(bmeta))
    a = load_side(ask, SideInput.read(ameta))
    paired, _ = asof_pair(b, a, max_staleness_ms=200)
    assert len(paired) == 3
    with pytest.raises(ResearchDataError, match="no valid"):
        asof_pair(b, a, max_staleness_ms=1)
    ask.write_text("corrupted")
    with pytest.raises(ResearchDataError, match="checksum"):
        load_side(ask, SideInput.read(ameta))
