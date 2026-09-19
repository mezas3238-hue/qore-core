"""Build consumed tick windows for R5 NAS100 high-density OCO ambiguity.

Research-only. The manifest contains only ambiguity discovered in already
consumed R5 M1 evidence.

Two ambiguity families are admitted:
- OCO_MULTI_PRICE_FIRST_FILL: multiple distinct OCO entry prices first touch
  the same M1 bar and M1 cannot establish which order filled first.
- OCO_FILL_BAR_PATH: one OCO order is selected, but its fill M1 also touches
  stop and/or target so post-fill order is unknown.

No setup is promoted and no fresh holdout is opened.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import cast

import vt31_nas100_entry_intelligence_oco_lab_v1 as oco

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
    Vt31R22ExecutionPolicy,
)

MARKET = "NAS100"
PARTITION = "r5"
PROVIDER = "USTEC"


def _ms(value: datetime) -> int:
    return int(value.astimezone(UTC).timestamp() * 1000)


def _window_id(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()[:24]


def _order_payload(setup: Vt31R22ExecutableSetup) -> dict[str, object]:
    return {
        "family": setup.selected_family.value,
        "side": setup.side.value,
        "entry": format(setup.entry_price, "f"),
        "initial_stop": format(setup.stop_price, "f"),
        "target": format(setup.target_price, "f"),
        "activation_at": setup.decision_at.astimezone(UTC).isoformat(),
        "activation_ms": _ms(setup.decision_at),
    }


def build(evidence_path: Path) -> dict[str, object]:
    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(evidence_path)
    )
    if provider != PROVIDER:
        raise ValueError(f"expected provider {PROVIDER}, got {provider}")
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("manifest requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }
    policy = Vt31R22ExecutionPolicy()
    windows: list[dict[str, object]] = []
    counts: Counter[str] = Counter()

    for local_day in sorted(by_day):
        day_bars = by_day[local_day]
        timeline = oco._timeline(day_bars, evidence_fingerprint=evidence)
        if timeline is None:
            continue

        fill_candidates: list[tuple[int, Vt31R22ExecutableSetup]] = []
        for candidate in timeline.candidates:
            setup = oco._candidate_order(timeline.source, candidate, policy)
            if setup is None:
                continue
            fill_index, reason = oco._fill_before_invalidation(
                day_bars,
                setup,
                timeline.both_sides_swept_at,
            )
            if reason is not None:
                counts[f"candidate-{reason}"] += 1
            if fill_index is not None:
                fill_candidates.append((fill_index, setup))

        if not fill_candidates:
            continue
        earliest_index = min(index for index, _ in fill_candidates)
        first = [
            setup
            for index, setup in fill_candidates
            if index == earliest_index
        ]
        fill_bar = day_bars[earliest_index]
        opened_at = cast(datetime, getattr(fill_bar, "opened_at"))
        closed_at = cast(datetime, getattr(fill_bar, "closed_at"))
        prices = {item.entry_price for item in first}

        if len(prices) > 1:
            base: dict[str, object] = {
                "classification": "OCO_MULTI_PRICE_FIRST_FILL",
                "partition": PARTITION,
                "market": MARKET,
                "provider": PROVIDER,
                "ny_date": local_day.isoformat(),
                "side": first[0].side.value,
                "tick_window_open_ms": _ms(opened_at),
                "tick_window_close_ms": _ms(closed_at) - 1,
                "fill_bar_opened_at": opened_at.astimezone(UTC).isoformat(),
                "fill_bar_closed_at": closed_at.astimezone(UTC).isoformat(),
                "orders": [
                    _order_payload(item)
                    for item in sorted(
                        first,
                        key=lambda item: (
                            item.decision_at,
                            item.selected_family.value,
                            item.entry_price,
                        ),
                    )
                ],
            }
            base["window_id"] = _window_id(base)
            windows.append(base)
            counts["OCO_MULTI_PRICE_FIRST_FILL"] += 1
            continue

        selected = sorted(
            first,
            key=lambda item: (
                item.decision_at,
                item.selected_family.value,
            ),
        )[0]
        high = getattr(fill_bar, "high")
        low = getattr(fill_bar, "low")
        side = selected.side.value
        stop_hit = (
            low <= selected.stop_price
            if side == "long"
            else high >= selected.stop_price
        )
        target_hit = (
            high >= selected.target_price
            if side == "long"
            else low <= selected.target_price
        )
        if not (stop_hit or target_hit):
            continue

        base = {
            "classification": "OCO_FILL_BAR_PATH",
            "partition": PARTITION,
            "market": MARKET,
            "provider": PROVIDER,
            "ny_date": local_day.isoformat(),
            "side": side,
            "tick_window_open_ms": _ms(opened_at),
            "tick_window_close_ms": _ms(closed_at) - 1,
            "fill_bar_opened_at": opened_at.astimezone(UTC).isoformat(),
            "fill_bar_closed_at": closed_at.astimezone(UTC).isoformat(),
            "entry": format(selected.entry_price, "f"),
            "initial_stop": format(selected.stop_price, "f"),
            "target": format(selected.target_price, "f"),
            "activation_at": selected.decision_at.astimezone(UTC).isoformat(),
            "activation_ms": _ms(selected.decision_at),
            "family": selected.selected_family.value,
            "m1_high": format(high, "f"),
            "m1_low": format(low, "f"),
        }
        base["window_id"] = _window_id(base)
        windows.append(base)
        counts["OCO_FILL_BAR_PATH"] += 1

    if not windows:
        raise ValueError("high-density ambiguity manifest unexpectedly empty")

    payload: dict[str, object] = {
        "schema": "qore.vt31.nas100.high_density_tick_manifest.v1",
        "research_only": True,
        "opens_new_holdout": False,
        "candidate_status": "RESEARCH_NOT_CERTIFIED",
        "partition": PARTITION,
        "market": MARKET,
        "provider": PROVIDER,
        "source_evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "evidence_software_sha": evidence_sha,
            "checked_at": checked.astimezone(UTC).isoformat(),
        },
        "window_count": len(windows),
        "counts": dict(sorted(counts.items())),
        "windows": sorted(
            windows,
            key=lambda row: (
                cast(int, row["tick_window_open_ms"]),
                cast(str, row["window_id"]),
            ),
        ),
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    payload["sha256"] = hashlib.sha256(encoded).hexdigest()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = build(args.evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "window_count": payload["window_count"],
                "counts": payload["counts"],
                "sha256": payload["sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
