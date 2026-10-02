"""Source adapter for the sealed Phase22 V3 NAS100 M1 corpus."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.cibo_phase22_next_exam_governance import NEXT_CANDIDATE_ID
from qore.infrastructure.cibo_phase22_v3_source_receipt import (
    PHASE22_V3_SOURCE_RECEIPT,
)
from qore.infrastructure.market_data import Instrument, OhlcSnapshot
from qore.infrastructure.trader_lab.cibo_market_atlas_journey_extractor_v1 import (
    PRICE_SCALE,
)
from qore.infrastructure.trader_lab.vt31_silver_bullet_v2_backtest import _snapshot

SOURCE_IDENTITY = "CIBO_PHASE22_NEXT_EXAM_NAS100_M1_SOURCE_V1"
SOURCE_SCHEMA = "qore.cibo.phase22.next-exam-nas100-m1-source.v1"
RAW_SOURCE_SHA256 = (
    "9dad424b473b0694d630f94fd5b598d60c26604efad4d0f85262d38ea1c21201"
)


@dataclass(frozen=True, slots=True)
class Phase22V3Vt31M1Source:
    series: tuple[OhlcSnapshot, ...]
    provider_symbol: str
    raw_sha256: str
    collector_git_sha: str
    first_observed_at: datetime
    last_closed_at: datetime

    @property
    def fingerprint(self) -> str:
        payload = {
            "candidate_id": NEXT_CANDIDATE_ID,
            "provider_symbol": self.provider_symbol,
            "raw_sha256": self.raw_sha256,
            "collector_git_sha": self.collector_git_sha,
            "bars": len(self.series),
            "first_observed_at": self.first_observed_at.isoformat(),
            "last_closed_at": self.last_closed_at.isoformat(),
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()


def _binding():
    rows = tuple(
        item
        for item in PHASE22_V3_SOURCE_RECEIPT.bindings
        if item.symbol == "NAS100" and item.timeframe == "M1"
    )
    if len(rows) != 1:
        raise ValueError("V3 VT31 exact M1 binding missing")
    return rows[0]


def _price(relative: int, digits: int) -> str:
    if relative <= 0 or digits <= 0:
        raise ValueError("V3 VT31 relative price/digits invalid")
    value = (Decimal(relative) / PRICE_SCALE).quantize(
        Decimal(1).scaleb(-digits)
    )
    return format(value, "f")


def load_phase22_v3_vt31_m1(root: Path) -> Phase22V3Vt31M1Source:
    binding = _binding()
    manifest_path = root / "phase22-v3-nas100-m1-manifest.json"
    ledger_path = root / "RAW_M1_LEDGER" / "holdout-v3.jsonl"
    if not manifest_path.is_file() or not ledger_path.is_file():
        raise ValueError("V3 VT31 M1 source artifact incomplete")

    manifest_bytes = manifest_path.read_bytes()
    manifest_sha = "sha256:" + hashlib.sha256(manifest_bytes).hexdigest()
    if manifest_sha != binding.manifest_sha256:
        raise ValueError("V3 VT31 manifest SHA drift")
    manifest = json.loads(manifest_bytes)
    if (
        manifest.get("candidate_id") != NEXT_CANDIDATE_ID
        or manifest.get("identity") != SOURCE_IDENTITY
        or manifest.get("schema") != SOURCE_SCHEMA
        or manifest.get("canonical_symbol") != "NAS100"
        or manifest.get("provider_symbol") != "USTEC"
        or manifest.get("raw_sha256") != RAW_SOURCE_SHA256
        or int(manifest.get("retained_bars", 0)) != binding.retained_bars
        or manifest.get("first_observed_m1") != binding.first_observed_at
        or manifest.get("last_observed_m1") != binding.last_observed_at
        or manifest.get("trader_logic_executed") is not False
        or manifest.get("outcomes_inspected") is not False
        or manifest.get("broker_mutation") is not False
        or manifest.get("productive_authority") is not False
    ):
        raise ValueError("V3 VT31 M1 source manifest drift")

    raw_bytes = ledger_path.read_bytes()
    observed_sha = hashlib.sha256(raw_bytes).hexdigest()
    if observed_sha != RAW_SOURCE_SHA256:
        raise ValueError("V3 VT31 M1 raw SHA drift")

    instrument = Instrument("NAS100")
    snapshots: list[OhlcSnapshot] = []
    prior_opened: datetime | None = None
    for raw in raw_bytes.decode("utf-8").splitlines():
        if not raw.strip():
            continue
        item = json.loads(raw)
        if (
            item.get("canonical_symbol") != "NAS100"
            or item.get("provider_symbol") != "USTEC"
        ):
            raise ValueError("V3 VT31 row identity drift")
        opened = datetime.fromisoformat(str(item["opened_at"])).astimezone(UTC)
        if (
            opened.second != 0
            or opened.microsecond != 0
            or (prior_opened is not None and opened <= prior_opened)
        ):
            raise ValueError("V3 VT31 chronology drift")
        prior_opened = opened
        digits = int(item["digits"])
        row = {
            "opened_at": opened.isoformat(),
            "closed_at": (opened + timedelta(minutes=1)).isoformat(),
            "open": _price(int(item["open_relative"]), digits),
            "high": _price(int(item["high_relative"]), digits),
            "low": _price(int(item["low_relative"]), digits),
            "close": _price(int(item["close_relative"]), digits),
        }
        snapshots.append(_snapshot(row, instrument=instrument))

    series = tuple(snapshots)
    if len(series) != binding.retained_bars or len(series) != 168204:
        raise ValueError("V3 VT31 retained bar count drift")
    if not series:
        raise ValueError("V3 VT31 source is empty")
    first = series[0].opened_at.astimezone(UTC)
    last_closed = series[-1].closed_at.astimezone(UTC)
    if first.isoformat() != binding.first_observed_at:
        raise ValueError("V3 VT31 first bar drift")
    if last_closed.isoformat() != "2015-10-19T00:00:00+00:00":
        raise ValueError("V3 VT31 terminal bar drift")
    return Phase22V3Vt31M1Source(
        series=series,
        provider_symbol="USTEC",
        raw_sha256=observed_sha,
        collector_git_sha=binding.collector_git_sha,
        first_observed_at=first,
        last_closed_at=last_closed,
    )
