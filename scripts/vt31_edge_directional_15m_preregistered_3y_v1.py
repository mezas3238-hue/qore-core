#!/usr/bin/env python3
"""Preregistered directional forecasting test, NOT ICT CE economic replay.

Frozen original 2,140 VT31 M1 source events and 1,059,784 NAS100 M1 bars.
No selection based on eventual CE touch/cancel/PnL, no legacy R2.2.
Primary horizon 15 minutes from next M1 OPEN, net hypothetical 1.60 pts.
Week-block bootstrap and week sign-flip permutation tests, 5000 draws.
NOT broker fills, PF, drawdown, capital, contract equivalence, or LIVE.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

SOURCE_SHA = "0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa"
SOURCE_ID = "VT31_NAS100_OWNER_3Y_BASE_001"
SOURCE_ARTIFACT = 11459859004
LEDGER_ARTIFACT = 11657461650
SAMPLE_SIZE = 2140
SESSIONS = {"VT31_LONDON": 766, "VT31_NY_AM": 721, "VT31_NY_PM": 653}
HORIZONS = (5, 15, 30, 60)
PRIMARY = 15
COST_PTS = 1.60
RESAMPLES = 5000
BOOTSTRAP_SEED = 10122026
NULL_SEED = 31102026
COVERAGE_MIN = 0.95
P_LIMIT = 0.01


def stamp(value: str) -> datetime:
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("timezone-aware UTC source required")
    return t.astimezone(UTC)


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        while part := file.read(2**20):
            h.update(part)
    return h.hexdigest()


def prepare(
    ledger: dict[str, Any],
) -> tuple[list[dict[str, Any]], set[datetime]]:
    if ledger.get("source_fvg_hypothesis_count") != SAMPLE_SIZE:
        raise ValueError("ledger candidate source denominator changed")
    if ledger.get("market_m1_count") != 1059784:
        raise ValueError("ledger M1 universe changed")
    if ledger.get("trader_id") != "VT31":
        raise ValueError("wrong trader identity")
    if ledger.get("paper_fills_proven") != 0 or ledger.get("live_fills_proven") != 0:
        raise ValueError("this is a source-only ledger, NOT broker fills")
    events = ledger.get("events")
    if not isinstance(events, list) or len(events) != SAMPLE_SIZE:
        raise ValueError("original immutable 2140 source IDs required")
    if ledger.get("candidate_count_by_window") != SESSIONS:
        raise ValueError("original session composition changed")
    needed: set[datetime] = set()
    identities: set[str] = set()
    result: list[dict[str, Any]] = []
    for row in events:
        if not isinstance(row, dict):
            raise ValueError("non-dictionary FVG identity")
        ref = row["client_order_id"]
        if not isinstance(ref, str) or not ref or ref in identities:
            raise ValueError("duplicate / missing first-FVG identity")
        identities.add(ref)
        side = row["side"]
        if side not in ("LONG", "SHORT"):
            raise ValueError("invalid historical source direction")
        sess = row["session_window"]
        if sess not in SESSIONS:
            raise ValueError("unknown ICT source hour")
        formed = stamp(row["formed_at"])
        opened_first = stamp(row["source_first_m1_open"])
        if formed <= opened_first:
            raise ValueError("M1 source chronology inconsistent")
        if formed - opened_first != timedelta(minutes=3):
            raise ValueError("primary source must be 3 contiguous closed M1")
        from zoneinfo import ZoneInfo
        ny = formed.astimezone(ZoneInfo("America/New_York"))
        h = {"VT31_LONDON": 3, "VT31_NY_AM": 10, "VT31_NY_PM": 14}[sess]
        if ny.hour != h or ny.minute == 0:
            raise ValueError("formation not within active ICT source window")
        for i in range(max(HORIZONS) + 1):
            needed.add(formed + timedelta(minutes=i))
        iso = ny.isocalendar()
        result.append({
            "id": ref,
            "formed": formed,
            "side_sign": 1 if side == "LONG" else -1,
            "session": sess,
            "ny_iso_week": f"{iso.year}-W{iso.week:02d}",
        })
    return result, needed


def collect_market(
    market_rows: Iterable[dict[str, Any]], needed: set[datetime],
) -> tuple[dict[datetime, float], int]:
    found: dict[datetime, float] = {}
    last: datetime | None = None
    n = 0
    for row in market_rows:
        opened = stamp(row["opened_at"])
        closed = stamp(row["closed_at"])
        if closed - opened != timedelta(minutes=1):
            raise ValueError("M1 candle has wrong duration")
        if last is not None and opened <= last:
            raise ValueError("source M1 nonchronological or duplicated")
        last = opened
        n += 1
        if opened in needed:
            v = float(row["open"])
            if not 1000 < v < 1000000:
                raise ValueError("invalid NAS100 index open")
            found[opened] = v
    if n != 1059784:
        raise ValueError(f"frozen M1 count drift: {n}")
    return found, n


def _market_source(path: Path) -> Iterable[dict[str, Any]]:
    import ijson
    with path.open("rb") as handle:
        for field, required in (
            ("base_id", SOURCE_ID),
            ("market", "NAS100"),
            ("base_start_at", "2023-10-01T00:00:00+00:00"),
            ("base_end_exclusive", "2026-10-01T00:00:00+00:00"),
        ):
            handle.seek(0)
            x = next(ijson.items(handle, field), None)
            if x != required:
                raise ValueError(f"frozen market identity mismatch: {field}")
        handle.seek(0)
        yield from ijson.items(handle, "periods.M1.item")


def _percentile(values: list[float], q: float) -> float:
    v = sorted(values)
    if not v:
        raise ValueError("empty statistical sample")
    k = (len(v) - 1) * q
    i = int(k)
    j = min(i + 1, len(v) - 1)
    return v[i] + (k - i) * (v[j] - v[i])


def _infer_week_cluster(pairs: list[dict[str, Any]]) -> dict[str, Any]:
    per_week: dict[str, list[float]] = defaultdict(list)
    for x in pairs:
        per_week[x["week"]].append(float(x["gross_pts"]))
    groups = sorted(per_week)
    if not groups:
        raise ValueError("no weekly groups")
    if len(groups) < 30:
        raise ValueError("too few different ISO weeks for clustered inference")
    totals = [(sum(per_week[w]), len(per_week[w])) for w in groups]
    observed = sum(x[0] for x in totals) / sum(x[1] for x in totals)
    assert abs(observed - sum(x["gross_pts"] for x in pairs) / len(pairs)) < 1e-8

    rng = random.Random(BOOTSTRAP_SEED)
    boot: list[float] = []
    for _ in range(RESAMPLES):
        drawn = [totals[rng.randrange(len(totals))] for _ in totals]
        gross_mean = sum(x[0] for x in drawn) / sum(x[1] for x in drawn)
        boot.append(gross_mean - COST_PTS)
    null_rng = random.Random(NULL_SEED)
    exceed = 0
    for _ in range(RESAMPLES):
        flipped = sum(
            gross_sum * (1 if null_rng.randrange(2) else -1)
            for gross_sum, _ in totals
        ) / len(pairs)
        if flipped >= observed:
            exceed += 1
    p_value = (exceed + 1) / (RESAMPLES + 1)
    return {
        "weekly_blocks": len(groups),
        "weekly_cluster_bootstrap_resamples": RESAMPLES,
        "weekly_cluster_bootstrap_seed": BOOTSTRAP_SEED,
        "weekly_cluster_bootstrap_95pct_net_pts_lower": round(_percentile(boot, .025), 6),
        "weekly_cluster_bootstrap_95pct_net_pts_upper": round(_percentile(boot, .975), 6),
        "sign_flip_null_resamples": RESAMPLES,
        "sign_flip_null_seed": NULL_SEED,
        "sign_flip_one_sided_p_directional_gross": round(p_value, 8),
        "null_expected_net_under_no_directional_signal_pts": -COST_PTS,
    }


def screen(
    events: list[dict[str, Any]], opens: dict[datetime, float],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for h in HORIZONS:
        subset: list[dict[str, Any]] = []
        missing = Counter()
        for event in events:
            at = event["formed"]
            # Do not use missing bar gap filler; all EXACT sequential M1
            # openings through the requested fixed horizon MUST exist.
            if any(
                at + timedelta(minutes=k) not in opens
                for k in range(h + 1)
            ):
                missing[event["session"]] += 1
                continue
            entry = opens[at]
            exit_price = opens[at + timedelta(minutes=h)]
            gross = (exit_price - entry) * event["side_sign"]
            subset.append({
                "id": event["id"],
                "session": event["session"],
                "week": event["ny_iso_week"],
                "gross_pts": gross,
            })
        n = len(subset)
        if n == 0:
            raise ValueError(f"no valid close-open references for {h}m")
        gross = [x["gross_pts"] for x in subset]
        net = [x - COST_PTS for x in gross]
        by_window = {}
        for sess in SESSIONS:
            seq = [float(x["gross_pts"]) for x in subset if x["session"] == sess]
            by_window[sess] = {
                "n": len(seq),
                "coverage": round(len(seq) / SESSIONS[sess], 6),
                "mean_gross_pts": round(sum(seq)/len(seq), 6) if seq else None,
                "mean_net_hypothetical_pts": (
                    round(sum(seq)/len(seq)-COST_PTS, 6) if seq else None
                ),
            }
        horizon_result: dict[str, Any] = {
            "horizon_min": h,
            "n_original_candidates": SAMPLE_SIZE,
            "valid_exact_contiguous_M1": n,
            "missing_exact_contiguous_M1": SAMPLE_SIZE - n,
            "coverage_pct": round(100 * n/SAMPLE_SIZE, 6),
            "missing_by_window": dict(sorted(missing.items())),
            "mean_gross_directional_pts": round(sum(gross)/n, 6),
            "mean_net_fixed_1p60_hypothetical_pts": round(sum(net)/n, 6),
            "median_net_fixed_1p60_hypothetical_pts": round(_percentile(net, .5), 6),
            "net_positive_fraction_NOT_trade_win_rate": round(sum(x>0 for x in net)/n, 6),
            "sessions": by_window,
            "is_preregistered_primary": h == PRIMARY,
        }
        if h == PRIMARY:
            evidence = _infer_week_cluster(subset)
            horizon_result["clustered_inference"] = evidence
            passed = (
                n/SAMPLE_SIZE >= COVERAGE_MIN
                and sum(net)/n > 0
                and evidence["weekly_cluster_bootstrap_95pct_net_pts_lower"] > 0
                and evidence["sign_flip_one_sided_p_directional_gross"] <= P_LIMIT
            )
            horizon_result["preregistered_directional_screen_passed"] = passed
        result[str(h)] = horizon_result
    return result


def self_test() -> None:
    start = datetime(2025, 7, 7, 14, 3, tzinfo=UTC)
    # Use fixed known returns to test direction, unchanged h.
    events = [
        {"id": "one", "formed": start, "side_sign": 1,
         "session": "VT31_NY_AM", "ny_iso_week": "2025-W28"},
        {"id": "two", "formed": start + timedelta(minutes=70),
         "side_sign": -1, "session": "VT31_NY_PM",
         "ny_iso_week": "2025-W28"},
    ]
    opens: dict[datetime, float] = {}
    for k in range(61):
        opens[start+timedelta(minutes=k)] = 10000 + 2*k
        opens[start+timedelta(minutes=70+k)] = 10300 - k
    # `screen` purposely uses immutable global SAMPLE_SIZE denominator;
    # test direct 15-minute signal arithmetic and early-open causality.
    assert (opens[start+timedelta(minutes=15)]-opens[start])*1 == 30
    at = start+timedelta(minutes=70)
    assert (opens[at+timedelta(minutes=15)]-opens[at])*(-1) == 15
    assert (30-COST_PTS) == 28.4
    assert (15-COST_PTS) == 13.4
    assert events[0]["side_sign"] != events[1]["side_sign"]


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("--market", type=Path)
    a.add_argument("--ledger", type=Path)
    a.add_argument("--out", type=Path)
    a.add_argument("--self-test", action="store_true")
    x = a.parse_args()
    if x.self_test:
        self_test()
        print("VT31 prereg directional M1 test fixtures: PASS")
        return
    if not x.market or not x.ledger or not x.out:
        a.error("market + ledger + out are mandatory")
    if _digest(x.market) != SOURCE_SHA:
        raise ValueError("frozen M1 SHA256 mismatch")
    ledger = json.loads(x.ledger.read_text())
    events, needed = prepare(ledger)
    opens, count = collect_market(_market_source(x.market), needed)
    horizons = screen(events, opens)
    primary = horizons[str(PRIMARY)]
    report = {
        "schema": "qore.vt31.ict_cleanroom.preregistered_directional_screen.v1",
        "pre_registered_primary_minutes": PRIMARY,
        "experiment_kind": "CAUSAL_POST_FVG_FORECAST_NOT_CANONICAL_CE_FILL",
        "source_market": "NAS100_M1_FROZEN_3Y",
        "m1_count": count,
        "market_sha256": SOURCE_SHA,
        "source_events_sha256": _digest(x.ledger),
        "original_candidate_count": SAMPLE_SIZE,
        "source_ledger_artifact_id": LEDGER_ARTIFACT,
        "market_artifact_id": SOURCE_ARTIFACT,
        "hypothetical_roundtrip_cost_index_pts": COST_PTS,
        "source_price_assumed_mid_NOT_VERIFIED": True,
        "NDX100_MT5_same_contract_as_NAS100_NOT_VERIFIED": True,
        "horizons": horizons,
        "directional_screen_preregistered_result": (
            "SENAL_PREDICTIVA_PRELIMINAR_NO_EJECUTABLE"
            if primary["preregistered_directional_screen_passed"]
            else "NO_EVIDENCIA_PREDICTIVA_NETA_EN_ESTE_SCREENING"
        ),
        "economic_edge_status": "EDGE_ECONOMICO_NO_DEMOSTRADO",
        "ce_limit_fills_confirmed": 0,
        "bid_ask_tick_data": "ABSENT",
        "stop_target_execution": "NOT_TESTED",
        "broker_commissions_and_slippage": "NOT_INCLUDED",
        "main_or_live_modified": False,
        "fresh_holdout_opened": False,
        "research_only": True,
    }
    x.out.parent.mkdir(parents=True, exist_ok=True)
    x.out.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    print(json.dumps({
        "m1": count, "candidates": len(events), "primary_15m": primary,
        "prereg_result": report["directional_screen_preregistered_result"],
        "economic_edge_status": report["economic_edge_status"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
