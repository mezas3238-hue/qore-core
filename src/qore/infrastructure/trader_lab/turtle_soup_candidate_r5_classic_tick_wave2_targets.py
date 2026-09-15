"""R5 Wave 2 targets exposed only after Wave 1/1B causal resolution."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256

from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError

_EXPECTED_DIGEST = "839714b3be5a461d0994bb5c5d155b100ac41aae28cd471c509f3c202a092290"
_EMBARGO = datetime(2026, 3, 1, tzinfo=UTC)
_ROWS: dict[str, tuple[tuple[str, str], ...]] = {
    "EURUSD": (("2025-04-21T00:11:00+00:00", "short"),),
    "GBPUSD": (
        ("2024-03-22T07:53:00+00:00", "long"),
        ("2024-09-18T18:01:00+00:00", "short"),
        ("2024-11-06T12:33:00+00:00", "long"),
        ("2024-11-21T16:19:00+00:00", "long"),
        ("2025-04-04T17:32:00+00:00", "long"),
        ("2025-07-16T13:48:00+00:00", "long"),
    ),
    "USDJPY": (("2025-04-03T09:13:00+00:00", "long"),),
    "AUDUSD": (
        ("2024-08-19T14:02:00+00:00", "short"),
        ("2024-12-17T15:52:00+00:00", "long"),
    ),
    "USDCAD": (
        ("2025-01-20T14:45:00+00:00", "long"),
        ("2025-06-02T07:21:00+00:00", "long"),
    ),
    "GBPJPY": (
        ("2023-11-24T14:35:00+00:00", "short"),
        ("2024-06-12T10:43:00+00:00", "short"),
        ("2025-04-04T10:53:00+00:00", "long"),
        ("2026-02-11T04:36:00+00:00", "long"),
    ),
    "AUDJPY": (
        ("2023-10-31T09:40:00+00:00", "short"),
        ("2023-11-14T14:35:00+00:00", "short"),
        ("2024-03-11T08:35:00+00:00", "long"),
        ("2026-01-20T07:03:00+00:00", "short"),
    ),
}


def frozen_wave2_tick_target_manifest() -> dict[str, object]:
    targets: dict[str, list[dict[str, str]]] = {}
    for symbol, rows in _ROWS.items():
        parsed: list[dict[str, str]] = []
        for minute_opened_at, side in rows:
            opened = datetime.fromisoformat(minute_opened_at).astimezone(UTC)
            if opened >= _EMBARGO or opened.second != 0 or opened.microsecond != 0:
                raise CTraderDemoLabProbeError("R5 Wave 2 target violates embargo/minute boundary")
            if side not in {"long", "short"}:
                raise CTraderDemoLabProbeError("R5 Wave 2 side is invalid")
            parsed.append({"minute_opened_at": opened.isoformat(timespec="seconds"), "side": side})
        targets[symbol] = parsed
    payload: dict[str, object] = {
        "schema": (
            "qore.trader_lab.turtle_soup_candidate_r5."
            "classic_tick_target_manifest.wave2.v1"
        ),
        "research_identity": "turtle-soup-candidate-r5",
        "selection_reason": "resolve-latent-CLASSIC-M1-INTRABAR_PATH_AMBIGUOUS-after-Wave1",
        "quote_type": "BID",
        "fresh_oos_embargo_start": _EMBARGO.isoformat(),
        "target_count": 20,
        "m1_data_unavailable_count": 0,
        "targets": targets,
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
        raise CTraderDemoLabProbeError("R5 Wave 2 target manifest digest mismatch")
    payload["manifest_digest_sha256"] = digest
    return payload
