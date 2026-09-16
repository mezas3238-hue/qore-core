"""Freeze bounded consumed follow-up windows for non-executable first M1 touches.

The source set is mechanically restricted to consumed ambiguity rows classified
`no-executable-fill-in-source-minute` by the immutable BID/ASK resolver. The
pending limit remains eligible only until 11:00 America/New_York, matching the
frozen VT-31 simulator. No new setup is discovered and no fresh date is opened.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")
_EXPECTED_SOURCE_STATUS_COUNT = 59


def _canonical_id(row: dict[str, Any]) -> str:
    material = json.dumps(row, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(material.encode()).hexdigest()[:24]


def build(source_manifest_path: Path, resolution_path: Path, output_path: Path) -> dict[str, Any]:
    source = json.loads(source_manifest_path.read_text())
    resolution = json.loads(resolution_path.read_text())
    if source.get("research_only") is not True or source.get("opens_new_holdout") is not False:
        raise ValueError("source manifest governance guard failed")
    if resolution.get("research_only") is not True or resolution.get("opens_new_holdout") is not False:
        raise ValueError("resolution governance guard failed")
    source_rows = source.get("windows")
    resolution_rows = resolution.get("results")
    if not isinstance(source_rows, list) or len(source_rows) != 437:
        raise ValueError("source manifest must contain 437 consumed windows")
    if not isinstance(resolution_rows, list) or len(resolution_rows) != 437:
        raise ValueError("resolution must contain 437 consumed rows")
    by_id = {row["window_id"]: row for row in source_rows if isinstance(row, dict)}
    selected = [
        row for row in resolution_rows
        if isinstance(row, dict) and row.get("status") == "no-executable-fill-in-source-minute"
    ]
    if len(selected) != _EXPECTED_SOURCE_STATUS_COUNT:
        raise ValueError(f"no-fill source count changed: {len(selected)}")

    windows: list[dict[str, Any]] = []
    session_expired: list[dict[str, Any]] = []
    for resolved in selected:
        parent_id = resolved.get("window_id")
        if not isinstance(parent_id, str) or parent_id not in by_id:
            raise ValueError("resolved row is missing source identity")
        original = by_id[parent_id]
        source_close = original.get("tick_window_close_ms")
        if type(source_close) is not int:
            raise ValueError("source close boundary is malformed")
        source_open_dt = datetime.fromtimestamp(original["tick_window_open_ms"] / 1000, tz=UTC)
        local_day = source_open_dt.astimezone(NY).date()
        pending_end = datetime.combine(local_day, time(11, 0), tzinfo=NY).astimezone(UTC)
        follow_open_ms = source_close + 1
        follow_close_ms = int(pending_end.timestamp() * 1000) - 1
        if follow_open_ms > follow_close_ms:
            session_expired.append(
                {
                    "parent_window_id": parent_id,
                    "partition": original["partition"],
                    "market": original["market"],
                    "ny_date": original["ny_date"],
                    "side": original["side"],
                    "status": "pending-entry-window-expired-no-fill",
                }
            )
            continue
        row = {
            "parent_window_id": parent_id,
            "partition": original["partition"],
            "market": original["market"],
            "provider": original["provider"],
            "ny_date": original["ny_date"],
            "side": original["side"],
            "entry": original["entry"],
            "initial_stop": original["initial_stop"],
            "fixed_2r_target": original["fixed_2r_target"],
            "tick_window_open_ms": follow_open_ms,
            "tick_window_close_ms": follow_close_ms,
            "followup_reason": "first-m1-touch-not-executable-pending-limit-through-11-ny",
        }
        row["window_id"] = _canonical_id(row)
        windows.append(row)

    windows.sort(key=lambda row: (row["market"], row["tick_window_open_ms"], row["window_id"]))
    if len(windows) + len(session_expired) != _EXPECTED_SOURCE_STATUS_COUNT:
        raise AssertionError("follow-up partition lost consumed source rows")
    if len({row["window_id"] for row in windows}) != len(windows):
        raise AssertionError("follow-up ids must be unique")
    payload: dict[str, Any] = {
        "schema": "qore.vt31.consumed_no_executable_fill_followup_manifest.v1",
        "research_only": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_R9_NOT_CERTIFIED",
        "source_resolution_status": "no-executable-fill-in-source-minute",
        "source_resolution_count": _EXPECTED_SOURCE_STATUS_COUNT,
        "pending_entry_cutoff": "11:00:00 America/New_York",
        "windows": windows,
        "session_expired_no_fill": session_expired,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    output_path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-manifest", required=True, type=Path)
    parser.add_argument("--resolution", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = build(args.source_manifest, args.resolution, args.output)
    print(json.dumps({"followup_windows": len(payload["windows"]), "session_expired_no_fill": len(payload["session_expired_no_fill"])}, sort_keys=True))


if __name__ == "__main__":
    main()
