"""Source adapter for the sealed Phase22 V4 NAS100 M1 corpus."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.cibo_phase22_v4_governance import (
    PHASE22_V4_CANDIDATE,
    V4_CANDIDATE_ID,
)
from qore.infrastructure.cibo_phase22_v4_source_receipt import (
    Phase22V4SourceBinding,
    Phase22V4SourceReceipt,
    load_phase22_v4_source_receipt,
)
from qore.infrastructure.market_data import Instrument, OhlcSnapshot
from qore.infrastructure.trader_lab.cibo_market_atlas_journey_extractor_v1 import (
    PRICE_SCALE,
)
from qore.infrastructure.trader_lab.vt31_silver_bullet_v2_backtest import _snapshot

RECEIPT_PATH = Path("docs/research/CIBO-PHASE22-V4-SOURCE-RECEIPT.json")


@dataclass(frozen=True, slots=True)
class Phase22V4Vt31M1Source:
    series: tuple[OhlcSnapshot, ...]
    provider_symbol: str
    raw_sha256: str
    corpus_git_sha: str
    first_observed_at: datetime
    last_closed_at: datetime

    @property
    def fingerprint(self) -> str:
        payload = {
            "candidate_id": V4_CANDIDATE_ID,
            "provider_symbol": self.provider_symbol,
            "raw_sha256": self.raw_sha256,
            "corpus_git_sha": self.corpus_git_sha,
            "bars": len(self.series),
            "first_observed_at": self.first_observed_at.isoformat(),
            "last_closed_at": self.last_closed_at.isoformat(),
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def _binding(receipt: Phase22V4SourceReceipt) -> Phase22V4SourceBinding:
    rows = tuple(
        item
        for item in receipt.bindings
        if item.symbol == "NAS100" and item.timeframe == "M1"
    )
    if len(rows) != 1:
        raise ValueError("V4 VT31 exact M1 binding missing")
    return rows[0]


def _price(relative: int, digits: int) -> str:
    if relative <= 0 or digits <= 0:
        raise ValueError("V4 VT31 relative price/digits invalid")
    value = (Decimal(relative) / PRICE_SCALE).quantize(
        Decimal(1).scaleb(-digits)
    )
    return format(value, "f")


def load_phase22_v4_vt31_m1(
    root: Path,
    *,
    receipt_path: Path = RECEIPT_PATH,
) -> Phase22V4Vt31M1Source:
    receipt = load_phase22_v4_source_receipt(receipt_path)
    binding = _binding(receipt)
    manifest_path = root / "phase22-v4-nas100-m1-manifest.json"
    ledger_path = root / "RAW_M1_LEDGER" / "holdout-v4.jsonl"
    if not manifest_path.is_file() or not ledger_path.is_file():
        raise ValueError("V4 VT31 M1 source artifact incomplete")

    manifest_bytes = manifest_path.read_bytes()
    manifest_sha = "sha256:" + hashlib.sha256(manifest_bytes).hexdigest()
    if manifest_sha != binding.manifest_sha256:
        raise ValueError("V4 VT31 manifest SHA drift")
    manifest = json.loads(manifest_bytes)
    if (
        manifest.get("candidate_id") != V4_CANDIDATE_ID
        or manifest.get("canonical_symbol") != "NAS100"
        or int(manifest.get("retained_bars", 0)) != binding.retained_bars
        or manifest.get("trader_logic_executed") is not False
        or manifest.get("outcomes_inspected") is not False
        or manifest.get("broker_mutation") is not False
        or manifest.get("productive_authority") is not False
    ):
        raise ValueError("V4 VT31 M1 source manifest drift")
    window = manifest.get("window")
    if not isinstance(window, dict) or (
        window.get("start") != PHASE22_V4_CANDIDATE.start_at.isoformat()
        or window.get("end_exclusive")
        != PHASE22_V4_CANDIDATE.end_exclusive_at.isoformat()
    ):
        raise ValueError("V4 VT31 M1 source window drift")
    raw_expected = str(manifest.get("raw_sha256", ""))
    raw_bytes = ledger_path.read_bytes()
    raw_observed = hashlib.sha256(raw_bytes).hexdigest()
    if raw_expected != raw_observed:
        raise ValueError("V4 VT31 M1 raw SHA drift")

    instrument = Instrument("NAS100")
    snapshots: list[OhlcSnapshot] = []
    prior_opened: datetime | None = None
    for raw in raw_bytes.decode("utf-8").splitlines():
        if not raw.strip():
            continue
        item = json.loads(raw)
        if (
            item.get("canonical_symbol") != "NAS100"
            or not item.get("provider_symbol")
        ):
            raise ValueError("V4 VT31 row identity drift")
        opened = datetime.fromisoformat(str(item["opened_at"])).astimezone(UTC)
        if (
            opened.second != 0
            or opened.microsecond != 0
            or (prior_opened is not None and opened <= prior_opened)
            or not (
                PHASE22_V4_CANDIDATE.start_at
                <= opened
                < PHASE22_V4_CANDIDATE.end_exclusive_at
            )
        ):
            raise ValueError("V4 VT31 chronology drift")
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
    if len(series) != binding.retained_bars or not series:
        raise ValueError("V4 VT31 retained bar count drift")
    first = series[0].opened_at.astimezone(UTC)
    last_closed = series[-1].closed_at.astimezone(UTC)
    if (
        first < PHASE22_V4_CANDIDATE.start_at
        or last_closed > PHASE22_V4_CANDIDATE.end_exclusive_at
    ):
        raise ValueError("V4 VT31 terminal source boundary drift")
    return Phase22V4Vt31M1Source(
        series=series,
        provider_symbol=str(manifest["provider_symbol"]),
        raw_sha256=raw_observed,
        corpus_git_sha=receipt.corpus_git_sha,
        first_observed_at=first,
        last_closed_at=last_closed,
    )
