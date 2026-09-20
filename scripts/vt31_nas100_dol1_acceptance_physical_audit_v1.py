"""Audit physical executability of the DOL1 acceptance runner branch.

Certified variant: EQ50_COMPRESSED_ACCEPT_RUN25.

For compressed-reference trades where EQ is reached first and DOL1 is later
touched, the research selector decides runner eligibility from the CLOSE of
that DOL1-touch M1. A live executor cannot both wait for that close and
retroactively exit the non-runner 25% at the exact DOL1 price.

This diagnostic measures the execution delta:
- certified accounting for non-accept compressed case: remaining 50% at DOL1;
- physically causal accounting: 25% at DOL1 + 25% at DOL1-touch-bar close.

No strategy policy is changed.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import vt31_nas100_alt_tier_bifurcation_forensics_v1 as alt
import vt31_nas100_path_causal_target_ladder_v2 as pathcausal
import vt31_nas100_structural_target_ladder_frontier_v1 as ladder

from qore.infrastructure.trader_lab.vt31_silver_bullet_r2_5_multi_index_research import (
    _day,
    _wall,
    load_market_evidence,
)

SCHEMA = "qore.vt31.nas100.dol1_acceptance_physical_audit.v1"


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _forward(side: str, entry: Decimal, level: Decimal) -> bool:
    return level > entry if side == "long" else level < entry


def replay(path: Path, *, partition: str) -> dict[str, object]:
    rows, _evidence, _diagnostics, _stats = alt._current_rows(path)
    series, account, fingerprint, checked, evidence_sha, provider = load_market_evidence(path)
    raw: dict[date, list[object]] = defaultdict(list)
    for bar in series:
        raw[_day(bar.opened_at)].append(bar)
    by_day = {
        day: tuple(sorted(items, key=lambda item: item.opened_at))
        for day, items in raw.items()
    }

    # Apply the already-certified physical precedence filter so only cases
    # eligible for the EQ overlay are audited.
    adjusted_base, _diag = pathcausal._apply_path_causal(rows, by_day=by_day)
    # Map by signal for the overlay-allowed marker/reason from path-causal output.
    base_by_signal = {str(row["signal_at"]): row for row in adjusted_base}

    cases: list[dict[str, object]] = []
    total_delta = Decimal("0")

    for original in rows:
        row = base_by_signal.get(str(original["signal_at"]), original)
        if str(row.get("reference_volatility_state")) != "compressed":
            continue

        entry = _d(row["entry"])
        stop = _d(row["initial_stop"])
        dol1 = _d(row["structural_target"])
        risk = abs(entry - stop)
        if risk <= 0:
            continue
        side = str(row["side"])
        day = date.fromisoformat(str(row["local_date"]))
        bars = by_day.get(day, ())
        reference = tuple(
            bar for bar in bars
            if (9, 0, 0) <= _wall(bar.opened_at) < (10, 0, 0)
        )
        if len(reference) != 60:
            continue
        ref_high = max(_d(bar.high) for bar in reference)
        ref_low = min(_d(bar.low) for bar in reference)
        eq = (ref_high + ref_low) / Decimal("2")
        if not _forward(side, entry, eq):
            continue

        filled_at = datetime.fromisoformat(str(row["filled_at"]))
        terminal_at = datetime.fromisoformat(str(row["exit_at"]))
        fill_index = next(
            (i for i, bar in enumerate(bars) if bar.closed_at == filled_at),
            None,
        )
        if fill_index is None:
            continue

        eq_index = ladder._first_touch_index(
            bars,
            start_index=fill_index,
            terminal_at=terminal_at,
            side=side,
            level=eq,
        )
        if eq_index is None:
            continue
        dol1_index = ladder._first_touch_index(
            bars,
            start_index=eq_index + 1,
            terminal_at=terminal_at,
            side=side,
            level=dol1,
        )
        if dol1_index is None:
            continue

        bar = bars[dol1_index]
        close = _d(bar.close)
        accepts = close >= dol1 if side == "long" else close <= dol1
        if accepts:
            continue

        dol1_r = abs(dol1 - entry) / risk
        close_r = (
            (close - entry) / risk
            if side == "long"
            else (entry - close) / risk
        )
        # Only 25% of original position is affected: the first 25% of the
        # post-EQ remainder can be preassigned to DOL1; the potential runner
        # must survive until the close decision.
        delta = Decimal("0.25") * (close_r - dol1_r)
        total_delta += delta
        cases.append({
            "local_date": row["local_date"],
            "signal_at": row["signal_at"],
            "side": side,
            "family": row.get("entry_family"),
            "tier": row.get("tier"),
            "dol1_r": format(dol1_r, "f"),
            "touch_close_r": format(close_r, "f"),
            "portfolio_r_delta": format(delta, "f"),
            "dol1_touch_closed_at": bar.closed_at.isoformat(),
        })

    return {
        "schema": SCHEMA,
        "partition": partition,
        "case_count": len(cases),
        "sum_portfolio_r_delta": format(total_delta, "f"),
        "cases": cases,
        "physically_exact_under_current_accounting": len(cases) == 0,
        "evidence": {
            "account_fingerprint": account,
            "evidence_fingerprint": fingerprint,
            "checked_at": checked.isoformat(),
            "software_sha": evidence_sha,
            "provider": provider,
        },
        "governance": {
            "diagnostic_only": True,
            "strategy_changed": False,
            "runtime_policy_changed": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--partition", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = replay(args.evidence, partition=args.partition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "partition": payload["partition"],
        "case_count": payload["case_count"],
        "sum_portfolio_r_delta": payload["sum_portfolio_r_delta"],
        "physically_exact": payload["physically_exact_under_current_accounting"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
