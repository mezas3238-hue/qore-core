"""Public-source eligibility preflight: no credentials, payment, or market prices.

Checks CME DataMine documented authentication boundary and six GitHub public
OHLCV folders to determine whether any *native* 2012-2024 delivery-month candles
can currently be proved free. Inventories file names only. NO PnL or candles.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOTS = ("CL", "NG", "GC", "HG", "ZC", "ZS")
GH_BASE = "https://api.github.com/repos/axb0306/cme-futures-ohlc/contents"
CME_NO_CREDS = (
    "https://datamine.new.cmegroup.com/cme/api/v2/download"
    "?fid=20250625-EOD_XCBT_C_FUT_0_ETH_P&headers_only=true"
)
MAX_BODY = 120_000


def safe_get_json(url: str) -> dict[str, Any] | list[Any]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "QORE-Futures-A-Source-Metadata-Audit/1.0",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        data = response.read(MAX_BODY + 1)
    if len(data) > MAX_BODY:
        raise ValueError("EXCEEDS_METADATA_LIMIT")
    ans: dict[str, Any] | list[Any] = json.loads(data)
    return ans


def inspect_public_ohlcv_files(root: str) -> dict[str, Any]:
    out: dict[str, Any] = {
        "root": root,
        "public_repo": "axb0306/cme-futures-ohlc",
        "feed": "TopstepX_from_README_NOT_CME_DIRECT",
        "status": "UNVERIFIED",
        "dated_daily_files": [],
        "dated_1min_files": [],
        "oldest_daily_start": None,
        "newest_daily_end": None,
        "covers_mission_2012_2024": False,
        "contract_expiration_per_row_verified": False,
        "historical_reuse_license_verified": False,
        "market_prices_downloaded": False,
    }
    try:
        rows = safe_get_json(f"{GH_BASE}/{root}")
        if not isinstance(rows, list):
            raise ValueError("GH_DIRECTORY_IS_NOT_LIST")
        for item in rows:
            if not isinstance(item, dict):
                continue
            filename = item.get("name", "")
            if not isinstance(filename, str):
                continue
            match = re.fullmatch(
                re.escape(root)
                + r"_(daily|1min)_(20\d{6})_(20\d{6})\.csv",
                filename,
            )
            if match is None:
                continue
            period = match.group(1)
            bounds = (match.group(2), match.group(3))
            name_key = "dated_daily_files" if period == "daily" else "dated_1min_files"
            out[name_key].append(filename)
            if period == "daily":
                if out["oldest_daily_start"] is None or bounds[0] < out["oldest_daily_start"]:
                    out["oldest_daily_start"] = bounds[0]
                if out["newest_daily_end"] is None or bounds[1] > out["newest_daily_end"]:
                    out["newest_daily_end"] = bounds[1]
        starts = [
            x.split("_")[-2] for x in out["dated_daily_files"]
        ]
        ends = [
            x.split("_")[-1].split(".")[0] for x in out["dated_daily_files"]
        ]
        out["covers_mission_2012_2024"] = bool(
            starts and ends and min(starts) <= "20120101"
            and max(ends) >= "20240916"
        )
        out["status"] = "FILE_INVENTORY_OBSERVED"
    except (OSError, ValueError, urllib.error.HTTPError) as exc:
        out["status"] = "NETWORK_OR_SCHEMA_ERROR"
        out["error_type"] = type(exc).__name__
    return out


def inspect_cme_unauthenticated() -> dict[str, Any]:
    """At most ONE public metadata-only request; never attempt to bypass login."""
    out: dict[str, Any] = {
        "provider": "CME_Datamine",
        "api_documentation": "https://www.cmegroup.com/datamine/datamine-api.html",
        "free_midnight_settlement_notice": (
            "https://www.cmegroup.com/notices/electronic-trading/2023/11/20231120.html"
        ),
        "end_of_market_summary_documented_as_paid": True,
        "no_auth_key_supplied": True,
        "body_content_downloaded": False,
        "data_rights_verified": False,
        "2012_2024_history_free_confirmed": False,
    }
    req = urllib.request.Request(
        CME_NO_CREDS,
        headers={"User-Agent": "QORE-Futures-A-Access-Check/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            out["http_status"] = response.status
            # No content read, no binary stored or interpreted.
    except urllib.error.HTTPError as exc:
        out["http_status"] = exc.code
        out["access_state"] = "REQUIRES_ACCESS_OR_REQUEST_REJECTED"
    except (OSError, ValueError) as exc:
        out["http_status"] = None
        out["access_state"] = "NETWORK_BLOCKED"
        out["error_type"] = type(exc).__name__
    return out


def main() -> None:
    src = [inspect_public_ohlcv_files(root) for root in ROOTS]
    cme = inspect_cme_unauthenticated()
    report = {
        "identity": "QORE_FUTURES_A_FREE_CME_GITHUB_ACCESS_20261013",
        "snapshot_utc": datetime.now(UTC).isoformat(),
        "github_root_inventory": src,
        "cme": cme,
        "budget_usd": 0,
        "new_trader_certified": 0,
        "2012_2024_all_native_ohlcv_6x2_certified": False,
        "license_entitlement_verified": False,
        "real_futures_data_or_prices_downloaded": False,
        "backtest_or_PnL_calculated": False,
        "source_ready_for_prereg": False,
        "fx_holdout_consumed": False,
    }
    Path("qore_futures_a_zero_budget_cme_public_source_metadata.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("GITHUB_PUBLIC_OHLCV_METADATA", json.dumps(src, sort_keys=True))
    print("CME_NO_CREDS_ACCESS", json.dumps(cme, sort_keys=True))
    print("NO_LICENSE_NO_TRADABLE_6ROOTS_NO_PNL")


if __name__ == "__main__":
    main()
