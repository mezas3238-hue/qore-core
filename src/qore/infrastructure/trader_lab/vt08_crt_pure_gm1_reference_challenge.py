"""Enumerate raw historical H4 extrema; never select Model #1 old levels.

Reviewers compare multiple PRE-EXISTING references without access to C3 future.
An H4 candle extremum is NOT asserted to be a RomeoTPT-certified CRT high/low.
No entry, no indicator tuning, no PnL and no sizing.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_gm3_real_case_safety import (
    audit_blind_case,
)

H4 = timedelta(hours=4)
SCHEMA = "qore.vt08.crt_pure.gm1_reference_ambiguity_challenge.v1"


def enumerate_reference_dispute(blind: dict[str, Any]) -> dict[str, Any]:
    """Return both H4 C1/C2 raw extrema before any independent adjudication.

    The parent direction is only a research label used to choose which *side*
    is worth examining. This is no endorsement of its authority as Romeo bias.
    """
    # Validate no future, OHLC shape and temporal continuity by the existing
    # audited adapter. A bad case cannot silently pass through this exporter.
    safety = audit_blind_case(blind)
    direction = blind["parent_H4_direction_context"]
    if direction not in ("BULLISH", "BEARISH"):
        raise ValueError("unknown H4 parent direction")
    side = "low" if direction == "BULLISH" else "high"
    references: list[dict[str, Any]] = []
    for origin in ("C1", "C2"):
        ohlc = blind[f"parent_H4_{origin}_ohlc"]
        started = datetime.fromisoformat(ohlc["opened_at_utc"])
        known_at = started + H4
        decision_at = datetime.fromisoformat(blind["decision_clock_utc"])
        if known_at > decision_at:
            raise ValueError("old reference not known before C2 decision")
        for key in ("open_relative", "high_relative", "low_relative", "close_relative"):
            if type(ohlc[key]) is not int:
                raise ValueError("reference price must be integer relative OHLC")
        if not (
            ohlc["low_relative"] <= min(ohlc["open_relative"], ohlc["close_relative"])
            and max(ohlc["open_relative"], ohlc["close_relative"]) <= ohlc["high_relative"]
        ):
            raise ValueError("invalid historical H4 candle geometry")
        references.append(
            {
                "origin": f"H4_{origin}",
                "origin_opened_at_utc": started.isoformat(),
                "raw_extremum_kind": "H4_LOW" if side == "low" else "H4_HIGH",
                "raw_extremum_relative": ohlc[f"{side}_relative"],
                "known_at_utc": known_at.isoformat(),
                "certified_old_crt_level": False,
                "source_selectability": "UNKNOWN",
            }
        )
    distinct = len(set(x["raw_extremum_relative"] for x in references))
    return {
        "schema": SCHEMA,
        "case_id": blind["case_id"],
        "market": blind["market"],
        "decision_clock_utc": blind["decision_clock_utc"],
        "direction_context_engineering_only": direction,
        "two_raw_h4_extrema": references,
        "distinct_raw_price_count": distinct,
        "source_authorized_selection": None,
        "selection_verdict": "UNRESOLVED_BY_PRIMARY_SOURCE",
        "human_reviewer_question": (
            "Are either of these already closed H4 extrema an old CRTH/CRTL "
            "under ORIGINAL RomeoTPT methodology? If both or neither, justify "
            "the tie-break or abstention WITHOUT looking at subsequent candles."
        ),
        "cognitive_input_certified": False,
        "safety_audit_action": safety["reason_action"],
        "not_model1_entry": True,
        "no_profit_loss_or_sizing": True,
        "not_fresh_holdout": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("blind_cases", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    cases = [
        json.loads(line)
        for line in args.blind_cases.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = [enumerate_reference_dispute(case) for case in cases]
    if not rows or len(set(row["case_id"] for row in rows)) != len(rows):
        raise ValueError("empty/duplicate G-M1 reference challenge cases")
    counts = Counter(str(row["distinct_raw_price_count"]) for row in rows)
    summary = {
        "schema": SCHEMA,
        "cases": len(rows),
        "reference_origins_per_case": 2,
        "candidate_reference_count": sum(len(row["two_raw_h4_extrema"]) for row in rows),
        "distinct_raw_price_count_histogram": dict(sorted(counts.items())),
        "source_reference_selection_certified": False,
        "human_original_source_review_completed": False,
        "GM1_PASS": False,
        "GM2_PASS": False,
        "GM3_PASS": False,
        "GM4_PASS": False,
        "GM5_certificate_issued": False,
        "live_authorized": False,
        "sizing_performed": False,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "gm1-reference-dispute-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (args.output / "gm1-reference-dispute-reviewer-only.jsonl").open(
        "w", encoding="utf-8"
    ) as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
