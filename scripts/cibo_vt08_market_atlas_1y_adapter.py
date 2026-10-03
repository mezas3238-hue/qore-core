#!/usr/bin/env python3
"""Build research-only VT08 M15 evidence from canonical Market Atlas M5.

The adapter does not change VT08 methodology. It converts the immutable
Market Atlas provider-relative M5 corpus through the canonical loader and
retains only complete closed 3xM5 buckets. A one-calendar-year warm-up
precedes each frozen one-year group so the frozen VT08 backtest retains its
>=730-day source contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.cibo_market_atlas_journey_extractor_v1 import (
    load_raw_m5,
)
from qore.infrastructure.trader_lab.cibo_three_holdout_1y_contract import (
    expected_windows,
)

AUTHORIZED_SYMBOLS = (
    "AUDJPY",
    "AUDUSD",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "USDCAD",
    "USDJPY",
)


def _group(group_id: str) -> tuple[datetime, datetime]:
    for item in expected_windows():
        if item.group_id == group_id:
            return item.start_at, item.end_exclusive_at
    raise ValueError(f"unknown group: {group_id}")


def _warmup_start(start_at: datetime) -> datetime:
    try:
        one_year = start_at.replace(year=start_at.year - 1)
    except ValueError:
        one_year = start_at.replace(year=start_at.year - 1, day=28)
    # The frozen VT08 source contract requires >=730 elapsed days between
    # first and last retained M15 bars. A calendar boundary may fall on a
    # weekend/holiday, so add causal pre-evaluation session padding.
    return one_year - timedelta(days=14)


def _account_fingerprint(
    *,
    symbol: str,
    source_root: Path,
    group_id: str,
) -> str:
    manifests = tuple(source_root.rglob("symbol-consumption-manifest.json"))
    if len(manifests) != 1:
        raise ValueError("exact one Market Atlas symbol manifest required")
    manifest_sha = hashlib.sha256(manifests[0].read_bytes()).hexdigest()
    material = "|".join(
        (
            "CIBO_TRADER_LAB_3X1Y_VT08_RESEARCH",
            symbol,
            group_id,
            manifest_sha,
        )
    ).encode()
    return hashlib.sha256(material).hexdigest()


def _aggregate_m15(
    bars: tuple[Any, ...],
    *,
    opened_at: datetime,
    closed_at: datetime,
) -> list[dict[str, str]]:
    selected = tuple(
        row for row in bars if opened_at <= row.opened_at < closed_at
    )
    by_bucket: dict[datetime, list[Any]] = defaultdict(list)
    for row in selected:
        minute = row.opened_at.minute - row.opened_at.minute % 15
        bucket = row.opened_at.replace(minute=minute, second=0, microsecond=0)
        by_bucket[bucket].append(row)

    result: list[dict[str, str]] = []
    for bucket in sorted(by_bucket):
        rows = sorted(by_bucket[bucket], key=lambda item: item.opened_at)
        expected = tuple(bucket + timedelta(minutes=x) for x in (0, 5, 10))
        if (
            len(rows) != 3
            or tuple(item.opened_at for item in rows) != expected
            or any(
                item.closed_at != item.opened_at + timedelta(minutes=5)
                for item in rows
            )
        ):
            continue
        result.append(
            {
                "opened_at": bucket.astimezone(UTC).isoformat(),
                "closed_at": (bucket + timedelta(minutes=15))
                .astimezone(UTC)
                .isoformat(),
                "open": format(rows[0].open, "f"),
                "high": format(max(item.high for item in rows), "f"),
                "low": format(min(item.low for item in rows), "f"),
                "close": format(rows[-1].close, "f"),
            }
        )
    return result


def build_evidence(
    *,
    source_root: Path,
    symbol: str,
    group_id: str,
    software_sha: str,
) -> dict[str, Any]:
    if symbol not in AUTHORIZED_SYMBOLS:
        raise ValueError("VT08 symbol outside frozen seven-market surface")
    if len(software_sha) != 40 or any(c not in "0123456789abcdef" for c in software_sha):
        raise ValueError("software_sha must be exact lowercase Git SHA")

    start_at, end_at = _group(group_id)
    warmup_at = _warmup_start(start_at)
    evidence, provenance = load_raw_m5(source_root)
    if evidence.symbol != symbol:
        raise ValueError("Market Atlas symbol drift")

    m15 = _aggregate_m15(
        evidence.bars,
        opened_at=warmup_at,
        closed_at=end_at,
    )
    if not m15:
        raise ValueError("derived VT08 M15 evidence is empty")
    first = datetime.fromisoformat(m15[0]["opened_at"])
    last = datetime.fromisoformat(m15[-1]["closed_at"])
    span = last - first
    if span < timedelta(days=730):
        raise ValueError(
            f"VT08 M15 evidence below 730-day source contract: {span.days}"
        )

    return {
        "schema": "qore.cibo.trader-lab.vt08-market-atlas-1y-adapter.v1",
        "environment": "demo",
        "read_only": True,
        "research_only": True,
        "adaptive_research_only": True,
        "account_is_live": False,
        "trading_permission_verified": False,
        "account_fingerprint": _account_fingerprint(
            symbol=symbol,
            source_root=source_root,
            group_id=group_id,
        ),
        "software_sha": software_sha,
        "symbol": {"symbol_name": symbol},
        "provider_symbol_name": provenance["provider_symbol"],
        "checked_at": end_at.isoformat(),
        "group_id": group_id,
        "warmup_opened_at": warmup_at.isoformat(),
        "evaluation_opened_at": start_at.isoformat(),
        "evaluation_closed_at": end_at.isoformat(),
        "periods": {"M15": m15},
        "coverage": {
            "M15": {
                "bar_count": len(m15),
                "first_opened_at": m15[0]["opened_at"],
                "last_closed_at": m15[-1]["closed_at"],
                "span_seconds": int(span.total_seconds()),
            }
        },
        "source": {
            "identity": "CIBO_MARKET_ATLAS_10Y_CONSUMPTION_V1",
            "canonical_symbol": provenance["canonical_symbol"],
            "provider_symbol": provenance["provider_symbol"],
            "digits": provenance["digits"],
            "retained_source_m5_bars": provenance["retained_bars"],
        },
        "governance": {
            "trader_methodology_changed": False,
            "outcome_used_for_evidence_construction": False,
            "partial_m15_used": False,
            "broker_mutation": False,
            "live": False,
            "production": False,
            "real_capital": False,
            "fresh_oos_claimed": False,
            "certification_claimed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--symbol", choices=AUTHORIZED_SYMBOLS, required=True)
    parser.add_argument(
        "--group-id",
        choices=("GROUP_1", "GROUP_2", "GROUP_3"),
        required=True,
    )
    parser.add_argument("--software-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_evidence(
        source_root=args.source_root,
        symbol=args.symbol,
        group_id=args.group_id,
        software_sha=args.software_sha,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "group_id": payload["group_id"],
                "symbol": args.symbol,
                "m15_bars": payload["coverage"]["M15"]["bar_count"],
                "evaluation_opened_at": payload["evaluation_opened_at"],
                "evaluation_closed_at": payload["evaluation_closed_at"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
