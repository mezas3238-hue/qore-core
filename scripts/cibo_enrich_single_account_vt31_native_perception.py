#!/usr/bin/env python3
"""Enrich VT31 rows in a single-account manifest from causal NAS100 M1.

The script accepts one or more existing VT31 market-evidence files covering the
population window, concatenates/deduplicates their closed M1 bars, and rebuilds
native perception at every archived VT31 decision timestamp.

No outcome field participates in reconstruction. The source manifest's
settlement labels are copied unchanged only for later research settlement.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_single_account_manifest_integrity import (
    reseal_single_account_manifest,
    validate_single_account_manifest_sha256,
)
from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_nas100_native_perception import (
    build_vt31_native_causal_perception,
)

_NY = ZoneInfo("America/New_York")


def _local_day(bar: object) -> date:
    return bar.opened_at.astimezone(_NY).date()


def _load_one(path: Path) -> tuple[object, ...]:
    if path.suffix.lower() != ".zip":
        series, *_ = load_market_evidence(path)
        return tuple(series)

    with zipfile.ZipFile(path) as archive:
        candidates = tuple(
            name
            for name in archive.namelist()
            if name.replace("\\", "/").endswith(
                "fresh/NAS100/market-evidence.json"
            )
        )
        if len(candidates) != 1:
            raise CiboCapitalManagementError(
                "VT31 source ZIP requires exactly one NAS100 market-evidence.json"
            )
        with tempfile.TemporaryDirectory(prefix="qore-vt31-m1-") as tmp:
            target = Path(tmp) / "market-evidence.json"
            with archive.open(candidates[0]) as source, target.open("wb") as sink:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    sink.write(chunk)
            series, *_ = load_market_evidence(target)
            return tuple(series)


def _load_all(paths: tuple[Path, ...]) -> tuple[object, ...]:
    by_identity: dict[tuple[object, object], object] = {}
    for path in paths:
        for bar in _load_one(path):
            key = (bar.opened_at, bar.closed_at)
            existing = by_identity.get(key)
            if existing is not None:
                if (
                    existing.open != bar.open
                    or existing.high != bar.high
                    or existing.low != bar.low
                    or existing.close != bar.close
                ):
                    raise CiboCapitalManagementError(
                        "VT31 M1 duplicate timestamp has differing OHLC"
                    )
                continue
            by_identity[key] = bar
    rows = tuple(
        sorted(by_identity.values(), key=lambda bar: bar.opened_at)
    )
    if not rows:
        raise CiboCapitalManagementError(
            "VT31 perception enrichment requires M1 evidence"
        )
    return rows


def enrich(
    manifest: dict[str, Any],
    series: tuple[object, ...],
) -> dict[str, Any]:
    source_manifest_sha256 = validate_single_account_manifest_sha256(manifest)
    by_day_raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        by_day_raw[_local_day(bar)].append(bar)
    by_day = {
        day: tuple(sorted(rows, key=lambda bar: bar.opened_at))
        for day, rows in by_day_raw.items()
    }
    ordered_days = sorted(by_day)
    admitted: list[date] = []
    for day in ordered_days:
        bars = by_day[day]
        ref = [
            bar
            for bar in bars
            if (9, 0, 0)
            <= (
                bar.opened_at.astimezone(_NY).hour,
                bar.opened_at.astimezone(_NY).minute,
                bar.opened_at.astimezone(_NY).second,
            )
            < (10, 0, 0)
        ]
        if len(ref) == 60:
            admitted.append(day)

    opportunities = manifest.get("opportunities")
    if not isinstance(opportunities, list):
        raise CiboCapitalManagementError(
            "VT31 enrichment requires manifest opportunities"
        )

    enriched = 0
    blocked: list[dict[str, str]] = []
    result_rows: list[dict[str, Any]] = []
    for row in opportunities:
        if row.get("trader_id") != "VT31_NAS100":
            result_rows.append(row)
            continue

        decision_at = __import__("datetime").datetime.fromisoformat(
            str(row["market_decision_at"])
        )
        day = decision_at.astimezone(_NY).date()
        day_bars = by_day.get(day)
        if not day_bars:
            blocked.append(
                {
                    "signal_fingerprint": str(row["signal_fingerprint"]),
                    "reason": "no-m1-day",
                }
            )
            result_rows.append(row)
            continue

        prior_days = [item for item in admitted if item < day]
        prior_day = prior_days[-1] if prior_days else None
        prior_bars = () if prior_day is None else by_day[prior_day]
        prior5_days = prior_days[-5:]
        prior5 = tuple(by_day[item] for item in prior5_days)

        payload = row["trader_opportunity"]
        try:
            context = build_vt31_native_causal_perception(
                day_bars=day_bars,
                prior_admitted_day_bars=prior_bars,
                prior_admitted_days=prior5,
                decision_at=decision_at,
                side=str(payload["side"]),
                intended_entry=__import__("decimal").Decimal(
                    str(payload["intended_entry"])
                ),
                stop_loss=__import__("decimal").Decimal(
                    str(payload["stop_loss"])
                ),
                take_profit=__import__("decimal").Decimal(
                    str(payload["take_profit"])
                ),
            )
        except Exception as error:
            blocked.append(
                {
                    "signal_fingerprint": str(row["signal_fingerprint"]),
                    "reason": str(error),
                }
            )
            result_rows.append(row)
            continue

        updated = dict(row)
        opp = dict(payload)
        existing = {
            str(item[0]): str(item[1])
            for item in opp.get("decision_context", [])
        }
        existing.update(dict(context))
        opp["decision_context"] = [
            [key, value] for key, value in sorted(existing.items())
        ]
        updated["trader_opportunity"] = opp
        result_rows.append(updated)
        enriched += 1

    result = dict(manifest)
    result["opportunities"] = result_rows
    result["vt31_native_perception_enrichment"] = {
        "schema": "qore.cibo.vt31-native-perception-enrichment.v1",
        "source_manifest_sha256": source_manifest_sha256,
        "attempted": sum(
            1 for row in opportunities if row.get("trader_id") == "VT31_NAS100"
        ),
        "enriched": enriched,
        "blocked_count": len(blocked),
        "blocked": blocked,
        "source_m1_bar_count": len(series),
        "outcome_used": False,
        "future_bar_lookup": False,
        "external_ai": False,
    }
    return reseal_single_account_manifest(result)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--vt31-evidence",
        action="append",
        type=Path,
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    result = enrich(manifest, _load_all(tuple(args.vt31_evidence)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = result["vt31_native_perception_enrichment"]
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["blocked_count"] == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
