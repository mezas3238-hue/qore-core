"""Exact consumed tick manifest for NEG_P100 partial-management fill-bar ambiguity.

This is an execution-evidence manifest, not a market-discovery lab. It reuses
the existing ALLOC_G targeted-management replay and instruments the existing
partial-runner simulator only to record exact M1 fill windows where the
predeclared +1R partial overlay is path-ambiguous.

Selection, WAIT1025 authorization, OCO routing, monthly budgets and causal
negative-context classification remain exactly those of the existing Core
labs. Terminal PnL is not used to select a window.
"""
# ruff: noqa: B009
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import vt31_nas100_intelligence_policy_lab_v2b as v2b
import vt31_nas100_r5_corrective_management_frontier_v1 as corrective
import vt31_nas100_specialist_r1_candidate as specialist

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    load_market_evidence,
)
from qore.infrastructure.traders import vt31_silver_bullet_r2_2 as silver
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import (
    Vt31R22ExecutableSetup,
)

SCHEMA = "qore.vt31.nas100.neg_p100_partial_tick_manifest.v1"
MARKET = "NAS100"
PROVIDER = "USTEC"
PARTIAL_R = Decimal("1.00")
EXPECTED_SOURCE_SHA256 = (
    "bd729056fadc30d20045e4677240b3a6cbb65123ced317e7413b6ffe81936ddf"
)


def _ms(value: datetime) -> int:
    return int(value.astimezone(UTC).timestamp() * 1000)


def _window_id(payload: dict[str, object]) -> str:
    material = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(material).hexdigest()[:24]


def build(path: Path, *, partition: str) -> dict[str, object]:
    if silver.SOURCE_SHA256 != EXPECTED_SOURCE_SHA256:
        raise AssertionError("Silver Bullet source identity changed")

    series, account, evidence, checked, evidence_sha, provider = (
        load_market_evidence(path)
    )
    if provider != PROVIDER:
        raise ValueError(f"expected {PROVIDER}, got {provider}")
    if not series or getattr(series[0], "instrument").symbol != MARKET:
        raise ValueError("NEG_P100 manifest requires NAS100")

    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(getattr(bar, "opened_at"))].append(bar)
    by_day = {
        local_day: tuple(
            sorted(items, key=lambda item: getattr(item, "opened_at"))
        )
        for local_day, items in raw.items()
    }
    context_by_day = specialist._context_map(by_day)

    captured: list[dict[str, object]] = []
    original = v2b._simulate_partial_runner

    def instrumented(
        day_bars: tuple[object, ...],
        setup: Vt31R22ExecutableSetup,
        local_r: Decimal,
    ) -> dict[str, object]:
        outcome = original(day_bars, setup, local_r)
        if (
            local_r == PARTIAL_R
            and outcome.get("status") == "censored-fill-bar-path"
        ):
            fill_index = v2b._fill_index(day_bars, setup)
            if fill_index is None:
                raise AssertionError("censored fill-bar path without fill")
            fill_bar = day_bars[fill_index]
            opened_at = cast(datetime, getattr(fill_bar, "opened_at"))
            closed_at = cast(datetime, getattr(fill_bar, "closed_at"))
            risk = setup.initial_risk
            partial = v2b._target_price(
                setup.side.value,
                setup.entry_price,
                risk,
                local_r,
            )
            base: dict[str, object] = {
                "classification": "NEG_P100_PARTIAL_FILL_BAR_PATH",
                "variant": "NEG_P100",
                "partition": partition,
                "market": MARKET,
                "provider": PROVIDER,
                "ny_date": _day(setup.decision_at).isoformat(),
                "side": setup.side.value,
                "family": setup.selected_family.value,
                "entry": format(setup.entry_price, "f"),
                "initial_stop": format(setup.stop_price, "f"),
                "partial_target": format(partial, "f"),
                "partial_target_r": format(local_r, "f"),
                "structural_target": format(setup.target_price, "f"),
                "boundary_r": format(
                    abs(setup.target_price - setup.entry_price) / risk,
                    "f",
                ),
                "activation_at": setup.decision_at.astimezone(UTC).isoformat(),
                "activation_ms": _ms(setup.decision_at),
                "fill_bar_opened_at": opened_at.astimezone(UTC).isoformat(),
                "fill_bar_closed_at": closed_at.astimezone(UTC).isoformat(),
                "tick_window_open_ms": _ms(opened_at),
                "tick_window_close_ms": _ms(closed_at) - 1,
                "m1_low": format(
                    Decimal(str(getattr(fill_bar, "low"))),
                    "f",
                ),
                "m1_high": format(
                    Decimal(str(getattr(fill_bar, "high"))),
                    "f",
                ),
            }
            base["window_id"] = _window_id(base)
            captured.append(base)
        return outcome

    v2b._simulate_partial_runner = instrumented
    try:
        first_rows, diagnostics = corrective._first_rows(
            by_day,
            context_by_day,
            evidence=evidence,
            alt_partial_r=PARTIAL_R,
            secondary_route_policy="ORIGINAL",
            secondary_partial_scope="CAUSAL_NEGATIVE",
        )
    finally:
        v2b._simulate_partial_runner = original

    unique = {
        cast(str, row["window_id"]): row
        for row in captured
    }
    windows = sorted(
        unique.values(),
        key=lambda row: (
            cast(int, row["tick_window_open_ms"]),
            cast(str, row["window_id"]),
        ),
    )
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "research_only": True,
        "opens_new_holdout": False,
        "candidate_status": "RESEARCH_NOT_CERTIFIED",
        "partition": partition,
        "market": MARKET,
        "provider": PROVIDER,
        "variant": "NEG_P100",
        "partial_target_r": "1.00",
        "window_count": len(windows),
        "classification_counts": dict(
            sorted(
                Counter(
                    cast(str, row["classification"])
                    for row in windows
                ).items()
            )
        ),
        "first_terminal_trade_count": len(first_rows),
        "first_diagnostics_status_counts": diagnostics["status_counts"],
        "windows": windows,
        "source_evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": evidence,
            "evidence_software_sha": evidence_sha,
            "checked_at": checked.astimezone(UTC).isoformat(),
        },
        "governance": {
            "silver_bullet_modified": False,
            "existing_first_rows_reused": True,
            "existing_partial_runner_reused": True,
            "existing_causal_negative_classifier_reused": True,
            "terminal_pnl_used_to_form_window": False,
            "fold_identity_used_at_runtime": False,
            "future_bar_used_to_authorize_trade": False,
            "policy_promoted": False,
            "live_authorized": False,
            "production_authorized": False,
        },
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
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = build(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "partition": payload["partition"],
                "window_count": payload["window_count"],
                "first_terminal_trade_count": payload[
                    "first_terminal_trade_count"
                ],
                "classification_counts": payload[
                    "classification_counts"
                ],
                "sha256": payload["sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
