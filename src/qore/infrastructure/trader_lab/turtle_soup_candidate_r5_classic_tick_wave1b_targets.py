"""Corrective R5 Wave 1B targets omitted from the original 291-row manifest."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256

from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError

_EXPECTED_DIGEST = "cb22a2ece84238492f526247295c4c0ee5ede01a1827f0a9a42b45f6943c64be"
_EMBARGO = datetime(2026, 3, 1, tzinfo=UTC)


def frozen_wave1b_tick_target_manifest() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": (
            "qore.trader_lab.turtle_soup_candidate_r5."
            "classic_tick_target_manifest.wave1b.v1"
        ),
        "research_identity": "turtle-soup-candidate-r5",
        "selection_reason": "correct-R1-CLASSIC-M1-INTRABAR_PATH_AMBIGUOUS-omissions",
        "quote_type": "BID",
        "fresh_oos_embargo_start": _EMBARGO.isoformat(),
        "target_count": 2,
        "m1_data_unavailable_count": 0,
        "targets": {
            "GBPUSD": [
                {
                    "minute_opened_at": "2024-04-10T15:45:00+00:00",
                    "side": "long",
                }
            ],
            "USDCAD": [
                {
                    "minute_opened_at": "2025-07-29T12:05:00+00:00",
                    "side": "short",
                }
            ],
        },
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    digest = sha256(encoded).hexdigest()
    if digest != _EXPECTED_DIGEST:
        raise CTraderDemoLabProbeError("R5 Wave 1B target manifest digest mismatch")
    payload["manifest_digest_sha256"] = digest
    return payload
