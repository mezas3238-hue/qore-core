#!/usr/bin/env python3
"""VT31 M2: independent historical-source parity, P3 #930 vs V1 #932.

P3 module must be copied from pinned Git commit by CI before import.
Source M1 is real; the neutral COG-like probe is SYNTHETIC and NEVER
counts as actual cognition, a trade, or a pass of ICT doctrine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    CognitiveDecision,
    M1Bar,
    SessionId,
    Side,
)
from scripts.vt31_ict_dol_source_v1_20261014 import attest_ict_dol_source
from scripts.vt31_mc_p3_ict_independent_dol_20261014 import verify_ict_dol_from_m1

NY = ZoneInfo("America/New_York")
MARKET_SHA = "0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa"
P3_SHA = "1c820086339323f79d4ec1cb5954fb53841064b2"
V1_SHA = "e3f65b34599cc868d6cf1867dcc3df480e1e66d4"
PREREG_SHA = "8ddbdf3ba9c3728af5cdb6d34f95fe60ea29d484"
DATES = (
    "2024-01-16", "2024-04-16", "2024-07-16", "2024-10-15",
    "2025-01-14", "2025-04-15", "2025-07-15", "2025-10-14",
    "2026-01-13", "2026-04-14", "2026-07-14", "2026-09-15",
)
SESSIONS = ((SessionId.LONDON, 3), (SessionId.NY_AM, 10),
            (SessionId.NY_PM, 14))
FAMILIES = (
    "PRIOR_NY_CASH_SESSION", "ASIA_NY_CLOCK", "LONDON_NY_CLOCK",
)


def checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as src:
        while chunk := src.read(2**20):
            h.update(chunk)
    return h.hexdigest()


def as_utc(value: object) -> datetime:
    t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("SOURCE_NAIVE_TIMESTAMP")
    return t.astimezone(UTC)


def collect_frozen_days(path: Path) -> tuple[dict[str, tuple[M1Bar, ...]], int]:
    import ijson

    # The frozen source remains the 3Y development dataset, not a new OOS.
    anchors = [(s, date.fromisoformat(s)) for s in DATES]
    gathered: dict[str, list[M1Bar]] = {s: [] for s in DATES}
    count = 0
    last: datetime | None = None
    with path.open("rb") as src:
        for raw in ijson.items(src, "periods.M1.item"):
            opened, closed = as_utc(raw["opened_at"]), as_utc(raw["closed_at"])
            if closed - opened != timedelta(minutes=1):
                raise ValueError("INVALID_M1_BAR_DURATION")
            if last is not None and opened <= last:
                raise ValueError("SOURCE_OUT_OF_ORDER_OR_DUPLICATE")
            last = opened
            count += 1
            day = opened.astimezone(NY).date()
            relevant = [
                s for s, d in anchors
                if d - timedelta(days=5) <= day <= d
            ]
            if not relevant:
                continue
            b = M1Bar(
                opened, closed, Decimal(str(raw["open"])),
                Decimal(str(raw["high"])), Decimal(str(raw["low"])),
                Decimal(str(raw["close"])),
            )
            for s in relevant:
                gathered[s].append(b)
    if count != 1059784:
        raise ValueError(f"FROZEN_M1_COUNT_DRIFT_{count}")
    return {k: tuple(v) for k, v in gathered.items()}, count


def compare_one(
    history: tuple[M1Bar, ...], *, as_of: datetime,
    session: SessionId, family: str, side: Side,
) -> dict[str, Any]:
    # Independent V1 generates its own six pools using only closed M1.
    # Neutral DTO probes are explicitly NOT emitted by VT31's authentic COG.
    source = attest_ict_dol_source(
        as_of=as_of, session=session, history=history, cognition=None,
    )
    label = family + ("_HIGH" if side is Side.LONG else "_LOW")
    pool = next((p for p in source.pools if p.family == label), None)
    if pool is None:
        raise AssertionError("MISSING_FROZEN_FAMILY")
    probe = CognitiveDecision(
        session=session, side=side, observed_at=as_of,
        draw_target=pool.level if pool.level is not None else Decimal("100"),
        draw_family=label,
        draw_level_observed_at=pool.source_end,
        structure_level=Decimal("100"),
        structure_level_confirmed_at=as_of - timedelta(minutes=1),
        structure_break_confirmed_at=as_of,
        source_provenance="RECONCILIATION_PROBE_NOT_NATIVE_COG",
        cognitive_version="SYNTHETIC_PROBE_NO_METHOD_CERT",
    )
    p3 = verify_ict_dol_from_m1(
        as_of=as_of, session=session, history=history, cognition=probe,
    )
    v1 = attest_ict_dol_source(
        as_of=as_of, session=session, history=history, cognition=probe,
    )
    state_p3 = (
        "SUPPORTED" if p3.state == "VERIFIED_QORE_DOL_PRICE_LINEAGE"
        else p3.state
    )
    state_v1 = "SUPPORTED" if v1.state == "CONFIRMED" else v1.state
    return {
        "family": label,
        "probe_not_authentic_cognition": True,
        "v1_pool_state": pool.state,
        "p3_state": state_p3,
        "v1_state": state_v1,
        "p3_reasons": list(p3.reasons),
        "v1_reasons": list(v1.reasons),
        "same_normalized_state": state_p3 == state_v1,
        "p3_source_start": (
            p3.source_start.isoformat() if p3.source_start else None
        ),
        "v1_source_start": pool.source_start.isoformat(),
        "p3_source_level": (
            str(p3.observed_level) if p3.observed_level is not None else None
        ),
        "v1_source_level": (
            str(pool.level) if pool.level is not None else None
        ),
        "method_certified": False,
        "cognition_certified": False,
        "execution_authorized": False,
    }


def audit_days(groups: dict[str, tuple[M1Bar, ...]]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    paired: Counter[str] = Counter()
    missing = 0
    for day_str in DATES:
        d = date.fromisoformat(day_str)
        for session, hour in SESSIONS:
            at = datetime.combine(d, time(hour, 30), tzinfo=NY).astimezone(UTC)
            rows = tuple(x for x in groups[day_str] if x.closed_at <= at)
            source_present = bool(rows and rows[-1].closed_at == at)
            for family in FAMILIES:
                for side in (Side.LONG, Side.SHORT):
                    common = {
                        "ny_date": day_str, "session": session.value,
                        "as_of": at.isoformat(), "side": side.value,
                    }
                    if not source_present:
                        missing += 1
                        records.append({
                            **common, "family": family,
                            "p3_state": "UNKNOWN_INPUT",
                            "v1_state": "UNKNOWN_INPUT",
                            "p3_reasons": ["M1_AT_ASOF_MISSING"],
                            "v1_reasons": ["M1_AT_ASOF_MISSING"],
                            "same_normalized_state": False,
                            "probe_not_authentic_cognition": True,
                            "method_certified": False,
                            "cognition_certified": False,
                            "execution_authorized": False,
                        })
                        continue
                    comparison = compare_one(
                        rows, as_of=at, session=session, family=family, side=side,
                    )
                    paired[comparison["p3_state"] + "|" +
                           comparison["v1_state"]] += 1
                    records.append({**common, **comparison})
    if len(records) != len(DATES) * len(SESSIONS) * len(FAMILIES) * 2:
        raise AssertionError("FROZEN_PROBE_GRID_INCOMPLETE")
    return {
        "identity": "VT31_M2_930_932_SOURCE_CONTRACT_RECONCILIATION",
        "historical_source": "NAS100_3Y_ALREADY_SEEN_DEVELOPMENT_NOT_OOS",
        "market_sha256": MARKET_SHA,
        "p3_source_commit": P3_SHA,
        "v1_source_commit": V1_SHA,
        "prereg_commit": PREREG_SHA,
        "fixed_dates": list(DATES),
        "scheduled_probes": len(records),
        "unavailable_source_probes": missing,
        "paired_state_matrix": dict(sorted(paired.items())),
        "disagreements": [
            row for row in records
            if row["p3_state"] != row["v1_state"]
        ],
        "records": records,
        "real_market_m1_but_synthetic_cog_probe": True,
        "native_cog_evaluated": False,
        "ict_authorial_method_certified": False,
        "method_certified": False,
        "cognition_certified": False,
        "trader_certified": False,
        "economic_pnl": None,
        "profit_factor": None,
        "broker_ack_or_fills": 0,
        "execution_authorized": False,
        "live_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if checksum(args.market) != MARKET_SHA:
        raise ValueError("FROZEN_MARKET_SHA_DRIFT")
    groups, n = collect_frozen_days(args.market)
    report = audit_days(groups)
    report["original_m1_total"] = n
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "original_m1_total": n,
        "scheduled_probes": report["scheduled_probes"],
        "unavailable": report["unavailable_source_probes"],
        "matrix": report["paired_state_matrix"],
        "disagreement_count": len(report["disagreements"]),
        "method_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
