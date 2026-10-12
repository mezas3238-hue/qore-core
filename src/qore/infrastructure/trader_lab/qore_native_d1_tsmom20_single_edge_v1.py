"""One frozen D1 TSMOM-20 panel experiment on ORIGINAL 33 M5 sources.

Not a production backtest. Uses a 1bp-per-side *assumed* turnover cost.
No tick fills/fees, no broker-equivalent contracts and no virgin holdout.
Never computes returns on / after 2024-09-17 (sealed existing holdout).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import subprocess
import tempfile
import zipfile
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

# Frozen universe, independent of later research branches not merged into G0.
UNIVERSE33 = (
    "NAS100", "SP500", "US30", "XAUUSD", "XAGUSD",
    "AUDUSD", "EURUSD", "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY",
    "AUDJPY", "AUDCAD", "AUDCHF", "AUDNZD", "CADCHF", "CADJPY", "CHFJPY",
    "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD",
    "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD",
    "NZDCAD", "NZDCHF", "NZDJPY",
)


def universe() -> tuple[str, ...]:
    if len(UNIVERSE33) != 33 or len(set(UNIVERSE33)) != 33:
        raise ValueError("FROZEN_33_DUPLICATE_OR_INCOMPLETE")
    return UNIVERSE33


IDENTITY = "QORE_NATIVE_D1_TSMOM20_SINGLE_FROZEN_PANEL_V1"
SIGNAL_DAYS = 20
BPS_PER_SIDE = 1.0
SIDE_COST = 0.0001
FIRST_EXEC_MINUTE_UTC = 10
MIN_M5_BARS_PER_DAY = 12
MIN_SIGNAL_TO_ORDER_SECONDS = 300
MAX_GAP_DAYS = 7
LOWER = date(2016, 9, 17)
DEV_START = date(2016, 9, 17)
VALIDATION_START = date(2022, 1, 1)
EMBARGO = date(2024, 9, 17)
SOURCE_END = date(2026, 9, 17)
DAYS_PER_YEAR = 252
PRODUCER12 = "ab782b8e9f890f86a2b6500070f0556b4b685e3d"
PRODUCER21 = "e0ca5a13c866a19d8505c68cffc473598984b340"
SOURCE_RUNS = (35166210458, 38193802541)
ORIGINAL12 = frozenset(("AUDJPY", "AUDUSD", "EURUSD", "GBPJPY", "GBPUSD",
                        "USDCAD", "USDJPY", "NAS100", "SP500", "US30",
                        "XAUUSD", "XAGUSD"))


def source_name(symbol: str) -> str:
    if symbol in ORIGINAL12:
        return f"qore-cibo-market-atlas-10y-windowed-{symbol}-{PRODUCER12}"
    return f"qore-native-icmarkets-10Y-provider-M5-{symbol}-{PRODUCER21}"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_checksum(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        pieces = line.split(maxsplit=1)
        if len(pieces) != 2 or len(pieces[0]) != 64:
            raise ValueError("INVALID_SOURCE_SHA_LEDGER")
        digest, name = pieces
        name = name.strip().removeprefix("*")
        if name in out or name.startswith("/") or ".." in Path(name).parts:
            raise ValueError("DUPLICATE_OR_UNSAFE_SHA_PATH")
        if any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("MALFORMED_SHA256")
        out[name] = digest
    return out


def valid_utc(s: str) -> datetime:
    t = datetime.fromisoformat(s)
    if t.tzinfo is None or t.utcoffset() != timedelta(0):
        raise ValueError("SOURCE_TIMESTAMP_NOT_UTC")
    return t.astimezone(UTC)


def get_artifact_register(repo: str, token: str) -> dict[str, dict]:
    """Use GH CLI with token, metadata only; check exact signed artifact names."""
    found = {}
    for run in SOURCE_RUNS:
        result = subprocess.check_output(
            ["gh", "api", f"repos/{repo}/actions/runs/{run}/artifacts",
             "-f", "per_page=100", "--method", "GET"],
            env={**os.environ, "GH_TOKEN": token}, text=True)
        info = json.loads(result)
        if info.get("total_count", 0) > 100:
            raise ValueError("SOURCE_ARTIFACT_LIST_PAGINATION_UNEXPECTED")
        for x in info["artifacts"]:
            if x["name"] in found:
                raise ValueError("SOURCE_ARTIFACT_DUPLICATE_NAME")
            found[x["name"]] = x
    register = {}
    for symbol in universe():
        name = source_name(symbol)
        x = found.get(name)
        if (not x or x.get("expired") is not False
                or x.get("size_in_bytes", 0) <= 0):
            raise ValueError("FROZEN_SOURCE_M5_ARTIFACT_UNAVAILABLE_" + symbol)
        register[symbol] = {
            "artifact_id": x["id"], "original_name": name,
            "original_run": 35166210458 if symbol in ORIGINAL12 else 38193802541,
        }
    if len(register) != 33:
        raise ValueError("FROZEN_SOURCE_UNIVERSE_NOT_33")
    return register


def _member_bytes(z: zipfile.ZipFile, name: str) -> bytes:
    if name not in z.namelist():
        raise ValueError("MISSING_SOURCE_MEMBER_" + name)
    return z.read(name)


def daily_from_zip(path: Path, symbol: str) -> tuple[list[dict], dict]:
    """Verify annual RAW hashes and M5 chronology, then create UTC daily bars.

    2024-09-17+ is SHA checked for source integrity but NEVER used in economics.
    No source price series or source raw rows are written to any output.
    """
    original = symbol in ORIGINAL12
    manifest_identity = ("CIBO_MARKET_ATLAS_10Y_CONSUMPTION_V1" if original
                         else "QORE_NATIVE_ICMARKETS_DEMO_UNIVERSE33_M5_10Y_NEW_CAPTURE_V1")
    raw_schema = ("qore.cibo_market_atlas.raw_m5.v1" if original
                  else "qore.native.icmarkets_demo_universe33_m5_10y.v1.raw")
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        if any(x.startswith("/") or ".." in Path(x).parts for x in names):
            raise ValueError("UNSAFE_ZIP_MEMBER_PATH")
        mani_name = "symbol-consumption-manifest.json"
        meta = json.loads(_member_bytes(z, mani_name))
        hashes = parse_checksum(_member_bytes(z, "MANIFEST_SHA256SUMS.txt").decode())
        if hashes.get(mani_name) != sha256_bytes(_member_bytes(z, mani_name)):
            raise ValueError("SOURCE_MANIFEST_SHA_MISMATCH")
        if (meta.get("identity") != manifest_identity
                or meta.get("canonical_symbol") != symbol
                or meta.get("target_start") != "2016-09-17T00:00:00+00:00"
                or meta.get("target_end_exclusive") != "2026-09-17T00:00:00+00:00"
                or meta.get("raw_integrity_status") != "CLEAN_PROVIDER_PAYLOAD"
                or [p["partition"] for p in meta.get("partitions", [])]
                   != [str(y) for y in range(2016, 2027)]):
            raise ValueError("FROZEN_M5_MANIFEST_IDENTITY_OR_SCOPE_DRIFT")
        allowed_provider = ("USTEC" if symbol == "NAS100" else
                            "US500" if symbol == "SP500" else symbol)
        if meta.get("provider_symbol") != allowed_provider:
            raise ValueError("SOURCE_PROVIDER_ALIAS_MISMATCH")

        daily = {}
        last_dt = None
        total_rows = 0
        for year in range(2016, 2027):
            raw = f"RAW_M5_LEDGER/{year}.jsonl"
            partsha = f"PARTITION_MANIFEST/{year}.sha256"
            if partsha not in hashes or hashes[partsha] != sha256_bytes(_member_bytes(z, partsha)):
                raise ValueError("SOURCE_YEAR_SHA_MANIFEST_DRIFT")
            annual_hashes = parse_checksum(_member_bytes(z, partsha).decode())
            expected_hash = annual_hashes.get(raw)
            if not expected_hash:
                raise ValueError("SOURCE_RAW_YEAR_SHA_MISSING")
            hasher = hashlib.sha256()
            with z.open(raw) as stream:
                for line in stream:
                    hasher.update(line)
                    # Strict quarantine of reserved period: source bytes SHA
                    # checked only. Do not parse price or compute economic return.
                    if year > 2024:
                        continue
                    row = json.loads(line)
                    stamp = valid_utc(row["opened_at"])
                    if stamp.year != year:
                        raise ValueError("SOURCE_YEAR_TIMESTAMP_DRIFT")
                    if stamp.date() >= EMBARGO:
                        continue
                    if (stamp.second or stamp.microsecond or stamp.minute % 5
                            or (last_dt is not None and stamp <= last_dt)):
                        raise ValueError("SOURCE_TIMESTAMP_ORDER_INVALID")
                    last_dt = stamp
                    if (row.get("canonical_symbol") != symbol
                            or row.get("identity") != manifest_identity
                            or row.get("schema") != raw_schema):
                        raise ValueError("RAW_M5_SOURCE_IDENTITY_INVALID")
                    op = row.get("open_relative")
                    cl = row.get("close_relative")
                    hi = row.get("high_relative")
                    lo = row.get("low_relative")
                    if (any(type(v) is not int or v <= 0 for v in (op, cl, hi, lo))
                            or lo > min(op, cl) or hi < max(op, cl)):
                        raise ValueError("M5_PRICE_GEOMETRY_INVALID")
                    total_rows += 1
                    day = stamp.date()
                    if day < LOWER or stamp.weekday() > 4:
                        continue
                    state = daily.setdefault(day, {
                        "date": day, "first_ts": None, "last_ts": None,
                        "entry_ts": None, "entry_open": None, "close": None,
                        "bars": 0,
                    })
                    state["bars"] += 1
                    state["last_ts"] = stamp
                    state["close"] = cl
                    if state["first_ts"] is None:
                        state["first_ts"] = stamp
                    if (state["entry_open"] is None
                            and stamp.hour * 60 + stamp.minute >= FIRST_EXEC_MINUTE_UTC):
                        state["entry_ts"] = stamp
                        state["entry_open"] = op
            if hasher.hexdigest() != expected_hash:
                raise ValueError("ORIGINAL_RAW_M5_YEAR_SHA_MISMATCH")
        selected = [x for x in daily.values()
                    if x["bars"] >= MIN_M5_BARS_PER_DAY and x["entry_open"] is not None]
        selected.sort(key=lambda x: x["date"])
        if len(selected) < 400:
            raise ValueError("SOURCE_NOT_ENOUGH_VALID_D1_SESSIONS")
        return selected, {
            "symbol": symbol, "source_sha_verified_11_annual_partitions": True,
            "preembargo_m5_rows": total_rows, "valid_daily_sessions": len(selected),
            "preembargo_last_daily_date": selected[-1]["date"].isoformat(),
            "original12": original,
        }


def period(day: date) -> str:
    return "DEV" if DEV_START <= day < VALIDATION_START else (
        "DIAG" if VALIDATION_START <= day < EMBARGO else "EMBARGO")


def market_experiment(symbol: str, bars: list[dict]) -> tuple[list[dict], dict]:
    """Signal calculated only from previous 20 *completed trading sessions*.

    Execution price = first eligible historical next UTC-day M5 open at 00:10+
    (or first available later). OHLC proxy, not a broker fill.
    Return is marked on exit day; two periods independently flat at edges.
    """
    dates = [b["date"] for b in bars]
    if dates != sorted(set(dates)):
        raise ValueError("D1_DATES_DUPLICATED_OR_UNSORTED")
    daily_pnl = []
    benchmark = {}
    for i in range(1, len(bars)):
        a, b = bars[i - 1], bars[i]
        if (b["date"] - a["date"]).days <= MAX_GAP_DAYS and period(a["date"]) == period(b["date"]):
            benchmark[b["date"]] = b["entry_open"] / a["entry_open"] - 1.
    for era in ("DEV", "DIAG"):
        prev_position = 0
        selected_indexes = []
        for t in range(SIGNAL_DAYS + 1, len(bars) - 1):
            openbar = bars[t]
            exitbar = bars[t + 1]
            prior = bars[t-1]
            ancestor = bars[t - 1 - SIGNAL_DAYS]
            if period(openbar["date"]) != era or period(exitbar["date"]) != era:
                continue
            if ((openbar["date"] - prior["date"]).days > MAX_GAP_DAYS
                    or (exitbar["date"] - openbar["date"]).days > MAX_GAP_DAYS
                    or (prior["last_ts"] + timedelta(minutes=5)
                        + timedelta(seconds=MIN_SIGNAL_TO_ORDER_SECONDS)
                        > openbar["entry_ts"])):
                continue
            # 20-session lookback: C[t-1] / C[t-21], known before entry_t.
            movement = prior["close"] - ancestor["close"]
            direction = (movement > 0) - (movement < 0)
            if direction == 0:
                continue
            raw_return = exitbar["entry_open"] / openbar["entry_open"] - 1.
            if not math.isfinite(raw_return) or abs(raw_return) > .45:
                raise ValueError("DAILY_OPEN_TO_OPEN_IMPLAUSIBLE_RETURN")
            # 1 bp per transaction side, reversal costs 2bp.
            cost = SIDE_COST * abs(direction - prev_position)
            row = {
                "symbol": symbol, "era": era, "mark_date": exitbar["date"],
                "strategy_daily_net_assumed": direction * raw_return - cost,
                "turnover_sides": abs(direction - prev_position),
                "raw_daily_underlying": raw_return, "position": direction,
            }
            selected_indexes.append(len(daily_pnl))
            daily_pnl.append(row)
            prev_position = direction
        if selected_indexes:
            # Ensure final liquidation 1 bp is reflected, independently by era.
            last = daily_pnl[selected_indexes[-1]]
            last["strategy_daily_net_assumed"] -= SIDE_COST * abs(prev_position)
            last["turnover_sides"] += abs(prev_position)
    if not daily_pnl:
        raise ValueError("D1_TSMOM_NO_TRADING_ROWS_" + symbol)
    return daily_pnl, benchmark


def performance(returns: list[float]) -> dict:
    if not returns or any(not math.isfinite(x) or x <= -1 for x in returns):
        raise ValueError("INVALID_PERFORMANCE_SERIES")
    nav = 1.
    peak = 1.
    worst = 0.
    for ret in returns:
        nav *= (1. + ret)
        peak = max(peak, nav)
        worst = min(worst, nav / peak - 1.)
    avg = statistics.mean(returns)
    std = statistics.stdev(returns) if len(returns) >= 2 else 0.
    return {
        "observations": len(returns),
        "cumulative_return": nav - 1.,
        "annualized_return_252": nav ** (DAYS_PER_YEAR / len(returns)) - 1.,
        "annualized_sharpe_252_rf0": (math.sqrt(DAYS_PER_YEAR) * avg / std
                                     if std > 0 else None),
        "max_drawdown": worst,
    }


def correlation(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 60:
        return None
    meanx, meany = statistics.mean(xs), statistics.mean(ys)
    dx = [x - meanx for x in xs]
    dy = [y - meany for y in ys]
    base = math.sqrt(sum(v*v for v in dx) * sum(v*v for v in dy))
    return sum(x*y for x,y in zip(dx,dy)) / base if base else None


def aggregate(rows: list[dict], proxy: dict[date, float], sources: list[dict]) -> dict:
    if len(sources) != 33 or {s["symbol"] for s in sources} != set(universe()):
        raise ValueError("INCOMPLETE_FROZEN_MARKET_SOURCES")
    byera = {}
    for era, begin, end in (
        ("DEV", date(2016, 9, 17), VALIDATION_START),
        ("DIAG", VALIDATION_START, EMBARGO),
    ):
        realized: dict[date, float] = defaultdict(float)
        per_market: dict[str, list[float]] = defaultdict(list)
        trades = 0
        turnover = 0
        for row in rows:
            if row["era"] != era:
                continue
            d = row["mark_date"]
            if not begin <= d < end:
                raise ValueError("PERIOD_RETURN_LEAK")
            # Capital fixed ex-ante at 1/33 per symbol, missing session = cash.
            realized[d] += row["strategy_daily_net_assumed"] / 33.
            per_market[row["symbol"]].append(row["strategy_daily_net_assumed"])
            trades += 1
            turnover += row["turnover_sides"]
        all_weekdays = []
        d = begin
        while d < end:
            if d.weekday() < 5:
                all_weekdays.append(d)
            d += timedelta(days=1)
        ret = [realized.get(d, 0.) for d in all_weekdays]
        benchmark_pairs = [(realized.get(d, 0.), proxy[d]) for d in all_weekdays if d in proxy]
        byera[era] = {
            **performance(ret),
            "dates": [begin.isoformat(), end.isoformat()],
            "active_mark_dates": len(realized),
            "market_day_positions": trades,
            "turnover_sides_total": turnover,
            "equal_weight_fixed_notional": "1/33",
            "annualization": 252,
            "correlation_to_SP500_CFD_open_proxy_NOT_SPX": correlation(
                [p[0] for p in benchmark_pairs], [p[1] for p in benchmark_pairs]),
            "SP500_CFD_matching_days": len(benchmark_pairs),
            "market_diagnostic_not_a_selection_rule": {
                s: performance(v) for s,v in sorted(per_market.items())
            },
        }
    return {
        "identity": IDENTITY,
        "status": "ONE_FROZEN_D1_TSMOM20_EXPLORATORY_COST_ASSUMPTION_NOT_BROKER_NET",
        "frozen_markets": 33,
        "source_m5_sha_verified_11_partitions_each": True,
        "signal_trading_days": SIGNAL_DAYS,
        "next_day_execution_UTC_not_before_minute": FIRST_EXEC_MINUTE_UTC,
        "min_signal_to_order_latency_seconds": MIN_SIGNAL_TO_ORDER_SECONDS,
        "round_trip_cost_bp_if_new_and_closed": 2 * BPS_PER_SIDE,
        "cost_bp_per_position_side_change": BPS_PER_SIDE,
        "performance": byera,
        "source_reports": sources,
        "holdout_start_utc": EMBARGO.isoformat(),
        "holdout_outcomes_calculated": False,
        "performance_is_real_broker_NET": False,
        "SPX_exact_index_correlation_available": False,
        "33_accounts_historically_homologated": False,
        "certified_traders": 0,
        "no_orders_or_production_touch": True,
    }


def run(workdir: Path, output: Path) -> dict:
    repo = os.environ.get("GITHUB_REPOSITORY", "mezas3238-hue/qore-core")
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise ValueError("READ_ONLY_GITHUB_ACTIONS_TOKEN_REQUIRED")
    register = get_artifact_register(repo, token)
    daily_rows, sources, benchmark = [], [], {}
    workdir.mkdir(parents=True, exist_ok=True)
    for symbol in sorted(universe()):
        info = register[symbol]
        archive = workdir / (symbol + ".zip")
        try:
            subprocess.run([
                "curl", "--fail", "--silent", "--show-error", "--location",
                "--retry", "2",
                "-H", f"Authorization: Bearer {token}",
                "-H", "Accept: application/vnd.github+json",
                f"https://api.github.com/repos/{repo}/actions/artifacts/{info['artifact_id']}/zip",
                "--output", str(archive)], check=True)
            sessions, source_report = daily_from_zip(archive, symbol)
            rows, index_series = market_experiment(symbol, sessions)
            source_report.update({
                "artifact_id": info["artifact_id"],
                "original_source_run": info["original_run"],
                "original_artifact_name": info["original_name"],
                "daily_strategy_rows": len(rows),
            })
            sources.append(source_report)
            daily_rows.extend(rows)
            if symbol == "SP500":
                benchmark = index_series
            print("TSMOM_D1_MARKET_PASS",symbol,source_report["valid_daily_sessions"],
                  len(rows), flush=True)
        finally:
            archive.unlink(missing_ok=True)
    if not benchmark:
        raise ValueError("SP500_PROXY_SOURCE_MISSING")
    report = aggregate(daily_rows, benchmark, sources)
    output.mkdir(parents=True, exist_ok=True)
    path = output / "D1_TSMOM20_FROZEN_33_MARKETS_COST1BP_SIDE.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    (output / "SHA256SUMS.txt").write_text(
        sha256_bytes(path.read_bytes()) + "  " + path.name + "\n")
    print("QORE_D1_TSMOM20_SOURCE33_COST_ASSUMPTION_EXPERIMENT_COMPLETE",
          json.dumps({k: {a: v for a,v in d.items() if a in (
              "annualized_sharpe_252_rf0", "annualized_return_252",
              "max_drawdown", "market_day_positions",
              "correlation_to_SP500_CFD_open_proxy_NOT_SPX")}
          for k,d in report["performance"].items()}, sort_keys=True))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workdir", type=Path)
    parser.add_argument("outdir", type=Path)
    args = parser.parse_args()
    run(args.workdir, args.outdir)


if __name__ == "__main__":
    main()
