"""QORE Native artifact expiry register: metadata ONLY, not permanent backup.

Reads GitHub Actions run and artifact metadata, no OHLC, no author trading rules.
Counts only exact expected symbol artifacts from successful completed run and
nonexpired artifacts. Declares SHA verification UNPROVEN unless restored and
hashed; workflow upload success alone is NOT archive permanence.
"""
from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from qore.infrastructure.trader_lab.qore_native_universe_33_source_registry_v1 import (
    M1_10Y, M5_10Y, universe,
)

IDENTITY = "QORE_NATIVE_DATA_ARCHIVE_EXPIRY_REGISTER_V1"
M5_NEW_RUN = 38193802541
M5_ORIGINAL_RUN = 35166210458
M1_ORIGINAL_RUN = 35548099334
M1_PILOT_RUN = 38262534602
M1_REMAINING_RUN = 38264253297
M1_PILOT = frozenset(("SP500", "XAGUSD", "NZDUSD"))
M1_REMAINING = frozenset(universe()) - M1_10Y - M1_PILOT
RUNS = (
    (M5_ORIGINAL_RUN, "M5_ORIGINAL_12", M5_10Y, "qore-cibo-market-atlas-10y-windowed-"),
    (M5_NEW_RUN, "M5_NEW_21", frozenset(universe()) - M5_10Y, "qore-native-icmarkets-10Y-provider-M5-"),
    (M1_ORIGINAL_RUN, "M1_ORIGINAL_9", M1_10Y, "qore-capitalizer-cibo-10y-native-m1-"),
    (M1_PILOT_RUN, "M1_PILOT_3", M1_PILOT, "qore-native-icmarkets-10Y-provider-M1-"),
    (M1_REMAINING_RUN, "M1_REMAINING_21", M1_REMAINING, "qore-native-icmarkets-10Y-provider-M1-"),
)


def _api(path: str, *, repo: str, token: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("INVALID_GITHUB_REPO_IDENTIFIER")
    if not token:
        raise ValueError("GITHUB_ACTIONS_READ_TOKEN_REQUIRED")
    request = Request(
        "https://api.github.com/repos/" + repo + "/" + path,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": IDENTITY,
        },
        method="GET",
    )
    with urlopen(request, timeout=35) as response:
        return json.load(response)


def _expired_at(value: str | None, now: datetime) -> bool:
    if not isinstance(value, str) or not value:
        return True
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return True
    return stamp.tzinfo is None or stamp <= now


def evaluate(
    run_data: dict[int, dict],
    artifacts_data: dict[int, list[dict]],
    *,
    now: datetime,
) -> dict:
    if now.tzinfo is None:
        raise ValueError("CLOCK_MUST_BE_TZ_AWARE")
    all_rows: list[dict] = []
    accepted = {"M5": set(), "M1": set()}
    for run_id, cohort, expected, prefix in RUNS:
        run = run_data[run_id]
        run_ok = (run.get("id") == run_id and
                  run.get("status") == "completed" and
                  run.get("conclusion") == "success")
        by_symbol: dict[str, list[dict]] = {s: [] for s in expected}
        for a in artifacts_data[run_id]:
            name = a.get("name", "")
            if not isinstance(name, str) or not name.startswith(prefix):
                continue
            suffix = name[len(prefix):]
            # Ambiguity guard: always match 'SYMBOL-' followed by Git SHA;
            # ignore aggregates, replays and unknown artifacts.
            match = re.fullmatch(r"([A-Z0-9]+)-([a-f0-9]{40})", suffix)
            if match and match.group(1) in expected:
                by_symbol[match.group(1)].append(a)
        for symbol in sorted(expected):
            hits = by_symbol[symbol]
            a = hits[0] if len(hits) == 1 else None
            sha_match = (
                a is not None and
                a["name"].endswith("-" + str(run.get("head_sha", "")))
            )
            retained = (len(hits) == 1 and sha_match and run_ok and
                        a.get("expired") is False and
                        not _expired_at(a.get("expires_at"), now) and
                        type(a.get("size_in_bytes")) is int and
                        a["size_in_bytes"] > 100)
            kind = cohort.split("_")[0]
            if retained:
                accepted[kind].add(symbol)
            all_rows.append({
                "timeframe": kind,
                "cohort": cohort,
                "symbol": symbol,
                "run_id": run_id,
                "run_success": run_ok,
                "matching_artifact_count": len(hits),
                "artifact_id": a.get("id") if a is not None else None,
                "artifact_bytes": a.get("size_in_bytes") if a is not None else None,
                "artifact_expires_at": a.get("expires_at") if a is not None else None,
                "github_artifact_retained_as_of_check": retained,
                "source_zip_sha256_verified": False,
                "permanent_storage_restore_proven": False,
                "status": "ACTIONS_TEMPORARY_ONLY" if retained else "MISSING_OR_IN_PROGRESS",
            })
    m5_expected = frozenset(universe())
    m1_expected = frozenset(universe())
    if set(accepted["M5"]) - m5_expected or set(accepted["M1"]) - m1_expected:
        raise AssertionError("SOURCE_ASSET_UNIVERSE_INCONSISTENT")
    dates = [r["artifact_expires_at"] for r in all_rows
             if r["github_artifact_retained_as_of_check"]]
    return {
        "identity": IDENTITY,
        "checked_at_utc": now.isoformat(),
        "source_type": "GITHUB_ACTIONS_METADATA_ONLY",
        "certification": "NOT_ECONOMIC_OOS_AND_NOT_DURABLE_BACKUP",
        "metadata_available": {
            "M5": len(accepted["M5"]), "M1": len(accepted["M1"]),
            "universe": len(m5_expected),
        },
        "m5_missing": sorted(m5_expected - accepted["M5"]),
        "m1_missing": sorted(m1_expected - accepted["M1"]),
        "nearest_expiry_utc": min(dates) if dates else None,
        "all_artifacts_restored_and_hashed": False,
        "all_artifacts_backed_up_permanently": False,
        "rows": all_rows,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GH_TOKEN", "")
    runs = {}
    artifacts = {}
    try:
        for run_id, _, _, _ in RUNS:
            runs[run_id] = _api(f"actions/runs/{run_id}", repo=repo, token=token)
            page = _api(
                f"actions/runs/{run_id}/artifacts?per_page=100",
                repo=repo, token=token,
            )
            if page.get("total_count", 0) > 100:
                raise ValueError("PAGINATED_ARTIFACT_LIST_REQUIRES_ADJUDICATION")
            artifacts[run_id] = page.get("artifacts", [])
        report = evaluate(runs, artifacts, now=datetime.now(UTC))
    except (ValueError, HTTPError, URLError, TimeoutError, KeyError) as exc:
        # Never dump token-bearing urllib exceptions or unknown URL payloads.
        print("ARCHIVE_REGISTER_SOURCE_METADATA_BLOCKED", type(exc).__name__)
        raise SystemExit(4) from None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("QORE_ARCHIVE_METADATA_STATUS", json.dumps({
        "available": report["metadata_available"],
        "m1_missing_count": len(report["m1_missing"]),
        "m5_missing_count": len(report["m5_missing"]),
        "nearest_expiry": report["nearest_expiry_utc"],
        "not_permanent": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
