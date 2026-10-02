"""Source-only adapter from Phase22 NAS100 M1 archive to frozen VT31 bars."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from qore.infrastructure.market_data import Instrument, OhlcSnapshot
from qore.infrastructure.trader_lab.cibo_market_atlas_journey_extractor_v1 import (
    PRICE_SCALE,
)
from qore.infrastructure.trader_lab.vt31_silver_bullet_v2_backtest import (
    _snapshot,
)

CANDIDATE_ID = "CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2"
SOURCE_IDENTITY = "CIBO_PHASE22_HOLDOUT_V2_NAS100_M1_SOURCE_V1"
SOURCE_SCHEMA = "qore.cibo.phase22.holdout-v2-nas100-m1-source.v1"
RAW_SOURCE_SHA256 = (
    "00f99459aa9bcf93007bc90157129be088d8d4c122dd0098987047cdce090098"
)
COLLECTOR_GIT_SHA = "00358aad1d174a1e97b2850814f26431979798c6"


@dataclass(frozen=True, slots=True)
class Phase22Vt31M1Source:
    series: tuple[OhlcSnapshot, ...]
    provider_symbol: str
    raw_sha256: str
    collector_git_sha: str
    first_observed_at: datetime
    last_closed_at: datetime

    @property
    def fingerprint(self) -> str:
        payload = {
            "candidate_id": CANDIDATE_ID,
            "provider_symbol": self.provider_symbol,
            "raw_sha256": self.raw_sha256,
            "collector_git_sha": self.collector_git_sha,
            "bars": len(self.series),
            "first_observed_at": self.first_observed_at.isoformat(),
            "last_closed_at": self.last_closed_at.isoformat(),
        }
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return sha256(raw).hexdigest()


def _price(relative: int, digits: int) -> str:
    if relative <= 0 or digits <= 0:
        raise ValueError("Phase22 VT31 relative price/digits invalid")
    value = (Decimal(relative) / PRICE_SCALE).quantize(
        Decimal(1).scaleb(-digits)
    )
    return format(value, "f")


def load_phase22_vt31_m1(root: Path) -> Phase22Vt31M1Source:
    manifest_path = root / "phase22-v2-nas100-m1-manifest.json"
    ledger_path = root / "RAW_M1_LEDGER" / "holdout-v2.jsonl"
    if not manifest_path.is_file() or not ledger_path.is_file():
        raise ValueError("Phase22 VT31 M1 source artifact incomplete")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("candidate_id") != CANDIDATE_ID
        or manifest.get("identity") != SOURCE_IDENTITY
        or manifest.get("schema") != SOURCE_SCHEMA
        or manifest.get("canonical_symbol") != "NAS100"
        or manifest.get("provider_symbol") != "USTEC"
        or manifest.get("raw_sha256") != RAW_SOURCE_SHA256
        or manifest.get("trader_logic_executed") is not False
        or manifest.get("outcomes_inspected") is not False
        or manifest.get("productive_authority") is not False
    ):
        raise ValueError("Phase22 VT31 M1 source manifest drift")

    raw_bytes = ledger_path.read_bytes()
    observed_sha = sha256(raw_bytes).hexdigest()
    if observed_sha != RAW_SOURCE_SHA256:
        raise ValueError("Phase22 VT31 M1 raw SHA drift")

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
            raise ValueError("Phase22 VT31 M1 row identity drift")
        opened = datetime.fromisoformat(str(item["opened_at"])).astimezone(UTC)
        if (
            opened.second != 0
            or opened.microsecond != 0
            or (prior_opened is not None and opened <= prior_opened)
        ):
            raise ValueError("Phase22 VT31 M1 chronology drift")
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
    if len(series) != int(manifest["retained_bars"]):
        raise ValueError("Phase22 VT31 M1 retained bar count drift")
    if len(series) != 170396:
        raise ValueError("Phase22 VT31 M1 expected population drift")
    if not series:
        raise ValueError("Phase22 VT31 M1 source is empty")
    first = series[0].opened_at.astimezone(UTC)
    last_closed = series[-1].closed_at.astimezone(UTC)
    if first.isoformat() != "2015-10-19T00:00:00+00:00":
        raise ValueError("Phase22 VT31 first bar drift")
    if last_closed.isoformat() != "2016-04-19T00:00:00+00:00":
        raise ValueError("Phase22 VT31 terminal bar drift")
    return Phase22Vt31M1Source(
        series=series,
        provider_symbol="USTEC",
        raw_sha256=observed_sha,
        collector_git_sha=COLLECTOR_GIT_SHA,
        first_observed_at=first,
        last_closed_at=last_closed,
    )
