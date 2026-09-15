"""Frozen Classic tick-resolution targets for Turtle Soup candidate R5."""

from __future__ import annotations

import base64
import json
import zlib
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import cast

from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError

_SCHEMA = "qore.trader_lab.turtle_soup_candidate_r5.classic_tick_target_manifest.v1"
_EXPECTED_DIGEST = "4923fe9eb2d85416e69d03a4514ebe92bda4a2e277c73ca1e70df5f1cd6bc27f"
_EMBARGO = datetime(2026, 3, 1, tzinfo=UTC)
_COMPRESSED_MANIFEST_B64 = (
    "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"
)


def _canonical_digest(payload: dict[str, object]) -> str:
    material = dict(payload)
    material.pop("manifest_digest_sha256", None)
    encoded = json.dumps(
        material,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def frozen_tick_target_manifest() -> dict[str, object]:
    """Return and validate the immutable ambiguity-only target manifest."""

    raw = zlib.decompress(base64.b64decode(_COMPRESSED_MANIFEST_B64)).decode("utf-8")
    payload = cast(dict[str, object], json.loads(raw))
    if payload.get("schema") != _SCHEMA:
        raise CTraderDemoLabProbeError("R5 tick target schema mismatch")
    if payload.get("research_identity") != "turtle-soup-candidate-r5":
        raise CTraderDemoLabProbeError("R5 tick target research identity mismatch")
    if payload.get("selection_reason") != (
        "resolve-only-R1-CLASSIC-M1-INTRABAR_PATH_AMBIGUOUS"
    ):
        raise CTraderDemoLabProbeError("R5 tick target selection reason mismatch")
    if payload.get("quote_type") != "BID" or payload.get("target_count") != 293:
        raise CTraderDemoLabProbeError("R5 tick target contract changed")
    if payload.get("fresh_oos_embargo_start") != _EMBARGO.isoformat():
        raise CTraderDemoLabProbeError("R5 tick target embargo mismatch")
    if payload.get("manifest_digest_sha256") != _EXPECTED_DIGEST:
        raise CTraderDemoLabProbeError("R5 tick target stored digest mismatch")
    if _canonical_digest(payload) != _EXPECTED_DIGEST:
        raise CTraderDemoLabProbeError("R5 tick target manifest digest mismatch")
    targets = payload.get("targets")
    if not isinstance(targets, dict):
        raise CTraderDemoLabProbeError("R5 tick targets must be a market mapping")
    expected = {"EURUSD": 40, "GBPUSD": 47, "USDJPY": 35, "AUDUSD": 43, "USDCAD": 43, "GBPJPY": 44, "AUDJPY": 41}
    if {key: len(value) for key, value in targets.items() if isinstance(value, list)} != expected:
        raise CTraderDemoLabProbeError("R5 tick target census changed")
    for rows in targets.values():
        if not isinstance(rows, list):
            raise CTraderDemoLabProbeError("R5 tick target market rows must be lists")
        for row in rows:
            if not isinstance(row, dict):
                raise CTraderDemoLabProbeError("R5 tick target row must be object")
            raw_time = row.get("minute_opened_at")
            side = row.get("side")
            if not isinstance(raw_time, str) or side not in {"long", "short"}:
                raise CTraderDemoLabProbeError("R5 tick target row is invalid")
            opened = datetime.fromisoformat(raw_time.replace("Z", "+00:00")).astimezone(UTC)
            if opened + timedelta(minutes=1) > _EMBARGO:
                raise CTraderDemoLabProbeError("R5 tick target crosses fresh OOS embargo")
    return payload
