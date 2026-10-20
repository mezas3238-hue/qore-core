"""VT08 A -> B: source-only per-market raw custody catalog, not semantic proof.

Reuse the frozen A M30/M3 family census without importing B's verifier.
Canonical M3/M15 bar IDs, pinned physical-file SHA, market-specific custody,
and exact pre-C2 / C3 clocks are provided for B to validate independently.

No numeric feature is inferred, no TTrades setup admitted, and no PnL accessed.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Final

from qore.infrastructure.trader_lab.vt08_a_m30m3_raw_bar_custody_v1 import MARKETS

SCHEMA: Final = "qore.vt08.a_b.market_raw_custody_catalog.v1"
STAGE: Final = "UNIQUE_M3_CISD_PS_SHAPE_REQUIRES_AUTHOR_ADJUDICATION"
BARS: Final = (
    ("c1_m3_raw_bar_receipts", "M3", 10),
    ("c2_m3_raw_bar_receipts", "M3", 10),
    ("c2_m15_raw_bar_receipts", "M15", 2),
    ("pre_c2_h1_m15_raw_bar_receipts", "M15", 12),
)


def _sha(data: object) -> bool:
    return (
        isinstance(data, str)
        and len(data) == 64
        and all(c in "0123456789abcdef" for c in data)
    )


def _instant(raw: object) -> datetime:
    if not isinstance(raw, str):
        raise ValueError("VT08 source clock must be ISO8601 text")
    try:
        value = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("VT08 source timestamp invalid") from exc
    if value.utcoffset() is None:
        raise ValueError("VT08 source timestamps must have timezone")
    return value.astimezone(UTC)


def _bar_id(body: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False)
        .encode("utf-8")
    ).hexdigest()


def _source_bar(
    raw: object,
    *,
    market: str,
    raw_sha: str,
    expected_profile: str,
    latest_available: datetime,
) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise ValueError("VT08 expected raw bar object")
    if raw.get("source_raw_sha256") != raw_sha:
        raise ValueError("VT08 source bar references wrong feed or market")
    if raw.get("profile") != expected_profile:
        raise ValueError("VT08 source profile mismatch; no legacy profile alias")
    if raw.get("semantics") != "OBSERVED_OHLC_ONLY_NOT_TTRADES_RULE":
        raise ValueError("VT08 raw bar cannot claim semantic TTrades authority")
    ohlc = raw.get("ohlc")
    if not isinstance(ohlc, (tuple, list)) or len(ohlc) != 4:
        raise ValueError("VT08 source OHLC invalid")
    try:
        values = [Decimal(v) for v in ohlc]
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("VT08 source OHLC invalid") from exc
    if not all(v.is_finite() and v > 0 for v in values):
        raise ValueError("VT08 source OHLC not finite-positive")
    op, high, low, close = values
    if low > min(op, close) or high < max(op, close) or low > high:
        raise ValueError("VT08 source OHLC logically impossible")
    opened = _instant(raw.get("opened_at_utc"))
    closed = _instant(raw.get("closed_at_utc"))
    available = _instant(raw.get("available_at_utc"))
    minutes = 3 if expected_profile == "M3" else 15
    if closed - opened != timedelta(minutes=minutes) or closed != available:
        raise ValueError("VT08 source bar time interval/availability mismatch")
    if closed > latest_available:
        raise ValueError("VT08 bar unavailable when decision was made")
    body: dict[str, object] = {
        "profile": expected_profile,
        "source_raw_sha256": raw_sha,
        "opened_at_utc": opened.isoformat(),
        "closed_at_utc": closed.isoformat(),
        "ohlc": tuple(ohlc),
    }
    if _bar_id(body) != raw.get("source_bar_id"):
        raise ValueError("VT08 bar SHA is not canonical or was modified")
    return {
        **body,
        "source_bar_id": raw["source_bar_id"],
        "market": market,
        "available_at_utc": available.isoformat(),
        "semantics": "OBSERVED_OHLC_ONLY_NOT_TTRADES_RULE",
    }


def build_catalog(
    *,
    market: str,
    source_report: Mapping[str, object],
    frozen_manifest: Mapping[str, object],
) -> dict[str, object]:
    """Create unprivileged B-ready raw catalog, never a signed A/B manifest."""
    if market not in MARKETS or source_report.get("market") != market:
        raise ValueError("VT08 source market identity inconsistent")
    markets = frozen_manifest.get("market_rows")
    if not isinstance(markets, dict) or market not in markets:
        raise ValueError("VT08 immutable census manifest missing market")
    expected = markets[market]
    if not isinstance(expected, dict):
        raise ValueError("VT08 malformed frozen census")
    raw_shas = {
        "M3": expected.get("m3_raw_sha256"),
        "M15": expected.get("m15_raw_sha256"),
    }
    if not all(_sha(x) for x in raw_shas.values()) or len(set(raw_shas.values())) != 2:
        raise ValueError("VT08 frozen feed SHA missing or colliding")
    if (source_report.get("source_m3_sha256") != raw_shas["M3"]
            or source_report.get("source_m15_sha256") != raw_shas["M15"]):
        raise ValueError("VT08 raw file manifest mismatch")
    if (source_report.get("c2_windows_total") != expected.get("c2_windows_total")
            or source_report.get("stage_counts") != expected.get("stage_counts")):
        raise ValueError("VT08 frozen source census changed")
    if source_report.get("pnl_evaluated") is not False:
        raise ValueError("VT08 source-only report contaminated by PnL")
    stages = source_report.get("examples_by_stage")
    if not isinstance(stages, dict) or not isinstance(stages.get(STAGE), list):
        raise ValueError("VT08 source stage receipts absent")
    cases = stages[STAGE]
    if len(cases) != expected["stage_counts"][STAGE]:
        raise ValueError("VT08 missing a structural precursor: no favorable sampling")
    catalog: dict[str, dict[str, object]] = {}
    event_index: list[dict[str, object]] = []
    for case in cases:
        if not isinstance(case, dict) or case.get("market") != market:
            raise ValueError("VT08 cross-market case injection")
        if case.get("stage") != STAGE:
            raise ValueError("VT08 case misclassified")
        if (case.get("A_rule_complete") is not False
                or case.get("cognitive_ready") is not False
                or case.get("broker_fill") is not False
                or case.get("pnl_read") is not False):
            raise ValueError("VT08 promoted synthetic shape to trade")
        if (case.get("source_m3_file_sha256") != raw_shas["M3"]
                or case.get("source_m15_file_sha256") != raw_shas["M15"]):
            raise ValueError("VT08 cross-feed case SHA mismatch")
        c1 = _instant(case.get("c1_opened_at_utc"))
        c2 = _instant(case.get("c2_opened_at_utc"))
        decision = _instant(case.get("decision_at_utc"))
        if c2 != c1 + timedelta(minutes=30) or decision != c2 + timedelta(minutes=30):
            raise ValueError("VT08 C1/C2/C3 temporal lineage invalid")
        available_h1 = case.get("pre_c2_h1_context_available") is True
        fields: dict[str, list[str]] = {}
        for field, profile, count in BARS:
            items = case.get(field)
            if not isinstance(items, list):
                raise ValueError("VT08 raw source list missing")
            if field == "pre_c2_h1_m15_raw_bar_receipts" and not available_h1:
                if items:
                    raise ValueError("VT08 incomplete H1 context cannot claim bars")
                fields[field] = []
                continue
            if len(items) != count:
                raise ValueError("VT08 incomplete expected source bar window")
            cutoff = c2 if field.startswith(("c1_", "pre_c2_")) else decision
            expected_start = (
                c1 if field.startswith("c1_")
                else c2 if field.startswith("c2_")
                else c2.replace(minute=0, second=0, microsecond=0)
                - timedelta(hours=3)
            )
            step = timedelta(minutes=3 if profile == "M3" else 15)
            ids: list[str] = []
            for i, item in enumerate(items):
                record = _source_bar(
                    item, market=market, raw_sha=raw_shas[profile],
                    expected_profile=profile, latest_available=cutoff,
                )
                if _instant(record["opened_at_utc"]) != expected_start + i * step:
                    raise ValueError("VT08 source bars not chronologically contiguous")
                key = str(record["source_bar_id"])
                if key in catalog and catalog[key] != record:
                    raise ValueError("VT08 source bar SHA collision or conflicting market")
                catalog[key] = record
                ids.append(key)
            fields[field] = ids
        event_index.append({
            "market": market,
            "c2_opened_at_utc": c2.isoformat(),
            "decision_at_utc": decision.isoformat(),
            "source_bar_groups": fields,
            "author_relevant_swing_verified": False,
            "author_poi_verified": False,
            "author_cisd_ps_verified": False,
            "author_breaker_verified": False,
            "author_target_verified": False,
            "cognitive_situation_27_fields_verified": False,
            "source_complete": False,
        })
    return {
        "schema": SCHEMA,
        "market": market,
        "source_raw_market_map": {raw_sha: market for raw_sha in raw_shas.values()},
        "pinned_raw_shas": sorted(raw_shas.values()),
        "bar_catalog": catalog,
        "source_only_events": event_index,
        "catalog_unique_bars": len(catalog),
        "source_only_event_count": len(event_index),
        "author_fidelity_certified": False,
        "cognitive_certified": False,
        "economic_gates_certified": False,
        "independent_B_verified": False,
        "signed_A_B_manifest_sha256": None,
        "orders": 0,
        "fills": 0,
        "pnl_evaluated": False,
    }
