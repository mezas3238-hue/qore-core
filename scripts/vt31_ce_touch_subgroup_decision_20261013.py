#!/usr/bin/env python3
"""VT31 P0 quick post-hoc diagnostic; NOT new V1, economic replay or fill model.

Original 2140 old-source FVGs, split by later M1 OHLC CE-overlap WHILE valid.
Primary 15m directional price change remains anchored at next open after FVG C3.
Post-touch 15m direction is a separate descriptive horizon, never a CE limit fill.
Samples chosen by a future price path are NOT causal filters or a confirmation test.
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

MARKET_SHA256 = "0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa"
MARKET_ARTIFACT = 11459859004
LEDGER_ARTIFACT = 11657461650
TOTAL = 2140
MARKET_TOTAL = 1059784
PRIMARY_MINUTES = 15
RESAMPLES = 2000
SEED = 13102026


def stamp(v: str) -> datetime:
    t = datetime.fromisoformat(v.replace("Z", "+00:00"))
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("timezone-less fact prohibited")
    return t.astimezone(UTC)


def checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(2**20):
            h.update(chunk)
    return h.hexdigest()


def events_from_original(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    if (
        ledger.get("source_fvg_hypothesis_count") != TOTAL
        or ledger.get("market_m1_count") != MARKET_TOTAL
        or ledger.get("trader_id") != "VT31"
        or ledger.get("paper_fills_proven") != 0
        or ledger.get("live_fills_proven") != 0
    ):
        raise ValueError("original 2140 cleanroom ledger identity/fill contract broken")
    rows = ledger.get("events")
    if not isinstance(rows, list) or len(rows) != TOTAL:
        raise ValueError("source-only original 2140 event identities required")
    observed: set[str] = set()
    out: list[dict[str, Any]] = []
    for r in rows:
        ident = r["client_order_id"]
        if not isinstance(ident, str) or ident in observed:
            raise ValueError("invalid/duplicate original event identity")
        observed.add(ident)
        formed = stamp(r["formed_at"])
        if formed - stamp(r["source_first_m1_open"]) != timedelta(minutes=3):
            raise ValueError("original FVG three-bar source chronology broken")
        side = {"LONG": 1, "SHORT": -1}.get(r["side"])
        if side is None:
            raise ValueError("invalid direction")
        touched = r["m1_touch_observed_at_not_fill"]
        touch = stamp(touched) if touched else None
        if touch is not None and touch <= formed:
            raise ValueError("CE price overlap precedes formed FVG")
        assert r["broker_execution_ack"] is None
        assert r["paper_fill_count"] == r["live_fill_count"] == 0
        out.append({
            "id": ident,
            "formed": formed,
            "touch": touch,
            "side": side,
            "session": r["session_window"],
            "week": f"{formed.isocalendar().year}-W{formed.isocalendar().week:02d}",
            "same_bar_revocation_overlap": (
                r["m1_ce_overlap_same_m1_as_source_revocation"] is not None
            ),
            "ambiguous_path": r["m1_ambiguous_price_path_at"] is not None,
            "final_status": r["final_source_phase"],
            "ce": float(r["m1_ce_research_limit"]),
            "dol": float(r["draw_target"]),
        })
    return out


def needed_opens(events: list[dict[str, Any]]) -> set[datetime]:
    out = set()
    for e in events:
        for base in (e["formed"], e["touch"]):
            if base is not None:
                for minute in range(PRIMARY_MINUTES + 1):
                    out.add(base + timedelta(minutes=minute))
    return out


def collect_opens(
    rows: Iterable[dict[str, Any]], needed: set[datetime],
    expected_n: int = MARKET_TOTAL,
) -> dict[datetime, float]:
    result = {}
    previous = None
    count = 0
    for row in rows:
        t = stamp(row["opened_at"])
        if stamp(row["closed_at"]) - t != timedelta(minutes=1):
            raise ValueError("not M1")
        if previous is not None and t <= previous:
            raise ValueError("duplicate or out-of-order M1")
        previous = t
        count += 1
        if t in needed:
            v = float(row["open"])
            if not 1000 < v < 1_000_000:
                raise ValueError("invalid NAS100 original M1 open")
            result[t] = v
    if count != expected_n:
        raise ValueError("source M1 count drift")
    return result


def market_rows(path: Path) -> Iterable[dict[str, Any]]:
    import ijson
    with path.open("rb") as handle:
        for field, expected in (
            ("base_id", "VT31_NAS100_OWNER_3Y_BASE_001"),
            ("market", "NAS100"),
            ("base_start_at", "2023-10-01T00:00:00+00:00"),
            ("base_end_exclusive", "2026-10-01T00:00:00+00:00"),
        ):
            handle.seek(0)
            if next(ijson.items(handle, field), None) != expected:
                raise ValueError(f"market provenance drift: {field}")
        handle.seek(0)
        yield from ijson.items(handle, "periods.M1.item")


def signed_return(
    event: dict[str, Any], base: datetime | None,
    opens: dict[datetime, float],
) -> float | None:
    if base is None:
        return None
    for step in range(PRIMARY_MINUTES + 1):
        if base + timedelta(minutes=step) not in opens:
            return None
    return (opens[base + timedelta(minutes=PRIMARY_MINUTES)] - opens[base]) * event["side"]


def _quantile(v: list[float], q: float) -> float:
    values = sorted(v)
    index = (len(values) - 1) * q
    low = int(index)
    return values[low] + (values[min(low + 1, len(values) - 1)] - values[low]) * (
        index - low
    )


def summarize(values: list[dict[str, Any]], seed: int) -> dict[str, Any]:
    if not values:
        return {"n": 0, "mean_gross_pts": None, "weekly_boot_ci95": None}
    mean = sum(x["pts"] for x in values) / len(values)
    per_week: dict[str, list[float]] = defaultdict(list)
    for x in values:
        per_week[x["week"]].append(x["pts"])
    clusters = [(sum(arr), len(arr)) for arr in per_week.values()]
    rng = random.Random(seed)
    bootstrap = []
    for _ in range(RESAMPLES):
        selected = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        bootstrap.append(sum(x for x, _ in selected) / sum(n for _, n in selected))
    return {
        "n": len(values),
        "mean_gross_pts": round(mean, 6),
        "positive_fraction_not_win_rate": round(
            sum(x["pts"] > 0 for x in values) / len(values), 6
        ),
        "weekly_blocks": len(clusters),
        "weekly_boot_ci95": [
            round(_quantile(bootstrap, .025), 6),
            round(_quantile(bootstrap, .975), 6),
        ],
        "not_independent_holdout": True,
        "posthoc_subgroup_not_confirmatory": True,
    }


def adjudicate(events: list[dict[str, Any]], opens: dict[datetime, float]) -> dict[str, Any]:
    if len(events) != TOTAL:
        raise ValueError("cannot run economic diagnostic on changed population")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    missing = Counter()
    for e in events:
        signal = signed_return(e, e["formed"], opens)
        if signal is None:
            missing["signal"] += 1
        else:
            entry = {"pts": signal, "week": e["week"]}
            groups["all_signal"].append(entry)
            groups["touch_signal" if e["touch"] is not None else "no_touch_signal"].append(
                entry
            )
        if e["touch"] is not None:
            follow = signed_return(e, e["touch"], opens)
            if follow is None:
                missing["post_touch"] += 1
            else:
                groups["touch_next_open_post_contact"].append(
                    {"pts": follow, "week": e["week"]}
                )
    all_ = summarize(groups["all_signal"], SEED)
    if all_["n"] != TOTAL or abs(all_["mean_gross_pts"] - (-1.919664)) > 0.00002:
        raise ValueError("old prereg primary 15m return cannot be reproduced")
    touch = summarize(groups["touch_signal"], SEED + 1)
    no_touch = summarize(groups["no_touch_signal"], SEED + 2)
    post = summarize(groups["touch_next_open_post_contact"], SEED + 3)
    if touch["n"] + no_touch["n"] != TOTAL:
        raise ValueError("missing partition of original cohort")
    touch_count = sum(e["touch"] is not None for e in events)
    if touch_count != touch["n"] or post["n"] != touch_count:
        raise ValueError("CE touch follow-up history missing")
    def weak_positive(result: dict[str, Any]) -> bool:
        return (
            result["n"] >= 30
            and result["mean_gross_pts"] > 0
            and result["weekly_boot_ci95"][0] > 0
        )

    return {
        "schema": "qore.vt31.rapid_ce_touch_subgroup_research.v1",
        "old_candidate_count_NOT_V1": TOTAL,
        "m1_price_overlap_while_source_eligible_NOT_FILL": touch_count,
        "without_eligible_m1_ce_overlap": TOTAL - touch_count,
        "same_m1_as_revocation_price_overlap_UNRESOLVED_not_additive": sum(
            e["same_bar_revocation_overlap"] for e in events
        ),
        "original_ambiguous_path_not_additive": sum(
            e["ambiguous_path"] for e in events
        ),
        "coverage_missing": dict(missing),
        "all_signals_original_15m_from_next_open": all_,
        "later_ce_touch_signals_original_15m_from_next_open": touch,
        "no_later_eligible_ce_touch_signals_original_15m_from_next_open": no_touch,
        "later_ce_touch_cohort_new_15m_after_observed_m1_close": post,
        "latter_two_are_selected_on_future_CE_touch": True,
        "CE_then_target_before_stop_not_identifiable_from_M1": True,
        "target_first_subgroup_would_condition_on_winner_outcome": True,
        "gross_directional_results_NOT_CE_limit_trade_returns": True,
        "new_G3_V1_cohort_tested": False,
        "broker_bid_ask_or_acks_present": False,
        "economic_pf_drawdown_proven": False,
        "G3_doc_sha": "a446afa17ed6e411b8f0b6fc182b103a78959a97",
        "G3_code_sha": "78d4cdac0e09d1a6eef37b99c505ffc5098031fc",
        "G3_current_state": "PENDING_DUAL_SIGNATURE",
        "scientific_directional_ce_touch_positive_cluster_CI": weak_positive(touch),
        "scientific_post_touch_positive_cluster_CI": weak_positive(post),
        "go_live_or_certify": False,
        "further_unapproved_G6_spending": "NO_GO",
        "one_final_V1_test_only_if_signed_and_same_broker_tick_data": True,
        "holdout_opened": False,
        "main_or_vps_modified": False,
    }


def self_test() -> None:
    t = datetime(2025, 5, 5, 10, tzinfo=UTC)
    e = {"formed": t, "touch": t + timedelta(minutes=5), "side": 1}
    opens = {t + timedelta(minutes=i): 10000 + i for i in range(21)}
    assert signed_return(e, e["formed"], opens) == 15
    assert signed_return(e, e["touch"], opens) == 15
    del opens[t + timedelta(minutes=3)]
    assert signed_return(e, e["formed"], opens) is None
    assert signed_return(e, e["touch"], opens) == 15
    assert summarize([{"pts": 3., "week": "x"}], 4)["mean_gross_pts"] == 3


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("--market", type=Path)
    a.add_argument("--ledger", type=Path)
    a.add_argument("--out", type=Path)
    a.add_argument("--self-test", action="store_true")
    z = a.parse_args()
    if z.self_test:
        self_test()
        print("rapid subgroups price chronology synthetic: PASS")
        return
    if not z.market or not z.ledger or not z.out:
        a.error("market ledger out mandatory")
    if checksum(z.market) != MARKET_SHA256:
        raise ValueError("original NAS100 M1 SHA256 mismatch")
    ledger = json.loads(z.ledger.read_text())
    events = events_from_original(ledger)
    opens = collect_opens(market_rows(z.market), needed_opens(events))
    report = adjudicate(events, opens)
    report["sha256_M1"] = checksum(z.market)
    report["sha256_original_ledger"] = checksum(z.ledger)
    report["source_m1_artifact"] = MARKET_ARTIFACT
    report["source_ledger_artifact"] = LEDGER_ARTIFACT
    z.out.parent.mkdir(parents=True, exist_ok=True)
    z.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "old_total": report["old_candidate_count_NOT_V1"],
        "m1_ce_overlap_not_fill": report[
            "m1_price_overlap_while_source_eligible_NOT_FILL"
        ],
        "original_15m": report["all_signals_original_15m_from_next_open"],
        "touch_subgroup_original_15m": report[
            "later_ce_touch_signals_original_15m_from_next_open"
        ],
        "touch_postclose_15m": report[
            "later_ce_touch_cohort_new_15m_after_observed_m1_close"
        ],
        "further_unapproved_G6_spending": report["further_unapproved_G6_spending"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
